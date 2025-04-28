#!/usr/bin/env python3
import pandas as pd
import matplotlib.pyplot as plt
import os
from datetime import datetime

# ─── CONFIG ────────────────────────────────────────────────────────────────
HIST_FILE = "historical_listings.csv"
OUT_DIR   = "docs"
REPORT    = os.path.join(OUT_DIR, "index.html")
# ────────────────────────────────────────────────────────────────────────────

# Ensure output directory exists
os.makedirs(OUT_DIR, exist_ok=True)

# Load and clean data
df = pd.read_csv(HIST_FILE, parse_dates=["scrape_date"])
df["year"]        = pd.to_numeric(df["year"], errors="coerce")
df["price_value"] = pd.to_numeric(df["price_value"], errors="coerce")
df["mileage"]     = pd.to_numeric(
    df["mileage"].astype(str)
       .str.replace(r"\D+", "", regex=True),
    errors="coerce"
)
# Drop rows missing core numeric fields
df = df.dropna(subset=["year", "price_value"])
# Convert types and derive
df["year"]       = df["year"].astype(int)
df["price"]      = df["price_value"].astype(float)
df["age"]        = datetime.now().year - df["year"]

# ─── SUMMARY METRICS ────────────────────────────────────────────────────────
total_listings    = len(df)
missing_price     = df["price_value"].isna().sum()
avg_price_overall = df["price"].mean()
avg_mileage       = df["mileage"].mean()
avg_age           = df["age"].mean()

# Fuel distribution & avg price by fuel
fuel_counts    = df["fuel"].value_counts()
avg_price_fuel = df.groupby("fuel")["price"].mean()

# Top models by count
top_models = df["model"].value_counts()

# Top 5 models for depreciation curve
models_for_curve = top_models.head(5).index

# Region mapping
def map_region(m):
    m = str(m).lower()
    if "tir" in m:
        return "Tirane"
    if "dur" in m:
        return "Durres"
    if "vl" in m:
        return "Vlore"
    return "Other"

df["region"] = df["municipality"].apply(map_region)
avg_region    = df.groupby("region")["price"].mean()

# Time-series: daily & weekly
daily_avg_price  = df.groupby(pd.Grouper(key="scrape_date", freq="D"))["price"].mean()
weekly_counts    = df.set_index("scrape_date").resample("W")["listing_url"].count()
weekly_avg_price = df.set_index("scrape_date").resample("W")["price"].mean()

# ─── DATA EXPORTS ───────────────────────────────────────────────────────────
# Save raw and aggregated CSVs to docs/
df.to_csv(os.path.join(OUT_DIR, "historical_listings.csv"), index=False)
pivot = df.pivot_table(
    index="model", columns="year", values="price", aggfunc="mean"
).fillna(0)
pivot.to_csv(os.path.join(OUT_DIR, "avg_price_model_year.csv"))
avg_price_fuel.to_csv(
    os.path.join(OUT_DIR, "avg_price_by_fuel.csv"),
    header=["avg_price"],
)
avg_region.to_csv(
    os.path.join(OUT_DIR, "avg_price_by_region.csv"),
    header=["avg_price"],
)
weekly_counts.to_csv(
    os.path.join(OUT_DIR, "weekly_volume.csv"),
    header=["listings"],
)
weekly_avg_price.to_csv(
    os.path.join(OUT_DIR, "weekly_avg_price.csv"),
    header=["avg_price"],
)
top_models.to_csv(
    os.path.join(OUT_DIR, "top_models.csv"),
    header=["count"],
)
daily_avg_price.to_csv(
    os.path.join(OUT_DIR, "daily_avg_price.csv"),
    header=["avg_price"],
)

# ─── CHARTS ─────────────────────────────────────────────────────────────────
# 1) Heatmap: Avg Price by Model & Year
plt.figure(figsize=(10,6))
plt.imshow(pivot, aspect="auto", origin="lower")
plt.colorbar(label="Avg Price")
plt.yticks(range(len(pivot.index)), pivot.index)
plt.xticks(range(len(pivot.columns)), pivot.columns, rotation=45)
plt.title("Avg Price by Model & Year")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "heatmap_model_year.png"))
plt.close()

# 2) Depreciation Curve
plt.figure()
for model in models_for_curve:
    series = df[df["model"] == model].groupby("age")["price"].mean()
    plt.plot(series.index, series.values, marker='o', label=model)
plt.xlabel("Age (years)")
plt.ylabel("Avg Price")
plt.title("Depreciation Curve – Top 5 Models")
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "depreciation_top5.png"))
plt.close()

# 3) Price Distribution Boxplots
samples, labels = [], []
for (model, year), grp in df.groupby(["model", "year"]):
    if model in models_for_curve and len(grp) >= 10:
        samples.append(grp["price"].values)
        labels.append(f"{model}-{year}")
if samples:
    plt.figure(figsize=(12,6))
    plt.boxplot(samples, labels=labels, vert=True)
    plt.xticks(rotation=90)
    plt.title("Price Distribution for Top Models by Year")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "boxplots.png"))
    plt.close()

# 4) Regional Comparison
if not avg_region.empty:
    plt.figure()
    avg_region.plot(kind="bar")
    plt.ylabel("Avg Price")
    plt.title("Avg Price by Region")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "regional_comparison.png"))
    plt.close()

# 5) Listings Volume Over Time
if not weekly_counts.empty:
    plt.figure()
    weekly_counts.plot()
    plt.ylabel("Listings Scraped")
    plt.title("Listings Volume Over Time (weekly)")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "volume_over_time.png"))
    plt.close()

# 6) Weekly Avg Price Over Time
if not weekly_avg_price.empty:
    plt.figure()
    weekly_avg_price.plot(marker='o')
    plt.ylabel("Avg Price")
    plt.title("Weekly Average Price Over Time")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "weekly_avg_price.png"))
    plt.close()

# ─── BUILD HTML REPORT ───────────────────────────────────────────────────────
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
html = f"""<!doctype html>
<html><head><meta charset='utf-8'><title>Auto Listings Dashboard</title>
<style>
  body {{ font-family: sans-serif; padding:1rem; }}
  table {{ border-collapse: collapse; margin-bottom: 1rem; width:100%; }}
  th, td {{ border: 1px solid #ccc; padding: 0.5rem; text-align: left; }}
</style>
</head><body>
<h1>Auto Listings Dashboard</h1>
<p>Generated: {now}</p>

<h2>Summary Metrics</h2>
<table>
<tr><th>Total Listings</th><td>{total_listings}</td></tr>
<tr><th>Missing Price</th><td>{missing_price}</td></tr>
<tr><th>Average Price</th><td>{avg_price_overall:,.2f}</td></tr>
<tr><th>Average Mileage</th><td>{avg_mileage:,.0f}</td></tr>
<tr><th>Average Age</th><td>{avg_age:,.1f}</td></tr>
</table>

<h2>Top 10 Models by Count</h2>
<table>
<tr><th>Model</th><th>Count</th></tr>
{''.join(f'<tr><td>{m}</td><td>{c}</td></tr>' for m,c in top_models.head(10).items())}
</table>

<h2>Average Price by Fuel Type</h2>
<table>
<tr><th>Fuel</th><th>Avg Price</th></tr>
{''.join(f'<tr><td>{fuel}</td><td>{avg:,.2f}</td></tr>' for fuel,avg in avg_price_fuel.items())}
</table>

<h2>Average Price by Region</h2>
<img src="regional_comparison.png" width="600"/>
<table>
<tr><th>Region</th><th>Avg Price</th></tr>
{''.join(f'<tr><td>{r}</td><td>{p:,.2f}</td></tr>' for r,p in avg_region.items())}
</table>

<h2>Avg Price by Model & Year</h2>
<img src="heatmap_model_year.png" width="800"/>

<h2>Depreciation Curve – Top 5 Models</h2>
<img src="deprecation_top5.png" width="800"/>

<h2>Price Distribution Boxplots</h2>
<img src="boxplots.png" width="800"/>

<h2>Listings Volume Over Time</h2>
<img src="volume_over_time.png" width="800"/>
<table>
<tr><th>Week</th><th>Listings</th></tr>
{''.join(f"<tr><td>{idx.strftime('%Y-%m-%d')}</td><td>{cnt}</td></tr>" for idx,cnt in weekly_counts.tail(10).items())}
</table>

<h2>Weekly Average Price</h2>
<img src="weekly_avg_price.png" width="800"/>
<table>
<tr><th>Week</th><th>Avg Price</th></tr>
{''.join(f"<tr><td>{idx.strftime('%Y-%m-%d')}</td><td>{val:,.2f}</td></tr>" for idx,val in weekly_avg_price.tail(10).items())}
</table>

<h2>Download Data</h2>
<ul>
  <li><a href="historical_listings.csv">Full Scraped Data (CSV)</a></li>
  <li><a href="avg_price_model_year.csv">Avg Price by Model & Year (CSV)</a></li>
  <li><a href="top_models.csv">Top Models Counts (CSV)</a></li>
  <li><a href="avg_price_by_fuel.csv">Avg Price by Fuel Type (CSV)</a></li>
  <li><a href="avg_price_by_region.csv">Avg Price by Region (CSV)</a></li>
  <li><a href="weekly_volume.csv">Weekly Listings Volume (CSV)</a></li>
  <li><a href="weekly_avg_price.csv">Weekly Avg Price Over Time (CSV)</a></li>
  <li><a href="daily_avg_price.csv">Daily Avg Price Time Series (CSV)</a></li>
</ul>

</body></html>"""

with open(REPORT, "w", encoding="utf-8") as f:
    f.write(html)

print(f"✅ Dashboard (and data) generated to {REPORT}")