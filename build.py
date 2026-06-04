"""
build.py — Genera docs/index.html estático para el board de partners
(Traventia · BuscoUnChollo · Weekendesk)
Brandbook HolidayPirates: purple #6A3460, Open Sans, pills filters
"""

import sqlite3, json, os
from datetime import datetime

DB_PATH  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ofertas.db")
OUT_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
OUT_FILE = os.path.join(OUT_DIR, "index.html")

# Pension normalizer — datos vienen de texto libre, muchos "Sin especificar"
PENSION_EN = {
    "Todo Incluido": "All Inclusive", "Media Pensión": "Half Board",
    "Pensión Completa": "Full Board", "Desayuno": "Breakfast",
    "Solo Alojamiento": "Room Only", "Sin especificar": "",
}

FUENTE_LABELS = {
    "traventia":     "Traventia",
    "buscounchollo": "BuscoUnChollo",
    "weekendesk":    "Weekendesk",
}


def load_data():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT
            o.id, o.url, o.fuente, o.titulo, o.destino, o.region, o.pais,
            o.tipo_clima, o.tipo_viaje, o.estrellas, o.pension, o.extras,
            o.precio, o.precio_anterior, o.precio_min, o.precio_por, o.imagen_url,
            o.duracion_noches, o.gemini_tags, o.gemini_resumen,
            o.primera_vez, o.ultima_vez
        FROM ofertas o
        WHERE o.activa = 1
        ORDER BY o.primera_vez DESC
    """).fetchall()
    conn.close()

    ofertas = []
    for r in rows:
        d = dict(r)
        try:    d["gemini_tags"] = json.loads(d.get("gemini_tags") or "[]")
        except: d["gemini_tags"] = []

        if d.get("precio") and d.get("precio_anterior"):
            try:
                d["bajada_pct"] = round(
                    (float(d["precio_anterior"]) - float(d["precio"])) /
                    float(d["precio_anterior"]) * 100
                )
            except: d["bajada_pct"] = None
        else:
            d["bajada_pct"] = None

        # Normalizar pension a inglés, vaciar "Sin especificar"
        d["pension_en"] = PENSION_EN.get(d.get("pension",""), d.get("pension",""))
        ofertas.append(d)

    stats = {
        "total":    len(ofertas),
        "generado": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }

    # Filtros únicos
    fuentes   = sorted(set(o["fuente"]     for o in ofertas if o.get("fuente")))
    regiones  = sorted(set(o["region"]     for o in ofertas if o.get("region")))
    paises    = sorted(set(o["pais"]       for o in ofertas if o.get("pais")))
    tipos     = sorted(set(o["tipo_viaje"] for o in ofertas if o.get("tipo_viaje")))
    climas    = sorted(set(o["tipo_clima"] for o in ofertas if o.get("tipo_clima")))
    pensiones = sorted(set(o["pension_en"] for o in ofertas if o.get("pension_en")))
    estrellas = sorted(set(o["estrellas"]  for o in ofertas if o.get("estrellas")))

    return {
        "ofertas": ofertas,
        "stats":   stats,
        "filtros": {
            "fuentes":   fuentes,
            "regiones":  regiones,
            "paises":    paises,
            "tipos":     tipos,
            "climas":    climas,
            "pensiones": pensiones,
            "estrellas": estrellas,
        }
    }


def build():
    print("📦 Reading database...")
    data    = load_data()
    stats   = data["stats"]
    data_js = json.dumps(data, ensure_ascii=False)

    os.makedirs(OUT_DIR, exist_ok=True)

    html = HTML.replace("__DATA__",      data_js)\
               .replace("__GENERATED__", stats["generado"])\
               .replace("__TOTAL__",     str(stats["total"]))

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ {OUT_FILE} ({os.path.getsize(OUT_FILE)//1024} KB, {stats['total']} offers)")


HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Partner Deals · HolidayPirates</title>
<link href="https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --hp:#6A3460;--hp-l:#f3eef2;--hp-m:#d4b8cf;
  --black:#333;--white:#fff;--bg:#f7f4f6;--surface:#fff;
  --border:#e8e0e6;--text:#333;--muted:#8a7a87;
  --green:#a9d380;--green-l:#f0fae6;--green-d:#3d6b1a;
  --radius:12px;--shadow:0 1px 4px rgba(106,52,96,.08);
  --shadow-md:0 6px 20px rgba(106,52,96,.14);
}
body{font-family:"Open Sans",sans-serif;background:var(--bg);color:var(--text);font-size:14px;-webkit-font-smoothing:antialiased}
a{text-decoration:none}
button{cursor:pointer;font:inherit;border:none;background:none}

/* ── Topbar ── */
.topbar{
  background:var(--hp);padding:0 24px;height:52px;
  display:flex;align-items:center;justify-content:space-between;
  position:sticky;top:0;z-index:100;
  box-shadow:0 2px 8px rgba(106,52,96,.3);
}
.topbar-brand{display:flex;align-items:center;gap:10px;color:#fff}
.topbar-brand h1{font-size:16px;font-weight:700}
.topbar-meta{font-size:12px;color:var(--hp-m)}
.topbar-right{display:flex;align-items:center;gap:12px}
.view-toggle{display:flex;gap:4px}
.vbtn{padding:5px 10px;border-radius:8px;font-size:14px;color:rgba(255,255,255,.6);transition:all .15s}
.vbtn.on{background:rgba(255,255,255,.2);color:#fff}
.vbtn:hover{color:#fff}

/* ── Filter bar ── */
.filterbar{
  background:var(--surface);border-bottom:1px solid var(--border);
  padding:10px 24px;display:flex;flex-direction:column;gap:8px;
  position:sticky;top:52px;z-index:99;
  box-shadow:0 2px 6px rgba(106,52,96,.06);
}
.frow{display:flex;align-items:center;gap:7px;flex-wrap:wrap}
.flabel{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--hp);white-space:nowrap;min-width:52px}

/* Pills */
.pill{
  padding:5px 13px;border-radius:20px;font-size:12px;font-weight:600;
  background:var(--bg);border:1.5px solid var(--border);color:var(--muted);
  cursor:pointer;transition:all .15s;white-space:nowrap;
}
.pill:hover{border-color:var(--hp);color:var(--hp)}
.pill.on{background:var(--hp);border-color:var(--hp);color:#fff}

/* Source pills with brand colors */
.pill-traventia.on{background:#f59e0b;border-color:#f59e0b;color:#fff}
.pill-traventia:hover{border-color:#f59e0b;color:#f59e0b}
.pill-buscounchollo.on{background:#16a34a;border-color:#16a34a;color:#fff}
.pill-buscounchollo:hover{border-color:#16a34a;color:#16a34a}
.pill-weekendesk.on{background:#2563eb;border-color:#2563eb;color:#fff}
.pill-weekendesk:hover{border-color:#2563eb;color:#2563eb}

/* Search & select */
.sw{position:relative;flex:1;max-width:300px}
.sw input{
  width:100%;padding:6px 12px 6px 30px;border:1.5px solid var(--border);
  border-radius:20px;font:inherit;font-size:13px;background:var(--bg);outline:none;
  transition:border-color .15s;
}
.sw input:focus{border-color:var(--hp)}
.si{position:absolute;left:9px;top:50%;transform:translateY(-50%);color:var(--muted);font-size:13px;pointer-events:none}
.hp-sel{
  padding:5px 11px;border:1.5px solid var(--border);border-radius:20px;
  font:inherit;font-size:13px;background:var(--bg);outline:none;color:var(--text);cursor:pointer;
}
.hp-sel:focus{border-color:var(--hp)}
.rc{font-size:12px;color:var(--muted);margin-left:auto;white-space:nowrap}

/* ── Grid ── */
.grid-wrap{padding:14px 24px 32px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(278px,1fr));gap:13px}

.card{
  background:var(--surface);border-radius:var(--radius);overflow:hidden;
  box-shadow:var(--shadow);transition:box-shadow .2s,transform .2s;
  display:flex;flex-direction:column;border:1px solid var(--border);
}
.card:hover{box-shadow:var(--shadow-md);transform:translateY(-2px)}
.card-img{height:155px;overflow:hidden;position:relative;flex-shrink:0;background:var(--bg);display:flex;align-items:center;justify-content:center;font-size:36px;color:var(--muted)}
.card-img img{width:100%;height:100%;object-fit:cover;display:block}
.drop-badge{position:absolute;top:8px;right:8px;background:var(--green);color:#fff;font-size:11px;font-weight:700;padding:3px 8px;border-radius:7px}

.card-body{padding:11px 13px;flex:1;display:flex;flex-direction:column;gap:4px}
.src-badge{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;padding:2px 8px;border-radius:4px;align-self:flex-start}
.src-traventia{background:#fef3c7;color:#92400e}
.src-buscounchollo{background:#dcfce7;color:#166534}
.src-weekendesk{background:#dbeafe;color:#1e40af}
.card-title{font-size:13px;font-weight:700;line-height:1.3}
.card-loc{font-size:12px;color:var(--muted)}
.card-badges{display:flex;flex-wrap:wrap;gap:4px;margin-top:2px}
.bdg{font-size:11px;padding:2px 8px;border-radius:6px;font-weight:600}
.bdg-tipo{background:#fff7ed;color:#c2410c}
.bdg-clima{background:var(--green-l);color:var(--green-d)}
.bdg-pension{background:var(--hp-l);color:var(--hp)}
.bdg-stars{background:#fefce8;color:#9a7206}
.gtag{font-size:10px;padding:2px 7px;border-radius:5px;background:var(--hp-l);color:var(--hp)}

.card-footer{padding:9px 13px 12px;border-top:1px solid var(--border);display:flex;align-items:flex-end;justify-content:space-between;margin-top:auto}
.price-main{font-size:22px;font-weight:800;color:var(--hp);line-height:1}
.price-label{font-size:10px;color:var(--muted);margin-top:1px}
.price-old{font-size:11px;color:var(--muted);text-decoration:line-through}
.cta-btn{padding:7px 13px;background:var(--hp);color:#fff;border-radius:9px;font-size:12px;font-weight:700;white-space:nowrap;transition:background .15s}
.cta-btn:hover{background:#4e2647}

/* ── List view ── */
.list{display:flex;flex-direction:column}
.list-item{background:var(--surface);border-bottom:1px solid var(--border);display:flex;align-items:stretch;transition:background .15s}
.list-item:first-child{border-top:1px solid var(--border);border-radius:var(--radius) var(--radius) 0 0;overflow:hidden}
.list-item:last-child{border-radius:0 0 var(--radius) var(--radius);overflow:hidden}
.list-item:hover{background:#faf7f9}
.list-thumb{width:100px;min-width:100px;height:72px;overflow:hidden;flex-shrink:0;background:var(--bg);display:flex;align-items:center;justify-content:center;font-size:24px;color:var(--muted)}
.list-thumb img{width:100%;height:100%;object-fit:cover;display:block}
.list-body{flex:1;padding:9px 13px;display:flex;flex-direction:column;justify-content:center;gap:2px;min-width:0}
.list-name{font-size:13px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.list-loc{font-size:12px;color:var(--muted)}
.list-right{padding:9px 14px;display:flex;flex-direction:column;align-items:flex-end;justify-content:center;gap:3px;min-width:140px;border-left:1px solid var(--border)}

.empty{text-align:center;padding:80px 20px;color:var(--muted)}
.empty .icon{font-size:52px;margin-bottom:12px}

  #auth-gate{position:fixed;inset:0;background:var(--bg);z-index:9999;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:20px}
  #auth-gate .auth-box{background:#fff;border-radius:18px;padding:40px 48px;text-align:center;box-shadow:0 8px 40px rgba(106,52,96,.12);max-width:380px;width:90%}
  #auth-gate .auth-title{font-size:22px;font-weight:800;color:var(--hp);margin-bottom:8px}
  #auth-gate .auth-sub{font-size:13px;color:var(--muted);margin-bottom:28px}
  #auth-gate .auth-btn{width:100%;font-family:inherit;font-size:14px;font-weight:700;padding:13px;border-radius:20px;border:none;background:var(--hp);color:#fff;cursor:pointer;transition:opacity .15s;display:flex;align-items:center;justify-content:center;gap:10px}
  #auth-gate .auth-btn:hover{opacity:.88}
  #auth-gate .auth-error{color:#c0392b;font-size:12px;margin-top:12px;display:none}
  #app-content{display:none}
  .signout-btn{font-family:inherit;font-size:11px;font-weight:700;padding:5px 12px;border-radius:20px;border:1.5px solid rgba(255,255,255,.3);background:none;color:rgba(255,255,255,.8);cursor:pointer;transition:all .15s}
  .signout-btn:hover{background:rgba(255,255,255,.15);color:#fff}
</style>
</head>
<body>

<!-- AUTH GATE -->
<div id="auth-gate">
  <div class="auth-box">
    <div style="font-size:40px;margin-bottom:12px">🏴‍☠️</div>
    <div class="auth-title">Partner Deals</div>
    <div class="auth-sub">Sign in with your HolidayPirates account to continue</div>
    <button class="auth-btn" id="login-btn">
      <svg width="18" height="18" viewBox="0 0 18 18"><path fill="#fff" d="M9 3.48c1.69 0 2.83.73 3.48 1.34l2.54-2.48C13.46.89 11.43 0 9 0 5.48 0 2.44 2.02.96 4.96l2.91 2.26C4.6 5.05 6.62 3.48 9 3.48z"/><path fill="#fff" d="M17.64 9.2c0-.74-.06-1.28-.19-1.84H9v3.34h4.96c-.1.83-.64 2.08-1.84 2.92l2.84 2.2c1.7-1.57 2.68-3.88 2.68-6.62z"/><path fill="#fff" d="M3.88 10.78A5.54 5.54 0 0 1 3.58 9c0-.62.11-1.22.29-1.78L.96 4.96A9.008 9.008 0 0 0 0 9c0 1.45.35 2.82.96 4.04l2.92-2.26z"/><path fill="#fff" d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.84-2.2c-.76.53-1.78.9-3.12.9-2.38 0-4.4-1.57-5.12-3.74L.97 13.04C2.45 15.98 5.48 18 9 18z"/></svg>
      Sign in with Google
    </button>
    <div class="auth-error" id="auth-error">Access restricted to @holidaypirates.com accounts.</div>
  </div>
</div>

<div id="app-content">

<div class="topbar">
  <div class="topbar-brand">
    <svg width="24" height="24" viewBox="0 0 100 100"><path d="M50 8C31 8 16 23 16 42c0 27 34 52 34 52s34-25 34-52C84 23 69 8 50 8z" fill="rgba(255,255,255,.2)" stroke="#fff" stroke-width="3"/><circle cx="62" cy="34" r="13" fill="#e63030"/><circle cx="68" cy="30" r="3" fill="#fff"/><path d="M57 43 L44 54 L51 57 L47 67 L61 55 L54 52 Z" fill="#f39c12"/><path d="M47 24 L51 17 L55 24" fill="#27ae60"/></svg>
    <h1>Partner Deals · HolidayPirates</h1>
  </div>
  <div class="topbar-right"><button class="signout-btn" id="signout-btn">Sign out</button>
    <span class="topbar-meta">Updated __GENERATED__ · __TOTAL__ offers</span>
    <div class="view-toggle">
      <button class="vbtn on" id="btn-grid" onclick="setView('grid')" title="Grid">⊞</button>
      <button class="vbtn" id="btn-list" onclick="setView('list')" title="List">≡</button>
    </div>
  </div>
</div>

<!-- FILTERS -->
<div class="filterbar">

  <div class="frow">
    <span class="flabel">Source</span>
    <button class="pill on" data-g="source" data-v="">All</button>
    <button class="pill pill-traventia" data-g="source" data-v="traventia">Traventia</button>
    <button class="pill pill-buscounchollo" data-g="source" data-v="buscounchollo">BuscoUnChollo</button>
    <button class="pill pill-weekendesk" data-g="source" data-v="weekendesk">Weekendesk</button>
    <div class="sw" style="margin-left:auto">
      <span class="si">🔍</span>
      <input type="text" id="f-search" placeholder="Search destination, hotel…" oninput="applyFilters()">
    </div>
    <select class="hp-sel" id="f-sort" onchange="applyFilters()">
      <option value="recientes">Most recent</option>
      <option value="precio_asc">Price ↑</option>
      <option value="precio_desc">Price ↓</option>
      <option value="bajada">Biggest drop</option>
    </select>
    <span class="rc" id="rc"></span>
  </div>

  <div class="frow">
    <span class="flabel">Region</span>
    <button class="pill on" data-g="region" data-v="">All</button>
    <div id="region-pills" style="display:flex;gap:6px;flex-wrap:wrap"></div>
  </div>

  <div class="frow">
    <span class="flabel">Type</span>
    <button class="pill on" data-g="tipo" data-v="">All</button>
    <div id="tipo-pills" style="display:flex;gap:6px;flex-wrap:wrap"></div>
    <span style="color:var(--border);margin:0 6px">|</span>
    <span class="flabel">Climate</span>
    <button class="pill on" data-g="clima" data-v="">All</button>
    <div id="clima-pills" style="display:flex;gap:6px;flex-wrap:wrap"></div>
  </div>

  <div class="frow">
    <span class="flabel">Board</span>
    <button class="pill on" data-g="pension" data-v="">All</button>
    <div id="pension-pills" style="display:flex;gap:6px;flex-wrap:wrap"></div>
    <span style="color:var(--border);margin:0 6px">|</span>
    <span class="flabel">Stars</span>
    <button class="pill on" data-g="estrellas" data-v="">All</button>
    <div id="estrellas-pills" style="display:flex;gap:6px;flex-wrap:wrap"></div>
    <span style="color:var(--border);margin:0 6px">|</span>
    <span class="flabel">Price</span>
    <input type="number" id="f-pmin" placeholder="Min €" class="hp-sel" style="width:72px" oninput="applyFilters()">
    <span style="color:var(--muted);font-size:13px">–</span>
    <input type="number" id="f-pmax" placeholder="Max €" class="hp-sel" style="width:72px" oninput="applyFilters()">
    <button class="pill" id="chip-drop" style="margin-left:8px" onclick="toggleDrop()">💚 Price drop</button>
    <button style="margin-left:auto;padding:5px 12px;border:1.5px solid var(--border);border-radius:20px;font-size:12px;color:var(--muted);background:var(--bg);cursor:pointer" onclick="resetFilters()">✕ Clear</button>
  </div>

</div>

<!-- CONTENT -->
<div class="grid-wrap">
  <div id="content"></div>
</div>

<script>
const D = __DATA__;
const F = { source:"", region:"", tipo:"", clima:"", pension:"", estrellas:"", pmin:0, pmax:Infinity, search:"", drop:false };
let viewMode = "grid";

let appStarted = false;
function initApp() {
  if (appStarted) return;
  appStarted = true;
  buildPills("region-pills",   "region",    D.filtros.regiones);
  buildPills("tipo-pills",     "tipo",      D.filtros.tipos);
  buildPills("clima-pills",    "clima",     D.filtros.climas);
  buildPills("pension-pills",  "pension",   D.filtros.pensiones);
  buildPills("estrellas-pills","estrellas", D.filtros.estrellas);
  bindPills();
  applyFilters();
}

function buildPills(containerId, group, values) {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.innerHTML = "";
  values.forEach(v => {
    const b = document.createElement("button");
    b.className = "pill"; b.dataset.g = group; b.dataset.v = v;
    b.textContent = v; el.appendChild(b);
  });
}

function bindPills() {
  document.addEventListener("click", e => {
    const pill = e.target.closest(".pill[data-g]");
    if (!pill) return;
    const g = pill.dataset.g, v = pill.dataset.v;
    document.querySelectorAll(`.pill[data-g="${g}"]`).forEach(p => p.classList.remove("on"));
    pill.classList.add("on");
    F[g] = v;
    applyFilters();
  });
}

function setView(mode) {
  viewMode = mode;
  document.getElementById("btn-grid").classList.toggle("on", mode==="grid");
  document.getElementById("btn-list").classList.toggle("on", mode==="list");
  render();
}

function toggleDrop() {
  F.drop = !F.drop;
  document.getElementById("chip-drop").classList.toggle("on", F.drop);
  applyFilters();
}

function applyFilters() {
  F.pmin   = parseFloat(document.getElementById("f-pmin")?.value) || 0;
  F.pmax   = parseFloat(document.getElementById("f-pmax")?.value) || Infinity;
  F.search = (document.getElementById("f-search")?.value || "").toLowerCase();
  const sort = document.getElementById("f-sort")?.value || "recientes";

  let filtered = D.ofertas.filter(o => {
    if (F.source    && o.fuente     !== F.source)    return false;
    if (F.region    && o.region     !== F.region)    return false;
    if (F.tipo      && o.tipo_viaje !== F.tipo)      return false;
    if (F.clima     && o.tipo_clima !== F.clima)     return false;
    if (F.pension   && o.pension_en !== F.pension)   return false;
    if (F.estrellas && o.estrellas  !== F.estrellas) return false;
    if (F.drop      && !(o.bajada_pct > 0))          return false;
    if (o.precio && o.precio < F.pmin) return false;
    if (o.precio && o.precio > F.pmax) return false;
    if (F.search) {
      const hay = ((o.titulo||"")+(o.destino||"")+(o.region||"")+(o.extras||"")).toLowerCase();
      if (!hay.includes(F.search)) return false;
    }
    return true;
  });

  if (sort === "precio_asc")  filtered.sort((a,b) => (a.precio||9999)-(b.precio||9999));
  if (sort === "precio_desc") filtered.sort((a,b) => (b.precio||0)-(a.precio||0));
  if (sort === "bajada")      filtered.sort((a,b) => (b.bajada_pct||0)-(a.bajada_pct||0));

  document.getElementById("rc").textContent = filtered.length + " result" + (filtered.length===1?"":"s");
  window._filtered = filtered;
  render();
}

function render() {
  const el  = document.getElementById("content");
  const filtered = window._filtered || [];
  if (!filtered.length) {
    el.innerHTML = '<div class="empty"><div class="icon">🏖️</div><p>No results found.</p></div>';
    return;
  }
  el.innerHTML = "";
  if (viewMode === "grid") {
    const g = document.createElement("div"); g.className = "grid";
    filtered.forEach(o => g.appendChild(makeCard(o)));
    el.appendChild(g);
  } else {
    const l = document.createElement("div"); l.className = "list";
    filtered.forEach(o => l.appendChild(makeRow(o)));
    el.appendChild(l);
  }
}

function makeCard(o) {
  const el = document.createElement("div"); el.className = "card";
  const img = o.imagen_url
    ? `<img src="${esc(o.imagen_url)}" loading="lazy" alt="" onerror="this.parentElement.innerHTML='✈️'">`
    : "✈️";
  const destino = [o.destino, o.region].filter(Boolean).join(" · ");
  const badges = [
    o.tipo_viaje ? `<span class="bdg bdg-tipo">${esc(o.tipo_viaje)}</span>` : "",
    o.tipo_clima ? `<span class="bdg bdg-clima">${esc(o.tipo_clima)}</span>` : "",
    o.pension_en ? `<span class="bdg bdg-pension">${esc(o.pension_en)}</span>` : "",
    o.estrellas  ? `<span class="bdg bdg-stars">${esc(o.estrellas)}</span>` : "",
  ].filter(Boolean).join("");
  const gtags = (o.gemini_tags||[]).slice(0,2).map(t=>`<span class="gtag">✦ ${esc(t)}</span>`).join(" ");
  const resumen = o.gemini_resumen ? `<div style="font-size:11px;color:var(--muted);font-style:italic;margin-top:2px">${esc(o.gemini_resumen)}</div>` : "";

  el.innerHTML = `
    <div class="card-img">
      ${img}
      ${o.bajada_pct>0?`<div class="drop-badge">↓ ${o.bajada_pct}%</div>`:""}
    </div>
    <div class="card-body">
      <div style="display:flex;align-items:center;justify-content:space-between">
        <span class="src-badge src-${o.fuente}">${esc(o.fuente==="buscounchollo"?"BUC":o.fuente==="weekendesk"?"WKD":"TRV")}</span>
        ${o.duracion_noches?`<span style="font-size:11px;color:var(--muted)">${o.duracion_noches}🌙</span>`:""}
      </div>
      <div class="card-title">${esc(o.titulo||"")}</div>
      ${destino?`<div class="card-loc">📍 ${esc(destino)}</div>`:""}
      ${resumen}
      <div class="card-badges">${badges}</div>
      ${gtags?`<div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:2px">${gtags}</div>`:""}
    </div>
    <div class="card-footer">
      <div>
        <div class="price-main">${o.precio?Math.round(o.precio)+"€":"—"}</div>
        <div class="price-label">/ ${o.precio_por==="noche"?"night":"person"}</div>
        ${o.bajada_pct>0&&o.precio_anterior?`<div class="price-old">${Math.round(o.precio_anterior)}€</div>`:""}
      </div>
      <a href="${esc(o.url)}" target="_blank" class="cta-btn">View →</a>
    </div>`;
  return el;
}

function makeRow(o) {
  const el = document.createElement("div"); el.className = "list-item";
  const img = o.imagen_url
    ? `<img src="${esc(o.imagen_url)}" loading="lazy" alt="" onerror="this.parentElement.innerHTML='✈️'">`
    : "✈️";
  const destino = [o.destino, o.region].filter(Boolean).join(", ");
  const pension = o.pension_en ? `<span class="bdg bdg-pension" style="font-size:10px;padding:1px 6px">${esc(o.pension_en)}</span>` : "";
  const tipo    = o.tipo_viaje ? `<span class="bdg bdg-tipo" style="font-size:10px;padding:1px 6px">${esc(o.tipo_viaje)}</span>` : "";

  el.innerHTML = `
    <div class="list-thumb">${img}</div>
    <div class="list-body">
      <div style="display:flex;align-items:center;gap:6px">
        <span class="src-badge src-${o.fuente}" style="font-size:9px">${esc(o.fuente==="buscounchollo"?"BUC":o.fuente==="weekendesk"?"WKD":"TRV")}</span>
        ${o.estrellas?`<span style="font-size:11px;color:#9a7206">${esc(o.estrellas)}</span>`:""}
      </div>
      <div class="list-name">${esc(o.titulo||"")}</div>
      ${destino?`<div class="list-loc">📍 ${esc(destino)}</div>`:""}
      <div style="display:flex;gap:4px;margin-top:2px">${tipo}${pension}</div>
    </div>
    <div class="list-right">
      ${o.bajada_pct>0?`<div style="font-size:11px;font-weight:700;color:var(--green-d);background:var(--green-l);padding:2px 7px;border-radius:5px">↓ ${o.bajada_pct}%</div>`:""}
      <div class="price-main" style="font-size:20px">${o.precio?Math.round(o.precio)+"€":"—"}</div>
      <div class="price-label">/ ${o.precio_por==="noche"?"night":"person"}</div>
      ${o.bajada_pct>0&&o.precio_anterior?`<div class="price-old">${Math.round(o.precio_anterior)}€</div>`:""}
      <a href="${esc(o.url)}" target="_blank" class="cta-btn" style="font-size:11px;padding:5px 10px;margin-top:4px">View →</a>
    </div>`;
  return el;
}

function resetFilters() {
  Object.keys(F).forEach(k => F[k] = k==="pmin"?0:k==="pmax"?Infinity:k==="drop"?false:"");
  document.querySelectorAll(".pill[data-g]").forEach(p => p.classList.remove("on"));
  document.querySelectorAll(".pill[data-v='']").forEach(p => p.classList.add("on"));
  document.getElementById("chip-drop").classList.remove("on");
  ["f-search","f-pmin","f-pmax"].forEach(id => { const el=document.getElementById(id); if(el) el.value=""; });
  document.getElementById("f-sort").value = "recientes";
  applyFilters();
}

function esc(s){ return String(s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"); }
</script>
</div><!-- /app-content -->

<!-- NETLIFY IDENTITY — redirect flow -->
<script>
  const IDENTITY = "https://scraper-partners-es.netlify.app/.netlify/identity";
  const gate       = document.getElementById('auth-gate');
  const appDiv     = document.getElementById('app-content');
  const loginBtn   = document.getElementById('login-btn');
  const errMsg     = document.getElementById('auth-error');
  const signoutBtn = document.getElementById('signout-btn');

  // Handle redirect callback from Google OAuth
  function handleCallback() {
    const hash = window.location.hash;
    if (!hash.includes('access_token') && !hash.includes('confirmation_token')) return false;
    const params = new URLSearchParams(hash.slice(1));
    const token = params.get('access_token');
    if (!token) return false;

    // Fetch user info with the token
    fetch(IDENTITY + '/user', {
      headers: { Authorization: 'Bearer ' + token }
    })
    .then(r => r.json())
    .then(user => {
      const email = (user.email || '').toLowerCase();
      if (email.endsWith('@holidaypirates.com')) {
        localStorage.setItem('hp_token', token);
        localStorage.setItem('hp_email', email);
        window.location.hash = '';
        showApp(email);
      } else {
        errMsg.textContent = 'Access restricted to @holidaypirates.com accounts.';
        errMsg.style.display = 'block';
        localStorage.removeItem('hp_token');
        localStorage.removeItem('hp_email');
      }
    })
    .catch(() => {
      errMsg.textContent = 'Login failed. Please try again.';
      errMsg.style.display = 'block';
    });
    return true;
  }

  function showApp(email) {
    gate.style.display = 'none';
    appDiv.style.display = 'block';
    const authUser = document.getElementById('auth-user');
    if (authUser) authUser.textContent = email;
    initApp();
  }

  function checkExistingSession() {
    const token = localStorage.getItem('hp_token');
    const email = localStorage.getItem('hp_email');
    if (!token || !email) return false;
    // Verify token is still valid
    fetch(IDENTITY + '/user', {
      headers: { Authorization: 'Bearer ' + token }
    })
    .then(r => {
      if (r.ok) showApp(email);
      else { localStorage.removeItem('hp_token'); localStorage.removeItem('hp_email'); }
    })
    .catch(() => { localStorage.removeItem('hp_token'); localStorage.removeItem('hp_email'); });
    return true;
  }

  // On load: check callback or existing session
  window.addEventListener('DOMContentLoaded', () => {
    if (!handleCallback()) {
      checkExistingSession();
    }
    if (sessionStorage.getItem('hp_domain_error')) {
      errMsg.style.display = 'block';
      sessionStorage.removeItem('hp_domain_error');
    }
  });

  // Login button → redirect to Google OAuth
  loginBtn.addEventListener('click', () => {
    errMsg.style.display = 'none';
    window.location.href = IDENTITY + '/authorize?provider=google&site_id=cda8b8f2-51e5-4025-ab65-1e6f0a4e9a37';
  });

  // Sign out
  if (signoutBtn) signoutBtn.addEventListener('click', () => {
    localStorage.removeItem('hp_token');
    localStorage.removeItem('hp_email');
    location.reload();
  });
</script>
</body>
</html>"""


if __name__ == "__main__":
    build()
