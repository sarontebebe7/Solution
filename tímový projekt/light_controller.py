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
        
        self.last_detection_time = 0
    
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
    
    def on_object_detected(self):
        """Called when a target object is detected"""
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
