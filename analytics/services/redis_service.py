"""
Redis service for analytics data storage and retrieval
"""

import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import aioredis
import structlog

from models.analytics import AnalyticsResult, StreamAnalytics

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
            analytics_json = json.dumps(analytics_data)
            
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
        """Initialize stream state"""
        try:
            state_key = self.STREAM_STATE_KEY.format(stream_id=stream_id)
            summary_key = self.STREAM_SUMMARY_KEY.format(stream_id=stream_id)
            
            # Initialize stream state
            stream_state = {
                "stream_id": stream_id,
                "status": "active",
                "start_time": datetime.utcnow().isoformat(),
                "settings": settings,
                "last_update": datetime.utcnow().isoformat()
            }
            
            # Initialize stream summary
            stream_summary = StreamAnalytics(
                stream_id=stream_id,
                start_time=datetime.utcnow(),
                total_frames=0,
                total_detections=0,
                unique_tracks=0,
                average_speed=0.0,
                max_speed=0.0,
                pose_detection_rate=0.0,
                average_processing_time=0.0
            )
            
            await self.redis_client.setex(
                state_key, self.STREAM_STATE_TTL, json.dumps(stream_state)
            )
            await self.redis_client.setex(
                summary_key, self.STREAM_STATE_TTL, stream_summary.json()
            )
            
            logger.info("Initialized stream", stream_id=stream_id)
            
        except Exception as e:
            logger.error("Failed to initialize stream", error=str(e), stream_id=stream_id)
            raise
    
    async def cleanup_stream(self, stream_id: str):
        """Clean up stream data"""
        try:
            # Get all keys for this stream
            keys_to_delete = [
                self.ANALYTICS_KEY.format(stream_id=stream_id),
                self.STREAM_STATE_KEY.format(stream_id=stream_id),
                self.STREAM_SUMMARY_KEY.format(stream_id=stream_id),
                self.LATEST_ANALYTICS_KEY.format(stream_id=stream_id),
                self.BETTING_OPPORTUNITIES_KEY.format(stream_id=stream_id),
                self.ALERTS_KEY.format(stream_id=stream_id)
            ]
            
            # Delete all keys
            await self.redis_client.delete(*keys_to_delete)
            
            logger.info("Cleaned up stream data", stream_id=stream_id)
            
        except Exception as e:
            logger.error("Failed to cleanup stream", error=str(e), stream_id=stream_id)
    
    async def update_stream_summary(self, stream_id: str, analytics: AnalyticsResult):
        """Update stream summary statistics"""
        try:
            summary_key = self.STREAM_SUMMARY_KEY.format(stream_id=stream_id)
            
            # Get existing summary
            summary_json = await self.redis_client.get(summary_key)
            if summary_json:
                summary_data = json.loads(summary_json)
                summary = StreamAnalytics(**summary_data)
            else:
                summary = StreamAnalytics(
                    stream_id=stream_id,
                    start_time=datetime.utcnow()
                )
            
            # Update statistics
            summary.total_frames += 1
            
            if analytics.vibrio:
                summary.total_detections += analytics.vibrio.total_detections
                
                # Update speed statistics
                if analytics.vibrio.tracks:
                    speeds = [track.speed for track in analytics.vibrio.tracks if track.speed > 0]
                    if speeds:
                        max_speed = max(speeds)
                        avg_speed = sum(speeds) / len(speeds)
                        
                        summary.max_speed = max(summary.max_speed, max_speed)
                        
                        # Running average of speed
                        if summary.total_frames > 1:
                            summary.average_speed = (
                                (summary.average_speed * (summary.total_frames - 1) + avg_speed) / 
                                summary.total_frames
                            )
                        else:
                            summary.average_speed = avg_speed
            
            if analytics.moriarty and analytics.moriarty.pose_detected:
                # Update pose detection rate
                pose_frames = summary.total_frames * summary.pose_detection_rate + 1
                summary.pose_detection_rate = pose_frames / summary.total_frames
            
            # Update processing time
            if summary.total_frames > 1:
                summary.average_processing_time = (
                    (summary.average_processing_time * (summary.total_frames - 1) + 
                     analytics.processing_time) / summary.total_frames
                )
            else:
                summary.average_processing_time = analytics.processing_time
            
            # Store updated summary
            await self.redis_client.setex(
                summary_key, self.STREAM_STATE_TTL, summary.json()
            )
            
        except Exception as e:
            logger.error("Failed to update stream summary", error=str(e), stream_id=stream_id)
    
    async def get_stream_summary(self, stream_id: str) -> Optional[Dict[str, Any]]:
        """Get stream analytics summary"""
        try:
            summary_key = self.STREAM_SUMMARY_KEY.format(stream_id=stream_id)
            summary_json = await self.redis_client.get(summary_key)
            
            if summary_json:
                return json.loads(summary_json)
            
            return None
            
        except Exception as e:
            logger.error("Failed to get stream summary", error=str(e), stream_id=stream_id)
            return None
    
    async def store_betting_opportunity(self, stream_id: str, opportunity: Dict[str, Any]):
        """Store a betting opportunity"""
        try:
            betting_key = self.BETTING_OPPORTUNITIES_KEY.format(stream_id=stream_id)
            opportunity_json = json.dumps(opportunity)
            
            # Store with timestamp as score
            timestamp = opportunity.get("timestamp", datetime.utcnow().timestamp())
            await self.redis_client.zadd(betting_key, {opportunity_json: timestamp})
            
            # Keep only recent opportunities (last hour)
            cutoff_time = datetime.utcnow().timestamp() - 3600
            await self.redis_client.zremrangebyscore(betting_key, 0, cutoff_time)
            
            logger.info("Stored betting opportunity", stream_id=stream_id, type=opportunity.get("type"))
            
        except Exception as e:
            logger.error("Failed to store betting opportunity", error=str(e), stream_id=stream_id)
    
    async def store_alert(self, stream_id: str, alert: Dict[str, Any]):
        """Store an analytics alert"""
        try:
            alerts_key = self.ALERTS_KEY.format(stream_id=stream_id)
            alert_json = json.dumps(alert)
            
            # Store with timestamp as score
            timestamp = alert.get("timestamp", datetime.utcnow().timestamp())
            await self.redis_client.zadd(alerts_key, {alert_json: timestamp})
            
            # Keep only recent alerts (last 24 hours)
            cutoff_time = datetime.utcnow().timestamp() - 86400
            await self.redis_client.zremrangebyscore(alerts_key, 0, cutoff_time)
            
            logger.info("Stored alert", stream_id=stream_id, type=alert.get("type"))
            
        except Exception as e:
            logger.error("Failed to store alert", error=str(e), stream_id=stream_id) 