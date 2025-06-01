pub mod manager;
pub mod types;

pub use manager::StreamManager;
pub use types::*;

use std::sync::Arc;
use std::collections::HashMap;
use tokio::sync::RwLock;
use serde::{Deserialize, Serialize};
use uuid::Uuid;
use anyhow::{Result, anyhow};

use crate::state::StateManager;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StreamInfo {
    pub id: String,
    pub title: String,
    pub status: StreamStatus,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub settings: StreamSettings,
    pub analytics_enabled: bool,
    pub viewer_count: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StreamSettings {
    pub quality: String,
    pub frame_rate: u32,
    pub enable_cv: bool,
    pub enable_betting: bool,
    pub max_viewers: Option<u32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum StreamStatus {
    Inactive,
    Activating,
    Active,
    Error(String),
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ActivationResult {
    pub success: bool,
    pub stream_id: String,
    pub status: StreamStatus,
    pub message: String,
}

pub struct StreamManager {
    state_manager: Arc<StateManager>,
    streams: Arc<RwLock<HashMap<String, StreamInfo>>>,
    activation_queue: Arc<RwLock<Vec<String>>>,
}

impl StreamManager {
    pub async fn new(state_manager: Arc<StateManager>) -> Result<Self> {
        let streams = Arc::new(RwLock::new(HashMap::new()));
        let activation_queue = Arc::new(RwLock::new(Vec::new()));
        
        let manager = Self {
            state_manager,
            streams,
            activation_queue,
        };
        
        // Load existing streams from state
        manager.load_streams().await?;
        
        Ok(manager)
    }
    
    async fn load_streams(&self) -> Result<()> {
        // Load stream data from Redis/state storage
        let stream_keys = self.state_manager.get_stream_keys().await?;
        let mut streams = self.streams.write().await;
        
        for key in stream_keys {
            if let Ok(Some(stream_data)) = self.state_manager.get_stream(&key).await {
                if let Ok(stream_info) = serde_json::from_str::<StreamInfo>(&stream_data) {
                    streams.insert(stream_info.id.clone(), stream_info);
                }
            }
        }
        
        tracing::info!("Loaded {} streams from state", streams.len());
        Ok(())
    }
    
    pub async fn list_streams(&self) -> Result<Vec<StreamInfo>> {
        let streams = self.streams.read().await;
        Ok(streams.values().cloned().collect())
    }
    
    pub async fn get_stream(&self, stream_id: &str) -> Result<Option<StreamInfo>> {
        let streams = self.streams.read().await;
        Ok(streams.get(stream_id).cloned())
    }
    
    pub async fn create_stream(&self, title: String, settings: StreamSettings) -> Result<StreamInfo> {
        let stream_id = Uuid::new_v4().to_string();
        let stream_info = StreamInfo {
            id: stream_id.clone(),
            title,
            status: StreamStatus::Inactive,
            created_at: chrono::Utc::now(),
            settings,
            analytics_enabled: true,
            viewer_count: 0,
        };
        
        // Store in state
        let stream_data = serde_json::to_string(&stream_info)?;
        self.state_manager.set_stream(&stream_id, &stream_data).await?;
        
        // Add to local cache
        let mut streams = self.streams.write().await;
        streams.insert(stream_id.clone(), stream_info.clone());
        
        tracing::info!("Created new stream: {}", stream_id);
        Ok(stream_info)
    }
    
    pub async fn try_activate_stream(&self, stream_id: &str) -> Result<ActivationResult> {
        let mut streams = self.streams.write().await;
        
        let stream = streams.get_mut(stream_id)
            .ok_or_else(|| anyhow!("Stream not found: {}", stream_id))?;
        
        match &stream.status {
            StreamStatus::Active => {
                return Ok(ActivationResult {
                    success: true,
                    stream_id: stream_id.to_string(),
                    status: StreamStatus::Active,
                    message: "Stream is already active".to_string(),
                });
            }
            StreamStatus::Activating => {
                return Ok(ActivationResult {
                    success: false,
                    stream_id: stream_id.to_string(),
                    status: StreamStatus::Activating,
                    message: "Stream is already being activated".to_string(),
                });
            }
            _ => {}
        }
        
        // Check if we can activate more streams
        let active_count = streams.values()
            .filter(|s| matches!(s.status, StreamStatus::Active | StreamStatus::Activating))
            .count();
            
        let max_concurrent = std::env::var("MAX_CONCURRENT_STREAMS")
            .unwrap_or_else(|_| "10".to_string())
            .parse::<usize>()
            .unwrap_or(10);
            
        if active_count >= max_concurrent {
            return Ok(ActivationResult {
                success: false,
                stream_id: stream_id.to_string(),
                status: stream.status.clone(),
                message: format!("Maximum concurrent streams reached: {}", max_concurrent),
            });
        }
        
        // Set to activating state
        stream.status = StreamStatus::Activating;
        
        // Update state
        let stream_data = serde_json::to_string(&stream)?;
        self.state_manager.set_stream(stream_id, &stream_data).await?;
        
        // Add to activation queue
        let mut queue = self.activation_queue.write().await;
        queue.push(stream_id.to_string());
        
        // Spawn activation task
        let state_manager = self.state_manager.clone();
        let streams_ref = self.streams.clone();
        let stream_id_owned = stream_id.to_string();
        
        tokio::spawn(async move {
            if let Err(e) = Self::activate_stream_async(
                state_manager,
                streams_ref,
                stream_id_owned
            ).await {
                tracing::error!("Failed to activate stream: {}", e);
            }
        });
        
        Ok(ActivationResult {
            success: true,
            stream_id: stream_id.to_string(),
            status: StreamStatus::Activating,
            message: "Stream activation started".to_string(),
        })
    }
    
    async fn activate_stream_async(
        state_manager: Arc<StateManager>,
        streams: Arc<RwLock<HashMap<String, StreamInfo>>>,
        stream_id: String,
    ) -> Result<()> {
        // Simulate stream activation process
        tokio::time::sleep(tokio::time::Duration::from_secs(2)).await;
        
        // Update stream status to active
        {
            let mut streams_guard = streams.write().await;
            if let Some(stream) = streams_guard.get_mut(&stream_id) {
                stream.status = StreamStatus::Active;
                
                // Update state
                let stream_data = serde_json::to_string(&stream)?;
                state_manager.set_stream(&stream_id, &stream_data).await?;
            }
        }
        
        tracing::info!("Stream activated successfully: {}", stream_id);
        Ok(())
    }
    
    pub async fn deactivate_stream(&self, stream_id: &str) -> Result<()> {
        let mut streams = self.streams.write().await;
        
        if let Some(stream) = streams.get_mut(stream_id) {
            stream.status = StreamStatus::Inactive;
            stream.viewer_count = 0;
            
            // Update state
            let stream_data = serde_json::to_string(&stream)?;
            self.state_manager.set_stream(stream_id, &stream_data).await?;
            
            tracing::info!("Stream deactivated: {}", stream_id);
        }
        
        Ok(())
    }
    
    pub async fn get_stream_status(&self, stream_id: &str) -> Result<Option<StreamStatus>> {
        let streams = self.streams.read().await;
        Ok(streams.get(stream_id).map(|s| s.status.clone()))
    }
    
    pub async fn update_viewer_count(&self, stream_id: &str, count: u32) -> Result<()> {
        let mut streams = self.streams.write().await;
        
        if let Some(stream) = streams.get_mut(stream_id) {
            stream.viewer_count = count;
            
            // Update state
            let stream_data = serde_json::to_string(&stream)?;
            self.state_manager.set_stream(stream_id, &stream_data).await?;
        }
        
        Ok(())
    }
    
    pub async fn delete_stream(&self, stream_id: &str) -> Result<()> {
        // First deactivate if active
        self.deactivate_stream(stream_id).await?;
        
        // Remove from local cache
        let mut streams = self.streams.write().await;
        streams.remove(stream_id);
        
        // Remove from state
        self.state_manager.delete_stream(stream_id).await?;
        
        tracing::info!("Stream deleted: {}", stream_id);
        Ok(())
    }
    
    pub async fn get_active_streams(&self) -> Result<Vec<StreamInfo>> {
        let streams = self.streams.read().await;
        Ok(streams.values()
            .filter(|s| matches!(s.status, StreamStatus::Active))
            .cloned()
            .collect())
    }
    
    pub async fn health_check(&self) -> Result<HashMap<String, serde_json::Value>> {
        let streams = self.streams.read().await;
        let total_streams = streams.len();
        let active_streams = streams.values()
            .filter(|s| matches!(s.status, StreamStatus::Active))
            .count();
        let activating_streams = streams.values()
            .filter(|s| matches!(s.status, StreamStatus::Activating))
            .count();
            
        let mut health = HashMap::new();
        health.insert("total_streams".to_string(), serde_json::Value::from(total_streams));
        health.insert("active_streams".to_string(), serde_json::Value::from(active_streams));
        health.insert("activating_streams".to_string(), serde_json::Value::from(activating_streams));
        health.insert("health_status".to_string(), serde_json::Value::from("healthy"));
        
        Ok(health)
    }
} 