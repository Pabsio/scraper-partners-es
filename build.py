"""
build.py — Genera index.html estático con todos los datos embebidos en JSON.
Se ejecuta después del scraper. El HTML resultante se sube a Netlify.

Uso:
    python3 build.py
    → genera docs/index.html
"""

import sqlite3
import json
import os
from datetime import datetime

DB_PATH  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ofertas.db")
OUT_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
OUT_FILE = os.path.join(OUT_DIR, "index.html")

AIRPORT_LABELS = {
    "MAD": "Madrid", "BCN": "Barcelona", "BIO": "Bilbao",
    "SVQ": "Sevilla", "VLC": "Valencia", "AGP": "Málaga",
    "ALC": "Alicante", "OVD": "Asturias", "SCQ": "Santiago",
    "SDR": "Santander", "ZAZ": "Zaragoza", "GRX": "Granada", "PMI": "Mallorca",
}


def load_data():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Cargar todas las ofertas activas con su precio mínimo
    rows = conn.execute("""
        SELECT
            o.id, o.url, o.fuente, o.titulo, o.destino, o.region, o.pais,
            o.tipo_clima, o.tipo_viaje, o.estrellas, o.pension, o.extras,
            o.precio, o.precio_anterior, o.precio_min, o.imagen_url,
            o.duracion_noches, o.gemini_tags, o.gemini_resumen,
            o.primera_vez, o.ultima_vez
        FROM ofertas o
        WHERE o.activa = 1
        ORDER BY o.primera_vez DESC
    """).fetchall()

    ofertas = []
    for r in rows:
        d = dict(r)
        # Parsear gemini_tags
        try:
            d["gemini_tags"] = json.loads(d.get("gemini_tags") or "[]")
        except Exception:
            d["gemini_tags"] = []
        # Calcular bajada
        if d.get("precio") and d.get("precio_anterior"):
            try:
                d["bajada_pct"] = round(
                    (float(d["precio_anterior"]) - float(d["precio"])) /
                    float(d["precio_anterior"]) * 100
                )
            except Exception:
                d["bajada_pct"] = None
        else:
            d["bajada_pct"] = None
        ofertas.append(d)

    # Stats
    total    = len(ofertas)
    bajadas  = sum(1 for o in ofertas if o.get("bajada_pct") and o["bajada_pct"] > 0)
    precios  = [float(o["precio"]) for o in ofertas if o.get("precio")]
    precio_min = round(min(precios)) if precios else 0
    precio_med = round(sum(precios) / len(precios)) if precios else 0

    # Valores únicos para filtros
    fuentes    = sorted(set(o["fuente"]     for o in ofertas if o.get("fuente")))
    paises     = sorted(set(o["pais"]       for o in ofertas if o.get("pais")))
    regiones   = sorted(set(o["region"]     for o in ofertas if o.get("region")))
    tipos      = sorted(set(o["tipo_viaje"] for o in ofertas if o.get("tipo_viaje")))
    climas     = sorted(set(o["tipo_clima"] for o in ofertas if o.get("tipo_clima")))
    pensiones  = sorted(set(o["pension"]    for o in ofertas if o.get("pension")))
    estrellas  = sorted(set(o["estrellas"]  for o in ofertas if o.get("estrellas")))

    conn.close()
    return {
        "ofertas":   ofertas,
        "stats": {
            "total":      total,
            "bajadas":    bajadas,
            "precio_min": precio_min,
            "precio_med": precio_med,
            "generado":   datetime.now().strftime("%d/%m/%Y %H:%M"),
        },
        "filtros": {
            "fuentes":   fuentes,
            "paises":    paises,
            "regiones":  regiones,
            "tipos":     tipos,
            "climas":    climas,
            "pensiones": pensiones,
            "estrellas": estrellas,
        }
    }


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Ofertas de Viaje · Dashboard</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{
      --bg: #f4f6fa; --surface: #fff; --border: #e2e8f0; --text: #1a202c;
      --muted: #64748b; --primary: #2563eb; --primary-l: #dbeafe;
      --green: #16a34a; --green-l: #dcfce7; --red: #dc2626; --red-l: #fee2e2;
      --radius: 10px; --shadow: 0 1px 3px rgba(0,0,0,.08);
      --shadow-md: 0 4px 12px rgba(0,0,0,.10);
    }}
    body {{ font-family: system-ui,-apple-system,sans-serif; background: var(--bg); color: var(--text); font-size: 14px; }}
    a {{ color: var(--primary); text-decoration: none; }}
    button {{ cursor: pointer; font: inherit; border: none; }}

    .topbar {{
      background: var(--surface); border-bottom: 1px solid var(--border);
      padding: 0 24px; height: 56px; display: flex; align-items: center;
      justify-content: space-between; position: sticky; top: 0; z-index: 100;
      box-shadow: var(--shadow);
    }}
    .topbar h1 {{ font-size: 18px; font-weight: 700; }}
    .topbar-meta {{ font-size: 12px; color: var(--muted); }}

    .main {{ display: flex; height: calc(100vh - 56px); overflow: hidden; }}

    .sidebar {{
      width: 255px; min-width: 255px; background: var(--surface);
      border-right: 1px solid var(--border); overflow-y: auto;
      padding: 16px; display: flex; flex-direction: column; gap: 11px;
    }}
    .sidebar h2 {{ font-size: 11px; font-weight: 700; text-transform: uppercase;
      letter-spacing: .08em; color: var(--muted); }}
    .fg {{ display: flex; flex-direction: column; gap: 5px; }}
    .fg label {{ font-size: 12px; color: var(--muted); font-weight: 500; }}
    .fg select, .fg input {{
      width: 100%; padding: 7px 10px; border: 1px solid var(--border);
      border-radius: 6px; background: var(--bg); font: inherit; font-size: 13px; outline: none;
    }}
    .fg select:focus, .fg input:focus {{ border-color: var(--primary); }}
    .price-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }}
    .chip-group {{ display: flex; flex-wrap: wrap; gap: 5px; }}
    .chip {{
      padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 500;
      background: var(--bg); border: 1px solid var(--border); color: var(--muted); cursor: pointer;
    }}
    .chip:hover {{ border-color: var(--primary); color: var(--primary); }}
    .chip.active {{ background: var(--primary-l); border-color: var(--primary); color: var(--primary); }}
    .chip.bajada {{ background: var(--green-l); border-color: var(--green); color: var(--green); }}
    .btn-reset {{
      width: 100%; padding: 8px; background: var(--bg); border: 1px solid var(--border);
      border-radius: 6px; color: var(--muted); font-size: 13px; margin-top: auto;
    }}
    .btn-reset:hover {{ background: var(--red-l); border-color: var(--red); color: var(--red); }}

    .content {{ flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 16px; }}

    .stats-bar {{ display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; }}
    .stat-card {{
      background: var(--surface); border: 1px solid var(--border);
      border-radius: var(--radius); padding: 14px 16px; box-shadow: var(--shadow);
    }}
    .stat-card .slabel {{ font-size: 11px; color: var(--muted); font-weight: 600;
      text-transform: uppercase; letter-spacing: .06em; }}
    .stat-card .svalue {{ font-size: 28px; font-weight: 700; margin-top: 4px; }}
    .stat-card.blue .svalue {{ color: var(--primary); }}
    .stat-card.green .svalue {{ color: var(--green); }}

    .toolbar {{
      display: flex; align-items: center; gap: 10px; background: var(--surface);
      border: 1px solid var(--border); border-radius: var(--radius);
      padding: 10px 14px; box-shadow: var(--shadow);
    }}
    .toolbar .sw {{ flex: 1; position: relative; }}
    .toolbar .sw input {{
      width: 100%; padding: 8px 12px 8px 34px; border: 1px solid var(--border);
      border-radius: 6px; font: inherit; font-size: 13px; background: var(--bg); outline: none;
    }}
    .toolbar .sw input:focus {{ border-color: var(--primary); }}
    .toolbar .si {{ position: absolute; left: 10px; top: 50%; transform: translateY(-50%); color: var(--muted); }}
    .toolbar select {{
      padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px;
      font: inherit; font-size: 13px; background: var(--bg); outline: none;
    }}
    .rc {{ font-size: 13px; color: var(--muted); white-space: nowrap; }}

    .grid {{ display: grid; grid-template-columns: repeat(auto-fill,minmax(280px,1fr)); gap: 14px; }}

    .card {{
      background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius);
      overflow: hidden; box-shadow: var(--shadow); transition: box-shadow .2s, transform .2s;
      display: flex; flex-direction: column;
    }}
    .card:hover {{ box-shadow: var(--shadow-md); transform: translateY(-2px); }}
    .card-img {{ width: 100%; height: 150px; object-fit: cover; background: var(--bg);
      display: flex; align-items: center; justify-content: center; color: var(--muted); font-size: 32px; }}
    .card-img img {{ width: 100%; height: 100%; object-fit: cover; }}
    .card-body {{ padding: 12px 14px; flex: 1; display: flex; flex-direction: column; gap: 5px; }}
    .card-fuente {{
      font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .08em;
      padding: 2px 7px; border-radius: 4px; align-self: flex-start;
    }}
    .ft {{ background: #fef3c7; color: #92400e; }}
    .fb {{ background: #dcfce7; color: #166534; }}
    .fw {{ background: #dbeafe; color: #1e40af; }}
    .card-title {{ font-size: 13px; font-weight: 600; line-height: 1.35; }}
    .card-dest {{ font-size: 12px; color: var(--muted); }}
    .badges {{ display: flex; flex-wrap: wrap; gap: 4px; }}
    .badge {{
      font-size: 11px; padding: 2px 7px; border-radius: 4px;
      background: var(--bg); color: var(--muted); border: 1px solid var(--border);
    }}
    .badge.pension {{ background: #faf5ff; color: #7c3aed; border-color: #e9d5ff; }}
    .badge.tipo    {{ background: #fff7ed; color: #c2410c; border-color: #fed7aa; }}
    .badge.clima   {{ background: #f0fdf4; color: #166534; border-color: #bbf7d0; }}
    .gtag {{
      font-size: 10px; padding: 2px 6px; border-radius: 4px;
      background: #f5f3ff; color: #6d28d9; border: 1px solid #ddd6fe;
    }}
    .card-footer {{
      padding: 10px 14px 12px; display: flex; align-items: flex-end;
      justify-content: space-between; border-top: 1px solid var(--border); margin-top: auto;
    }}
    .price-main {{ font-size: 22px; font-weight: 800; }}
    .price-label {{ font-size: 11px; color: var(--muted); }}
    .price-old {{ font-size: 12px; text-decoration: line-through; color: var(--muted); }}
    .badge-down {{
      font-size: 11px; font-weight: 700; padding: 3px 8px;
      background: var(--green-l); color: var(--green); border-radius: 20px;
    }}
    .card-link {{
      font-size: 12px; font-weight: 600; padding: 6px 12px;
      background: var(--primary); color: white; border-radius: 6px;
    }}
    .card-link:hover {{ background: #1d4ed8; text-decoration: none; }}

    .pagination {{ display: flex; align-items: center; justify-content: center; gap: 6px; }}
    .pagination button {{
      padding: 6px 12px; border: 1px solid var(--border); border-radius: 6px;
      background: var(--surface); font-size: 13px; color: var(--text);
    }}
    .pagination button:hover:not(:disabled) {{ border-color: var(--primary); color: var(--primary); }}
    .pagination button.active {{ background: var(--primary); color: white; border-color: var(--primary); }}
    .pagination button:disabled {{ opacity: .4; cursor: not-allowed; }}

    .empty {{ text-align: center; padding: 60px; color: var(--muted); }}
    .empty .icon {{ font-size: 48px; margin-bottom: 12px; }}
  </style>
</head>
<body>

<div class="topbar">
  <h1>✈️ Ofertas de Viaje</h1>
  <span class="topbar-meta">Actualizado: {generado} · {total} ofertas activas</span>
</div>

<div class="main">
  <aside class="sidebar">
    <h2>Filtros</h2>

    <div class="fg">
      <label>Buscar</label>
      <input type="text" id="f-search" placeholder="Destino, hotel, extras…" oninput="applyFilters()">
    </div>

    <div class="fg">
      <label>Estado precio</label>
      <div class="chip-group">
        <span class="chip bajada" id="chip-bajada" onclick="toggleBajada()">💚 Precio bajado</span>
      </div>
    </div>

    <div class="fg">
      <label>Fuente</label>
      <select id="f-fuente" onchange="applyFilters()"><option value="">Todas</option>{fuente_opts}</select>
    </div>

    <div class="fg">
      <label>País</label>
      <select id="f-pais" onchange="applyFilters()"><option value="">Todos</option>{pais_opts}</select>
    </div>

    <div class="fg">
      <label>Región / CCAA</label>
      <select id="f-region" onchange="applyFilters()"><option value="">Todas</option>{region_opts}</select>
    </div>

    <div class="fg">
      <label>Tipo de viaje</label>
      <select id="f-tipo" onchange="applyFilters()"><option value="">Todos</option>{tipo_opts}</select>
    </div>

    <div class="fg">
      <label>Entorno</label>
      <select id="f-clima" onchange="applyFilters()"><option value="">Todos</option>{clima_opts}</select>
    </div>

    <div class="fg">
      <label>Régimen</label>
      <select id="f-pension" onchange="applyFilters()"><option value="">Todos</option>{pension_opts}</select>
    </div>

    <div class="fg">
      <label>Estrellas</label>
      <select id="f-estrellas" onchange="applyFilters()"><option value="">Todas</option>{estrellas_opts}</select>
    </div>

    <div class="fg">
      <label>Precio €/persona</label>
      <div class="price-row">
        <input type="number" id="f-pmin" placeholder="Mín" oninput="applyFilters()">
        <input type="number" id="f-pmax" placeholder="Máx" oninput="applyFilters()">
      </div>
    </div>

    <button class="btn-reset" onclick="resetFilters()">✕ Limpiar filtros</button>
  </aside>

  <main class="content">
    <div class="stats-bar">
      <div class="stat-card blue"><div class="slabel">Activas</div><div class="svalue" id="st-total">{total}</div></div>
      <div class="stat-card"><div class="slabel">Históricas</div><div class="svalue">{historico}</div></div>
      <div class="stat-card green"><div class="slabel">Precio bajado</div><div class="svalue">{bajadas}</div></div>
      <div class="stat-card"><div class="slabel">Precio medio</div><div class="svalue">{precio_med}€</div></div>
    </div>

    <div class="toolbar">
      <div class="sw">
        <span class="si">🔍</span>
        <input type="text" id="t-search" placeholder="Buscar destino, hotel, extras…" oninput="syncSearch(this)">
      </div>
      <label style="font-size:12px;color:var(--muted);white-space:nowrap">Ordenar:</label>
      <select id="f-orden" onchange="applyFilters()">
        <option value="recientes">Más recientes</option>
        <option value="precio_asc">Precio ↑</option>
        <option value="precio_desc">Precio ↓</option>
        <option value="bajada">Mayor bajada</option>
      </select>
      <span class="rc" id="rc"></span>
    </div>

    <div id="grid-container"></div>
    <div class="pagination" id="pagination"></div>
  </main>
</div>

<script>
const DATA = {data_json};

let filtered  = [];
let page      = 1;
const PER     = 48;
let bajadaOn  = false;

function syncSearch(el) {{
  document.getElementById("f-search").value = el.value;
  applyFilters();
}}

function toggleBajada() {{
  bajadaOn = !bajadaOn;
  document.getElementById("chip-bajada").classList.toggle("active", bajadaOn);
  applyFilters();
}}

function g(id) {{ return document.getElementById(id)?.value || ""; }}

function applyFilters() {{
  const search   = (g("f-search") || g("t-search")).toLowerCase();
  const fuente   = g("f-fuente");
  const pais     = g("f-pais");
  const region   = g("f-region");
  const tipo     = g("f-tipo");
  const clima    = g("f-clima");
  const pension  = g("f-pension");
  const estrellas = g("f-estrellas");
  const pmin     = parseFloat(g("f-pmin")) || 0;
  const pmax     = parseFloat(g("f-pmax")) || Infinity;
  const orden    = g("f-orden");

  filtered = DATA.ofertas.filter(o => {{
    if (fuente   && o.fuente      !== fuente)   return false;
    if (pais     && o.pais        !== pais)     return false;
    if (region   && o.region      !== region)   return false;
    if (tipo     && o.tipo_viaje  !== tipo)     return false;
    if (clima    && o.tipo_clima  !== clima)    return false;
    if (pension  && o.pension     !== pension)  return false;
    if (estrellas && o.estrellas  !== estrellas) return false;
    if (bajadaOn && !(o.bajada_pct > 0))        return false;
    if (o.precio && o.precio < pmin)            return false;
    if (o.precio && o.precio > pmax)            return false;
    if (search) {{
      const hay = (o.titulo||"") + (o.destino||"") + (o.region||"") + (o.extras||"");
      if (!hay.toLowerCase().includes(search)) return false;
    }}
    return true;
  }});

  // Ordenar
  if (orden === "precio_asc")  filtered.sort((a,b) => (a.precio||9999) - (b.precio||9999));
  if (orden === "precio_desc") filtered.sort((a,b) => (b.precio||0)    - (a.precio||0));
  if (orden === "bajada")      filtered.sort((a,b) => (b.bajada_pct||0) - (a.bajada_pct||0));
  // recientes: ya viene ordenado por primera_vez DESC del build

  document.getElementById("st-total").textContent = filtered.length;
  document.getElementById("rc").textContent = filtered.length + " resultado" + (filtered.length===1?"":"s");

  page = 1;
  render();
}}

function render() {{
  const container = document.getElementById("grid-container");
  const start = (page-1)*PER;
  const slice = filtered.slice(start, start+PER);

  if (!slice.length) {{
    container.innerHTML = '<div class="empty"><div class="icon">🏖️</div><p>Sin resultados.</p></div>';
    document.getElementById("pagination").innerHTML = "";
    return;
  }}

  const grid = document.createElement("div");
  grid.className = "grid";
  slice.forEach(o => grid.appendChild(card(o)));
  container.innerHTML = "";
  container.appendChild(grid);
  renderPagination();
}}

function card(o) {{
  const el = document.createElement("div");
  el.className = "card";

  const fClass = {{traventia:"ft", buscounchollo:"fb", weekendesk:"fw"}}[o.fuente] || "ft";
  const fLabel = {{traventia:"Traventia", buscounchollo:"BuscoUnChollo", weekendesk:"Weekendesk"}}[o.fuente] || o.fuente;

  const imgHtml = o.imagen_url
    ? `<div class="card-img"><img src="${{o.imagen_url}}" loading="lazy" onerror="this.parentElement.innerHTML='✈️'"></div>`
    : `<div class="card-img">✈️</div>`;

  const badges = [
    o.tipo_viaje  ? `<span class="badge tipo">${{o.tipo_viaje}}</span>`  : "",
    o.tipo_clima  ? `<span class="badge clima">${{o.tipo_clima}}</span>` : "",
    o.pension && o.pension !== "Sin especificar" ? `<span class="badge pension">${{o.pension}}</span>` : "",
    o.estrellas   ? `<span class="badge">${{o.estrellas}}</span>` : "",
  ].filter(Boolean).join("");

  const gtags = (o.gemini_tags||[]).slice(0,3).map(t=>`<span class="gtag">✦ ${{t}}</span>`).join(" ");
  const resumen = o.gemini_resumen ? `<div style="font-size:12px;color:var(--muted);font-style:italic">${{o.gemini_resumen}}</div>` : "";
  const destino = [o.destino, o.region].filter(Boolean).join(" · ");

  let priceHtml = "";
  if (o.precio) {{
    priceHtml += `<div class="price-main">${{Math.round(o.precio)}}€</div>`;
    priceHtml += `<div class="price-label">/ persona</div>`;
    if (o.bajada_pct > 0) {{
      priceHtml += `<div class="price-old">${{Math.round(o.precio_anterior)}}€</div>`;
    }}
  }} else {{
    priceHtml = `<div class="price-main" style="font-size:14px;color:var(--muted)">Consultar</div>`;
  }}

  const priceBadge = o.bajada_pct > 0 ? `<span class="badge-down">↓ ${{o.bajada_pct}}%</span>` : "";

  el.innerHTML = `
    ${{imgHtml}}
    <div class="card-body">
      <div style="display:flex;align-items:center;justify-content:space-between">
        <span class="card-fuente ${{fClass}}">${{fLabel}}</span>
        ${{o.duracion_noches ? `<span style="font-size:11px;color:var(--muted)">${{o.duracion_noches}}🌙</span>` : ""}}
      </div>
      <div class="card-title">${{esc(o.titulo||"")}}</div>
      ${{destino ? `<div class="card-dest">📍 ${{esc(destino)}}</div>` : ""}}
      ${{resumen}}
      <div class="badges">${{badges}}</div>
      ${{gtags ? `<div style="display:flex;flex-wrap:wrap;gap:4px">${{gtags}}</div>` : ""}}
    </div>
    <div class="card-footer">
      <div>${{priceHtml}}${{priceBadge}}</div>
      <a href="${{o.url}}" target="_blank" class="card-link">Ver →</a>
    </div>
  `;
  return el;
}}

function renderPagination() {{
  const total = filtered.length;
  const pages = Math.ceil(total / PER);
  const el    = document.getElementById("pagination");
  if (pages <= 1) {{ el.innerHTML = ""; return; }}

  const btns = [];
  btns.push(`<button onclick="goPage(${{page-1}})" ${{page===1?"disabled":""}}>‹</button>`);
  for (let i=1; i<=pages; i++) {{
    if (i===1||i===pages||Math.abs(i-page)<=2)
      btns.push(`<button class="${{i===page?'active':''}}" onclick="goPage(${{i}})">${{i}}</button>`);
    else if (Math.abs(i-page)===3) btns.push(`<span style="padding:0 4px">…</span>`);
  }}
  btns.push(`<button onclick="goPage(${{page+1}})" ${{page===pages?"disabled":""}}>›</button>`);
  el.innerHTML = btns.join("");
}}

function goPage(p) {{
  const pages = Math.ceil(filtered.length / PER);
  if (p<1||p>pages) return;
  page = p;
  render();
  window.scrollTo({{top:0,behavior:"smooth"}});
}}

function resetFilters() {{
  ["f-fuente","f-pais","f-region","f-tipo","f-clima","f-pension","f-estrellas","f-orden"].forEach(id=>{{
    const el=document.getElementById(id); if(el) el.value="";
  }});
  ["f-search","t-search","f-pmin","f-pmax"].forEach(id=>{{
    const el=document.getElementById(id); if(el) el.value="";
  }});
  bajadaOn = false;
  document.getElementById("chip-bajada").classList.remove("active");
  applyFilters();
}}

function esc(s) {{
  return String(s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}}

// Inicializar
applyFilters();
</script>
</body>
</html>"""


def make_opts(values):
    return "".join(f'<option value="{v}">{v}</option>' for v in values if v)


def build():
    print("📦 Leyendo DB...")
    data = load_data()

    os.makedirs(OUT_DIR, exist_ok=True)

    stats   = data["stats"]
    filtros = data["filtros"]
    ofertas = data["ofertas"]

    # Stats para header
    conn2   = sqlite3.connect(DB_PATH)
    historico = conn2.execute("SELECT COUNT(*) FROM ofertas").fetchone()[0]
    conn2.close()

    html = HTML_TEMPLATE.format(
        generado      = stats["generado"],
        total         = stats["total"],
        historico     = historico,
        bajadas       = stats["bajadas"],
        precio_med    = stats["precio_med"],
        fuente_opts   = make_opts(filtros["fuentes"]),
        pais_opts     = make_opts(filtros["paises"]),
        region_opts   = make_opts(filtros["regiones"]),
        tipo_opts     = make_opts(filtros["tipos"]),
        clima_opts    = make_opts(filtros["climas"]),
        pension_opts  = make_opts(filtros["pensiones"]),
        estrellas_opts= make_opts(filtros["estrellas"]),
        data_json     = json.dumps({"ofertas": ofertas}, ensure_ascii=False),
    )

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    size_kb = os.path.getsize(OUT_FILE) // 1024
    print(f"✅ Generado: {OUT_FILE} ({size_kb} KB, {stats['total']} ofertas)")


if __name__ == "__main__":
    build()
