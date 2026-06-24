"""
parsers.py — Utilidades compartidas de parseo
Todas las funciones son puras (sin efectos secundarios) y reutilizables por cualquier scraper.
"""

import re


# ── Limpieza ──────────────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    """Elimina emojis y espacios extra."""
    emoji_pattern = re.compile(
        "[\U00010000-\U0010ffff\U0001F600-\U0001F64F\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\u2600-\u26FF\u2700-\u27BF"
        "\u2B50\u2B55\u2B1B\u25AA\u25AB\u25B6\u25C0\u23E9-\u23F3\u23F8-\u23FA"
        "]+", flags=re.UNICODE)
    return emoji_pattern.sub("", text).strip()


def parse_price(text: str) -> float | None:
    """Extrae precio numérico de un string con € y puntos/comas."""
    if not text:
        return None
    clean = text.replace(".", "").replace(",", ".").replace(" ", "")
    match = re.search(r"(\d+(?:\.\d+)?)", clean)
    return float(match.group(1)) if match else None


# ── Región / País ─────────────────────────────────────────────────────────────

# Mapa ampliado: palabra clave → (región, país, tipo_clima)
DESTINATION_MAP = {
    # Baleares
    "mallorca":       ("Baleares",           "España",    "Playa"),
    "menorca":        ("Baleares",           "España",    "Playa"),
    "ibiza":          ("Baleares",           "España",    "Playa"),
    "formentera":     ("Baleares",           "España",    "Playa"),
    "el arenal":      ("Baleares",           "España",    "Playa"),
    "punta prima":    ("Baleares",           "España",    "Playa"),
    "palma":          ("Baleares",           "España",    "Ciudad"),
    # Canarias
    "tenerife":       ("Canarias",           "España",    "Playa"),
    "gran canaria":   ("Canarias",           "España",    "Playa"),
    "lanzarote":      ("Canarias",           "España",    "Playa"),
    "fuerteventura":  ("Canarias",           "España",    "Playa"),
    "la palma":       ("Canarias",           "España",    "Naturaleza"),
    "la gomera":      ("Canarias",           "España",    "Naturaleza"),
    "el hierro":      ("Canarias",           "España",    "Naturaleza"),
    # Andalucía
    "sevilla":        ("Andalucía",          "España",    "Ciudad"),
    "granada":        ("Andalucía",          "España",    "Ciudad"),
    "málaga":         ("Andalucía",          "España",    "Ciudad"),
    "malaga":         ("Andalucía",          "España",    "Ciudad"),
    "cádiz":          ("Andalucía",          "España",    "Playa"),
    "cadiz":          ("Andalucía",          "España",    "Playa"),
    "chipiona":       ("Andalucía",          "España",    "Playa"),
    "marbella":       ("Andalucía",          "España",    "Playa"),
    "costa ballena":  ("Andalucía",          "España",    "Playa"),
    "almería":        ("Andalucía",          "España",    "Playa"),
    "almeria":        ("Andalucía",          "España",    "Playa"),
    "huelva":         ("Andalucía",          "España",    "Playa"),
    "jaén":           ("Andalucía",          "España",    "Rural"),
    "córdoba":        ("Andalucía",          "España",    "Ciudad"),
    "cordoba":        ("Andalucía",          "España",    "Ciudad"),
    "costa del sol":  ("Andalucía",          "España",    "Playa"),
    # Cataluña
    "barcelona":      ("Cataluña",           "España",    "Ciudad"),
    "salou":          ("Cataluña",           "España",    "Playa"),
    "sitges":         ("Cataluña",           "España",    "Playa"),
    "portaventura":   ("Cataluña",           "España",    "Parque"),
    "tarragona":      ("Cataluña",           "España",    "Playa"),
    "girona":         ("Cataluña",           "España",    "Ciudad"),
    "lloret de mar":  ("Cataluña",           "España",    "Playa"),
    "tossa de mar":   ("Cataluña",           "España",    "Playa"),
    "costa brava":    ("Cataluña",           "España",    "Playa"),
    "costa dorada":   ("Cataluña",           "España",    "Playa"),
    # C. Valenciana
    "valencia":       ("C. Valenciana",      "España",    "Ciudad"),
    "peñiscola":      ("C. Valenciana",      "España",    "Playa"),
    "castellón":      ("C. Valenciana",      "España",    "Playa"),
    "castellon":      ("C. Valenciana",      "España",    "Playa"),
    "benidorm":       ("C. Valenciana",      "España",    "Playa"),
    "alicante":       ("C. Valenciana",      "España",    "Playa"),
    "costa blanca":   ("C. Valenciana",      "España",    "Playa"),
    "denia":          ("C. Valenciana",      "España",    "Playa"),
    # Asturias
    "asturias":       ("Asturias",           "España",    "Rural"),
    "avilés":         ("Asturias",           "España",    "Ciudad"),
    "oviedo":         ("Asturias",           "España",    "Ciudad"),
    "villaviciosa":   ("Asturias",           "España",    "Rural"),
    "gijón":          ("Asturias",           "España",    "Playa"),
    # Cantabria
    "cantabria":      ("Cantabria",          "España",    "Rural"),
    "santander":      ("Cantabria",          "España",    "Playa"),
    "somo":           ("Cantabria",          "España",    "Playa"),
    # País Vasco
    "bilbao":         ("País Vasco",         "España",    "Ciudad"),
    "san sebastián":  ("País Vasco",         "España",    "Ciudad"),
    "donostia":       ("País Vasco",         "España",    "Ciudad"),
    "vitoria":        ("País Vasco",         "España",    "Ciudad"),
    # Galicia
    "galicia":        ("Galicia",            "España",    "Rural"),
    "santiago":       ("Galicia",            "España",    "Ciudad"),
    "vigo":           ("Galicia",            "España",    "Ciudad"),
    "a coruña":       ("Galicia",            "España",    "Ciudad"),
    "pontevedra":     ("Galicia",            "España",    "Ciudad"),
    # Aragón / Pirineos
    "andorra":        ("Andorra",            "Andorra",   "Montaña"),
    "pirineos":       ("Aragón",             "España",    "Montaña"),
    "baqueira":       ("Aragón",             "España",    "Montaña"),
    "jaca":           ("Aragón",             "España",    "Montaña"),
    "zaragoza":       ("Aragón",             "España",    "Ciudad"),
    # Madrid / Castilla
    "madrid":         ("Madrid",             "España",    "Ciudad"),
    "segovia":        ("Castilla y León",    "España",    "Ciudad"),
    "san rafael":     ("Castilla y León",    "España",    "Rural"),
    "salamanca":      ("Castilla y León",    "España",    "Ciudad"),
    "toledo":         ("Castilla-La Mancha", "España",    "Ciudad"),
    # Murcia / Extremadura
    "murcia":         ("Murcia",             "España",    "Ciudad"),
    "cartagena":      ("Murcia",             "España",    "Playa"),
    "cáceres":        ("Extremadura",        "España",    "Ciudad"),
    "badajoz":        ("Extremadura",        "España",    "Ciudad"),
    # La Rioja / Navarra
    "la rioja":       ("La Rioja",           "España",    "Rural"),
    "logroño":        ("La Rioja",           "España",    "Ciudad"),
    "pamplona":       ("Navarra",            "España",    "Ciudad"),
    "navarra":        ("Navarra",            "España",    "Rural"),
    # Internacional — Europa
    "cerdeña":        ("Cerdeña",            "Italia",    "Playa"),
    "cerdena":        ("Cerdeña",            "Italia",    "Playa"),
    "roma":           ("Lacio",              "Italia",    "Ciudad"),
    "florencia":      ("Toscana",            "Italia",    "Ciudad"),
    "venecia":        ("Véneto",             "Italia",    "Ciudad"),
    "sicilia":        ("Sicilia",            "Italia",    "Playa"),
    "amalfi":         ("Campania",           "Italia",    "Playa"),
    "disneyland":     ("Île-de-France",      "Francia",   "Parque"),
    "parís":          ("Île-de-France",      "Francia",   "Ciudad"),
    "paris":          ("Île-de-France",      "Francia",   "Ciudad"),
    "niza":           ("Provenza",           "Francia",   "Playa"),
    "provenza":       ("Provenza",           "Francia",   "Rural"),
    "oporto":         ("Norte",              "Portugal",  "Ciudad"),
    "lisboa":         ("Lisboa",             "Portugal",  "Ciudad"),
    "algarve":        ("Algarve",            "Portugal",  "Playa"),
    "amsterdam":      ("Holanda del Norte",  "Países Bajos", "Ciudad"),
    "praga":          ("Bohemia",            "Chequia",   "Ciudad"),
    "viena":          ("Viena",              "Austria",   "Ciudad"),
    "budapest":       ("Budapest",           "Hungría",   "Ciudad"),
    "varsovia":       ("Mazovia",            "Polonia",   "Ciudad"),
    "cracovia":       ("Pequeña Polonia",    "Polonia",   "Ciudad"),
    "estambul":       ("Estambul",           "Turquía",   "Ciudad"),
    "atenas":         ("Ática",              "Grecia",    "Ciudad"),
    "santorini":      ("Egeo Meridional",    "Grecia",    "Playa"),
    "mykonos":        ("Egeo Meridional",    "Grecia",    "Playa"),
    "creta":          ("Creta",              "Grecia",    "Playa"),
    "rodas":          ("Egeo Meridional",    "Grecia",    "Playa"),
    "corfu":          ("Islas Jónicas",      "Grecia",    "Playa"),
    "dubrovnik":      ("Dalmacia",           "Croacia",   "Playa"),
    "split":          ("Dalmacia",           "Croacia",   "Playa"),
    "dubái":          ("Dubái",              "Emiratos",  "Ciudad"),
    "dubai":          ("Dubái",              "Emiratos",  "Ciudad"),
    # Internacional — Caribe / América
    "cancún":         ("Quintana Roo",       "México",    "Playa"),
    "cancun":         ("Quintana Roo",       "México",    "Playa"),
    "riviera maya":   ("Quintana Roo",       "México",    "Playa"),
    "punta cana":     ("La Altagracia",      "Rep. Dominicana", "Playa"),
    "cuba":           ("Cuba",               "Cuba",      "Playa"),
    "jamaica":        ("Jamaica",            "Jamaica",   "Playa"),
    "bahamas":        ("Bahamas",            "Bahamas",   "Playa"),
    "aruba":          ("Aruba",              "Aruba",     "Playa"),
    "maldivas":       ("Maldivas",           "Maldivas",  "Playa"),
    "mauricio":       ("Mauricio",           "Mauricio",  "Playa"),
}


def enrich_destination(text: str) -> tuple[str, str, str]:
    """
    Dado un texto (título o destino), devuelve (región, país, tipo_clima).
    Usa búsqueda de subcadena case-insensitive sobre DESTINATION_MAP.
    """
    t = text.lower()
    for key, (region, pais, clima) in DESTINATION_MAP.items():
        if key in t:
            return region, pais, clima
    return "", "España", ""   # por defecto España si no se detecta


# ── Tipo de viaje ─────────────────────────────────────────────────────────────

def extract_tipo_viaje(text: str) -> str:
    t = text.lower()
    if "ferry" in t and "hotel" in t:       return "Ferry + Hotel"
    if ("vuelo" in t or "avión" in t) and "hotel" in t: return "Vuelo + Hotel"
    if "disneyland" in t or "portaventura" in t or "ferrari land" in t: return "Parque Temático"
    if "esqui" in t or "esquí" in t or "forfait" in t: return "Esquí"
    if "crucero" in t:                       return "Crucero"
    return "Hotel"


# ── Estrellas ─────────────────────────────────────────────────────────────────

def extract_estrellas(text: str) -> str:
    match = re.search(r"(\d)[★⭐\*]", text)
    return match.group(1) + "★" if match else ""


# ── Pensión ───────────────────────────────────────────────────────────────────

def extract_pension(text: str) -> str:
    t = text.lower()
    if "todo incluido" in t or "all inclusive" in t: return "Todo Incluido"
    if "media pensión" in t or "media pension" in t: return "Media Pensión"
    if "pensión completa" in t or "pension completa" in t: return "Pensión Completa"
    if "desayuno" in t:                              return "Desayuno"
    if "solo alojamiento" in t or "sólo alojamiento" in t: return "Solo Alojamiento"
    return "Sin especificar"


# ── Extras ────────────────────────────────────────────────────────────────────

EXTRAS_MAP = {
    "SPA / Termas":         ["spa", "termal", "termas", "balneario", "jacuzzi"],
    "Entradas parque":      ["acceso ilimitado", "entradas al parque", "entrada parque"],
    "Ferry con coche":      ["ferry con tu coche", "coche en el ferry"],
    "Visita guiada":        ["visita guiada", "tour incluido"],
    "Cata de vinos":        ["cata de vino", "bodega", "enoturismo"],
    "Toboganes / Acuático": ["toboganes", "acuático", "parque acuático"],
    "Paseo en barco":       ["paseo en barco", "excursión en barco"],
    "Entradas museo":       ["entradas al museo", "museo incluido"],
    "Transfer incluido":    ["transfer", "traslado incluido"],
    "Romántico":            ["romántico", "romantico", "pareja", "luna de miel"],
    "Con niños":            ["niños", "familia", "familiar", "toboganes"],
    "Mascotas":             ["mascotas", "mascota", "perros"],
    "Golf":                 ["golf"],
    "Senderismo":           ["senderismo", "trekking", "ruta"],
    "Esquí":                ["esquí", "esqui", "forfait", "pistas"],
    "Vuelo incluido":       ["vuelo incluido", "con vuelo", "avión incluido"],
}

def extract_extras(text: str) -> str:
    t = text.lower()
    found = [label for label, kws in EXTRAS_MAP.items() if any(k in t for k in kws)]
    return ", ".join(found)


# ── Duración ──────────────────────────────────────────────────────────────────

def extract_noches(text: str) -> int | None:
    match = re.search(r"(\d+)\s*noche", text.lower())
    return int(match.group(1)) if match else None
