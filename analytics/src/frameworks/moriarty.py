import cv2
import numpy as np
import time
from typing import Dict, Any, Optional, Tuple
import logging

from ..moriarty.pose_analyzer import PoseAnalyzer
from ..models.analytics import (
    Landmark, BiomechanicsResult, MoriartyResult
)

logger = logging.getLogger(__name__)

class PoseEventDetector:
    """Detects specific pose events and patterns"""
    
    def __init__(self):
        self.event_history = []
        self.event_thresholds = {
            'high_kick': {'joint': 'left_knee', 'min_angle': 120},
            'squat': {'joint': 'left_knee', 'max_angle': 70},
            'jump': {'center_of_mass_threshold': 50},  # Vertical displacement
            'arm_raise': {'joint': 'left_shoulder', 'min_angle': 90}
        }
        
    def detect_events(self, landmarks: Dict[str, Landmark], biomechanics: BiomechanicsResult) -> Dict[str, Any]:
        """Detect pose events in the current frame"""
        events = {}
        
        # High kick detection
        if 'left_knee' in biomechanics.joint_angles:
            knee_angle = biomechanics.joint_angles['left_knee']
            if knee_angle > self.event_thresholds['high_kick']['min_angle']:
                events['high_kick'] = {
                    'detected': True,
                    'confidence': min((knee_angle - 120) / 60, 1.0),
                    'angle': knee_angle
                }
        
        # Squat detection
        if 'left_knee' in biomechanics.joint_angles and 'right_knee' in biomechanics.joint_angles:
            left_knee = biomechanics.joint_angles['left_knee']
            right_knee = biomechanics.joint_angles['right_knee']
            avg_knee_angle = (left_knee + right_knee) / 2
            
            if avg_knee_angle < self.event_thresholds['squat']['max_angle']:
                events['squat'] = {
                    'detected': True,
                    'confidence': max(0, (70 - avg_knee_angle) / 70),
                    'avg_knee_angle': avg_knee_angle
                }
        
        # Jump detection (simplified - based on center of mass height)
        if biomechanics.center_of_mass:
            com_y = biomechanics.center_of_mass[1]
            # Simple heuristic: if center of mass is in upper part of frame
            if com_y < 200:  # Assuming typical frame height
                events['jump'] = {
                    'detected': True,
                    'confidence': max(0, (200 - com_y) / 200),
                    'center_of_mass_y': com_y
                }
        
        # Arm raise detection
        if 'left_shoulder' in biomechanics.joint_angles:
            shoulder_angle = biomechanics.joint_angles['left_shoulder']
            if shoulder_angle > self.event_thresholds['arm_raise']['min_angle']:
                events['arm_raise'] = {
                    'detected': True,
                    'confidence': min((shoulder_angle - 90) / 90, 1.0),
                    'angle': shoulder_angle
                }
        
        return events

class MovementClassifier:
    """Classifies movement patterns and activities"""
    
    def __init__(self):
        self.movement_history = []
        self.classification_window = 30  # frames
        
    def classify_movement(self, biomechanics: BiomechanicsResult, pose_quality: float) -> Dict[str, Any]:
        """Classify the current movement pattern"""
        classification = {
            'activity': 'unknown',
            'confidence': 0.0,
            'movement_intensity': 'low',
            'symmetry_score': 0.0
        }
        
        if pose_quality < 0.5:  # Poor pose quality
            return classification
        
        # Calculate movement intensity based on velocities
        if biomechanics.velocities:
            velocity_magnitudes = []
            for joint, velocity in biomechanics.velocities.items():
                magnitude = np.linalg.norm(velocity)
                velocity_magnitudes.append(magnitude)
            
            if velocity_magnitudes:
                avg_velocity = np.mean(velocity_magnitudes)
                max_velocity = np.max(velocity_magnitudes)
                
                # Classify movement intensity
                if avg_velocity < 5:
                    classification['movement_intensity'] = 'low'
                elif avg_velocity < 15:
                    classification['movement_intensity'] = 'medium'
                else:
                    classification['movement_intensity'] = 'high'
        
        # Calculate symmetry score (compare left and right side angles)
        symmetry_scores = []
        joint_pairs = [
            ('left_shoulder', 'right_shoulder'),
            ('left_elbow', 'right_elbow'),
            ('left_hip', 'right_hip'),
            ('left_knee', 'right_knee')
        ]
        
        for left_joint, right_joint in joint_pairs:
            if left_joint in biomechanics.joint_angles and right_joint in biomechanics.joint_angles:
                left_angle = biomechanics.joint_angles[left_joint]
                right_angle = biomechanics.joint_angles[right_joint]
                
                # Calculate symmetry (1.0 = perfect symmetry)
                angle_diff = abs(left_angle - right_angle)
                symmetry = max(0, 1.0 - (angle_diff / 180))
                symmetry_scores.append(symmetry)
        
        if symmetry_scores:
            classification['symmetry_score'] = np.mean(symmetry_scores)
        
        # Simple activity classification based on joint angles and movement
        joint_angles = biomechanics.joint_angles
        
        # Walking/Running detection
        if 'left_hip' in joint_angles and 'right_hip' in joint_angles:
            hip_movement = abs(joint_angles['left_hip'] - joint_angles['right_hip'])
            if hip_movement > 20 and classification['movement_intensity'] in ['medium', 'high']:
                classification['activity'] = 'walking' if classification['movement_intensity'] == 'medium' else 'running'
                classification['confidence'] = min(hip_movement / 60, 1.0)
        
        # Exercise detection
        if 'left_knee' in joint_angles and 'right_knee' in joint_angles:
            avg_knee_angle = (joint_angles['left_knee'] + joint_angles['right_knee']) / 2
            if avg_knee_angle < 70:  # Deep knee bend
                classification['activity'] = 'squatting'
                classification['confidence'] = (70 - avg_knee_angle) / 70
        
        return classification

class MoriartyPipeline:
    """Complete Moriarty framework for pose and biomechanical analysis"""
    
    def __init__(self, complexity: int = 1, enable_biomechanics: bool = True):
        self.pose_analyzer = PoseAnalyzer(
            model_complexity=complexity,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.event_detector = PoseEventDetector()
        self.movement_classifier = MovementClassifier()
        self.enable_biomechanics = enable_biomechanics
        
    async def initialize(self):
        """Initialize the Moriarty pipeline"""
        # MediaPipe is initialized automatically
        logger.info("Moriarty pipeline initialized")
    
    async def analyze_frame(self, frame: np.ndarray, timestamp: float) -> MoriartyResult:
        """Complete pose analysis pipeline"""
        start_time = time.time()
        
        try:
            # 1. Pose detection and biomechanical analysis
            pose_detected, landmarks, biomechanics = self.pose_analyzer.analyze_pose(frame)
            
            if not pose_detected or not biomechanics:
                return MoriartyResult(
                    pose_detected=False,
                    landmarks={},
                    biomechanics=BiomechanicsResult(
                        joint_angles={},
                        velocities={},
                        center_of_mass=None
                    ),
                    pose_quality_score=0.0
                )
            
            # 2. Calculate pose quality score
            pose_quality = self.pose_analyzer.get_pose_quality_score(landmarks)
            
            # 3. Event detection
            events = self.event_detector.detect_events(landmarks, biomechanics)
            
            # 4. Movement classification
            movement_classification = self.movement_classifier.classify_movement(biomechanics, pose_quality)
            
            # 5. Enhanced biomechanics with additional analysis
            enhanced_biomechanics = BiomechanicsResult(
                joint_angles=biomechanics.joint_angles,
                velocities=biomechanics.velocities,
                center_of_mass=biomechanics.center_of_mass
            )
            
            # Add additional analysis to biomechanics
            if hasattr(enhanced_biomechanics, 'events'):
                enhanced_biomechanics.events = events
            if hasattr(enhanced_biomechanics, 'movement_classification'):
                enhanced_biomechanics.movement_classification = movement_classification
            
            result = MoriartyResult(
                pose_detected=True,
                landmarks=landmarks,
                biomechanics=enhanced_biomechanics,
                pose_quality_score=pose_quality
            )
            
            # Add additional fields if the model supports them
            if hasattr(result, 'events'):
                result.events = events
            if hasattr(result, 'movement_classification'):
                result.movement_classification = movement_classification
            
            processing_time = time.time() - start_time
            logger.debug(f"Moriarty analysis complete in {processing_time:.3f}s, quality: {pose_quality:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Moriarty analysis failed: {e}")
            return MoriartyResult(
                pose_detected=False,
                landmarks={},
                biomechanics=BiomechanicsResult(
                    joint_angles={},
                    velocities={},
                    center_of_mass=None
                ),
                pose_quality_score=0.0
            )
    
    def draw_analysis(self, frame: np.ndarray, result: MoriartyResult) -> np.ndarray:
        """Draw pose analysis results on frame"""
        if not result.pose_detected:
            return frame
        
        annotated_frame = self.pose_analyzer.draw_pose(
            frame, 
            result.landmarks, 
            result.biomechanics.joint_angles
        )
        
        # Add additional annotations
        y_offset = 200
        
        # Quality score
        cv2.putText(annotated_frame, f"Pose Quality: {result.pose_quality_score:.2f}", 
                   (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        y_offset += 25
        
        # Center of mass
        if result.biomechanics.center_of_mass:
            com = result.biomechanics.center_of_mass
            cv2.circle(annotated_frame, (int(com[0]), int(com[1])), 8, (0, 255, 255), -1)
            cv2.putText(annotated_frame, f"COM: ({com[0]:.0f}, {com[1]:.0f})", 
                       (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            y_offset += 20
        
        # Display events if available
        if hasattr(result, 'events'):
            for event_name, event_data in result.events.items():
                if event_data.get('detected', False):
                    cv2.putText(annotated_frame, f"{event_name}: {event_data['confidence']:.2f}", 
                               (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    y_offset += 20
        
        return annotated_frame
    
    def reset(self):
        """Reset the pipeline state"""
        self.pose_analyzer.reset()
        self.event_detector.event_history.clear()
        self.movement_classifier.movement_history.clear()
        logger.info("Moriarty pipeline reset") 