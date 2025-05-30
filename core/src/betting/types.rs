use serde::{Deserialize, Serialize};
use uuid::Uuid;
use chrono::{DateTime, Utc};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BetRequest {
    pub user_id: String,
    pub stream_id: String,
    pub bet_type: BetType,
    pub stake_amount: f64,
    pub prediction: Prediction,
    pub time_window_seconds: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum BetType {
    Binary,      // Yes/No predictions
    Quantity,    // Numeric predictions
    Timing,      // Event occurrence timing
    Pattern,     // Sequential events
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum Prediction {
    Binary { will_occur: bool },
    Quantity { predicted_value: f64, tolerance: f64 },
    Timing { predicted_seconds: f64, tolerance: f64 },
    Pattern { sequence: Vec<String> },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BetResult {
    pub bet_id: String,
    pub success: bool,
    pub message: String,
    pub remaining_balance: f64,
    pub bet_details: Option<Bet>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Bet {
    pub id: String,
    pub user_id: String,
    pub stream_id: String,
    pub bet_type: BetType,
    pub stake_amount: f64,
    pub prediction: Prediction,
    pub status: BetStatus,
    pub created_at: DateTime<Utc>,
    pub resolution_deadline: DateTime<Utc>,
    pub resolution_result: Option<BetResolution>,
    pub potential_payout: f64,
    pub odds: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum BetStatus {
    Active,
    Resolved,
    Cancelled,
    Expired,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BetResolution {
    pub actual_result: ActualResult,
    pub won: bool,
    pub payout_amount: f64,
    pub resolved_at: DateTime<Utc>,
    pub confidence_score: f64, // Based on how many users bet on same event
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ActualResult {
    Binary { occurred: bool },
    Quantity { actual_value: f64 },
    Timing { actual_seconds: f64 },
    Pattern { actual_sequence: Vec<String> },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UserBalance {
    pub user_id: String,
    pub stream_id: String,
    pub total_deposited: f64,
    pub activation_cost: f64,
    pub betting_balance: f64,
    pub active_bets_total: f64,
    pub total_winnings: f64,
    pub total_losses: f64,
    pub bet_count: u32,
    pub created_at: DateTime<Utc>,
    pub last_updated: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BetEvent {
    pub id: String,
    pub stream_id: String,
    pub event_type: String,
    pub description: String,
    pub detection_method: DetectionMethod,
    pub base_odds: f64,
    pub min_stake: f64,
    pub max_stake: f64,
    pub time_window_seconds: u64,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum DetectionMethod {
    ComputerVision,
    UserConsensus,
    ManualVerification,
    TimeBased,
}

impl Bet {
    pub fn new(
        user_id: String,
        stream_id: String,
        bet_type: BetType,
        stake_amount: f64,
        prediction: Prediction,
        time_window_seconds: u64,
        odds: f64,
    ) -> Self {
        let created_at = Utc::now();
        let resolution_deadline = created_at + chrono::Duration::seconds(time_window_seconds as i64);
        
        Self {
            id: Uuid::new_v4().to_string(),
            user_id,
            stream_id,
            bet_type,
            stake_amount,
            prediction,
            status: BetStatus::Active,
            created_at,
            resolution_deadline,
            resolution_result: None,
            potential_payout: stake_amount * odds,
            odds,
        }
    }

    pub fn is_expired(&self) -> bool {
        Utc::now() > self.resolution_deadline
    }

    pub fn can_resolve(&self) -> bool {
        matches!(self.status, BetStatus::Active) && !self.is_expired()
    }
}

impl UserBalance {
    pub fn new(user_id: String, stream_id: String, total_deposit: f64, activation_cost: f64) -> Self {
        let betting_balance = total_deposit - activation_cost;
        
        Self {
            user_id,
            stream_id,
            total_deposited: total_deposit,
            activation_cost,
            betting_balance,
            active_bets_total: 0.0,
            total_winnings: 0.0,
            total_losses: 0.0,
            bet_count: 0,
            created_at: Utc::now(),
            last_updated: Utc::now(),
        }
    }

    pub fn can_place_bet(&self, amount: f64) -> bool {
        self.betting_balance >= amount
    }

    pub fn place_bet(&mut self, amount: f64) -> bool {
        if self.can_place_bet(amount) {
            self.betting_balance -= amount;
            self.active_bets_total += amount;
            self.bet_count += 1;
            self.last_updated = Utc::now();
            true
        } else {
            false
        }
    }

    pub fn resolve_bet(&mut self, stake: f64, payout: f64) {
        self.active_bets_total -= stake;
        
        if payout > stake {
            // Won
            let winnings = payout - stake;
            self.betting_balance += payout;
            self.total_winnings += winnings;
        } else {
            // Lost (payout = 0)
            self.total_losses += stake;
        }
        
        self.last_updated = Utc::now();
    }

    pub fn available_balance(&self) -> f64 {
        self.betting_balance
    }

    pub fn loss_rate(&self) -> f64 {
        if self.total_deposited > 0.0 {
            self.total_losses / self.total_deposited
        } else {
            0.0
        }
    }
} 