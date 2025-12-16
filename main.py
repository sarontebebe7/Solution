"""
FastAPI Application - Smart Lighting Control
REST API for object detection and automated light control
"""

import cv2
import yaml
import logging
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uvicorn
from pathlib import Path

from camera import CameraStream
from detector import ObjectDetector
from light_controller import create_light_controller
from video_processor import VideoProcessor
from multi_camera_processor import MultiCameraProcessor
from get_youtube_stream import get_youtube_stream_url

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load configuration
def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logger.info(f"Configuration loaded from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        raise

# Initialize FastAPI app
app = FastAPI(
    title="Smart Lighting Control API",
    description="Object detection-based automated lighting control system using YOLOv8",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
config = load_config()
camera: Optional[CameraStream] = None
detector: Optional[ObjectDetector] = None
light_controller = None
video_processor: Optional[VideoProcessor] = None
multi_camera_processor: Optional[MultiCameraProcessor] = None
use_multi_camera = False


# Pydantic models for request/response
class ConfigUpdate(BaseModel):
    """Model for configuration updates"""
    camera: Optional[Dict[str, Any]] = None
    detection: Optional[Dict[str, Any]] = None
    lighting: Optional[Dict[str, Any]] = None


class LightControl(BaseModel):
    """Model for manual light control"""
    brightness: int
    duration: Optional[float] = None


class MessageResponse(BaseModel):
    """Standard message response"""
    message: str
    success: bool = True


class CameraSwitchRequest(BaseModel):
    """Model for camera switch request"""
    camera_id: str


class YouTubeStreamRequest(BaseModel):
    """Model for YouTube stream URL extraction"""
    camera_id: str
    youtube_url: str


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    global camera, detector, light_controller, video_processor, multi_camera_processor, use_multi_camera
    
    logger.info("Starting Smart Lighting Control System...")
    
    try:
        # Initialize detector (shared by all cameras)
        detector = ObjectDetector(config['detection'])
        logger.info("Object detector initialized")
        
        # Initialize light controller
        light_controller = create_light_controller(config['lighting'])
        logger.info("Light controller initialized")
        
        # Check if multi-camera mode is enabled
        multi_camera_config = config.get('camera', {}).get('multi_camera', {})
        use_multi_camera = multi_camera_config.get('enabled', False)
        
        if use_multi_camera and 'cameras' in multi_camera_config:
            # Initialize multi-camera processor
            logger.info("Initializing multi-camera mode...")
            cameras = {}
            
            for camera_id, camera_config in multi_camera_config['cameras'].items():
                cam_config = {
                    'source': camera_config['url'],
                    'fps': config['camera'].get('fps', 30),
                    'resolution': config['camera'].get('resolution', {'width': 640, 'height': 480})
                }
                cameras[camera_id] = CameraStream(cam_config)
                logger.info(f"Camera {camera_id} ({camera_config['name']}) configured")
            
            multi_camera_processor = MultiCameraProcessor(
                cameras=cameras,
                detector=detector,
                light_controller=light_controller,
                config=config['detection']
            )
            logger.info(f"Multi-camera processor initialized with {len(cameras)} cameras")
        else:
            # Initialize single camera mode (legacy)
            logger.info("Initializing single camera mode...")
            camera = CameraStream(config['camera'])
            logger.info("Camera initialized")
            
            video_processor = VideoProcessor(
                camera=camera,
                detector=detector,
                light_controller=light_controller,
                config=config['detection']
            )
            logger.info("Video processor initialized")
        
        logger.info("System initialization complete")
    
    except Exception as e:
        logger.error(f"Error during startup: {e}", exc_info=True)
        raise


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global video_processor, multi_camera_processor, camera
    
    logger.info("Shutting down...")
    
    if use_multi_camera and multi_camera_processor:
        if multi_camera_processor.is_running:
            multi_camera_processor.stop()
    elif video_processor:
        if video_processor.is_running:
            video_processor.stop()
    
    if camera:
        camera.disconnect()
    
    logger.info("Shutdown complete")


# API Endpoints

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the dashboard HTML"""
    dashboard_path = Path(__file__).parent / "dashboard.html"
    if dashboard_path.exists():
        return FileResponse(dashboard_path)
    else:
        return """
        <html>
            <body>
                <h1>Smart Lighting Control API</h1>
                <p>Dashboard not found. Please ensure dashboard.html exists.</p>
                <p><a href="/docs">View API Documentation</a></p>
            </body>
        </html>
        """


@app.get("/api")
async def api_info():
    """API information"""
    return {
        "name": "Smart Lighting Control API",
        "version": "1.0.0",
        "description": "Object detection-based automated lighting control",
        "endpoints": {
            "dashboard": "/",
            "status": "/status",
            "start": "/start",
            "stop": "/stop",
            "stream": "/stream",
            "lights": "/lights/*",
            "docs": "/docs"
        }
    }


@app.get("/status")
async def get_status():
    """Get current system status"""
    processor = multi_camera_processor if use_multi_camera else video_processor
    if not processor:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    status = processor.get_status()
    status['multi_camera_mode'] = use_multi_camera
    return status


@app.post("/start")
async def start_processing():
    """Start video processing and light control"""
    processor = multi_camera_processor if use_multi_camera else video_processor
    if not processor:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    if processor.is_running:
        return MessageResponse(
            message="Video processor already running",
            success=False
        )
    
    try:
        processor.start()
        mode = "multi-camera" if use_multi_camera else "single camera"
        return MessageResponse(message=f"Video processing started ({mode} mode)")
    except Exception as e:
        logger.error(f"Error starting video processor: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stop")
async def stop_processing():
    """Stop video processing"""
    processor = multi_camera_processor if use_multi_camera else video_processor
    if not processor:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    if not processor.is_running:
        return MessageResponse(
            message="Video processor not running",
            success=False
        )
    
    try:
        processor.stop()
        return MessageResponse(message="Video processing stopped")
    except Exception as e:
        logger.error(f"Error stopping video processor: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        video_processor.stop()
        return MessageResponse(message="Video processing stopped")
    except Exception as e:
        logger.error(f"Error stopping video processor: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pause")
async def pause_processing():
    """Pause video processing"""
    processor = multi_camera_processor if use_multi_camera else video_processor
    if not processor:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    processor.pause()
    return MessageResponse(message="Video processing paused")


@app.post("/resume")
async def resume_processing():
    """Resume video processing"""
    processor = multi_camera_processor if use_multi_camera else video_processor
    if not processor:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    processor.resume()
    return MessageResponse(message="Video processing resumed")


@app.get("/stream")
async def video_stream():
    """Stream processed video with detections"""
    processor = multi_camera_processor if use_multi_camera else video_processor
    if not processor:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    if not processor.is_running:
        raise HTTPException(status_code=400, detail="Video processor not running. Start it first with POST /start")
    
    def generate_frames():
        """Generate video frames"""
        while processor.is_running:
            # Get frame based on mode
            if use_multi_camera:
                # For multi-camera, show combined view
                frame = multi_camera_processor.get_combined_frame()
            else:
                frame = video_processor.get_latest_frame()
            
            if frame is not None:
                # Encode frame as JPEG
                ret, buffer = cv2.imencode('.jpg', frame)
                if ret:
                    frame_bytes = buffer.tobytes()
                    
                    # Yield frame in multipart format
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/lights/status")
async def get_light_status():
    """Get current light status"""
    if not light_controller:
        raise HTTPException(status_code=503, detail="Light controller not initialized")
    
    return light_controller.get_status()


@app.post("/lights/manual")
async def manual_light_control(control: LightControl):
    """Manually control lights"""
    if not light_controller:
        raise HTTPException(status_code=503, detail="Light controller not initialized")
    
    try:
        brightness = max(0, min(100, control.brightness))
        
        if brightness == 0:
            light_controller.turn_off()
        else:
            light_controller.turn_on(brightness)
        
        return {
            "message": f"Light brightness set to {brightness}%",
            "brightness": brightness,
            "status": light_controller.get_status()
        }
    except Exception as e:
        logger.error(f"Error controlling lights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/lights/on")
async def turn_lights_on(brightness: Optional[int] = None):
    """Turn lights on"""
    if not light_controller:
        raise HTTPException(status_code=503, detail="Light controller not initialized")
    
    light_controller.turn_on(brightness)
    return MessageResponse(message="Lights turned on")


@app.post("/lights/off")
async def turn_lights_off():
    """Turn lights off"""
    if not light_controller:
        raise HTTPException(status_code=503, detail="Light controller not initialized")
    
    light_controller.turn_off()
    return MessageResponse(message="Lights turned off")


@app.get("/detections/history")
async def get_detection_history(limit: int = 100):
    """Get recent detection history"""
    if not video_processor:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    return {
        "history": video_processor.get_detection_history(limit),
        "total_count": len(video_processor.detection_history)
    }


@app.post("/config/update")
async def update_config(config_update: ConfigUpdate):
    """Update system configuration"""
    global config
    
    try:
        updated_sections = []
        
        # Update detection config
        if config_update.detection and detector:
            config['detection'].update(config_update.detection)
            detector.update_config(config['detection'])
            updated_sections.append("detection")
        
        # Note: Camera and lighting updates require restart
        if config_update.camera:
            config['camera'].update(config_update.camera)
            updated_sections.append("camera (requires restart)")
        
        if config_update.lighting:
            config['lighting'].update(config_update.lighting)
            updated_sections.append("lighting (requires restart)")
        
        return {
            "message": "Configuration updated",
            "updated_sections": updated_sections,
            "note": "Some changes may require system restart"
        }
    
    except Exception as e:
        logger.error(f"Error updating configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/config")
async def get_config():
    """Get current configuration"""
    return config


@app.post("/stats/reset")
async def reset_stats():
    """Reset statistics"""
    if not video_processor:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    video_processor.reset_stats()
    return MessageResponse(message="Statistics reset")


@app.get("/camera/list")
async def list_cameras():
    """List all available camera sources"""
    if 'sources' not in config['camera']:
        return {
            "message": "No multiple camera sources configured",
            "current_source": config['camera'].get('source', 'Unknown')
        }
    
    sources = config['camera']['sources']
    current_source = config['camera'].get('source', '')
    
    camera_list = []
    for camera_id, camera_info in sources.items():
        camera_list.append({
            "id": camera_id,
            "name": camera_info.get('name', camera_id),
            "url": camera_info.get('url', ''),
            "type": camera_info.get('type', 'standard'),
            "is_active": camera_info.get('url') == current_source
        })
    
    return {
        "cameras": camera_list,
        "total": len(camera_list)
    }


@app.post("/camera/switch")
async def switch_camera(request: CameraSwitchRequest):
    """Switch active camera in multi-camera mode or switch source in single mode"""
    global config, camera, video_processor
    
    camera_id = request.camera_id
    
    # Multi-camera mode: just switch which camera to display
    if use_multi_camera and multi_camera_processor:
        if camera_id in multi_camera_processor.camera_processors:
            multi_camera_processor.set_active_camera(camera_id)
            return {
                "message": f"Switched to camera: {camera_id}",
                "camera_id": camera_id,
                "mode": "multi-camera"
            }
        else:
            available = list(multi_camera_processor.camera_processors.keys())
            raise HTTPException(
                status_code=404,
                detail=f"Camera '{camera_id}' not found. Available: {available}"
            )
    
    # Single camera mode: switch camera source (legacy behavior)
    if 'sources' not in config['camera']:
        raise HTTPException(
            status_code=400,
            detail="Multiple camera sources not configured in config.yaml"
        )
    
    # Validate camera ID
    if camera_id not in config['camera']['sources']:
        available = list(config['camera']['sources'].keys())
        raise HTTPException(
            status_code=404,
            detail=f"Camera '{camera_id}' not found. Available: {available}"
        )
    
    # Get camera configuration
    camera_source_config = config['camera']['sources'][camera_id]
    camera_name = camera_source_config.get('name', camera_id)
    
    try:
        # Stop video processing if running
        was_running = False
        if video_processor and video_processor.is_running:
            was_running = True
            video_processor.stop()
            logger.info("Stopped video processor for camera switch")
        
        # Disconnect old camera
        if camera:
            camera.disconnect()
            logger.info("Disconnected old camera")
        
        # Update config with the selected camera's full configuration
        new_camera_config = config['camera'].copy()
        
        # Merge camera source config into main camera config
        for key, value in camera_source_config.items():
            if key != 'name':  # Don't override config keys with 'name'
                new_camera_config[key] = value
        
        # Keep FPS and resolution from main config if not specified
        new_camera_config['fps'] = config['camera'].get('fps', 30)
        new_camera_config['resolution'] = config['camera'].get('resolution', {'width': 640, 'height': 480})
        
        # Initialize new camera with merged config
        camera = CameraStream(new_camera_config)
        if not camera.connect():
            raise Exception("Failed to connect to new camera source")
        
        logger.info(f"Connected to new camera: {camera_name}")
        
        # Update main config
        config['camera']['source'] = camera_source_config.get('url', camera_source_config)
        
        # Update video processor with new camera
        if video_processor:
            video_processor.camera = camera
        
        # Restart video processing if it was running
        if was_running and video_processor:
            video_processor.start()
            logger.info("Restarted video processor with new camera")
        
        return {
            "message": f"Successfully switched to camera: {camera_name}",
            "camera_id": camera_id,
            "camera_name": camera_name,
            "camera_type": camera_source_config.get('type', 'standard'),
            "processing_resumed": was_running,
            "mode": "single-camera"
        }
    
    except Exception as e:
        logger.error(f"Error switching camera: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to switch camera: {str(e)}")


@app.post("/camera/set-stream")
async def set_custom_stream(request: YouTubeStreamRequest):
    """
    Extract stream URL from YouTube or set custom RTSP/stream URL for specified camera
    
    Args:
        camera_id: ID of camera to update (e.g., 'camera1', 'camera2', 'real_camera')
        youtube_url: YouTube video/livestream URL or RTSP URL (e.g., rtsp://camera.openlab...)
    
    Returns:
        Success message with extracted stream URL
    """
    global config, camera, video_processor
    
    # Check if multiple sources are configured
    if 'sources' not in config['camera']:
        raise HTTPException(
            status_code=400,
            detail="Multiple camera sources not configured in config.yaml"
        )
    
    # Validate camera ID
    camera_id = request.camera_id
    if camera_id not in config['camera']['sources']:
        available = list(config['camera']['sources'].keys())
        raise HTTPException(
            status_code=404,
            detail=f"Camera '{camera_id}' not found. Available: {available}"
        )
    
    try:
        # Check if it's an RTSP URL or YouTube URL
        input_url = request.youtube_url.strip()
        
        if input_url.startswith('rtsp://') or (input_url.startswith('http') and 'youtube' not in input_url.lower()):
            # Direct stream URL (RTSP, HTTP, etc.)
            stream_url = input_url
            logger.info(f"Using direct stream URL: {stream_url}")
        else:
            # YouTube URL - extract stream
            logger.info(f"Extracting stream URL from YouTube: {request.youtube_url}")
            stream_url = get_youtube_stream_url(request.youtube_url)
            
            if not stream_url:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to extract stream URL from YouTube. Please check the URL."
                )
        
        # Update config in memory
        config['camera']['sources'][camera_id]['url'] = stream_url
        
        # Save to config.yaml file
        config_path = Path("config.yaml")
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        logger.info(f"Updated {camera_id} with new stream URL")
        
        stream_type = "RTSP" if stream_url.startswith('rtsp://') else "Stream"
        return {
            "message": f"Successfully updated {camera_id} with {stream_type}",
            "camera_id": camera_id,
            "camera_name": config['camera']['sources'][camera_id].get('name', camera_id),
            "input_url": request.youtube_url,
            "stream_url": stream_url[:100] + "..." if len(stream_url) > 100 else stream_url,
            "stream_type": stream_type,
            "note": "Use 'Camera Source' dropdown to switch to this camera"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting YouTube stream: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract YouTube stream: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health_status = {
        "status": "healthy",
        "camera": camera.is_opened if camera else False,
        "detector": detector is not None,
        "light_controller": light_controller is not None,
        "video_processor": video_processor.is_running if video_processor else False
    }
    
    is_healthy = all([
        camera and camera.is_opened,
        detector is not None,
        light_controller is not None,
        video_processor is not None
    ])
    
    if not is_healthy:
        health_status["status"] = "degraded"
    
    return health_status


# Main entry point
if __name__ == "__main__":
    api_config = config.get('api', {})
    
    uvicorn.run(
        "main:app",
        host=api_config.get('host', '0.0.0.0'),
        port=api_config.get('port', 8000),
        reload=api_config.get('reload', False),
        log_level=api_config.get('log_level', 'info').lower()
    )
