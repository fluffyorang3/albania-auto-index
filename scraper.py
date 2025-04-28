#!/usr/bin/env python3
import time
import csv
import requests
from bs4 import BeautifulSoup
from datetime import datetime

BASE_URL = "https://www.merrjep.al/njoftime/automjete/makina/ne-shitje"
PAGES = 20
OUTPUT_FILE = "today_listings.csv"

FIELDNAMES = [
    "scrape_date", "listing_url",
    "year", "transmission", "mileage", "fuel",
    "municipality", "color", "make", "model",
    "price_value", "price_currency"
]

def parse_listing(url):
    """Fetch details from a single listing page."""
    r = requests.get(url)
    soup = BeautifulSoup(r.text, "html.parser")
    data = {}
    # find all tag-item blocks
    for tag in soup.select(".tag-item"):
        label = tag.find("span").get_text(strip=True)
        value = tag.find("bdi").get_text(strip=True)
        if label.startswith("Viti"):
            data["year"] = value
        elif label.startswith("Transmetuesi"):
            data["transmission"] = value
        elif label.startswith("Kilometrazha"):
            data["mileage"] = value
        elif label.startswith("Karburanti"):
            data["fuel"] = value
        elif label.startswith("Komuna"):
            data["municipality"] = value
        elif label.startswith("Ngjyra"):
            data["color"] = value
        elif label.startswith("Prodhuesi"):
            data["make"] = value
        elif label.startswith("Modeli"):
            data["model"] = value
    # price
    price_elem = soup.select_one(".new-price .format-money-int")
    data["price_value"] = price_elem["value"] if price_elem else ""
    # currency is next span
    curr = soup.select_one(".new-price span:not(.format-money-int)")
    data["price_currency"] = curr.get_text(strip=True) if curr else ""
    return data

def main():
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for page in range(1, PAGES+1):
            pg_url = f"{BASE_URL}?Page={page}"
            print(f"Scraping page {page}…")
            r = requests.get(pg_url)
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.select("a.Link_vis"):
                href = a["href"]
                full_url = href if href.startswith("http") else "https://www.merrjep.al" + href
                print(" →", full_url)
                details = parse_listing(full_url)
                row = {
                    "scrape_date": datetime.utcnow().isoformat(),
                    "listing_url": full_url,
                    **details
                }
                writer.writerow(row)
                time.sleep(1.0)   # be polite
            time.sleep(2.0)       # between pages

if __name__ == "__main__":
    main()
