"""
main.py — Runner principal
Ejecuta todos los scrapers, sincroniza con SQLite, y lanza enriquecimiento Gemini.

Uso:
    python main.py                  # ejecutar todo
    python main.py --no-gemini      # saltar enriquecimiento
    python main.py --source traventia   # solo un scraper
"""

import sys
import argparse
from datetime import datetime

from database import init_db, upsert_offer, archive_missing
from gemini_enricher import enrich_pending

# Importar scrapers
sys.path.insert(0, "scrapers")
import traventia
import buscounchollo
import weekendesk

SCRAPERS = {
    "traventia":      traventia.scrape,
    "buscounchollo":  buscounchollo.scrape,
    "weekendesk":     weekendesk.scrape,
}


def run(sources=None, skip_gemini=False):
    print(f"\n{'='*60}")
    print(f"  Oferta Scraper — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")

    init_db()

    sources = sources or list(SCRAPERS.keys())
    total_stats = {"new": 0, "price_down": 0, "price_up": 0, "unchanged": 0, "archived": 0}

    for name in sources:
        if name not in SCRAPERS:
            print(f"⚠️  Scraper desconocido: {name}")
            continue

        print(f"\n▶ {name.upper()}")
        try:
            offers = SCRAPERS[name]()
        except Exception as e:
            print(f"   ❌ Error en scraper {name}: {e}")
            continue

        if not offers:
            print(f"   ⚠️  Sin resultados en {name}")
            continue

        # Sincronizar con DB
        active_urls = set()
        stats = {"new": 0, "price_down": 0, "price_up": 0, "unchanged": 0}
        for offer in offers:
            active_urls.add(offer["url"])
            result = upsert_offer(offer)
            stats[result] = stats.get(result, 0) + 1

        archived = archive_missing(active_urls, name)
        stats["archived"] = archived

        print(f"   📊 Nuevas: {stats['new']} | ↓ Precio: {stats['price_down']} | "
              f"↑ Precio: {stats['price_up']} | Archivadas: {archived}")

        for k, v in stats.items():
            total_stats[k] = total_stats.get(k, 0) + v

    print(f"\n{'─'*60}")
    print(f"  TOTAL — Nuevas: {total_stats['new']} | "
          f"↓ Precio: {total_stats['price_down']} | "
          f"↑ Precio: {total_stats['price_up']} | "
          f"Archivadas: {total_stats['archived']}")
    print(f"{'─'*60}\n")

    if not skip_gemini:
        print("🤖 Enriquecimiento Gemini...")
        enrich_pending()

    print("\n✅ ¡Listo!\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Oferta Scraper")
    parser.add_argument("--no-gemini", action="store_true", help="Saltar Gemini")
    parser.add_argument("--source", type=str, help="Solo un scraper: traventia|buscounchollo|weekendesk")
    args = parser.parse_args()

    sources = [args.source] if args.source else None
    run(sources=sources, skip_gemini=args.no_gemini)
