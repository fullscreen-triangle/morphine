import cv2
import numpy as np
import time
from typing import List, Dict, Any, Optional, Tuple
import logging

from ..vibrio.detector import HumanDetector
from ..vibrio.tracker import HumanTracker
from ..models.analytics import (
    Detection, Track, MotionEnergy, OpticalFlowResult, 
    VibrioResult
)

logger = logging.getLogger(__name__)

class SpeedEstimator:
    """Estimates speed of tracked objects"""
    
    def __init__(self, fps: float = 30.0, pixel_to_meter: float = 0.01):
        self.fps = fps
        self.pixel_to_meter = pixel_to_meter  # Conversion factor
        self.track_history = {}
        
    def estimate_speed(self, track: Track) -> float:
        """Estimate speed for a track in km/h"""
        track_id = track.track_id
        current_time = time.time()
        
        if track_id not in self.track_history:
            self.track_history[track_id] = {
                'positions': [track.position],
                'timestamps': [current_time]
            }
            return 0.0
        
        history = self.track_history[track_id]
        history['positions'].append(track.position)
        history['timestamps'].append(current_time)
        
        # Keep only recent history (last 10 frames)
        if len(history['positions']) > 10:
            history['positions'] = history['positions'][-10:]
            history['timestamps'] = history['timestamps'][-10:]
        
        # Calculate speed if we have enough data
        if len(history['positions']) >= 2:
            # Use last two positions for speed calculation
            pos1 = np.array(history['positions'][-2])
            pos2 = np.array(history['positions'][-1])
            time1 = history['timestamps'][-2]
            time2 = history['timestamps'][-1]
            
            # Calculate distance in pixels
            pixel_distance = np.linalg.norm(pos2 - pos1)
            
            # Convert to meters
            meter_distance = pixel_distance * self.pixel_to_meter
            
            # Calculate time difference
            time_diff = time2 - time1
            
            if time_diff > 0:
                # Speed in m/s
                speed_ms = meter_distance / time_diff
                # Convert to km/h
                speed_kmh = speed_ms * 3.6
                
                # Update track with calculated speed
                track.speed = speed_kmh
                return speed_kmh
        
        return 0.0

class OpticalAnalyzer:
    """Optical flow and motion analysis"""
    
    def __init__(self):
        self.previous_frame = None
        self.flow_params = dict(
            pyr_scale=0.5,
            levels=3,
            winsize=15,
            iterations=3,
            poly_n=5,
            poly_sigma=1.2,
            flags=0
        )
        
    def analyze_optical_flow(self, frame: np.ndarray) -> OpticalFlowResult:
        """Analyze optical flow in the frame"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if self.previous_frame is None:
            self.previous_frame = gray.copy()
            return OpticalFlowResult(
                flow_magnitude=0.0,
                flow_direction=[0.0, 0.0],
                flow_vectors=[]
            )
        
        # Calculate dense optical flow
        flow = cv2.calcOpticalFlowPyrLK(
            self.previous_frame, gray, None, None, **self.flow_params
        )
        
        if flow[0] is not None and len(flow[0]) > 0:
            # Calculate flow statistics
            flow_vectors = []
            if len(flow[0]) > 0:
                for i in range(len(flow[0])):
                    if flow[1][i] == 1:  # Good flow point
                        old_pt = flow[0][i]
                        new_pt = flow[2][i] if len(flow) > 2 and flow[2] is not None and i < len(flow[2]) else old_pt
                        flow_vectors.append([new_pt[0] - old_pt[0], new_pt[1] - old_pt[1]])
            
            if flow_vectors:
                flow_vectors = np.array(flow_vectors)
                magnitudes = np.linalg.norm(flow_vectors, axis=1)
                avg_magnitude = np.mean(magnitudes)
                avg_direction = np.mean(flow_vectors, axis=0).tolist()
            else:
                avg_magnitude = 0.0
                avg_direction = [0.0, 0.0]
                flow_vectors = []
        else:
            avg_magnitude = 0.0
            avg_direction = [0.0, 0.0]
            flow_vectors = []
        
        self.previous_frame = gray.copy()
        
        return OpticalFlowResult(
            flow_magnitude=float(avg_magnitude),
            flow_direction=avg_direction,
            flow_vectors=flow_vectors.tolist() if len(flow_vectors) > 0 else []
        )
    
    def analyze_motion_energy(self, frame: np.ndarray) -> MotionEnergy:
        """Analyze motion energy in the frame"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if self.previous_frame is None:
            self.previous_frame = gray.copy()
            return MotionEnergy(
                motion_energy=0.0,
                motion_regions=[],
                motion_vectors=[],
                dominant_direction=[0.0, 0.0]
            )
        
        # Calculate frame difference
        diff = cv2.absdiff(self.previous_frame, gray)
        
        # Threshold to get motion regions
        _, motion_mask = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
        
        # Calculate motion energy as percentage of moving pixels
        total_pixels = motion_mask.size
        moving_pixels = cv2.countNonZero(motion_mask)
        motion_energy = moving_pixels / total_pixels
        
        # Find motion regions (contours)
        contours, _ = cv2.findContours(motion_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        motion_regions = []
        motion_vectors = []
        
        for contour in contours:
            if cv2.contourArea(contour) > 100:  # Filter small regions
                x, y, w, h = cv2.boundingRect(contour)
                motion_regions.append([float(x), float(y), float(w), float(h)])
                
                # Calculate motion vector for this region
                center = [x + w/2, y + h/2]
                motion_vectors.append(center)
        
        # Calculate dominant motion direction
        if motion_vectors:
            motion_vectors = np.array(motion_vectors)
            # Simple approach: average of motion vector positions
            dominant_direction = np.mean(motion_vectors, axis=0).tolist()
        else:
            dominant_direction = [0.0, 0.0]
        
        return MotionEnergy(
            motion_energy=float(motion_energy),
            motion_regions=motion_regions,
            motion_vectors=[v.tolist() for v in motion_vectors] if motion_vectors else [],
            dominant_direction=dominant_direction
        )

class VibrioAnalyzer:
    """Main Vibrio framework analyzer integrating all components"""
    
    def __init__(self, model_path: str = "yolov8n.pt", device: str = "cpu"):
        self.detector = HumanDetector(model_path)
        self.tracker = HumanTracker()
        self.speed_estimator = SpeedEstimator()
        self.optical_analyzer = OpticalAnalyzer()
        self.device = device
        
    async def initialize(self):
        """Initialize all components"""
        # Download YOLO model if needed
        try:
            import ultralytics
            model = ultralytics.YOLO("yolov8n.pt")  # This will download if not present
            logger.info("YOLO model initialized")
        except Exception as e:
            logger.warning(f"Could not initialize YOLO model: {e}")
        
        logger.info("Vibrio analyzer initialized")
    
    async def analyze_frame(self, frame: np.ndarray, timestamp: float) -> VibrioResult:
        """Analyze a single frame with the complete Vibrio pipeline"""
        start_time = time.time()
        
        try:
            # 1. Human detection
            detections = self.detector.detect_humans(frame)
            
            # 2. Object tracking
            tracks = self.tracker.update(detections)
            
            # 3. Speed estimation for each track
            for track in tracks:
                self.speed_estimator.estimate_speed(track)
            
            # 4. Optical flow analysis
            optical_flow = self.optical_analyzer.analyze_optical_flow(frame)
            
            # 5. Motion energy analysis
            motion_energy = self.optical_analyzer.analyze_motion_energy(frame)
            
            # 6. Frame statistics
            frame_stats = {
                "frame_shape": list(frame.shape),
                "detection_count": len(detections),
                "track_count": len(tracks),
                "avg_confidence": np.mean([d.confidence for d in detections]) if detections else 0.0,
                "max_speed": max([t.speed for t in tracks]) if tracks else 0.0,
                "processing_time": time.time() - start_time
            }
            
            # Create result
            result = VibrioResult(
                detections=detections,
                tracks=tracks,
                motion_energy=motion_energy,
                optical_flow=optical_flow,
                frame_stats=frame_stats
            )
            
            logger.debug(f"Vibrio analysis complete: {len(detections)} detections, {len(tracks)} tracks")
            return result
            
        except Exception as e:
            logger.error(f"Vibrio analysis failed: {e}")
            # Return empty result on error
            return VibrioResult(
                detections=[],
                tracks=[],
                motion_energy=MotionEnergy(
                    motion_energy=0.0,
                    motion_regions=[],
                    motion_vectors=[],
                    dominant_direction=[0.0, 0.0]
                ),
                optical_flow=OpticalFlowResult(
                    flow_magnitude=0.0,
                    flow_direction=[0.0, 0.0],
                    flow_vectors=[]
                ),
                frame_stats={"error": str(e)}
            )
    
    def get_track_count(self) -> int:
        """Get the number of active tracks"""
        return self.tracker.get_track_count()
    
    def reset(self):
        """Reset all analyzers"""
        self.tracker.reset()
        self.optical_analyzer.previous_frame = None
        self.speed_estimator.track_history.clear()
        logger.info("Vibrio analyzer reset") 