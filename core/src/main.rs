mod stream;
mod state;
mod betting;
mod websocket;
mod config;
mod orchestrator;
mod geolocation;
mod reasoning;

use axum::{
    routing::{get, post, patch},
    Router,
    extract::Extension,
    http::StatusCode,
    response::Json as AxumJson,
};
use std::sync::Arc;
use tokio::net::TcpListener;
use tower_http::cors::CorsLayer;
use tracing::{info, warn};
use anyhow::Result;
use serde::{Deserialize, Serialize};

use crate::{
    config::Config,
    state::StateManager,
    stream::StreamManager,
    betting::BettingEngine,
    websocket::websocket_handler,
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
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize tracing
    tracing_subscriber::fmt::init();
    
    info!("Starting Morphine Core Service");

    // Load configuration
    let config = Config::from_env()?;
    info!("Loaded configuration from environment");

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
    let geolocation_service = Arc::new(GeolocationService::new().await);
    
    println!("🔀 Starting Hybrid Reasoning Engine...");
    let reasoning_engine = Arc::new(HybridReasoningEngine::new().await);

    // Create shared application state
    let app_state = AppState {
        state_manager,
        stream_manager,
        betting_engine,
        metacognitive_orchestrator,
        geolocation_service,
        reasoning_engine,
    };

    // Register AI systems with the orchestrator
    register_ai_systems(&app_state).await?;

    // Build application routes
    let app = Router::new()
        .route("/health", get(health_check))
        .route("/system/health", get(system_health))
        .route("/streams", get(list_streams))
        .route("/streams/:stream_id/status", get(get_stream_status))
        .route("/streams/:stream_id/activate", post(activate_stream))
        .route("/bets", post(place_bet))
        
        // Metacognitive orchestration endpoints
        .route("/orchestrator/streaming-decision", post(process_streaming_decision))
        .route("/orchestrator/streaming-decisions/:stream_id", get(get_streaming_decisions))
        .route("/orchestrator/ai-systems", post(register_ai_system))
        
        // Geolocation verification endpoints
        .route("/geolocation/session/start/:user_id", post(start_location_session))
        .route("/geolocation/update", post(update_location))
        .route("/geolocation/exclusion-zones", post(add_exclusion_zone))
        .route("/geolocation/verify-transaction", post(verify_transaction_location))
        .route("/geolocation/user/:user_id/history", get(get_location_history))
        .route("/geolocation/user/:user_id/excluded", get(check_user_exclusion))
        
        // Hybrid reasoning endpoints
        .route("/reasoning/evaluate-bet", post(evaluate_bet_outcome))
        .route("/reasoning/distribute-prize/:pool_id", post(distribute_prize_pool))
        .route("/reasoning/bet-trace/:bet_id", get(get_bet_reasoning_trace))
        .route("/reasoning/paradigm-weights", patch(update_paradigm_weights))
        
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

async fn health_check() -> &'static str {
    "Metacognitive orchestration system operational"
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

async fn list_streams(
    Extension(state): Extension<AppState>,
) -> Result<AxumJson<Vec<stream::StreamInfo>>, StatusCode> {
    match state.stream_manager.list_streams().await {
        Ok(streams) => Ok(AxumJson(streams)),
        Err(_) => Err(StatusCode::INTERNAL_SERVER_ERROR),
    }
}

async fn get_stream_status(
    axum::extract::Path(stream_id): axum::extract::Path<String>,
    Extension(state): Extension<AppState>,
) -> Result<AxumJson<stream::StreamStatus>, StatusCode> {
    match state.stream_manager.get_stream_status(&stream_id).await {
        Ok(Some(status)) => Ok(AxumJson(status)),
        Ok(None) => Err(StatusCode::NOT_FOUND),
        Err(_) => Err(StatusCode::INTERNAL_SERVER_ERROR),
    }
}

async fn activate_stream(
    axum::extract::Path(stream_id): axum::extract::Path<String>,
    Extension(state): Extension<AppState>,
) -> Result<AxumJson<stream::ActivationResult>, StatusCode> {
    match state.stream_manager.try_activate_stream(&stream_id).await {
        Ok(result) => Ok(AxumJson(result)),
        Err(_) => Err(StatusCode::INTERNAL_SERVER_ERROR),
    }
}

async fn place_bet(
    Extension(state): Extension<AppState>,
    axum::Json(bet_request): axum::Json<betting::BetRequest>,
) -> Result<AxumJson<betting::BetResult>, StatusCode> {
    match state.betting_engine.place_bet(bet_request).await {
        Ok(result) => Ok(AxumJson(result)),
        Err(_) => Err(StatusCode::BAD_REQUEST),
    }
}

async fn process_streaming_decision(
    Extension(state): Extension<AppState>,
    axum::Json(request): axum::Json<StreamingDecisionRequest>,
) -> Result<AxumJson<orchestrator::MetacognitiveDecision>, StatusCode> {
    // Create streaming context
    let context = orchestrator::StreamingContext {
        stream_id: request.stream_id.clone(),
        timestamp: chrono::Utc::now().timestamp() as f64,
        partial_data: request.context,
        confidence_level: 0.8, // Would calculate based on data quality
        processing_stage: orchestrator::ProcessingStage::Context,
    };
    
    // Update location if provided
    if let Some(location_data) = request.location_data {
        if let Ok(session_id) = state.geolocation_service.start_location_session(
            "user_placeholder".to_string()
        ).await {
            let _ = state.geolocation_service.update_location_multi_source(
                &session_id,
                location_data.gps_data,
                location_data.cell_towers,
                location_data.wifi_points,
                request.video_frame_hash
            ).await;
        }
    }
    
    // Create stream and get decision
    let (input_tx, mut output_rx) = state.metacognitive_orchestrator.create_stream(request.stream_id).await;
    
    // Send context
    if let Err(_) = input_tx.send(context).await {
        return Err(StatusCode::INTERNAL_SERVER_ERROR);
    }
    
    // Get decision (with timeout)
    match tokio::time::timeout(
        std::time::Duration::from_secs(5),
        output_rx.recv()
    ).await {
        Ok(Some(decision)) => Ok(AxumJson(decision)),
        _ => Err(StatusCode::REQUEST_TIMEOUT),
    }
}

async fn get_streaming_decisions(
    axum::extract::Path(stream_id): axum::extract::Path<String>,
    Extension(state): Extension<AppState>,
) -> Result<AxumJson<Vec<orchestrator::MetacognitiveDecision>>, StatusCode> {
    let decisions = state.metacognitive_orchestrator.get_streaming_decisions(&stream_id).await;
    Ok(AxumJson(decisions))
}

async fn register_ai_system(
    Extension(_state): Extension<AppState>,
    axum::Json(_request): axum::Json<serde_json::Value>,
) -> Result<AxumJson<serde_json::Value>, StatusCode> {
    // Would register actual AI system
    Ok(AxumJson(serde_json::json!({"status": "registered"})))
}

async fn start_location_session(
    axum::extract::Path(user_id): axum::extract::Path<String>,
    Extension(state): Extension<AppState>,
) -> Result<AxumJson<serde_json::Value>, StatusCode> {
    match state.geolocation_service.start_location_session(user_id).await {
        session_id => Ok(AxumJson(serde_json::json!({"session_id": session_id}))),
    }
}

async fn update_location(
    Extension(state): Extension<AppState>,
    axum::Json(request): axum::Json<serde_json::Value>,
) -> Result<AxumJson<geolocation::LocationVerification>, StatusCode> {
    // Parse location update request and process
    // This is a simplified version
    let session_id = request.get("session_id")
        .and_then(|v| v.as_str())
        .unwrap_or("default");
    
    match state.geolocation_service.update_location_multi_source(
        session_id,
        None, // Would parse GPS data
        Vec::new(), // Would parse cell tower data
        Vec::new(), // Would parse WiFi data
        None // Would parse video frame hash
    ).await {
        Ok(verification) => Ok(AxumJson(verification)),
        Err(_) => Err(StatusCode::INTERNAL_SERVER_ERROR),
    }
}

async fn add_exclusion_zone(
    Extension(state): Extension<AppState>,
    axum::Json(request): axum::Json<ExclusionZoneRequest>,
) -> Result<AxumJson<serde_json::Value>, StatusCode> {
    state.geolocation_service.add_exclusion_zone(request.zone).await;
    Ok(AxumJson(serde_json::json!({"status": "added"})))
}

async fn verify_transaction_location(
    Extension(_state): Extension<AppState>,
    axum::Json(_request): axum::Json<serde_json::Value>,
) -> Result<AxumJson<serde_json::Value>, StatusCode> {
    // Would verify transaction location
    Ok(AxumJson(serde_json::json!({"verified": true})))
}

async fn get_location_history(
    axum::extract::Path(user_id): axum::extract::Path<String>,
    Extension(state): Extension<AppState>,
) -> Result<AxumJson<Vec<geolocation::LocationVerification>>, StatusCode> {
    let history = state.geolocation_service.get_location_history(&user_id).await;
    Ok(AxumJson(history))
}

async fn check_user_exclusion(
    axum::extract::Path(user_id): axum::extract::Path<String>,
    Extension(state): Extension<AppState>,
) -> Result<AxumJson<serde_json::Value>, StatusCode> {
    let is_excluded = state.geolocation_service.is_user_excluded(&user_id).await;
    Ok(AxumJson(serde_json::json!({"excluded": is_excluded})))
}

async fn evaluate_bet_outcome(
    Extension(state): Extension<AppState>,
    axum::Json(request): axum::Json<BetEvaluationRequest>,
) -> Result<AxumJson<reasoning::BetOutcome>, StatusCode> {
    match state.reasoning_engine.evaluate_bet_outcome(
        &request.bet_id,
        &request.event_data,
        &request.context
    ).await {
        Ok(outcome) => Ok(AxumJson(outcome)),
        Err(_) => Err(StatusCode::INTERNAL_SERVER_ERROR),
    }
}

async fn distribute_prize_pool(
    axum::extract::Path(pool_id): axum::extract::Path<String>,
    Extension(state): Extension<AppState>,
) -> Result<AxumJson<std::collections::HashMap<String, f64>>, StatusCode> {
    match state.reasoning_engine.distribute_prize_pool(&pool_id).await {
        Ok(distribution) => Ok(AxumJson(distribution)),
        Err(_) => Err(StatusCode::INTERNAL_SERVER_ERROR),
    }
}

async fn get_bet_reasoning_trace(
    axum::extract::Path(bet_id): axum::extract::Path<String>,
    Extension(state): Extension<AppState>,
) -> Result<AxumJson<Vec<reasoning::ReasoningStep>>, StatusCode> {
    match state.reasoning_engine.get_reasoning_trace(&bet_id).await {
        Some(trace) => Ok(AxumJson(trace)),
        None => Err(StatusCode::NOT_FOUND),
    }
}

async fn update_paradigm_weights(
    Extension(state): Extension<AppState>,
    axum::Json(weights): axum::Json<std::collections::HashMap<String, f64>>,
) -> Result<AxumJson<serde_json::Value>, StatusCode> {
    state.reasoning_engine.update_paradigm_weights(weights).await;
    Ok(AxumJson(serde_json::json!({"status": "updated"})))
} 