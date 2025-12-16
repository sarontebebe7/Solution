"""
Object Detection Module using YOLOv8
Handles object detection, classification, and filtering based on size/type
"""

import cv2
import numpy as np
from ultralytics import YOLO
from typing import List, Dict, Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Detection:
    """Represents a single detected object"""
    
    def __init__(self, class_name: str, confidence: float, bbox: Tuple[int, int, int, int]):
        self.class_name = class_name
        self.confidence = confidence
        self.bbox = bbox  # (x1, y1, x2, y2)
        self.area = self._calculate_area()
    
    def _calculate_area(self) -> int:
        """Calculate bounding box area"""
        x1, y1, x2, y2 = self.bbox
        return (x2 - x1) * (y2 - y1)
    
    def get_center(self) -> Tuple[int, int]:
        """Get center point of bounding box"""
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) // 2, (y1 + y2) // 2)
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "class": self.class_name,
            "confidence": float(self.confidence),
            "bbox": self.bbox,
            "area": self.area,
            "center": self.get_center()
        }


class ObjectDetector:
    """YOLOv8-based object detector with filtering capabilities"""
    
    def __init__(self, config: dict):
        self.config = config
        self.model_name = config.get('model', 'yolov8n')
        self.confidence_threshold = config.get('confidence', 0.5)
        self.target_classes = config.get('target_classes', ['person'])
        self.ignore_classes = config.get('ignore_classes', [])
        self.min_size = config.get('min_object_size', 5000)
        self.max_size = config.get('max_object_size', 300000)
        
        # Load YOLOv8 model
        logger.info(f"Loading YOLOv8 model: {self.model_name}")
        try:
            self.model = YOLO(f"{self.model_name}.pt")
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise
        
        # COCO class names (YOLOv8 uses COCO dataset)
        self.class_names = self.model.names
    
    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        Detect objects in a frame
        
        Args:
            frame: Input image/frame (numpy array)
        
        Returns:
            List of Detection objects
        """
        try:
            # Run inference
            results = self.model(frame, conf=self.confidence_threshold, verbose=False)
            
            detections = []
            
            # Process results
            for result in results:
                boxes = result.boxes
                
                for box in boxes:
                    # Get box coordinates
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                    
                    # Get confidence and class
                    confidence = float(box.conf[0].cpu().numpy())
                    class_id = int(box.cls[0].cpu().numpy())
                    class_name = self.class_names[class_id]
                    
                    # Create detection object
                    detection = Detection(class_name, confidence, (x1, y1, x2, y2))
                    detections.append(detection)
            
            return detections
        
        except Exception as e:
            logger.error(f"Error during detection: {e}")
            return []
    
    def filter_detections(self, detections: List[Detection]) -> List[Detection]:
        """
        Filter detections based on class and size
        
        Args:
            detections: List of all detections
        
        Returns:
            List of filtered detections
        """
        filtered = []
        
        for detection in detections:
            # Check if class should be ignored
            if detection.class_name in self.ignore_classes:
                logger.debug(f"Ignoring {detection.class_name} (in ignore list)")
                continue
            
            # Check if class is in target list (if specified)
            if self.target_classes and detection.class_name not in self.target_classes:
                logger.debug(f"Ignoring {detection.class_name} (not in target list)")
                continue
            
            # Check size constraints
            if detection.area < self.min_size:
                logger.debug(f"Ignoring {detection.class_name} (too small: {detection.area} < {self.min_size})")
                continue
            
            if detection.area > self.max_size:
                logger.debug(f"Ignoring {detection.class_name} (too large: {detection.area} > {self.max_size})")
                continue
            
            # Detection passes all filters
            filtered.append(detection)
        
        return filtered
    
    def detect_and_filter(self, frame: np.ndarray) -> Tuple[List[Detection], List[Detection]]:
        """
        Detect and filter objects in one call
        
        Args:
            frame: Input image/frame
        
        Returns:
            Tuple of (all_detections, filtered_detections)
        """
        all_detections = self.detect(frame)
        filtered_detections = self.filter_detections(all_detections)
        
        logger.debug(f"Detected {len(all_detections)} objects, {len(filtered_detections)} passed filters")
        
        return all_detections, filtered_detections
    
    def draw_detections(self, frame: np.ndarray, detections: List[Detection], 
                       filtered_detections: List[Detection], brightness: int = 0) -> np.ndarray:
        """
        Draw bounding boxes and labels on frame
        
        Args:
            frame: Input frame
            detections: All detections (drawn in gray)
            filtered_detections: Filtered detections (drawn in green)
            brightness: Current light brightness (0-100)
        
        Returns:
            Frame with drawn detections
        """
        output_frame = frame.copy()
        
        # Draw all detections in gray
        for detection in detections:
            if detection not in filtered_detections:
                x1, y1, x2, y2 = detection.bbox
                cv2.rectangle(output_frame, (x1, y1), (x2, y2), (128, 128, 128), 2)
                
                label = f"{detection.class_name}: {detection.confidence:.2f}"
                cv2.putText(output_frame, label, (x1, y1 - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (128, 128, 128), 2)
        
        # Draw filtered detections in green (these trigger lights)
        for detection in filtered_detections:
            x1, y1, x2, y2 = detection.bbox
            cv2.rectangle(output_frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
            
            label = f"{detection.class_name}: {detection.confidence:.2f} (Area: {detection.area})"
            cv2.putText(output_frame, label, (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # Add status text
        status_text = f"Detections: {len(detections)} | Triggers: {len(filtered_detections)}"
        cv2.putText(output_frame, status_text, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Draw brightness indicator - LARGE VISUAL BAR
        self._draw_brightness_indicator(output_frame, brightness, len(filtered_detections) > 0)
        
        return output_frame
    
    def _draw_brightness_indicator(self, frame: np.ndarray, brightness: int, is_detecting: bool):
        """
        Draw a large visual brightness indicator on the frame
        
        Args:
            frame: Frame to draw on
            brightness: Current brightness (0-100)
            is_detecting: Whether objects are currently detected
        """
        height, width = frame.shape[:2]
        
        # Position for brightness bar (top-right corner)
        bar_width = 250
        bar_height = 60
        bar_x = width - bar_width - 20
        bar_y = 20
        
        # Draw background with semi-transparency
        overlay = frame.copy()
        
        # Background box
        cv2.rectangle(overlay, (bar_x - 10, bar_y - 10), 
                     (bar_x + bar_width + 10, bar_y + bar_height + 10),
                     (40, 40, 40), -1)
        
        # Blend overlay
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
        # Title
        title = "💡 LIGHT BRIGHTNESS"
        cv2.putText(frame, title, (bar_x, bar_y + 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Brightness bar background (gray)
        bar_inner_y = bar_y + 30
        bar_inner_height = 20
        cv2.rectangle(frame, (bar_x, bar_inner_y), 
                     (bar_x + bar_width, bar_inner_y + bar_inner_height),
                     (80, 80, 80), -1)
        
        # Brightness bar filled portion (colored based on level)
        if brightness > 0:
            filled_width = int((brightness / 100) * bar_width)
            
            # Color gradient based on brightness
            if brightness < 30:
                color = (100, 100, 255)  # Blue - low
            elif brightness < 70:
                color = (0, 255, 255)    # Yellow - medium
            else:
                color = (0, 255, 0)      # Green - high
            
            # Add glow effect if detecting
            if is_detecting:
                color = (0, 255, 255)  # Bright yellow when actively detecting
                # Pulsing effect
                import time
                pulse = int(abs(np.sin(time.time() * 5)) * 50)
                color = tuple(min(255, c + pulse) for c in color)
            
            cv2.rectangle(frame, (bar_x, bar_inner_y), 
                         (bar_x + filled_width, bar_inner_y + bar_inner_height),
                         color, -1)
        
        # Brightness text
        status = "ON" if brightness > 0 else "OFF"
        status_color = (0, 255, 0) if brightness > 0 else (128, 128, 128)
        text = f"{brightness}% - {status}"
        
        if is_detecting:
            text = f"{brightness}% - DETECTING!"
            status_color = (0, 255, 255)
        
        cv2.putText(frame, text, (bar_x + bar_width + 15, bar_inner_y + 15),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
        
        # Draw light bulb icon indicator
        icon_x = bar_x - 40
        icon_y = bar_y + 30
        
        if brightness > 0:
            # Lit bulb (circle with rays)
            cv2.circle(frame, (icon_x, icon_y), 15, (0, 255, 255), -1)
            # Rays
            for angle in range(0, 360, 45):
                rad = np.radians(angle)
                x1 = int(icon_x + 18 * np.cos(rad))
                y1 = int(icon_y + 18 * np.sin(rad))
                x2 = int(icon_x + 25 * np.cos(rad))
                y2 = int(icon_y + 25 * np.sin(rad))
                cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
        else:
            # Dark bulb
            cv2.circle(frame, (icon_x, icon_y), 15, (80, 80, 80), -1)
    
    def update_config(self, new_config: dict):
        """Update detector configuration"""
        self.config.update(new_config)
        self.confidence_threshold = self.config.get('confidence', self.confidence_threshold)
        self.target_classes = self.config.get('target_classes', self.target_classes)
        self.ignore_classes = self.config.get('ignore_classes', self.ignore_classes)
        self.min_size = self.config.get('min_object_size', self.min_size)
        self.max_size = self.config.get('max_object_size', self.max_size)
        logger.info("Detector configuration updated")
