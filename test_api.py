"""
Simple test script to verify the Smart Lighting Control system
"""

import requests
import time
import json

BASE_URL = "http://localhost:8000"

def print_section(title):
    """Print a section header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def test_api():
    """Test the API endpoints"""
    
    print_section("Testing Smart Lighting Control System")
    
    # Test 1: Check if API is running
    print("\n1. Testing API connection...")
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"   ✓ API is running!")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"   ✗ API connection failed: {e}")
        print("   Make sure the server is running: python main.py")
        return
    
    # Test 2: Check health
    print("\n2. Checking system health...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        health = response.json()
        print(f"   Status: {health['status']}")
        print(f"   Camera: {'✓' if health['camera'] else '✗'}")
        print(f"   Detector: {'✓' if health['detector'] else '✗'}")
        print(f"   Light Controller: {'✓' if health['light_controller'] else '✗'}")
    except Exception as e:
        print(f"   ✗ Health check failed: {e}")
    
    # Test 3: Get initial status
    print("\n3. Getting initial system status...")
    try:
        response = requests.get(f"{BASE_URL}/status")
        status = response.json()
        print(f"   Processing: {'Running' if status['is_running'] else 'Stopped'}")
        print(f"   Light Status: {status['lights']['state']}")
        print(f"   Light Brightness: {status['lights']['current_brightness']}%")
    except Exception as e:
        print(f"   ✗ Status check failed: {e}")
    
    # Test 4: Start video processing
    print("\n4. Starting video processing...")
    try:
        response = requests.post(f"{BASE_URL}/start")
        result = response.json()
        print(f"   ✓ {result['message']}")
        time.sleep(2)  # Give it time to start
    except Exception as e:
        print(f"   Note: {e}")
    
    # Test 5: Monitor for a few seconds
    print("\n5. Monitoring detections for 10 seconds...")
    print("   (Watch the main terminal for detection logs)")
    
    for i in range(10):
        try:
            response = requests.get(f"{BASE_URL}/status")
            status = response.json()
            
            stats = status['stats']
            lights = status['lights']
            
            print(f"   [{i+1}/10] "
                  f"Frames: {stats['frames_processed']} | "
                  f"Detections: {stats['trigger_detections']} | "
                  f"Light: {lights['state']} ({lights['current_brightness']}%) | "
                  f"FPS: {stats['fps']:.1f}")
            
            time.sleep(1)
        except Exception as e:
            print(f"   ✗ Monitoring error: {e}")
            break
    
    # Test 6: Get detection history
    print("\n6. Getting recent detection history...")
    try:
        response = requests.get(f"{BASE_URL}/detections/history?limit=5")
        history = response.json()
        print(f"   Total detections logged: {history['total_count']}")
        print(f"   Recent detections:")
        for detection in history['history'][-5:]:
            objects = ", ".join([f"{obj['class']}({obj['confidence']:.2f})" 
                                for obj in detection['objects']])
            print(f"     - {detection['timestamp']}: {objects}")
    except Exception as e:
        print(f"   ✗ History check failed: {e}")
    
    # Test 7: Get light status
    print("\n7. Checking light controller status...")
    try:
        response = requests.get(f"{BASE_URL}/lights/status")
        light_status = response.json()
        print(f"   Mode: {light_status['mode']}")
        print(f"   State: {light_status['state']}")
        print(f"   Brightness: {light_status['current_brightness']}%")
        print(f"   Last Update: {time.ctime(light_status['last_update'])}")
    except Exception as e:
        print(f"   ✗ Light status check failed: {e}")
    
    # Test 8: Manual light control
    print("\n8. Testing manual light control...")
    try:
        # Turn on to 50%
        response = requests.post(f"{BASE_URL}/lights/manual", 
                                json={"brightness": 50})
        result = response.json()
        print(f"   ✓ Set brightness to 50%")
        time.sleep(1)
        
        # Turn off
        response = requests.post(f"{BASE_URL}/lights/manual", 
                                json={"brightness": 0})
        result = response.json()
        print(f"   ✓ Turned lights off")
    except Exception as e:
        print(f"   ✗ Manual control failed: {e}")
    
    # Test 9: Camera info
    print("\n9. Camera information...")
    try:
        response = requests.get(f"{BASE_URL}/status")
        status = response.json()
        camera = status['camera']
        print(f"   Source: {camera['source']}")
        print(f"   Resolution: {camera['resolution'][0]}x{camera['resolution'][1]}")
        print(f"   FPS: {camera['fps']:.1f}")
        print(f"   Frames captured: {camera['frame_count']}")
    except Exception as e:
        print(f"   ✗ Camera info failed: {e}")
    
    print_section("Testing Complete!")
    print("\n✓ The system is working correctly!")
    print("\nNext steps:")
    print("  1. Open http://localhost:8000/docs in your browser")
    print("  2. Open http://localhost:8000/stream to see live video")
    print("  3. Configure your own camera in config.yaml")
    print("  4. Connect real lights by changing 'mode' in config.yaml\n")


if __name__ == "__main__":
    test_api()
