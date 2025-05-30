use axum::{
    extract::{
        ws::{WebSocket, Message},
        WebSocketUpgrade,
        Extension,
    },
    response::Response,
};
use serde::{Deserialize, Serialize};
use tokio::sync::broadcast;
use std::sync::Arc;
use tracing::{info, warn, error};
use uuid::Uuid;

use crate::AppState;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum WebSocketMessage {
    // Client -> Server
    JoinStream { stream_id: String, user_id: String },
    LeaveStream { stream_id: String },
    PlaceBet { bet_request: crate::betting::BetRequest },
    PledgeToStream { stream_id: String, amount: f64 },
    
    // Server -> Client
    StreamUpdate { stream_id: String, status: crate::stream::StreamStatus },
    BetUpdate { bet_id: String, result: crate::betting::BetResult },
    AnalyticsUpdate { stream_id: String, data: AnalyticsData },
    BalanceUpdate { user_id: String, stream_id: String, balance: f64 },
    ErrorMessage { error: String },
    
    // Bidirectional
    Ping,
    Pong,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnalyticsData {
    pub timestamp: chrono::DateTime<chrono::Utc>,
    pub detected_objects: Vec<DetectedObject>,
    pub motion_data: Option<MotionData>,
    pub betting_opportunities: Vec<BettingOpportunity>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DetectedObject {
    pub object_type: String,
    pub confidence: f64,
    pub bounding_box: BoundingBox,
    pub speed: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BoundingBox {
    pub x: f64,
    pub y: f64,
    pub width: f64,
    pub height: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MotionData {
    pub optical_flow_magnitude: f64,
    pub motion_energy: f64,
    pub dominant_direction: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BettingOpportunity {
    pub event_type: String,
    pub description: String,
    pub time_window_seconds: u64,
    pub suggested_odds: f64,
    pub confidence: f64,
}

pub struct WebSocketManager {
    broadcast_tx: broadcast::Sender<WebSocketMessage>,
}

impl WebSocketManager {
    pub fn new() -> Self {
        let (broadcast_tx, _) = broadcast::channel(1000);
        
        Self {
            broadcast_tx,
        }
    }

    pub fn broadcast(&self, message: WebSocketMessage) {
        if let Err(e) = self.broadcast_tx.send(message) {
            warn!("Failed to broadcast WebSocket message: {}", e);
        }
    }

    pub fn subscribe(&self) -> broadcast::Receiver<WebSocketMessage> {
        self.broadcast_tx.subscribe()
    }
}

pub async fn websocket_handler(
    ws: WebSocketUpgrade,
    Extension(state): Extension<AppState>,
) -> Response {
    ws.on_upgrade(|socket| handle_socket(socket, state))
}

async fn handle_socket(socket: WebSocket, state: AppState) {
    let (mut sender, mut receiver) = socket.split();
    let session_id = Uuid::new_v4().to_string();
    
    info!("New WebSocket connection: {}", session_id);

    // Create a channel for this specific connection
    let (tx, mut rx) = tokio::sync::mpsc::unbounded_channel();

    // Spawn a task to handle outgoing messages
    let send_task = tokio::spawn(async move {
        while let Some(msg) = rx.recv().await {
            if let Ok(json) = serde_json::to_string(&msg) {
                if sender.send(Message::Text(json)).await.is_err() {
                    break;
                }
            }
        }
    });

    // Handle incoming messages
    let state_clone = state.clone();
    let tx_clone = tx.clone();
    let receive_task = tokio::spawn(async move {
        while let Some(msg) = receiver.recv().await {
            if let Ok(msg) = msg {
                match msg {
                    Message::Text(text) => {
                        if let Err(e) = handle_text_message(text, &state_clone, &tx_clone).await {
                            error!("Error handling WebSocket message: {}", e);
                            let error_msg = WebSocketMessage::ErrorMessage {
                                error: "Internal server error".to_string(),
                            };
                            let _ = tx_clone.send(error_msg);
                        }
                    }
                    Message::Close(_) => {
                        info!("WebSocket connection closed: {}", session_id);
                        break;
                    }
                    _ => {}
                }
            } else {
                break;
            }
        }
    });

    // Wait for either task to complete
    tokio::select! {
        _ = send_task => {},
        _ = receive_task => {},
    }

    info!("WebSocket connection ended: {}", session_id);
}

async fn handle_text_message(
    text: String,
    state: &AppState,
    tx: &tokio::sync::mpsc::UnboundedSender<WebSocketMessage>,
) -> anyhow::Result<()> {
    let message: WebSocketMessage = serde_json::from_str(&text)?;

    match message {
        WebSocketMessage::JoinStream { stream_id, user_id } => {
            // Get current stream status and send to client
            if let Ok(Some(status)) = state.stream_manager.get_stream_status(&stream_id).await {
                let response = WebSocketMessage::StreamUpdate {
                    stream_id: stream_id.clone(),
                    status,
                };
                tx.send(response)?;
            }
        }

        WebSocketMessage::PlaceBet { bet_request } => {
            match state.betting_engine.place_bet(bet_request.clone()).await {
                Ok(result) => {
                    let response = WebSocketMessage::BetUpdate {
                        bet_id: result.bet_id.clone(),
                        result,
                    };
                    tx.send(response)?;

                    // Send balance update
                    let balance_update = WebSocketMessage::BalanceUpdate {
                        user_id: bet_request.user_id.clone(),
                        stream_id: bet_request.stream_id.clone(),
                        balance: 0.0, // Would get actual balance from state
                    };
                    tx.send(balance_update)?;
                }
                Err(e) => {
                    let error_msg = WebSocketMessage::ErrorMessage {
                        error: format!("Failed to place bet: {}", e),
                    };
                    tx.send(error_msg)?;
                }
            }
        }

        WebSocketMessage::PledgeToStream { stream_id, amount } => {
            // Handle stream pledge
            // This would integrate with payment processing
            info!("Received pledge of ${:.2} for stream {}", amount, stream_id);
            
            // For now, just acknowledge
            let response = WebSocketMessage::StreamUpdate {
                stream_id: stream_id.clone(),
                status: crate::stream::StreamStatus {
                    stream_id,
                    state: crate::stream::StreamState::Pledging,
                    current_pledges: amount,
                    activation_threshold: 100.0,
                    pledger_count: 1,
                    active_viewers: 0,
                    time_until_timeout: Some(300),
                    activation_percentage: amount / 100.0 * 100.0,
                    recent_activity: vec![],
                },
            };
            tx.send(response)?;
        }

        WebSocketMessage::Ping => {
            tx.send(WebSocketMessage::Pong)?;
        }

        _ => {
            // Handle other message types
        }
    }

    Ok(())
}

// Helper function to broadcast analytics updates
pub async fn broadcast_analytics_update(
    stream_id: String,
    analytics_data: AnalyticsData,
    ws_manager: &WebSocketManager,
) {
    let message = WebSocketMessage::AnalyticsUpdate {
        stream_id,
        data: analytics_data,
    };
    ws_manager.broadcast(message);
}

// Helper function to broadcast stream updates
pub async fn broadcast_stream_update(
    stream_id: String,
    status: crate::stream::StreamStatus,
    ws_manager: &WebSocketManager,
) {
    let message = WebSocketMessage::StreamUpdate {
        stream_id,
        status,
    };
    ws_manager.broadcast(message);
} 