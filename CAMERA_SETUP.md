# Public Camera Streams for Testing

## Free Public Camera Streams

Here are some free public camera streams you can use for testing:

### 1. **Sample RTSP Streams**
```
rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mp4
```
- Sample video with animated characters (good for testing)
- RTSP protocol

### 2. **EarthCam Public Streams**
Visit [EarthCam](https://www.earthcam.com/) for live streams from around the world:
- Times Square: `https://www.earthcam.com/usa/newyork/timessquare/`
- Abbey Road: `https://www.earthcam.com/world/england/london/abbeyroad/`

Note: You'll need to extract the actual stream URL using browser developer tools.

### 3. **Insecam - Public IP Cameras**
Visit [Insecam](http://www.insecam.org/) for access to public IP cameras worldwide.

### 4. **YouTube Live Streams**
You can use public YouTube live streams with `youtube-dl` or similar tools to extract the stream URL.

### 5. **Traffic Cameras**
Many cities provide public traffic camera feeds:
- Check your local city's transportation website
- Usually available as MJPEG or RTSP streams

## How to Use in the Dashboard

### Method 1: Using the Dashboard UI
1. Open the dashboard at `http://localhost:8000`
2. Scroll to "Camera Configuration"
3. Select "Custom URL..." from the dropdown
4. Enter your camera stream URL
5. Click "Save & Apply Configuration"
6. **Restart the server** for camera changes to take effect

### Method 2: Edit config.yaml Directly
1. Open `config.yaml` in a text editor
2. Find the `camera.source` setting
3. Change it to your desired stream:
   ```yaml
   camera:
     source: "rtsp://your-stream-url"
   ```
4. Save the file
5. Restart the server

## Testing with Your Own Camera

### Webcam (Easiest)
```yaml
camera:
  source: "0"  # 0 for default webcam, 1 for second camera, etc.
```

### Smartphone as IP Camera

#### Option 1: IP Webcam (Android)
1. Install "IP Webcam" from Google Play Store
2. Start the server in the app
3. Note the IP address shown (e.g., `http://192.168.1.100:8080`)
4. Use this in config:
   ```yaml
   camera:
     source: "http://192.168.1.100:8080/video"
   ```

#### Option 2: DroidCam (Android/iOS)
1. Install DroidCam on your phone and computer
2. Connect via WiFi
3. Use the provided IP address

#### Option 3: iVCam (iOS)
1. Install iVCam on iPhone and computer
2. Connect and use as camera source

### IP Security Camera
If you have an IP camera:
```yaml
camera:
  source: "rtsp://username:password@192.168.1.100:554/stream1"
```

Common formats:
- **Hikvision**: `rtsp://admin:password@192.168.1.64:554/Streaming/Channels/101`
- **Dahua**: `rtsp://admin:password@192.168.1.108:554/cam/realmonitor?channel=1&subtype=0`
- **Axis**: `rtsp://root:password@192.168.1.100/axis-media/media.amp`

## Detection Settings

### Adjust Sensitivity
In the dashboard or `config.yaml`:

```yaml
detection:
  confidence: 0.5  # 0.3 = more sensitive, 0.7 = less sensitive
  min_object_size: 5000  # Minimum area in pixels to trigger lights
```

**For outdoor cameras:**
- Use higher `min_object_size` (10000-20000) to ignore small objects
- Set `confidence` to 0.6+ for fewer false positives

**For indoor cameras:**
- Use lower `min_object_size` (3000-5000)
- Set `confidence` to 0.5 for balanced detection

### Target Specific Objects
```yaml
detection:
  target_classes:
    - "person"  # Only detect people
  ignore_classes:
    - "bird"
    - "cat"
    - "dog"
```

## Troubleshooting Camera Connections

### Camera Not Connecting
1. **Check the URL format** - ensure it's correct for your camera type
2. **Test with VLC Media Player** - open VLC → Media → Open Network Stream
3. **Check network connectivity** - ping the camera IP
4. **Verify credentials** - username/password for RTSP streams
5. **Try backup sources** - use webcam (`"0"`) as fallback

### Poor Performance
1. **Reduce resolution** in config.yaml:
   ```yaml
   camera:
     resolution:
       width: 640
       height: 480
   ```
2. **Increase frame interval**:
   ```yaml
   detection:
     frame_interval: 2  # Process every 2nd frame
   ```
3. **Use a faster YOLOv8 model**:
   ```yaml
   detection:
     model: "yolov8n"  # Nano - fastest
   ```

### Stream Keeps Disconnecting
1. Enable backup sources in config.yaml
2. Check network stability
3. Use local camera for testing
4. Increase timeout settings

## Recommended Setup for Best Results

1. **Start with webcam** to verify everything works
2. **Test with public RTSP stream** to validate streaming
3. **Configure your actual camera** once basics are working
4. **Adjust detection settings** based on your environment
5. **Connect real lights** when ready for production

## Need Help?

- Check the logs in the terminal where you run `python main.py`
- Test camera URL in VLC first
- Use the dashboard's detection log to see what's being detected
- Adjust sensitivity settings in real-time through the dashboard
