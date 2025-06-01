pub mod imperative;
pub mod logical;
pub mod fuzzy;
pub mod hybrid_engine;

use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BetOutcome {
    pub bet_id: String,
    pub user_id: String,
    pub outcome_type: OutcomeType,
    pub confidence_score: f64,
    pub fuzzy_membership: f64,
    pub logical_satisfaction: bool,
    pub imperative_result: f64,
    pub settlement_amount: f64,
    pub reasoning_trace: Vec<ReasoningStep>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum OutcomeType {
    Win,
    Loss,
    PartialWin,
    Void,
    Split,
    Uncertain,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReasoningStep {
    pub step_id: String,
    pub paradigm: ReasoningParadigm,
    pub input_data: serde_json::Value,
    pub output_data: serde_json::Value,
    pub confidence: f64,
    pub timestamp: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ReasoningParadigm {
    Imperative,
    Logical,
    Fuzzy,
    Hybrid,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BetCondition {
    pub condition_id: String,
    pub condition_type: ConditionType,
    pub parameters: HashMap<String, serde_json::Value>,
    pub fuzzy_sets: HashMap<String, FuzzySet>,
    pub logical_predicates: Vec<LogicalPredicate>,
    pub imperative_rules: Vec<ImperativeRule>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ConditionType {
    SpeedMilestone,
    PoseEvent,
    DetectionCount,
    TimeBasedEvent,
    MultiFactorEvent,
    ComplexPattern,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FuzzySet {
    pub name: String,
    pub membership_function: MembershipFunction,
    pub parameters: Vec<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum MembershipFunction {
    Triangular,
    Trapezoidal,
    Gaussian,
    Sigmoid,
    Bell,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogicalPredicate {
    pub predicate_id: String,
    pub predicate_type: PredicateType,
    pub variables: Vec<String>,
    pub constraints: Vec<Constraint>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum PredicateType {
    Exists,
    ForAll,
    Implies,
    And,
    Or,
    Not,
    Temporal,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Constraint {
    pub constraint_type: ConstraintType,
    pub target_value: f64,
    pub tolerance: f64,
    pub weight: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ConstraintType {
    Equal,
    GreaterThan,
    LessThan,
    Within,
    Outside,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ImperativeRule {
    pub rule_id: String,
    pub condition: String,
    pub action: String,
    pub priority: f64,
    pub execution_context: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PrizePool {
    pub pool_id: String,
    pub total_amount: f64,
    pub distribution_method: DistributionMethod,
    pub participants: Vec<Participant>,
    pub winning_criteria: Vec<BetCondition>,
    pub fuzzy_weights: HashMap<String, f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum DistributionMethod {
    WinnerTakesAll,
    ProportionalSharing,
    TieredDistribution,
    FuzzyProportional,
    HybridDistribution,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Participant {
    pub user_id: String,
    pub bet_amount: f64,
    pub bet_conditions: Vec<BetCondition>,
    pub performance_metrics: HashMap<String, f64>,
    pub fuzzy_scores: HashMap<String, f64>,
}

pub struct HybridReasoningEngine {
    imperative_engine: Arc<imperative::ImperativeEngine>,
    logical_engine: Arc<logical::LogicalEngine>,
    fuzzy_engine: Arc<fuzzy::FuzzyEngine>,
    hybrid_coordinator: Arc<hybrid_engine::HybridCoordinator>,
    
    // State management
    active_bets: Arc<RwLock<HashMap<String, BetCondition>>>,
    prize_pools: Arc<RwLock<HashMap<String, PrizePool>>>,
    reasoning_cache: Arc<RwLock<HashMap<String, BetOutcome>>>,
    
    // Paradigm weights for hybrid decisions
    paradigm_weights: Arc<RwLock<HashMap<String, f64>>>,
}

impl HybridReasoningEngine {
    pub async fn new() -> Self {
        Self {
            imperative_engine: Arc::new(imperative::ImperativeEngine::new()),
            logical_engine: Arc::new(logical::LogicalEngine::new()),
            fuzzy_engine: Arc::new(fuzzy::FuzzyEngine::new()),
            hybrid_coordinator: Arc::new(hybrid_engine::HybridCoordinator::new()),
            
            active_bets: Arc::new(RwLock::new(HashMap::new())),
            prize_pools: Arc::new(RwLock::new(HashMap::new())),
            reasoning_cache: Arc::new(RwLock::new(HashMap::new())),
            
            paradigm_weights: Arc::new(RwLock::new(HashMap::from([
                ("imperative".to_string(), 0.4),
                ("logical".to_string(), 0.3),
                ("fuzzy".to_string(), 0.3),
            ]))),
        }
    }
    
    pub async fn evaluate_bet_outcome(
        &self,
        bet_id: &str,
        event_data: &serde_json::Value,
        context: &HashMap<String, serde_json::Value>
    ) -> Result<BetOutcome, Box<dyn std::error::Error + Send + Sync>> {
        let bet_condition = {
            let bets = self.active_bets.read().await;
            bets.get(bet_id).cloned()
                .ok_or("Bet not found")?
        };
        
        let mut reasoning_trace = Vec::new();
        
        // Parallel evaluation across paradigms
        let (imperative_result, logical_result, fuzzy_result) = tokio::join!(
            self.evaluate_imperative(&bet_condition, event_data, context),
            self.evaluate_logical(&bet_condition, event_data, context),
            self.evaluate_fuzzy(&bet_condition, event_data, context)
        );
        
        // Record reasoning steps
        if let Ok(imp_result) = &imperative_result {
            reasoning_trace.push(ReasoningStep {
                step_id: uuid::Uuid::new_v4().to_string(),
                paradigm: ReasoningParadigm::Imperative,
                input_data: event_data.clone(),
                output_data: serde_json::to_value(imp_result)?,
                confidence: imp_result.confidence,
                timestamp: chrono::Utc::now().timestamp() as f64,
            });
        }
        
        if let Ok(log_result) = &logical_result {
            reasoning_trace.push(ReasoningStep {
                step_id: uuid::Uuid::new_v4().to_string(),
                paradigm: ReasoningParadigm::Logical,
                input_data: event_data.clone(),
                output_data: serde_json::to_value(log_result)?,
                confidence: if log_result.satisfied { 1.0 } else { 0.0 },
                timestamp: chrono::Utc::now().timestamp() as f64,
            });
        }
        
        if let Ok(fuzz_result) = &fuzzy_result {
            reasoning_trace.push(ReasoningStep {
                step_id: uuid::Uuid::new_v4().to_string(),
                paradigm: ReasoningParadigm::Fuzzy,
                input_data: event_data.clone(),
                output_data: serde_json::to_value(fuzz_result)?,
                confidence: fuzz_result.membership,
                timestamp: chrono::Utc::now().timestamp() as f64,
            });
        }
        
        // Hybrid synthesis
        let hybrid_outcome = self.synthesize_hybrid_outcome(
            bet_id,
            &bet_condition,
            imperative_result.ok(),
            logical_result.ok(),
            fuzzy_result.ok(),
            reasoning_trace
        ).await?;
        
        // Cache result
        {
            let mut cache = self.reasoning_cache.write().await;
            cache.insert(bet_id.to_string(), hybrid_outcome.clone());
        }
        
        Ok(hybrid_outcome)
    }
    
    async fn evaluate_imperative(
        &self,
        bet_condition: &BetCondition,
        event_data: &serde_json::Value,
        context: &HashMap<String, serde_json::Value>
    ) -> Result<imperative::ImperativeResult, Box<dyn std::error::Error + Send + Sync>> {
        self.imperative_engine.evaluate(bet_condition, event_data, context).await
    }
    
    async fn evaluate_logical(
        &self,
        bet_condition: &BetCondition,
        event_data: &serde_json::Value,
        context: &HashMap<String, serde_json::Value>
    ) -> Result<logical::LogicalResult, Box<dyn std::error::Error + Send + Sync>> {
        self.logical_engine.evaluate(bet_condition, event_data, context).await
    }
    
    async fn evaluate_fuzzy(
        &self,
        bet_condition: &BetCondition,
        event_data: &serde_json::Value,
        context: &HashMap<String, serde_json::Value>
    ) -> Result<fuzzy::FuzzyResult, Box<dyn std::error::Error + Send + Sync>> {
        self.fuzzy_engine.evaluate(bet_condition, event_data, context).await
    }
    
    async fn synthesize_hybrid_outcome(
        &self,
        bet_id: &str,
        bet_condition: &BetCondition,
        imperative_result: Option<imperative::ImperativeResult>,
        logical_result: Option<logical::LogicalResult>,
        fuzzy_result: Option<fuzzy::FuzzyResult>,
        reasoning_trace: Vec<ReasoningStep>
    ) -> Result<BetOutcome, Box<dyn std::error::Error + Send + Sync>> {
        let weights = self.paradigm_weights.read().await;
        
        // Calculate hybrid scores
        let imperative_score = imperative_result.as_ref()
            .map(|r| r.score * weights.get("imperative").unwrap_or(&0.4))
            .unwrap_or(0.0);
            
        let logical_score = logical_result.as_ref()
            .map(|r| if r.satisfied { 1.0 } else { 0.0 } * weights.get("logical").unwrap_or(&0.3))
            .unwrap_or(0.0);
            
        let fuzzy_score = fuzzy_result.as_ref()
            .map(|r| r.membership * weights.get("fuzzy").unwrap_or(&0.3))
            .unwrap_or(0.0);
        
        let total_score = imperative_score + logical_score + fuzzy_score;
        let confidence = self.calculate_confidence(
            imperative_result.as_ref(),
            logical_result.as_ref(),
            fuzzy_result.as_ref()
        );
        
        // Determine outcome type based on hybrid evaluation
        let outcome_type = self.determine_outcome_type(total_score, confidence);
        
        // Calculate settlement amount based on outcome
        let settlement_amount = self.calculate_settlement_amount(
            bet_id,
            &outcome_type,
            total_score,
            confidence
        ).await?;
        
        Ok(BetOutcome {
            bet_id: bet_id.to_string(),
            user_id: "".to_string(), // Would be filled from bet data
            outcome_type,
            confidence_score: confidence,
            fuzzy_membership: fuzzy_result.as_ref().map(|r| r.membership).unwrap_or(0.0),
            logical_satisfaction: logical_result.as_ref().map(|r| r.satisfied).unwrap_or(false),
            imperative_result: imperative_result.as_ref().map(|r| r.score).unwrap_or(0.0),
            settlement_amount,
            reasoning_trace,
        })
    }
    
    fn calculate_confidence(
        &self,
        imperative: Option<&imperative::ImperativeResult>,
        logical: Option<&logical::LogicalResult>,
        fuzzy: Option<&fuzzy::FuzzyResult>
    ) -> f64 {
        let mut confidence_sum = 0.0;
        let mut count = 0;
        
        if let Some(imp) = imperative {
            confidence_sum += imp.confidence;
            count += 1;
        }
        
        if logical.is_some() {
            confidence_sum += 1.0; // Logical reasoning is binary but certain
            count += 1;
        }
        
        if let Some(fuzz) = fuzzy {
            confidence_sum += fuzz.confidence;
            count += 1;
        }
        
        if count > 0 {
            confidence_sum / count as f64
        } else {
            0.0
        }
    }
    
    fn determine_outcome_type(&self, total_score: f64, confidence: f64) -> OutcomeType {
        match (total_score, confidence) {
            (s, c) if s >= 0.8 && c >= 0.9 => OutcomeType::Win,
            (s, c) if s <= 0.2 && c >= 0.9 => OutcomeType::Loss,
            (s, c) if s >= 0.4 && s < 0.8 && c >= 0.7 => OutcomeType::PartialWin,
            (_, c) if c < 0.5 => OutcomeType::Uncertain,
            (s, _) if s >= 0.3 && s < 0.7 => OutcomeType::Split,
            _ => OutcomeType::Void,
        }
    }
    
    async fn calculate_settlement_amount(
        &self,
        bet_id: &str,
        outcome_type: &OutcomeType,
        score: f64,
        confidence: f64
    ) -> Result<f64, Box<dyn std::error::Error + Send + Sync>> {
        // This would integrate with the actual betting system to get bet amounts
        let base_amount = 100.0; // Placeholder
        
        match outcome_type {
            OutcomeType::Win => Ok(base_amount * 2.0),
            OutcomeType::Loss => Ok(0.0),
            OutcomeType::PartialWin => Ok(base_amount * (1.0 + score)),
            OutcomeType::Split => Ok(base_amount),
            OutcomeType::Uncertain => Ok(base_amount * confidence),
            OutcomeType::Void => Ok(base_amount),
        }
    }
    
    pub async fn distribute_prize_pool(
        &self,
        pool_id: &str
    ) -> Result<HashMap<String, f64>, Box<dyn std::error::Error + Send + Sync>> {
        let prize_pool = {
            let pools = self.prize_pools.read().await;
            pools.get(pool_id).cloned()
                .ok_or("Prize pool not found")?
        };
        
        match prize_pool.distribution_method {
            DistributionMethod::WinnerTakesAll => {
                self.distribute_winner_takes_all(&prize_pool).await
            },
            DistributionMethod::ProportionalSharing => {
                self.distribute_proportional(&prize_pool).await
            },
            DistributionMethod::TieredDistribution => {
                self.distribute_tiered(&prize_pool).await
            },
            DistributionMethod::FuzzyProportional => {
                self.distribute_fuzzy_proportional(&prize_pool).await
            },
            DistributionMethod::HybridDistribution => {
                self.distribute_hybrid(&prize_pool).await
            },
        }
    }
    
    async fn distribute_winner_takes_all(
        &self,
        prize_pool: &PrizePool
    ) -> Result<HashMap<String, f64>, Box<dyn std::error::Error + Send + Sync>> {
        let mut distribution = HashMap::new();
        
        // Find participant with highest performance
        let winner = prize_pool.participants.iter()
            .max_by(|a, b| {
                let a_score: f64 = a.performance_metrics.values().sum();
                let b_score: f64 = b.performance_metrics.values().sum();
                a_score.partial_cmp(&b_score).unwrap_or(std::cmp::Ordering::Equal)
            });
        
        if let Some(winner) = winner {
            distribution.insert(winner.user_id.clone(), prize_pool.total_amount);
        }
        
        Ok(distribution)
    }
    
    async fn distribute_proportional(
        &self,
        prize_pool: &PrizePool
    ) -> Result<HashMap<String, f64>, Box<dyn std::error::Error + Send + Sync>> {
        let mut distribution = HashMap::new();
        
        let total_bet_amount: f64 = prize_pool.participants.iter()
            .map(|p| p.bet_amount)
            .sum();
        
        for participant in &prize_pool.participants {
            let proportion = participant.bet_amount / total_bet_amount;
            let payout = prize_pool.total_amount * proportion;
            distribution.insert(participant.user_id.clone(), payout);
        }
        
        Ok(distribution)
    }
    
    async fn distribute_tiered(
        &self,
        prize_pool: &PrizePool
    ) -> Result<HashMap<String, f64>, Box<dyn std::error::Error + Send + Sync>> {
        let mut distribution = HashMap::new();
        
        // Sort participants by performance
        let mut sorted_participants = prize_pool.participants.clone();
        sorted_participants.sort_by(|a, b| {
            let a_score: f64 = a.performance_metrics.values().sum();
            let b_score: f64 = b.performance_metrics.values().sum();
            b_score.partial_cmp(&a_score).unwrap_or(std::cmp::Ordering::Equal)
        });
        
        // Tiered distribution: 50%, 30%, 20% for top 3
        let tiers = vec![0.5, 0.3, 0.2];
        for (i, participant) in sorted_participants.iter().take(3).enumerate() {
            let payout = prize_pool.total_amount * tiers.get(i).unwrap_or(&0.0);
            distribution.insert(participant.user_id.clone(), payout);
        }
        
        Ok(distribution)
    }
    
    async fn distribute_fuzzy_proportional(
        &self,
        prize_pool: &PrizePool
    ) -> Result<HashMap<String, f64>, Box<dyn std::error::Error + Send + Sync>> {
        let mut distribution = HashMap::new();
        
        // Calculate fuzzy membership for each participant
        let total_fuzzy_score: f64 = prize_pool.participants.iter()
            .map(|p| p.fuzzy_scores.values().sum::<f64>())
            .sum();
        
        for participant in &prize_pool.participants {
            let fuzzy_score: f64 = participant.fuzzy_scores.values().sum();
            let fuzzy_proportion = if total_fuzzy_score > 0.0 {
                fuzzy_score / total_fuzzy_score
            } else {
                1.0 / prize_pool.participants.len() as f64
            };
            
            let payout = prize_pool.total_amount * fuzzy_proportion;
            distribution.insert(participant.user_id.clone(), payout);
        }
        
        Ok(distribution)
    }
    
    async fn distribute_hybrid(
        &self,
        prize_pool: &PrizePool
    ) -> Result<HashMap<String, f64>, Box<dyn std::error::Error + Send + Sync>> {
        // Combine multiple distribution methods using hybrid reasoning
        let winner_dist = self.distribute_winner_takes_all(prize_pool).await?;
        let prop_dist = self.distribute_proportional(prize_pool).await?;
        let fuzzy_dist = self.distribute_fuzzy_proportional(prize_pool).await?;
        
        let mut hybrid_distribution = HashMap::new();
        
        // Weighted combination of distribution methods
        let weights = [0.4, 0.3, 0.3]; // Winner, Proportional, Fuzzy
        
        for participant in &prize_pool.participants {
            let user_id = &participant.user_id;
            let winner_amount = winner_dist.get(user_id).unwrap_or(&0.0) * weights[0];
            let prop_amount = prop_dist.get(user_id).unwrap_or(&0.0) * weights[1];
            let fuzzy_amount = fuzzy_dist.get(user_id).unwrap_or(&0.0) * weights[2];
            
            let total_amount = winner_amount + prop_amount + fuzzy_amount;
            hybrid_distribution.insert(user_id.clone(), total_amount);
        }
        
        Ok(hybrid_distribution)
    }
    
    pub async fn add_bet_condition(&self, bet_id: String, condition: BetCondition) {
        let mut bets = self.active_bets.write().await;
        bets.insert(bet_id, condition);
    }
    
    pub async fn add_prize_pool(&self, pool: PrizePool) {
        let mut pools = self.prize_pools.write().await;
        pools.insert(pool.pool_id.clone(), pool);
    }
    
    pub async fn update_paradigm_weights(&self, weights: HashMap<String, f64>) {
        let mut current_weights = self.paradigm_weights.write().await;
        for (paradigm, weight) in weights {
            current_weights.insert(paradigm, weight);
        }
    }
    
    pub async fn get_reasoning_trace(&self, bet_id: &str) -> Option<Vec<ReasoningStep>> {
        let cache = self.reasoning_cache.read().await;
        cache.get(bet_id).map(|outcome| outcome.reasoning_trace.clone())
    }
} 