# Quick Start Guide - Pre kolegov / For Team Members

## 🚀 Rýchly štart / Quick Start

### Krok 1: Nainštaluj Docker Desktop
- Windows: https://www.docker.com/products/docker-desktop/
- Spusti Docker Desktop a počkaj kým sa naštartuje

### Krok 2: Stiahni projekt
```powershell
git clone <repository-url>
cd "tímový projekt"
```

### Krok 3: Nastav kameru v `config.yaml`

**Pre IP kameru (odporúčané):**
```yaml
camera:
  source: "http://192.168.1.100:8080/video"  # Zmeň na tvoju IP
```

**Pre video súbor (testovanie):**
```yaml
camera:
  source: "/app/videos/sample.mp4"
```

**POZOR:** USB webkamera nefunguje v Dockeri na Windows! Použi IP kameru z mobilu (app "IP Webcam").

### Krok 4: Spusti aplikáciu
```powershell
docker-compose up
```

### Krok 5: Otvor v prehliadači
- API: http://localhost:8000
- Dokumentácia: http://localhost:8000/docs

---

## 📱 Ako použiť mobil ako IP kameru

### Android:
1. Nainštaluj "IP Webcam" z Google Play
2. Spusti aplikáciu
3. Skroluj dole a klikni "Start server"
4. Zobrazí sa IP adresa, napr. `http://192.168.1.100:8080`
5. V `config.yaml` nastav:
   ```yaml
   camera:
     source: "http://192.168.1.100:8080/video"
   ```

### iPhone:
1. Nainštaluj "iVCam" alebo "EpocCam"
2. Postupuj podľa inštrukcií v aplikácii

---

## 🔧 Riešenie problémov / Troubleshooting

### Docker sa nespustí
- Uisti sa že Docker Desktop je spustený
- Reštartuj Docker Desktop
- Skontroluj či máš dosť miesta na disku (min. 15GB)

### Aplikácia nenájde kameru
- Skontroluj IP adresu v `config.yaml`
- Uisti sa že mobil aj počítač sú na rovnakej WiFi sieti
- Testuj kameru v prehliadači: `http://IP:8080` (Android)

### Port 8000 je už obsadený
```powershell
# Zastav existujúci kontajner
docker-compose down

# Alebo zmeň port v docker-compose.yml
ports:
  - "8001:8000"  # Použije port 8001 namiesto 8000
```

---

## 📝 Príkazy / Commands

```powershell
# Spusti aplikáciu
docker-compose up

# Spusti na pozadí (detached mode)
docker-compose up -d

# Zobraz logy
docker-compose logs -f

# Zastav aplikáciu
docker-compose down

# Reštartuj po zmene config.yaml
docker-compose restart

# Stiahni najnovšiu verziu
docker-compose pull
docker-compose up
```

---

## 🎯 Prvé spustenie - Checklist

- [ ] Docker Desktop nainštalovaný a spustený
- [ ] Projekt stiahnutý
- [ ] `config.yaml` upravený (IP kamera alebo video súbor)
- [ ] `docker-compose up` spustený
- [ ] http://localhost:8000 funguje v prehliadači
- [ ] Kamera stream sa zobrazuje (otvor `/stream` endpoint)

---

## 💡 Tipy

1. **Prvé spustenie trvá dlhšie** - Docker sťahuje image (~13GB)
2. **Používaj IP kameru** - USB webkamera nefunguje v Dockeri
3. **Konfigurácia bez restartu** - zmeny v `config.yaml` sa načítajú po `docker-compose restart`
4. **Dokumentácia API** - otvor http://localhost:8000/docs pre interaktívnu dokumentáciu

---

## 📞 Kontakt

Ak máš problémy, kontaktuj maintainera projektu alebo otvor issue v repository.
