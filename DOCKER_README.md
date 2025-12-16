# Docker Deployment Guide

This guide explains how to run the Smart Lighting Control application using Docker.

## Prerequisites

- Docker Desktop installed ([Download](https://www.docker.com/products/docker-desktop/))
- Docker Compose (included with Docker Desktop)

## Quick Start

### Option 1: Using Docker Compose (Recommended)

1. **Navigate to the project directory:**
   ```powershell
   cd "C:\Users\richa\OneDrive\Počítač\ZIVEIT\Solution\tímový projekt"
   ```

2. **Build and start the container:**
   ```powershell
   docker-compose up --build
   ```

3. **Access the application:**
   - API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Dashboard: http://localhost:8000/dashboard

4. **Stop the container:**
   ```powershell
   docker-compose down
   ```

### Option 2: Using Docker Commands Directly

1. **Build the image:**
   ```powershell
   docker build -t smart-lighting-detection .
   ```

2. **Run the container:**
   ```powershell
   docker run -d -p 8000:8000 --name smart-lighting smart-lighting-detection
   ```

3. **Stop the container:**
   ```powershell
   docker stop smart-lighting
   docker rm smart-lighting
   ```

## Configuration

### Camera Source

Edit `config.yaml` before building to set your camera source:

```yaml
camera:
  source: "0"  # Webcam
  # or
  source: "rtsp://username:password@ip:port/stream"  # IP Camera
  # or
  source: "/app/videos/sample.mp4"  # Video file
```

### Environment Variables

You can override settings using environment variables in `docker-compose.yml`:

```yaml
environment:
  - CAMERA_SOURCE=0
  - DETECTION_CONFIDENCE=0.5
```

## Important Notes for Windows

### Webcam Access
- **Windows with Docker Desktop:** Webcam access in Docker containers is limited on Windows
- **Recommended workarounds:**
  1. Use WSL2 with USB passthrough
  2. Use an IP camera (RTSP/HTTP stream)
  3. Use a video file for testing
  4. Run the container on a Linux host

### Best Practices for Windows Users

If you want to use a webcam:
1. Consider using the native Python installation (without Docker)
2. Or use an IP camera app on your phone (like "IP Webcam" for Android)
3. Update `config.yaml` to use the IP camera stream

Example IP camera configuration:
```yaml
camera:
  source: "http://192.168.1.100:8080/video"  # IP Webcam app
```

## Volume Mounts

The Docker Compose setup includes these volumes:

- **config.yaml**: Edit configuration without rebuilding
- **./videos**: Place video files here for testing
- **yolo-models**: Persistent storage for downloaded models

## Useful Commands

### View logs:
```powershell
docker-compose logs -f
```

### Restart container:
```powershell
docker-compose restart
```

### Rebuild after code changes:
```powershell
docker-compose up --build
```

### Run in background:
```powershell
docker-compose up -d
```

### Access container shell:
```powershell
docker exec -it smart-lighting-detection bash
```

### Check container status:
```powershell
docker-compose ps
```

## Troubleshooting

### Container won't start
- Check logs: `docker-compose logs`
- Verify port 8000 is not in use
- Check config.yaml syntax

### Camera connection fails
- Verify camera source in config.yaml
- For webcam on Windows, consider alternatives (see above)
- For IP cameras, ensure network accessibility

### Model download fails
- Check internet connection
- The first run downloads YOLOv8 models (~6MB for yolov8n)
- Subsequent runs use cached models

### Performance issues
- Reduce FPS in config.yaml
- Use smaller YOLO model (yolov8n instead of yolov8s/m/l)
- Increase frame_interval in config.yaml

## Production Deployment

For production use:

1. Use a proper reverse proxy (nginx, traefik)
2. Enable HTTPS
3. Set up proper authentication
4. Use environment variables for sensitive data
5. Configure logging and monitoring
6. Set resource limits in docker-compose.yml:

```yaml
services:
  object-detection:
    # ... other config ...
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

## License

See main project README for license information.
