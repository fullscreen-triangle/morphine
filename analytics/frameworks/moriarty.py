"""
Moriarty Framework - Sports Video Analysis
Framework for analyzing sports videos through computer vision and biomechanical principles.
"""

import asyncio
import time
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import cv2
import mediapipe as mp
from collections import deque, defaultdict
import math

import structlog

logger = structlog.get_logger(__name__)

class Pose:
    """Human pose representation"""
    def __init__(self, landmarks: Dict[str, Tuple[float, float, float]], frame_idx: int, timestamp: float):
        self.landmarks = landmarks  # {landmark_name: (x, y, visibility)}
        self.frame_idx = frame_idx
        self.timestamp = timestamp
        self.joint_angles = {}
        self.velocities = {}

class JointAngle:
    """Joint angle calculation and storage"""
    def __init__(self, name: str, point1: str, joint: str, point3: str):
        self.name = name
        self.point1 = point1
        self.joint = joint
        self.point3 = point3

class BiomechanicalMetrics:
    """Container for biomechanical analysis results"""
    def __init__(self):
        self.joint_angles = {}
        self.velocities = {}
        self.accelerations = {}
        self.stride_metrics = {}
        self.grf_estimates = []
        self.center_of_mass = None

class PoseAnalyzer:
    """MediaPipe-based pose analysis"""
    
    def __init__(self, complexity: int = 1, enable_segmentation: bool = False):
        self.complexity = complexity
        self.enable_segmentation = enable_segmentation
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.pose_detector = None
        
        # MediaPipe landmark indices
        self.landmark_names = {
            0: 'nose', 1: 'left_eye_inner', 2: 'left_eye', 3: 'left_eye_outer',
            4: 'right_eye_inner', 5: 'right_eye', 6: 'right_eye_outer',
            7: 'left_ear', 8: 'right_ear', 9: 'mouth_left', 10: 'mouth_right',
            11: 'left_shoulder', 12: 'right_shoulder', 13: 'left_elbow', 14: 'right_elbow',
            15: 'left_wrist', 16: 'right_wrist', 17: 'left_pinky', 18: 'right_pinky',
            19: 'left_index', 20: 'right_index', 21: 'left_thumb', 22: 'right_thumb',
            23: 'left_hip', 24: 'right_hip', 25: 'left_knee', 26: 'right_knee',
            27: 'left_ankle', 28: 'right_ankle', 29: 'left_heel', 30: 'right_heel',
            31: 'left_foot_index', 32: 'right_foot_index'
        }
        
        # Joint angle definitions for biomechanical analysis
        self.joint_definitions = {
            'left_elbow': JointAngle('left_elbow', 'left_shoulder', 'left_elbow', 'left_wrist'),
            'right_elbow': JointAngle('right_elbow', 'right_shoulder', 'right_elbow', 'right_wrist'),
            'left_knee': JointAngle('left_knee', 'left_hip', 'left_knee', 'left_ankle'),
            'right_knee': JointAngle('right_knee', 'right_hip', 'right_knee', 'right_ankle'),
            'left_hip': JointAngle('left_hip', 'left_shoulder', 'left_hip', 'left_knee'),
            'right_hip': JointAngle('right_hip', 'right_shoulder', 'right_hip', 'right_knee'),
            'left_shoulder': JointAngle('left_shoulder', 'left_elbow', 'left_shoulder', 'left_hip'),
            'right_shoulder': JointAngle('right_shoulder', 'right_elbow', 'right_shoulder', 'right_hip'),
        }
    
    async def initialize(self):
        """Initialize MediaPipe pose detection"""
        self.pose_detector = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=self.complexity,
            enable_segmentation=self.enable_segmentation,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        logger.info("MediaPipe pose detector initialized")
    
    def extract_pose(self, frame: np.ndarray, timestamp: float, frame_idx: int) -> Optional[Pose]:
        """Extract pose from a frame"""
        if self.pose_detector is None:
            raise RuntimeError("Pose detector not initialized")
        
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process the frame
        results = self.pose_detector.process(rgb_frame)
        
        if results.pose_landmarks is None:
            return None
        
        # Extract landmarks
        landmarks = {}
        for idx, landmark in enumerate(results.pose_landmarks.landmark):
            name = self.landmark_names.get(idx, f"landmark_{idx}")
            landmarks[name] = (
                landmark.x * frame.shape[1],  # Convert to pixel coordinates
                landmark.y * frame.shape[0],
                landmark.visibility
            )
        
        return Pose(landmarks, frame_idx, timestamp)

class KinematicsAnalyzer:
    """Biomechanical kinematics analysis"""
    
    def __init__(self, fps: float = 30.0, filter_cutoff: float = 6.0):
        self.fps = fps
        self.dt = 1.0 / fps
        self.filter_cutoff = filter_cutoff
        self.pose_history = deque(maxlen=30)  # Store last 1 second of poses
    
    def calculate_angle_between_vectors(self, p1: Tuple[float, float], center: Tuple[float, float], p3: Tuple[float, float]) -> float:
        """Calculate angle between three points"""
        # Create vectors
        v1 = np.array([p1[0] - center[0], p1[1] - center[1]])
        v2 = np.array([p3[0] - center[0], p3[1] - center[1]])
        
        # Calculate angle
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
        cos_angle = np.clip(cos_angle, -1.0, 1.0)  # Handle numerical errors
        angle = np.arccos(cos_angle)
        
        return np.degrees(angle)
    
    def calculate_joint_angles(self, pose: Pose, joint_definitions: Dict[str, JointAngle]) -> Dict[str, float]:
        """Calculate joint angles for a pose"""
        angles = {}
        
        for joint_name, joint_def in joint_definitions.items():
            try:
                p1 = pose.landmarks[joint_def.point1]
                center = pose.landmarks[joint_def.joint]
                p3 = pose.landmarks[joint_def.point3]
                
                # Check visibility
                if p1[2] < 0.5 or center[2] < 0.5 or p3[2] < 0.5:
                    continue
                
                angle = self.calculate_angle_between_vectors(p1[:2], center[:2], p3[:2])
                angles[joint_name] = angle
                
            except KeyError:
                # Missing landmark
                continue
        
        return angles
    
    def calculate_velocities(self, pose_sequence: List[Pose]) -> Dict[str, List[float]]:
        """Calculate joint velocities using central difference"""
        if len(pose_sequence) < 3:
            return {}
        
        velocities = defaultdict(list)
        
        for i in range(1, len(pose_sequence) - 1):
            prev_pose = pose_sequence[i - 1]
            next_pose = pose_sequence[i + 1]
            
            for landmark_name in prev_pose.landmarks:
                if landmark_name in next_pose.landmarks:
                    prev_pos = np.array(prev_pose.landmarks[landmark_name][:2])
                    next_pos = np.array(next_pose.landmarks[landmark_name][:2])
                    
                    # Central difference
                    velocity = (next_pos - prev_pos) / (2 * self.dt)
                    speed = np.linalg.norm(velocity)
                    
                    velocities[landmark_name].append(speed)
        
        return dict(velocities)
    
    def analyze_pose(self, pose: Pose, joint_definitions: Dict[str, JointAngle]) -> Dict[str, Any]:
        """Analyze a single pose for biomechanical metrics"""
        self.pose_history.append(pose)
        
        # Calculate joint angles
        joint_angles = self.calculate_joint_angles(pose, joint_definitions)
        pose.joint_angles = joint_angles
        
        # Calculate velocities if we have enough history
        velocities = {}
        if len(self.pose_history) >= 3:
            velocities = self.calculate_velocities(list(self.pose_history))
        
        return {
            "joint_angles": joint_angles,
            "velocities": velocities,
            "center_of_mass": self.estimate_center_of_mass(pose)
        }
    
    def estimate_center_of_mass(self, pose: Pose) -> Optional[Tuple[float, float]]:
        """Estimate center of mass using anthropometric data"""
        # Simplified COM estimation using major landmarks
        key_landmarks = ['left_shoulder', 'right_shoulder', 'left_hip', 'right_hip']
        
        positions = []
        weights = [0.25, 0.25, 0.25, 0.25]  # Equal weighting for simplicity
        
        for landmark in key_landmarks:
            if landmark in pose.landmarks and pose.landmarks[landmark][2] > 0.5:
                positions.append(pose.landmarks[landmark][:2])
            else:
                return None
        
        if len(positions) != len(key_landmarks):
            return None
        
        com = np.average(positions, axis=0, weights=weights)
        return tuple(com)

class StrideAnalyzer:
    """Gait and stride analysis"""
    
    def __init__(self, fps: float = 30.0):
        self.fps = fps
        self.contact_threshold = 0.1  # m/s threshold for foot contact detection
        self.ankle_history = {'left': deque(maxlen=90), 'right': deque(maxlen=90)}  # 3 seconds
    
    def detect_foot_contacts(self, ankle_positions: List[Tuple[float, float]]) -> List[int]:
        """Detect foot contact events based on ankle velocity"""
        if len(ankle_positions) < 3:
            return []
        
        # Calculate velocities
        velocities = []
        for i in range(1, len(ankle_positions) - 1):
            v = np.array(ankle_positions[i + 1]) - np.array(ankle_positions[i - 1])
            velocities.append(np.linalg.norm(v))
        
        # Find contact points (local minima in velocity)
        contacts = []
        for i in range(1, len(velocities) - 1):
            if (velocities[i] < velocities[i - 1] and 
                velocities[i] < velocities[i + 1] and 
                velocities[i] < self.contact_threshold):
                contacts.append(i + 1)  # Adjust for offset
        
        return contacts
    
    def calculate_stride_metrics(self, left_ankle_history: List, right_ankle_history: List) -> Dict[str, Any]:
        """Calculate stride metrics from ankle position history"""
        if len(left_ankle_history) < 30 or len(right_ankle_history) < 30:
            return {}
        
        # Extract positions
        left_positions = [(pos[0], pos[1]) for pos in left_ankle_history if pos[2] > 0.5]
        right_positions = [(pos[0], pos[1]) for pos in right_ankle_history if pos[2] > 0.5]
        
        if len(left_positions) < 10 or len(right_positions) < 10:
            return {}
        
        # Detect contacts
        left_contacts = self.detect_foot_contacts(left_positions)
        right_contacts = self.detect_foot_contacts(right_positions)
        
        # Calculate stride frequency
        stride_frequency = 0.0
        if len(left_contacts) > 1:
            time_between_contacts = (len(left_positions) / self.fps) / (len(left_contacts) - 1)
            stride_frequency = 1.0 / time_between_contacts if time_between_contacts > 0 else 0.0
        
        # Calculate stride length (simplified)
        stride_length = 0.0
        if len(left_positions) > 1:
            total_distance = 0.0
            for i in range(1, len(left_positions)):
                distance = np.linalg.norm(np.array(left_positions[i]) - np.array(left_positions[i-1]))
                total_distance += distance
            stride_length = total_distance / max(1, len(left_contacts))
        
        return {
            "stride_frequency": stride_frequency,
            "stride_length": stride_length,
            "left_contacts": len(left_contacts),
            "right_contacts": len(right_contacts),
            "contact_asymmetry": abs(len(left_contacts) - len(right_contacts))
        }

class GRFAnalyzer:
    """Ground Reaction Force estimation"""
    
    def __init__(self, body_mass: float = 70.0):
        self.body_mass = body_mass
        self.g = 9.81  # Gravitational acceleration
    
    def estimate_grf(self, pose_sequence: List[Pose], contact_events: List[int]) -> List[Dict[str, float]]:
        """Estimate ground reaction forces during contact events"""
        if len(pose_sequence) < 3:
            return []
        
        forces = []
        
        for i, pose in enumerate(pose_sequence):
            if i in contact_events:
                # Calculate COM acceleration (simplified)
                com_accel = self.calculate_com_acceleration(pose_sequence, i)
                
                # Estimate vertical GRF using Newton's second law
                vertical_force = self.body_mass * (self.g + com_accel[1])
                horizontal_force = self.body_mass * com_accel[0]
                
                forces.append({
                    "vertical_force": vertical_force,
                    "horizontal_force": horizontal_force,
                    "total_force": np.sqrt(vertical_force**2 + horizontal_force**2),
                    "frame_idx": i
                })
            else:
                forces.append({
                    "vertical_force": 0.0,
                    "horizontal_force": 0.0,
                    "total_force": 0.0,
                    "frame_idx": i
                })
        
        return forces
    
    def calculate_com_acceleration(self, pose_sequence: List[Pose], center_idx: int) -> Tuple[float, float]:
        """Calculate center of mass acceleration using central difference"""
        if center_idx < 1 or center_idx >= len(pose_sequence) - 1:
            return (0.0, 0.0)
        
        # Get COM positions
        prev_com = self.get_com_position(pose_sequence[center_idx - 1])
        curr_com = self.get_com_position(pose_sequence[center_idx])
        next_com = self.get_com_position(pose_sequence[center_idx + 1])
        
        if prev_com is None or curr_com is None or next_com is None:
            return (0.0, 0.0)
        
        # Calculate acceleration using central difference
        dt = 1.0 / 30.0  # Assume 30 FPS
        accel_x = (next_com[0] - 2 * curr_com[0] + prev_com[0]) / (dt**2)
        accel_y = (next_com[1] - 2 * curr_com[1] + prev_com[1]) / (dt**2)
        
        return (accel_x, accel_y)
    
    def get_com_position(self, pose: Pose) -> Optional[Tuple[float, float]]:
        """Get center of mass position from pose"""
        # Simplified COM using hip midpoint
        if 'left_hip' in pose.landmarks and 'right_hip' in pose.landmarks:
            left_hip = pose.landmarks['left_hip']
            right_hip = pose.landmarks['right_hip']
            
            if left_hip[2] > 0.5 and right_hip[2] > 0.5:
                com_x = (left_hip[0] + right_hip[0]) / 2
                com_y = (left_hip[1] + right_hip[1]) / 2
                return (com_x, com_y)
        
        return None

class MoriartyPipeline:
    """Main Moriarty framework pipeline"""
    
    def __init__(self, complexity: int = 1, enable_biomechanics: bool = True):
        self.pose_analyzer = PoseAnalyzer(complexity=complexity)
        self.kinematics_analyzer = KinematicsAnalyzer()
        self.stride_analyzer = StrideAnalyzer()
        self.grf_analyzer = GRFAnalyzer()
        self.enable_biomechanics = enable_biomechanics
        
        # History tracking
        self.pose_history = deque(maxlen=90)  # 3 seconds at 30 FPS
        self.frame_count = 0
    
    async def initialize(self):
        """Initialize all components"""
        await self.pose_analyzer.initialize()
        logger.info("Moriarty pipeline initialized")
    
    async def analyze_frame(self, frame: np.ndarray, timestamp: float) -> Dict[str, Any]:
        """Analyze a single frame"""
        start_time = time.time()
        
        # Extract pose
        pose = self.pose_analyzer.extract_pose(frame, timestamp, self.frame_count)
        self.frame_count += 1
        
        if pose is None:
            return {
                "timestamp": timestamp,
                "pose_detected": False,
                "processing_time": time.time() - start_time
            }
        
        self.pose_history.append(pose)
        
        result = {
            "timestamp": timestamp,
            "frame_idx": pose.frame_idx,
            "pose_detected": True,
            "landmarks": {name: {"x": pos[0], "y": pos[1], "visibility": pos[2]} 
                         for name, pos in pose.landmarks.items()},
            "processing_time": time.time() - start_time
        }
        
        if self.enable_biomechanics and len(self.pose_history) >= 3:
            # Biomechanical analysis
            biomechanics = self.kinematics_analyzer.analyze_pose(
                pose, self.pose_analyzer.joint_definitions
            )
            result["biomechanics"] = biomechanics
            
            # Stride analysis (if we have enough history)
            if len(self.pose_history) >= 30:
                left_ankle_history = []
                right_ankle_history = []
                
                for hist_pose in self.pose_history:
                    if 'left_ankle' in hist_pose.landmarks:
                        left_ankle_history.append(hist_pose.landmarks['left_ankle'])
                    if 'right_ankle' in hist_pose.landmarks:
                        right_ankle_history.append(hist_pose.landmarks['right_ankle'])
                
                stride_metrics = self.stride_analyzer.calculate_stride_metrics(
                    left_ankle_history, right_ankle_history
                )
                result["stride_metrics"] = stride_metrics
        
        result["processing_time"] = time.time() - start_time
        return result 