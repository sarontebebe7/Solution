"""
MQTT Camera Stream Handler
Connects to school's OpenLab MQTT system to access camera streams
"""

import json
import logging
import paho.mqtt.client as mqtt
from typing import Optional
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MQTTCameraClient:
    """Handle MQTT connection to retrieve camera stream URLs"""
    
    def __init__(self, broker: str = "openlab.kpi.fei.tuke.sk", port: int = 1883):
        """
        Initialize MQTT camera client
        
        Args:
            broker: MQTT broker address
            port: MQTT broker port
        """
        self.broker = broker
        self.port = port
        self.client = mqtt.Client()
        self.camera_stream_url: Optional[str] = None
        self.connected = False
        
        # Set up callbacks
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for when client connects to MQTT broker"""
        if rc == 0:
            self.connected = True
            logger.info(f"Connected to MQTT broker: {self.broker}")
            # Subscribe to camera topics if needed
            # client.subscribe("openlab/camera/#")
        else:
            logger.error(f"Failed to connect to MQTT broker, return code: {rc}")
            self.connected = False
    
    def _on_message(self, client, userdata, msg):
        """Callback for when a message is received"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            logger.info(f"Received message on topic {topic}: {payload}")
            
            # Parse camera stream URL from messages if needed
            # This depends on how the camera publishes its stream URL
            if 'camera' in topic.lower() and 'url' in topic.lower():
                self.camera_stream_url = payload
                logger.info(f"Camera stream URL updated: {self.camera_stream_url}")
                
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback for when client disconnects from broker"""
        self.connected = False
        logger.info(f"Disconnected from MQTT broker")
    
    def connect(self) -> bool:
        """
        Connect to MQTT broker
        
        Returns:
            True if connection successful
        """
        try:
            logger.info(f"Connecting to MQTT broker: {self.broker}:{self.port}")
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
            
            # Wait for connection
            timeout = 5
            start_time = time.time()
            while not self.connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if self.connected:
                logger.info("MQTT connection established")
                return True
            else:
                logger.error("MQTT connection timeout")
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to MQTT broker: {e}")
            self.connected = False
            return False
    
    def get_camera_stream_url(self, camera_topic: str = "openlab/camera/stream") -> Optional[str]:
        """
        Get camera stream URL from MQTT
        
        Args:
            camera_topic: MQTT topic where camera stream URL is published
            
        Returns:
            Camera stream URL or default RTSP URL
        """
        if not self.connected:
            logger.warning("Not connected to MQTT broker")
            return None
        
        # For OpenLab, we might need to construct or retrieve the RTSP stream URL
        # Based on the school's infrastructure
        # Common patterns:
        # - RTSP streams: rtsp://openlab.kpi.fei.tuke.sk:554/camera1
        # - HTTP streams: http://openlab.kpi.fei.tuke.sk:8080/stream.mjpg
        
        # Try to get from subscription if available
        if self.camera_stream_url:
            return self.camera_stream_url
        
        # Return a default RTSP URL for OpenLab cameras
        # You may need to adjust this based on actual camera configuration
        default_url = "rtsp://openlab.kpi.fei.tuke.sk:554/live/camera1"
        logger.info(f"Using default camera stream URL: {default_url}")
        return default_url
    
    def publish_command(self, topic: str, payload: dict):
        """
        Publish a command to MQTT
        
        Args:
            topic: MQTT topic
            payload: JSON payload as dictionary
        """
        if not self.connected:
            logger.warning("Cannot publish - not connected to MQTT broker")
            return
        
        try:
            json_payload = json.dumps(payload)
            self.client.publish(topic, json_payload)
            logger.info(f"Published to {topic}: {json_payload}")
        except Exception as e:
            logger.error(f"Error publishing MQTT message: {e}")
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        if self.connected:
            logger.info("Disconnecting from MQTT broker")
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False


def get_openlab_camera_url(broker: str = "openlab.kpi.fei.tuke.sk") -> Optional[str]:
    """
    Quick function to get OpenLab camera stream URL
    
    Args:
        broker: MQTT broker address
        
    Returns:
        Camera stream URL or None if failed
    """
    mqtt_client = MQTTCameraClient(broker)
    
    try:
        if mqtt_client.connect():
            url = mqtt_client.get_camera_stream_url()
            return url
        return None
    except Exception as e:
        logger.error(f"Error getting OpenLab camera URL: {e}")
        return None
    finally:
        mqtt_client.disconnect()


if __name__ == "__main__":
    # Test the MQTT camera connection
    print("Testing MQTT Camera Connection...")
    
    client = MQTTCameraClient()
    
    if client.connect():
        print(f"✓ Connected to MQTT broker: {client.broker}")
        
        # Get camera stream URL
        stream_url = client.get_camera_stream_url()
        print(f"Camera stream URL: {stream_url}")
        
        # Example: Send a test command (optional)
        # client.publish_command("openlab/test", {"message": "Hello from camera client"})
        
        time.sleep(2)
        client.disconnect()
        print("✓ Disconnected successfully")
    else:
        print("✗ Failed to connect to MQTT broker")
