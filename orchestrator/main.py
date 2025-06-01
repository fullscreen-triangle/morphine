import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import json
import time
from datetime import datetime, timedelta
import redis.asyncio as redis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ServiceStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

class StreamState(Enum):
    INACTIVE = "inactive"
    ACTIVATING = "activating"
    ACTIVE = "active"
    DEACTIVATING = "deactivating"
    ERROR = "error"

@dataclass
class ServiceHealth:
    service_name: str
    status: ServiceStatus
    response_time: float
    last_check: datetime
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None

@dataclass
class StreamMetrics:
    stream_id: str
    state: StreamState
    viewer_count: int
    analytics_fps: float
    detection_rate: float
    pose_detection_rate: float
    error_rate: float
    betting_activity: int
    last_update: datetime

@dataclass
class BettingOpportunity:
    stream_id: str
    opportunity_type: str
    confidence: float
    description: str
    metadata: Dict[str, Any]
    created_at: datetime
    expires_at: datetime

class MetacognitiveOrchestrator:
    """
    Metacognitive orchestrator that manages the entire Morphine platform,
    coordinating between services, making system-wide decisions, and optimizing performance.
    """
    
    def __init__(self):
        self.services = {
            "core": "http://core:8000",
            "analytics": "http://analytics:8080", 
            "api": "http://api:3000",
            "frontend": "http://frontend:3000"
        }
        
        self.service_health: Dict[str, ServiceHealth] = {}
        self.stream_metrics: Dict[str, StreamMetrics] = {}
        self.betting_opportunities: List[BettingOpportunity] = []
        
        self.redis_client: Optional[redis.Redis] = None
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Configuration
        self.health_check_interval = 30  # seconds
        self.metrics_collection_interval = 10  # seconds
        self.decision_making_interval = 5  # seconds
        
        # System state
        self.is_running = False
        self.total_processed_frames = 0
        self.system_start_time = datetime.now()
        
        # Decision thresholds
        self.max_concurrent_streams = 10
        self.min_analytics_fps = 15.0
        self.max_error_rate = 0.05
        self.betting_confidence_threshold = 0.7
        
    async def initialize(self):
        """Initialize the orchestrator"""
        try:
            # Initialize Redis connection
            self.redis_client = redis.Redis(
                host='redis',
                port=6379,
                decode_responses=True
            )
            await self.redis_client.ping()
            
            # Initialize HTTP session
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
            
            logger.info("Metacognitive Orchestrator initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")
            return False
    
    async def start(self):
        """Start the orchestrator main loop"""
        if not await self.initialize():
            logger.error("Failed to initialize, cannot start orchestrator")
            return
        
        self.is_running = True
        logger.info("Starting Metacognitive Orchestrator")
        
        # Start background tasks
        tasks = [
            asyncio.create_task(self.health_monitoring_loop()),
            asyncio.create_task(self.metrics_collection_loop()),
            asyncio.create_task(self.decision_making_loop()),
            asyncio.create_task(self.betting_opportunity_detection_loop())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("Orchestrator tasks cancelled")
        except Exception as e:
            logger.error(f"Error in orchestrator: {e}")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown the orchestrator"""
        self.is_running = False
        
        if self.session:
            await self.session.close()
        
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("Metacognitive Orchestrator shutdown complete")
    
    async def health_monitoring_loop(self):
        """Monitor health of all services"""
        while self.is_running:
            try:
                await self.check_all_services_health()
                await self.analyze_system_health()
                await asyncio.sleep(self.health_check_interval)
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(5)
    
    async def check_all_services_health(self):
        """Check health of all services"""
        tasks = []
        for service_name, service_url in self.services.items():
            tasks.append(self.check_service_health(service_name, service_url))
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def check_service_health(self, service_name: str, service_url: str):
        """Check health of a specific service"""
        start_time = time.time()
        
        try:
            async with self.session.get(f"{service_url}/health") as response:
                response_time = time.time() - start_time
                
                if response.status == 200:
                    data = await response.json()
                    status = ServiceStatus.HEALTHY
                    error_message = None
                    metadata = data
                elif response.status >= 500:
                    status = ServiceStatus.UNHEALTHY
                    error_message = f"HTTP {response.status}"
                    metadata = None
                else:
                    status = ServiceStatus.DEGRADED
                    error_message = f"HTTP {response.status}"
                    metadata = None
                
                self.service_health[service_name] = ServiceHealth(
                    service_name=service_name,
                    status=status,
                    response_time=response_time,
                    last_check=datetime.now(),
                    error_message=error_message,
                    metadata=metadata
                )
                
        except Exception as e:
            response_time = time.time() - start_time
            self.service_health[service_name] = ServiceHealth(
                service_name=service_name,
                status=ServiceStatus.UNHEALTHY,
                response_time=response_time,
                last_check=datetime.now(),
                error_message=str(e)
            )
    
    async def analyze_system_health(self):
        """Analyze overall system health and take corrective actions"""
        unhealthy_services = [
            name for name, health in self.service_health.items()
            if health.status == ServiceStatus.UNHEALTHY
        ]
        
        if len(unhealthy_services) > len(self.services) // 2:
            logger.critical("More than half of services are unhealthy!")
            await self.emergency_shutdown()
        
        elif unhealthy_services:
            logger.warning(f"Unhealthy services detected: {unhealthy_services}")
            await self.attempt_service_recovery(unhealthy_services)
    
    async def metrics_collection_loop(self):
        """Collect metrics from all streams and services"""
        while self.is_running:
            try:
                await self.collect_stream_metrics()
                await self.store_metrics()
                await asyncio.sleep(self.metrics_collection_interval)
            except Exception as e:
                logger.error(f"Error in metrics collection: {e}")
                await asyncio.sleep(5)
    
    async def collect_stream_metrics(self):
        """Collect metrics for all active streams"""
        try:
            # Get active streams from core service
            async with self.session.get(f"{self.services['core']}/api/streams") as response:
                if response.status == 200:
                    streams_data = await response.json()
                    
                    for stream in streams_data.get('data', []):
                        stream_id = stream['id']
                        await self.collect_single_stream_metrics(stream_id, stream)
        
        except Exception as e:
            logger.error(f"Error collecting stream metrics: {e}")
    
    async def collect_single_stream_metrics(self, stream_id: str, stream_data: Dict):
        """Collect metrics for a single stream"""
        try:
            # Get analytics metrics
            analytics_metrics = await self.get_analytics_metrics(stream_id)
            
            # Get betting activity
            betting_activity = await self.get_betting_activity(stream_id)
            
            # Calculate derived metrics
            state = StreamState(stream_data.get('status', 'inactive'))
            viewer_count = stream_data.get('viewer_count', 0)
            
            analytics_fps = analytics_metrics.get('fps', 0.0)
            detection_rate = analytics_metrics.get('detection_rate', 0.0)
            pose_detection_rate = analytics_metrics.get('pose_detection_rate', 0.0)
            error_rate = analytics_metrics.get('error_rate', 0.0)
            
            self.stream_metrics[stream_id] = StreamMetrics(
                stream_id=stream_id,
                state=state,
                viewer_count=viewer_count,
                analytics_fps=analytics_fps,
                detection_rate=detection_rate,
                pose_detection_rate=pose_detection_rate,
                error_rate=error_rate,
                betting_activity=betting_activity,
                last_update=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error collecting metrics for stream {stream_id}: {e}")
    
    async def get_analytics_metrics(self, stream_id: str) -> Dict[str, float]:
        """Get analytics metrics for a stream"""
        try:
            async with self.session.get(f"{self.services['analytics']}/api/analytics/{stream_id}/metrics") as response:
                if response.status == 200:
                    return await response.json()
                return {}
        except:
            return {}
    
    async def get_betting_activity(self, stream_id: str) -> int:
        """Get betting activity count for a stream"""
        try:
            async with self.session.get(f"{self.services['api']}/api/betting/stream/{stream_id}/activity") as response:
                if response.status == 200:
                    data = await response.json()
                    return len(data.get('data', {}).get('recent_bets', []))
                return 0
        except:
            return 0
    
    async def decision_making_loop(self):
        """Main decision-making loop for system optimization"""
        while self.is_running:
            try:
                await self.make_system_decisions()
                await asyncio.sleep(self.decision_making_interval)
            except Exception as e:
                logger.error(f"Error in decision making: {e}")
                await asyncio.sleep(5)
    
    async def make_system_decisions(self):
        """Make intelligent decisions about system operations"""
        # Resource optimization decisions
        await self.optimize_stream_allocation()
        
        # Performance tuning decisions
        await self.optimize_analytics_performance()
        
        # Quality control decisions
        await self.enforce_quality_standards()
        
        # Load balancing decisions
        await self.balance_system_load()
    
    async def optimize_stream_allocation(self):
        """Optimize stream resource allocation"""
        active_streams = [
            metrics for metrics in self.stream_metrics.values()
            if metrics.state == StreamState.ACTIVE
        ]
        
        # Check if we're approaching capacity limits
        if len(active_streams) >= self.max_concurrent_streams * 0.8:
            logger.warning("Approaching stream capacity limits")
            
            # Prioritize streams by viewer count and betting activity
            low_priority_streams = [
                stream for stream in active_streams
                if stream.viewer_count < 5 and stream.betting_activity < 2
            ]
            
            if low_priority_streams:
                # Consider deactivating low-priority streams
                stream_to_deactivate = min(low_priority_streams, key=lambda s: s.viewer_count)
                await self.deactivate_stream(stream_to_deactivate.stream_id, "Resource optimization")
    
    async def optimize_analytics_performance(self):
        """Optimize analytics performance based on metrics"""
        for stream_id, metrics in self.stream_metrics.items():
            if metrics.state == StreamState.ACTIVE:
                # Check if analytics FPS is too low
                if metrics.analytics_fps < self.min_analytics_fps:
                    logger.warning(f"Low analytics FPS for stream {stream_id}: {metrics.analytics_fps}")
                    await self.adjust_analytics_settings(stream_id, "reduce_quality")
                
                # Check if error rate is too high
                if metrics.error_rate > self.max_error_rate:
                    logger.warning(f"High error rate for stream {stream_id}: {metrics.error_rate}")
                    await self.adjust_analytics_settings(stream_id, "increase_robustness")
    
    async def enforce_quality_standards(self):
        """Enforce quality standards across all streams"""
        for stream_id, metrics in self.stream_metrics.items():
            if metrics.state == StreamState.ACTIVE:
                # Check detection quality
                if metrics.detection_rate < 0.5:  # Less than 50% detection rate
                    logger.warning(f"Low detection rate for stream {stream_id}: {metrics.detection_rate}")
                    # Could adjust detection thresholds or switch models
                
                # Check pose detection quality
                if metrics.pose_detection_rate < 0.3:  # Less than 30% pose detection
                    logger.warning(f"Low pose detection rate for stream {stream_id}: {metrics.pose_detection_rate}")
                    # Could adjust pose analysis settings
    
    async def betting_opportunity_detection_loop(self):
        """Detect and manage betting opportunities"""
        while self.is_running:
            try:
                await self.detect_betting_opportunities()
                await self.manage_betting_opportunities()
                await asyncio.sleep(2)  # More frequent for betting
            except Exception as e:
                logger.error(f"Error in betting opportunity detection: {e}")
                await asyncio.sleep(5)
    
    async def detect_betting_opportunities(self):
        """Detect betting opportunities from analytics data"""
        for stream_id, metrics in self.stream_metrics.items():
            if metrics.state == StreamState.ACTIVE and metrics.viewer_count > 0:
                # Get latest analytics data
                analytics_data = await self.get_latest_analytics(stream_id)
                
                if analytics_data:
                    opportunities = await self.analyze_for_betting_opportunities(stream_id, analytics_data)
                    
                    for opportunity in opportunities:
                        if opportunity.confidence >= self.betting_confidence_threshold:
                            self.betting_opportunities.append(opportunity)
                            await self.notify_betting_opportunity(opportunity)
    
    async def get_latest_analytics(self, stream_id: str) -> Optional[Dict]:
        """Get latest analytics data for a stream"""
        try:
            async with self.session.get(f"{self.services['analytics']}/api/analytics/{stream_id}/latest") as response:
                if response.status == 200:
                    return await response.json()
        except:
            pass
        return None
    
    async def analyze_for_betting_opportunities(self, stream_id: str, analytics_data: Dict) -> List[BettingOpportunity]:
        """Analyze analytics data for betting opportunities"""
        opportunities = []
        now = datetime.now()
        
        # Speed milestone opportunities
        vibrio_data = analytics_data.get('vibrio', {})
        tracks = vibrio_data.get('tracks', [])
        
        for track in tracks:
            speed = track.get('speed', 0)
            
            if speed > 10:  # High speed detected
                opportunity = BettingOpportunity(
                    stream_id=stream_id,
                    opportunity_type="speed_milestone",
                    confidence=min(speed / 20, 1.0),  # Confidence based on speed
                    description=f"High speed detected: {speed:.1f} units/sec",
                    metadata={"track_id": track.get('track_id'), "speed": speed},
                    created_at=now,
                    expires_at=now + timedelta(seconds=30)
                )
                opportunities.append(opportunity)
        
        # Pose event opportunities
        moriarty_data = analytics_data.get('moriarty', {})
        if moriarty_data.get('pose_detected'):
            biomechanics = moriarty_data.get('biomechanics', {})
            joint_angles = biomechanics.get('joint_angles', {})
            
            # Look for interesting joint angles (e.g., extreme positions)
            for joint, angle in joint_angles.items():
                if angle > 160 or angle < 20:  # Extreme angles
                    opportunity = BettingOpportunity(
                        stream_id=stream_id,
                        opportunity_type="pose_event",
                        confidence=0.8,
                        description=f"Extreme {joint} angle: {angle:.1f}°",
                        metadata={"joint": joint, "angle": angle},
                        created_at=now,
                        expires_at=now + timedelta(seconds=20)
                    )
                    opportunities.append(opportunity)
        
        return opportunities
    
    async def notify_betting_opportunity(self, opportunity: BettingOpportunity):
        """Notify about a new betting opportunity"""
        try:
            # Store in Redis for real-time access
            opportunity_data = asdict(opportunity)
            opportunity_data['created_at'] = opportunity.created_at.isoformat()
            opportunity_data['expires_at'] = opportunity.expires_at.isoformat()
            
            await self.redis_client.lpush(
                f"betting_opportunities:{opportunity.stream_id}",
                json.dumps(opportunity_data)
            )
            await self.redis_client.expire(f"betting_opportunities:{opportunity.stream_id}", 60)
            
            logger.info(f"New betting opportunity: {opportunity.description}")
            
        except Exception as e:
            logger.error(f"Error notifying betting opportunity: {e}")
    
    async def manage_betting_opportunities(self):
        """Manage and clean up expired betting opportunities"""
        now = datetime.now()
        
        # Remove expired opportunities
        self.betting_opportunities = [
            opp for opp in self.betting_opportunities
            if opp.expires_at > now
        ]
    
    async def store_metrics(self):
        """Store collected metrics in Redis"""
        try:
            # Store system metrics
            system_metrics = {
                "timestamp": datetime.now().isoformat(),
                "total_streams": len(self.stream_metrics),
                "active_streams": len([m for m in self.stream_metrics.values() if m.state == StreamState.ACTIVE]),
                "total_viewers": sum(m.viewer_count for m in self.stream_metrics.values()),
                "avg_analytics_fps": sum(m.analytics_fps for m in self.stream_metrics.values()) / len(self.stream_metrics) if self.stream_metrics else 0,
                "system_uptime": (datetime.now() - self.system_start_time).total_seconds()
            }
            
            await self.redis_client.lpush("system_metrics", json.dumps(system_metrics))
            await self.redis_client.ltrim("system_metrics", 0, 1000)  # Keep last 1000 entries
            
            # Store individual stream metrics
            for stream_id, metrics in self.stream_metrics.items():
                metrics_data = asdict(metrics)
                metrics_data['last_update'] = metrics.last_update.isoformat()
                
                await self.redis_client.hset(f"stream_metrics:{stream_id}", mapping=metrics_data)
                await self.redis_client.expire(f"stream_metrics:{stream_id}", 3600)  # 1 hour
            
        except Exception as e:
            logger.error(f"Error storing metrics: {e}")
    
    async def deactivate_stream(self, stream_id: str, reason: str):
        """Deactivate a stream"""
        try:
            async with self.session.post(f"{self.services['core']}/api/streams/{stream_id}/deactivate") as response:
                if response.status == 200:
                    logger.info(f"Deactivated stream {stream_id}: {reason}")
                else:
                    logger.error(f"Failed to deactivate stream {stream_id}")
        except Exception as e:
            logger.error(f"Error deactivating stream {stream_id}: {e}")
    
    async def adjust_analytics_settings(self, stream_id: str, adjustment_type: str):
        """Adjust analytics settings for a stream"""
        try:
            settings = {}
            
            if adjustment_type == "reduce_quality":
                settings = {"quality": "720p", "frame_rate": 20}
            elif adjustment_type == "increase_robustness":
                settings = {"detection_threshold": 0.3, "tracking_threshold": 0.7}
            
            async with self.session.patch(
                f"{self.services['analytics']}/api/analytics/{stream_id}/settings",
                json=settings
            ) as response:
                if response.status == 200:
                    logger.info(f"Adjusted analytics settings for stream {stream_id}: {adjustment_type}")
        
        except Exception as e:
            logger.error(f"Error adjusting analytics settings: {e}")
    
    async def balance_system_load(self):
        """Balance load across the system"""
        # Check service response times
        slow_services = [
            name for name, health in self.service_health.items()
            if health.response_time > 2.0  # More than 2 seconds
        ]
        
        if slow_services:
            logger.warning(f"Slow services detected: {slow_services}")
            # Could implement load balancing logic here
    
    async def attempt_service_recovery(self, unhealthy_services: List[str]):
        """Attempt to recover unhealthy services"""
        for service_name in unhealthy_services:
            logger.info(f"Attempting recovery for service: {service_name}")
            # Could implement service restart logic here
    
    async def emergency_shutdown(self):
        """Emergency shutdown procedure"""
        logger.critical("Initiating emergency shutdown")
        
        # Deactivate all streams
        for stream_id in self.stream_metrics.keys():
            await self.deactivate_stream(stream_id, "Emergency shutdown")
        
        # Store critical state information
        await self.store_emergency_state()
    
    async def store_emergency_state(self):
        """Store critical state information during emergency"""
        try:
            emergency_state = {
                "timestamp": datetime.now().isoformat(),
                "active_streams": list(self.stream_metrics.keys()),
                "service_health": {name: asdict(health) for name, health in self.service_health.items()},
                "betting_opportunities": len(self.betting_opportunities)
            }
            
            await self.redis_client.set("emergency_state", json.dumps(emergency_state))
            logger.info("Emergency state saved")
            
        except Exception as e:
            logger.error(f"Failed to save emergency state: {e}")

async def main():
    """Main entry point"""
    orchestrator = MetacognitiveOrchestrator()
    
    try:
        await orchestrator.start()
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"Orchestrator error: {e}")
    finally:
        await orchestrator.shutdown()

if __name__ == "__main__":
    asyncio.run(main()) 