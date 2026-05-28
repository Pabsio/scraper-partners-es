"""
gemini_enricher.py
Enriquece con Gemini SOLO las ofertas que no tienen región/país detectados.
Estrategia ultra-light:
  - Una sola llamada API por ejecución (batch de hasta 50 ofertas)
  - Solo procesa ofertas con gemini_enriquecida = 0
  - Modelo: gemini-2.5-flash via v1beta
  - Coste real estimado: < 0.001$ por ejecución

INSTALACIÓN:
    pip3 install google-genai
"""

import os
import json
import re

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from database import get_conn, get_pending_gemini, save_gemini_results

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
BATCH_SIZE     = 50
MODEL          = "gemini-2.5-flash"


def _build_prompt(offers: list) -> str:
    items = []
    for o in offers:
        items.append({
            "id":      o["id"],
            "titulo":  o["titulo"] or "",
            "destino": o["destino"] or "",
        })

    return f"""Analiza estas ofertas de viaje en español y para cada una devuelve un JSON.

Ofertas:
{json.dumps(items, ensure_ascii=False, indent=2)}

Para cada oferta devuelve SOLO este JSON array (sin explicaciones, sin markdown):
[
  {{
    "id": <id>,
    "region": "<comunidad autónoma o región del país>",
    "pais": "<país>",
    "tipo_clima": "<uno de: Playa | Montaña | Ciudad | Rural | Internacional | Parque>",
    "tags": ["tag1", "tag2"],
    "resumen": "<descripción atractiva de 1 frase>"
  }},
  ...
]

Reglas:
- Si el destino es en España, usa el nombre oficial de la comunidad autónoma.
- tags: máximo 3, ejemplos: Romántico, Familiar, Aventura, Gastronómico, Cultural, Relax, Lujo, Budget
- resumen: máximo 80 caracteres, atractivo y en español
- Si no puedes determinar algo, deja el campo vacío ("")
"""


def _parse_gemini_response(text: str) -> list[dict]:
    text = re.sub(r"```json|```", "", text).strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
    return []


def enrich_pending():
    """Llama a Gemini para enriquecer ofertas pendientes. Una sola llamada API."""
    if not GEMINI_AVAILABLE:
        print("   ⚠️  google-genai no instalado. Ejecuta: pip3 install google-genai")
        return

    if not GEMINI_API_KEY:
        print("   ⚠️  GEMINI_API_KEY no configurada. Salta enriquecimiento Gemini.")
        return

    pending = get_pending_gemini(limit=BATCH_SIZE)
    if not pending:
        print("   ✅ No hay ofertas pendientes de enriquecimiento Gemini.")
        return

    print(f"   🤖 Gemini: enriqueciendo {len(pending)} ofertas (1 llamada API)...")

    client = genai.Client(
        api_key=GEMINI_API_KEY,
        http_options={"api_version": "v1beta"},
    )
    prompt = _build_prompt(pending)

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=8192,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        results_raw = _parse_gemini_response(response.text)

        if not results_raw:
            print("   ⚠️  Gemini devolvió respuesta vacía o no parseable.")
            _mark_all_processed([o["id"] for o in pending])
            return

        results = []
        ids_processed = set()
        for r in results_raw:
            results.append({
                "id":         r.get("id"),
                "region":     r.get("region", ""),
                "pais":       r.get("pais", ""),
                "tipo_clima": r.get("tipo_clima", ""),
                "tags":       json.dumps(r.get("tags", []), ensure_ascii=False),
                "resumen":    r.get("resumen", ""),
            })
            if r.get("id"):
                ids_processed.add(r["id"])

        save_gemini_results(results)

        missing = [o["id"] for o in pending if o["id"] not in ids_processed]
        if missing:
            _mark_all_processed(missing)

        print(f"   ✅ Gemini: {len(results)} ofertas enriquecidas")

    except Exception as e:
        print(f"   ❌ Error Gemini API: {e}")


def _mark_all_processed(ids: list):
    with get_conn() as conn:
        for id_ in ids:
            conn.execute(
                "UPDATE ofertas SET gemini_enriquecida = 1 WHERE id = ?", (id_,)
            )
