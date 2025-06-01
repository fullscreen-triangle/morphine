import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json
import numpy as np
from pathlib import Path

# Import existing components
from .meta_orchestrator import MetaOrchestrator
from .rag_engine import RAGEngine
from .query_processor import QueryProcessor

logger = logging.getLogger(__name__)

@dataclass
class BiomechanicalAnnotation:
    """Detailed biomechanical annotation from Spectacular analysis"""
    session_id: str
    user_id: str
    timestamp: datetime
    
    # 3D model interactions
    clicked_joints: List[str]
    selected_muscles: List[str]
    interaction_sequence: List[Dict[str, Any]]
    
    # Movement analysis
    movement_type: str
    phase_annotations: Dict[str, Any]  # e.g., {"preparation": {...}, "execution": {...}}
    force_vectors: List[Dict[str, float]]
    angle_measurements: Dict[str, float]
    timing_analysis: Dict[str, float]
    
    # AI-generated insights
    pose_sequence: List[Dict[str, Any]]
    motion_quality_score: float
    technique_assessment: Dict[str, Any]
    
    # User's natural language analysis
    user_observations: List[str]
    predicted_outcome: str
    confidence_level: float
    reasoning: str

@dataclass
class PredictionEvent:
    """Links Spectacular analysis to real-world betting prediction"""
    prediction_id: str
    user_id: str
    annotation_session_id: str
    
    # Event details
    event_type: str  # "penalty_kick", "free_throw", "serve", etc.
    player_name: str
    match_id: str
    timestamp: datetime
    
    # Biomechanical prediction
    predicted_outcome: str
    prediction_details: Dict[str, Any]
    confidence_score: float
    biomechanical_reasoning: str
    
    # Betting information
    bet_amount: float
    odds: float
    bet_type: str
    
    # Validation (filled after event)
    actual_outcome: Optional[str] = None
    prediction_accuracy: Optional[float] = None
    validated: bool = False
    validation_timestamp: Optional[datetime] = None

@dataclass
class ValidatedTrainingData:
    """High-quality training data from successful predictions"""
    data_id: str
    user_id: str
    validation_score: float  # Based on betting success
    
    # Original analysis
    biomechanical_annotation: BiomechanicalAnnotation
    prediction_event: PredictionEvent
    
    # Quality metrics
    user_expertise_level: float
    historical_accuracy: float
    bet_success_rate: float
    
    # Enhanced annotations
    expert_verified: bool = False
    model_training_weight: float = 1.0
    annotation_quality_score: float = 0.0

class SpectacularMorphineBridge:
    """
    Bridge system that connects Spectacular's biomechanical analysis
    with Morphine's betting platform to create a revolutionary
    self-improving training data generation system.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.meta_orchestrator = MetaOrchestrator(config)
        self.rag_engine = RAGEngine(config)
        self.query_processor = QueryProcessor(config)
        
        # Data storage
        self.active_sessions: Dict[str, BiomechanicalAnnotation] = {}
        self.pending_predictions: Dict[str, PredictionEvent] = {}
        self.validated_data: List[ValidatedTrainingData] = []
        
        # Quality thresholds
        self.min_confidence_for_prediction = 0.6
        self.min_accuracy_for_training_data = 0.7
        self.expert_user_threshold = 0.8
        
        logger.info("Spectacular-Morphine Bridge initialized")
    
    async def capture_spectacular_session(self, session_data: Dict[str, Any]) -> str:
        """
        Capture a user's biomechanical analysis session in Spectacular.
        
        Args:
            session_data: Raw session data from Spectacular frontend
            
        Returns:
            session_id for tracking
        """
        try:
            # Parse session data into structured annotation
            annotation = BiomechanicalAnnotation(
                session_id=session_data["session_id"],
                user_id=session_data["user_id"],
                timestamp=datetime.fromisoformat(session_data["timestamp"]),
                clicked_joints=session_data.get("clicked_joints", []),
                selected_muscles=session_data.get("selected_muscles", []),
                interaction_sequence=session_data.get("interaction_sequence", []),
                movement_type=session_data.get("movement_type", "unknown"),
                phase_annotations=session_data.get("phase_annotations", {}),
                force_vectors=session_data.get("force_vectors", []),
                angle_measurements=session_data.get("angle_measurements", {}),
                timing_analysis=session_data.get("timing_analysis", {}),
                pose_sequence=session_data.get("pose_sequence", []),
                motion_quality_score=session_data.get("motion_quality_score", 0.0),
                technique_assessment=session_data.get("technique_assessment", {}),
                user_observations=session_data.get("user_observations", []),
                predicted_outcome=session_data.get("predicted_outcome", ""),
                confidence_level=session_data.get("confidence_level", 0.0),
                reasoning=session_data.get("reasoning", "")
            )
            
            # Store active session
            self.active_sessions[annotation.session_id] = annotation
            
            # Analyze the quality of the annotation
            quality_score = await self._assess_annotation_quality(annotation)
            
            logger.info(f"Captured Spectacular session {annotation.session_id} with quality score {quality_score}")
            
            return annotation.session_id
            
        except Exception as e:
            logger.error(f"Error capturing Spectacular session: {e}")
            raise
    
    async def link_prediction_to_betting(self, 
                                       session_id: str, 
                                       event_data: Dict[str, Any],
                                       betting_data: Dict[str, Any]) -> str:
        """
        Link a Spectacular analysis session to a real betting prediction.
        
        Args:
            session_id: ID of the Spectacular analysis session
            event_data: Real-world event being predicted
            betting_data: Betting information
            
        Returns:
            prediction_id for tracking
        """
        try:
            if session_id not in self.active_sessions:
                raise ValueError(f"Session {session_id} not found")
            
            annotation = self.active_sessions[session_id]
            
            # Create prediction event
            prediction = PredictionEvent(
                prediction_id=f"pred_{session_id}_{int(datetime.now().timestamp())}",
                user_id=annotation.user_id,
                annotation_session_id=session_id,
                event_type=event_data["event_type"],
                player_name=event_data["player_name"],
                match_id=event_data["match_id"],
                timestamp=datetime.fromisoformat(event_data["timestamp"]),
                predicted_outcome=annotation.predicted_outcome,
                prediction_details=event_data.get("prediction_details", {}),
                confidence_score=annotation.confidence_level,
                biomechanical_reasoning=annotation.reasoning,
                bet_amount=betting_data["amount"],
                odds=betting_data["odds"],
                bet_type=betting_data["bet_type"]
            )
            
            # Store pending prediction
            self.pending_predictions[prediction.prediction_id] = prediction
            
            # Check if prediction meets quality threshold
            if prediction.confidence_score >= self.min_confidence_for_prediction:
                await self._flag_high_quality_prediction(prediction)
            
            logger.info(f"Linked prediction {prediction.prediction_id} to betting system")
            
            return prediction.prediction_id
            
        except Exception as e:
            logger.error(f"Error linking prediction to betting: {e}")
            raise
    
    async def validate_prediction_outcome(self, 
                                        prediction_id: str, 
                                        actual_outcome: str,
                                        outcome_metadata: Dict[str, Any]) -> bool:
        """
        Validate a prediction against the actual outcome.
        
        Args:
            prediction_id: ID of the prediction to validate
            actual_outcome: What actually happened
            outcome_metadata: Additional outcome information
            
        Returns:
            True if prediction was accurate enough to generate training data
        """
        try:
            if prediction_id not in self.pending_predictions:
                logger.warning(f"Prediction {prediction_id} not found in pending")
                return False
            
            prediction = self.pending_predictions[prediction_id]
            annotation = self.active_sessions[prediction.annotation_session_id]
            
            # Calculate prediction accuracy
            accuracy = await self._calculate_prediction_accuracy(
                prediction.predicted_outcome, 
                actual_outcome, 
                outcome_metadata
            )
            
            # Update prediction with validation
            prediction.actual_outcome = actual_outcome
            prediction.prediction_accuracy = accuracy
            prediction.validated = True
            prediction.validation_timestamp = datetime.now()
            
            # If prediction was accurate enough, create training data
            if accuracy >= self.min_accuracy_for_training_data:
                await self._create_validated_training_data(prediction, annotation, accuracy)
                logger.info(f"Created training data from successful prediction {prediction_id}")
                return True
            else:
                logger.info(f"Prediction {prediction_id} not accurate enough for training data")
                return False
            
        except Exception as e:
            logger.error(f"Error validating prediction outcome: {e}")
            return False
    
    async def _create_validated_training_data(self, 
                                            prediction: PredictionEvent,
                                            annotation: BiomechanicalAnnotation,
                                            accuracy: float):
        """Create high-quality training data from successful prediction"""
        
        # Get user's historical performance
        user_stats = await self._get_user_expertise_stats(prediction.user_id)
        
        # Create validated training data
        training_data = ValidatedTrainingData(
            data_id=f"train_{prediction.prediction_id}",
            user_id=prediction.user_id,
            validation_score=accuracy,
            biomechanical_annotation=annotation,
            prediction_event=prediction,
            user_expertise_level=user_stats["expertise_level"],
            historical_accuracy=user_stats["historical_accuracy"],
            bet_success_rate=user_stats["bet_success_rate"],
            annotation_quality_score=await self._assess_annotation_quality(annotation)
        )
        
        # Calculate training weight based on user expertise and prediction quality
        training_data.model_training_weight = self._calculate_training_weight(training_data)
        
        # Store for model training
        self.validated_data.append(training_data)
        
        # If this is from an expert user, flag for additional verification
        if training_data.user_expertise_level >= self.expert_user_threshold:
            await self._flag_for_expert_verification(training_data)
    
    async def _assess_annotation_quality(self, annotation: BiomechanicalAnnotation) -> float:
        """Assess the quality of a biomechanical annotation"""
        
        quality_factors = {
            "interaction_depth": min(1.0, len(annotation.clicked_joints) / 10),
            "analysis_completeness": min(1.0, len(annotation.phase_annotations) / 5),
            "technical_detail": min(1.0, len(annotation.angle_measurements) / 8),
            "reasoning_quality": min(1.0, len(annotation.reasoning) / 200),
            "confidence_calibration": annotation.confidence_level,
            "time_spent": min(1.0, len(annotation.interaction_sequence) / 20)
        }
        
        # Weighted average
        weights = [0.2, 0.2, 0.15, 0.15, 0.15, 0.15]
        quality_score = sum(score * weight for score, weight in zip(quality_factors.values(), weights))
        
        return quality_score
    
    async def _calculate_prediction_accuracy(self, 
                                           predicted: str, 
                                           actual: str, 
                                           metadata: Dict[str, Any]) -> float:
        """Calculate how accurate a prediction was"""
        
        # Exact match
        if predicted.lower() == actual.lower():
            return 1.0
        
        # Semantic similarity for complex predictions
        if "details" in metadata:
            # Use AI to compare predicted vs actual biomechanical outcomes
            comparison_query = {
                "text": f"Compare predicted outcome '{predicted}' with actual outcome '{actual}' in biomechanical context",
                "predicted": predicted,
                "actual": actual,
                "metadata": metadata
            }
            
            similarity_result = await self.meta_orchestrator.process_query(comparison_query)
            return similarity_result.get("accuracy_score", 0.0)
        
        # Partial match scoring
        predicted_words = set(predicted.lower().split())
        actual_words = set(actual.lower().split())
        
        if predicted_words and actual_words:
            intersection = predicted_words.intersection(actual_words)
            union = predicted_words.union(actual_words)
            return len(intersection) / len(union)
        
        return 0.0
    
    async def _get_user_expertise_stats(self, user_id: str) -> Dict[str, float]:
        """Get user's historical performance statistics"""
        
        # Get user's prediction history
        user_predictions = [p for p in self.pending_predictions.values() 
                          if p.user_id == user_id and p.validated]
        
        if not user_predictions:
            return {
                "expertise_level": 0.5,
                "historical_accuracy": 0.5,
                "bet_success_rate": 0.5
            }
        
        # Calculate metrics
        accuracies = [p.prediction_accuracy for p in user_predictions if p.prediction_accuracy is not None]
        
        historical_accuracy = np.mean(accuracies) if accuracies else 0.5
        bet_success_rate = len([p for p in user_predictions if p.prediction_accuracy > 0.7]) / len(user_predictions)
        
        # Expertise is combination of accuracy and consistency
        expertise_level = (historical_accuracy * 0.7) + (bet_success_rate * 0.3)
        
        return {
            "expertise_level": expertise_level,
            "historical_accuracy": historical_accuracy,
            "bet_success_rate": bet_success_rate
        }
    
    def _calculate_training_weight(self, training_data: ValidatedTrainingData) -> float:
        """Calculate the weight this data should have in model training"""
        
        factors = {
            "validation_score": training_data.validation_score,
            "user_expertise": training_data.user_expertise_level,
            "annotation_quality": training_data.annotation_quality_score,
            "historical_success": training_data.bet_success_rate
        }
        
        # Higher weight for data from expert users with high-quality annotations
        weight = (
            factors["validation_score"] * 0.3 +
            factors["user_expertise"] * 0.3 +
            factors["annotation_quality"] * 0.2 +
            factors["historical_success"] * 0.2
        )
        
        return min(2.0, weight)  # Cap at 2x normal weight
    
    async def _flag_high_quality_prediction(self, prediction: PredictionEvent):
        """Flag high-quality predictions for special tracking"""
        logger.info(f"High-quality prediction flagged: {prediction.prediction_id}")
        # Could trigger additional monitoring or notification systems
    
    async def _flag_for_expert_verification(self, training_data: ValidatedTrainingData):
        """Flag training data from expert users for additional verification"""
        training_data.expert_verified = True
        logger.info(f"Training data flagged for expert verification: {training_data.data_id}")
    
    async def export_training_data(self, min_quality_score: float = 0.7) -> List[Dict[str, Any]]:
        """Export validated training data for model training"""
        
        high_quality_data = [
            data for data in self.validated_data 
            if data.validation_score >= min_quality_score
        ]
        
        return [asdict(data) for data in high_quality_data]
    
    async def get_system_statistics(self) -> Dict[str, Any]:
        """Get comprehensive system statistics"""
        
        total_sessions = len(self.active_sessions)
        total_predictions = len(self.pending_predictions)
        validated_predictions = len([p for p in self.pending_predictions.values() if p.validated])
        training_data_count = len(self.validated_data)
        
        avg_accuracy = np.mean([p.prediction_accuracy for p in self.pending_predictions.values() 
                               if p.prediction_accuracy is not None]) if validated_predictions > 0 else 0.0
        
        return {
            "total_spectacular_sessions": total_sessions,
            "total_predictions": total_predictions,
            "validated_predictions": validated_predictions,
            "training_data_generated": training_data_count,
            "average_prediction_accuracy": avg_accuracy,
            "system_learning_rate": training_data_count / max(1, total_predictions),
            "data_quality_metrics": {
                "high_quality_sessions": len([s for s in self.active_sessions.values() 
                                            if len(s.clicked_joints) >= 5]),
                "expert_users": len(set(d.user_id for d in self.validated_data 
                                      if d.user_expertise_level >= self.expert_user_threshold))
            }
        } 