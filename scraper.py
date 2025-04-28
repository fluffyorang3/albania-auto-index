#!/usr/bin/env python3
import csv
import os
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# ─── CONFIG ────────────────────────────────────────────────────────────────
BASE_URL           = "https://www.merrjep.al"
LISTING_PATH       = "/njoftime/automjete/makina/ne-shitje"
PAGES              = 60   # now scraping 60 pages
CHUNK_SIZE         = 5
MAX_DETAIL_WORKERS = 10
OUTPUT_FILE        = "today_listings.csv"

FIELDNAMES = [
    "scrape_date", "listing_url", "year", "transmission", "mileage",
    "fuel", "municipality", "color", "make", "model",
    "price_value", "price_currency"
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/115.0.0.0 Safari/537.36"
    )
}
# ────────────────────────────────────────────────────────────────────────────

def get_with_retries(session, url, retries=3, backoff=2):
    """GET with retries on HTTP errors and exponential back-off."""
    for attempt in range(1, retries + 1):
        try:
            resp = session.get(url, timeout=10)
            resp.raise_for_status()
            return resp
        except requests.HTTPError as e:
            if attempt < retries:
                tqdm.write(f"[Retry {attempt}/{retries}] {url} → {e}; waiting {backoff}s")
                time.sleep(backoff)
                backoff *= 2
            else:
                raise

def parse_detail(session, href):
    """Fetch and parse a single listing’s details."""
    url = href if href.startswith("http") else BASE_URL + href
    resp = get_with_retries(session, url)
    soup = BeautifulSoup(resp.text, "html.parser")
    data = {}

    for tag in soup.select(".tag-item"):
        label = tag.find("span").get_text(strip=True)
        val   = tag.find("bdi").get_text(strip=True)
        if   label.startswith("Viti"):         data["year"]         = val
        elif label.startswith("Transmetuesi"): data["transmission"] = val
        elif label.startswith("Kilometrazha"): data["mileage"]      = val
        elif label.startswith("Karburanti"):   data["fuel"]         = val
        elif label.startswith("Komuna"):       data["municipality"] = val
        elif label.startswith("Ngjyra"):       data["color"]        = val
        elif label.startswith("Prodhuesi"):    data["make"]         = val
        elif label.startswith("Modeli"):       data["model"]        = val

    pe = soup.select_one(".new-price .format-money-int")
    data["price_value"]    = pe["value"] if pe else ""
    ce = soup.select_one(".new-price span:not(.format-money-int)")
    data["price_currency"] = ce.get_text(strip=True) if ce else ""

    return url, data

def scrape_page(session, page_num, total_bar):
    """Scrape listings on a single page in parallel."""
    page_url = f"{BASE_URL}{LISTING_PATH}?Page={page_num}"
    resp     = get_with_retries(session, page_url)
    soup     = BeautifulSoup(resp.text, "html.parser")
    hrefs    = [a["href"] for a in soup.select("a.Link_vis")]

    results = []
    with ThreadPoolExecutor(max_workers=MAX_DETAIL_WORKERS) as executor:
        futures = {executor.submit(parse_detail, session, href): href for href in hrefs}
        for fut in tqdm(as_completed(futures),
                        total=len(futures),
                        desc=f"Page {page_num}",
                        unit="lst",
                        leave=False):
            try:
                url, details = fut.result()
                total_bar.update(1)
                results.append((url, details))
            except Exception as e:
                tqdm.write(f"[Page {page_num}] detail error for {futures[fut]} → {e}")
    return results

def main():
    os.makedirs(os.path.dirname(OUTPUT_FILE) or ".", exist_ok=True)
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()

        estimated_total = PAGES * 50
        total_bar = tqdm(total=estimated_total, desc="Total Listings", unit="lst")

        for i in range(0, PAGES, CHUNK_SIZE):
            chunk = list(range(i+1, min(PAGES, i+CHUNK_SIZE)+1))
            session = requests.Session()
            session.headers.update(HEADERS)

            with ThreadPoolExecutor(max_workers=len(chunk)) as page_exec:
                futures = {page_exec.submit(scrape_page, session, pg, total_bar): pg for pg in chunk}
                for fut in as_completed(futures):
                    pg = futures[fut]
                    try:
                        for url, details in fut.result():
                            writer.writerow({
                                "scrape_date": datetime.utcnow().isoformat(),
                                "listing_url": url,
                                **details
                            })
                    except Exception as e:
                        tqdm.write(f"[Page {pg}] failed after retries → {e}")
            session.close()

        total_bar.close()
    print(f"✅ Done — wrote {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
