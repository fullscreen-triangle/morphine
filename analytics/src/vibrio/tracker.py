import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import cv2
from filterpy.kalman import KalmanFilter
from scipy.optimize import linear_sum_assignment
from ..models.analytics import Detection, Track

@dataclass
class TrackState:
    """State information for a tracked object"""
    track_id: int
    kalman_filter: KalmanFilter
    age: int
    hits: int
    time_since_update: int
    position: Tuple[float, float]
    velocity: Tuple[float, float]
    bbox: List[float]
    confidence: float

class HumanTracker:
    """Multi-object tracking using Kalman filters and Hungarian algorithm"""
    
    def __init__(self, max_disappeared: int = 10, max_distance: float = 100.0):
        self.max_disappeared = max_disappeared
        self.max_distance = max_distance
        self.next_id = 0
        self.tracks: Dict[int, TrackState] = {}
        
    def _create_kalman_filter(self, initial_pos: Tuple[float, float]) -> KalmanFilter:
        """Create a Kalman filter for tracking"""
        kf = KalmanFilter(dim_x=4, dim_z=2)
        
        # State transition matrix (constant velocity model)
        kf.F = np.array([[1., 0., 1., 0.],
                        [0., 1., 0., 1.],
                        [0., 0., 1., 0.],
                        [0., 0., 0., 1.]])
        
        # Measurement function (we only measure position)
        kf.H = np.array([[1., 0., 0., 0.],
                        [0., 1., 0., 0.]])
        
        # Measurement noise
        kf.R = np.array([[10., 0.],
                        [0., 10.]])
        
        # Process noise
        kf.Q = np.array([[1., 0., 0., 0.],
                        [0., 1., 0., 0.],
                        [0., 0., 1., 0.],
                        [0., 0., 0., 1.]]) * 0.1
        
        # Initial state covariance
        kf.P = np.array([[100., 0., 0., 0.],
                        [0., 100., 0., 0.],
                        [0., 0., 100., 0.],
                        [0., 0., 0., 100.]])
        
        # Initialize state
        kf.x = np.array([initial_pos[0], initial_pos[1], 0., 0.])
        
        return kf
    
    def _calculate_distance(self, track: TrackState, detection: Detection) -> float:
        """Calculate distance between track and detection"""
        track_center = track.position
        detection_center = detection.center
        
        return np.sqrt((track_center[0] - detection_center[0])**2 + 
                      (track_center[1] - detection_center[1])**2)
    
    def _associate_detections_to_tracks(self, detections: List[Detection]) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        """Associate detections to existing tracks using Hungarian algorithm"""
        if len(self.tracks) == 0:
            return [], [], list(range(len(detections)))
        
        if len(detections) == 0:
            return [], list(self.tracks.keys()), []
        
        # Create cost matrix
        cost_matrix = np.zeros((len(self.tracks), len(detections)))
        track_ids = list(self.tracks.keys())
        
        for i, track_id in enumerate(track_ids):
            track = self.tracks[track_id]
            for j, detection in enumerate(detections):
                distance = self._calculate_distance(track, detection)
                cost_matrix[i, j] = distance if distance < self.max_distance else self.max_distance * 2
        
        # Solve assignment problem
        row_indices, col_indices = linear_sum_assignment(cost_matrix)
        
        # Extract matches and unmatched
        matches = []
        unmatched_tracks = []
        unmatched_detections = list(range(len(detections)))
        
        for i, j in zip(row_indices, col_indices):
            if cost_matrix[i, j] < self.max_distance:
                matches.append((track_ids[i], j))
                unmatched_detections.remove(j)
            else:
                unmatched_tracks.append(track_ids[i])
        
        # Add remaining unmatched tracks
        for i, track_id in enumerate(track_ids):
            if i not in row_indices:
                unmatched_tracks.append(track_id)
        
        return matches, unmatched_tracks, unmatched_detections
    
    def update(self, detections: List[Detection]) -> List[Track]:
        """Update tracker with new detections"""
        # Predict step for all tracks
        for track in self.tracks.values():
            track.kalman_filter.predict()
            track.age += 1
            track.time_since_update += 1
        
        # Associate detections to tracks
        matches, unmatched_tracks, unmatched_detections = self._associate_detections_to_tracks(detections)
        
        # Update matched tracks
        for track_id, detection_idx in matches:
            track = self.tracks[track_id]
            detection = detections[detection_idx]
            
            # Update Kalman filter
            measurement = np.array([detection.center[0], detection.center[1]])
            track.kalman_filter.update(measurement)
            
            # Update track state
            track.position = (track.kalman_filter.x[0], track.kalman_filter.x[1])
            track.velocity = (track.kalman_filter.x[2], track.kalman_filter.x[3])
            track.bbox = detection.bbox
            track.confidence = detection.confidence
            track.hits += 1
            track.time_since_update = 0
        
        # Create new tracks for unmatched detections
        for detection_idx in unmatched_detections:
            detection = detections[detection_idx]
            kf = self._create_kalman_filter((detection.center[0], detection.center[1]))
            
            track = TrackState(
                track_id=self.next_id,
                kalman_filter=kf,
                age=1,
                hits=1,
                time_since_update=0,
                position=(detection.center[0], detection.center[1]),
                velocity=(0.0, 0.0),
                bbox=detection.bbox,
                confidence=detection.confidence
            )
            
            self.tracks[self.next_id] = track
            self.next_id += 1
        
        # Remove old tracks
        tracks_to_remove = []
        for track_id in unmatched_tracks:
            if self.tracks[track_id].time_since_update > self.max_disappeared:
                tracks_to_remove.append(track_id)
        
        for track_id in tracks_to_remove:
            del self.tracks[track_id]
        
        # Convert to Track objects
        active_tracks = []
        for track in self.tracks.values():
            if track.hits >= 3 and track.time_since_update <= 1:  # Only return stable tracks
                speed = np.sqrt(track.velocity[0]**2 + track.velocity[1]**2)
                
                track_obj = Track(
                    track_id=track.track_id,
                    position=list(track.position),
                    speed=speed,
                    age=track.age,
                    bbox=track.bbox
                )
                active_tracks.append(track_obj)
        
        return active_tracks
    
    def get_track_count(self) -> int:
        """Get the number of active tracks"""
        return len([t for t in self.tracks.values() if t.hits >= 3 and t.time_since_update <= 1])
    
    def reset(self):
        """Reset tracker state"""
        self.tracks.clear()
        self.next_id = 0 