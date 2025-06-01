"""
Redis service for analytics data storage and retrieval
"""

import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import aioredis
import structlog

from ..models.analytics import AnalyticsResult, StreamAnalytics

logger = structlog.get_logger(__name__)

class RedisService:
    """Redis service for analytics data management"""
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis_client = None
        
        # Redis key patterns
        self.ANALYTICS_KEY = "morphine:analytics:{stream_id}"
        self.STREAM_STATE_KEY = "morphine:stream:{stream_id}:state"
        self.STREAM_SUMMARY_KEY = "morphine:stream:{stream_id}:summary"
        self.LATEST_ANALYTICS_KEY = "morphine:analytics:{stream_id}:latest"
        self.BETTING_OPPORTUNITIES_KEY = "morphine:betting:{stream_id}"
        self.ALERTS_KEY = "morphine:alerts:{stream_id}"
        
        # TTL settings (in seconds)
        self.ANALYTICS_TTL = 3600  # 1 hour
        self.STREAM_STATE_TTL = 86400  # 24 hours
        self.LATEST_TTL = 300  # 5 minutes
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=10
            )
            await self.redis_client.ping()
            logger.info("Connected to Redis", url=self.redis_url)
        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            raise
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")
    
    async def ping(self) -> bool:
        """Ping Redis to check connection"""
        try:
            if self.redis_client:
                await self.redis_client.ping()
                return True
        except Exception:
            pass
        return False
    
    async def store_analytics(self, stream_id: str, analytics: AnalyticsResult):
        """Store analytics result for a stream"""
        try:
            analytics_key = self.ANALYTICS_KEY.format(stream_id=stream_id)
            latest_key = self.LATEST_ANALYTICS_KEY.format(stream_id=stream_id)
            
            # Convert to JSON
            analytics_data = analytics.dict()
            analytics_json = json.dumps(analytics_data, default=str)
            
            # Store with timestamp as score for sorted set
            timestamp = analytics.timestamp
            
            # Store in sorted set for time-based retrieval
            await self.redis_client.zadd(analytics_key, {analytics_json: timestamp})
            
            # Store as latest analytics
            await self.redis_client.setex(latest_key, self.LATEST_TTL, analytics_json)
            
            # Set TTL for analytics set
            await self.redis_client.expire(analytics_key, self.ANALYTICS_TTL)
            
            # Update stream summary statistics
            await self.update_stream_summary(stream_id, analytics)
            
            logger.debug("Stored analytics", stream_id=stream_id, timestamp=timestamp)
            
        except Exception as e:
            logger.error("Failed to store analytics", error=str(e), stream_id=stream_id)
            raise
    
    async def get_latest_analytics(self, stream_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest analytics for a stream"""
        try:
            latest_key = self.LATEST_ANALYTICS_KEY.format(stream_id=stream_id)
            analytics_json = await self.redis_client.get(latest_key)
            
            if analytics_json:
                return json.loads(analytics_json)
            
            return None
            
        except Exception as e:
            logger.error("Failed to get latest analytics", error=str(e), stream_id=stream_id)
            return None
    
    async def get_analytics_range(self, stream_id: str, start_time: float, end_time: float) -> List[Dict[str, Any]]:
        """Get analytics within a time range"""
        try:
            analytics_key = self.ANALYTICS_KEY.format(stream_id=stream_id)
            
            # Get analytics within time range
            results = await self.redis_client.zrangebyscore(
                analytics_key, start_time, end_time, withscores=False
            )
            
            analytics_list = []
            for result in results:
                try:
                    analytics_data = json.loads(result)
                    analytics_list.append(analytics_data)
                except json.JSONDecodeError:
                    continue
            
            return analytics_list
            
        except Exception as e:
            logger.error("Failed to get analytics range", error=str(e), stream_id=stream_id)
            return []
    
    async def initialize_stream(self, stream_id: str, settings: Dict[str, Any]):
        """Initialize analytics state for a new stream"""
        try:
            state_key = self.STREAM_STATE_KEY.format(stream_id=stream_id)
            summary_key = self.STREAM_SUMMARY_KEY.format(stream_id=stream_id)
            
            # Initialize stream state
            initial_state = {
                "stream_id": stream_id,
                "status": "active",
                "settings": settings,
                "started_at": datetime.now().isoformat(),
                "frame_count": 0,
                "error_count": 0
            }
            
            await self.redis_client.hset(state_key, mapping=initial_state)
            await self.redis_client.expire(state_key, self.STREAM_STATE_TTL)
            
            # Initialize summary
            initial_summary = {
                "stream_id": stream_id,
                "total_frames": 0,
                "avg_processing_time": 0.0,
                "detection_rate": 0.0,
                "pose_detection_rate": 0.0,
                "error_rate": 0.0,
                "avg_fps": 0.0,
                "last_updated": datetime.now().isoformat()
            }
            
            await self.redis_client.hset(summary_key, mapping=initial_summary)
            await self.redis_client.expire(summary_key, self.STREAM_STATE_TTL)
            
            logger.info("Initialized stream analytics", stream_id=stream_id)
            
        except Exception as e:
            logger.error("Failed to initialize stream", error=str(e), stream_id=stream_id)
            raise
    
    async def update_stream_summary(self, stream_id: str, analytics: AnalyticsResult):
        """Update stream summary statistics"""
        try:
            summary_key = self.STREAM_SUMMARY_KEY.format(stream_id=stream_id)
            
            # Get current summary
            current_summary = await self.redis_client.hgetall(summary_key)
            
            if not current_summary:
                # Initialize if doesn't exist
                await self.initialize_stream(stream_id, {})
                current_summary = await self.redis_client.hgetall(summary_key)
            
            # Update statistics
            total_frames = int(current_summary.get("total_frames", 0)) + 1
            avg_processing_time = float(current_summary.get("avg_processing_time", 0.0))
            detection_rate = float(current_summary.get("detection_rate", 0.0))
            pose_detection_rate = float(current_summary.get("pose_detection_rate", 0.0))
            error_rate = float(current_summary.get("error_rate", 0.0))
            
            # Calculate new averages
            new_avg_processing_time = (
                (avg_processing_time * (total_frames - 1) + analytics.processing_time) / total_frames
            )
            
            # Detection rates
            has_detections = analytics.vibrio and len(analytics.vibrio.detections) > 0
            new_detection_rate = (
                (detection_rate * (total_frames - 1) + (1.0 if has_detections else 0.0)) / total_frames
            )
            
            has_pose = analytics.moriarty and analytics.moriarty.pose_detected
            new_pose_detection_rate = (
                (pose_detection_rate * (total_frames - 1) + (1.0 if has_pose else 0.0)) / total_frames
            )
            
            # Error rate (if there was an error in processing)
            has_error = analytics.error_message is not None
            new_error_rate = (
                (error_rate * (total_frames - 1) + (1.0 if has_error else 0.0)) / total_frames
            )
            
            # Update summary
            updated_summary = {
                "total_frames": total_frames,
                "avg_processing_time": new_avg_processing_time,
                "detection_rate": new_detection_rate,
                "pose_detection_rate": new_pose_detection_rate,
                "error_rate": new_error_rate,
                "avg_fps": 1.0 / new_avg_processing_time if new_avg_processing_time > 0 else 0.0,
                "last_updated": datetime.now().isoformat()
            }
            
            await self.redis_client.hset(summary_key, mapping=updated_summary)
            await self.redis_client.expire(summary_key, self.STREAM_STATE_TTL)
            
        except Exception as e:
            logger.error("Failed to update stream summary", error=str(e), stream_id=stream_id)
    
    async def get_stream_summary(self, stream_id: str) -> Dict[str, Any]:
        """Get stream summary statistics"""
        try:
            summary_key = self.STREAM_SUMMARY_KEY.format(stream_id=stream_id)
            summary = await self.redis_client.hgetall(summary_key)
            
            if not summary:
                return {
                    "stream_id": stream_id,
                    "total_frames": 0,
                    "avg_processing_time": 0.0,
                    "detection_rate": 0.0,
                    "pose_detection_rate": 0.0,
                    "error_rate": 0.0,
                    "avg_fps": 0.0
                }
            
            # Convert string values to appropriate types
            return {
                "stream_id": summary.get("stream_id", stream_id),
                "total_frames": int(summary.get("total_frames", 0)),
                "avg_processing_time": float(summary.get("avg_processing_time", 0.0)),
                "detection_rate": float(summary.get("detection_rate", 0.0)),
                "pose_detection_rate": float(summary.get("pose_detection_rate", 0.0)),
                "error_rate": float(summary.get("error_rate", 0.0)),
                "avg_fps": float(summary.get("avg_fps", 0.0)),
                "last_updated": summary.get("last_updated")
            }
            
        except Exception as e:
            logger.error("Failed to get stream summary", error=str(e), stream_id=stream_id)
            return {}
    
    async def cleanup_stream(self, stream_id: str):
        """Cleanup stream data"""
        try:
            # Remove stream state
            state_key = self.STREAM_STATE_KEY.format(stream_id=stream_id)
            await self.redis_client.delete(state_key)
            
            # Keep summary and analytics for historical purposes
            # Only mark as inactive
            summary_key = self.STREAM_SUMMARY_KEY.format(stream_id=stream_id)
            await self.redis_client.hset(summary_key, "status", "inactive")
            await self.redis_client.hset(summary_key, "ended_at", datetime.now().isoformat())
            
            logger.info("Cleaned up stream data", stream_id=stream_id)
            
        except Exception as e:
            logger.error("Failed to cleanup stream", error=str(e), stream_id=stream_id)
    
    async def store_betting_opportunity(self, stream_id: str, opportunity: Dict[str, Any]):
        """Store a betting opportunity"""
        try:
            betting_key = self.BETTING_OPPORTUNITIES_KEY.format(stream_id=stream_id)
            opportunity_json = json.dumps(opportunity, default=str)
            
            # Store with expiration timestamp as score
            expire_time = opportunity.get("expires_at", datetime.now().timestamp() + 60)
            await self.redis_client.zadd(betting_key, {opportunity_json: expire_time})
            
            # Set TTL for the key
            await self.redis_client.expire(betting_key, 300)  # 5 minutes
            
            logger.debug("Stored betting opportunity", stream_id=stream_id)
            
        except Exception as e:
            logger.error("Failed to store betting opportunity", error=str(e), stream_id=stream_id)
    
    async def get_betting_opportunities(self, stream_id: str) -> List[Dict[str, Any]]:
        """Get active betting opportunities for a stream"""
        try:
            betting_key = self.BETTING_OPPORTUNITIES_KEY.format(stream_id=stream_id)
            current_time = datetime.now().timestamp()
            
            # Get non-expired opportunities
            results = await self.redis_client.zrangebyscore(
                betting_key, current_time, '+inf', withscores=False
            )
            
            opportunities = []
            for result in results:
                try:
                    opportunity = json.loads(result)
                    opportunities.append(opportunity)
                except json.JSONDecodeError:
                    continue
            
            return opportunities
            
        except Exception as e:
            logger.error("Failed to get betting opportunities", error=str(e), stream_id=stream_id)
            return []
    
    async def store_alert(self, stream_id: str, alert: Dict[str, Any]):
        """Store an analytics alert"""
        try:
            alert_key = self.ALERTS_KEY.format(stream_id=stream_id)
            alert_json = json.dumps(alert, default=str)
            
            # Store with timestamp as score
            timestamp = alert.get("timestamp", datetime.now().timestamp())
            await self.redis_client.zadd(alert_key, {alert_json: timestamp})
            
            # Keep only recent alerts (last 1000)
            await self.redis_client.zremrangebyrank(alert_key, 0, -1001)
            
            # Set TTL
            await self.redis_client.expire(alert_key, 3600)  # 1 hour
            
            logger.info("Stored alert", stream_id=stream_id, alert_type=alert.get("alert_type"))
            
        except Exception as e:
            logger.error("Failed to store alert", error=str(e), stream_id=stream_id)
    
    async def get_recent_alerts(self, stream_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent alerts for a stream"""
        try:
            alert_key = self.ALERTS_KEY.format(stream_id=stream_id)
            
            # Get recent alerts (newest first)
            results = await self.redis_client.zrevrange(alert_key, 0, limit - 1, withscores=False)
            
            alerts = []
            for result in results:
                try:
                    alert = json.loads(result)
                    alerts.append(alert)
                except json.JSONDecodeError:
                    continue
            
            return alerts
            
        except Exception as e:
            logger.error("Failed to get alerts", error=str(e), stream_id=stream_id)
            return [] 