#!/usr/bin/env python3
import csv
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# ─── CONFIG ────────────────────────────────────────────────────────────────
BASE_URL     = "https://www.merrjep.al"
LISTING_PATH = "/njoftime/automjete/makina/ne-shitje"
PAGES        = 20
MAX_WORKERS  = 10
OUTPUT_FILE  = "today_listings.csv"

FIELDNAMES = [
    "scrape_date", "listing_url",
    "year", "transmission", "mileage", "fuel",
    "municipality", "color", "make", "model",
    "price_value", "price_currency"
]
# ────────────────────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/115.0.0.0 Safari/537.36"
    )
}

def parse_detail(session, href):
    """Fetch and parse a single listing detail page."""
    url = href if href.startswith("http") else BASE_URL + href
    resp = session.get(url, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    data = {}
    # attributes
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

    # price
    price_elem = soup.select_one(".new-price .format-money-int")
    data["price_value"]    = price_elem["value"] if price_elem else ""
    curr_elem              = soup.select_one(".new-price span:not(.format-money-int)")
    data["price_currency"] = curr_elem.get_text(strip=True) if curr_elem else ""
    return url, data

def scrape_page(session, page_num, total_bar):
    """Get all listing URLs on one page, then fetch details in parallel."""
    page_url = f"{BASE_URL}{LISTING_PATH}?Page={page_num}"
    r = session.get(page_url, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    links = [a["href"] for a in soup.select("a.Link_vis")]

    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as exec:
        futures = {
            exec.submit(parse_detail, session, href): href
            for href in links
        }
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
                tqdm.write(f"[Page {page_num}] error fetching {futures[fut]}: {e}")

    return results

def main():
    # ensure output dir exists
    os.makedirs(os.path.dirname(OUTPUT_FILE) or ".", exist_ok=True)

    # open CSV writer
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()

        # estimate total listings = PAGES * ~50
        estimated_total = PAGES * 50
        total_bar = tqdm(total=estimated_total, desc="Total", unit="lst")

        # use one session for all requests
        session = requests.Session()
        session.headers.update(HEADERS)

        for page in range(1, PAGES + 1):
            try:
                page_results = scrape_page(session, page, total_bar)
                for url, details in page_results:
                    row = {
                        "scrape_date": datetime.utcnow().isoformat(),
                        "listing_url": url,
                        **details
                    }
                    writer.writerow(row)
            except Exception as e:
                tqdm.write(f"[Page {page}] failed completely: {e}")

        total_bar.close()
    print(f"✅ Done — wrote {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
