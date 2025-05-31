---
layout: page
title: Micro-Betting System
nav_order: 5
---

# Micro-Betting System
{: .no_toc}

## Table of contents
{: .no_toc .text-delta}

1. TOC
{:toc}

---

## Overview

The Morphine Platform's micro-betting system represents a revolutionary approach to real-time wagering, directly integrated with computer vision analytics and live streaming. Unlike traditional betting systems, our platform enables sub-second betting opportunities based on real-time analysis of stream content.

## Core Concepts

### Micro-Betting Philosophy

Traditional sports betting operates on predetermined outcomes (who wins, final scores, etc.). Micro-betting breaks down events into granular, real-time opportunities:

- **Speed-based bets**: Will the next sprint exceed 25 km/h?
- **Action detection**: Will a jump occur in the next 10 seconds?
- **Performance metrics**: Will the next stride be longer than 2.5m?
- **Computer vision events**: Will the player enter the penalty box?

### Integration with Computer Vision

The betting system is tightly coupled with our Vibrio and Moriarty frameworks:

```
CV Analytics → Event Detection → Bet Generation → User Interface → Bet Resolution
     ↓              ↓                 ↓              ↓               ↓
  Real-time    Pattern Match    Market Creation   User Action   Automated Settle
```

## System Architecture

### Betting Engine Core

```rust
use tokio::sync::{broadcast, mpsc};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MicroBet {
    pub id: String,
    pub user_id: String,
    pub stream_id: String,
    pub bet_type: BetType,
    pub condition: BetCondition,
    pub stake: f64,
    pub odds: f64,
    pub created_at: SystemTime,
    pub expires_at: SystemTime,
    pub status: BetStatus,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum BetType {
    Speed { threshold: f64, direction: Direction },
    Action { action_type: ActionType, timeframe: Duration },
    Position { zone: Zone, entry_exit: EntryExit },
    Performance { metric: Metric, threshold: f64 },
}

pub struct BettingEngine {
    analytics_receiver: broadcast::Receiver<AnalyticsEvent>,
    bet_sender: mpsc::Sender<BetResult>,
    active_bets: Arc<RwLock<HashMap<String, MicroBet>>>,
    bet_generators: Vec<Box<dyn BetGenerator>>,
}

impl BettingEngine {
    pub async fn new() -> Result<Self> {
        let (analytics_tx, analytics_rx) = broadcast::channel(1000);
        let (bet_tx, bet_rx) = mpsc::channel(100);
        
        let generators = vec![
            Box::new(SpeedBetGenerator::new()) as Box<dyn BetGenerator>,
            Box::new(ActionBetGenerator::new()) as Box<dyn BetGenerator>,
            Box::new(PoseBetGenerator::new()) as Box<dyn BetGenerator>,
        ];
        
        Ok(BettingEngine {
            analytics_receiver: analytics_rx,
            bet_sender: bet_tx,
            active_bets: Arc::new(RwLock::new(HashMap::new())),
            bet_generators: generators,
        })
    }
    
    pub async fn process_analytics_stream(&mut self) -> Result<()> {
        while let Ok(analytics) = self.analytics_receiver.recv().await {
            // Generate new betting opportunities
            let new_bets = self.generate_betting_opportunities(&analytics).await?;
            
            // Resolve existing bets
            let resolved_bets = self.resolve_active_bets(&analytics).await?;
            
            // Send updates to clients
            for bet in new_bets {
                self.broadcast_new_bet(bet).await?;
            }
            
            for result in resolved_bets {
                self.broadcast_bet_result(result).await?;
            }
        }
        
        Ok(())
    }
    
    async fn generate_betting_opportunities(&self, analytics: &AnalyticsEvent) -> Result<Vec<MicroBet>> {
        let mut opportunities = Vec::new();
        
        for generator in &self.bet_generators {
            let bets = generator.generate_bets(analytics).await?;
            opportunities.extend(bets);
        }
        
        Ok(opportunities)
    }
}
```

### Bet Generation Strategies

#### 1. Speed-Based Betting

```rust
pub struct SpeedBetGenerator {
    speed_thresholds: Vec<f64>,
    confidence_threshold: f64,
}

impl BetGenerator for SpeedBetGenerator {
    async fn generate_bets(&self, analytics: &AnalyticsEvent) -> Result<Vec<MicroBet>> {
        let mut bets = Vec::new();
        
        if let Some(speed_data) = &analytics.vibrio_result.speed_analysis {
            for detection in &speed_data.detections {
                if detection.confidence > self.confidence_threshold {
                    // Generate bets for different speed thresholds
                    for &threshold in &self.speed_thresholds {
                        if detection.current_speed < threshold * 0.8 {
                            // Only generate bet if current speed is significantly below threshold
                            let bet = MicroBet {
                                id: generate_bet_id(),
                                stream_id: analytics.stream_id.clone(),
                                bet_type: BetType::Speed {
                                    threshold,
                                    direction: Direction::Above,
                                },
                                condition: BetCondition::NextDetection {
                                    timeframe: Duration::from_secs(10),
                                    target_id: detection.track_id.clone(),
                                },
                                odds: self.calculate_speed_odds(detection.current_speed, threshold),
                                expires_at: SystemTime::now() + Duration::from_secs(30),
                                status: BetStatus::Open,
                                ..Default::default()
                            };
                            bets.push(bet);
                        }
                    }
                }
            }
        }
        
        Ok(bets)
    }
}
```

#### 2. Action-Based Betting

```rust
pub struct ActionBetGenerator {
    action_classifiers: HashMap<ActionType, ActionClassifier>,
}

impl BetGenerator for ActionBetGenerator {
    async fn generate_bets(&self, analytics: &AnalyticsEvent) -> Result<Vec<MicroBet>> {
        let mut bets = Vec::new();
        
        if let Some(pose_data) = &analytics.moriarty_result.pose_analysis {
            for pose in &pose_data.poses {
                // Analyze pose for potential actions
                let action_probabilities = self.predict_upcoming_actions(pose).await?;
                
                for (action_type, probability) in action_probabilities {
                    if probability > 0.3 && probability < 0.7 {
                        // Sweet spot for betting - uncertain but plausible
                        let bet = MicroBet {
                            id: generate_bet_id(),
                            stream_id: analytics.stream_id.clone(),
                            bet_type: BetType::Action {
                                action_type,
                                timeframe: Duration::from_secs(15),
                            },
                            condition: BetCondition::ActionDetection {
                                target_id: pose.person_id.clone(),
                                confidence_threshold: 0.8,
                            },
                            odds: self.probability_to_odds(probability),
                            expires_at: SystemTime::now() + Duration::from_secs(45),
                            status: BetStatus::Open,
                            ..Default::default()
                        };
                        bets.push(bet);
                    }
                }
            }
        }
        
        Ok(bets)
    }
}
```

### Bet Resolution Engine

```rust
pub struct BetResolver {
    active_bets: Arc<RwLock<HashMap<String, MicroBet>>>,
    resolution_strategies: HashMap<BetType, Box<dyn ResolutionStrategy>>,
}

impl BetResolver {
    pub async fn resolve_bets(&self, analytics: &AnalyticsEvent) -> Result<Vec<BetResult>> {
        let active_bets = self.active_bets.read().await;
        let mut results = Vec::new();
        
        for (bet_id, bet) in active_bets.iter() {
            if let Some(strategy) = self.resolution_strategies.get(&bet.bet_type) {
                if let Some(result) = strategy.evaluate(bet, analytics).await? {
                    results.push(BetResult {
                        bet_id: bet_id.clone(),
                        outcome: result.outcome,
                        payout: result.calculate_payout(bet.stake, bet.odds),
                        resolved_at: SystemTime::now(),
                        evidence: result.evidence,
                    });
                }
            }
        }
        
        Ok(results)
    }
}

#[async_trait]
trait ResolutionStrategy: Send + Sync {
    async fn evaluate(&self, bet: &MicroBet, analytics: &AnalyticsEvent) -> Result<Option<ResolutionResult>>;
}

struct SpeedResolutionStrategy;

#[async_trait]
impl ResolutionStrategy for SpeedResolutionStrategy {
    async fn evaluate(&self, bet: &MicroBet, analytics: &AnalyticsEvent) -> Result<Option<ResolutionResult>> {
        if let BetType::Speed { threshold, direction } = &bet.bet_type {
            if let Some(speed_data) = &analytics.vibrio_result.speed_analysis {
                for detection in &speed_data.detections {
                    if self.matches_bet_condition(bet, detection) {
                        let outcome = match direction {
                            Direction::Above => detection.current_speed > *threshold,
                            Direction::Below => detection.current_speed < *threshold,
                        };
                        
                        return Ok(Some(ResolutionResult {
                            outcome: if outcome { Outcome::Win } else { Outcome::Loss },
                            evidence: Evidence::Speed {
                                measured_speed: detection.current_speed,
                                threshold: *threshold,
                                timestamp: analytics.timestamp,
                            },
                        }));
                    }
                }
            }
        }
        
        Ok(None)
    }
}
```

## Real-Time Integration

### WebSocket Event Streaming

```typescript
interface BettingWebSocketClient {
  // Incoming events from server
  onNewBettingOpportunity(bet: MicroBet): void;
  onBetResolution(result: BetResult): void;
  onOddsUpdate(betId: string, newOdds: number): void;
  onAnalyticsUpdate(analytics: AnalyticsData): void;
  
  // Outgoing actions to server
  placeBet(bet: PlaceBetRequest): Promise<BetConfirmation>;
  cancelBet(betId: string): Promise<CancelConfirmation>;
  subscribeToStream(streamId: string): Promise<void>;
}

class MorphineBettingClient implements BettingWebSocketClient {
  private websocket: WebSocket;
  private eventHandlers: Map<string, Function> = new Map();
  
  constructor(streamId: string) {
    this.websocket = new WebSocket(`wss://betting.morphine.com/stream/${streamId}`);
    this.setupEventHandlers();
  }
  
  private setupEventHandlers() {
    this.websocket.onmessage = (event) => {
      const message = JSON.parse(event.data) as BettingMessage;
      
      switch (message.type) {
        case 'new_bet_opportunity':
          this.handleNewBettingOpportunity(message.payload);
          break;
        case 'bet_resolved':
          this.handleBetResolution(message.payload);
          break;
        case 'odds_update':
          this.handleOddsUpdate(message.payload);
          break;
        case 'analytics_update':
          this.handleAnalyticsUpdate(message.payload);
          break;
      }
    };
  }
  
  async placeBet(bet: PlaceBetRequest): Promise<BetConfirmation> {
    return new Promise((resolve, reject) => {
      const requestId = generateRequestId();
      
      // Set up response handler
      this.eventHandlers.set(requestId, (response: BetConfirmation) => {
        resolve(response);
        this.eventHandlers.delete(requestId);
      });
      
      // Send bet request
      this.websocket.send(JSON.stringify({
        type: 'place_bet',
        requestId,
        payload: bet
      }));
      
      // Timeout after 5 seconds
      setTimeout(() => {
        if (this.eventHandlers.has(requestId)) {
          this.eventHandlers.delete(requestId);
          reject(new Error('Bet placement timeout'));
        }
      }, 5000);
    });
  }
}
```

### Frontend Betting Interface

```typescript
interface BettingPanelProps {
  streamId: string;
  analytics: AnalyticsData;
  userBalance: number;
}

const BettingPanel: React.FC<BettingPanelProps> = ({ streamId, analytics, userBalance }) => {
  const [activeBets, setActiveBets] = useState<MicroBet[]>([]);
  const [availableOpportunities, setAvailableOpportunities] = useState<MicroBet[]>([]);
  const [bettingClient, setBettingClient] = useState<MorphineBettingClient | null>(null);
  
  useEffect(() => {
    const client = new MorphineBettingClient(streamId);
    
    client.onNewBettingOpportunity = (bet: MicroBet) => {
      setAvailableOpportunities(prev => [...prev, bet]);
      
      // Auto-remove expired opportunities
      setTimeout(() => {
        setAvailableOpportunities(prev => prev.filter(b => b.id !== bet.id));
      }, bet.expires_at.getTime() - Date.now());
    };
    
    client.onBetResolution = (result: BetResult) => {
      setActiveBets(prev => prev.filter(b => b.id !== result.bet_id));
      // Show resolution notification
      showBetResult(result);
    };
    
    setBettingClient(client);
    
    return () => client.disconnect();
  }, [streamId]);
  
  const handlePlaceBet = async (opportunity: MicroBet, stake: number) => {
    if (!bettingClient || stake > userBalance) return;
    
    try {
      const confirmation = await bettingClient.placeBet({
        betId: opportunity.id,
        stake,
        userId: getCurrentUserId()
      });
      
      if (confirmation.success) {
        setActiveBets(prev => [...prev, { ...opportunity, stake }]);
        setAvailableOpportunities(prev => prev.filter(b => b.id !== opportunity.id));
      }
    } catch (error) {
      console.error('Failed to place bet:', error);
    }
  };
  
  return (
    <div className="betting-panel">
      <div className="available-opportunities">
        <h3>Live Betting Opportunities</h3>
        {availableOpportunities.map(opportunity => (
          <BettingOpportunityCard
            key={opportunity.id}
            opportunity={opportunity}
            onPlaceBet={(stake) => handlePlaceBet(opportunity, stake)}
            analytics={analytics}
          />
        ))}
      </div>
      
      <div className="active-bets">
        <h3>Your Active Bets</h3>
        {activeBets.map(bet => (
          <ActiveBetCard key={bet.id} bet={bet} analytics={analytics} />
        ))}
      </div>
    </div>
  );
};

const BettingOpportunityCard: React.FC<{
  opportunity: MicroBet;
  onPlaceBet: (stake: number) => void;
  analytics: AnalyticsData;
}> = ({ opportunity, onPlaceBet, analytics }) => {
  const [stake, setStake] = useState(5);
  const timeRemaining = opportunity.expires_at.getTime() - Date.now();
  
  const getBetDescription = () => {
    switch (opportunity.bet_type.type) {
      case 'speed':
        return `Next speed > ${opportunity.bet_type.threshold} km/h`;
      case 'action':
        return `${opportunity.bet_type.action_type} in next ${opportunity.bet_type.timeframe}s`;
      case 'position':
        return `Player enters ${opportunity.bet_type.zone}`;
      default:
        return 'Unknown bet type';
    }
  };
  
  return (
    <div className="betting-opportunity-card">
      <div className="bet-info">
        <h4>{getBetDescription()}</h4>
        <div className="odds">Odds: {opportunity.odds.toFixed(2)}</div>
        <div className="expires">Expires in {Math.ceil(timeRemaining / 1000)}s</div>
      </div>
      
      <div className="bet-controls">
        <input
          type="number"
          value={stake}
          onChange={(e) => setStake(Number(e.target.value))}
          min="1"
          max="100"
        />
        <button
          onClick={() => onPlaceBet(stake)}
          className="place-bet-btn"
        >
          Bet ${stake} to win ${(stake * opportunity.odds).toFixed(2)}
        </button>
      </div>
      
      <BetAnalyticsPreview opportunity={opportunity} analytics={analytics} />
    </div>
  );
};
```

## Advanced Features

### Machine Learning Odds Calculation

```python
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from typing import Dict, List, Tuple

class OddsCalculationEngine:
    def __init__(self):
        self.models = {
            'speed': SpeedOddsModel(),
            'action': ActionOddsModel(),
            'position': PositionOddsModel()
        }
        
    def calculate_odds(self, bet_type: str, context: AnalyticsContext) -> float:
        model = self.models.get(bet_type)
        if not model:
            return 2.0  # Default odds
            
        probability = model.predict_probability(context)
        
        # Convert probability to odds with house edge
        house_edge = 0.05
        fair_odds = 1.0 / probability
        return fair_odds * (1 + house_edge)

class SpeedOddsModel:
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100)
        self.is_trained = False
        
    def predict_probability(self, context: AnalyticsContext) -> float:
        if not self.is_trained:
            return 0.5  # Default probability
            
        features = self.extract_features(context)
        probability = self.model.predict([features])[0]
        return np.clip(probability, 0.1, 0.9)
    
    def extract_features(self, context: AnalyticsContext) -> List[float]:
        return [
            context.current_speed,
            context.speed_trend,
            context.acceleration,
            context.pose_confidence,
            context.time_in_frame,
            context.environmental_factors.lighting,
            context.environmental_factors.crowd_density
        ]
```

### Risk Management

```rust
pub struct RiskManager {
    max_exposure_per_user: f64,
    max_exposure_per_event: f64,
    volatility_limits: HashMap<BetType, f64>,
}

impl RiskManager {
    pub fn validate_bet(&self, bet: &MicroBet, user_exposure: f64, event_exposure: f64) -> Result<()> {
        // Check user exposure limits
        if user_exposure + bet.stake > self.max_exposure_per_user {
            return Err(RiskError::UserExposureExceeded);
        }
        
        // Check event exposure limits
        if event_exposure + (bet.stake * bet.odds) > self.max_exposure_per_event {
            return Err(RiskError::EventExposureExceeded);
        }
        
        // Check volatility limits
        if let Some(&volatility_limit) = self.volatility_limits.get(&bet.bet_type) {
            let implied_probability = 1.0 / bet.odds;
            if implied_probability < volatility_limit {
                return Err(RiskError::VolatilityTooHigh);
            }
        }
        
        Ok(())
    }
}
```

---

## Next Steps

- [Getting Started](/getting-started) - Set up the complete platform
- [API Reference](/api-reference) - Explore betting APIs
- [Architecture Overview](/architecture) - Understand system integration
- [Computer Vision Deep Dive](/computer-vision) - Learn about analytics integration
