"""
scrapers/traventia.py
Scrapea https://www.traventia.es (home estática + páginas JS con Playwright)
"""

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Page

from parsers import (
    clean_text, parse_price, enrich_destination,
    extract_tipo_viaje, extract_estrellas, extract_pension,
    extract_extras, extract_noches,
)

FUENTE   = "traventia"
BASE_URL = "https://www.traventia.es"

STATIC_URLS = [
    "https://www.traventia.es",
]
JS_URLS = [
    "https://www.traventia.es/ofertas-costa",
    "https://www.traventia.es/hoteles-con-toboganes",
    "https://www.traventia.es/ofertas-ferry-hotel",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9",
}


def _extract_destino_from_title(title: str) -> str:
    """Traventia suele poner 📍 Destino o | Destino al final."""
    import re
    match = re.search(r"📍\s*([^\|]+)", title)
    if match:
        return match.group(1).strip().rstrip(".")
    if "|" in title:
        return title.split("|")[-1].strip().rstrip(".")
    return title


def _parse_card(card) -> dict | None:
    title_tag = card.select_one("h3") or card.select_one("h2")
    title_raw = title_tag.get_text(separator=" ", strip=True) if title_tag else ""
    if not title_raw:
        return None

    desc_tag = card.select_one("div[class*='_textoffer_'] p, div[class*='_textoffer_']")
    if desc_tag:
        desc = desc_tag.get_text(separator=" ", strip=True)
        title_raw = title_raw + " | " + desc

    import re
    price_text = next((t.strip() for t in card.find_all(string=re.compile(r"€"))), None)
    href       = card.get("href", "")
    url        = href if href.startswith("http") else BASE_URL + href

    titulo  = clean_text(title_raw)
    destino = _extract_destino_from_title(titulo)
    region, pais, tipo_clima = enrich_destination(destino + " " + titulo)

    img_tag = card.select_one("img")
    imagen  = img_tag.get("src") or img_tag.get("data-src") if img_tag else None

    return {
        "url":           url,
        "fuente":        FUENTE,
        "titulo":        titulo,
        "destino":       destino,
        "region":        region,
        "pais":          pais,
        "tipo_clima":    tipo_clima,
        "tipo_viaje":    extract_tipo_viaje(titulo),
        "estrellas":     extract_estrellas(titulo),
        "pension":       extract_pension(titulo),
        "extras":        extract_extras(titulo),
        "precio":        parse_price(price_text) if price_text else None,
        "moneda":        "EUR",
        "precio_por":    "persona",
        "imagen_url":    imagen,
        "duracion_noches": extract_noches(titulo),
        "adultos_min":   2,
    }


def _parse_html(html: str) -> list[dict]:
    soup   = BeautifulSoup(html, "html.parser")
    offers = []
    for card in soup.select("a[href*='/ofertas/']"):
        o = _parse_card(card)
        if o:
            offers.append(o)
    return offers


def _scrape_static(url: str) -> list[dict]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return _parse_html(r.text)
    except Exception as e:
        print(f"   ❌ Traventia static {url}: {e}")
        return []


def _scroll_and_parse(page: Page, url: str) -> list[dict]:
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_selector("a[href*='/ofertas/']", timeout=15000)
        prev = 0
        for _ in range(20):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1500)
            curr = page.locator("a[href*='/ofertas/']").count()
            if curr == prev:
                break
            prev = curr
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(500)
        return _parse_html(page.content())
    except Exception as e:
        print(f"   ❌ Traventia JS {url}: {e}")
        return []


def scrape(playwright_page=None) -> list[dict]:
    """
    Punto de entrada del scraper.
    Si se pasa playwright_page ya abierta, la reutiliza (modo batch).
    Devuelve lista de dicts normalizados.
    """
    seen  = set()
    all_  = []

    for url in STATIC_URLS:
        print(f"   🔍 [traventia] {url} (estático)")
        for o in _scrape_static(url):
            if o["url"] not in seen:
                seen.add(o["url"])
                all_.append(o)

    print(f"   🔍 [traventia] JS pages con Playwright...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page    = browser.new_page()
        page.set_extra_http_headers({"Accept-Language": "es-ES,es;q=0.9"})
        for url in JS_URLS:
            print(f"      {url}")
            for o in _scroll_and_parse(page, url):
                if o["url"] not in seen:
                    seen.add(o["url"])
                    all_.append(o)
        browser.close()

    print(f"   ✅ [traventia] {len(all_)} ofertas únicas")
    return all_
