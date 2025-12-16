"""
Camera Stream Handler
Supports multiple video sources: webcam, IP cameras, RTSP, HTTP streams, video files, MQTT cameras
"""

import cv2
import numpy as np
from typing import Optional, Tuple
import logging
import time
import subprocess

# Optional imports
try:
    from streamlink import Streamlink
    STREAMLINK_AVAILABLE = True
except ImportError:
    STREAMLINK_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Streamlink not available, HLS streams may not work")

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
        
        # MQTT camera support
        self.is_mqtt_camera = False
        self.mqtt_broker = None
        self.mqtt_port = 1883
        
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
            # Check if this is an MQTT camera by looking at config
            if self._is_mqtt_camera():
                logger.info("Detected MQTT camera configuration")
                return self._connect_mqtt_camera()
            
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
    
    def _is_mqtt_camera(self) -> bool:
        """Check if the current configuration is for an MQTT camera"""
        # Check if config has MQTT-specific fields
        return (self.config.get('type') == 'mqtt' or 
                'mqtt_broker' in self.config)
    
    def _connect_mqtt_camera(self) -> bool:
        """
        Connect to MQTT camera and get stream URL
        
        Returns:
            True if successful
        """
        try:
            # Import mqtt_camera module
            from mqtt_camera import MQTTCameraClient
            
            # Get MQTT configuration
            self.mqtt_broker = self.config.get('mqtt_broker', 'openlab.kpi.fei.tuke.sk')
            self.mqtt_port = self.config.get('mqtt_port', 1883)
            
            logger.info(f"Connecting to MQTT camera via {self.mqtt_broker}:{self.mqtt_port}")
            
            # Create MQTT client
            mqtt_client = MQTTCameraClient(self.mqtt_broker, self.mqtt_port)
            
            # Connect to MQTT broker
            if mqtt_client.connect():
                logger.info("Successfully connected to MQTT broker")
                
                # Get camera stream URL from MQTT or use configured URL
                stream_url = self.config.get('url')
                
                if not stream_url:
                    # Try to get URL from MQTT
                    stream_url = mqtt_client.get_camera_stream_url()
                
                mqtt_client.disconnect()
                
                if stream_url:
                    logger.info(f"Using MQTT camera stream URL: {stream_url}")
                    self.source = stream_url
                    self.is_mqtt_camera = True
                    
                    # Now connect to the actual stream
                    return self._try_connect(stream_url)
                else:
                    logger.error("Failed to get camera stream URL from MQTT")
                    return False
            else:
                logger.error("Failed to connect to MQTT broker")
                # Try to use configured URL as fallback
                if 'url' in self.config:
                    logger.info("Attempting to connect using configured URL as fallback")
                    self.source = self.config['url']
                    self.is_mqtt_camera = True
                    return self._try_connect(self.source)
                return False
                
        except ImportError:
            logger.error("mqtt_camera module not found. Please ensure mqtt_camera.py exists.")
            return False
        except Exception as e:
            logger.error(f"Error connecting to MQTT camera: {e}")
            return False
    
    def _is_hls_url(self, source) -> bool:
        """Check if source is an HLS stream URL"""
        if not isinstance(source, str):
            return False
        return '.m3u8' in source or 'manifest.googlevideo.com' in source or 'youtube.com' in source or 'youtu.be' in source
    
    def _get_streamlink_url(self, source: str) -> Optional[str]:
        """Get direct stream URL using streamlink for HLS sources"""
        if not STREAMLINK_AVAILABLE:
            logger.warning("Streamlink not available, cannot extract HLS stream URL")
            return None
            
        try:
            logger.info(f"Using streamlink to extract stream URL from: {source}")
            session = Streamlink()
            streams = session.streams(source)
            
            if not streams:
                logger.warning(f"No streams found by streamlink for: {source}")
                return None
            
            # Try to get the best quality stream, fallback to any available
            if 'best' in streams:
                stream_url = streams['best'].to_url()
            elif 'worst' in streams:
                stream_url = streams['worst'].to_url()
            else:
                # Get first available stream
                stream_url = next(iter(streams.values())).to_url()
            
            logger.info(f"Streamlink extracted URL: {stream_url[:100]}...")
            return stream_url
            
        except Exception as e:
            logger.error(f"Streamlink failed to extract stream: {e}")
            return None
    
    def _try_connect(self, source) -> bool:
        """
        Try to connect to a specific source
        
        Args:
            source: Camera source (int, str URL, or file path)
        
        Returns:
            True if successful
        """
        try:
            # Check if source is HLS and needs streamlink processing
            if self._is_hls_url(source):
                logger.info(f"Detected HLS stream, using streamlink: {source}")
                stream_url = self._get_streamlink_url(source)
                if stream_url:
                    source = stream_url
                else:
                    logger.warning("Streamlink failed, trying direct connection anyway")
            
            # For RTSP streams, use optimized settings
            if isinstance(source, str) and source.startswith('rtsp://'):
                # Use TCP for reliability and set environment variables for minimal latency
                import os
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|buffer_size;1024000|max_delay;0"
                self.cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
            else:
                self.cap = cv2.VideoCapture(source)
            
            # Reduce buffer size to minimize delay (especially for RTSP streams)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # For RTSP, also set additional low-latency parameters
            if isinstance(source, str) and source.startswith('rtsp://'):
                self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'H264'))
            
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
            # For RTSP streams, flush buffer to get latest frame
            if isinstance(self.source, str) and self.source.startswith('rtsp://'):
                # Grab multiple frames to clear buffer and get the most recent one
                for _ in range(3):
                    self.cap.grab()
            
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
