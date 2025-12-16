"""
Test script for OpenLab light controller
"""

import time
import yaml
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Load config
print("📋 Loading configuration...")
with open('config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# Import controller
from openlab_light_controller import OpenLabLightController

print("\n" + "="*70)
print("  🧪 OpenLab Light Controller Test")
print("="*70)

# Create controller
print("\n🔌 Connecting to OpenLab MQTT broker...")
controller = OpenLabLightController(config['lighting'])

# Wait for connection
time.sleep(2)

print("\n✨ Testing OpenLab lights...")
print("="*70)

# Test 1: Turn on at 50%
print("\n1️⃣  Turning lights ON at 50% brightness")
controller.turn_on(50)
time.sleep(3)

# Test 2: Increase to 100%
print("\n2️⃣  Increasing to 100% brightness")
controller.turn_on(100)
time.sleep(3)

# Test 3: Dim to 20%
print("\n3️⃣  Dimming to 20% brightness")
controller.turn_on(20)
time.sleep(3)

# Test 4: Auto-adjust based on person count
print("\n4️⃣  Auto-adjusting based on person count")
for persons in [1, 3, 5, 3, 1, 0]:
    print(f"   👤 Persons detected: {persons}")
    controller.adjust_brightness(persons, max_persons=5)
    time.sleep(2)

# Test 5: Turn off
print("\n5️⃣  Turning lights OFF")
controller.turn_off()
time.sleep(2)

# Status
print("\n" + "="*70)
print("📊 Final status:")
status = controller.get_status()
for key, value in status.items():
    print(f"   {key}: {value}")
print("="*70)

# Disconnect
controller.disconnect()
print("\n✅ Test complete!")
print()
