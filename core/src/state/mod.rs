use anyhow::{Result, Context};
use redis::{AsyncCommands, Client};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::RwLock;

use crate::stream::{StreamInfo, StreamActivity};

pub struct StateManager {
    redis_client: Client,
    connection_pool: Arc<RwLock<Option<redis::aio::Connection>>>,
}

impl StateManager {
    pub async fn new(redis_url: &str) -> Result<Self> {
        let client = Client::open(redis_url)
            .context("Failed to create Redis client")?;

        let mut connection = client.get_async_connection().await
            .context("Failed to connect to Redis")?;

        // Test connection
        let _: String = redis::cmd("PING").query_async(&mut connection).await
            .context("Failed to ping Redis")?;

        Ok(Self {
            redis_client: client,
            connection_pool: Arc::new(RwLock::new(Some(connection))),
        })
    }

    async fn get_connection(&self) -> Result<redis::aio::Connection> {
        let mut pool = self.connection_pool.write().await;
        
        if let Some(conn) = pool.take() {
            Ok(conn)
        } else {
            self.redis_client.get_async_connection().await
                .context("Failed to get Redis connection")
        }
    }

    async fn return_connection(&self, connection: redis::aio::Connection) {
        let mut pool = self.connection_pool.write().await;
        *pool = Some(connection);
    }

    pub async fn set_stream(&self, stream_id: &str, stream_info: &StreamInfo) -> Result<()> {
        let mut conn = self.get_connection().await?;
        
        let serialized = serde_json::to_string(stream_info)
            .context("Failed to serialize stream info")?;
        
        let key = format!("stream:{}", stream_id);
        conn.set(&key, serialized).await
            .context("Failed to set stream in Redis")?;

        // Add to stream list
        conn.sadd("streams", stream_id).await
            .context("Failed to add stream to list")?;

        self.return_connection(conn).await;
        Ok(())
    }

    pub async fn get_stream(&self, stream_id: &str) -> Result<Option<StreamInfo>> {
        let mut conn = self.get_connection().await?;
        
        let key = format!("stream:{}", stream_id);
        let result: Option<String> = conn.get(&key).await
            .context("Failed to get stream from Redis")?;

        self.return_connection(conn).await;

        if let Some(serialized) = result {
            let stream_info = serde_json::from_str(&serialized)
                .context("Failed to deserialize stream info")?;
            Ok(Some(stream_info))
        } else {
            Ok(None)
        }
    }

    pub async fn get_stream_keys(&self) -> Result<Vec<String>> {
        let mut conn = self.get_connection().await?;
        
        let keys: Vec<String> = conn.smembers("streams").await
            .context("Failed to get stream keys")?;

        self.return_connection(conn).await;
        Ok(keys)
    }

    pub async fn add_stream_activity(&self, stream_id: &str, activity: &StreamActivity) -> Result<()> {
        let mut conn = self.get_connection().await?;
        
        let serialized = serde_json::to_string(activity)
            .context("Failed to serialize activity")?;
        
        let key = format!("stream:{}:activity", stream_id);
        
        // Add to list (keep last 100 activities)
        conn.lpush(&key, &serialized).await
            .context("Failed to add activity")?;
        
        conn.ltrim(&key, 0, 99).await
            .context("Failed to trim activity list")?;

        self.return_connection(conn).await;
        Ok(())
    }

    pub async fn get_stream_activity(&self, stream_id: &str) -> Result<Vec<StreamActivity>> {
        let mut conn = self.get_connection().await?;
        
        let key = format!("stream:{}:activity", stream_id);
        let activities: Vec<String> = conn.lrange(&key, 0, -1).await
            .context("Failed to get activities")?;

        self.return_connection(conn).await;

        let mut parsed_activities = Vec::new();
        for activity_str in activities {
            if let Ok(activity) = serde_json::from_str::<StreamActivity>(&activity_str) {
                parsed_activities.push(activity);
            }
        }

        Ok(parsed_activities)
    }

    pub async fn set_user_balance(&self, user_id: &str, stream_id: &str, balance: f64) -> Result<()> {
        let mut conn = self.get_connection().await?;
        
        let key = format!("balance:{}:{}", user_id, stream_id);
        conn.set(&key, balance).await
            .context("Failed to set user balance")?;

        self.return_connection(conn).await;
        Ok(())
    }

    pub async fn get_user_balance(&self, user_id: &str, stream_id: &str) -> Result<f64> {
        let mut conn = self.get_connection().await?;
        
        let key = format!("balance:{}:{}", user_id, stream_id);
        let balance: Option<f64> = conn.get(&key).await
            .context("Failed to get user balance")?;

        self.return_connection(conn).await;
        Ok(balance.unwrap_or(0.0))
    }

    pub async fn update_user_balance(&self, user_id: &str, stream_id: &str, delta: f64) -> Result<f64> {
        let mut conn = self.get_connection().await?;
        
        let key = format!("balance:{}:{}", user_id, stream_id);
        let new_balance: f64 = conn.incr(&key, delta).await
            .context("Failed to update user balance")?;

        self.return_connection(conn).await;
        Ok(new_balance)
    }

    pub async fn store_bet(&self, bet_id: &str, bet_data: &str) -> Result<()> {
        let mut conn = self.get_connection().await?;
        
        let key = format!("bet:{}", bet_id);
        conn.set(&key, bet_data).await
            .context("Failed to store bet")?;

        // Set expiration (24 hours)
        conn.expire(&key, 86400).await
            .context("Failed to set bet expiration")?;

        self.return_connection(conn).await;
        Ok(())
    }

    pub async fn get_bet(&self, bet_id: &str) -> Result<Option<String>> {
        let mut conn = self.get_connection().await?;
        
        let key = format!("bet:{}", bet_id);
        let result: Option<String> = conn.get(&key).await
            .context("Failed to get bet")?;

        self.return_connection(conn).await;
        Ok(result)
    }

    pub async fn increment_counter(&self, key: &str) -> Result<i64> {
        let mut conn = self.get_connection().await?;
        
        let count: i64 = conn.incr(key, 1).await
            .context("Failed to increment counter")?;

        self.return_connection(conn).await;
        Ok(count)
    }

    pub async fn set_key_with_expiry(&self, key: &str, value: &str, expiry_seconds: usize) -> Result<()> {
        let mut conn = self.get_connection().await?;
        
        conn.set_ex(key, value, expiry_seconds).await
            .context("Failed to set key with expiry")?;

        self.return_connection(conn).await;
        Ok(())
    }
} 