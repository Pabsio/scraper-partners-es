# 🏖️ Oferta Scraper

Scraper multi-fuente de ofertas de viaje con dashboard local.  
**Fuentes:** Traventia · BuscoUnChollo · Weekendesk

---

## Arquitectura

```
GitHub Actions (cron 3x/día)
        ↓
  main.py  →  scrapers/{fuente}.py   (Playwright + requests)
        ↓
   parsers.py  →  database.py (SQLite)
        ↓
   gemini_enricher.py  (1 llamada API / ejecución, solo novedades)
        ↓
   app.py (Flask)  →  http://localhost:5000
```

---

## Instalación (primera vez)

```bash
# 1. Clonar / copiar el proyecto
cd ofertascraper

# 2. Instalar dependencias Python
pip install -r requirements.txt

# 3. Instalar Chromium para Playwright
playwright install chromium

# 4. (Opcional) Configurar Gemini API key
export GEMINI_API_KEY="tu_clave_aqui"
```

---

## Uso

### Ejecutar scraper manualmente
```bash
# Todas las fuentes
python main.py

# Solo una fuente
python main.py --source traventia
python main.py --source buscounchollo
python main.py --source weekendesk

# Sin enriquecimiento Gemini
python main.py --no-gemini
```

### Lanzar el dashboard
```bash
python app.py
# → http://localhost:5000
```

---

## GitHub Actions (ejecución automática en la nube)

### Setup
1. Sube el proyecto a un repositorio GitHub (puede ser privado)
2. Ve a **Settings → Secrets and variables → Actions**
3. Añade el secret `GEMINI_API_KEY` con tu clave de Gemini
4. El workflow `.github/workflows/scraper.yml` ya está configurado para correr:
   - **Lunes a viernes** a las 9:00, 13:00 y 18:00 (hora España)
   - También puedes lanzarlo manualmente desde la pestaña *Actions*

### Ver logs
GitHub Actions → pestaña *Actions* → click en el run más reciente

### Descargar la base de datos
La DB `ofertas.db` se commitea automáticamente al repo tras cada scrape.  
Para tenerla en local: `git pull` y ejecuta `python app.py`.

> **Nota:** el archivo `ofertas.db` crece con el tiempo.  
> Para excluirlo del repo y usar otro método de persistencia, edita `.github/workflows/scraper.yml`.

---

## Añadir una nueva web

1. Crea `scrapers/nueva_web.py` con una función `scrape() -> list[dict]`  
   (copia `scrapers/buscounchollo.py` como plantilla)
2. Importa y añade al dict `SCRAPERS` en `main.py`
3. ¡Listo! El sistema lo deduplica, archiva caducadas y enrichece con Gemini automáticamente.

---

## Schema SQLite

```sql
ofertas (
  id, url, fuente,
  titulo, destino, region, pais, tipo_clima,
  tipo_viaje, estrellas, pension, extras,
  precio, precio_anterior, precio_min, moneda, precio_por,
  primera_vez, ultima_vez, activa,
  gemini_enriquecida, gemini_tags, gemini_resumen,
  imagen_url, duracion_noches, adultos_min
)
```

---

## Gemini — uso y coste

- Modelo: `gemini-2.0-flash` (~0.075$ / 1M tokens input)
- **1 sola llamada por ejecución**, batch de hasta 50 ofertas nuevas
- Solo enriquece ofertas con `gemini_enriquecida = 0`
- Completa: región, país, tipo_clima, tags, resumen de 1 frase
- **Coste estimado real: < 0.001$ por ejecución** (< 0.03$ al mes)
- Si no quieres usar Gemini: `python main.py --no-gemini`

---

## Dashboard — filtros disponibles

| Filtro | Descripción |
|--------|-------------|
| Búsqueda texto | Titulo, destino, región |
| Fuente | Traventia / BuscoUnChollo / Weekendesk |
| País | España, Francia, Italia… |
| Región/CCAA | Andalucía, Baleares, Canarias… |
| Tipo viaje | Hotel, Vuelo+Hotel, Ferry+Hotel, Esquí… |
| Entorno | Playa, Montaña, Ciudad, Rural, Parque |
| Régimen | Todo Incluido, Desayuno, Media Pensión… |
| Estrellas | 3★ 4★ 5★ |
| Precio min/max | Rango numérico |
| Solo precio bajado | Filtra bajadas de precio |
| Estado | Activas / Archivadas / Todas |
| Ordenación | Recientes, Precio ↑↓, Mayor bajada |
