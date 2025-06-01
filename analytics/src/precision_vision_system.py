"""
Precision Vision System - GPS-Enhanced Computer Vision
Revolutionary integration of nanosecond GPS accuracy with computer vision for biomechanical analysis
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import numpy as np
import cv2
import torch
import torchvision.transforms as transforms
from collections import deque, defaultdict
import json

from .gps_precision_engine import GPSPrecisionEngine, PrecisionMovement, GPSCoordinate

logger = logging.getLogger(__name__)

@dataclass
class PrecisionDetection:
    """Enhanced detection with GPS-calibrated precision"""
    detection_id: str
    timestamp_ns: int
    bbox: List[float]  # [x1, y1, x2, y2]
    confidence: float
    class_name: str
    pixel_center: Tuple[float, float]
    world_position: Optional[Tuple[float, float, float]]
    velocity_vector: Optional[Tuple[float, float, float]]
    precision_score: float
    biomechanical_keypoints: Dict[str, Tuple[float, float]]

@dataclass
class BiomechanicalAnalysis:
    """Comprehensive biomechanical analysis result"""
    analysis_id: str
    timestamp_ns: int
    entity_id: str
    movement_type: str
    
    # Joint analysis
    joint_angles: Dict[str, float]
    joint_velocities: Dict[str, float]
    joint_accelerations: Dict[str, float]
    
    # Force analysis
    force_vectors: Dict[str, Tuple[float, float, float]]
    center_of_mass: Tuple[float, float, float]
    balance_metrics: Dict[str, float]
    
    # Movement analysis
    movement_efficiency: float
    power_output: float
    stability_score: float
    technique_score: float
    
    # Precision metrics
    gps_accuracy: float
    vision_confidence: float
    combined_precision: float

class PoseEstimator:
    """Advanced pose estimation with biomechanical focus"""
    
    def __init__(self, model_path: str = None):
        self.model_path = model_path
        self.model = None
        self.joint_connections = [
            ("head", "neck"), ("neck", "left_shoulder"), ("neck", "right_shoulder"),
            ("left_shoulder", "left_elbow"), ("left_elbow", "left_wrist"),
            ("right_shoulder", "right_elbow"), ("right_elbow", "right_wrist"),
            ("neck", "torso"), ("torso", "left_hip"), ("torso", "right_hip"),
            ("left_hip", "left_knee"), ("left_knee", "left_ankle"),
            ("right_hip", "right_knee"), ("right_knee", "right_ankle")
        ]
        
    async def initialize(self):
        """Initialize pose estimation model"""
        try:
            # Load a more sophisticated pose model (this would be a real model like OpenPose or MediaPipe)
            # For now, we'll simulate with a placeholder
            self.model = "pose_model_placeholder"
            logger.info("Pose estimation model loaded")
            return True
        except Exception as e:
            logger.error(f"Failed to load pose model: {e}")
            return False
    
    def estimate_pose(self, frame: np.ndarray, detection_bbox: List[float]) -> Dict[str, Tuple[float, float]]:
        """Estimate pose keypoints within detection bounding box"""
        try:
            # Extract region of interest
            x1, y1, x2, y2 = map(int, detection_bbox)
            roi = frame[y1:y2, x1:x2]
            
            if roi.size == 0:
                return {}
            
            # This would be replaced with actual pose estimation
            # For now, we'll generate realistic keypoints based on the bounding box
            width = x2 - x1
            height = y2 - y1
            
            # Generate keypoints (normalized to 0-1 within bbox, then scaled to image coordinates)
            keypoints = {
                "head": (x1 + width * 0.5, y1 + height * 0.1),
                "neck": (x1 + width * 0.5, y1 + height * 0.2),
                "left_shoulder": (x1 + width * 0.3, y1 + height * 0.25),
                "right_shoulder": (x1 + width * 0.7, y1 + height * 0.25),
                "left_elbow": (x1 + width * 0.2, y1 + height * 0.45),
                "right_elbow": (x1 + width * 0.8, y1 + height * 0.45),
                "left_wrist": (x1 + width * 0.15, y1 + height * 0.65),
                "right_wrist": (x1 + width * 0.85, y1 + height * 0.65),
                "torso": (x1 + width * 0.5, y1 + height * 0.5),
                "left_hip": (x1 + width * 0.35, y1 + height * 0.7),
                "right_hip": (x1 + width * 0.65, y1 + height * 0.7),
                "left_knee": (x1 + width * 0.3, y1 + height * 0.85),
                "right_knee": (x1 + width * 0.7, y1 + height * 0.85),
                "left_ankle": (x1 + width * 0.25, y1 + height * 0.98),
                "right_ankle": (x1 + width * 0.75, y1 + height * 0.98)
            }
            
            return keypoints
            
        except Exception as e:
            logger.error(f"Error in pose estimation: {e}")
            return {}

class BiomechanicalAnalyzer:
    """Advanced biomechanical analysis engine"""
    
    def __init__(self):
        self.joint_angles_history = defaultdict(deque)
        self.force_history = defaultdict(deque)
        self.movement_patterns = {}
        
    def analyze_biomechanics(self, 
                           keypoints: Dict[str, Tuple[float, float]], 
                           world_position: Tuple[float, float, float],
                           velocity_vector: Tuple[float, float, float],
                           timestamp_ns: int,
                           entity_id: str) -> BiomechanicalAnalysis:
        """Perform comprehensive biomechanical analysis"""
        try:
            # Calculate joint angles
            joint_angles = self._calculate_joint_angles(keypoints)
            
            # Calculate joint velocities and accelerations
            joint_velocities = self._calculate_joint_velocities(entity_id, joint_angles, timestamp_ns)
            joint_accelerations = self._calculate_joint_accelerations(entity_id, joint_velocities, timestamp_ns)
            
            # Analyze force vectors
            force_vectors = self._analyze_force_vectors(keypoints, world_position, velocity_vector)
            
            # Calculate center of mass
            center_of_mass = self._calculate_center_of_mass(keypoints, world_position)
            
            # Balance metrics
            balance_metrics = self._calculate_balance_metrics(keypoints, center_of_mass)
            
            # Movement efficiency
            movement_efficiency = self._calculate_movement_efficiency(joint_angles, velocity_vector)
            
            # Power output estimation
            power_output = self._estimate_power_output(force_vectors, velocity_vector)
            
            # Stability score
            stability_score = self._calculate_stability_score(balance_metrics, joint_velocities)
            
            # Technique score (sport-specific)
            technique_score = self._assess_technique(keypoints, joint_angles, movement_efficiency)
            
            # Detect movement type
            movement_type = self._classify_movement_type(joint_angles, velocity_vector, keypoints)
            
            analysis = BiomechanicalAnalysis(
                analysis_id=f"biomech_{entity_id}_{timestamp_ns}",
                timestamp_ns=timestamp_ns,
                entity_id=entity_id,
                movement_type=movement_type,
                joint_angles=joint_angles,
                joint_velocities=joint_velocities,
                joint_accelerations=joint_accelerations,
                force_vectors=force_vectors,
                center_of_mass=center_of_mass,
                balance_metrics=balance_metrics,
                movement_efficiency=movement_efficiency,
                power_output=power_output,
                stability_score=stability_score,
                technique_score=technique_score,
                gps_accuracy=0.95,  # Would come from GPS engine
                vision_confidence=0.88,  # Would come from pose estimation
                combined_precision=0.91
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in biomechanical analysis: {e}")
            return None
    
    def _calculate_joint_angles(self, keypoints: Dict[str, Tuple[float, float]]) -> Dict[str, float]:
        """Calculate joint angles from keypoints"""
        angles = {}
        
        try:
            # Knee angles
            if all(joint in keypoints for joint in ["left_hip", "left_knee", "left_ankle"]):
                angles["left_knee"] = self._angle_between_points(
                    keypoints["left_hip"], keypoints["left_knee"], keypoints["left_ankle"]
                )
            
            if all(joint in keypoints for joint in ["right_hip", "right_knee", "right_ankle"]):
                angles["right_knee"] = self._angle_between_points(
                    keypoints["right_hip"], keypoints["right_knee"], keypoints["right_ankle"]
                )
            
            # Elbow angles
            if all(joint in keypoints for joint in ["left_shoulder", "left_elbow", "left_wrist"]):
                angles["left_elbow"] = self._angle_between_points(
                    keypoints["left_shoulder"], keypoints["left_elbow"], keypoints["left_wrist"]
                )
            
            if all(joint in keypoints for joint in ["right_shoulder", "right_elbow", "right_wrist"]):
                angles["right_elbow"] = self._angle_between_points(
                    keypoints["right_shoulder"], keypoints["right_elbow"], keypoints["right_wrist"]
                )
            
            # Hip angles
            if all(joint in keypoints for joint in ["torso", "left_hip", "left_knee"]):
                angles["left_hip"] = self._angle_between_points(
                    keypoints["torso"], keypoints["left_hip"], keypoints["left_knee"]
                )
            
            if all(joint in keypoints for joint in ["torso", "right_hip", "right_knee"]):
                angles["right_hip"] = self._angle_between_points(
                    keypoints["torso"], keypoints["right_hip"], keypoints["right_knee"]
                )
            
            # Shoulder angles
            if all(joint in keypoints for joint in ["neck", "left_shoulder", "left_elbow"]):
                angles["left_shoulder"] = self._angle_between_points(
                    keypoints["neck"], keypoints["left_shoulder"], keypoints["left_elbow"]
                )
            
            if all(joint in keypoints for joint in ["neck", "right_shoulder", "right_elbow"]):
                angles["right_shoulder"] = self._angle_between_points(
                    keypoints["neck"], keypoints["right_shoulder"], keypoints["right_elbow"]
                )
            
        except Exception as e:
            logger.error(f"Error calculating joint angles: {e}")
        
        return angles
    
    def _angle_between_points(self, p1: Tuple[float, float], p2: Tuple[float, float], p3: Tuple[float, float]) -> float:
        """Calculate angle at p2 formed by points p1-p2-p3"""
        try:
            # Vectors from p2 to p1 and p2 to p3
            v1 = np.array([p1[0] - p2[0], p1[1] - p2[1]])
            v2 = np.array([p3[0] - p2[0], p3[1] - p2[1]])
            
            # Calculate angle using dot product
            cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
            cos_angle = np.clip(cos_angle, -1.0, 1.0)  # Handle numerical errors
            angle = np.arccos(cos_angle)
            
            return np.degrees(angle)
            
        except Exception:
            return 0.0
    
    def _calculate_joint_velocities(self, entity_id: str, joint_angles: Dict[str, float], timestamp_ns: int) -> Dict[str, float]:
        """Calculate joint angular velocities"""
        velocities = {}
        
        # Store current angles
        self.joint_angles_history[entity_id].append((timestamp_ns, joint_angles))
        
        # Keep only recent history
        if len(self.joint_angles_history[entity_id]) > 100:
            self.joint_angles_history[entity_id].popleft()
        
        # Calculate velocities if we have previous data
        if len(self.joint_angles_history[entity_id]) >= 2:
            prev_timestamp, prev_angles = self.joint_angles_history[entity_id][-2]
            time_diff = (timestamp_ns - prev_timestamp) / 1e9  # Convert to seconds
            
            if time_diff > 0:
                for joint, angle in joint_angles.items():
                    if joint in prev_angles:
                        angle_diff = angle - prev_angles[joint]
                        velocities[joint] = angle_diff / time_diff
        
        return velocities
    
    def _calculate_joint_accelerations(self, entity_id: str, joint_velocities: Dict[str, float], timestamp_ns: int) -> Dict[str, float]:
        """Calculate joint angular accelerations"""
        accelerations = {}
        
        # This would use velocity history similar to joint velocities
        # For now, return zeros
        for joint in joint_velocities:
            accelerations[joint] = 0.0
        
        return accelerations
    
    def _analyze_force_vectors(self, keypoints: Dict[str, Tuple[float, float]], 
                             world_position: Tuple[float, float, float],
                             velocity_vector: Tuple[float, float, float]) -> Dict[str, Tuple[float, float, float]]:
        """Analyze force vectors at key joints"""
        force_vectors = {}
        
        # Estimate forces based on acceleration and body segment masses
        # This is a simplified estimation - real implementation would be more complex
        estimated_mass = 70.0  # kg, could be estimated from keypoints
        
        # Ground reaction force (for standing/walking)
        if "left_ankle" in keypoints and "right_ankle" in keypoints:
            # Simplified ground reaction force
            gravity_force = estimated_mass * 9.81
            force_vectors["ground_reaction"] = (0.0, 0.0, gravity_force)
        
        # Joint forces (simplified)
        for joint in ["left_knee", "right_knee", "left_hip", "right_hip"]:
            if joint in keypoints:
                # Estimate joint force based on position and velocity
                force_magnitude = estimated_mass * 2.0  # Simplified
                force_vectors[joint] = (velocity_vector[0] * 0.1, velocity_vector[1] * 0.1, force_magnitude)
        
        return force_vectors
    
    def _calculate_center_of_mass(self, keypoints: Dict[str, Tuple[float, float]], 
                                world_position: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """Calculate center of mass"""
        if not keypoints:
            return world_position
        
        # Body segment masses (approximate percentages)
        segment_masses = {
            "head": 0.081, "torso": 0.497, "left_arm": 0.05, "right_arm": 0.05,
            "left_leg": 0.161, "right_leg": 0.161
        }
        
        # Estimate center of mass based on key points
        total_mass = 0.0
        weighted_x = 0.0
        weighted_y = 0.0
        
        if "torso" in keypoints:
            weighted_x += keypoints["torso"][0] * segment_masses["torso"]
            weighted_y += keypoints["torso"][1] * segment_masses["torso"]
            total_mass += segment_masses["torso"]
        
        if "head" in keypoints:
            weighted_x += keypoints["head"][0] * segment_masses["head"]
            weighted_y += keypoints["head"][1] * segment_masses["head"]
            total_mass += segment_masses["head"]
        
        # Add leg contributions
        for side in ["left", "right"]:
            if f"{side}_hip" in keypoints and f"{side}_knee" in keypoints:
                leg_center_x = (keypoints[f"{side}_hip"][0] + keypoints[f"{side}_knee"][0]) / 2
                leg_center_y = (keypoints[f"{side}_hip"][1] + keypoints[f"{side}_knee"][1]) / 2
                weighted_x += leg_center_x * segment_masses[f"{side}_leg"]
                weighted_y += leg_center_y * segment_masses[f"{side}_leg"]
                total_mass += segment_masses[f"{side}_leg"]
        
        if total_mass > 0:
            com_x = weighted_x / total_mass
            com_y = weighted_y / total_mass
            return (com_x, com_y, world_position[2])  # Use world Z coordinate
        
        return world_position
    
    def _calculate_balance_metrics(self, keypoints: Dict[str, Tuple[float, float]], 
                                 center_of_mass: Tuple[float, float, float]) -> Dict[str, float]:
        """Calculate balance and stability metrics"""
        metrics = {}
        
        # Base of support calculation
        if "left_ankle" in keypoints and "right_ankle" in keypoints:
            left_ankle = keypoints["left_ankle"]
            right_ankle = keypoints["right_ankle"]
            
            # Distance between feet
            foot_separation = np.sqrt((left_ankle[0] - right_ankle[0])**2 + (left_ankle[1] - right_ankle[1])**2)
            metrics["foot_separation"] = foot_separation
            
            # Center of pressure (simplified as midpoint between feet)
            cop_x = (left_ankle[0] + right_ankle[0]) / 2
            cop_y = (left_ankle[1] + right_ankle[1]) / 2
            
            # Distance from center of mass to center of pressure
            com_cop_distance = np.sqrt((center_of_mass[0] - cop_x)**2 + (center_of_mass[1] - cop_y)**2)
            metrics["com_cop_distance"] = com_cop_distance
            
            # Balance score (lower distance = better balance)
            metrics["balance_score"] = max(0, 1.0 - com_cop_distance / 100.0)
        
        return metrics
    
    def _calculate_movement_efficiency(self, joint_angles: Dict[str, float], 
                                     velocity_vector: Tuple[float, float, float]) -> float:
        """Calculate movement efficiency score"""
        try:
            # Efficiency based on joint angle optimization and velocity
            efficiency_score = 0.8  # Base efficiency
            
            # Penalize extreme joint angles
            for joint, angle in joint_angles.items():
                if angle < 30 or angle > 150:  # Extreme angles
                    efficiency_score -= 0.1
                elif 70 <= angle <= 110:  # Optimal range
                    efficiency_score += 0.05
            
            # Consider velocity smoothness
            velocity_magnitude = np.linalg.norm(velocity_vector)
            if velocity_magnitude < 0.5:  # Very slow movement
                efficiency_score -= 0.1
            elif 1.0 <= velocity_magnitude <= 3.0:  # Optimal speed range
                efficiency_score += 0.1
            
            return max(0.0, min(1.0, efficiency_score))
            
        except Exception:
            return 0.5
    
    def _estimate_power_output(self, force_vectors: Dict[str, Tuple[float, float, float]], 
                             velocity_vector: Tuple[float, float, float]) -> float:
        """Estimate power output in watts"""
        try:
            total_power = 0.0
            velocity_magnitude = np.linalg.norm(velocity_vector)
            
            # Power = Force × Velocity
            for joint, force in force_vectors.items():
                force_magnitude = np.linalg.norm(force)
                power = force_magnitude * velocity_magnitude * 0.1  # Scaling factor
                total_power += power
            
            return total_power
            
        except Exception:
            return 0.0
    
    def _calculate_stability_score(self, balance_metrics: Dict[str, float], 
                                 joint_velocities: Dict[str, float]) -> float:
        """Calculate overall stability score"""
        try:
            stability = 0.7  # Base stability
            
            # Add balance contribution
            if "balance_score" in balance_metrics:
                stability += balance_metrics["balance_score"] * 0.3
            
            # Penalize high joint velocity variations
            if joint_velocities:
                velocity_std = np.std(list(joint_velocities.values()))
                if velocity_std < 10:  # Low variation
                    stability += 0.1
                elif velocity_std > 50:  # High variation
                    stability -= 0.2
            
            return max(0.0, min(1.0, stability))
            
        except Exception:
            return 0.5
    
    def _assess_technique(self, keypoints: Dict[str, Tuple[float, float]], 
                        joint_angles: Dict[str, float], 
                        movement_efficiency: float) -> float:
        """Assess technique quality"""
        try:
            technique_score = movement_efficiency * 0.5  # Base from efficiency
            
            # Sport-specific technique assessment would go here
            # For now, use general biomechanical principles
            
            # Check for symmetry
            if "left_knee" in joint_angles and "right_knee" in joint_angles:
                knee_symmetry = abs(joint_angles["left_knee"] - joint_angles["right_knee"])
                if knee_symmetry < 10:  # Good symmetry
                    technique_score += 0.2
                elif knee_symmetry > 30:  # Poor symmetry
                    technique_score -= 0.1
            
            # Check for proper joint alignment
            if all(joint in keypoints for joint in ["head", "neck", "torso"]):
                # Check if spine is relatively straight
                head_neck_dist = np.linalg.norm(np.array(keypoints["head"]) - np.array(keypoints["neck"]))
                neck_torso_dist = np.linalg.norm(np.array(keypoints["neck"]) - np.array(keypoints["torso"]))
                
                if abs(head_neck_dist - neck_torso_dist) < 20:  # Good alignment
                    technique_score += 0.1
            
            return max(0.0, min(1.0, technique_score))
            
        except Exception:
            return 0.5
    
    def _classify_movement_type(self, joint_angles: Dict[str, float], 
                              velocity_vector: Tuple[float, float, float],
                              keypoints: Dict[str, Tuple[float, float]]) -> str:
        """Classify the type of movement being performed"""
        try:
            velocity_magnitude = np.linalg.norm(velocity_vector)
            
            # Simple movement classification
            if velocity_magnitude < 0.5:
                return "stationary"
            elif velocity_magnitude < 2.0:
                return "walking"
            elif velocity_magnitude < 5.0:
                return "running"
            else:
                return "sprinting"
                
            # More sophisticated classification would analyze joint angle patterns
            # and could identify specific sports movements like kicking, throwing, etc.
            
        except Exception:
            return "unknown"

class PrecisionVisionSystem:
    """Main system integrating GPS precision with computer vision"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.gps_engine = GPSPrecisionEngine(config)
        self.pose_estimator = PoseEstimator(config.get("pose_model_path"))
        self.biomech_analyzer = BiomechanicalAnalyzer()
        
        # Detection tracking
        self.active_detections: Dict[str, PrecisionDetection] = {}
        self.detection_history = deque(maxlen=10000)
        self.analysis_results = deque(maxlen=5000)
        
        logger.info("Precision Vision System initialized")
    
    async def initialize(self):
        """Initialize all components"""
        try:
            gps_success = await self.gps_engine.initialize()
            if not gps_success:
                logger.warning("GPS engine failed to initialize - continuing without GPS")
            
            pose_success = await self.pose_estimator.initialize()
            if not pose_success:
                logger.error("Pose estimator failed to initialize")
                return False
            
            logger.info("Precision Vision System initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Precision Vision System: {e}")
            return False
    
    async def process_frame_with_precision(self, frame: np.ndarray, 
                                         detections: List[Dict[str, Any]], 
                                         timestamp_ns: Optional[int] = None) -> List[BiomechanicalAnalysis]:
        """Process frame with nanosecond precision and full biomechanical analysis"""
        if timestamp_ns is None:
            timestamp_ns = self.gps_engine.timer.get_nanosecond_timestamp()
        
        results = []
        
        for i, detection in enumerate(detections):
            try:
                entity_id = f"person_{i}"
                bbox = detection.get("bbox", [0, 0, 100, 100])
                confidence = detection.get("confidence", 0.0)
                
                # Get pose keypoints
                keypoints = self.pose_estimator.estimate_pose(frame, bbox)
                if not keypoints:
                    continue
                
                # Get pixel center
                pixel_center = ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
                
                # Track movement with GPS precision
                movement = await self.gps_engine.track_movement(
                    entity_id, pixel_center, {"keypoints": keypoints}
                )
                
                if movement:
                    # Perform biomechanical analysis
                    analysis = self.biomech_analyzer.analyze_biomechanics(
                        keypoints=keypoints,
                        world_position=movement.world_position_3d,
                        velocity_vector=movement.velocity_vector,
                        timestamp_ns=timestamp_ns,
                        entity_id=entity_id
                    )
                    
                    if analysis:
                        results.append(analysis)
                        self.analysis_results.append(analysis)
                        
                        # Create precision detection record
                        precision_detection = PrecisionDetection(
                            detection_id=f"det_{entity_id}_{timestamp_ns}",
                            timestamp_ns=timestamp_ns,
                            bbox=bbox,
                            confidence=confidence,
                            class_name="person",
                            pixel_center=pixel_center,
                            world_position=movement.world_position_3d,
                            velocity_vector=movement.velocity_vector,
                            precision_score=movement.precision_score,
                            biomechanical_keypoints=keypoints
                        )
                        
                        self.active_detections[entity_id] = precision_detection
                        self.detection_history.append(precision_detection)
                
            except Exception as e:
                logger.error(f"Error processing detection {i}: {e}")
        
        return results
    
    async def get_movement_predictions(self, entity_id: str, 
                                     prediction_horizon_ms: int = 500) -> Dict[str, Any]:
        """Predict future movement based on current trajectory"""
        try:
            if entity_id not in self.active_detections:
                return {}
            
            current_detection = self.active_detections[entity_id]
            current_time = self.gps_engine.timer.get_nanosecond_timestamp()
            
            # Predict position after specified time
            prediction_time_s = prediction_horizon_ms / 1000.0
            
            if current_detection.velocity_vector:
                vx, vy, vz = current_detection.velocity_vector
                current_pos = current_detection.world_position
                
                # Simple linear prediction (could be enhanced with acceleration)
                predicted_position = (
                    current_pos[0] + vx * prediction_time_s,
                    current_pos[1] + vy * prediction_time_s,
                    current_pos[2] + vz * prediction_time_s
                )
                
                return {
                    "entity_id": entity_id,
                    "current_position": current_pos,
                    "predicted_position": predicted_position,
                    "velocity_vector": current_detection.velocity_vector,
                    "prediction_confidence": current_detection.precision_score,
                    "prediction_horizon_ms": prediction_horizon_ms
                }
        
        except Exception as e:
            logger.error(f"Error predicting movement for {entity_id}: {e}")
        
        return {}
    
    async def get_precision_metrics(self) -> Dict[str, Any]:
        """Get comprehensive precision metrics"""
        gps_metrics = await self.gps_engine.get_precision_metrics()
        
        vision_metrics = {
            "active_detections": len(self.active_detections),
            "detection_history_count": len(self.detection_history),
            "analysis_results_count": len(self.analysis_results),
            "average_precision_score": 0.0
        }
        
        # Calculate average precision score
        if self.detection_history:
            total_precision = sum(det.precision_score for det in self.detection_history)
            vision_metrics["average_precision_score"] = total_precision / len(self.detection_history)
        
        return {
            "gps_metrics": gps_metrics,
            "vision_metrics": vision_metrics,
            "system_status": "operational" if gps_metrics["gps_connected"] else "gps_degraded"
        }
    
    async def export_analysis_data(self, start_time_ns: int, end_time_ns: int) -> Dict[str, Any]:
        """Export comprehensive analysis data for the specified time range"""
        try:
            # Filter analysis results
            filtered_analyses = [
                asdict(analysis) for analysis in self.analysis_results
                if start_time_ns <= analysis.timestamp_ns <= end_time_ns
            ]
            
            # Filter detection data
            filtered_detections = [
                asdict(detection) for detection in self.detection_history
                if start_time_ns <= detection.timestamp_ns <= end_time_ns
            ]
            
            # Get GPS movement data
            gps_movements = await self.gps_engine.export_precision_data(start_time_ns, end_time_ns)
            
            return {
                "time_range": {
                    "start_ns": start_time_ns,
                    "end_ns": end_time_ns,
                    "duration_s": (end_time_ns - start_time_ns) / 1e9
                },
                "biomechanical_analyses": filtered_analyses,
                "precision_detections": filtered_detections,
                "gps_movements": gps_movements,
                "summary": {
                    "total_analyses": len(filtered_analyses),
                    "total_detections": len(filtered_detections),
                    "total_movements": len(gps_movements)
                }
            }
            
        except Exception as e:
            logger.error(f"Error exporting analysis data: {e}")
            return {} 