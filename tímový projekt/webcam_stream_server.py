"""
Simple Webcam MJPEG Streaming Server
Share your USB webcam over HTTP for team access
"""
import cv2
from flask import Flask, Response
import argparse

app = Flask(__name__)

# Global camera object
camera = None

def init_camera(camera_index=0):
    """Initialize camera"""
    global camera
    camera = cv2.VideoCapture(camera_index)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    camera.set(cv2.CAP_PROP_FPS, 30)
    return camera.isOpened()

def generate_frames():
    """Generate frames from camera"""
    while True:
        success, frame = camera.read()
        if not success:
            break
        
        # Encode frame as JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        
        # Yield frame in multipart format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    """Info page"""
    return """
    <h1>Webcam Stream Server</h1>
    <p>Stream URL: <code>http://YOUR_IP:5000/video</code></p>
    <p><a href="/video">View Stream</a></p>
    <p><a href="/preview">Preview in Browser</a></p>
    """

@app.route('/video')
def video():
    """Video stream endpoint for OpenCV/Docker"""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/preview')
def preview():
    """Preview page"""
    return """
    <html>
    <head><title>Webcam Preview</title></head>
    <body>
        <h1>Webcam Stream Preview</h1>
        <img src="/video" width="1280" height="720" />
        <p>Use in config.yaml: <code>source: "http://YOUR_IP:5000/video"</code></p>
    </body>
    </html>
    """

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Webcam Streaming Server')
    parser.add_argument('--camera', type=int, default=0, help='Camera index (default: 0)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind (default: 5000)')
    args = parser.parse_args()
    
    print(f"Initializing camera {args.camera}...")
    if not init_camera(args.camera):
        print("ERROR: Could not open camera!")
        exit(1)
    
    print(f"\n🎥 Webcam stream server starting...")
    print(f"📡 Stream URL: http://YOUR_IP:{args.port}/video")
    print(f"🌐 Preview: http://localhost:{args.port}/preview")
    print(f"\n💡 Use in config.yaml:")
    print(f"   camera:")
    print(f"     source: \"http://YOUR_IP:{args.port}/video\"")
    print(f"\nPress Ctrl+C to stop\n")
    
    try:
        app.run(host=args.host, port=args.port, threaded=True)
    finally:
        if camera:
            camera.release()
