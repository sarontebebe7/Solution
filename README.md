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

### Option 1: Using Docker (Recommended for Team/Production)

**Prerequisites:**
- Docker Desktop installed ([Download](https://www.docker.com/products/docker-desktop/))

**For Team Members - Pull Pre-built Image:**

```powershell
# Pull the latest image
docker pull rs735my/smart-lighting-detection:latest

# Run with docker-compose
docker-compose up
```

The application will be available at `http://localhost:8000`

**Note:** USB webcams don't work in Docker on Windows. Use IP camera, RTSP stream, or video file. Edit `config.yaml`:
```yaml
camera:
  source: "http://192.168.1.100:8080/video"  # IP Webcam from phone
  # OR
  source: "/app/videos/sample.mp4"  # Video file
```

**For Developers - Build Locally:**

```powershell
# Build and run
docker-compose up --build

# Or build without running
docker build -t smart-lighting-detection .
```

### Option 2: Native Python Installation (For USB Webcam Development)

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

4. **Set camera source in `config.yaml`**:
   ```yaml
   camera:
     source: "0"  # USB webcam works with native Python
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

### Updating Docker Image (For Maintainers)

When you add new dependencies or make changes:

1. **Update `requirements.txt`** with new packages:
   ```powershell
   pip freeze > requirements.txt
   ```

2. **Rebuild the Docker image**:
   ```powershell
   docker-compose build --no-cache
   ```

3. **Tag the new version**:
   ```powershell
   docker tag tmovprojekt-object-detection:latest rs735my/smart-lighting-detection:latest
   # Or with version number
   docker tag tmovprojekt-object-detection:latest rs735my/smart-lighting-detection:v1.1
   ```

4. **Push to Docker Hub**:
   ```powershell
   # Login first (if not already)
   docker login
   
   # Push latest
   docker push rs735my/smart-lighting-detection:latest
   
   # Also push versioned tag (recommended)
   docker push rs735my/smart-lighting-detection:v1.1
   ```

5. **Notify team members** to pull the new image:
   ```powershell
   docker-compose pull
   docker-compose up
   ```

### Adding New Python Packages

1. Install package locally:
   ```powershell
   pip install package-name
   ```

2. Update requirements.txt:
   ```powershell
   pip freeze > requirements.txt
   ```

3. Rebuild and push Docker image (steps above)

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
