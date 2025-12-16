"""
Database Module - SQLite with SQLAlchemy ORM
Tracks detection events, light control, and system statistics
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, JSON, Text, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()


# Database Models

class DetectionEvent(Base):
    """Records object detection events"""
    __tablename__ = 'detection_events'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Detection details
    object_class = Column(String(50), nullable=False, index=True)
    confidence = Column(Float, nullable=False)
    bbox_x1 = Column(Integer)
    bbox_y1 = Column(Integer)
    bbox_x2 = Column(Integer)
    bbox_y2 = Column(Integer)
    bbox_area = Column(Integer)
    
    # Context
    frame_number = Column(Integer)
    triggered_lights = Column(Boolean, default=False, index=True)
    
    # Additional data
    extra_data = Column(JSON, nullable=True)
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'object_class': self.object_class,
            'confidence': self.confidence,
            'bbox': [self.bbox_x1, self.bbox_y1, self.bbox_x2, self.bbox_y2],
            'bbox_area': self.bbox_area,
            'frame_number': self.frame_number,
            'triggered_lights': self.triggered_lights,
            'extra_data': self.extra_data
        }


class LightControlEvent(Base):
    """Records light control changes"""
    __tablename__ = 'light_control_events'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Light state
    action = Column(String(20), nullable=False)  # 'on', 'off', 'dim', 'manual'
    brightness_before = Column(Integer)
    brightness_after = Column(Integer)
    
    # Trigger
    trigger_type = Column(String(50), index=True)  # 'detection', 'manual', 'auto_off', 'system'
    trigger_source = Column(String(100))  # detection_id, user_id, etc.
    
    # Additional info
    extra_data = Column(JSON, nullable=True)
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'action': self.action,
            'brightness_before': self.brightness_before,
            'brightness_after': self.brightness_after,
            'trigger_type': self.trigger_type,
            'trigger_source': self.trigger_source,
            'extra_data': self.extra_data
        }


class SystemSession(Base):
    """Records system runtime sessions"""
    __tablename__ = 'system_sessions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    start_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    end_time = Column(DateTime, nullable=True)
    
    # Statistics
    total_frames_processed = Column(Integer, default=0)
    total_detections = Column(Integer, default=0)
    total_trigger_events = Column(Integer, default=0)
    avg_fps = Column(Float, default=0.0)
    
    # System info
    config_snapshot = Column(JSON, nullable=True)
    status = Column(String(20), default='running')  # 'running', 'stopped', 'error'
    error_message = Column(Text, nullable=True)
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'total_frames_processed': self.total_frames_processed,
            'total_detections': self.total_detections,
            'total_trigger_events': self.total_trigger_events,
            'avg_fps': self.avg_fps,
            'status': self.status,
            'error_message': self.error_message
        }


class UserAction(Base):
    """Records manual user interactions"""
    __tablename__ = 'user_actions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    action_type = Column(String(50), nullable=False, index=True)  # 'start', 'stop', 'config_change', 'manual_light'
    description = Column(Text)
    
    # Request details
    endpoint = Column(String(100))
    parameters = Column(JSON, nullable=True)
    
    # Result
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'action_type': self.action_type,
            'description': self.description,
            'endpoint': self.endpoint,
            'parameters': self.parameters,
            'success': self.success,
            'error_message': self.error_message
        }


class SensorReading(Base):
    """Records IoT sensor readings for future integration"""
    __tablename__ = 'sensor_readings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Sensor identification
    sensor_id = Column(String(100), nullable=False, index=True)  # e.g., "temp_sensor_01"
    sensor_type = Column(String(50), nullable=False, index=True)  # e.g., "temperature", "humidity", "motion", "light"
    location = Column(String(100))  # e.g., "living_room", "bedroom"
    
    # Reading data
    value = Column(Float, nullable=False)  # The actual sensor reading
    unit = Column(String(20))  # e.g., "celsius", "percent", "lux", "ppm"
    
    # Additional metadata
    extra_data = Column(JSON, nullable=True)  # Any extra sensor-specific data
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'sensor_id': self.sensor_id,
            'sensor_type': self.sensor_type,
            'location': self.location,
            'value': self.value,
            'unit': self.unit,
            'extra_data': self.extra_data
        }


# Database Manager

class DatabaseManager:
    """Manages database connections and operations"""
    
    def __init__(self, db_url: str = "sqlite:///smart_lighting.db"):
        """
        Initialize database manager
        
        Args:
            db_url: SQLAlchemy database URL
                    Examples: 
                    - SQLite: "sqlite:///smart_lighting.db"
                    - PostgreSQL: "postgresql://user:pass@localhost/dbname"
                    - MySQL: "mysql+pymysql://user:pass@localhost/dbname"
        """
        self.db_url = db_url
        self.engine = create_engine(db_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.current_session_id: Optional[int] = None
        
        # Create tables
        self._create_tables()
        logger.info(f"Database initialized: {db_url}")
    
    def _create_tables(self):
        """Create database tables if they don't exist"""
        Base.metadata.create_all(self.engine)
        logger.info("Database tables created/verified")
    
    def get_session(self) -> Session:
        """Get a new database session"""
        return self.SessionLocal()
    
    # Detection Event Operations
    
    def log_detection(self, detection: Dict[str, Any], frame_number: int, 
                     triggered_lights: bool = False, extra_data: Optional[dict] = None) -> int:
        """
        Log a detection event
        
        Args:
            detection: Detection dictionary with class, confidence, bbox
            frame_number: Current frame number
            triggered_lights: Whether this detection triggered lights
            extra_data: Additional metadata
            
        Returns:
            Detection event ID
        """
        session = self.get_session()
        try:
            bbox = detection.get('bbox', [0, 0, 0, 0])
            event = DetectionEvent(
                object_class=detection.get('class', 'unknown'),
                confidence=detection.get('confidence', 0.0),
                bbox_x1=bbox[0],
                bbox_y1=bbox[1],
                bbox_x2=bbox[2],
                bbox_y2=bbox[3],
                bbox_area=detection.get('area', 0),
                frame_number=frame_number,
                triggered_lights=triggered_lights,
                extra_data=extra_data
            )
            session.add(event)
            session.commit()
            event_id = event.id
            logger.debug(f"Logged detection event {event_id}: {detection.get('class')}")
            return event_id
        except Exception as e:
            session.rollback()
            logger.error(f"Error logging detection: {e}")
            return -1
        finally:
            session.close()
    
    def get_recent_detections(self, limit: int = 100, 
                             triggered_only: bool = False) -> List[Dict]:
        """Get recent detection events"""
        session = self.get_session()
        try:
            query = session.query(DetectionEvent)
            if triggered_only:
                query = query.filter(DetectionEvent.triggered_lights == True)
            
            events = query.order_by(DetectionEvent.timestamp.desc()).limit(limit).all()
            return [e.to_dict() for e in events]
        finally:
            session.close()
    
    def get_detection_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get detection statistics for the last N hours"""
        from sqlalchemy import func
        from datetime import timedelta
        
        session = self.get_session()
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Total detections
            total = session.query(func.count(DetectionEvent.id)).filter(
                DetectionEvent.timestamp >= cutoff_time
            ).scalar()
            
            # Detections by class
            by_class = session.query(
                DetectionEvent.object_class,
                func.count(DetectionEvent.id)
            ).filter(
                DetectionEvent.timestamp >= cutoff_time
            ).group_by(DetectionEvent.object_class).all()
            
            # Triggered lights
            triggered = session.query(func.count(DetectionEvent.id)).filter(
                DetectionEvent.timestamp >= cutoff_time,
                DetectionEvent.triggered_lights == True
            ).scalar()
            
            return {
                'total_detections': total or 0,
                'detections_by_class': {cls: count for cls, count in by_class},
                'triggered_lights': triggered or 0,
                'period_hours': hours
            }
        finally:
            session.close()
    
    # Light Control Event Operations
    
    def log_light_event(self, action: str, brightness_before: int, brightness_after: int,
                       trigger_type: str = 'system', trigger_source: Optional[str] = None,
                       extra_data: Optional[dict] = None) -> int:
        """Log a light control event"""
        session = self.get_session()
        try:
            event = LightControlEvent(
                action=action,
                brightness_before=brightness_before,
                brightness_after=brightness_after,
                trigger_type=trigger_type,
                trigger_source=trigger_source,
                extra_data=extra_data
            )
            session.add(event)
            session.commit()
            event_id = event.id
            logger.debug(f"Logged light event {event_id}: {action}")
            return event_id
        except Exception as e:
            session.rollback()
            logger.error(f"Error logging light event: {e}")
            return -1
        finally:
            session.close()
    
    def get_recent_light_events(self, limit: int = 100) -> List[Dict]:
        """Get recent light control events"""
        session = self.get_session()
        try:
            events = session.query(LightControlEvent).order_by(
                LightControlEvent.timestamp.desc()
            ).limit(limit).all()
            return [e.to_dict() for e in events]
        finally:
            session.close()
    
    # System Session Operations
    
    def start_session(self, config: Optional[dict] = None) -> int:
        """Start a new system session"""
        session = self.get_session()
        try:
            sys_session = SystemSession(
                config_snapshot=config,
                status='running'
            )
            session.add(sys_session)
            session.commit()
            self.current_session_id = sys_session.id
            logger.info(f"Started system session {self.current_session_id}")
            return self.current_session_id
        except Exception as e:
            session.rollback()
            logger.error(f"Error starting session: {e}")
            return -1
        finally:
            session.close()
    
    def end_session(self, stats: Optional[dict] = None, error_message: Optional[str] = None):
        """End the current system session"""
        if not self.current_session_id:
            return
        
        session = self.get_session()
        try:
            sys_session = session.query(SystemSession).get(self.current_session_id)
            if sys_session:
                sys_session.end_time = datetime.utcnow()
                sys_session.status = 'error' if error_message else 'stopped'
                sys_session.error_message = error_message
                
                if stats:
                    sys_session.total_frames_processed = stats.get('frames_processed', 0)
                    sys_session.total_detections = stats.get('total_detections', 0)
                    sys_session.total_trigger_events = stats.get('trigger_detections', 0)
                    sys_session.avg_fps = stats.get('fps', 0.0)
                
                session.commit()
                logger.info(f"Ended system session {self.current_session_id}")
        except Exception as e:
            session.rollback()
            logger.error(f"Error ending session: {e}")
        finally:
            session.close()
            self.current_session_id = None
    
    def get_session_history(self, limit: int = 50) -> List[Dict]:
        """Get recent system sessions"""
        session = self.get_session()
        try:
            sessions = session.query(SystemSession).order_by(
                SystemSession.start_time.desc()
            ).limit(limit).all()
            return [s.to_dict() for s in sessions]
        finally:
            session.close()
    
    # User Action Operations
    
    def log_user_action(self, action_type: str, description: str,
                       endpoint: Optional[str] = None, parameters: Optional[dict] = None,
                       success: bool = True, error_message: Optional[str] = None) -> int:
        """Log a user action"""
        session = self.get_session()
        try:
            action = UserAction(
                action_type=action_type,
                description=description,
                endpoint=endpoint,
                parameters=parameters,
                success=success,
                error_message=error_message
            )
            session.add(action)
            session.commit()
            action_id = action.id
            logger.debug(f"Logged user action {action_id}: {action_type}")
            return action_id
        except Exception as e:
            session.rollback()
            logger.error(f"Error logging user action: {e}")
            return -1
        finally:
            session.close()
    
    def get_user_actions(self, limit: int = 100) -> List[Dict]:
        """Get recent user actions"""
        session = self.get_session()
        try:
            actions = session.query(UserAction).order_by(
                UserAction.timestamp.desc()
            ).limit(limit).all()
            return [a.to_dict() for a in actions]
        finally:
            session.close()
    
    # Sensor Reading Operations
    
    def log_sensor_reading(self, sensor_id: str, sensor_type: str, value: float,
                          unit: Optional[str] = None, location: Optional[str] = None,
                          extra_data: Optional[dict] = None) -> int:
        """Log a sensor reading for future IoT integration"""
        session = self.get_session()
        try:
            reading = SensorReading(
                sensor_id=sensor_id,
                sensor_type=sensor_type,
                value=value,
                unit=unit,
                location=location,
                extra_data=extra_data
            )
            session.add(reading)
            session.commit()
            reading_id = reading.id
            logger.debug(f"Logged sensor reading {reading_id}: {sensor_type}={value}{unit or ''}")
            return reading_id
        except Exception as e:
            session.rollback()
            logger.error(f"Error logging sensor reading: {e}")
            return -1
        finally:
            session.close()
    
    def get_sensor_readings(self, sensor_type: Optional[str] = None, 
                           sensor_id: Optional[str] = None,
                           limit: int = 100) -> List[Dict]:
        """Get recent sensor readings with optional filtering"""
        session = self.get_session()
        try:
            query = session.query(SensorReading)
            
            if sensor_type:
                query = query.filter(SensorReading.sensor_type == sensor_type)
            if sensor_id:
                query = query.filter(SensorReading.sensor_id == sensor_id)
            
            readings = query.order_by(SensorReading.timestamp.desc()).limit(limit).all()
            return [r.to_dict() for r in readings]
        finally:
            session.close()
    
    def get_sensor_stats(self, sensor_type: str, hours: int = 24) -> Dict[str, Any]:
        """Get statistics for a specific sensor type over time period"""
        from datetime import timedelta
        
        session = self.get_session()
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            readings = session.query(SensorReading).filter(
                SensorReading.sensor_type == sensor_type,
                SensorReading.timestamp >= cutoff_time
            ).all()
            
            if not readings:
                return {'sensor_type': sensor_type, 'count': 0}
            
            values = [r.value for r in readings]
            return {
                'sensor_type': sensor_type,
                'count': len(readings),
                'min': min(values),
                'max': max(values),
                'avg': sum(values) / len(values),
                'latest': readings[0].to_dict(),
                'period_hours': hours
            }
        finally:
            session.close()
    
    # Analytics & Reports
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics for dashboard"""
        from datetime import timedelta
        
        session = self.get_session()
        try:
            now = datetime.utcnow()
            last_24h = now - timedelta(hours=24)
            last_7d = now - timedelta(days=7)
            
            # Last 24 hours stats
            detections_24h = session.query(func.count(DetectionEvent.id)).filter(
                DetectionEvent.timestamp >= last_24h
            ).scalar() or 0
            
            triggers_24h = session.query(func.count(DetectionEvent.id)).filter(
                DetectionEvent.timestamp >= last_24h,
                DetectionEvent.triggered_lights == True
            ).scalar() or 0
            
            # Last 7 days stats
            detections_7d = session.query(func.count(DetectionEvent.id)).filter(
                DetectionEvent.timestamp >= last_7d
            ).scalar() or 0
            
            # Current session
            current_session = None
            if self.current_session_id:
                current_session = session.query(SystemSession).get(self.current_session_id)
            
            return {
                'last_24_hours': {
                    'detections': detections_24h,
                    'light_triggers': triggers_24h
                },
                'last_7_days': {
                    'detections': detections_7d
                },
                'current_session': current_session.to_dict() if current_session else None
            }
        finally:
            session.close()
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Delete data older than specified days"""
        from datetime import timedelta
        
        session = self.get_session()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            # Delete old detections
            deleted_detections = session.query(DetectionEvent).filter(
                DetectionEvent.timestamp < cutoff_date
            ).delete()
            
            # Delete old light events
            deleted_lights = session.query(LightControlEvent).filter(
                LightControlEvent.timestamp < cutoff_date
            ).delete()
            
            # Delete old user actions
            deleted_actions = session.query(UserAction).filter(
                UserAction.timestamp < cutoff_date
            ).delete()
            
            session.commit()
            logger.info(f"Cleaned up old data: {deleted_detections} detections, "
                       f"{deleted_lights} light events, {deleted_actions} user actions")
        except Exception as e:
            session.rollback()
            logger.error(f"Error cleaning up data: {e}")
        finally:
            session.close()


# Global database instance
db_manager: Optional[DatabaseManager] = None


def init_database(db_url: str = "sqlite:///smart_lighting.db") -> DatabaseManager:
    """Initialize the global database instance"""
    global db_manager
    db_manager = DatabaseManager(db_url)
    return db_manager


def get_db() -> DatabaseManager:
    """Get the global database instance"""
    global db_manager
    if db_manager is None:
        db_manager = init_database()
    return db_manager
