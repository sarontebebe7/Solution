"""
Camera Stream Handler
Supports multiple video sources: webcam, IP cameras, RTSP, HTTP streams, video files
"""

import cv2
import numpy as np
from typing import Optional, Tuple
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CameraStream:
    """Handles video capture from various sources"""
    
    def __init__(self, config: dict):
        self.config = config
        self.source = config.get('source', '0')
        self.backup_sources = config.get('backup_sources', [])
        self.fps = config.get('fps', 30)
        self.resolution = config.get('resolution', {'width': 640, 'height': 480})
        
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_opened = False
        self.frame_count = 0
        self.last_frame_time = 0
        
        # Convert string "0" to integer for webcam
        if isinstance(self.source, str) and self.source.isdigit():
            self.source = int(self.source)
    
    def connect(self) -> bool:
        """
        Connect to camera source
        
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Attempting to connect to camera source: {self.source}")
        
        try:
            # Try main source
            if self._try_connect(self.source):
                return True
            
            # Try backup sources
            logger.warning(f"Failed to connect to primary source: {self.source}")
            for backup in self.backup_sources:
                logger.info(f"Trying backup source: {backup}")
                if isinstance(backup, str) and backup.isdigit():
                    backup = int(backup)
                
                if self._try_connect(backup):
                    self.source = backup
                    return True
            
            logger.error("Failed to connect to any camera source")
            return False
        
        except Exception as e:
            logger.error(f"Error connecting to camera: {e}")
            return False
    
    def _try_connect(self, source) -> bool:
        """
        Try to connect to a specific source
        
        Args:
            source: Camera source (int, str URL, or file path)
        
        Returns:
            True if successful
        """
        try:
            self.cap = cv2.VideoCapture(source)
            
            # Wait a bit for connection to establish
            time.sleep(0.5)
            
            if not self.cap.isOpened():
                return False
            
            # Try to read a frame to verify
            ret, frame = self.cap.read()
            if not ret or frame is None:
                self.cap.release()
                return False
            
            # Set resolution if it's a webcam
            if isinstance(source, int):
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution['width'])
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution['height'])
                self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            
            self.is_opened = True
            logger.info(f"Successfully connected to camera: {source}")
            
            # Log camera properties
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(self.cap.get(cv2.CAP_PROP_FPS))
            logger.info(f"Camera properties - Resolution: {width}x{height}, FPS: {fps}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error trying to connect to {source}: {e}")
            return False
    
    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Read a frame from the camera
        
        Returns:
            Tuple of (success, frame)
        """
        if not self.is_opened or self.cap is None:
            logger.error("Camera not connected")
            return False, None
        
        try:
            ret, frame = self.cap.read()
            
            if not ret or frame is None:
                logger.warning("Failed to read frame")
                return False, None
            
            self.frame_count += 1
            self.last_frame_time = time.time()
            
            return True, frame
        
        except Exception as e:
            logger.error(f"Error reading frame: {e}")
            return False, None
    
    def get_frame_rate(self) -> float:
        """Get actual frame rate"""
        if self.cap is None:
            return 0.0
        return self.cap.get(cv2.CAP_PROP_FPS)
    
    def get_resolution(self) -> Tuple[int, int]:
        """Get current resolution (width, height)"""
        if self.cap is None:
            return (0, 0)
        
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return (width, height)
    
    def get_stats(self) -> dict:
        """Get camera statistics"""
        return {
            "source": str(self.source),
            "is_opened": self.is_opened,
            "frame_count": self.frame_count,
            "resolution": self.get_resolution(),
            "fps": self.get_frame_rate(),
            "last_frame_time": self.last_frame_time
        }
    
    def reconnect(self) -> bool:
        """Reconnect to camera"""
        logger.info("Attempting to reconnect to camera")
        self.disconnect()
        return self.connect()
    
    def disconnect(self):
        """Disconnect from camera"""
        if self.cap is not None:
            logger.info("Disconnecting from camera")
            self.cap.release()
            self.cap = None
            self.is_opened = False
    
    def __del__(self):
        """Cleanup on deletion"""
        self.disconnect()


class VideoFileStream(CameraStream):
    """Specialized stream for video files with looping support"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.loop = config.get('loop', True)
        self.total_frames = 0
    
    def connect(self) -> bool:
        """Connect to video file"""
        if super().connect():
            if self.cap is not None:
                self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                logger.info(f"Video file has {self.total_frames} frames")
            return True
        return False
    
    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Read frame with looping support"""
        ret, frame = super().read_frame()
        
        # If end of video and looping enabled, restart
        if not ret and self.loop and self.cap is not None:
            logger.info("End of video reached, looping...")
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.frame_count = 0
            ret, frame = super().read_frame()
        
        return ret, frame
