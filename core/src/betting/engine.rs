use super::types::*;
use crate::state::StateManager;
use anyhow::{Result, Context};
use dashmap::DashMap;
use std::sync::Arc;
use tokio::time::{Duration, interval};
use tracing::{info, warn, error};
use sqlx::{Pool, Postgres, Row};
use chrono::Utc;

pub struct BettingEngine {
    state_manager: Arc<StateManager>,
    db_pool: Pool<Postgres>,
    active_bets: DashMap<String, Bet>, // bet_id -> Bet
    user_balances: DashMap<String, UserBalance>, // user_id:stream_id -> UserBalance
}

impl BettingEngine {
    pub async fn new(
        state_manager: Arc<StateManager>,
        database_url: &str,
    ) -> Result<Self> {
        let db_pool = sqlx::postgres::PgPool::connect(database_url).await
            .context("Failed to connect to PostgreSQL")?;

        // Run migrations
        sqlx::migrate!("./migrations").run(&db_pool).await
            .context("Failed to run database migrations")?;

        let engine = Self {
            state_manager,
            db_pool,
            active_bets: DashMap::new(),
            user_balances: DashMap::new(),
        };

        // Start background tasks
        engine.start_bet_resolution_monitor().await;
        engine.start_balance_sync_task().await;

        Ok(engine)
    }

    pub async fn place_bet(&self, bet_request: BetRequest) -> Result<BetResult> {
        let balance_key = format!("{}:{}", bet_request.user_id, bet_request.stream_id);

        // Get or create user balance
        let mut user_balance = self.get_or_create_user_balance(
            &bet_request.user_id,
            &bet_request.stream_id,
        ).await?;

        // Check if user can place the bet
        if !user_balance.can_place_bet(bet_request.stake_amount) {
            return Ok(BetResult {
                bet_id: String::new(),
                success: false,
                message: format!(
                    "Insufficient balance: ${:.2} available, ${:.2} required",
                    user_balance.available_balance(),
                    bet_request.stake_amount
                ),
                remaining_balance: user_balance.available_balance(),
                bet_details: None,
            });
        }

        // Calculate odds based on bet type and current market
        let odds = self.calculate_odds(&bet_request).await?;

        // Create the bet
        let bet = Bet::new(
            bet_request.user_id.clone(),
            bet_request.stream_id.clone(),
            bet_request.bet_type,
            bet_request.stake_amount,
            bet_request.prediction,
            bet_request.time_window_seconds,
            odds,
        );

        // Deduct from balance
        if !user_balance.place_bet(bet_request.stake_amount) {
            return Ok(BetResult {
                bet_id: String::new(),
                success: false,
                message: "Failed to place bet due to balance issue".to_string(),
                remaining_balance: user_balance.available_balance(),
                bet_details: None,
            });
        }

        // Store bet in database
        self.store_bet_in_db(&bet).await?;

        // Store bet in active bets
        self.active_bets.insert(bet.id.clone(), bet.clone());

        // Update user balance in cache and Redis
        self.user_balances.insert(balance_key.clone(), user_balance.clone());
        self.sync_balance_to_redis(&user_balance).await?;

        info!(
            "Placed bet {} for user {} on stream {} (${:.2})",
            bet.id, bet.user_id, bet.stream_id, bet.stake_amount
        );

        Ok(BetResult {
            bet_id: bet.id.clone(),
            success: true,
            message: "Bet placed successfully".to_string(),
            remaining_balance: user_balance.available_balance(),
            bet_details: Some(bet),
        })
    }

    async fn get_or_create_user_balance(
        &self,
        user_id: &str,
        stream_id: &str,
    ) -> Result<UserBalance> {
        let balance_key = format!("{}:{}", user_id, stream_id);

        // Check cache first
        if let Some(balance) = self.user_balances.get(&balance_key) {
            return Ok(balance.clone());
        }

        // Check database
        let row = sqlx::query(
            "SELECT * FROM user_balances WHERE user_id = $1 AND stream_id = $2"
        )
        .bind(user_id)
        .bind(stream_id)
        .fetch_optional(&self.db_pool)
        .await?;

        if let Some(row) = row {
            let balance = UserBalance {
                user_id: row.get("user_id"),
                stream_id: row.get("stream_id"),
                total_deposited: row.get("total_deposited"),
                activation_cost: row.get("activation_cost"),
                betting_balance: row.get("betting_balance"),
                active_bets_total: row.get("active_bets_total"),
                total_winnings: row.get("total_winnings"),
                total_losses: row.get("total_losses"),
                bet_count: row.get("bet_count"),
                created_at: row.get("created_at"),
                last_updated: row.get("last_updated"),
            };

            self.user_balances.insert(balance_key, balance.clone());
            Ok(balance)
        } else {
            // Create new balance (this would happen when user first joins a stream)
            let default_deposit = 50.0; // Default for development
            let activation_cost = 10.0;
            
            let mut balance = UserBalance::new(
                user_id.to_string(),
                stream_id.to_string(),
                default_deposit,
                activation_cost,
            );

            self.store_balance_in_db(&balance).await?;
            self.user_balances.insert(balance_key, balance.clone());
            
            Ok(balance)
        }
    }

    async fn calculate_odds(&self, bet_request: &BetRequest) -> Result<f64> {
        // Simple odds calculation - in a real system this would be more sophisticated
        let base_odds = match bet_request.bet_type {
            BetType::Binary => 1.9,      // Slightly house favored
            BetType::Quantity => 2.1,    // Harder to predict exactly
            BetType::Timing => 2.5,      // Time-sensitive, harder
            BetType::Pattern => 3.0,     // Most complex
        };

        // Adjust based on time window (shorter = higher odds)
        let time_factor = if bet_request.time_window_seconds < 30 {
            1.2
        } else if bet_request.time_window_seconds < 120 {
            1.0
        } else {
            0.9
        };

        Ok(base_odds * time_factor)
    }

    async fn store_bet_in_db(&self, bet: &Bet) -> Result<()> {
        let prediction_json = serde_json::to_string(&bet.prediction)?;
        
        sqlx::query(
            r#"
            INSERT INTO bets (
                id, user_id, stream_id, bet_type, stake_amount, prediction,
                status, created_at, resolution_deadline, potential_payout, odds
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            "#
        )
        .bind(&bet.id)
        .bind(&bet.user_id)
        .bind(&bet.stream_id)
        .bind(serde_json::to_string(&bet.bet_type)?)
        .bind(bet.stake_amount)
        .bind(prediction_json)
        .bind(serde_json::to_string(&bet.status)?)
        .bind(bet.created_at)
        .bind(bet.resolution_deadline)
        .bind(bet.potential_payout)
        .bind(bet.odds)
        .execute(&self.db_pool)
        .await?;

        Ok(())
    }

    async fn store_balance_in_db(&self, balance: &UserBalance) -> Result<()> {
        sqlx::query(
            r#"
            INSERT INTO user_balances (
                user_id, stream_id, total_deposited, activation_cost, betting_balance,
                active_bets_total, total_winnings, total_losses, bet_count, created_at, last_updated
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ON CONFLICT (user_id, stream_id) DO UPDATE SET
                betting_balance = EXCLUDED.betting_balance,
                active_bets_total = EXCLUDED.active_bets_total,
                total_winnings = EXCLUDED.total_winnings,
                total_losses = EXCLUDED.total_losses,
                bet_count = EXCLUDED.bet_count,
                last_updated = EXCLUDED.last_updated
            "#
        )
        .bind(&balance.user_id)
        .bind(&balance.stream_id)
        .bind(balance.total_deposited)
        .bind(balance.activation_cost)
        .bind(balance.betting_balance)
        .bind(balance.active_bets_total)
        .bind(balance.total_winnings)
        .bind(balance.total_losses)
        .bind(balance.bet_count as i32)
        .bind(balance.created_at)
        .bind(balance.last_updated)
        .execute(&self.db_pool)
        .await?;

        Ok(())
    }

    async fn sync_balance_to_redis(&self, balance: &UserBalance) -> Result<()> {
        let balance_json = serde_json::to_string(balance)?;
        let key = format!("balance:{}:{}", balance.user_id, balance.stream_id);
        
        self.state_manager.set_key_with_expiry(&key, &balance_json, 3600).await?;
        Ok(())
    }

    pub async fn resolve_bet(
        &self,
        bet_id: &str,
        actual_result: ActualResult,
        confidence_score: f64,
    ) -> Result<bool> {
        if let Some(mut bet_entry) = self.active_bets.get_mut(bet_id) {
            let bet = bet_entry.value_mut();

            if !bet.can_resolve() {
                return Ok(false);
            }

            // Determine if bet won
            let won = self.check_bet_outcome(&bet.prediction, &actual_result);
            let payout_amount = if won { bet.potential_payout } else { 0.0 };

            // Create resolution
            let resolution = BetResolution {
                actual_result,
                won,
                payout_amount,
                resolved_at: Utc::now(),
                confidence_score,
            };

            bet.resolution_result = Some(resolution);
            bet.status = BetStatus::Resolved;

            // Update user balance
            let balance_key = format!("{}:{}", bet.user_id, bet.stream_id);
            if let Some(mut balance_entry) = self.user_balances.get_mut(&balance_key) {
                let balance = balance_entry.value_mut();
                balance.resolve_bet(bet.stake_amount, payout_amount);
                
                // Update database
                self.store_balance_in_db(balance).await?;
                self.sync_balance_to_redis(balance).await?;
            }

            // Update bet in database
            self.update_bet_in_db(bet).await?;

            info!("Resolved bet {} - Won: {}, Payout: ${:.2}", bet_id, won, payout_amount);
            Ok(true)
        } else {
            Ok(false)
        }
    }

    fn check_bet_outcome(&self, prediction: &Prediction, actual: &ActualResult) -> bool {
        match (prediction, actual) {
            (Prediction::Binary { will_occur }, ActualResult::Binary { occurred }) => {
                will_occur == occurred
            }
            (
                Prediction::Quantity { predicted_value, tolerance },
                ActualResult::Quantity { actual_value }
            ) => {
                (predicted_value - actual_value).abs() <= *tolerance
            }
            (
                Prediction::Timing { predicted_seconds, tolerance },
                ActualResult::Timing { actual_seconds }
            ) => {
                (predicted_seconds - actual_seconds).abs() <= *tolerance
            }
            (
                Prediction::Pattern { sequence },
                ActualResult::Pattern { actual_sequence }
            ) => {
                sequence == actual_sequence
            }
            _ => false,
        }
    }

    async fn update_bet_in_db(&self, bet: &Bet) -> Result<()> {
        let resolution_json = bet.resolution_result.as_ref()
            .map(|r| serde_json::to_string(r))
            .transpose()?;

        sqlx::query(
            "UPDATE bets SET status = $1, resolution_result = $2 WHERE id = $3"
        )
        .bind(serde_json::to_string(&bet.status)?)
        .bind(resolution_json)
        .bind(&bet.id)
        .execute(&self.db_pool)
        .await?;

        Ok(())
    }

    async fn start_bet_resolution_monitor(&self) {
        let active_bets = self.active_bets.clone();
        
        tokio::spawn(async move {
            let mut interval = interval(Duration::from_secs(1));
            
            loop {
                interval.tick().await;
                
                // Check for expired bets
                let now = Utc::now();
                for mut entry in active_bets.iter_mut() {
                    let bet = entry.value_mut();
                    
                    if bet.status == BetStatus::Active && bet.resolution_deadline < now {
                        bet.status = BetStatus::Expired;
                        warn!("Bet {} expired without resolution", bet.id);
                    }
                }
            }
        });
    }

    async fn start_balance_sync_task(&self) {
        let user_balances = self.user_balances.clone();
        let state_manager = self.state_manager.clone();
        
        tokio::spawn(async move {
            let mut interval = interval(Duration::from_secs(10));
            
            loop {
                interval.tick().await;
                
                // Sync balances to Redis periodically
                for entry in user_balances.iter() {
                    let balance = entry.value();
                    if let Ok(balance_json) = serde_json::to_string(balance) {
                        let key = format!("balance:{}:{}", balance.user_id, balance.stream_id);
                        let _ = state_manager.set_key_with_expiry(&key, &balance_json, 3600).await;
                    }
                }
            }
        });
    }
} 