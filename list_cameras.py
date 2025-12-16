"""
List all available cameras/video devices
"""
import cv2

def list_cameras():
    """Test cameras 0-5 and show which ones work"""
    print("Scanning for cameras...\n")
    working_cameras = []
    
    for i in range(6):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = int(cap.get(cv2.CAP_PROP_FPS))
                print(f"✅ Camera {i}: {width}x{height} @ {fps}fps")
                working_cameras.append(i)
            else:
                print(f"⚠️  Camera {i}: Opened but cannot read frames")
            cap.release()
        else:
            print(f"❌ Camera {i}: Not available")
    
    if working_cameras:
        print(f"\n💡 Use camera {working_cameras[0]} in webcam_stream_server.py")
        print(f"   python webcam_stream_server.py --camera {working_cameras[0]}")
    else:
        print("\n❌ No working cameras found!")

if __name__ == '__main__':
    list_cameras()
