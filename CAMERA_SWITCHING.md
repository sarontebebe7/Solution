# Multi-Camera Setup Guide

## Prepínanie medzi viacerými kamerami / Switching Between Multiple Cameras

Tento návod vysvetľuje ako nastaviť a prepínať medzi viacerými zdrojmi kamier.

---

## 🎥 Konfigurácia viacerých kamier

### Krok 1: Upraviť `config.yaml`

```yaml
camera:
  # Aktívny zdroj (default)
  source: "URL_FIRST_CAMERA"
  
  # Zoznam všetkých dostupných kamier
  sources:
    camera1:
      name: "YouTube Stream - Tokyo"
      url: "https://youtube_direct_url_1..."
    camera2:
      name: "Local Webcam"
      url: "http://192.168.1.15:5000/video"
    camera3:
      name: "YouTube Stream - NYC"
      url: "https://youtube_direct_url_2..."
```

### Krok 2: Získať YouTube URL (ak používaš YouTube)

```powershell
# Pre každý YouTube stream spusti:
pip install yt-dlp
python get_youtube_stream.py "https://www.youtube.com/watch?v=VIDEO_ID"

# Skopíruj vygenerované URL do config.yaml pod príslušnú kameru
```

---

## 🔄 Prepínanie kamier cez API

### Metóda 1: Cez Swagger UI (najjednoduchšie)

1. Otvor http://localhost:8000/docs
2. Nájdi endpoint **GET /camera/list** → zobrazí zoznam kamier
3. Nájdi endpoint **POST /camera/switch**
4. Klikni "Try it out"
5. Zadaj JSON:
   ```json
   {
     "camera_id": "camera2"
   }
   ```
6. Klikni "Execute"

### Metóda 2: Cez PowerShell/curl

```powershell
# Zobraziť zoznam kamier
Invoke-RestMethod -Uri http://localhost:8000/camera/list

# Prepnúť na camera2
$body = @{camera_id = "camera2"} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8000/camera/switch -Body $body -ContentType "application/json"

# Alebo curl
curl -X POST http://localhost:8000/camera/switch -H "Content-Type: application/json" -d "{\"camera_id\":\"camera3\"}"
```

### Metóda 3: Cez Python

```python
import requests

# List cameras
response = requests.get("http://localhost:8000/camera/list")
print(response.json())

# Switch camera
response = requests.post(
    "http://localhost:8000/camera/switch",
    json={"camera_id": "camera2"}
)
print(response.json())
```

---

## 📋 API Endpoints

### GET /camera/list
Vráti zoznam všetkých nakonfigurovaných kamier.

**Response:**
```json
{
  "cameras": [
    {
      "id": "camera1",
      "name": "YouTube Stream - Tokyo",
      "url": "https://...",
      "is_active": true
    },
    {
      "id": "camera2",
      "name": "Local Webcam",
      "url": "http://192.168.1.15:5000/video",
      "is_active": false
    }
  ],
  "total": 2
}
```

### POST /camera/switch
Prepne na inú kameru.

**Request:**
```json
{
  "camera_id": "camera2"
}
```

**Response:**
```json
{
  "message": "Successfully switched to camera: Local Webcam",
  "camera_id": "camera2",
  "camera_name": "Local Webcam",
  "url": "http://192.168.1.15:5000/video",
  "processing_resumed": true
}
```

---

## 🎯 Typické použitie

### Scenár 1: Sledovanie 3 rôznych YouTube streamov

```yaml
sources:
  tokyo:
    name: "Tokyo Street View"
    url: "https://youtube_direct_url_tokyo"
  nyc:
    name: "NYC Times Square"
    url: "https://youtube_direct_url_nyc"
  london:
    name: "London Traffic"
    url: "https://youtube_direct_url_london"
```

Prepínaj medzi nimi:
```powershell
# Tokyo
curl -X POST http://localhost:8000/camera/switch -d '{"camera_id":"tokyo"}' -H "Content-Type: application/json"

# NYC
curl -X POST http://localhost:8000/camera/switch -d '{"camera_id":"nyc"}' -H "Content-Type: application/json"
```

### Scenár 2: Mix YouTube + lokálna kamera

```yaml
sources:
  youtube:
    name: "YouTube Stream"
    url: "https://youtube_url..."
  local:
    name: "My Webcam"
    url: "http://192.168.1.15:5000/video"
  rtsp:
    name: "IP Camera"
    url: "rtsp://192.168.1.100:554/stream"
```

---

## 💡 Tipy a triky

### Automatické prepínanie (scripting)

Vytvor PowerShell script ktorý prepína kamery každých 5 minút:

```powershell
# switch_cameras_loop.ps1
$cameras = @("camera1", "camera2", "camera3")
$interval = 300  # 5 minutes

while ($true) {
    foreach ($cam in $cameras) {
        Write-Host "Switching to $cam..."
        
        $body = @{camera_id = $cam} | ConvertTo-Json
        Invoke-RestMethod -Method Post `
            -Uri http://localhost:8000/camera/switch `
            -Body $body `
            -ContentType "application/json"
        
        Start-Sleep -Seconds $interval
    }
}
```

Spusti:
```powershell
.\switch_cameras_loop.ps1
```

### Refresh YouTube URLs

YouTube URL expirujú ~6 hodín. Automatizuj refresh:

```powershell
# refresh_youtube_urls.ps1
$youtubeLinks = @{
    camera1 = "https://www.youtube.com/watch?v=VIDEO1"
    camera3 = "https://www.youtube.com/watch?v=VIDEO2"
}

foreach ($cam in $youtubeLinks.Keys) {
    $url = $youtubeLinks[$cam]
    Write-Host "Refreshing $cam from $url"
    
    # Get new direct URL
    $output = python get_youtube_stream.py $url
    # Parse output and update config.yaml
    # (potrebuješ doplniť parsing logiku)
}
```

### Monitor aktívnej kamery

```powershell
# Získaj info o aktívnej kamere
(Invoke-RestMethod http://localhost:8000/status).camera
```

---

## 🔧 Riešenie problémov

### Prepnutie zlyhá

- Over že `camera_id` existuje v `config.yaml` → `sources`
- Skontroluj logy: `docker logs -f smart-lighting-detection`
- URL musí byť platné a dostupné

### Video processing sa nezreštartoval

- Manuálne reštartuj: `POST /start`
- Alebo: `docker-compose restart`

### YouTube URL expiroval

- Zopakuj `python get_youtube_stream.py` pre nové URL
- Uprav `config.yaml`
- Prepni na inú kameru a späť

---

## 📞 Pre kolegov

Ak chceš prepnúť kameru na serveri ktorý niekto iný spustil:

```powershell
# Pripoj sa na vzdialený server (nahraď IP)
$serverUrl = "http://192.168.1.50:8000"

# Zobraz zoznam
Invoke-RestMethod "$serverUrl/camera/list"

# Prepni
$body = @{camera_id = "camera2"} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "$serverUrl/camera/switch" -Body $body -ContentType "application/json"
```

Alebo otvor v prehliadači:
- http://192.168.1.50:8000/docs
- Použij Swagger UI na prepnutie
