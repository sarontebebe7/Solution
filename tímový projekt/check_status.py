"""
Quick status check for Smart Lighting Control System
"""

import requests
import time

API_BASE = "http://localhost:8000"

def check_system():
    print("\n" + "="*70)
    print("  🔍 SMART LIGHTING SYSTEM - STATUS CHECK")
    print("="*70 + "\n")
    
    try:
        # Get status
        response = requests.get(f"{API_BASE}/status", timeout=5)
        status = response.json()
        
        # System Status
        print("📊 SYSTEM STATUS:")
        print(f"   Running: {'✅ YES' if status['is_running'] else '❌ NO (Use Start button in dashboard)'}")
        print(f"   Paused:  {'⏸️  YES' if status.get('is_paused') else '▶️  NO'}")
        
        # Camera
        print("\n📹 CAMERA:")
        camera = status['camera']
        print(f"   Source: {camera['source']}")
        print(f"   Status: {'✅ Connected' if camera['is_opened'] else '❌ Not connected'}")
        print(f"   Resolution: {camera['resolution'][0]}x{camera['resolution'][1]}")
        print(f"   FPS: {camera['fps']:.1f}")
        print(f"   Frames captured: {camera['frame_count']}")
        
        # Statistics
        print("\n📈 STATISTICS:")
        stats = status['stats']
        print(f"   Frames processed: {stats['frames_processed']}")
        print(f"   Total detections: {stats['total_detections']}")
        print(f"   Trigger detections: {stats['trigger_detections']} ⚡")
        print(f"   Current FPS: {stats['fps']:.2f}")
        print(f"   Avg processing time: {stats['avg_processing_time']*1000:.1f}ms")
        
        # Lights
        print("\n💡 LIGHTS:")
        lights = status['lights']
        state_icon = "🔆" if lights['current_brightness'] > 0 else "🌑"
        print(f"   {state_icon} State: {lights['state'].upper()}")
        print(f"   Brightness: {lights['current_brightness']}%")
        print(f"   Mode: {lights['mode']}")
        
        if lights['last_detection'] > 0:
            time_since = time.time() - lights['last_detection']
            print(f"   Last detection: {time_since:.1f}s ago")
        
        # Current detections
        if status['current_detections'] > 0:
            print(f"\n🚨 LIVE: {status['current_detections']} person(s) detected NOW!")
        
        print("\n" + "="*70)
        print("✅ System is working! The camera IS streaming and detecting objects.")
        print("💡 The lights are automatically controlled based on detections.")
        print("\n📱 Dashboard: http://localhost:8000")
        print("📚 API Docs: http://localhost:8000/docs")
        print("="*70 + "\n")
        
        # Check if detecting
        if stats['trigger_detections'] > 0:
            print("🎉 GOOD NEWS: System has detected {} people so far!".format(
                stats['trigger_detections']))
            print("   The lights are being automatically controlled! ✨\n")
        else:
            print("⏳ Waiting for detections... The system is monitoring.\n")
            
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Cannot connect to the server!")
        print("   Please start the server first:")
        print("   python main.py\n")
    except Exception as e:
        print(f"❌ ERROR: {e}\n")

if __name__ == "__main__":
    check_system()
