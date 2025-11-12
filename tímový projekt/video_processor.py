"""
Video Processing Service
Coordinates camera stream, object detection, and light control
"""

import cv2
import numpy as np
import time
import threading
import logging
from typing import Optional, List
from datetime import datetime

from camera import CameraStream
from detector import ObjectDetector, Detection
from light_controller import LightController

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VideoProcessor:
    """Main video processing service"""
    
    def __init__(self, camera: CameraStream, detector: ObjectDetector, 
                 light_controller: LightController, config: dict):
        self.camera = camera
        self.detector = detector
        self.light_controller = light_controller
        self.config = config
        
        self.is_running = False
        self.is_paused = False
        self.processing_thread: Optional[threading.Thread] = None
        
        # Frame processing settings
        self.frame_interval = config.get('frame_interval', 1)
        self.frame_counter = 0
        
        # Statistics
        self.stats = {
            'frames_processed': 0,
            'total_detections': 0,
            'trigger_detections': 0,
            'start_time': None,
            'fps': 0,
            'avg_processing_time': 0
        }
        
        # Latest frame and detections (for streaming)
        self.latest_frame: Optional[np.ndarray] = None
        self.latest_all_detections: List[Detection] = []
        self.latest_filtered_detections: List[Detection] = []
        self.frame_lock = threading.Lock()
        
        # Detection history for logging
        self.detection_history = []
        self.max_history = 1000
    
    def start(self):
        """Start video processing"""
        if self.is_running:
            logger.warning("Video processor already running")
            return
        
        logger.info("Starting video processor...")
        
        # Connect to camera
        if not self.camera.is_opened:
            if not self.camera.connect():
                logger.error("Failed to connect to camera")
                return
        
        self.is_running = True
        self.stats['start_time'] = time.time()
        
        # Start processing thread
        self.processing_thread = threading.Thread(target=self._process_loop, daemon=True)
        self.processing_thread.start()
        
        logger.info("Video processor started")
    
    def stop(self):
        """Stop video processing"""
        if not self.is_running:
            return
        
        logger.info("Stopping video processor...")
        self.is_running = False
        
        if self.processing_thread:
            self.processing_thread.join(timeout=5.0)
        
        # Turn off lights
        self.light_controller.turn_off()
        
        logger.info("Video processor stopped")
    
    def pause(self):
        """Pause processing"""
        self.is_paused = True
        logger.info("Video processor paused")
    
    def resume(self):
        """Resume processing"""
        self.is_paused = False
        logger.info("Video processor resumed")
    
    def _process_loop(self):
        """Main processing loop"""
        logger.info("Processing loop started")
        
        processing_times = []
        
        while self.is_running:
            try:
                # Check if paused
                if self.is_paused:
                    time.sleep(0.1)
                    continue
                
                # Read frame
                ret, frame = self.camera.read_frame()
                if not ret or frame is None:
                    logger.warning("Failed to read frame, attempting to reconnect...")
                    if not self.camera.reconnect():
                        logger.error("Camera reconnection failed")
                        break
                    continue
                
                self.frame_counter += 1
                
                # Process only every N frames
                if self.frame_counter % self.frame_interval != 0:
                    continue
                
                # Process frame
                start_time = time.time()
                self._process_frame(frame)
                processing_time = time.time() - start_time
                
                # Update statistics
                processing_times.append(processing_time)
                if len(processing_times) > 30:
                    processing_times.pop(0)
                
                self.stats['avg_processing_time'] = sum(processing_times) / len(processing_times)
                
                # Calculate FPS
                elapsed = time.time() - self.stats['start_time']
                if elapsed > 0:
                    self.stats['fps'] = self.stats['frames_processed'] / elapsed
                
                # Small delay to prevent CPU overload
                time.sleep(0.001)
            
            except Exception as e:
                logger.error(f"Error in processing loop: {e}", exc_info=True)
                time.sleep(1)
        
        logger.info("Processing loop ended")
    
    def _process_frame(self, frame: np.ndarray):
        """
        Process a single frame
        
        Args:
            frame: Input frame from camera
        """
        # Detect objects
        all_detections, filtered_detections = self.detector.detect_and_filter(frame)
        
        # Update statistics
        self.stats['frames_processed'] += 1
        self.stats['total_detections'] += len(all_detections)
        self.stats['trigger_detections'] += len(filtered_detections)
        
        # Get frame dimensions for relative area calculation
        frame_height, frame_width = frame.shape[:2]
        frame_size = (frame_width, frame_height)
        
        # Control lights based on detections (dynamic brightness)
        self.light_controller.update_from_detections(filtered_detections, frame_size)
        
        # Log detection if any
        if len(filtered_detections) > 0:
            self._log_detection(filtered_detections)
        
        # Get current brightness for display
        current_brightness = self.light_controller.current_brightness
        
        # Draw detections on frame with brightness indicator
        annotated_frame = self.detector.draw_detections(frame, all_detections, 
                                                        filtered_detections, current_brightness)
        
        # Add additional info
        self._add_info_overlay(annotated_frame)
        
        # Store latest frame and detections (thread-safe)
        with self.frame_lock:
            self.latest_frame = annotated_frame.copy()
            self.latest_all_detections = all_detections
            self.latest_filtered_detections = filtered_detections
    
    def _add_info_overlay(self, frame: np.ndarray):
        """Add information overlay to frame"""
        # Light status
        light_status = self.light_controller.get_status()
        light_text = f"Light: {light_status['state'].upper()} ({light_status['current_brightness']}%)"
        cv2.putText(frame, light_text, (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        # FPS
        fps_text = f"FPS: {self.stats['fps']:.1f}"
        cv2.putText(frame, fps_text, (10, 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        # Processing time
        proc_text = f"Proc: {self.stats['avg_processing_time']*1000:.1f}ms"
        cv2.putText(frame, proc_text, (10, 120),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
    
    def _log_detection(self, detections: List[Detection]):
        """Log detection event"""
        timestamp = datetime.now().isoformat()
        
        detection_data = {
            'timestamp': timestamp,
            'count': len(detections),
            'objects': [d.to_dict() for d in detections]
        }
        
        self.detection_history.append(detection_data)
        
        # Limit history size
        if len(self.detection_history) > self.max_history:
            self.detection_history.pop(0)
        
        # Log to console
        objects_str = ", ".join([f"{d.class_name}({d.confidence:.2f})" for d in detections])
        logger.info(f"Detection: {objects_str}")
    
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Get the latest processed frame (thread-safe)"""
        with self.frame_lock:
            if self.latest_frame is not None:
                return self.latest_frame.copy()
        return None
    
    def get_status(self) -> dict:
        """Get current processor status"""
        with self.frame_lock:
            current_detections = len(self.latest_filtered_detections)
        
        return {
            'is_running': self.is_running,
            'is_paused': self.is_paused,
            'stats': self.stats,
            'camera': self.camera.get_stats(),
            'lights': self.light_controller.get_status(),
            'current_detections': current_detections
        }
    
    def get_detection_history(self, limit: int = 100) -> list:
        """Get recent detection history"""
        return self.detection_history[-limit:]
    
    def reset_stats(self):
        """Reset statistics"""
        self.stats = {
            'frames_processed': 0,
            'total_detections': 0,
            'trigger_detections': 0,
            'start_time': time.time() if self.is_running else None,
            'fps': 0,
            'avg_processing_time': 0
        }
        logger.info("Statistics reset")
