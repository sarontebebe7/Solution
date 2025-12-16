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
from database import init_database, get_db

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
db = None  # Database manager


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


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    global camera, detector, light_controller, video_processor, db
    
    logger.info("Starting Smart Lighting Control System...")
    
    try:
        # Initialize database
        if config.get('database', {}).get('enabled', True):
            db_url = config.get('database', {}).get('url', 'sqlite:///smart_lighting.db')
            db = init_database(db_url)
            logger.info("Database initialized")
            
            # Start system session
            db.start_session(config)
        
        # Initialize camera
        camera = CameraStream(config['camera'])
        logger.info("Camera initialized")
        
        # Initialize detector
        detector = ObjectDetector(config['detection'])
        logger.info("Object detector initialized")
        
        # Initialize light controller
        light_controller = create_light_controller(config['lighting'])
        logger.info("Light controller initialized")
        
        # Initialize video processor
        video_processor = VideoProcessor(
            camera=camera,
            detector=detector,
            light_controller=light_controller,
            config=config['detection'],
            database=db  # Pass database to video processor
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
    global video_processor, camera, db
    
    logger.info("Shutting down...")
    
    if video_processor and video_processor.is_running:
        video_processor.stop()
    
    # End database session
    if db:
        stats = video_processor.stats if video_processor else None
        db.end_session(stats)
        logger.info("Database session ended")
    
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
    if not video_processor:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    return video_processor.get_status()


@app.post("/start")
async def start_processing():
    """Start video processing and light control"""
    if not video_processor:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    if video_processor.is_running:
        if db:
            db.log_user_action('start', 'Attempted to start already running processor', 
                             endpoint='/start', success=False)
        return MessageResponse(
            message="Video processor already running",
            success=False
        )
    
    try:
        video_processor.start()
        if db:
            db.log_user_action('start', 'Started video processing', endpoint='/start')
        return MessageResponse(message="Video processing started")
    except Exception as e:
        logger.error(f"Error starting video processor: {e}")
        if db:
            db.log_user_action('start', 'Failed to start video processing', 
                             endpoint='/start', success=False, error_message=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stop")
async def stop_processing():
    """Stop video processing"""
    if not video_processor:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    if not video_processor.is_running:
        if db:
            db.log_user_action('stop', 'Attempted to stop already stopped processor',
                             endpoint='/stop', success=False)
        return MessageResponse(
            message="Video processor not running",
            success=False
        )
    
    try:
        video_processor.stop()
        if db:
            db.log_user_action('stop', 'Stopped video processing', endpoint='/stop')
        return MessageResponse(message="Video processing stopped")
    except Exception as e:
        logger.error(f"Error stopping video processor: {e}")
        if db:
            db.log_user_action('stop', 'Failed to stop video processing',
                             endpoint='/stop', success=False, error_message=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pause")
async def pause_processing():
    """Pause video processing"""
    if not video_processor:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    video_processor.pause()
    return MessageResponse(message="Video processing paused")


@app.post("/resume")
async def resume_processing():
    """Resume video processing"""
    if not video_processor:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    video_processor.resume()
    return MessageResponse(message="Video processing resumed")


@app.get("/stream")
async def video_stream():
    """Stream processed video with detections"""
    if not video_processor:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    if not video_processor.is_running:
        raise HTTPException(status_code=400, detail="Video processor not running. Start it first with POST /start")
    
    def generate_frames():
        """Generate video frames"""
        while video_processor.is_running:
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


# Database API Endpoints

@app.get("/db/stats")
async def get_database_stats():
    """Get comprehensive database statistics"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not enabled")
    
    try:
        return db.get_dashboard_stats()
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/db/detections")
async def get_detections(limit: int = 100, triggered_only: bool = False):
    """Get recent detection events"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not enabled")
    
    try:
        detections = db.get_recent_detections(limit=limit, triggered_only=triggered_only)
        return {
            "count": len(detections),
            "detections": detections
        }
    except Exception as e:
        logger.error(f"Error getting detections: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/db/detections/stats")
async def get_detection_statistics(hours: int = 24):
    """Get detection statistics for the last N hours"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not enabled")
    
    try:
        return db.get_detection_stats(hours=hours)
    except Exception as e:
        logger.error(f"Error getting detection stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/db/lights")
async def get_light_events(limit: int = 100):
    """Get recent light control events"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not enabled")
    
    try:
        events = db.get_recent_light_events(limit=limit)
        return {
            "count": len(events),
            "events": events
        }
    except Exception as e:
        logger.error(f"Error getting light events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/db/sessions")
async def get_session_history(limit: int = 50):
    """Get system session history"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not enabled")
    
    try:
        sessions = db.get_session_history(limit=limit)
        return {
            "count": len(sessions),
            "sessions": sessions
        }
    except Exception as e:
        logger.error(f"Error getting sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/db/user-actions")
async def get_user_action_history(limit: int = 100):
    """Get user action history"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not enabled")
    
    try:
        actions = db.get_user_actions(limit=limit)
        return {
            "count": len(actions),
            "actions": actions
        }
    except Exception as e:
        logger.error(f"Error getting user actions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/db/cleanup")
async def cleanup_old_data(days_to_keep: int = 30):
    """Manually trigger database cleanup"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not enabled")
    
    try:
        db.cleanup_old_data(days_to_keep=days_to_keep)
        return MessageResponse(message=f"Cleaned up data older than {days_to_keep} days")
    except Exception as e:
        logger.error(f"Error cleaning up data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
