"""
Vibrio Framework - Human Motion Analysis
Computer vision framework for detecting, tracking, and analyzing humans in video footage.
"""

import asyncio
import time
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import cv2
import torch
from ultralytics import YOLO
from scipy.spatial.distance import cdist
from collections import defaultdict, deque

import structlog

logger = structlog.get_logger(__name__)

class Detection:
    """Human detection result"""
    def __init__(self, bbox: List[float], confidence: float, class_id: int = 0):
        self.bbox = bbox  # [x1, y1, x2, y2]
        self.confidence = confidence
        self.class_id = class_id
        self.center = [(bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2]
        self.area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])

class Track:
    """Human tracking result"""
    def __init__(self, track_id: int, detection: Detection):
        self.track_id = track_id
        self.detections = [detection]
        self.positions = [detection.center]
        self.speeds = deque(maxlen=10)  # Speed history
        self.current_speed = 0.0
        self.age = 0
        self.hits = 1
        self.time_since_update = 0
        
        # Kalman filter state [x, y, w, h, vx, vy, vs]
        self.state = np.array([
            detection.center[0], detection.center[1],
            detection.bbox[2] - detection.bbox[0],
            detection.bbox[3] - detection.bbox[1],
            0, 0, 0
        ], dtype=float)
        
        # Initialize covariance matrix
        self.P = np.eye(7) * 1000
        
        # Process noise
        self.Q = np.eye(7)
        self.Q[4:6, 4:6] *= 0.01  # Velocity noise
        
        # Measurement noise
        self.R = np.eye(4) * 10

class HumanDetector:
    """Human detection using YOLOv8"""
    
    def __init__(self, model_path: str = "yolov8n.pt", conf_threshold: float = 0.5, device: str = "cpu"):
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.device = device
        self.model = None
        
    async def initialize(self):
        """Initialize the YOLO model"""
        try:
            self.model = YOLO(self.model_path)
            logger.info(f"Loaded YOLO model from {self.model_path}")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            raise
    
    def detect(self, frame: np.ndarray) -> List[Detection]:
        """Detect humans in a frame"""
        if self.model is None:
            raise RuntimeError("Model not initialized")
        
        # Run inference
        results = self.model(frame, conf=self.conf_threshold, classes=[0])  # Class 0 is person
        
        detections = []
        for result in results:
            if result.boxes is not None:
                for box in result.boxes:
                    # Extract bounding box and confidence
                    bbox = box.xyxy[0].cpu().numpy().tolist()
                    confidence = float(box.conf[0])
                    
                    detection = Detection(bbox, confidence)
                    detections.append(detection)
        
        return detections

class HumanTracker:
    """Multi-object tracking with Kalman filters"""
    
    def __init__(self, max_age: int = 30, min_hits: int = 3, iou_threshold: float = 0.3):
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.tracks = []
        self.track_id_counter = 0
        
    def _calculate_iou(self, bbox1: List[float], bbox2: List[float]) -> float:
        """Calculate Intersection over Union"""
        x1 = max(bbox1[0], bbox2[0])
        y1 = max(bbox1[1], bbox2[1])
        x2 = min(bbox1[2], bbox2[2])
        y2 = min(bbox1[3], bbox2[3])
        
        if x2 <= x1 or y2 <= y1:
            return 0.0
        
        intersection = (x2 - x1) * (y2 - y1)
        area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def _associate_detections_to_tracks(self, detections: List[Detection]) -> Tuple[List, List, List]:
        """Associate detections to existing tracks using Hungarian algorithm"""
        if not self.tracks:
            return [], list(range(len(detections))), []
        
        # Calculate IoU matrix
        iou_matrix = np.zeros((len(detections), len(self.tracks)))
        for d, detection in enumerate(detections):
            for t, track in enumerate(self.tracks):
                # Get predicted bbox from track state
                predicted_bbox = [
                    track.state[0] - track.state[2] / 2,
                    track.state[1] - track.state[3] / 2,
                    track.state[0] + track.state[2] / 2,
                    track.state[1] + track.state[3] / 2
                ]
                iou_matrix[d, t] = self._calculate_iou(detection.bbox, predicted_bbox)
        
        # Simple greedy assignment (could be improved with Hungarian algorithm)
        matched = []
        unmatched_detections = list(range(len(detections)))
        unmatched_tracks = list(range(len(self.tracks)))
        
        # Find matches above threshold
        while len(unmatched_detections) > 0 and len(unmatched_tracks) > 0:
            max_iou = 0
            max_d, max_t = -1, -1
            
            for d in unmatched_detections:
                for t in unmatched_tracks:
                    if iou_matrix[d, t] > max_iou and iou_matrix[d, t] > self.iou_threshold:
                        max_iou = iou_matrix[d, t]
                        max_d, max_t = d, t
            
            if max_d == -1:
                break
            
            matched.append([max_d, max_t])
            unmatched_detections.remove(max_d)
            unmatched_tracks.remove(max_t)
        
        return matched, unmatched_detections, unmatched_tracks
    
    def update(self, detections: List[Detection], frame_idx: int) -> List[Track]:
        """Update tracks with new detections"""
        # Associate detections to tracks
        matched, unmatched_detections, unmatched_tracks = self._associate_detections_to_tracks(detections)
        
        # Update matched tracks
        for match in matched:
            detection_idx, track_idx = match
            track = self.tracks[track_idx]
            detection = detections[detection_idx]
            
            # Update track with new detection
            track.detections.append(detection)
            track.positions.append(detection.center)
            track.hits += 1
            track.time_since_update = 0
            
            # Update Kalman filter
            self._update_kalman_filter(track, detection)
        
        # Create new tracks for unmatched detections
        for detection_idx in unmatched_detections:
            new_track = Track(self.track_id_counter, detections[detection_idx])
            self.tracks.append(new_track)
            self.track_id_counter += 1
        
        # Update unmatched tracks
        for track_idx in unmatched_tracks:
            self.tracks[track_idx].time_since_update += 1
        
        # Remove old tracks
        self.tracks = [track for track in self.tracks 
                      if track.time_since_update < self.max_age]
        
        # Return active tracks
        return [track for track in self.tracks 
                if track.hits >= self.min_hits or track.time_since_update == 0]
    
    def _update_kalman_filter(self, track: Track, detection: Detection):
        """Update track's Kalman filter with new detection"""
        # Prediction step
        F = np.eye(7)  # State transition matrix
        F[0, 4] = 1  # x += vx
        F[1, 5] = 1  # y += vy
        F[2, 6] = 1  # scale += vs
        
        track.state = F @ track.state
        track.P = F @ track.P @ F.T + track.Q
        
        # Update step
        H = np.eye(4, 7)  # Measurement matrix (observe x, y, w, h)
        measurement = np.array([
            detection.center[0], detection.center[1],
            detection.bbox[2] - detection.bbox[0],
            detection.bbox[3] - detection.bbox[1]
        ])
        
        y = measurement - H @ track.state  # Innovation
        S = H @ track.P @ H.T + track.R  # Innovation covariance
        K = track.P @ H.T @ np.linalg.inv(S)  # Kalman gain
        
        track.state = track.state + K @ y
        track.P = (np.eye(7) - K @ H) @ track.P

class SpeedEstimator:
    """Estimate human movement speed"""
    
    def __init__(self, fps: float = 30.0, pixel_to_meter_ratio: float = 0.01, smoothing_window: int = 5):
        self.fps = fps
        self.pixel_to_meter_ratio = pixel_to_meter_ratio
        self.smoothing_window = smoothing_window
    
    def estimate_speed(self, track: Track) -> float:
        """Estimate speed for a track"""
        if len(track.positions) < 2:
            return 0.0
        
        # Calculate displacement between last two positions
        pos1 = np.array(track.positions[-2])
        pos2 = np.array(track.positions[-1])
        
        displacement_pixels = np.linalg.norm(pos2 - pos1)
        displacement_meters = displacement_pixels * self.pixel_to_meter_ratio
        
        # Convert to speed (m/s to km/h)
        speed_ms = displacement_meters * self.fps
        speed_kmh = speed_ms * 3.6
        
        # Add to track's speed history
        track.speeds.append(speed_kmh)
        
        # Calculate smoothed speed
        if len(track.speeds) >= self.smoothing_window:
            track.current_speed = np.mean(list(track.speeds)[-self.smoothing_window:])
        else:
            track.current_speed = np.mean(list(track.speeds))
        
        return track.current_speed

class OpticalAnalyzer:
    """Advanced optical analysis methods"""
    
    def __init__(self):
        self.prev_frame = None
        self.motion_history = deque(maxlen=10)
    
    def analyze_optical_flow(self, frame: np.ndarray) -> Dict[str, Any]:
        """Analyze optical flow using Farneback method"""
        if self.prev_frame is None:
            self.prev_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            return {"flow_magnitude": 0.0, "flow_direction": 0.0}
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Calculate optical flow
        flow = cv2.calcOpticalFlowPyrLK(
            self.prev_frame, gray, None, None,
            winSize=(15, 15), maxLevel=2,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)
        )[0]
        
        if flow is not None:
            # Calculate flow statistics
            magnitude = np.sqrt(flow[:, :, 0]**2 + flow[:, :, 1]**2)
            direction = np.arctan2(flow[:, :, 1], flow[:, :, 0])
            
            avg_magnitude = np.mean(magnitude)
            avg_direction = np.mean(direction)
        else:
            avg_magnitude = 0.0
            avg_direction = 0.0
        
        self.prev_frame = gray
        
        return {
            "flow_magnitude": float(avg_magnitude),
            "flow_direction": float(avg_direction),
            "motion_intensity": float(avg_magnitude) / 255.0
        }
    
    def analyze_motion_energy(self, frame: np.ndarray) -> Dict[str, Any]:
        """Analyze motion energy using frame differencing"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        self.motion_history.append(gray)
        
        if len(self.motion_history) < 2:
            return {"motion_energy": 0.0, "active_regions": 0}
        
        # Calculate frame difference
        diff = cv2.absdiff(self.motion_history[-2], self.motion_history[-1])
        
        # Threshold to get binary motion mask
        _, motion_mask = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
        
        # Calculate motion energy
        motion_energy = np.sum(motion_mask) / motion_mask.size
        
        # Count active regions
        contours, _ = cv2.findContours(motion_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        active_regions = len([c for c in contours if cv2.contourArea(c) > 100])
        
        return {
            "motion_energy": float(motion_energy),
            "active_regions": int(active_regions)
        }

class VibrioAnalyzer:
    """Main Vibrio framework analyzer"""
    
    def __init__(self, model_path: str = "yolov8n.pt", device: str = "cpu"):
        self.detector = HumanDetector(model_path, device=device)
        self.tracker = HumanTracker()
        self.speed_estimator = SpeedEstimator()
        self.optical_analyzer = OpticalAnalyzer()
        
    async def initialize(self):
        """Initialize all components"""
        await self.detector.initialize()
        logger.info("Vibrio analyzer initialized")
    
    async def analyze_frame(self, frame: np.ndarray, timestamp: float) -> Dict[str, Any]:
        """Analyze a single frame"""
        start_time = time.time()
        
        # Human detection
        detections = self.detector.detect(frame)
        
        # Object tracking
        tracks = self.tracker.update(detections, int(timestamp * 30))  # Assume 30 FPS
        
        # Speed estimation
        for track in tracks:
            self.speed_estimator.estimate_speed(track)
        
        # Optical analysis
        optical_flow = self.optical_analyzer.analyze_optical_flow(frame)
        motion_energy = self.optical_analyzer.analyze_motion_energy(frame)
        
        processing_time = time.time() - start_time
        
        # Compile results
        result = {
            "timestamp": timestamp,
            "detections": [
                {
                    "bbox": det.bbox,
                    "confidence": det.confidence,
                    "center": det.center
                } for det in detections
            ],
            "tracks": [
                {
                    "track_id": track.track_id,
                    "position": track.positions[-1] if track.positions else [0, 0],
                    "speed": track.current_speed,
                    "age": track.age,
                    "bbox": track.detections[-1].bbox if track.detections else [0, 0, 0, 0]
                } for track in tracks
            ],
            "optical_flow": optical_flow,
            "motion_energy": motion_energy,
            "processing_time": processing_time,
            "total_detections": len(detections),
            "active_tracks": len(tracks)
        }
        
        return result 