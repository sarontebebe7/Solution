"""
Launch script for Smart Lighting Control System
Opens the dashboard in the default browser
"""

import webbrowser
import time
import sys
import subprocess

def main():
    print("=" * 60)
    print("  Smart Lighting Control System")
    print("=" * 60)
    print()
    
    # Check if server is already running
    import requests
    try:
        response = requests.get("http://localhost:8000/api", timeout=2)
        print("✓ Server is already running!")
    except:
        print("⚠ Server not running. Please start it first:")
        print("  python main.py")
        print()
        response = input("Would you like to start the server now? (y/n): ")
        if response.lower() == 'y':
            print("\nStarting server...")
            # This won't work well in Windows, just provide instructions
            print("\nPlease open a new terminal and run:")
            print("  python main.py")
            print("\nThen run this script again.")
            sys.exit(0)
        else:
            sys.exit(1)
    
    # Open dashboard
    dashboard_url = "http://localhost:8000"
    print(f"\n🌐 Opening dashboard at: {dashboard_url}")
    print()
    print("📋 Quick Guide:")
    print("  1. Click 'Start System' to begin video processing")
    print("  2. View live detections in the video feed")
    print("  3. Control lights manually with the slider")
    print("  4. Monitor statistics in real-time")
    print()
    print("🔧 Configuration:")
    print("  - Change camera source in the dashboard")
    print("  - Adjust detection sensitivity")
    print("  - Configure light control mode in config.yaml")
    print()
    
    time.sleep(1)
    webbrowser.open(dashboard_url)
    
    print("✓ Dashboard opened in your browser!")
    print("\nPress Ctrl+C in the server terminal to stop the system.")

if __name__ == "__main__":
    main()
