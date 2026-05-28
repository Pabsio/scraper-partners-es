"""
scrapers/buscounchollo.py
Scrapea https://www.buscounchollo.com (carga JS con React → Playwright)

Estructura real de las tarjetas:
  <article>
    <a href="/reserva-chollo/ID/slug">  ← enlace principal
    <picture><img ...>                  ← imagen
    <h2> Título </h2>
    <span class="*price*"> 99€ </span>
"""

import re
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from parsers import (
    clean_text, parse_price, enrich_destination,
    extract_tipo_viaje, extract_estrellas, extract_pension,
    extract_extras, extract_noches,
)

FUENTE   = "buscounchollo"
BASE_URL = "https://www.buscounchollo.com"

SCRAPE_URLS = [
    "https://www.buscounchollo.com/",
    "https://www.buscounchollo.com/top-chollos/",
    "https://www.buscounchollo.com/tematicos/chollos-playa/1/",
    "https://www.buscounchollo.com/tematicos/chollos-toboganes/155/",
    "https://www.buscounchollo.com/regimenes/todo-incluido/169/",
]


def _parse_card(card) -> dict | None:
    # ── Enlace principal ──────────────────────────────────────────────────────
    # BuscoUnChollo usa /reserva-chollo/ o /chollo/
    link = (
        card.select_one("a[href*='/reserva-chollo/']") or
        card.select_one("a[href*='/chollo/']") or
        card.select_one("a[href]")
    )
    if not link:
        return None
    href = link.get("href", "")
    if not href or href in ("#", "/"):
        return None
    url = href if href.startswith("http") else BASE_URL + href

    # ── Título ────────────────────────────────────────────────────────────────
    title_tag = (
        card.select_one("h2") or
        card.select_one("h3") or
        card.select_one("[class*='title']") or
        card.select_one("[class*='nombre']")
    )
    titulo = clean_text(title_tag.get_text(strip=True)) if title_tag else ""

    # Si no hay h2/h3, intentar sacar del atributo alt de la imagen
    if not titulo:
        img = card.select_one("img")
        if img:
            titulo = clean_text(img.get("alt", ""))
    if not titulo:
        return None

    # ── Precio ────────────────────────────────────────────────────────────────
    # BuscoUnChollo: <span class="chollo-price">399</span> <span>&nbsp;€</span>
    price_text = None

    # 1. Clase exacta chollo-price
    price_tag = card.select_one("span.chollo-price")
    if price_tag:
        price_text = price_tag.get_text(strip=True) + "€"

    # 2. Fallback: clases genéricas con "price"
    if not price_text:
        price_tag = card.select_one(
            "[class*='price'], [class*='Price'], [class*='precio'], "
            "[class*='amount'], [class*='Amount'], [class*='coste']"
        )
        if price_tag:
            price_text = price_tag.get_text(strip=True)

    # 3. Fallback: número justo antes de un nodo con €
    if not price_text:
        for tag in card.find_all(string=re.compile(r"^\s*€\s*$")):
            prev = tag.find_previous(string=re.compile(r"\d+"))
            if prev:
                price_text = prev.strip() + "€"
                break

    # ── Destino ───────────────────────────────────────────────────────────────
    dest_tag = card.select_one(
        "[class*='destination'], [class*='Destination'], "
        "[class*='destino'], [class*='location'], [class*='Location'], "
        "[class*='city'], [class*='lugar']"
    )
    destino = clean_text(dest_tag.get_text(strip=True)) if dest_tag else ""
    if not destino:
        destino = titulo  # extraer del título como fallback

    # ── Imagen ────────────────────────────────────────────────────────────────
    img_tag = card.select_one("img")
    imagen = None
    if img_tag:
        imagen = (
            img_tag.get("src") or
            img_tag.get("data-src") or
            img_tag.get("data-lazy-src") or
            img_tag.get("srcset", "").split(" ")[0]
        )
        if imagen and imagen.startswith("//"):
            imagen = "https:" + imagen

    combined = titulo + " " + destino
    region, pais, tipo_clima = enrich_destination(combined)

    return {
        "url":             url,
        "fuente":          FUENTE,
        "titulo":          titulo,
        "destino":         destino,
        "region":          region,
        "pais":            pais,
        "tipo_clima":      tipo_clima,
        "tipo_viaje":      extract_tipo_viaje(combined),
        "estrellas":       extract_estrellas(combined),
        "pension":         extract_pension(combined),
        "extras":          extract_extras(combined),
        "precio":          parse_price(price_text) if price_text else None,
        "moneda":          "EUR",
        "precio_por":      "persona",
        "imagen_url":      imagen,
        "duracion_noches": extract_noches(combined),
        "adultos_min":     2,
    }


def _parse_html(html: str) -> list[dict]:
    soup   = BeautifulSoup(html, "html.parser")
    offers = []

    # Tarjetas principales: <article>
    cards = soup.select("article")

    # Fallback si no hay article
    if not cards:
        cards = (
            soup.select("div[class*='offer-card'], div[class*='OfferCard']") or
            soup.select("div[class*='chollo-card'], div[class*='CholloCard']") or
            soup.select("a[href*='/reserva-chollo/']")
        )

    for card in cards:
        o = _parse_card(card)
        if o and o.get("titulo"):
            offers.append(o)

    return offers


def scrape() -> list[dict]:
    seen  = set()
    all_  = []

    print(f"   🔍 [buscounchollo] cargando con Playwright...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page    = browser.new_page()
        page.set_extra_http_headers({"Accept-Language": "es-ES,es;q=0.9"})

        for url in SCRAPE_URLS:
            print(f"      {url}")
            try:
                page.goto(url, wait_until="networkidle", timeout=30000)

                # Esperar a que aparezcan los articles
                try:
                    page.wait_for_selector("article", timeout=12000)
                except Exception:
                    pass

                # Scroll para cargar lazy-load
                prev = 0
                for _ in range(10):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(1500)
                    curr = page.locator("article").count()
                    if curr == prev:
                        break
                    prev = curr

                offers = _parse_html(page.content())
                for o in offers:
                    if o["url"] not in seen:
                        seen.add(o["url"])
                        all_.append(o)
                print(f"      → {len(offers)} ofertas")

            except Exception as e:
                print(f"      ❌ {url}: {e}")

        browser.close()

    print(f"   ✅ [buscounchollo] {len(all_)} ofertas únicas")
    return all_
