"""
Stream service for communicating with the core service and managing stream processing
"""

import asyncio
import json
from typing import Dict, Any, Optional
import httpx
import structlog

from ..models.analytics import AnalyticsResult
from .redis_service import RedisService

logger = structlog.get_logger(__name__)

class StreamService:
    """Service for managing stream processing and communication with core service"""
    
    def __init__(self, core_service_url: str, redis_service: RedisService):
        self.core_service_url = core_service_url.rstrip('/')
        self.redis_service = redis_service
        self.active_streams = set()
        self.processing_tasks = {}
        
    async def start_stream_processing(self, stream_id: str):
        """Start processing analytics for a stream"""
        if stream_id in self.active_streams:
            logger.warning("Stream already being processed", stream_id=stream_id)
            return
        
        self.active_streams.add(stream_id)
        
        # Create background task for stream processing
        task = asyncio.create_task(self._process_stream_loop(stream_id))
        self.processing_tasks[stream_id] = task
        
        logger.info("Started stream processing", stream_id=stream_id)
    
    async def stop_stream_processing(self, stream_id: str):
        """Stop processing analytics for a stream"""
        if stream_id in self.active_streams:
            self.active_streams.remove(stream_id)
        
        # Cancel processing task
        if stream_id in self.processing_tasks:
            task = self.processing_tasks[stream_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.processing_tasks[stream_id]
        
        logger.info("Stopped stream processing", stream_id=stream_id)
    
    async def _process_stream_loop(self, stream_id: str):
        """Background loop for processing stream data"""
        try:
            while stream_id in self.active_streams:
                # This would typically fetch frames from the stream source
                # For now, we'll just wait and let the main processing handle frames
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            logger.info("Stream processing loop cancelled", stream_id=stream_id)
        except Exception as e:
            logger.error("Error in stream processing loop", error=str(e), stream_id=stream_id)
    
    async def notify_analytics_update(self, stream_id: str, analytics: AnalyticsResult):
        """Notify core service of analytics update"""
        try:
            # Prepare notification data
            notification_data = {
                "stream_id": stream_id,
                "timestamp": analytics.timestamp,
                "analytics": analytics.dict(),
                "processing_time": analytics.processing_time
            }
            
            # Extract key metrics for notification
            if analytics.vibrio:
                notification_data["vibrio_summary"] = {
                    "detection_count": len(analytics.vibrio.detections),
                    "track_count": len(analytics.vibrio.tracks),
                    "motion_energy": analytics.vibrio.motion_energy.motion_energy,
                    "max_speed": max([track.speed for track in analytics.vibrio.tracks], default=0.0)
                }
            
            if analytics.moriarty:
                notification_data["moriarty_summary"] = {
                    "pose_detected": analytics.moriarty.pose_detected,
                    "pose_quality": analytics.moriarty.pose_quality_score,
                    "joint_count": len(analytics.moriarty.biomechanics.joint_angles),
                    "has_center_of_mass": analytics.moriarty.biomechanics.center_of_mass is not None
                }
            
            # Send notification to core service
            await self._send_analytics_notification(notification_data)
            
            # Check for betting opportunities
            await self._check_betting_opportunities(stream_id, analytics)
            
            # Check for alerts
            await self._check_analytics_alerts(stream_id, analytics)
            
        except Exception as e:
            logger.error("Failed to notify analytics update", error=str(e), stream_id=stream_id)
    
    async def _send_analytics_notification(self, notification_data: Dict[str, Any]):
        """Send analytics notification to core service"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.core_service_url}/analytics/update",
                    json=notification_data,
                    timeout=5.0
                )
                
                if response.status_code not in [200, 202]:
                    logger.warning(
                        "Core service returned error for analytics notification",
                        status_code=response.status_code,
                        stream_id=notification_data["stream_id"]
                    )
                    
        except Exception as e:
            logger.error("Failed to send analytics notification", error=str(e))
    
    async def _check_betting_opportunities(self, stream_id: str, analytics: AnalyticsResult):
        """Check for betting opportunities in analytics data"""
        try:
            opportunities = []
            current_time = analytics.timestamp
            
            # Speed-based opportunities
            if analytics.vibrio and analytics.vibrio.tracks:
                for track in analytics.vibrio.tracks:
                    if track.speed > 20:  # High speed threshold
                        opportunity = {
                            "stream_id": stream_id,
                            "opportunity_type": "high_speed",
                            "confidence": min(track.speed / 50, 1.0),
                            "description": f"High speed detected: {track.speed:.1f} km/h",
                            "metadata": {
                                "track_id": track.track_id,
                                "speed": track.speed,
                                "position": track.position
                            },
                            "created_at": current_time,
                            "expires_at": current_time + 30  # 30 second window
                        }
                        opportunities.append(opportunity)
            
            # Pose-based opportunities
            if analytics.moriarty and analytics.moriarty.pose_detected:
                joint_angles = analytics.moriarty.biomechanics.joint_angles
                
                # Look for interesting pose events
                for joint, angle in joint_angles.items():
                    if angle > 150 or angle < 30:  # Extreme angles
                        opportunity = {
                            "stream_id": stream_id,
                            "opportunity_type": "extreme_pose",
                            "confidence": 0.8,
                            "description": f"Extreme {joint} angle: {angle:.1f}°",
                            "metadata": {
                                "joint": joint,
                                "angle": angle,
                                "pose_quality": analytics.moriarty.pose_quality_score
                            },
                            "created_at": current_time,
                            "expires_at": current_time + 20  # 20 second window
                        }
                        opportunities.append(opportunity)
            
            # Store opportunities in Redis
            for opportunity in opportunities:
                await self.redis_service.store_betting_opportunity(stream_id, opportunity)
                logger.info("Generated betting opportunity", 
                           stream_id=stream_id, 
                           type=opportunity["opportunity_type"])
            
        except Exception as e:
            logger.error("Failed to check betting opportunities", error=str(e), stream_id=stream_id)
    
    async def _check_analytics_alerts(self, stream_id: str, analytics: AnalyticsResult):
        """Check for analytics alerts"""
        try:
            alerts = []
            
            # High processing time alert
            if analytics.processing_time > 0.5:  # 500ms threshold
                alerts.append({
                    "stream_id": stream_id,
                    "timestamp": analytics.timestamp,
                    "alert_type": "high_processing_time",
                    "severity": "medium",
                    "message": f"High processing time: {analytics.processing_time:.3f}s",
                    "metadata": {"processing_time": analytics.processing_time}
                })
            
            # High speed alert
            if analytics.vibrio and analytics.vibrio.tracks:
                max_speed = max([track.speed for track in analytics.vibrio.tracks], default=0.0)
                if max_speed > 50.0:  # Very high speed threshold
                    alerts.append({
                        "stream_id": stream_id,
                        "timestamp": analytics.timestamp,
                        "alert_type": "high_speed",
                        "severity": "high",
                        "message": f"Very high speed detected: {max_speed:.1f} km/h",
                        "metadata": {"max_speed": max_speed}
                    })
            
            # Motion anomaly alert
            if analytics.vibrio:
                motion_energy = analytics.vibrio.motion_energy.motion_energy
                if motion_energy > 0.8:  # High motion threshold
                    alerts.append({
                        "stream_id": stream_id,
                        "timestamp": analytics.timestamp,
                        "alert_type": "unusual_motion",
                        "severity": "medium",
                        "message": f"High motion energy detected: {motion_energy:.2f}",
                        "metadata": {"motion_energy": motion_energy}
                    })
            
            # No pose detection alert (if expected)
            if analytics.moriarty and not analytics.moriarty.pose_detected:
                # Only alert if we haven't detected pose for a while
                # This would require tracking state over time
                pass
            
            # Store alerts in Redis
            for alert in alerts:
                await self.redis_service.store_alert(stream_id, alert)
                logger.warning("Analytics alert generated", 
                             stream_id=stream_id, 
                             alert_type=alert["alert_type"],
                             severity=alert["severity"])
            
        except Exception as e:
            logger.error("Failed to check analytics alerts", error=str(e), stream_id=stream_id)
    
    async def get_stream_status(self, stream_id: str) -> Dict[str, Any]:
        """Get status of a stream from core service"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.core_service_url}/api/streams/{stream_id}",
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    return {"success": False, "error": "Stream not found"}
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}"}
                    
        except Exception as e:
            logger.error("Failed to get stream status", error=str(e), stream_id=stream_id)
            return {"success": False, "error": str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of core service connection"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.core_service_url}/health",
                    timeout=5.0
                )
                
                return {
                    "core_service_connected": response.status_code == 200,
                    "active_streams": len(self.active_streams),
                    "processing_tasks": len(self.processing_tasks)
                }
                
        except Exception as e:
            logger.error("Core service health check failed", error=str(e))
            return {
                "core_service_connected": False,
                "error": str(e),
                "active_streams": len(self.active_streams),
                "processing_tasks": len(self.processing_tasks)
            } 