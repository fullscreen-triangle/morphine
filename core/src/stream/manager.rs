use super::types::*;
use crate::state::StateManager;
use anyhow::{Result, Context};
use dashmap::DashMap;
use std::sync::Arc;
use tokio::time::{Duration, sleep};
use tracing::{info, warn, error};
use uuid::Uuid;
use chrono::Utc;

pub struct StreamManager {
    state_manager: Arc<StateManager>,
    active_streams: DashMap<String, StreamInfo>,
    viewers: DashMap<String, DashMap<String, Viewer>>, // stream_id -> viewer_id -> Viewer
}

impl StreamManager {
    pub async fn new(state_manager: Arc<StateManager>) -> Result<Self> {
        let manager = Self {
            state_manager,
            active_streams: DashMap::new(),
            viewers: DashMap::new(),
        };

        // Load existing streams from Redis on startup
        manager.load_streams_from_state().await?;
        
        // Start background tasks
        manager.start_activation_monitor().await;
        manager.start_timeout_monitor().await;

        Ok(manager)
    }

    async fn load_streams_from_state(&self) -> Result<()> {
        // Load stream data from Redis
        let stream_keys = self.state_manager.get_stream_keys().await?;
        
        for stream_id in stream_keys {
            if let Ok(Some(stream_info)) = self.state_manager.get_stream(&stream_id).await {
                self.active_streams.insert(stream_id.clone(), stream_info);
            }
        }

        info!("Loaded {} streams from state", self.active_streams.len());
        Ok(())
    }

    pub async fn list_streams(&self) -> Result<Vec<StreamInfo>> {
        let mut streams = Vec::new();
        
        for entry in self.active_streams.iter() {
            streams.push(entry.value().clone());
        }

        // Sort by creation time, newest first
        streams.sort_by(|a, b| b.created_at.cmp(&a.created_at));
        
        Ok(streams)
    }

    pub async fn get_stream_status(&self, stream_id: &str) -> Result<Option<StreamStatus>> {
        if let Some(stream_info) = self.active_streams.get(stream_id) {
            let active_viewers = self.get_active_viewer_count(stream_id).await;
            let time_until_timeout = self.calculate_timeout_remaining(stream_id).await;
            let recent_activity = self.get_recent_activity(stream_id).await?;

            let status = StreamStatus::from_stream_info(
                &stream_info,
                active_viewers,
                time_until_timeout,
                recent_activity,
            );

            Ok(Some(status))
        } else {
            Ok(None)
        }
    }

    pub async fn create_stream(
        &self,
        title: String,
        description: String,
        cost_per_viewer: f64,
        min_viewers: usize,
        metadata: StreamMetadata,
    ) -> Result<StreamInfo> {
        let mut stream_info = StreamInfo::new(
            title,
            description,
            cost_per_viewer,
            min_viewers,
            metadata,
        );

        // Set to pledging state immediately
        stream_info.status = StreamState::Pledging;

        // Store in Redis
        self.state_manager.set_stream(&stream_info.id, &stream_info).await?;
        
        // Store in local cache
        let stream_id = stream_info.id.clone();
        self.active_streams.insert(stream_id.clone(), stream_info.clone());
        self.viewers.insert(stream_id, DashMap::new());

        info!("Created new stream: {} ({})", stream_info.title, stream_info.id);
        
        Ok(stream_info)
    }

    pub async fn add_pledge(
        &self,
        stream_id: &str,
        viewer_id: &str,
        amount: f64,
        betting_balance: f64,
    ) -> Result<bool> {
        if let Some(mut stream_entry) = self.active_streams.get_mut(stream_id) {
            let stream_info = stream_entry.value_mut();

            // Check if stream can accept pledges
            if !matches!(stream_info.status, StreamState::Listed | StreamState::Pledging) {
                return Ok(false);
            }

            // Create or update viewer
            let viewer = Viewer {
                id: viewer_id.to_string(),
                pledge_amount: amount,
                betting_balance,
                joined_at: Utc::now(),
                last_activity: Utc::now(),
                total_bets: 0,
                is_active: true,
            };

            // Add viewer to stream
            if let Some(stream_viewers) = self.viewers.get(stream_id) {
                let is_new_viewer = !stream_viewers.contains_key(viewer_id);
                stream_viewers.insert(viewer_id.to_string(), viewer);

                // Update stream totals
                if is_new_viewer {
                    stream_info.current_pledges += amount;
                    stream_info.pledger_count += 1;
                    stream_info.status = StreamState::Pledging;
                }

                // Record activity
                self.record_activity(
                    stream_id,
                    ActivityType::PledgeReceived,
                    Some(amount),
                    Some(viewer_id.to_string()),
                ).await?;

                // Update state in Redis
                self.state_manager.set_stream(stream_id, stream_info).await?;

                info!(
                    "Added pledge of ${:.2} to stream {} ({:.1}% funded)",
                    amount,
                    stream_id,
                    stream_info.activation_percentage()
                );

                Ok(true)
            } else {
                Ok(false)
            }
        } else {
            Ok(false)
        }
    }

    pub async fn try_activate_stream(&self, stream_id: &str) -> Result<ActivationResult> {
        if let Some(mut stream_entry) = self.active_streams.get_mut(stream_id) {
            let stream_info = stream_entry.value_mut();

            if stream_info.can_activate() {
                stream_info.status = StreamState::Active;
                
                // Update state in Redis
                self.state_manager.set_stream(stream_id, stream_info).await?;

                // Record activation
                self.record_activity(
                    stream_id,
                    ActivityType::StreamActivated,
                    None,
                    None,
                ).await?;

                // Generate activation URL (this would integrate with your streaming service)
                let activation_url = format!("https://stream.morphine.live/{}", stream_id);

                info!("Activated stream: {} ({})", stream_info.title, stream_id);

                Ok(ActivationResult {
                    success: true,
                    message: "Stream activated successfully".to_string(),
                    stream_state: StreamState::Active,
                    activation_url: Some(activation_url),
                })
            } else {
                Ok(ActivationResult {
                    success: false,
                    message: format!(
                        "Insufficient funding: ${:.2} of ${:.2} required",
                        stream_info.current_pledges,
                        stream_info.activation_threshold
                    ),
                    stream_state: stream_info.status.clone(),
                    activation_url: None,
                })
            }
        } else {
            Ok(ActivationResult {
                success: false,
                message: "Stream not found".to_string(),
                stream_state: StreamState::Failed,
                activation_url: None,
            })
        }
    }

    async fn get_active_viewer_count(&self, stream_id: &str) -> usize {
        if let Some(stream_viewers) = self.viewers.get(stream_id) {
            stream_viewers.iter().filter(|entry| entry.value().is_active).count()
        } else {
            0
        }
    }

    async fn calculate_timeout_remaining(&self, stream_id: &str) -> Option<u64> {
        // Implementation would check activation timeout
        // For now, return a placeholder
        Some(300) // 5 minutes
    }

    async fn get_recent_activity(&self, stream_id: &str) -> Result<Vec<StreamActivity>> {
        // Load recent activity from Redis
        self.state_manager.get_stream_activity(stream_id).await
            .unwrap_or_else(|_| Vec::new())
            .into_iter()
            .take(10) // Last 10 activities
            .collect::<Vec<_>>()
            .into()
    }

    async fn record_activity(
        &self,
        stream_id: &str,
        activity_type: ActivityType,
        amount: Option<f64>,
        user_id: Option<String>,
    ) -> Result<()> {
        let activity = StreamActivity {
            timestamp: Utc::now(),
            activity_type,
            amount,
            user_id,
        };

        self.state_manager.add_stream_activity(stream_id, &activity).await
    }

    async fn start_activation_monitor(&self) {
        let state_manager = self.state_manager.clone();
        let streams = self.active_streams.clone();

        tokio::spawn(async move {
            let mut interval = tokio::time::interval(Duration::from_secs(5));
            
            loop {
                interval.tick().await;
                
                for entry in streams.iter() {
                    let (stream_id, stream_info) = (entry.key(), entry.value());
                    
                    if stream_info.can_activate() {
                        info!("Stream {} ready for activation", stream_id);
                        // In a real implementation, you might auto-activate or notify
                    }
                }
            }
        });
    }

    async fn start_timeout_monitor(&self) {
        let state_manager = self.state_manager.clone();
        let streams = self.active_streams.clone();

        tokio::spawn(async move {
            let mut interval = tokio::time::interval(Duration::from_secs(30));
            
            loop {
                interval.tick().await;
                
                // Check for timed-out streams and mark them as failed
                // Implementation would check creation time + timeout
            }
        });
    }
} 