mod stream;
mod state;
mod betting;
mod websocket;
mod config;
mod orchestrator;
mod geolocation;
mod reasoning;

use axum::{
    routing::{get, post, patch, delete},
    Router,
    extract::{Extension, Path, Query, State},
    http::StatusCode,
    response::Json as AxumJson,
};
use std::sync::Arc;
use tokio::net::TcpListener;
use tower_http::cors::CorsLayer;
use tracing::{info, warn, error};
use anyhow::Result;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sqlx::{Pool, Postgres};

use crate::{
    config::Config,
    state::StateManager,
    stream::StreamManager,
    betting::BettingEngine,
    websocket::WebSocketManager,
    orchestrator::MetacognitiveOrchestrator,
    geolocation::GeolocationService,
    reasoning::HybridReasoningEngine,
};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SystemHealth {
    pub core_status: String,
    pub orchestrator_health: serde_json::Value,
    pub geolocation_active: bool,
    pub reasoning_engine_status: String,
    pub active_streams: usize,
    pub total_ai_systems: usize,
    pub metabolic_state: serde_json::Value,
    pub exclusion_zones_count: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StreamingDecisionRequest {
    pub stream_id: String,
    pub data: serde_json::Value,
    pub context: std::collections::HashMap<String, serde_json::Value>,
    pub location_data: Option<LocationUpdateRequest>,
    pub video_frame_hash: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LocationUpdateRequest {
    pub gps_data: Option<geolocation::GeolocationPoint>,
    pub cell_towers: Vec<geolocation::CellTowerData>,
    pub wifi_points: Vec<geolocation::WiFiAccessPoint>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BetEvaluationRequest {
    pub bet_id: String,
    pub event_data: serde_json::Value,
    pub context: std::collections::HashMap<String, serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExclusionZoneRequest {
    pub zone: geolocation::ExclusionZone,
}

#[derive(Clone)]
pub struct AppState {
    pub state_manager: Arc<StateManager>,
    pub stream_manager: Arc<StreamManager>,
    pub betting_engine: Arc<BettingEngine>,
    pub metacognitive_orchestrator: Arc<MetacognitiveOrchestrator>,
    pub geolocation_service: Arc<GeolocationService>,
    pub reasoning_engine: Arc<HybridReasoningEngine>,
    pub websocket_manager: Arc<WebSocketManager>,
    pub db_pool: Pool<Postgres>,
}

#[derive(Deserialize)]
struct CreateStreamRequest {
    title: String,
    source_type: String,
    source_url: String,
    settings: Option<Value>,
}

#[derive(Serialize)]
struct StreamResponse {
    success: bool,
    data: Option<Value>,
    error: Option<String>,
}

#[derive(Deserialize)]
struct PlaceBetRequest {
    user_id: String,
    stream_id: String,
    bet_type: String,
    stake_amount: f64,
    prediction: Value,
    time_window_seconds: u32,
}

#[derive(Serialize)]
struct BetResponse {
    success: bool,
    bet_id: Option<String>,
    message: String,
    remaining_balance: Option<f64>,
    bet_details: Option<Value>,
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_max_level(tracing::Level::INFO)
        .init();
    
    info!("Starting Morphine Core Service");

    // Load configuration
    let config = Config::from_env()?;
    info!("Loaded configuration from environment");

    // Initialize database connection
    let db_pool = sqlx::postgres::PgPool::connect(&config.database_url).await?;
    sqlx::migrate!("./migrations").run(&db_pool).await?;

    // Initialize state manager (Redis connection)
    let state_manager = Arc::new(StateManager::new(&config.redis_url).await?);
    info!("Connected to Redis state store");

    // Initialize stream manager
    let stream_manager = Arc::new(StreamManager::new(state_manager.clone()).await?);
    info!("Stream manager initialized");

    // Initialize betting engine
    let betting_engine = Arc::new(BettingEngine::new(
        state_manager.clone(),
        &config.database_url
    ).await?);
    info!("Betting engine initialized");

    // Initialize advanced components
    println!("🧠 Starting Metacognitive Orchestrator...");
    let metacognitive_orchestrator = Arc::new(MetacognitiveOrchestrator::new().await);
    
    println!("🌍 Initializing Geolocation Verification System...");
    let geolocation_service = Arc::new(GeolocationService::new(config.precision_timing_enabled));
    
    println!("🔀 Starting Hybrid Reasoning Engine...");
    let reasoning_engine = Arc::new(HybridReasoningEngine::new(config.reasoning_config.clone()).await?);

    // Initialize websocket manager
    let websocket_manager = Arc::new(WebSocketManager::new());

    // Create shared application state
    let app_state = AppState {
        state_manager,
        stream_manager,
        betting_engine,
        metacognitive_orchestrator,
        geolocation_service,
        reasoning_engine,
        websocket_manager,
        db_pool,
    };

    // Register AI systems with the orchestrator
    register_ai_systems(&app_state).await?;

    // Build application routes
    let app = Router::new()
        // Health check
        .route("/health", get(health_check))
        
        // Stream management
        .route("/api/streams", get(list_streams))
        .route("/api/streams", post(create_stream))
        .route("/api/streams/:id", get(get_stream))
        .route("/api/streams/:id/start", post(start_stream))
        .route("/api/streams/:id/stop", post(stop_stream))
        .route("/api/streams/:id/status", get(stream_status))
        
        // Betting endpoints
        .route("/api/betting/place", post(place_bet))
        .route("/api/betting/balance/:stream_id", get(get_balance))
        .route("/api/betting/stream/:stream_id/activity", get(get_betting_activity))
        .route("/api/betting/types", get(get_bet_types))
        .route("/api/betting/resolve/:bet_id", post(resolve_bet))
        
        // Analytics integration
        .route("/api/analytics/:stream_id/notify", post(analytics_update))
        .route("/api/analytics/:stream_id/history", get(get_analytics_history))
        
        // Geolocation verification
        .route("/api/geolocation/verify", post(verify_location))
        .route("/api/geolocation/session/start/:user_id", post(start_location_session))
        
        // WebSocket for real-time updates
        .route("/ws/:stream_id", get(websocket_handler))
        
        .layer(CorsLayer::permissive())
        .layer(Extension(app_state));

    // Start server
    let listener = TcpListener::bind(&config.bind_address).await?;
    info!("Server listening on {}", config.bind_address);

    axum::serve(listener, app).await?;

    Ok(())
}

async fn register_ai_systems(app_state: &AppState) -> Result<()> {
    // This would register actual AI systems with the orchestrator
    // For now, we'll register placeholder systems
    
    println!("🤖 Registering AI Systems with Metacognitive Orchestrator...");
    
    // Example registrations would go here
    // app_state.metacognitive_orchestrator.register_ai_system(...).await?;
    
    Ok(())
}

async fn health_check() -> Json<Value> {
    Json(json!({
        "status": "healthy",
        "service": "morphine-core",
        "version": "1.0.0",
        "timestamp": chrono::Utc::now().timestamp()
    }))
}

async fn system_health(
    Extension(state): Extension<AppState>,
) -> Result<AxumJson<SystemHealth>, StatusCode> {
    let orchestrator_health = state.metacognitive_orchestrator.get_system_health().await;
    
    // Check if reasoning engine is functional
    let reasoning_status = "operational"; // Would check actual status
    
    let health = SystemHealth {
        core_status: "operational".to_string(),
        orchestrator_health: serde_json::to_value(orchestrator_health).unwrap_or_default(),
        geolocation_active: true,
        reasoning_engine_status: reasoning_status.to_string(),
        active_streams: 0, // Would get actual count
        total_ai_systems: 0, // Would get actual count
        metabolic_state: serde_json::json!({}), // Would get actual metabolic state
        exclusion_zones_count: 0, // Would get actual count
    };
    
    Ok(AxumJson(health))
}

async fn list_streams(State(state): State<AppState>) -> Result<Json<StreamResponse>, StatusCode> {
    match state.stream_manager.list_streams().await {
        Ok(streams) => Ok(Json(StreamResponse {
            success: true,
            data: Some(json!(streams)),
            error: None,
        })),
        Err(e) => {
            error!("Failed to list streams: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

async fn get_stream(
    State(state): State<AppState>,
    Path(stream_id): Path<String>,
) -> Result<Json<StreamResponse>, StatusCode> {
    match state.stream_manager.get_stream(&stream_id).await {
        Ok(Some(stream)) => Ok(Json(StreamResponse {
            success: true,
            data: Some(json!(stream)),
            error: None,
        })),
        Ok(None) => Ok(Json(StreamResponse {
            success: false,
            data: None,
            error: Some("Stream not found".to_string()),
        })),
        Err(e) => {
            error!("Failed to get stream {}: {}", stream_id, e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

async fn start_stream(
    State(state): State<AppState>,
    Path(stream_id): Path<String>,
) -> Result<Json<StreamResponse>, StatusCode> {
    match state.stream_manager.start_stream(&stream_id).await {
        Ok(_) => {
            info!("Started stream: {}", stream_id);
            Ok(Json(StreamResponse {
                success: true,
                data: Some(json!({"status": "starting"})),
                error: None,
            }))
        }
        Err(e) => {
            error!("Failed to start stream {}: {}", stream_id, e);
            Ok(Json(StreamResponse {
                success: false,
                data: None,
                error: Some(e.to_string()),
            }))
        }
    }
}

async fn stop_stream(
    State(state): State<AppState>,
    Path(stream_id): Path<String>,
) -> Result<Json<StreamResponse>, StatusCode> {
    match state.stream_manager.stop_stream(&stream_id).await {
        Ok(_) => {
            info!("Stopped stream: {}", stream_id);
            Ok(Json(StreamResponse {
                success: true,
                data: Some(json!({"status": "stopped"})),
                error: None,
            }))
        }
        Err(e) => {
            error!("Failed to stop stream {}: {}", stream_id, e);
            Ok(Json(StreamResponse {
                success: false,
                data: None,
                error: Some(e.to_string()),
            }))
        }
    }
}

async fn stream_status(
    State(state): State<AppState>,
    Path(stream_id): Path<String>,
) -> Result<Json<Value>, StatusCode> {
    match state.stream_manager.get_stream_status(&stream_id).await {
        Ok(status) => Ok(Json(json!({
            "success": true,
            "status": status,
            "timestamp": chrono::Utc::now().timestamp()
        }))),
        Err(e) => {
            error!("Failed to get stream status for {}: {}", stream_id, e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

async fn place_bet(
    State(state): State<AppState>,
    Json(request): Json<PlaceBetRequest>,
) -> Result<Json<BetResponse>, StatusCode> {
    let bet_request = betting::BetRequest {
        user_id: request.user_id,
        stream_id: request.stream_id,
        bet_type: request.bet_type.parse().unwrap_or_default(),
        stake_amount: request.stake_amount,
        prediction: request.prediction,
        time_window_seconds: request.time_window_seconds,
    };

    match state.betting_engine.place_bet(bet_request).await {
        Ok(result) => Ok(Json(BetResponse {
            success: result.success,
            bet_id: if result.success { Some(result.bet_id) } else { None },
            message: result.message,
            remaining_balance: Some(result.remaining_balance),
            bet_details: result.bet_details.map(|bet| json!(bet)),
        })),
        Err(e) => {
            error!("Failed to place bet: {}", e);
            Ok(Json(BetResponse {
                success: false,
                bet_id: None,
                message: format!("Failed to place bet: {}", e),
                remaining_balance: None,
                bet_details: None,
            }))
        }
    }
}

async fn get_balance(
    State(state): State<AppState>,
    Path(stream_id): Path<String>,
) -> Result<Json<Value>, StatusCode> {
    // For demo purposes, using a fixed user ID
    let user_id = "demo-user";
    
    match state.betting_engine.get_user_balance(user_id, &stream_id).await {
        Ok(balance) => Ok(Json(json!({
            "success": true,
            "data": {
                "available": balance.available_balance(),
                "total_deposited": balance.total_deposited,
                "active_bets": balance.active_bets_total,
                "total_winnings": balance.total_winnings,
                "bet_count": balance.bet_count
            }
        }))),
        Err(e) => {
            error!("Failed to get balance: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

async fn get_betting_activity(
    State(state): State<AppState>,
    Path(stream_id): Path<String>,
) -> Result<Json<Value>, StatusCode> {
    match state.betting_engine.get_stream_activity(&stream_id).await {
        Ok(activity) => Ok(Json(json!({
            "success": true,
            "data": activity
        }))),
        Err(e) => {
            error!("Failed to get betting activity: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

async fn get_bet_types() -> Json<Value> {
    Json(json!({
        "success": true,
        "data": [
            {
                "id": "speed_milestone",
                "name": "Speed Milestone",
                "description": "Bet on reaching a specific speed"
            },
            {
                "id": "pose_event",
                "name": "Pose Event", 
                "description": "Bet on specific pose or joint angles"
            },
            {
                "id": "detection_count",
                "name": "Object Count",
                "description": "Bet on number of detected objects"
            },
            {
                "id": "motion_threshold",
                "name": "Motion Level",
                "description": "Bet on motion energy levels"
            }
        ]
    }))
}

async fn resolve_bet(
    State(state): State<AppState>,
    Path(bet_id): Path<String>,
    Json(resolution): Json<Value>,
) -> Result<Json<Value>, StatusCode> {
    match state.betting_engine.resolve_bet(&bet_id, resolution).await {
        Ok(resolved) => Ok(Json(json!({
            "success": true,
            "resolved": resolved
        }))),
        Err(e) => {
            error!("Failed to resolve bet {}: {}", bet_id, e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

async fn analytics_update(
    State(state): State<AppState>,
    Path(stream_id): Path<String>,
    Json(analytics): Json<Value>,
) -> Result<Json<Value>, StatusCode> {
    // Process analytics through the orchestrator
    match state.metacognitive_orchestrator.process_analytics(&stream_id, analytics).await {
        Ok(_) => Ok(Json(json!({"success": true}))),
        Err(e) => {
            error!("Failed to process analytics for stream {}: {}", stream_id, e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

async fn get_analytics_history(
    State(state): State<AppState>,
    Path(stream_id): Path<String>,
    Query(params): Query<HashMap<String, String>>,
) -> Result<Json<Value>, StatusCode> {
    let range = params.get("range").unwrap_or(&"5min".to_string()).clone();
    
    match state.state_manager.get_analytics_history(&stream_id, &range).await {
        Ok(history) => Ok(Json(json!({
            "success": true,
            "data": history
        }))),
        Err(e) => {
            error!("Failed to get analytics history: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

async fn verify_location(
    State(state): State<AppState>,
    Json(request): Json<Value>,
) -> Result<Json<Value>, StatusCode> {
    match state.geolocation_service.verify_location(request).await {
        Ok(verification) => Ok(Json(json!({
            "success": true,
            "verification": verification
        }))),
        Err(e) => {
            error!("Failed to verify location: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

async fn start_location_session(
    State(state): State<AppState>,
    Path(user_id): Path<String>,
) -> Result<Json<Value>, StatusCode> {
    match state.geolocation_service.start_session(&user_id).await {
        Ok(session_id) => Ok(Json(json!({
            "success": true,
            "session_id": session_id
        }))),
        Err(e) => {
            error!("Failed to start location session: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

async fn websocket_handler(
    State(state): State<AppState>,
    Path(stream_id): Path<String>,
    ws: axum::extract::WebSocketUpgrade,
) -> axum::response::Response {
    ws.on_upgrade(move |socket| {
        state.websocket_manager.handle_connection(stream_id, socket)
    })
} 