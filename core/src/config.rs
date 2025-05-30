use anyhow::{Result, Context};
use serde::Deserialize;

#[derive(Debug, Deserialize)]
pub struct Config {
    pub bind_address: String,
    pub redis_url: String,
    pub database_url: String,
    pub analytics_service_url: String,
    pub stream_storage_path: String,
    pub max_concurrent_streams: usize,
    pub stream_activation_timeout_seconds: u64,
}

impl Config {
    pub fn from_env() -> Result<Self> {
        let config = Config {
            bind_address: std::env::var("BIND_ADDRESS")
                .unwrap_or_else(|_| "0.0.0.0:3001".to_string()),
            
            redis_url: std::env::var("REDIS_URL")
                .unwrap_or_else(|_| "redis://localhost:6379".to_string()),
            
            database_url: std::env::var("DATABASE_URL")
                .context("DATABASE_URL must be set")?,
            
            analytics_service_url: std::env::var("ANALYTICS_SERVICE_URL")
                .unwrap_or_else(|_| "http://localhost:8000".to_string()),
            
            stream_storage_path: std::env::var("STREAM_STORAGE_PATH")
                .unwrap_or_else(|_| "./storage/streams".to_string()),
            
            max_concurrent_streams: std::env::var("MAX_CONCURRENT_STREAMS")
                .unwrap_or_else(|_| "10".to_string())
                .parse()
                .context("MAX_CONCURRENT_STREAMS must be a valid number")?,
            
            stream_activation_timeout_seconds: std::env::var("STREAM_ACTIVATION_TIMEOUT")
                .unwrap_or_else(|_| "300".to_string())
                .parse()
                .context("STREAM_ACTIVATION_TIMEOUT must be a valid number")?,
        };

        Ok(config)
    }
} 