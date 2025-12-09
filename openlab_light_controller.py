"""
OpenLab Light Controller - Real MQTT-based light control
Connects to OpenLab Bridge and controls real lights via MQTT
"""

import json
import logging
import time
import paho.mqtt.client as mqtt
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class OpenLabLightController:
    """Controller for OpenLab lights via MQTT"""
    
    def __init__(self, config: dict):
        """
        Initialize OpenLab light controller
        
        Args:
            config: Configuration dictionary with MQTT settings
        """
        self.config = config
        self.mqtt_config = config.get('mqtt', {})
        
        # MQTT settings
        self.broker = self.mqtt_config.get('broker', 'localhost')
        self.port = self.mqtt_config.get('port', 1883)
        self.topic = self.mqtt_config.get('topic', 'openlab/lights')
        self.username = self.mqtt_config.get('username')
        self.password = self.mqtt_config.get('password')
        
        # Light settings
        self.min_brightness = config.get('min_brightness', 0)
        self.max_brightness = config.get('max_brightness', 100)
        self.fade_duration = config.get('fade_duration', 1000)  # milliseconds
        self.epilepsy_safe_duration = 250  # minimum duration for safety
        
        # State
        self.current_brightness = 0
        self.is_on = False
        self.last_command_time = 0
        self.command_cooldown = 0.1  # seconds between commands (reduced for faster response)
        
        # Initialize MQTT client
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_publish = self._on_publish
        
        # Set credentials if provided
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)
        
        # Connect to broker
        self._connect()
        
        logger.info(f"OpenLab Light Controller initialized (broker: {self.broker}:{self.port})")
    
    def _connect(self):
        """Connect to MQTT broker"""
        try:
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
            logger.info(f"Connecting to MQTT broker at {self.broker}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            raise
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker"""
        if rc == 0:
            logger.info("✅ Connected to MQTT broker successfully")
        else:
            logger.error(f"❌ Failed to connect to MQTT broker (code: {rc})")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker"""
        if rc != 0:
            logger.warning(f"Unexpected disconnection from MQTT broker (code: {rc})")
    
    def _on_publish(self, client, userdata, mid):
        """Callback when message is published"""
        logger.debug(f"Message published (mid: {mid})")
    
    def _brightness_to_rgbw(self, brightness: int) -> str:
        """
        Convert brightness percentage to RGBW hex value
        
        Args:
            brightness: Brightness level (0-100)
        
        Returns:
            RGBW hex string (e.g., "000000ff" for full white)
        """
        # Clamp brightness
        brightness = max(0, min(100, brightness))
        
        # Convert to 0-255 range for white channel
        white_value = int((brightness / 100) * 255)
        
        # Format as RGBW (RGB off, only white channel)
        rgbw = f"000000{white_value:02x}"
        
        return rgbw
    
    def _send_mqtt_command(self, rgbw_value: str, duration: Optional[int] = None):
        """
        Send MQTT command to control lights
        
        Args:
            rgbw_value: RGBW hex value (e.g., "000000ff")
            duration: Fade duration in milliseconds
        """
        # Respect command cooldown
        current_time = time.time()
        time_since_last = current_time - self.last_command_time
        if time_since_last < self.command_cooldown:
            time.sleep(self.command_cooldown - time_since_last)
        
        # Use default duration if not specified
        if duration is None:
            duration = self.fade_duration
        
        # Ensure epilepsy-safe duration
        duration = max(duration, self.epilepsy_safe_duration)
        
        # Create message
        message = {
            "all": rgbw_value,
            "duration": duration
        }
        
        # Publish to MQTT
        try:
            result = self.client.publish(
                self.topic,
                json.dumps(message),
                qos=1
            )
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"💡 Sent light command: {rgbw_value} (duration: {duration}ms)")
                self.last_command_time = time.time()
            else:
                logger.error(f"Failed to publish MQTT message (code: {result.rc})")
        
        except Exception as e:
            logger.error(f"Error sending MQTT command: {e}")
    
    def turn_on(self, brightness: Optional[int] = None):
        """
        Turn lights on
        
        Args:
            brightness: Optional brightness level (0-100)
        """
        if brightness is None:
            brightness = self.max_brightness
        
        # Clamp brightness
        brightness = max(self.min_brightness, min(self.max_brightness, brightness))
        
        # Convert to RGBW
        rgbw = self._brightness_to_rgbw(brightness)
        
        # Send command
        self._send_mqtt_command(rgbw)
        
        # Update state
        self.is_on = True
        self.current_brightness = brightness
        
        logger.info(f"🔆 Lights turned ON (brightness: {brightness}%)")
    
    def turn_off(self):
        """Turn lights off"""
        # Send command to turn off (all zeros)
        self._send_mqtt_command("00000000")
        
        # Update state
        self.is_on = False
        self.current_brightness = 0
        
        logger.info("🔅 Lights turned OFF")
    
    def set_brightness(self, brightness: int):
        """
        Set light brightness
        
        Args:
            brightness: Brightness level (0-100)
        """
        if brightness == 0:
            self.turn_off()
        else:
            self.turn_on(brightness)
    
    def adjust_brightness(self, person_count: int, max_persons: int = 10):
        """
        Automatically adjust brightness based on person count
        
        Args:
            person_count: Number of detected persons
            max_persons: Maximum expected persons (for scaling)
        """
        if person_count == 0:
            self.turn_off()
        else:
            # Calculate brightness (linear scaling)
            brightness_range = self.max_brightness - self.min_brightness
            brightness = self.min_brightness + (
                (person_count / max_persons) * brightness_range
            )
            
            # Clamp to max
            brightness = min(brightness, self.max_brightness)
            
            self.turn_on(int(brightness))
    
    def update_from_detections(self, detections: list, frame_size: tuple):
        """
        Update light brightness based on current detections
        
        Args:
            detections: List of Detection objects
            frame_size: Tuple (width, height) of frame
        """
        if detections:
            # Count persons
            person_count = len([d for d in detections if d.class_name == 'person'])
            
            if person_count > 0:
                # Adjust brightness based on person count
                self.adjust_brightness(person_count)
        else:
            # No detections - turn off
            self.turn_off()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current light status"""
        return {
            "state": "on" if self.is_on else "off",
            "current_brightness": self.current_brightness,
            "mqtt_connected": self.client.is_connected(),
            "broker": f"{self.broker}:{self.port}",
            "topic": self.topic
        }
    
    def get_current_brightness(self) -> int:
        """Get current brightness level"""
        return self.current_brightness
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        try:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("Disconnected from MQTT broker")
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")
