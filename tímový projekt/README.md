# Smart Lighting Control with Object Detection

An intelligent lighting control system that uses YOLOv8 object detection to automatically adjust light brightness based on detected objects in a camera stream. The system can distinguish between people (triggers lights) and smaller objects like birds (ignored).

## Features

- 🎯 **Real-time Object Detection** using YOLOv8
- 📹 **Multiple Camera Sources** support (webcam, IP cameras, RTSP, HTTP streams)
- 💡 **Intelligent Light Control** based on object size and type
- 🔧 **FastAPI REST API** for control and monitoring
- ⚙️ **Configurable Thresholds** for object filtering
- 🎚️ **Smooth Transitions** with debouncing to prevent flickering
- 📊 **Real-time Monitoring** via API endpoints

## Technology Stack

- **Object Detection**: YOLOv8 (Ultralytics)
- **API Framework**: FastAPI
- **Computer Vision**: OpenCV
- **Configuration**: YAML

## Installation

1. **Clone or navigate to the project directory**

2. **Create a virtual environment**:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

## Configuration

Edit `config.yaml` to customize:

- **Camera source** (webcam, IP camera URL, video file)
- **Detection settings** (model type, confidence threshold, target classes)
- **Object size filtering** (min/max bounding box area)
- **Light control** (brightness levels, fade duration, auto-off delay)
- **Lighting backend** (simulated, MQTT, HTTP, Philips Hue)

## Usage

### Start the Application

```powershell
python main.py
```

The API will be available at: `http://localhost:8000`

### API Endpoints

- **GET** `/` - API information
- **GET** `/status` - Get current system status
- **POST** `/start` - Start video processing
- **POST** `/stop` - Stop video processing
- **GET** `/stream` - Live video stream with detections
- **POST** `/config` - Update configuration
- **GET** `/lights/status` - Get current light status
- **POST** `/lights/manual` - Manually control lights

### Interactive API Documentation

Visit `http://localhost:8000/docs` for Swagger UI documentation.

## How It Works

1. **Video Capture**: Fetches frames from configured camera source
2. **Object Detection**: YOLOv8 analyzes each frame and detects objects
3. **Filtering**: Filters objects by class (person) and size (area > threshold)
4. **Light Control**: Adjusts light brightness based on detected objects
5. **Debouncing**: Prevents rapid on/off switching with configurable delays

## Configuration Examples

### Use Webcam
```yaml
camera:
  source: "0"
```

### Use IP Camera (RTSP)
```yaml
camera:
  source: "rtsp://username:password@192.168.1.100:554/stream"
```

### Use HTTP Stream
```yaml
camera:
  source: "http://192.168.1.100:8080/video"
```

### Adjust Detection Sensitivity
```yaml
detection:
  confidence: 0.6  # Higher = more strict
  min_object_size: 10000  # Larger = only bigger objects
```

## Light Control Modes

### Simulated (Testing)
```yaml
lighting:
  mode: "simulated"
```

### MQTT
```yaml
lighting:
  mode: "mqtt"
  mqtt:
    broker: "192.168.1.100"
    topic: "home/lights/control"
```

### HTTP API
```yaml
lighting:
  mode: "http"
  http:
    url: "http://your-light-api.com/control"
```

## Troubleshooting

### Camera not connecting
- Verify camera URL/source in `config.yaml`
- Check network connectivity
- Test with webcam (`source: "0"`) first

### No objects detected
- Lower `confidence` threshold in config
- Verify camera has clear view
- Check `target_classes` includes "person"

### Lights not responding
- Verify `lighting.mode` is configured correctly
- Check connection to light control system
- Test with `mode: "simulated"` first

## Development

### Project Structure
```
.
├── main.py              # FastAPI application entry point
├── detector.py          # YOLOv8 object detection
├── camera.py            # Camera stream handling
├── light_controller.py  # Light control logic
├── video_processor.py   # Video processing service
├── config.yaml          # Configuration file
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## License

MIT License

## Future Enhancements

- [ ] Web dashboard for monitoring
- [ ] Multiple camera support
- [ ] Zone-based detection
- [ ] Activity logging and analytics
- [ ] Mobile app integration
- [ ] Advanced scheduling rules
