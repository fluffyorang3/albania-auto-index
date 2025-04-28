#!/usr/bin/env python3
import time
import csv
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from tqdm import tqdm

BASE_URL    = "https://www.merrjep.al/njoftime/automjete/makina/ne-shitje"
PAGES       = 20
OUTPUT_FILE = "today_listings.csv"

FIELDNAMES = [
    "scrape_date", "listing_url",
    "year", "transmission", "mileage", "fuel",
    "municipality", "color", "make", "model",
    "price_value", "price_currency"
]

def parse_listing(url):
    r    = requests.get(url)
    soup = BeautifulSoup(r.text, "html.parser")
    data = {}
    # tag-item blocks
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
    return data

def main():
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()

        # Page‐level progress
        for page in tqdm(range(1, PAGES+1), desc="Pages", unit="page"):
            pg_url = f"{BASE_URL}?Page={page}"
            resp   = requests.get(pg_url)
            soup   = BeautifulSoup(resp.text, "html.parser")
            links  = soup.select("a.Link_vis")

            # Listing‐level progress (≈50 per page)
            for a in tqdm(links, desc=f"Page {page} listings", unit="listing", leave=False):
                href = a["href"]
                url  = href if href.startswith("http") else "https://www.merrjep.al" + href

                details = parse_listing(url)
                # print spot-check line
                make  = details.get("make",    "?")
                model = details.get("model",   "?")
                year  = details.get("year",    "?")
                price = details.get("price_value", "?")
                curr  = details.get("price_currency", "")
                tqdm.write(f"{make} {model} ({year}) — {price} {curr}")

                row = {
                    "scrape_date":  datetime.utcnow().isoformat(),
                    "listing_url":  url,
                    **details
                }
                writer.writerow(row)

                time.sleep(1.0)   # be polite between detail requests
            time.sleep(2.0)       # be polite between pages

    print("✅ Scraping complete — wrote", OUTPUT_FILE)

if __name__ == "__main__":
    main()
