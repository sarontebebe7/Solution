"""
Test OpenLab MQTT Light Control
Send a test message to turn on the lights
"""
import json
import paho.mqtt.client as mqtt
import time

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✓ Connected to OpenLab MQTT broker")
    else:
        print(f"✗ Connection failed with code {rc}")

def on_publish(client, userdata, mid):
    print(f"✓ Message published successfully (mid: {mid})")

# Create MQTT client
client = mqtt.Client()
client.on_connect = on_connect
client.on_publish = on_publish

# Connect to OpenLab
broker = "openlab.kpi.fei.tuke.sk"
port = 1883
print(f"Connecting to {broker}:{port}...")

try:
    client.connect(broker, port, 60)
    client.loop_start()
    
    time.sleep(2)  # Wait for connection
    
    # Test with both topic formats
    topics_to_test = ["openlab/lights", "/openlab/lights"]
    
    for topic in topics_to_test:
        print(f"\n{'='*60}")
        print(f"Testing with topic: '{topic}'")
        print(f"{'='*60}")
        
        # Test 1: Turn all lights to 50% white
        payload1 = {
            "all": "0000007f",  # 50% white (127 in hex = 7f)
            "duration": 1000
        }
        
        print(f"\nTest 1: Setting all lights to 50% white")
        print(f"Topic: {topic}")
        print(f"Payload: {json.dumps(payload1)}")
        result = client.publish(topic, json.dumps(payload1))
        print(f"Publish result code: {result.rc}")
        
        time.sleep(4)
        
        # Test 2: Turn all lights off
        payload2 = {
            "all": "00000000",  # Off
            "duration": 1000
        }
        
        print(f"\nTest 2: Turning all lights off")
        print(f"Topic: {topic}")
        print(f"Payload: {json.dumps(payload2)}")
        result = client.publish(topic, json.dumps(payload2))
        print(f"Publish result code: {result.rc}")
        
        time.sleep(3)
    
    client.loop_stop()
    client.disconnect()
    print("\n✓ Test complete!")
    
except Exception as e:
    print(f"✗ Error: {e}")
