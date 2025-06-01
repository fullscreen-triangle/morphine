import cv2
import numpy as np
from ultralytics import YOLO
from typing import List, Tuple, Optional
import torch
from ..models.analytics import Detection

class HumanDetector:
    """YOLOv8-based human detection for the Vibrio framework"""
    
    def __init__(self, model_path: str = "yolov8n.pt", confidence_threshold: float = 0.5):
        self.model = YOLO(model_path)
        self.confidence_threshold = confidence_threshold
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Human class ID in COCO dataset
        self.human_class_id = 0
        
    def detect_humans(self, frame: np.ndarray) -> List[Detection]:
        """
        Detect humans in the given frame
        
        Args:
            frame: Input frame as numpy array
            
        Returns:
            List of Detection objects for detected humans
        """
        results = self.model(frame, device=self.device, verbose=False)
        detections = []
        
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for i, box in enumerate(boxes):
                    # Filter for human detections only
                    class_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                    
                    if class_id == self.human_class_id and confidence >= self.confidence_threshold:
                        # Get bounding box coordinates
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        bbox = [x1, y1, x2 - x1, y2 - y1]  # Convert to [x, y, width, height]
                        
                        # Calculate center point
                        center_x = x1 + (x2 - x1) / 2
                        center_y = y1 + (y2 - y1) / 2
                        center = [center_x, center_y]
                        
                        detection = Detection(
                            bbox=bbox,
                            confidence=confidence,
                            class_id=class_id,
                            center=center
                        )
                        detections.append(detection)
        
        return detections
    
    def draw_detections(self, frame: np.ndarray, detections: List[Detection]) -> np.ndarray:
        """
        Draw detection bounding boxes on the frame
        
        Args:
            frame: Input frame
            detections: List of detections to draw
            
        Returns:
            Frame with drawn detections
        """
        annotated_frame = frame.copy()
        
        for detection in detections:
            x, y, w, h = detection.bbox
            x1, y1, x2, y2 = int(x), int(y), int(x + w), int(y + h)
            
            # Draw bounding box
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Draw confidence score
            label = f"Human: {detection.confidence:.2f}"
            cv2.putText(annotated_frame, label, (x1, y1 - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Draw center point
            center_x, center_y = detection.center
            cv2.circle(annotated_frame, (int(center_x), int(center_y)), 5, (255, 0, 0), -1)
        
        return annotated_frame
    
    def get_detection_stats(self, detections: List[Detection]) -> dict:
        """
        Get statistics about detections
        
        Args:
            detections: List of detections
            
        Returns:
            Dictionary with detection statistics
        """
        if not detections:
            return {
                "total_detections": 0,
                "avg_confidence": 0.0,
                "max_confidence": 0.0,
                "detection_density": 0.0
            }
        
        confidences = [d.confidence for d in detections]
        
        return {
            "total_detections": len(detections),
            "avg_confidence": np.mean(confidences),
            "max_confidence": np.max(confidences),
            "detection_density": len(detections) / 1000  # Normalize by frame area assumption
        } 