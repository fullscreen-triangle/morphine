mod stream;
mod state;
mod betting;
mod websocket;
mod config;

use axum::{
    routing::{get, post},
    Router,
    extract::Extension,
};
use std::sync::Arc;
use tokio::net::TcpListener;
use tower_http::cors::CorsLayer;
use tracing::{info, warn};
use anyhow::Result;

use crate::{
    config::Config,
    state::StateManager,
    stream::StreamManager,
    betting::BettingEngine,
    websocket::websocket_handler,
};

#[derive(Clone)]
pub struct AppState {
    pub state_manager: Arc<StateManager>,
    pub stream_manager: Arc<StreamManager>,
    pub betting_engine: Arc<BettingEngine>,
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

    // Create shared application state
    let app_state = AppState {
        state_manager,
        stream_manager,
        betting_engine,
    };

    // Build application routes
    let app = Router::new()
        .route("/health", get(health_check))
        .route("/streams", get(list_streams))
        .route("/streams/:id/status", get(get_stream_status))
        .route("/streams/:id/activate", post(activate_stream))
        .route("/betting/place", post(place_bet))
        .route("/ws", get(websocket_handler))
        .layer(CorsLayer::permissive())
        .layer(Extension(app_state));

    // Start server
    let listener = TcpListener::bind(&config.bind_address).await?;
    info!("Server listening on {}", config.bind_address);

    axum::serve(listener, app).await?;

    Ok(())
}

async fn health_check() -> &'static str {
    "OK"
}

async fn list_streams(
    Extension(state): Extension<AppState>,
) -> Result<axum::Json<Vec<stream::StreamInfo>>, axum::http::StatusCode> {
    match state.stream_manager.list_streams().await {
        Ok(streams) => Ok(axum::Json(streams)),
        Err(_) => Err(axum::http::StatusCode::INTERNAL_SERVER_ERROR),
    }
}

async fn get_stream_status(
    axum::extract::Path(stream_id): axum::extract::Path<String>,
    Extension(state): Extension<AppState>,
) -> Result<axum::Json<stream::StreamStatus>, axum::http::StatusCode> {
    match state.stream_manager.get_stream_status(&stream_id).await {
        Ok(Some(status)) => Ok(axum::Json(status)),
        Ok(None) => Err(axum::http::StatusCode::NOT_FOUND),
        Err(_) => Err(axum::http::StatusCode::INTERNAL_SERVER_ERROR),
    }
}

async fn activate_stream(
    axum::extract::Path(stream_id): axum::extract::Path<String>,
    Extension(state): Extension<AppState>,
) -> Result<axum::Json<stream::ActivationResult>, axum::http::StatusCode> {
    match state.stream_manager.try_activate_stream(&stream_id).await {
        Ok(result) => Ok(axum::Json(result)),
        Err(_) => Err(axum::http::StatusCode::INTERNAL_SERVER_ERROR),
    }
}

async fn place_bet(
    Extension(state): Extension<AppState>,
    axum::Json(bet_request): axum::Json<betting::BetRequest>,
) -> Result<axum::Json<betting::BetResult>, axum::http::StatusCode> {
    match state.betting_engine.place_bet(bet_request).await {
        Ok(result) => Ok(axum::Json(result)),
        Err(_) => Err(axum::http::StatusCode::BAD_REQUEST),
    }
} 