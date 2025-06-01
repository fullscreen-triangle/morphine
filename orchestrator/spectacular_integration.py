import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import json
import websockets
from aiohttp import web, WSMsgType
import aioredis

from .spectacular_morphine_bridge import SpectacularMorphineBridge
from .meta_orchestrator import MetaOrchestrator

logger = logging.getLogger(__name__)

class SpectacularIntegration:
    """
    Integration layer that creates the revolutionary feedback loop:
    Spectacular Analysis → Prediction → Betting → Validation → Training Data
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.bridge = SpectacularMorphineBridge(config)
        self.meta_orchestrator = MetaOrchestrator(config)
        
        # Real-time connections
        self.websocket_connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.redis_client: Optional[aioredis.Redis] = None
        
        # Event handlers
        self.event_handlers = {
            "spectacular_session_started": self._handle_session_started,
            "biomechanical_analysis_completed": self._handle_analysis_completed,
            "prediction_made": self._handle_prediction_made,
            "bet_placed": self._handle_bet_placed,
            "event_outcome_received": self._handle_event_outcome,
            "training_data_generated": self._handle_training_data_generated
        }
        
        # Statistics tracking
        self.session_stats = {
            "total_sessions": 0,
            "successful_predictions": 0,
            "training_data_points": 0,
            "user_expertise_improvements": {}
        }
        
        logger.info("Spectacular Integration initialized")
    
    async def initialize(self):
        """Initialize the integration system"""
        try:
            # Initialize Redis for real-time communication
            self.redis_client = await aioredis.from_url(
                self.config.get("redis_url", "redis://localhost:6379")
            )
            
            # Subscribe to real-time events
            await self._setup_event_subscriptions()
            
            logger.info("Spectacular Integration initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Spectacular Integration: {e}")
            return False
    
    async def _setup_event_subscriptions(self):
        """Setup Redis subscriptions for real-time events"""
        pubsub = self.redis_client.pubsub()
        
        # Subscribe to key event channels
        await pubsub.subscribe(
            "spectacular:session_events",
            "spectacular:analysis_events", 
            "morphine:betting_events",
            "morphine:outcome_events"
        )
        
        # Start listening for events
        asyncio.create_task(self._event_listener(pubsub))
    
    async def _event_listener(self, pubsub):
        """Listen for events and route them to appropriate handlers"""
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        event_data = json.loads(message["data"])
                        event_type = event_data.get("event_type")
                        
                        if event_type in self.event_handlers:
                            await self.event_handlers[event_type](event_data)
                        else:
                            logger.warning(f"Unknown event type: {event_type}")
                            
                    except Exception as e:
                        logger.error(f"Error processing event: {e}")
                        
        except Exception as e:
            logger.error(f"Error in event listener: {e}")
    
    async def _handle_session_started(self, event_data: Dict[str, Any]):
        """Handle when a user starts a Spectacular analysis session"""
        session_id = event_data["session_id"]
        user_id = event_data["user_id"]
        
        logger.info(f"Spectacular session started: {session_id} by user {user_id}")
        
        # Track session start
        self.session_stats["total_sessions"] += 1
        
        # Notify user's connected clients
        await self._notify_user_clients(user_id, {
            "type": "session_started",
            "session_id": session_id,
            "message": "Biomechanical analysis session started"
        })
    
    async def _handle_analysis_completed(self, event_data: Dict[str, Any]):
        """Handle when biomechanical analysis is completed in Spectacular"""
        session_data = event_data["session_data"]
        
        try:
            # Capture the session through the bridge
            session_id = await self.bridge.capture_spectacular_session(session_data)
            
            # Analyze the session for prediction potential
            analysis_quality = await self._analyze_session_quality(session_data)
            
            # If high quality, suggest making a prediction
            if analysis_quality["prediction_ready"]:
                await self._suggest_prediction_opportunity(session_data, analysis_quality)
            
            logger.info(f"Analysis completed for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error handling analysis completion: {e}")
    
    async def _handle_prediction_made(self, event_data: Dict[str, Any]):
        """Handle when user makes a prediction based on their analysis"""
        session_id = event_data["session_id"]
        prediction_data = event_data["prediction_data"]
        
        logger.info(f"Prediction made for session {session_id}")
        
        # Store prediction for when betting occurs
        await self.redis_client.setex(
            f"prediction:{session_id}",
            3600,  # 1 hour expiry
            json.dumps(prediction_data)
        )
        
        # Notify user about prediction recording
        await self._notify_user_clients(event_data["user_id"], {
            "type": "prediction_recorded",
            "session_id": session_id,
            "confidence": prediction_data.get("confidence_level", 0.0),
            "message": "Your biomechanical prediction has been recorded"
        })
    
    async def _handle_bet_placed(self, event_data: Dict[str, Any]):
        """Handle when user places a bet based on their prediction"""
        try:
            bet_data = event_data["bet_data"]
            user_id = bet_data["user_id"]
            
            # Find matching prediction session
            prediction_key = None
            for key in await self.redis_client.keys("prediction:*"):
                stored_prediction = json.loads(await self.redis_client.get(key))
                if (stored_prediction["user_id"] == user_id and 
                    stored_prediction["event_type"] == bet_data["event_type"]):
                    prediction_key = key
                    break
            
            if prediction_key:
                session_id = prediction_key.split(":")[1]
                stored_prediction = json.loads(await self.redis_client.get(prediction_key))
                
                # Link prediction to betting through the bridge
                prediction_id = await self.bridge.link_prediction_to_betting(
                    session_id,
                    bet_data["event_data"],
                    bet_data["betting_data"]
                )
                
                # Store bet reference for outcome validation
                await self.redis_client.setex(
                    f"bet:{bet_data['bet_id']}",
                    86400,  # 24 hours
                    json.dumps({
                        "prediction_id": prediction_id,
                        "session_id": session_id,
                        "user_id": user_id
                    })
                )
                
                logger.info(f"Bet linked to prediction: {prediction_id}")
                
                # Notify user about successful linking
                await self._notify_user_clients(user_id, {
                    "type": "bet_linked",
                    "bet_id": bet_data["bet_id"],
                    "prediction_id": prediction_id,
                    "message": "Your bet has been linked to your biomechanical analysis"
                })
            
        except Exception as e:
            logger.error(f"Error handling bet placement: {e}")
    
    async def _handle_event_outcome(self, event_data: Dict[str, Any]):
        """Handle when real-world event outcome is received"""
        try:
            outcome_data = event_data["outcome_data"]
            bet_ids = outcome_data.get("related_bet_ids", [])
            
            for bet_id in bet_ids:
                bet_key = f"bet:{bet_id}"
                bet_info = await self.redis_client.get(bet_key)
                
                if bet_info:
                    bet_info = json.loads(bet_info)
                    prediction_id = bet_info["prediction_id"]
                    
                    # Validate prediction outcome through the bridge
                    training_data_created = await self.bridge.validate_prediction_outcome(
                        prediction_id,
                        outcome_data["actual_outcome"],
                        outcome_data.get("metadata", {})
                    )
                    
                    if training_data_created:
                        self.session_stats["training_data_points"] += 1
                        self.session_stats["successful_predictions"] += 1
                        
                        # Update user expertise tracking
                        user_id = bet_info["user_id"]
                        if user_id not in self.session_stats["user_expertise_improvements"]:
                            self.session_stats["user_expertise_improvements"][user_id] = 0
                        self.session_stats["user_expertise_improvements"][user_id] += 1
                        
                        # Notify about training data generation
                        await self._notify_training_data_generated(bet_info, outcome_data)
                    
                    logger.info(f"Outcome validated for prediction {prediction_id}")
            
        except Exception as e:
            logger.error(f"Error handling event outcome: {e}")
    
    async def _handle_training_data_generated(self, event_data: Dict[str, Any]):
        """Handle when new training data is generated from successful predictions"""
        training_data = event_data["training_data"]
        
        # Trigger model retraining if enough new data accumulated
        if self.session_stats["training_data_points"] % 100 == 0:
            await self._trigger_model_retraining()
        
        logger.info(f"Training data generated: {training_data['data_id']}")
    
    async def _analyze_session_quality(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the quality of a Spectacular session for prediction potential"""
        
        quality_indicators = {
            "detailed_analysis": len(session_data.get("clicked_joints", [])) >= 5,
            "movement_understanding": bool(session_data.get("phase_annotations")),
            "technical_depth": len(session_data.get("angle_measurements", {})) >= 3,
            "confidence_level": session_data.get("confidence_level", 0.0) >= 0.6,
            "reasoning_provided": len(session_data.get("reasoning", "")) >= 50
        }
        
        prediction_ready = sum(quality_indicators.values()) >= 3
        quality_score = sum(quality_indicators.values()) / len(quality_indicators)
        
        return {
            "prediction_ready": prediction_ready,
            "quality_score": quality_score,
            "quality_indicators": quality_indicators,
            "recommended_action": "make_prediction" if prediction_ready else "continue_analysis"
        }
    
    async def _suggest_prediction_opportunity(self, session_data: Dict[str, Any], quality: Dict[str, Any]):
        """Suggest prediction opportunities to users with high-quality analysis"""
        
        user_id = session_data["user_id"]
        movement_type = session_data.get("movement_type", "unknown")
        
        # Find upcoming events matching the analyzed movement
        upcoming_events = await self._find_matching_events(movement_type)
        
        if upcoming_events:
            await self._notify_user_clients(user_id, {
                "type": "prediction_opportunity",
                "session_id": session_data["session_id"],
                "quality_score": quality["quality_score"],
                "upcoming_events": upcoming_events[:3],  # Top 3 matches
                "message": f"Your {movement_type} analysis is ready for prediction! Found {len(upcoming_events)} matching events."
            })
    
    async def _find_matching_events(self, movement_type: str) -> List[Dict[str, Any]]:
        """Find upcoming sports events that match the analyzed movement type"""
        
        # Query events database/API for matching events
        # This would integrate with sports data providers
        
        # Mock implementation - in reality this would query real sports APIs
        mock_events = [
            {
                "event_id": "match_123",
                "event_type": movement_type,
                "player_name": "Lionel Messi",
                "match_name": "Barcelona vs Real Madrid",
                "start_time": "2024-01-15T20:00:00Z",
                "betting_markets": ["penalty_outcome", "free_kick_result"]
            }
        ]
        
        return mock_events
    
    async def _notify_user_clients(self, user_id: str, message: Dict[str, Any]):
        """Send real-time notifications to user's connected clients"""
        
        # Find user's WebSocket connections
        user_connections = [
            conn for conn_id, conn in self.websocket_connections.items()
            if conn_id.startswith(f"user:{user_id}:")
        ]
        
        for connection in user_connections:
            try:
                await connection.send(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending notification to user {user_id}: {e}")
        
        # Also store in Redis for mobile/offline clients
        await self.redis_client.lpush(
            f"notifications:{user_id}",
            json.dumps({**message, "timestamp": datetime.now().isoformat()})
        )
        
        # Keep only last 50 notifications
        await self.redis_client.ltrim(f"notifications:{user_id}", 0, 49)
    
    async def _notify_training_data_generated(self, bet_info: Dict[str, Any], outcome_data: Dict[str, Any]):
        """Notify about successful training data generation"""
        
        user_id = bet_info["user_id"]
        
        await self._notify_user_clients(user_id, {
            "type": "training_contribution",
            "prediction_id": bet_info["prediction_id"],
            "message": "Congratulations! Your successful prediction contributed to improving the AI models.",
            "expertise_level": "increasing",
            "contribution_impact": "Your biomechanical analysis is now part of the training dataset"
        })
        
        # Also notify system administrators
        logger.info(f"Training data generated from user {user_id} successful prediction")
    
    async def _trigger_model_retraining(self):
        """Trigger model retraining when sufficient new data is available"""
        
        logger.info("Triggering model retraining with new validated data")
        
        # Export training data from bridge
        training_data = await self.bridge.export_training_data(min_quality_score=0.7)
        
        # Trigger retraining process (would integrate with ML pipeline)
        await self.redis_client.publish("ml_pipeline:retrain", json.dumps({
            "trigger": "new_training_data",
            "data_count": len(training_data),
            "timestamp": datetime.now().isoformat()
        }))
    
    async def get_integration_statistics(self) -> Dict[str, Any]:
        """Get comprehensive integration statistics"""
        
        bridge_stats = await self.bridge.get_system_statistics()
        
        return {
            **self.session_stats,
            **bridge_stats,
            "active_connections": len(self.websocket_connections),
            "system_learning_efficiency": (
                self.session_stats["training_data_points"] / 
                max(1, self.session_stats["total_sessions"])
            ),
            "user_engagement_metrics": {
                "active_analysts": len(self.session_stats["user_expertise_improvements"]),
                "expert_contributors": len([
                    u for u, count in self.session_stats["user_expertise_improvements"].items()
                    if count >= 5
                ])
            }
        }
    
    # WebSocket handler for real-time communication
    async def websocket_handler(self, request):
        """Handle WebSocket connections for real-time communication"""
        
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        # Extract user info from connection
        user_id = request.headers.get("X-User-ID")
        if not user_id:
            await ws.close(code=4001, message="Missing user ID")
            return ws
        
        connection_id = f"user:{user_id}:{datetime.now().timestamp()}"
        self.websocket_connections[connection_id] = ws
        
        try:
            # Send any pending notifications
            notifications = await self.redis_client.lrange(f"notifications:{user_id}", 0, -1)
            for notification in notifications:
                await ws.send_str(notification)
            
            # Listen for messages
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self._handle_websocket_message(user_id, data)
                    except Exception as e:
                        logger.error(f"Error handling WebSocket message: {e}")
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
                    
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
        finally:
            if connection_id in self.websocket_connections:
                del self.websocket_connections[connection_id]
        
        return ws
    
    async def _handle_websocket_message(self, user_id: str, message: Dict[str, Any]):
        """Handle incoming WebSocket messages from clients"""
        
        message_type = message.get("type")
        
        if message_type == "ping":
            # Respond to ping
            await self._notify_user_clients(user_id, {"type": "pong"})
            
        elif message_type == "get_session_stats":
            # Send current session statistics
            stats = await self.get_integration_statistics()
            await self._notify_user_clients(user_id, {
                "type": "session_stats",
                "stats": stats
            })
            
        elif message_type == "request_prediction_suggestions":
            # Find prediction opportunities for user
            session_id = message.get("session_id")
            if session_id and session_id in self.bridge.active_sessions:
                session_data = self.bridge.active_sessions[session_id]
                quality = await self._analyze_session_quality(asdict(session_data))
                await self._suggest_prediction_opportunity(asdict(session_data), quality)
        
        else:
            logger.warning(f"Unknown WebSocket message type: {message_type}") 