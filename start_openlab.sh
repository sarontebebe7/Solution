#!/bin/bash

echo "================================================"
echo "  OpenLab Light Integration - Quick Start"
echo "================================================"
echo ""

# Check if paho-mqtt is installed
echo "1. Checking dependencies..."
python -c "import paho.mqtt.client" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "   ⚠️  Installing paho-mqtt..."
    pip install paho-mqtt
else
    echo "   ✅ paho-mqtt is installed"
fi

echo ""
echo "2. Testing OpenLab light connection..."
python test_openlab_lights.py

echo ""
echo "3. Starting main application..."
echo "   Dashboard will be available at: http://localhost:8000"
echo ""
python main.py
