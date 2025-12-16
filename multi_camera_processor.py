"""
Multi-Camera Video Processing Service
Coordinates multiple camera streams, object detection, and light control
"""

import cv2
import numpy as np
import time
import threading
import logging
from typing import Optional, List, Dict
from datetime import datetime

from camera import CameraStream
from detector import ObjectDetector, Detection
from light_controller import LightController

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CameraProcessor:
    """Handles processing for a single camera"""
    
    def __init__(self, camera_id: str, camera: CameraStream, detector: ObjectDetector, config: dict):
        self.camera_id = camera_id
        self.camera = camera
        self.detector = detector
        self.config = config
        
        # Latest frame and detections
        self.latest_frame: Optional[np.ndarray] = None
        self.latest_all_detections: List[Detection] = []
        self.latest_filtered_detections: List[Detection] = []
        self.frame_lock = threading.Lock()
        
        # Statistics
        self.stats = {
            'frames_processed': 0,
            'total_detections': 0,
            'trigger_detections': 0,
            'fps': 0,
            'avg_processing_time': 0
        }
        
        self.last_process_time = time.time()
        self.processing_times = []
        
    def process_frame(self) -> bool:
        """Process a single frame from this camera"""
        success, frame = self.camera.read_frame()
        if not success or frame is None:
            return False
        
        start_time = time.time()
        
        # Run detection
        all_detections = self.detector.detect(frame)
        filtered_detections = self.detector.filter_detections(all_detections)
        
        # Draw detections on frame
        annotated_frame = frame.copy()
        for detection in all_detections:
            color = (0, 255, 0) if detection in filtered_detections else (255, 0, 0)
            x1, y1, x2, y2 = detection.bbox
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
            
            label = f"{detection.class_name} {detection.confidence:.2f}"
            cv2.putText(annotated_frame, label, (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # Add camera ID label
        cv2.putText(annotated_frame, f"Camera: {self.camera_id}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        # Update stored data
        with self.frame_lock:
            self.latest_frame = annotated_frame
            self.latest_all_detections = all_detections
            self.latest_filtered_detections = filtered_detections
        
        # Update statistics
        process_time = time.time() - start_time
        self.processing_times.append(process_time)
        if len(self.processing_times) > 30:
            self.processing_times.pop(0)
        
        self.stats['frames_processed'] += 1
        self.stats['total_detections'] = len(all_detections)
        self.stats['trigger_detections'] = len(filtered_detections)
        self.stats['avg_processing_time'] = sum(self.processing_times) / len(self.processing_times)
        
        # Calculate FPS
        current_time = time.time()
        if current_time - self.last_process_time > 0:
            self.stats['fps'] = 1.0 / (current_time - self.last_process_time)
        self.last_process_time = current_time
        
        return True
    
    def get_frame(self) -> Optional[np.ndarray]:
        """Get the latest processed frame"""
        with self.frame_lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None
    
    def get_detections(self) -> tuple:
        """Get the latest detections"""
        with self.frame_lock:
            return self.latest_all_detections.copy(), self.latest_filtered_detections.copy()
    
    def get_people_count(self) -> int:
        """Get current people count"""
        with self.frame_lock:
            return len(self.latest_filtered_detections)


class MultiCameraProcessor:
    """Multi-camera video processing service"""
    
    def __init__(self, cameras: Dict[str, CameraStream], detector: ObjectDetector, 
                 light_controller: LightController, config: dict):
        self.cameras = cameras
        self.detector = detector
        self.light_controller = light_controller
        self.config = config
        
        # Create processor for each camera
        self.camera_processors = {
            camera_id: CameraProcessor(camera_id, camera, detector, config)
            for camera_id, camera in cameras.items()
        }
        
        self.is_running = False
        self.is_paused = False
        self.processing_threads: Dict[str, threading.Thread] = {}
        self.light_control_thread: Optional[threading.Thread] = None
        
        # Frame processing settings
        self.frame_interval = config.get('frame_interval', 1)
        
        # Overall statistics
        self.stats = {
            'frames_processed': 0,
            'start_time': None,
            'cameras': {}
        }
        
        # Detection history for logging
        self.detection_history = []
        self.max_history = 1000
        
        # Active camera for streaming (can switch between cameras)
        self.active_camera_id = list(cameras.keys())[0] if cameras else None
    
    def start(self):
        """Start multi-camera video processing"""
        if self.is_running:
            logger.warning("Multi-camera processor already running")
            return
        
        logger.info("Starting multi-camera processor...")
        
        # Connect to all cameras
        all_connected = True
        for camera_id, camera in self.cameras.items():
            if not camera.is_opened:
                if not camera.connect():
                    logger.error(f"Failed to connect to camera {camera_id}")
                    all_connected = False
                else:
                    logger.info(f"Connected to camera {camera_id}")
        
        if not all_connected:
            logger.error("Failed to connect to all cameras")
            return
        
        self.is_running = True
        self.stats['start_time'] = time.time()
        
        # Start processing thread for each camera
        for camera_id in self.cameras.keys():
            thread = threading.Thread(
                target=self._camera_process_loop,
                args=(camera_id,),
                daemon=True,
                name=f"CameraProcessor-{camera_id}"
            )
            thread.start()
            self.processing_threads[camera_id] = thread
            logger.info(f"Started processing thread for camera {camera_id}")
        
        # Start light control thread
        self.light_control_thread = threading.Thread(
            target=self._light_control_loop,
            daemon=True,
            name="LightControl"
        )
        self.light_control_thread.start()
        logger.info("Started light control thread")
        
        logger.info("Multi-camera processor started")
    
    def stop(self):
        """Stop video processing"""
        if not self.is_running:
            return
        
        logger.info("Stopping multi-camera processor...")
        self.is_running = False
        
        # Wait for all threads to finish
        for camera_id, thread in self.processing_threads.items():
            if thread:
                thread.join(timeout=5.0)
                logger.info(f"Stopped processing thread for camera {camera_id}")
        
        if self.light_control_thread:
            self.light_control_thread.join(timeout=5.0)
        
        # Disconnect all cameras
        for camera_id, camera in self.cameras.items():
            camera.disconnect()
            logger.info(f"Disconnected camera {camera_id}")
        
        # Turn off lights
        self.light_controller.turn_off()
        
        logger.info("Multi-camera processor stopped")
    
    def _camera_process_loop(self, camera_id: str):
        """Processing loop for a single camera"""
        processor = self.camera_processors[camera_id]
        frame_counter = 0
        
        logger.info(f"Processing loop started for camera {camera_id}")
        
        while self.is_running:
            if self.is_paused:
                time.sleep(0.1)
                continue
            
            # Process every Nth frame
            if frame_counter % self.frame_interval == 0:
                success = processor.process_frame()
                if not success:
                    logger.warning(f"Failed to process frame from camera {camera_id}")
                    time.sleep(1.0)  # Wait before retrying
            
            frame_counter += 1
            
            # Small sleep to prevent busy-waiting
            time.sleep(0.001)
        
        logger.info(f"Processing loop ended for camera {camera_id}")
    
    def _light_control_loop(self):
        """Separate thread for light control logic"""
        logger.info("Light control loop started")
        last_light_state = False
        last_person_seen_time = None
        lights_off_delay = 30.0  # 30 seconds delay before turning off lights
        
        while self.is_running:
            if self.is_paused:
                time.sleep(0.1)
                continue
            
            # Aggregate detection results from all cameras
            total_people = 0
            any_camera_has_people = False
            
            for processor in self.camera_processors.values():
                people_count = processor.get_people_count()
                total_people += people_count
                if people_count > 0:
                    any_camera_has_people = True
            
            current_time = time.time()
            
            # Update last seen time if people are detected
            if any_camera_has_people:
                last_person_seen_time = current_time
            
            # Determine if lights should be on
            should_turn_on = False
            if any_camera_has_people:
                # People currently detected
                should_turn_on = True
            elif last_person_seen_time is not None:
                # Check if we're still within the delay period
                time_since_last_person = current_time - last_person_seen_time
                if time_since_last_person < lights_off_delay:
                    should_turn_on = True
            
            if should_turn_on and not last_light_state:
                # Turn on lights
                brightness = self.config.get('light_on_brightness', 100)
                self.light_controller.set_brightness(brightness)
                logger.info(f"Lights turned ON (detected {total_people} people across all cameras)")
                self._log_detection(f"Lights ON - {total_people} people detected")
                last_light_state = True
                
            elif not should_turn_on and last_light_state:
                # Turn off lights (after 30 second delay)
                self.light_controller.turn_off()
                logger.info("Lights turned OFF (no people detected for 30 seconds)")
                self._log_detection("Lights OFF - no people detected for 30 seconds")
                last_light_state = False
            
            time.sleep(0.1)  # Check 10 times per second
        
        logger.info("Light control loop ended")
    
    def _log_detection(self, message: str):
        """Log detection event"""
        entry = {
            'timestamp': datetime.now(),
            'message': message
        }
        self.detection_history.append(entry)
        
        # Keep history size limited
        if len(self.detection_history) > self.max_history:
            self.detection_history.pop(0)
    
    def get_combined_frame(self) -> Optional[np.ndarray]:
        """Get combined frame from all cameras (side by side)"""
        frames = []
        for camera_id in sorted(self.cameras.keys()):
            processor = self.camera_processors[camera_id]
            frame = processor.get_frame()
            if frame is not None:
                frames.append(frame)
        
        if not frames:
            return None
        
        # Resize frames to same height
        target_height = 480
        resized_frames = []
        for frame in frames:
            h, w = frame.shape[:2]
            new_width = int(w * (target_height / h))
            resized = cv2.resize(frame, (new_width, target_height))
            resized_frames.append(resized)
        
        # Combine horizontally
        combined = np.hstack(resized_frames)
        return combined
    
    def get_active_camera_frame(self) -> Optional[np.ndarray]:
        """Get frame from the active camera"""
        if self.active_camera_id not in self.camera_processors:
            return None
        return self.camera_processors[self.active_camera_id].get_frame()
    
    def set_active_camera(self, camera_id: str):
        """Set which camera to stream"""
        if camera_id in self.camera_processors:
            self.active_camera_id = camera_id
            logger.info(f"Active camera set to {camera_id}")
    
    def get_status(self) -> dict:
        """Get current system status"""
        # Aggregate statistics from all cameras
        total_people = 0
        total_objects = 0
        avg_fps = 0
        
        camera_stats = {}
        for camera_id, processor in self.camera_processors.items():
            people_count = processor.get_people_count()
            total_people += people_count
            total_objects += processor.stats['total_detections']
            avg_fps += processor.stats['fps']
            
            camera_stats[camera_id] = {
                'frames_processed': processor.stats['frames_processed'],
                'people_count': people_count,
                'total_detections': processor.stats['total_detections'],
                'fps': round(processor.stats['fps'], 2),
                'avg_processing_time': round(processor.stats['avg_processing_time'], 3)
            }
        
        if self.camera_processors:
            avg_fps /= len(self.camera_processors)
        
        # Get light status
        light_brightness = self.light_controller.get_current_brightness()
        
        uptime = 0
        if self.stats['start_time']:
            uptime = time.time() - self.stats['start_time']
        
        return {
            'running': self.is_running,
            'paused': self.is_paused,
            'uptime': round(uptime, 1),
            'people_count': total_people,
            'total_objects': total_objects,
            'fps': round(avg_fps, 2),
            'light_brightness': light_brightness,
            'light_on': light_brightness > 0,
            'active_camera': self.active_camera_id,
            'cameras': camera_stats,
            'available_cameras': [
                {'id': cid, 'name': f"Camera {cid}"} 
                for cid in self.cameras.keys()
            ],
            'recent_detections': [
                {
                    'timestamp': entry['timestamp'].isoformat(),
                    'message': entry['message']
                }
                for entry in self.detection_history[-10:]
            ]
        }
    
    def pause(self):
        """Pause processing"""
        self.is_paused = True
        logger.info("Multi-camera processor paused")
    
    def resume(self):
        """Resume processing"""
        self.is_paused = False
        logger.info("Multi-camera processor resumed")
