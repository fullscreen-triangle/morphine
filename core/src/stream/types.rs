use serde::{Deserialize, Serialize};
use uuid::Uuid;
use chrono::{DateTime, Utc};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StreamInfo {
    pub id: String,
    pub title: String,
    pub description: String,
    pub activation_threshold: f64,
    pub cost_per_viewer: f64,
    pub current_pledges: f64,
    pub pledger_count: usize,
    pub status: StreamState,
    pub created_at: DateTime<Utc>,
    pub metadata: StreamMetadata,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StreamMetadata {
    pub category: String,
    pub tags: Vec<String>,
    pub estimated_duration_minutes: u32,
    pub content_rating: String,
    pub analytics_enabled: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum StreamState {
    Listed,
    Pledging,
    Active,
    Concluded,
    Failed,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StreamStatus {
    pub stream_id: String,
    pub state: StreamState,
    pub current_pledges: f64,
    pub activation_threshold: f64,
    pub pledger_count: usize,
    pub active_viewers: usize,
    pub time_until_timeout: Option<u64>,
    pub activation_percentage: f64,
    pub recent_activity: Vec<StreamActivity>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StreamActivity {
    pub timestamp: DateTime<Utc>,
    pub activity_type: ActivityType,
    pub amount: Option<f64>,
    pub user_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ActivityType {
    PledgeReceived,
    ViewerJoined,
    ViewerLeft,
    StreamActivated,
    StreamConcluded,
    BetPlaced,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActivationResult {
    pub success: bool,
    pub message: String,
    pub stream_state: StreamState,
    pub activation_url: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Viewer {
    pub id: String,
    pub pledge_amount: f64,
    pub betting_balance: f64,
    pub joined_at: DateTime<Utc>,
    pub last_activity: DateTime<Utc>,
    pub total_bets: u32,
    pub is_active: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StreamPledge {
    pub viewer_id: String,
    pub amount: f64,
    pub timestamp: DateTime<Utc>,
    pub transaction_id: String,
}

impl StreamInfo {
    pub fn new(
        title: String,
        description: String,
        cost_per_viewer: f64,
        min_viewers: usize,
        metadata: StreamMetadata,
    ) -> Self {
        let activation_threshold = cost_per_viewer * min_viewers as f64;
        
        Self {
            id: Uuid::new_v4().to_string(),
            title,
            description,
            activation_threshold,
            cost_per_viewer,
            current_pledges: 0.0,
            pledger_count: 0,
            status: StreamState::Listed,
            created_at: Utc::now(),
            metadata,
        }
    }

    pub fn activation_percentage(&self) -> f64 {
        if self.activation_threshold <= 0.0 {
            return 100.0;
        }
        (self.current_pledges / self.activation_threshold * 100.0).min(100.0)
    }

    pub fn can_activate(&self) -> bool {
        self.current_pledges >= self.activation_threshold
            && matches!(self.status, StreamState::Pledging)
    }
}

impl StreamStatus {
    pub fn from_stream_info(
        stream_info: &StreamInfo,
        active_viewers: usize,
        time_until_timeout: Option<u64>,
        recent_activity: Vec<StreamActivity>,
    ) -> Self {
        Self {
            stream_id: stream_info.id.clone(),
            state: stream_info.status.clone(),
            current_pledges: stream_info.current_pledges,
            activation_threshold: stream_info.activation_threshold,
            pledger_count: stream_info.pledger_count,
            active_viewers,
            time_until_timeout,
            activation_percentage: stream_info.activation_percentage(),
            recent_activity,
        }
    }
} 