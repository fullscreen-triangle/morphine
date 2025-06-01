"""
Stream service for communicating with the core service and managing stream processing
"""

import asyncio
import json
from typing import Dict, Any, Optional
import httpx
import structlog

from models.analytics import AnalyticsResult
from services.redis_service import RedisService

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
        """Background loop for processing a stream"""
        try:
            while stream_id in self.active_streams:
                # This would typically listen for frames from the core service
                # For now, we'll just sleep and check for stream status
                await asyncio.sleep(1.0)
                
                # Check if stream is still active in core service
                if not await self._is_stream_active(stream_id):
                    logger.info("Stream no longer active in core service", stream_id=stream_id)
                    break
                    
        except asyncio.CancelledError:
            logger.info("Stream processing cancelled", stream_id=stream_id)
        except Exception as e:
            logger.error("Error in stream processing loop", error=str(e), stream_id=stream_id)
        finally:
            if stream_id in self.active_streams:
                self.active_streams.remove(stream_id)
    
    async def _is_stream_active(self, stream_id: str) -> bool:
        """Check if stream is active in core service"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.core_service_url}/streams/{stream_id}/status",
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    status_data = response.json()
                    return status_data.get("status") == "active"
                
                return False
                
        except Exception as e:
            logger.error("Failed to check stream status", error=str(e), stream_id=stream_id)
            return False
    
    async def notify_analytics_update(self, stream_id: str, analytics: AnalyticsResult):
        """Notify core service of analytics update"""
        try:
            # Prepare analytics data for core service
            notification_data = {
                "stream_id": stream_id,
                "timestamp": analytics.timestamp,
                "frame_idx": analytics.frame_idx,
                "analytics": {
                    "total_detections": 0,
                    "active_tracks": 0,
                    "pose_detected": False,
                    "processing_time": analytics.processing_time
                }
            }
            
            # Add Vibrio data
            if analytics.vibrio:
                notification_data["analytics"].update({
                    "total_detections": analytics.vibrio.total_detections,
                    "active_tracks": analytics.vibrio.active_tracks,
                    "max_speed": max([track.speed for track in analytics.vibrio.tracks], default=0.0),
                    "motion_energy": analytics.vibrio.motion_energy.motion_energy,
                    "flow_magnitude": analytics.vibrio.optical_flow.flow_magnitude
                })
            
            # Add Moriarty data
            if analytics.moriarty:
                notification_data["analytics"].update({
                    "pose_detected": analytics.moriarty.pose_detected,
                    "landmarks_count": len(analytics.moriarty.landmarks)
                })
                
                if analytics.moriarty.biomechanics:
                    notification_data["analytics"]["joint_angles"] = analytics.moriarty.biomechanics.joint_angles
                
                if analytics.moriarty.stride_metrics:
                    notification_data["analytics"]["stride_metrics"] = {
                        "stride_frequency": analytics.moriarty.stride_metrics.stride_frequency,
                        "stride_length": analytics.moriarty.stride_metrics.stride_length
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
            
            # Speed-based opportunities
            if analytics.vibrio and analytics.vibrio.tracks:
                for track in analytics.vibrio.tracks:
                    if track.speed > 30.0:  # High speed threshold
                        opportunities.append({
                            "stream_id": stream_id,
                            "timestamp": analytics.timestamp,
                            "opportunity_type": "speed_milestone",
                            "description": f"Track {track.track_id} reached {track.speed:.1f} km/h",
                            "confidence": 0.8,
                            "related_track_id": track.track_id,
                            "metadata": {"speed": track.speed, "track_id": track.track_id}
                        })
            
            # Pose-based opportunities
            if analytics.moriarty and analytics.moriarty.pose_detected:
                if analytics.moriarty.biomechanics:
                    joint_angles = analytics.moriarty.biomechanics.joint_angles
                    
                    # Check for specific pose patterns
                    if "left_knee" in joint_angles and "right_knee" in joint_angles:
                        avg_knee_angle = (joint_angles["left_knee"] + joint_angles["right_knee"]) / 2
                        
                        if avg_knee_angle < 90:  # Deep squat/crouch
                            opportunities.append({
                                "stream_id": stream_id,
                                "timestamp": analytics.timestamp,
                                "opportunity_type": "pose_event",
                                "description": f"Deep crouch detected (avg knee angle: {avg_knee_angle:.1f}°)",
                                "confidence": 0.7,
                                "metadata": {"avg_knee_angle": avg_knee_angle}
                            })
            
            # Store opportunities in Redis
            for opportunity in opportunities:
                await self.redis_service.store_betting_opportunity(stream_id, opportunity)
                
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
            
            # Store alerts in Redis
            for alert in alerts:
                await self.redis_service.store_alert(stream_id, alert)
                
        except Exception as e:
            logger.error("Failed to check analytics alerts", error=str(e), stream_id=stream_id)
    
    async def get_stream_health(self, stream_id: str) -> Dict[str, Any]:
        """Get health status of stream processing"""
        is_processing = stream_id in self.active_streams
        is_core_active = await self._is_stream_active(stream_id)
        
        return {
            "stream_id": stream_id,
            "analytics_processing": is_processing,
            "core_service_active": is_core_active,
            "health_status": "healthy" if is_processing and is_core_active else "degraded"
        } 