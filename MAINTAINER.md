# Maintainer Guide - Správa Docker Image

Tento súbor je pre **maintainerov projektu** - ako aktualizovať a publikovať Docker image.

## 🔄 Ako aktualizovať Docker image

### Keď pridáš novú Python knižnicu:

1. **Nainštaluj knižnicu lokálne** (pre testovanie):
   ```powershell
   pip install nova-kniznica
   ```

2. **Aktualizuj requirements.txt**:
   ```powershell
   pip freeze > requirements.txt
   ```

3. **Otestuj že to funguje**:
   ```powershell
   python main.py
   ```

4. **Rebuild Docker image**:
   ```powershell
   # V priečinku projektu
   cd "C:\Users\richa\OneDrive\Počítač\ZIVEIT\Solution\tímový projekt"
   
   # Build s force (bez cache)
   docker-compose build --no-cache
   ```

5. **Otestuj Docker verziu**:
   ```powershell
   docker-compose up
   # Otvor http://localhost:8000 a over že funguje
   ```

6. **Tag image pre Docker Hub**:
   ```powershell
   # Latest verzia
   docker tag tmovprojekt-object-detection:latest rs735my/smart-lighting-detection:latest
   
   # Voliteľne: verzia s číslom (odporúčané)
   docker tag tmovprojekt-object-detection:latest rs735my/smart-lighting-detection:v1.1
   ```

7. **Push na Docker Hub**:
   ```powershell
   # Prihlás sa (ak nie si prihlásený)
   docker login
   
   # Push latest
   docker push rs735my/smart-lighting-detection:latest
   
   # Push aj verziu s číslom
   docker push rs735my/smart-lighting-detection:v1.1
   ```

8. **Oznám tímu**:
   - Napíš správu do tímového chatu
   - Aktualizuj CHANGELOG.md (ak máte)
   - Kolegovia si stiahnu: `docker-compose pull && docker-compose up`

---

## 📋 Checklist pre release novej verzie

- [ ] Všetky zmeny otestované lokálne (native Python)
- [ ] `requirements.txt` aktualizovaný
- [ ] `config.yaml` má rozumné default hodnoty
- [ ] Docker build úspešný bez chýb
- [ ] Docker verzia otestovaná (`docker-compose up`)
- [ ] README.md aktualizovaný (ak treba)
- [ ] Image tagged s verziou (v1.x)
- [ ] Pushed na Docker Hub
- [ ] Tím informovaný o novej verzii

---

## 🏷️ Versioning Strategy

Používaj semantic versioning:

```
v1.0 - Prvá stabilná verzia
v1.1 - Menšie vylepšenia, nové features
v1.1.1 - Bugfixy
v2.0 - Breaking changes, veľké zmeny
```

Pri každom release:
```powershell
# Tag s verziou
docker tag tmovprojekt-object-detection:latest rs735my/smart-lighting-detection:v1.2

# Push aj latest aj versioned
docker push rs735my/smart-lighting-detection:latest
docker push rs735my/smart-lighting-detection:v1.2
```

Potom kolegovia môžu použiť:
- `latest` - vždy najnovšia verzia (môže sa zmeniť)
- `v1.2` - konkrétna verzia (stabilná)

---

## 🔧 Keď zmeníš Dockerfile

Ak upravuješ `Dockerfile` (napr. system packages):

```powershell
# Build s full rebuild (môže trvať 10-20 min)
docker-compose build --no-cache

# Test
docker-compose up

# Tag & Push (ako vyššie)
```

---

## 📁 Keď zmeníš config.yaml

`config.yaml` je **mountovaný ako volume**, takže:
- ❌ **Netreba** rebuild Docker image
- ✅ **Stačí** reštartovať: `docker-compose restart`

---

## 🗑️ Cleanup starých images

Časom sa nazbiera veľa starých Docker images:

```powershell
# Zobraz všetky images
docker images

# Vymaž staré/unused images
docker image prune -a

# Vymaž konkrétny image
docker rmi rs735my/smart-lighting-detection:v1.0
```

---

## 🌐 Docker Hub Management

1. **Prihlás sa na** https://hub.docker.com
2. **Repository**: https://hub.docker.com/r/rs735my/smart-lighting-detection
3. Môžeš:
   - Vidieť počet stiahnutí
   - Spravovať tags
   - Nastaviť README pre Docker Hub
   - Vymazať staré verzie

---

## 🚨 Troubleshooting

### Build failne kvôli nedostatku miesta
```powershell
# Vyčisti Docker cache
docker system prune -a --volumes

# Skontroluj že Docker používa D: disk (nie C:)
# Settings → Resources → Disk image location
```

### Push je veľmi pomalý
- Image má 13GB, upload trvá 10-30 min
- Používaj cache - nerobí `--no-cache` ak nie je nutné
- Použi rýchlejšie internetové pripojenie

### Kolegovia majú starú verziu
```powershell
# Musia pullnúť najnovšiu
docker-compose pull
docker-compose up
```

---

## 📞 Kontakt

Tento projekt spravuje: **richardsokol**
Docker Hub: https://hub.docker.com/r/rs735my
