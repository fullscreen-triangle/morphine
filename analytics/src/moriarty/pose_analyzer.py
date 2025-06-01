import cv2
import numpy as np
import mediapipe as mp
from typing import Dict, List, Optional, Tuple
import math
from ..models.analytics import Landmark, BiomechanicsResult

class PoseAnalyzer:
    """MediaPipe BlazePose-based pose analysis for the Moriarty framework"""
    
    def __init__(self, model_complexity: int = 1, min_detection_confidence: float = 0.5, min_tracking_confidence: float = 0.5):
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        
        self.pose = self.mp_pose.Pose(
            model_complexity=model_complexity,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        
        # Define key joint connections for biomechanical analysis
        self.joint_connections = {
            'left_shoulder': (self.mp_pose.PoseLandmark.LEFT_SHOULDER, 
                            self.mp_pose.PoseLandmark.LEFT_ELBOW,
                            self.mp_pose.PoseLandmark.LEFT_HIP),
            'right_shoulder': (self.mp_pose.PoseLandmark.RIGHT_SHOULDER,
                             self.mp_pose.PoseLandmark.RIGHT_ELBOW,
                             self.mp_pose.PoseLandmark.RIGHT_HIP),
            'left_elbow': (self.mp_pose.PoseLandmark.LEFT_SHOULDER,
                          self.mp_pose.PoseLandmark.LEFT_ELBOW,
                          self.mp_pose.PoseLandmark.LEFT_WRIST),
            'right_elbow': (self.mp_pose.PoseLandmark.RIGHT_SHOULDER,
                           self.mp_pose.PoseLandmark.RIGHT_ELBOW,
                           self.mp_pose.PoseLandmark.RIGHT_WRIST),
            'left_hip': (self.mp_pose.PoseLandmark.LEFT_SHOULDER,
                        self.mp_pose.PoseLandmark.LEFT_HIP,
                        self.mp_pose.PoseLandmark.LEFT_KNEE),
            'right_hip': (self.mp_pose.PoseLandmark.RIGHT_SHOULDER,
                         self.mp_pose.PoseLandmark.RIGHT_HIP,
                         self.mp_pose.PoseLandmark.RIGHT_KNEE),
            'left_knee': (self.mp_pose.PoseLandmark.LEFT_HIP,
                         self.mp_pose.PoseLandmark.LEFT_KNEE,
                         self.mp_pose.PoseLandmark.LEFT_ANKLE),
            'right_knee': (self.mp_pose.PoseLandmark.RIGHT_HIP,
                          self.mp_pose.PoseLandmark.RIGHT_KNEE,
                          self.mp_pose.PoseLandmark.RIGHT_ANKLE),
        }
        
        # Store previous landmarks for velocity calculation
        self.previous_landmarks = None
        self.frame_time = 1/30.0  # Assume 30 FPS for velocity calculation
        
    def analyze_pose(self, frame: np.ndarray) -> Tuple[bool, Dict[str, Landmark], Optional[BiomechanicsResult]]:
        """
        Analyze pose in the given frame
        
        Args:
            frame: Input frame as BGR numpy array
            
        Returns:
            Tuple of (pose_detected, landmarks_dict, biomechanics_result)
        """
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process the frame
        results = self.pose.process(rgb_frame)
        
        if not results.pose_landmarks:
            return False, {}, None
        
        # Extract landmarks
        landmarks_dict = self._extract_landmarks(results.pose_landmarks, frame.shape)
        
        # Calculate biomechanics
        biomechanics = self._calculate_biomechanics(landmarks_dict)
        
        # Store current landmarks for next frame velocity calculation
        self.previous_landmarks = landmarks_dict
        
        return True, landmarks_dict, biomechanics
    
    def _extract_landmarks(self, pose_landmarks, frame_shape: Tuple[int, int, int]) -> Dict[str, Landmark]:
        """Extract and normalize landmarks"""
        landmarks_dict = {}
        height, width = frame_shape[:2]
        
        for idx, landmark in enumerate(pose_landmarks.landmark):
            landmark_name = self.mp_pose.PoseLandmark(idx).name.lower()
            
            # Convert normalized coordinates to pixel coordinates
            x = landmark.x * width
            y = landmark.y * height
            visibility = landmark.visibility
            
            landmarks_dict[landmark_name] = Landmark(
                x=x,
                y=y,
                visibility=visibility
            )
        
        return landmarks_dict
    
    def _calculate_angle(self, point1: Landmark, point2: Landmark, point3: Landmark) -> float:
        """Calculate angle between three points"""
        # Vector from point2 to point1
        v1 = np.array([point1.x - point2.x, point1.y - point2.y])
        # Vector from point2 to point3
        v2 = np.array([point3.x - point2.x, point3.y - point2.y])
        
        # Calculate angle using dot product
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6)
        cos_angle = np.clip(cos_angle, -1.0, 1.0)  # Ensure valid range
        angle = np.arccos(cos_angle)
        
        return np.degrees(angle)
    
    def _calculate_distance(self, point1: Landmark, point2: Landmark) -> float:
        """Calculate Euclidean distance between two points"""
        return math.sqrt((point1.x - point2.x)**2 + (point1.y - point2.y)**2)
    
    def _calculate_center_of_mass(self, landmarks: Dict[str, Landmark]) -> Optional[Tuple[float, float]]:
        """Calculate approximate center of mass"""
        # Use key body landmarks to estimate center of mass
        key_points = ['left_shoulder', 'right_shoulder', 'left_hip', 'right_hip']
        
        valid_points = []
        for point_name in key_points:
            if point_name in landmarks and landmarks[point_name].visibility > 0.5:
                valid_points.append(landmarks[point_name])
        
        if len(valid_points) < 2:
            return None
        
        # Calculate weighted average (equal weights for simplicity)
        com_x = sum(point.x for point in valid_points) / len(valid_points)
        com_y = sum(point.y for point in valid_points) / len(valid_points)
        
        return (com_x, com_y)
    
    def _calculate_velocities(self, current_landmarks: Dict[str, Landmark]) -> Dict[str, List[float]]:
        """Calculate velocities of key landmarks"""
        velocities = {}
        
        if self.previous_landmarks is None:
            # No previous frame, return zero velocities
            for landmark_name in current_landmarks:
                velocities[landmark_name] = [0.0, 0.0]
            return velocities
        
        for landmark_name, current_landmark in current_landmarks.items():
            if landmark_name in self.previous_landmarks:
                prev_landmark = self.previous_landmarks[landmark_name]
                
                # Calculate velocity (pixels per second)
                vx = (current_landmark.x - prev_landmark.x) / self.frame_time
                vy = (current_landmark.y - prev_landmark.y) / self.frame_time
                
                velocities[landmark_name] = [vx, vy]
            else:
                velocities[landmark_name] = [0.0, 0.0]
        
        return velocities
    
    def _calculate_biomechanics(self, landmarks: Dict[str, Landmark]) -> BiomechanicsResult:
        """Calculate biomechanical metrics"""
        joint_angles = {}
        
        # Calculate joint angles
        for joint_name, (point1_enum, point2_enum, point3_enum) in self.joint_connections.items():
            point1_name = point1_enum.name.lower()
            point2_name = point2_enum.name.lower()
            point3_name = point3_enum.name.lower()
            
            if all(name in landmarks for name in [point1_name, point2_name, point3_name]):
                if all(landmarks[name].visibility > 0.5 for name in [point1_name, point2_name, point3_name]):
                    angle = self._calculate_angle(
                        landmarks[point1_name],
                        landmarks[point2_name],
                        landmarks[point3_name]
                    )
                    joint_angles[joint_name] = angle
        
        # Calculate velocities
        velocities = self._calculate_velocities(landmarks)
        
        # Calculate center of mass
        center_of_mass = self._calculate_center_of_mass(landmarks)
        
        return BiomechanicsResult(
            joint_angles=joint_angles,
            velocities=velocities,
            center_of_mass=list(center_of_mass) if center_of_mass else None
        )
    
    def draw_pose(self, frame: np.ndarray, landmarks: Dict[str, Landmark], joint_angles: Dict[str, float]) -> np.ndarray:
        """Draw pose landmarks and joint angles on frame"""
        annotated_frame = frame.copy()
        
        # Convert landmarks back to MediaPipe format for drawing
        mp_landmarks = mp.solutions.pose.PoseLandmark
        landmark_list = []
        
        for i in range(33):  # MediaPipe has 33 pose landmarks
            landmark_name = mp_landmarks(i).name.lower()
            if landmark_name in landmarks:
                landmark = landmarks[landmark_name]
                # Normalize coordinates for MediaPipe drawing
                height, width = frame.shape[:2]
                normalized_landmark = type('Landmark', (), {
                    'x': landmark.x / width,
                    'y': landmark.y / height,
                    'z': 0,
                    'visibility': landmark.visibility
                })()
                landmark_list.append(normalized_landmark)
            else:
                # Default landmark if missing
                landmark_list.append(type('Landmark', (), {'x': 0, 'y': 0, 'z': 0, 'visibility': 0})())
        
        # Create MediaPipe landmark object
        pose_landmarks = type('PoseLandmarks', (), {'landmark': landmark_list})()
        
        # Draw pose connections
        self.mp_drawing.draw_landmarks(
            annotated_frame, 
            pose_landmarks, 
            self.mp_pose.POSE_CONNECTIONS,
            self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
            self.mp_drawing.DrawingSpec(color=(0, 0, 255), thickness=2)
        )
        
        # Draw joint angles
        y_offset = 30
        for joint_name, angle in joint_angles.items():
            text = f"{joint_name}: {angle:.1f}°"
            cv2.putText(annotated_frame, text, (10, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            y_offset += 25
        
        return annotated_frame
    
    def get_pose_quality_score(self, landmarks: Dict[str, Landmark]) -> float:
        """Calculate a pose quality score based on landmark visibility"""
        if not landmarks:
            return 0.0
        
        total_visibility = sum(landmark.visibility for landmark in landmarks.values())
        return total_visibility / len(landmarks)
    
    def reset(self):
        """Reset pose analyzer state"""
        self.previous_landmarks = None 