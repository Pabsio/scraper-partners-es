"""
database.py — SQLite schema y helpers
Tabla única: ofertas
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ofertas.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS ofertas (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Identificación
    url             TEXT UNIQUE NOT NULL,
    fuente          TEXT NOT NULL,          -- 'traventia' | 'buscounchollo' | 'weekendesk'

    -- Contenido principal
    titulo          TEXT,
    destino         TEXT,
    region          TEXT,                   -- Comunidad autónoma o país
    pais            TEXT,                   -- España / Francia / Italia / etc.
    tipo_clima      TEXT,                   -- Playa / Montaña / Ciudad / Rural / Internacional
    tipo_viaje      TEXT,                   -- Hotel / Vuelo+Hotel / Ferry+Hotel / Parque / Esquí
    estrellas       TEXT,                   -- '3★' '4★' etc.
    pension         TEXT,                   -- Todo Incluido / Media Pensión / Desayuno / etc.
    extras          TEXT,                   -- SPA, Toboganes, Romántico, etc. (CSV)

    -- Precio
    precio          REAL,
    precio_anterior REAL,                   -- último precio conocido (para detectar bajadas)
    precio_min      REAL,                   -- precio histórico más bajo
    moneda          TEXT DEFAULT 'EUR',
    precio_por      TEXT DEFAULT 'persona', -- 'persona' | 'noche' | 'habitacion'

    -- Fechas
    primera_vez     TEXT,                   -- ISO datetime de cuando se vio por primera vez
    ultima_vez      TEXT,                   -- ISO datetime del último scrape donde apareció
    activa          INTEGER DEFAULT 1,      -- 1 = en venta ahora, 0 = archivada

    -- Enriquecimiento Gemini
    gemini_enriquecida  INTEGER DEFAULT 0,  -- 0 = pendiente, 1 = ya procesada
    gemini_tags         TEXT,               -- tags extra que puso Gemini (JSON array string)
    gemini_resumen      TEXT,               -- descripción corta generada por Gemini

    -- Meta
    imagen_url      TEXT,
    duracion_noches INTEGER,
    adultos_min     INTEGER DEFAULT 2
);

CREATE INDEX IF NOT EXISTS idx_fuente   ON ofertas(fuente);
CREATE INDEX IF NOT EXISTS idx_region   ON ofertas(region);
CREATE INDEX IF NOT EXISTS idx_activa   ON ofertas(activa);
CREATE INDEX IF NOT EXISTS idx_precio   ON ofertas(precio);
CREATE INDEX IF NOT EXISTS idx_tipo     ON ofertas(tipo_viaje);
"""


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
    print(f"✅ DB lista: {DB_PATH}")


def upsert_offer(offer: dict) -> str:
    """
    Inserta o actualiza una oferta.
    Devuelve: 'new' | 'price_down' | 'price_up' | 'unchanged'
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    url = offer["url"]

    with get_conn() as conn:
        existing = conn.execute(
            "SELECT precio, precio_min, primera_vez FROM ofertas WHERE url = ?", (url,)
        ).fetchone()

        if existing is None:
            conn.execute("""
                INSERT INTO ofertas (
                    url, fuente, titulo, destino, region, pais, tipo_clima,
                    tipo_viaje, estrellas, pension, extras, precio, precio_anterior,
                    precio_min, moneda, precio_por, primera_vez, ultima_vez,
                    activa, imagen_url, duracion_noches, adultos_min
                ) VALUES (
                    :url, :fuente, :titulo, :destino, :region, :pais, :tipo_clima,
                    :tipo_viaje, :estrellas, :pension, :extras, :precio, :precio,
                    :precio, :moneda, :precio_por, :primera_vez, :ultima_vez,
                    1, :imagen_url, :duracion_noches, :adultos_min
                )
            """, {**offer, "primera_vez": now, "ultima_vez": now})
            return "new"

        # Ya existe — actualizar
        old_precio  = existing["precio"]
        new_precio  = offer.get("precio")
        old_min     = existing["precio_min"] or old_precio

        updates = {
            "ultima_vez": now,
            "activa": 1,
            "titulo":   offer.get("titulo"),
            "url":      url,
        }
        result = "unchanged"

        if new_precio and old_precio and abs(new_precio - old_precio) > 0.01:
            updates["precio_anterior"] = old_precio
            updates["precio"]          = new_precio
            updates["precio_min"]      = min(old_min or new_precio, new_precio)
            result = "price_down" if new_precio < old_precio else "price_up"
        elif new_precio:
            updates["precio_min"] = min(old_min or new_precio, new_precio)

        set_clause = ", ".join(f"{k} = :{k}" for k in updates if k != "url")
        conn.execute(f"UPDATE ofertas SET {set_clause} WHERE url = :url", updates)
        return result


def archive_missing(active_urls: set, fuente: str):
    """Marca como inactivas las ofertas de una fuente que ya no aparecen."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT url FROM ofertas WHERE fuente = ? AND activa = 1", (fuente,)
        ).fetchall()
        archived = 0
        for row in rows:
            if row["url"] not in active_urls:
                conn.execute(
                    "UPDATE ofertas SET activa = 0 WHERE url = ?", (row["url"],)
                )
                archived += 1
    return archived


def get_pending_gemini(limit=50):
    """Ofertas nuevas que aún no han sido enriquecidas con Gemini."""
    with get_conn() as conn:
        return conn.execute("""
            SELECT id, titulo, destino, region, tipo_viaje, extras
            FROM ofertas
            WHERE gemini_enriquecida = 0 AND activa = 1
            LIMIT ?
        """, (limit,)).fetchall()


def save_gemini_results(results: list[dict]):
    """Guarda los resultados de Gemini. results = [{id, region, pais, tipo_clima, tags, resumen}]"""
    with get_conn() as conn:
        for r in results:
            conn.execute("""
                UPDATE ofertas SET
                    region          = COALESCE(NULLIF(:region, ''), region),
                    pais            = COALESCE(NULLIF(:pais, ''), pais),
                    tipo_clima      = COALESCE(NULLIF(:tipo_clima, ''), tipo_clima),
                    gemini_tags     = :tags,
                    gemini_resumen  = :resumen,
                    gemini_enriquecida = 1
                WHERE id = :id
            """, r)
