# 🔌 OpenLab Light Integration

Tento projekt je integrovaný s **reálnymi svetlami v OpenLab** pomocá MQTT protokolu.

## 🎯 Ako to funguje

```
Kamera deteguje osoby → YOLOv8 → Počet osôb → Intenzita svetla → MQTT → OpenLab svetlá
```

### Proces:
1. **Kamera** zachytáva video stream z OpenLab
2. **YOLOv8** deteguje osoby v real-time
3. **Počet osôb** sa premietne na intenzitu svetla:
   - 0 osôb = svetlá vypnuté (0%)
   - 1 osoba = 20-30% intenzita
   - 5+ osôb = 100% intenzita
4. **MQTT správa** sa pošle na `openlab/lights`
5. **97 svetiel v OpenLab** sa rozsvietia podľa intenzity

## 📋 Požiadavky

```bash
pip install paho-mqtt
```

Alebo:
```bash
pip install -r requirements.txt
```

## ⚙️ Konfigurácia

Súbor `config.yaml` je už nakonfigurovaný:

```yaml
lighting:
  mode: openlab  # Používa OpenLab svetlá
  
  mqtt:
    broker: openlab.kpi.fei.tuke.sk
    port: 1883
    topic: openlab/lights
  
  min_brightness: 20      # Minimálna intenzita
  max_brightness: 100     # Maximálna intenzita
  fade_duration: 1000     # Fade trvanie v ms (min 250ms)
```

## 🚀 Spustenie

### 1. Test pripojenia k OpenLab svetlám

```bash
python test_openlab_lights.py
```

Tento test:
- Pripojí sa k MQTT brokeru
- Zapne svetlá na 50%
- Zvýši na 100%
- Stlmí na 20%
- Simuluje rôzny počet osôb
- Vypne svetlá

### 2. Spustenie hlavnej aplikácie

```bash
python main.py
```

Potom otvorte dashboard: **http://localhost:8000**

### 3. Použitie s Dockerom

```bash
docker-compose up
```

## 📊 Dashboard

Na **http://localhost:8000** uvidíte:

- 📹 **Video stream** z kamery v reálnom čase
- 👥 **Počet detegovaných osôb**
- 💡 **Graf intenzity svetla** v čase
- 📈 **Štatistiky** (FPS, detekcie, jas)
- 🔌 **MQTT status** - či ste pripojení k OpenLab

## 🎯 OpenLab API

### MQTT Message Format

Aplikácia posiela MQTT správy na `openlab/lights` v JSON formáte:

```json
{
  "all": "000000ff",
  "duration": 1000
}
```

Kde:
- `all`: RGBW hex hodnota
  - `RRGGBBWW` = Red, Green, Blue, White
  - `000000ff` = plná biela (RGB off, W=255)
  - `0000007f` = 50% biela
  - `00000000` = svetlá vypnuté
- `duration`: Fade trvanie v ms (min 250ms pre epilepsy safety)

### Príklady intenzít

| Počet osôb | Brightness | RGBW Hex   | Popis          |
|-----------|-----------|-----------|----------------|
| 0         | 0%        | 00000000  | Vypnuté        |
| 1         | 20%       | 00000033  | Slabé svetlo   |
| 2         | 40%       | 00000066  | Stredné svetlo |
| 3         | 60%       | 00000099  | Silné svetlo   |
| 5+        | 100%      | 000000ff  | Plné svetlo    |

## 🔒 Bezpečnosť

- ⚡ **Minimálna duration 250ms** (epilepsy-safe)
- ⏱️ **Command cooldown 0.5s** medzi príkazmi
- 🔄 **Automatické reconnect** pri výpadku MQTT
- 📊 **Debounce detekcie** aby sa svetlá nemenili príliš často

## 🧪 Testovanie

### Test MQTT pripojenia

```python
from openlab_light_controller import OpenLabLightController
import yaml

# Načítaj konfiguráciu
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Vytvor kontrolér
controller = OpenLabLightController(config['lighting'])

# Test
controller.turn_on(50)  # 50% intenzita
time.sleep(2)
controller.turn_off()
```

### Test cez REST API

```bash
# Zapni systém
curl -X POST http://localhost:8000/start

# Skontroluj status
curl http://localhost:8000/status

# Manuálne ovládanie svetiel
curl -X POST http://localhost:8000/lights/manual \
  -H "Content-Type: application/json" \
  -d '{"brightness": 80}'
```

## 📝 Log Messages

Pri spustení uvidíte logy:

```
🔌 Creating OpenLab MQTT light controller for real OpenLab lights
OpenLab Light Controller initialized (broker: openlab.kpi.fei.tuke.sk:1883)
Connecting to MQTT broker at openlab.kpi.fei.tuke.sk:1883
✅ Connected to MQTT broker successfully
💡 Sent light command: 00000080 (duration: 1000ms)
🔆 Lights turned ON (brightness: 50%)
```

## 🐛 Riešenie problémov

### Svetlá sa nerozsvietia

1. **Skontrolujte MQTT pripojenie:**
   ```bash
   python test_openlab_lights.py
   ```

2. **Skontrolujte config.yaml:**
   ```yaml
   lighting:
     mode: openlab  # Musí byť openlab, nie simulated
   ```

3. **Skontrolujte logy:**
   ```
   tail -f logs/system.log
   ```

### Chyba "Failed to connect to MQTT broker"

- Skontrolujte internetové pripojenie
- Overte že broker je dostupný: `openlab.kpi.fei.tuke.sk:1883`
- Skúste ping: `ping openlab.kpi.fei.tuke.sk`

### Svetlá sa menia príliš často

Upravte `debounce_time` v `config.yaml`:

```yaml
lighting:
  debounce_time: 2.0  # Zvýšte na 2 sekundy
```

## 🔧 Pokročilé nastavenia

### Vlastná logika intenzity

V `openlab_light_controller.py`, upravte `adjust_brightness()`:

```python
def adjust_brightness(self, person_count: int, max_persons: int = 10):
    if person_count == 0:
        self.turn_off()
    elif person_count == 1:
        self.turn_on(30)  # 1 osoba = 30%
    elif person_count == 2:
        self.turn_on(60)  # 2 osoby = 60%
    else:
        self.turn_on(100)  # 3+ osôb = 100%
```

### Použitie farebných svetiel

Upravte `_brightness_to_rgbw()` pre RGB farby:

```python
def _brightness_to_rgbw(self, brightness: int) -> str:
    # Červená farba namiesto bielej
    red_value = int((brightness / 100) * 255)
    return f"{red_value:02x}000000"
```

## 📚 Dokumentácia OpenLab API

Viac informácií o OpenLab API:
- **Bridge - Lights**: https://openlab.kpi.fei.tuke.sk/docs/bridge/lights
- **MQTT Protocol**: Topic `openlab/lights`
- **REST API**: `/rest/light/*` endpoints

## 🎉 Hotovo!

Teraz keď niekto prejde pred kamerou v OpenLab, **skutočné svetlá sa automaticky rozsvieti**! ✨

---

**Autor:** Smart Lighting Control System  
**Dátum:** December 2025  
**Verzia:** 1.0
