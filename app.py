"""
app.py — Dashboard Flask
Servidor local con board de ofertas, filtros y vista detalle.

Ejecutar:
    pip install flask
    python app.py
    → http://localhost:5000
"""

from flask import Flask, render_template, request, jsonify, g
import sqlite3
import os
import json

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ofertas.db")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(e=None):
    db = g.pop("db", None)
    if db:
        db.close()


def query(sql, params=()):
    return get_db().execute(sql, params).fetchall()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/ofertas")
def api_ofertas():
    """Endpoint principal con filtros."""
    # Filtros desde query params
    fuente     = request.args.get("fuente", "")
    region     = request.args.get("region", "")
    pais       = request.args.get("pais", "")
    tipo_viaje = request.args.get("tipo_viaje", "")
    tipo_clima = request.args.get("tipo_clima", "")
    pension    = request.args.get("pension", "")
    estrellas  = request.args.get("estrellas", "")
    precio_max = request.args.get("precio_max", "")
    precio_min = request.args.get("precio_min", "")
    activa     = request.args.get("activa", "1")
    search     = request.args.get("q", "")
    orden      = request.args.get("orden", "primera_vez")
    page       = int(request.args.get("page", 1))
    per_page   = int(request.args.get("per_page", 50))
    bajada     = request.args.get("bajada", "")  # solo ofertas con precio bajado

    where  = ["1=1"]
    params = []

    if fuente:
        where.append("fuente = ?")
        params.append(fuente)
    if region:
        where.append("region = ?")
        params.append(region)
    if pais:
        where.append("pais = ?")
        params.append(pais)
    if tipo_viaje:
        where.append("tipo_viaje = ?")
        params.append(tipo_viaje)
    if tipo_clima:
        where.append("tipo_clima = ?")
        params.append(tipo_clima)
    if pension:
        where.append("pension = ?")
        params.append(pension)
    if estrellas:
        where.append("estrellas = ?")
        params.append(estrellas)
    if activa != "all":
        where.append("activa = ?")
        params.append(int(activa))
    if precio_min:
        where.append("precio >= ?")
        params.append(float(precio_min))
    if precio_max:
        where.append("precio <= ?")
        params.append(float(precio_max))
    if bajada == "1":
        where.append("precio_anterior IS NOT NULL AND precio < precio_anterior")
    if search:
        where.append("(titulo LIKE ? OR destino LIKE ? OR region LIKE ?)")
        s = f"%{search}%"
        params.extend([s, s, s])

    order_map = {
        "primera_vez": "primera_vez DESC",
        "precio_asc":  "precio ASC",
        "precio_desc": "precio DESC",
        "bajada":      "(precio_anterior - precio) DESC",
        "ultima_vez":  "ultima_vez DESC",
    }
    order_clause = order_map.get(orden, "primera_vez DESC")

    where_str = " AND ".join(where)
    offset    = (page - 1) * per_page

    # Total
    total_row = get_db().execute(
        f"SELECT COUNT(*) FROM ofertas WHERE {where_str}", params
    ).fetchone()[0]

    rows = get_db().execute(
        f"""
        SELECT id, fuente, titulo, destino, region, pais, tipo_clima,
               tipo_viaje, estrellas, pension, extras, precio, precio_anterior,
               precio_min, precio_por, primera_vez, ultima_vez, activa,
               imagen_url, duracion_noches, gemini_tags, gemini_resumen, url
        FROM ofertas
        WHERE {where_str}
        ORDER BY {order_clause}
        LIMIT ? OFFSET ?
        """,
        params + [per_page, offset]
    ).fetchall()

    def row_to_dict(r):
        d = dict(r)
        # Parsear gemini_tags si es string JSON
        if d.get("gemini_tags"):
            try:
                d["gemini_tags"] = json.loads(d["gemini_tags"])
            except Exception:
                d["gemini_tags"] = []
        # Calcular % de bajada
        if d.get("precio") and d.get("precio_anterior"):
            d["bajada_pct"] = round(
                (d["precio_anterior"] - d["precio"]) / d["precio_anterior"] * 100
            )
        else:
            d["bajada_pct"] = None
        return d

    return jsonify({
        "total":    total_row,
        "page":     page,
        "per_page": per_page,
        "pages":    (total_row + per_page - 1) // per_page,
        "items":    [row_to_dict(r) for r in rows],
    })


@app.route("/api/stats")
def api_stats():
    """Estadísticas para el dashboard."""
    db = get_db()

    total_activas = db.execute("SELECT COUNT(*) FROM ofertas WHERE activa=1").fetchone()[0]
    total_todas   = db.execute("SELECT COUNT(*) FROM ofertas").fetchone()[0]
    bajadas_precio = db.execute(
        "SELECT COUNT(*) FROM ofertas WHERE activa=1 AND precio < precio_anterior"
    ).fetchone()[0]
    precio_medio  = db.execute(
        "SELECT ROUND(AVG(precio),2) FROM ofertas WHERE activa=1 AND precio IS NOT NULL"
    ).fetchone()[0]

    por_fuente = db.execute(
        "SELECT fuente, COUNT(*) as n FROM ofertas WHERE activa=1 GROUP BY fuente"
    ).fetchall()

    por_region = db.execute(
        """SELECT region, COUNT(*) as n FROM ofertas
           WHERE activa=1 AND region != ''
           GROUP BY region ORDER BY n DESC LIMIT 15"""
    ).fetchall()

    por_tipo = db.execute(
        "SELECT tipo_viaje, COUNT(*) as n FROM ofertas WHERE activa=1 GROUP BY tipo_viaje ORDER BY n DESC"
    ).fetchall()

    por_clima = db.execute(
        "SELECT tipo_clima, COUNT(*) as n FROM ofertas WHERE activa=1 AND tipo_clima != '' GROUP BY tipo_clima ORDER BY n DESC"
    ).fetchall()

    return jsonify({
        "total_activas":   total_activas,
        "total_historico": total_todas,
        "bajadas_precio":  bajadas_precio,
        "precio_medio":    precio_medio,
        "por_fuente":      [dict(r) for r in por_fuente],
        "por_region":      [dict(r) for r in por_region],
        "por_tipo":        [dict(r) for r in por_tipo],
        "por_clima":       [dict(r) for r in por_clima],
    })


@app.route("/api/filtros")
def api_filtros():
    """Valores únicos para poblar los dropdowns de filtros."""
    db = get_db()
    def vals(col):
        rows = db.execute(
            f"SELECT DISTINCT {col} FROM ofertas WHERE activa=1 AND {col} != '' ORDER BY {col}"
        ).fetchall()
        return [r[0] for r in rows]

    return jsonify({
        "fuentes":      vals("fuente"),
        "regiones":     vals("region"),
        "paises":       vals("pais"),
        "tipos_viaje":  vals("tipo_viaje"),
        "tipos_clima":  vals("tipo_clima"),
        "pensiones":    vals("pension"),
        "estrellas":    vals("estrellas"),
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
