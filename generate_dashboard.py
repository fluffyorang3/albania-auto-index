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

# Load raw data
df = pd.read_csv(HIST_FILE, parse_dates=["scrape_date"])

# Filter only Euro prices
df = df[df['price_currency'].str.upper() == 'EUR']

# Parse numeric year and price
df["year"]        = pd.to_numeric(df["year"], errors="coerce").astype('Int64')
df["price"]       = pd.to_numeric(df["price_value"].astype(str).str.replace(r"\D+", "", regex=True), errors="coerce")

# Parse mileage ranges: take lower bound
def parse_mileage(m):
    try:
        m = str(m)
        if '-' in m:
            low = m.split('-')[0]
        else:
            low = m
        return int(low.replace(' ', ''))
    except:
        return pd.NA

# original mileage string
df['mileage_raw'] = df['mileage']
df['mileage']     = df['mileage_raw'].apply(parse_mileage).astype('Int64')

# Drop rows missing core numeric fields
df = df.dropna(subset=["year", "price", "mileage"])

# Derive age
df["age"] = datetime.now().year - df["year"].astype(int)

# Summary metrics
total_listings    = len(df)
missing_price     = df['price_value'].isna().sum()
avg_price_overall = df['price'].mean()
avg_mileage       = df['mileage'].mean()
avg_age           = df['age'].mean()

# Fuel distribution & avg price by fuel
avg_price_fuel = df.groupby('fuel')['price'].mean()

# Top models by count & select top 8
top_models      = df['model'].value_counts().head(8)
models_for_curv = top_models.index

# Region mapping
def map_region(m):
    m = str(m).lower()
    if 'tir' in m: return 'Tirane'
    if 'dur' in m: return 'Durres'
    if 'vl'  in m: return 'Vlore'
    return 'Other'

df['region'] = df['municipality'].apply(map_region)
avg_region   = df.groupby('region')['price'].mean()

# Time series
daily_avg_price  = df.groupby(pd.Grouper(key='scrape_date', freq='D'))['price'].mean()
weekly_counts    = df.set_index('scrape_date').resample('W')['listing_url'].count()
weekly_avg_price = df.set_index('scrape_date').resample('W')['price'].mean()

# Export data CSVs
df.to_csv(os.path.join(OUT_DIR, 'historical_listings.csv'), index=False)
top_models.to_csv(os.path.join(OUT_DIR, 'top_models.csv'), header=['count'])
avg_price_fuel.to_csv(os.path.join(OUT_DIR, 'avg_price_by_fuel.csv'), header=['avg_price'])
avg_region.to_csv(os.path.join(OUT_DIR, 'avg_price_by_region.csv'), header=['avg_price'])
weekly_counts.to_csv(os.path.join(OUT_DIR, 'weekly_volume.csv'), header=['listings'])
weekly_avg_price.to_csv(os.path.join(OUT_DIR, 'weekly_avg_price.csv'), header=['avg_price'])
daily_avg_price.to_csv(os.path.join(OUT_DIR, 'daily_avg_price.csv'), header=['avg_price'])

# Charts
# Limit heatmap to top models to reduce crowding
pivot = df[df['model'].isin(models_for_curv)].pivot_table(
    index='model', columns='year', values='price', aggfunc='mean'
).fillna(0)

plt.figure(figsize=(8,6))
plt.imshow(pivot, aspect='auto', origin='lower', cmap='magma')
plt.colorbar(label='Avg Price (EUR)')
plt.yticks(range(len(pivot.index)), pivot.index)
plt.xticks(range(len(pivot.columns)), pivot.columns, rotation=45)
plt.title('Avg Price by Model & Year (Top 8 Models)')
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'heatmap_model_year.png'))
plt.close()

# Depreciation curve
plt.figure(figsize=(8,5))
for model in models_for_curv:
    series = df[df['model']==model].groupby('age')['price'].mean()
    plt.plot(series.index, series.values, marker='o', label=model)
plt.xlabel('Age (years)')
plt.ylabel('Avg Price (EUR)')
plt.title('Depreciation Curve – Top Models')
plt.legend(loc='upper right', fontsize='small')
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'depreciation_top.png'))
plt.close()

# Listings volume over time
plt.figure(figsize=(8,4))
weekly_counts.plot()
plt.ylabel('Listings')
plt.title('Weekly Listing Volume')
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'volume_over_time.png'))
plt.close()

# Weekly avg price
plt.figure(figsize=(8,4))
weekly_avg_price.plot()
plt.ylabel('Avg Price (EUR)')
plt.title('Weekly Avg Price')
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'weekly_avg_price.png'))
plt.close()

# Build modern HTML
now = datetime.now().strftime('%Y-%m-%d %H:%M')
html = f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Auto Listings Dashboard</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
  <style>
    body {{ font-family:'Inter',sans-serif; background:#f5f5f5; color:#333; margin:0; padding:1rem; }}
    header {{ text-align:center; margin-bottom:2rem; }}
    header h1 {{ margin:0; font-weight:600; }}
    .metrics {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:1rem; margin-bottom:2rem; }}
    .card {{ background:#fff; padding:1rem; border-radius:8px; box-shadow:0 1px 4px rgba(0,0,0,0.1); }}
    .card h2 {{ margin:0 0 .5rem; font-size:1.1rem; font-weight:600; }}
    img {{ max-width:100%; border-radius:4px; margin-bottom:2rem; }}
    table {{ width:100%; border-collapse:collapse; margin-bottom:2rem; }}
    th,td {{ padding:.75rem; border-bottom:1px solid #eee; text-align:left; }}
    th {{ background:#fafafa; font-weight:600; }}
    ul {{ list-style:none; padding:0; }}
    ul li {{ margin:.5rem 0; }}
  </style>
</head>
<body>
  <header>
    <h1>Auto Listings Dashboard</h1>
    <p>Generated: {now}</p>
  </header>

  <section class="metrics">
    <div class="card"><h2>Total Listings</h2><p>{total_listings}</p></div>
    <div class="card"><h2>Avg Price (EUR)</h2><p>{avg_price_overall:,.0f}</p></div>
    <div class="card"><h2>Avg Mileage</h2><p>{avg_mileage:,.0f}</p></div>
    <div class="card"><h2>Avg Age</h2><p>{avg_age:.1f}</p></div>
    <div class="card"><h2>Missing Prices</h2><p>{missing_price}</p></div>
  </section>

  <section>
    <h2>Avg Price by Model & Year</h2>
    <img src="heatmap_model_year.png" alt="Heatmap">
  </section>

  <section>
    <h2>Depreciation Curve – Top Models</h2>
    <img src="depreciation_top.png" alt="Depreciation">
  </section>

  <section>
    <h2>Weekly Listing Volume</h2>
    <img src="volume_over_time.png" alt="Volume Over Time">
  </section>

  <section>
    <h2>Weekly Avg Price</h2>
    <img src="weekly_avg_price.png" alt="Weekly Avg Price">
  </section>

  <section>
    <h2>Download Data</h2>
    <ul>
      <li><a href="historical_listings.csv">historical_listings.csv</a></li>
      <li><a href="daily_avg_price.csv">daily_avg_price.csv</a></li>
      <li><a href="weekly_volume.csv">weekly_volume.csv</a></li>
      <li><a href="weekly_avg_price.csv">weekly_avg_price.csv</a></li>
      <li><a href="avg_price_model_year.csv">avg_price_model_year.csv</a></li>
      <li><a href="top_models.csv">top_models.csv</a></li>
      <li><a href="avg_price_by_fuel.csv">avg_price_by_fuel.csv</a></li>
      <li><a href="avg_price_by_region.csv">avg_price_by_region.csv</a></li>
    </ul>
  </section>

</body>
</html>'''

# Write file
with open(REPORT, "w", encoding="utf-8") as f:
    f.write(html)

print(f"✅ Dashboard updated: {REPORT}")
