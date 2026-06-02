"""
scrapers/weekendesk.py — Weekendesk con paginación automática
"""

import re
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from parsers import (
    clean_text, parse_price, enrich_destination,
    extract_tipo_viaje, extract_estrellas, extract_pension,
    extract_extras, extract_noches,
)

FUENTE   = "weekendesk"
BASE_URL = "https://www.weekendesk.es"

# URLs base — el scraper detecta automáticamente cuántas páginas hay
BASE_URLS = [
    "https://www.weekendesk.es/escapadas/CNT2_16VRS1_9/escapadas-fin-de-semana-Espana",
    "https://www.weekendesk.es/tema/2qrk/escapadas-fin-de-semana-Chollos",
    "https://www.weekendesk.es/tema/ccg/escapadas-fin-de-semana-spa",
    "https://www.weekendesk.es/tema/2gqg/escapadas-fin-de-semana-Ultima_hora",
]

MAX_PAGES = 10  # máximo de páginas a scrapeар por URL


def _build_page_url(base_url: str, page: int) -> str:
    """
    Genera la URL de una página específica.
    Página 0 → URL base sin parámetros
    Página 1+ → ?page=N (1, 2, 3...)
    """
    clean = base_url.split("#")[0].split("?")[0]
    if page == 0:
        return f"{clean}#country=42;a=2;c=0;b=0;sort=priceAsc"
    return f"{clean}?page={page}#country=42;a=2;c=0;b=0;sort=priceAsc"


def _parse_card(card) -> dict | None:
    link = (
        card.select_one("a[href*='/oferta-hoteles/']") or
        card.select_one("a[href*='/escapada/']") or
        card.select_one("a[href*='/hotel/']")
    )
    if not link:
        return None
    href = link.get("href", "")
    if not href:
        return None
    url = href if href.startswith("http") else BASE_URL + href

    label_tag = card.select_one("[class*='label__'], [class*='_label']")
    titulo = clean_text(label_tag.get_text(strip=True)) if label_tag else ""
    hotel_name = clean_text(link.get_text(strip=True))
    if not titulo:
        titulo = hotel_name
    if not titulo:
        return None

    destino = ""
    slug_match = re.search(r"/oferta-hoteles/\d+/([^#?]+)", href)
    if slug_match:
        slug = slug_match.group(1)
        parts = slug.replace("_", " ").split("-")
        if len(parts) >= 2:
            destino = parts[-1].strip()
    if not destino:
        destino = hotel_name

    star_icons = card.select("span[class*='star__'], span[class*='_star__']")
    n_stars = sum(1 for s in star_icons if any("star" in c for c in (s.get("class") or [])))
    estrellas = f"{n_stars}★" if n_stars > 0 else extract_estrellas(titulo)

    price_text = None
    price_tag = card.select_one("[class*='sellPrice']")
    if price_tag:
        price_text = price_tag.get_text(separator="", strip=True).replace("\xa0", "")
    if not price_text:
        price_tag = card.select_one("[class*='price__'], [class*='Price__']")
        if price_tag:
            price_text = price_tag.get_text(separator="", strip=True).replace("\xa0", "")
    if not price_text:
        for tag in card.find_all(string=re.compile(r"^\d+$")):
            next_s = tag.find_next(string=re.compile(r"€"))
            if next_s:
                price_text = tag.strip() + "€"
                break

    img_tag = card.select_one("img[src*='weekendesk'], img[src*='booking']")
    if not img_tag:
        img_tag = card.select_one("img")
    imagen = None
    if img_tag:
        imagen = img_tag.get("src") or img_tag.get("data-src")
        if not imagen or not imagen.startswith("http"):
            alt = img_tag.get("alt", "")
            if alt.startswith("http"):
                imagen = alt

    combined = titulo + " " + destino + " " + hotel_name
    region, pais, tipo_clima = enrich_destination(combined)

    pension = extract_pension(combined)
    if pension == "Sin especificar":
        pension = "Desayuno"

    return {
        "url":             url,
        "fuente":          FUENTE,
        "titulo":          titulo,
        "destino":         destino,
        "region":          region,
        "pais":            pais,
        "tipo_clima":      tipo_clima,
        "tipo_viaje":      extract_tipo_viaje(combined),
        "estrellas":       estrellas,
        "pension":         pension,
        "extras":          extract_extras(combined),
        "precio":          parse_price(price_text) if price_text else None,
        "moneda":          "EUR",
        "precio_por":      "noche",
        "imagen_url":      imagen,
        "duracion_noches": extract_noches(combined),
        "adultos_min":     2,
    }


def _parse_html(html: str) -> list[dict]:
    soup  = BeautifulSoup(html, "html.parser")
    cards = soup.select("article") or soup.select("div[class*='card']")
    offers = []
    for card in cards:
        if not card.select_one("a[href*='/oferta-hoteles/'], a[href*='/escapada/']"):
            continue
        o = _parse_card(card)
        if o and o.get("titulo"):
            offers.append(o)
    return offers


def _scrape_url_with_pagination(page, base_url: str, seen: set) -> list[dict]:
    """Scrapea una URL y todas sus páginas."""
    all_offers = []

    for page_num in range(MAX_PAGES):
        url = _build_page_url(base_url, page_num)
        print(f"      {url}")
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            try:
                page.wait_for_selector("article", timeout=12000)
            except Exception:
                pass

            # Scroll para lazy load
            prev = 0
            for _ in range(8):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(1200)
                curr = page.locator("article").count()
                if curr == prev:
                    break
                prev = curr

            offers = _parse_html(page.content())

            # Si no hay ofertas nuevas, hemos llegado al final
            new_offers = [o for o in offers if o["url"] not in seen]
            if not new_offers:
                print(f"      → 0 nuevas, fin de paginación")
                break

            for o in new_offers:
                seen.add(o["url"])
                all_offers.append(o)

            print(f"      → {len(new_offers)} nuevas ({len(offers)} total en página)")

            # Si hay menos de 10 ofertas, probablemente es la última página
            if len(offers) < 10:
                break

        except Exception as e:
            print(f"      ❌ {url}: {e}")
            break

    return all_offers


def scrape() -> list[dict]:
    seen  = set()
    all_  = []

    print(f"   🔍 [weekendesk] cargando con Playwright...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page    = browser.new_page()
        page.set_extra_http_headers({
            "Accept-Language": "es-ES,es;q=0.9",
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
        })

        for base_url in BASE_URLS:
            offers = _scrape_url_with_pagination(page, base_url, seen)
            all_.extend(offers)

        browser.close()

    print(f"   ✅ [weekendesk] {len(all_)} ofertas únicas")
    return all_
