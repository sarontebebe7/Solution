"""
Light Controller Module
Supports multiple lighting control backends: simulated, MQTT, HTTP, Philips Hue
"""

import time
import logging
from typing import Optional, Dict
from abc import ABC, abstractmethod
import requests
from enum import Enum

# Optional MQTT support
try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    logging.warning("paho-mqtt not installed. MQTT support disabled.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LightState(Enum):
    """Light states"""
    OFF = "off"
    ON = "on"
    TRANSITIONING = "transitioning"


class LightController(ABC):
    """Abstract base class for light controllers"""
    
    def __init__(self, config: dict):
        self.config = config
        self.current_brightness = 0
        self.target_brightness = 0
        self.state = LightState.OFF
        self.last_update = time.time()
        
        self.brightness_levels = config.get('brightness', {
            'off': 0,
            'low': 30,
            'medium': 60,
            'high': 100
        })
        
        self.default_on_brightness = config.get('default_on_brightness', 80)
        self.fade_duration = config.get('fade_duration', 1.0)
        self.debounce_time = config.get('debounce_time', 2.0)
        self.auto_off_delay = config.get('auto_off_delay', 10.0)
        
        # Dynamic brightness settings
        self.dynamic_config = config.get('dynamic_brightness', {})
        self.dynamic_enabled = self.dynamic_config.get('enabled', True)
        self.min_brightness = self.dynamic_config.get('min_brightness', 20)
        self.max_brightness = self.dynamic_config.get('max_brightness', 100)
        self.score_threshold = self.dynamic_config.get('score_threshold', 0.05)
        self.score_ceiling = self.dynamic_config.get('score_ceiling', 0.3)
        self.class_weights = self.dynamic_config.get('class_weights', {'person': 1.0, 'default': 0.1})
        
        self.last_detection_time = 0
    
    def calculate_brightness_from_detections(self, detections: list, frame_size: tuple) -> int:
        """
        Calculate brightness based on detection score
        
        Formula: score = sum(confidence_i × relative_area_i × class_weight_i)
        
        Args:
            detections: List of Detection objects with .confidence, .area, .class_name
            frame_size: Tuple (width, height) of frame for calculating relative area
        
        Returns:
            Brightness value (0-100)
        """
        if not self.dynamic_enabled or not detections:
            return 0
        
        # Calculate total frame area
        frame_width, frame_height = frame_size
        total_frame_area = frame_width * frame_height
        
        # Calculate score
        score = 0.0
        for detection in detections:
            confidence = detection.confidence
            relative_area = detection.area / total_frame_area
            
            # Get class weight (use default if class not in weights)
            class_weight = self.class_weights.get(
                detection.class_name, 
                self.class_weights.get('default', 0.1)
            )
            
            detection_score = confidence * relative_area * class_weight
            score += detection_score
            
            logger.debug(f"Detection score: {detection.class_name} conf={confidence:.2f} "
                        f"area={relative_area:.4f} weight={class_weight} -> {detection_score:.4f}")
        
        logger.info(f"Total detection score: {score:.4f}")
        
        # Check if score meets threshold
        if score < self.score_threshold:
            return 0
        
        # Map score to brightness range [min_brightness, max_brightness]
        # score_threshold maps to min_brightness
        # score_ceiling maps to max_brightness
        normalized_score = min(1.0, (score - self.score_threshold) / 
                              (self.score_ceiling - self.score_threshold))
        
        brightness = int(self.min_brightness + 
                        normalized_score * (self.max_brightness - self.min_brightness))
        
        # Clamp to valid range
        brightness = max(0, min(100, brightness))
        
        logger.info(f"Calculated brightness: {brightness}% (score: {score:.4f}, normalized: {normalized_score:.2f})")
        
        return brightness
    
    @abstractmethod
    def set_brightness(self, brightness: int):
        """Set light brightness (0-100)"""
        pass
    
    @abstractmethod
    def get_status(self) -> dict:
        """Get current light status"""
        pass
    
    def turn_on(self, brightness: Optional[int] = None):
        """Turn lights on"""
        if brightness is None:
            brightness = self.default_on_brightness
        
        logger.info(f"Turning lights ON (brightness: {brightness})")
        self.target_brightness = brightness
        self.state = LightState.ON
        self.set_brightness(brightness)
    
    def turn_off(self):
        """Turn lights off"""
        logger.info("Turning lights OFF")
        self.target_brightness = 0
        self.state = LightState.OFF
        self.set_brightness(0)
    
    def update_from_detections(self, detections: list, frame_size: tuple):
        """
        Update light brightness based on current detections
        
        Args:
            detections: List of Detection objects
            frame_size: Tuple (width, height) of frame
        """
        current_time = time.time()
        
        if detections:
            # Calculate brightness from detections
            calculated_brightness = self.calculate_brightness_from_detections(detections, frame_size)
            
            if calculated_brightness > 0:
                # Update detection time
                self.last_detection_time = current_time
                
                # Set brightness immediately (no debounce - allow smooth real-time changes)
                self.target_brightness = calculated_brightness
                self.state = LightState.ON
                self.set_brightness(calculated_brightness)
                self.last_update = current_time
        else:
            # No detections - handle auto-off
            self.on_no_detection()
    
    def on_object_detected(self):
        """Called when a target object is detected (DEPRECATED - use update_from_detections)"""
        current_time = time.time()
        
        # Debounce check
        if current_time - self.last_detection_time < self.debounce_time:
            # Update detection time but don't change lights rapidly
            self.last_detection_time = current_time
            return
        
        self.last_detection_time = current_time
        
        # Turn on lights if not already on
        if self.state == LightState.OFF:
            self.turn_on()
    
    def on_no_detection(self):
        """Called when no objects are detected"""
        current_time = time.time()
        
        # Only turn off after auto_off_delay
        if self.state == LightState.ON:
            time_since_detection = current_time - self.last_detection_time
            
            if time_since_detection > self.auto_off_delay:
                logger.info(f"No detection for {time_since_detection:.1f}s, turning off")
                self.turn_off()


class SimulatedLightController(LightController):
    """Simulated light controller for testing"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        logger.info("Initialized Simulated Light Controller")
    
    def set_brightness(self, brightness: int):
        """Set brightness (simulated)"""
        brightness = max(0, min(100, brightness))  # Clamp to 0-100
        self.current_brightness = brightness
        self.last_update = time.time()
        logger.info(f"[SIMULATED] Light brightness set to: {brightness}%")
    
    def get_status(self) -> dict:
        """Get status"""
        return {
            "mode": "simulated",
            "state": self.state.value,
            "current_brightness": self.current_brightness,
            "target_brightness": self.target_brightness,
            "last_update": self.last_update,
            "last_detection": self.last_detection_time
        }


class MQTTLightController(LightController):
    """MQTT-based light controller"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        
        if not MQTT_AVAILABLE:
            raise ImportError("paho-mqtt not installed")
        
        mqtt_config = config.get('mqtt', {})
        self.broker = mqtt_config.get('broker', 'localhost')
        self.port = mqtt_config.get('port', 1883)
        self.topic = mqtt_config.get('topic', 'home/lights/control')
        self.username = mqtt_config.get('username')
        self.password = mqtt_config.get('password')
        
        # Create MQTT client
        self.client = mqtt.Client()
        
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)
        
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            logger.info(f"Connected to MQTT broker: {self.broker}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            raise
    
    def set_brightness(self, brightness: int):
        """Set brightness via MQTT"""
        brightness = max(0, min(100, brightness))
        
        try:
            payload = str(brightness)
            self.client.publish(self.topic, payload)
            self.current_brightness = brightness
            self.last_update = time.time()
            logger.info(f"Published brightness {brightness} to {self.topic}")
        except Exception as e:
            logger.error(f"Error publishing to MQTT: {e}")
    
    def get_status(self) -> dict:
        """Get status"""
        return {
            "mode": "mqtt",
            "broker": self.broker,
            "topic": self.topic,
            "state": self.state.value,
            "current_brightness": self.current_brightness,
            "target_brightness": self.target_brightness,
            "last_update": self.last_update,
            "last_detection": self.last_detection_time
        }
    
    def __del__(self):
        """Cleanup"""
        if hasattr(self, 'client'):
            self.client.loop_stop()
            self.client.disconnect()


class HTTPLightController(LightController):
    """HTTP API-based light controller"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        
        http_config = config.get('http', {})
        self.url = http_config.get('url', 'http://localhost:8000/api/lights')
        self.method = http_config.get('method', 'POST').upper()
        
        logger.info(f"Initialized HTTP Light Controller: {self.url}")
    
    def set_brightness(self, brightness: int):
        """Set brightness via HTTP API"""
        brightness = max(0, min(100, brightness))
        
        try:
            payload = {"brightness": brightness}
            
            if self.method == 'POST':
                response = requests.post(self.url, json=payload, timeout=5)
            elif self.method == 'PUT':
                response = requests.put(self.url, json=payload, timeout=5)
            else:
                response = requests.get(self.url, params=payload, timeout=5)
            
            response.raise_for_status()
            self.current_brightness = brightness
            self.last_update = time.time()
            logger.info(f"HTTP request sent: brightness={brightness}, status={response.status_code}")
        
        except Exception as e:
            logger.error(f"Error sending HTTP request: {e}")
    
    def get_status(self) -> dict:
        """Get status"""
        return {
            "mode": "http",
            "url": self.url,
            "method": self.method,
            "state": self.state.value,
            "current_brightness": self.current_brightness,
            "target_brightness": self.target_brightness,
            "last_update": self.last_update,
            "last_detection": self.last_detection_time
        }


class PhilipsHueLightController(LightController):
    """Philips Hue light controller"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        
        hue_config = config.get('hue', {})
        self.bridge_ip = hue_config.get('bridge_ip', '192.168.1.100')
        self.username = hue_config.get('username', 'your-hue-username')
        self.light_ids = hue_config.get('light_ids', [1])
        
        self.base_url = f"http://{self.bridge_ip}/api/{self.username}"
        
        logger.info(f"Initialized Philips Hue Controller: {self.bridge_ip}")
    
    def set_brightness(self, brightness: int):
        """Set brightness for Hue lights"""
        brightness = max(0, min(100, brightness))
        
        # Convert 0-100 to 0-254 (Hue range)
        hue_brightness = int(brightness * 254 / 100)
        
        try:
            for light_id in self.light_ids:
                url = f"{self.base_url}/lights/{light_id}/state"
                
                if brightness == 0:
                    payload = {"on": False}
                else:
                    payload = {"on": True, "bri": hue_brightness}
                
                response = requests.put(url, json=payload, timeout=5)
                response.raise_for_status()
            
            self.current_brightness = brightness
            self.last_update = time.time()
            logger.info(f"Hue lights brightness set to: {brightness}%")
        
        except Exception as e:
            logger.error(f"Error controlling Hue lights: {e}")
    
    def get_status(self) -> dict:
        """Get status"""
        return {
            "mode": "hue",
            "bridge_ip": self.bridge_ip,
            "light_ids": self.light_ids,
            "state": self.state.value,
            "current_brightness": self.current_brightness,
            "target_brightness": self.target_brightness,
            "last_update": self.last_update,
            "last_detection": self.last_detection_time
        }


def create_light_controller(config: dict) -> LightController:
    """
    Factory function to create appropriate light controller
    
    Args:
        config: Lighting configuration dict
    
    Returns:
        LightController instance
    """
    mode = config.get('mode', 'simulated').lower()
    
    if mode == 'simulated':
        return SimulatedLightController(config)
    elif mode == 'mqtt':
        return MQTTLightController(config)
    elif mode == 'http':
        return HTTPLightController(config)
    elif mode == 'hue':
        return PhilipsHueLightController(config)
    else:
        logger.warning(f"Unknown mode '{mode}', using simulated")
        return SimulatedLightController(config)
