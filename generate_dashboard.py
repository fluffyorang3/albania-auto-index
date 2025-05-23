# generate_dashboard.py
#!/usr/bin/env python3
import pandas as pd
import matplotlib.pyplot as plt
import os
import numpy as np
from datetime import datetime

# ─── CONFIG ────────────────────────────────────────────────────────────────
HIST_FILE = "historical_listings.csv"
OUT_DIR   = "docs"
REPORT    = os.path.join(OUT_DIR, "index.html")
# ───────────────────────────────────────────────────────────────────────────

# Ensure output directory exists
os.makedirs(OUT_DIR, exist_ok=True)

# Load raw data
df = pd.read_csv(HIST_FILE, parse_dates=["scrape_date"])

# Filter only Euro prices
df = df[df['price_currency'].str.upper() == 'EUR']

# Parse numeric year and price
df["year"]  = pd.to_numeric(df["year"], errors="coerce").astype('Int64')
df["price"] = pd.to_numeric(df["price_value"], errors="coerce")

# Parse mileage ranges: take lower bound
def parse_mileage(m):
    try:
        m = str(m)
        low = m.split('-')[0] if '-' in m else m
        return int(low.replace(' ', ''))
    except:
        return pd.NA

df['mileage'] = df['mileage'].apply(parse_mileage).astype('Int64')

# Drop rows missing core numeric fields
df = df.dropna(subset=["year", "price", "mileage"]).copy()

# Filter out unrealistic price outliers using IQR
Q1 = df['price'].quantile(0.25)
Q3 = df['price'].quantile(0.75)
IQR = Q3 - Q1
lower_bound = max(Q1 - 1.5 * IQR, 0)
upper_bound = Q3 + 1.5 * IQR
df = df[(df['price'] >= lower_bound) & (df['price'] <= upper_bound)].copy()

# Derive age
df["age"] = datetime.now().year - df["year"].astype(int)

# ─── SUMMARY METRICS ────────────────────────────────────────────────────────
total_listings  = len(df)
avg_price       = df['price'].mean()
avg_mileage     = df['mileage'].mean()
avg_age         = df['age'].mean()

# Price by fuel type
type_counts    = df['fuel'].value_counts()
avg_price_fuel = df.groupby('fuel')['price'].mean()

# Top models by count
top_models         = df['model'].value_counts().head(20)
models_for_heatmap = top_models.index

# Region mapping
def map_region(m):
    m = str(m).lower()
    if 'tir' in m:
        return 'Tirane'
    if 'dur' in m:
        return 'Durres'
    if 'vl' in m:
        return 'Vlore'
    return 'Other'

df['region']        = df['municipality'].apply(map_region)
avg_price_region   = df.groupby('region')['price'].mean()
count_region       = df['region'].value_counts()

# Time series
daily_counts      = df.set_index('scrape_date').resample('D')['listing_url'].count()
daily_avg_price   = df.set_index('scrape_date').resample('D')['price'].mean()
monthly_counts    = df.set_index('scrape_date').resample('M')['listing_url'].count()
monthly_avg_price = df.set_index('scrape_date').resample('M')['price'].mean()

# Top municipalities
top_munis = df.groupby('municipality')['price'].mean().sort_values(ascending=False).head(10)

# ─── PERCENTAGES ─────────────────────────────────────────────────────────────
model_pct   = top_models     / total_listings * 100
fuel_pct    = type_counts    / total_listings * 100
region_pct  = count_region   / total_listings * 100
daily_pct   = daily_counts   / total_listings * 100
monthly_pct = monthly_counts / total_listings * 100

# ─── EXPORT DATA ───────────────────────────────────────────────────────────
df.to_csv(os.path.join(OUT_DIR, 'historical_listings.csv'), index=False)
top_models.to_csv(os.path.join(OUT_DIR, 'top_models.csv'), header=['count'])
avg_price_fuel.to_csv(os.path.join(OUT_DIR, 'avg_price_by_fuel.csv'), header=['avg_price'])
avg_price_region.to_csv(os.path.join(OUT_DIR, 'avg_price_by_region.csv'), header=['avg_price'])
count_region.to_csv(os.path.join(OUT_DIR, 'count_by_region.csv'), header=['count'])
daily_counts.to_csv(os.path.join(OUT_DIR, 'daily_volume.csv'), header=['count'])
daily_avg_price.to_csv(os.path.join(OUT_DIR, 'daily_avg_price.csv'), header=['avg_price'])
monthly_counts.to_csv(os.path.join(OUT_DIR, 'monthly_volume.csv'), header=['count'])
monthly_avg_price.to_csv(os.path.join(OUT_DIR, 'monthly_avg_price.csv'), header=['avg_price'])
top_munis.to_csv(os.path.join(OUT_DIR, 'top_municipalities.csv'), header=['avg_price'])

# ─── EXPORT PERCENTAGE DATA ─────────────────────────────────────────────────
model_pct.to_csv(os.path.join(OUT_DIR, 'top_models_pct.csv'), header=['percent'])
fuel_pct.to_csv(os.path.join(OUT_DIR, 'fuel_distribution_pct.csv'), header=['percent'])
region_pct.to_csv(os.path.join(OUT_DIR, 'count_by_region_pct.csv'), header=['percent'])
daily_pct.to_csv(os.path.join(OUT_DIR, 'daily_volume_pct.csv'), header=['percent'])
monthly_pct.to_csv(os.path.join(OUT_DIR, 'monthly_volume_pct.csv'), header=['percent'])

# ─── CHARTS ─────────────────────────────────────────────────────────────────
# Heatmap: Avg price by model & year
pivot = df[df['model'].isin(models_for_heatmap)].pivot_table(
    index='model', columns='year', values='price', aggfunc='mean'
).reindex(models_for_heatmap)
plt.figure(figsize=(10,8))
plt.imshow(pivot, aspect='auto', origin='lower', cmap='magma')
plt.colorbar(label='Avg Price (EUR)')
plt.yticks(range(len(pivot.index)), pivot.index)
plt.xticks(range(len(pivot.columns)), pivot.columns, rotation=45)
plt.title('Avg Price by Model & Year (Top 20 Models)')
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'heatmap_model_year.png'))
plt.close()

# Depreciation curves for top 8 models
plt.figure(figsize=(10,6))
for model in top_models.head(8).index:
    series = df[df['model'] == model].groupby('age')['price'].mean()
    plt.plot(series.index, series.values, marker='o', label=model)
plt.xlabel('Age (years)')
plt.ylabel('Avg Price (EUR)')
plt.title('Depreciation Curve – Top 8 Models')
plt.legend(fontsize='small')
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'depreciation_top8.png'))
plt.close()

# Historical avg price – Top 10 Models (monthly)
model_monthly = (
    df[df['model'].isin(top_models.index)]
      .set_index('scrape_date')
      .groupby([pd.Grouper(freq='M'), 'model'])['price']
      .mean()
      .unstack()
      .reindex(columns=top_models.index)
)

plt.figure(figsize=(12,8))
for m in top_models.index:
    s = model_monthly[m]
    plt.plot(s.index, s.values, marker='o', label=m)
plt.xlabel('Date')
plt.ylabel('Avg Price (EUR)')
plt.title('Historical Avg Price – Top 10 Models')
plt.legend(fontsize='small', ncol=2)
plt.xlim(model_monthly.index.min(), model_monthly.index.max())
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'historical_avg_price_top10.png'))
plt.close()

# Price by region bar chart
plt.figure(figsize=(8,6))
avg_price_region.plot(kind='bar')
plt.ylabel('Avg Price (EUR)')
plt.title('Avg Price by Region')
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'regional_price.png'))
plt.close()

# Mileage distribution
plt.figure(figsize=(8,4))
df['mileage'].plot(kind='hist', bins=30)
plt.xlabel('Mileage (km)')
plt.title('Mileage Distribution')
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'mileage_hist.png'))
plt.close()

# Fuel type distribution
plt.figure(figsize=(6,4))
type_counts.plot(kind='bar')
plt.ylabel('Count')
plt.title('Listings by Fuel Type')
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'fuel_counts.png'))
plt.close()

# Monthly trends
plt.figure(figsize=(8,4))
monthly_counts.plot()
plt.ylabel('Count')
plt.title('Monthly Listing Volume')
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'monthly_volume.png'))
plt.close()

plt.figure(figsize=(8,4))
monthly_avg_price.plot()
plt.ylabel('Avg Price (EUR)')
plt.title('Monthly Avg Price')
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'monthly_avg_price.png'))
plt.close()

# ─── BUILD HTML REPORT ───────────────────────────────────────────────────────
now = datetime.now().strftime('%Y-%m-%d %H:%M')
html = f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Auto Listings Dashboard</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
  <style>
    body {{ font-family:'Inter',sans-serif; background:#f0f2f5; color:#333; margin:0; }}
    .container {{ max-width:1200px; margin:0 auto; padding:1rem; }}
    header {{ text-align:center; margin-bottom:2rem; }}
    header h1 {{ margin:0; font-weight:600; }}
    .metrics {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:1rem; margin-bottom:2rem; }}
    .card {{ background:#fff; padding:1rem; border-radius:8px; box-shadow:0 1px 4px rgba(0,0,0,0.1); }}
    .card h2 {{ margin:0 0 .5rem; font-size:1rem; font-weight:600; }}
    img {{ max-width:100%; border-radius:6px; margin-bottom:1.5rem; }}
    section {{ margin-bottom:2rem; }}
    h2.section-title {{ font-size:1.2rem; margin-bottom:.5rem; }}
    table {{ width:100%; border-collapse:collapse; margin-bottom:1rem; }}
    th, td {{ padding:.5rem; border-bottom:1px solid #e0e0e0; text-align:left; }}
    th {{ background:#fafafa; font-weight:600; }}
    ul {{ list-style:none; padding:0; }}
    ul li {{ margin:.4rem 0; }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>Auto Listings Dashboard</h1>
      <p>{now}</p>
    </header>

    <div class="metrics">
      <div class="card"><h2>Total Listings</h2><p>{total_listings}</p></div>
      <div class="card"><h2>Avg Price (EUR)</h2><p>{avg_price:,.0f}</p></div>
      <div class="card"><h2>Avg Mileage (km)</h2><p>{avg_mileage:,.0f}</p></div>
      <div class="card"><h2>Avg Age (yrs)</h2><p>{avg_age:.1f}</p></div>
    </div>

    <section>
      <h2 class="section-title">Avg Price by Model & Year</h2>
      <img src="heatmap_model_year.png">
      <table>
        <tr><th>Model</th><th>Percentage</th></tr>
        {''.join(f'<tr><td>{m}</td><td>{model_pct[m]:.1f}%</td></tr>' for m in model_pct.index)}
      </table>
    </section>

    <section>
      <h2 class="section-title">Depreciation Curve – Top 8 Models</h2>
      <img src="depreciation_top8.png">
    </section>

    <section>
  <h2 class="section-title">Historical Avg Price – Top 10 Models</h2>
    <img src="historical_avg_price_top10.png">
  </section>


    <section>
      <h2 class="section-title">Avg Price by Region</h2>
      <img src="regional_price.png">
      <table>
        <tr><th>Region</th><th>Avg Price</th><th>Percentage</th></tr>
        {''.join(f'<tr><td>{r}</td><td>{avg_price_region[r]:,.0f}</td><td>{region_pct[r]:.1f}%</td></tr>' for r in region_pct.index)}
      </table>
    </section>

    <section>
      <h2 class="section-title">Fuel Type Distribution</h2>
      <img src="fuel_counts.png">
      <table>
        <tr><th>Fuel</th><th>Avg Price</th><th>Percentage</th></tr>
        {''.join(f'<tr><td>{fuel}</td><td>{avg_price_fuel[fuel]:,.0f}</td><td>{fuel_pct[fuel]:.1f}%</td></tr>' for fuel in fuel_pct.index)}
      </table>
    </section>

    <section>
      <h2 class="section-title">Mileage Distribution</h2>
      <img src="mileage_hist.png">
    </section>

    <section>
      <h2 class="section-title">Monthly Trends</h2>
      <img src="monthly_volume.png">
      <img src="monthly_avg_price.png">
      <table>
        <tr><th>Month</th><th>Percentage</th><th>Avg Price</th></tr>
        {''.join(f"<tr><td>{idx.strftime('%Y-%m')}</td><td>{monthly_pct[idx]:.1f}%</td><td>{monthly_avg_price[idx]:,.0f}</td></tr>" for idx in monthly_pct.index[-6:])}
      </table>
    </section>

    

    <section>
      <h2 class="section-title">Download Data</h2>
      <ul>
        <li><a href="historical_listings.csv">historical_listings.csv</a></li>
        <li><a href="top_models.csv">top_models.csv</a></li>
        <li><a href="avg_price_by_fuel.csv">avg_price_by_fuel.csv</a></li>
        <li><a href="avg_price_by_region.csv">avg_price_by_region.csv</a></li>
        <li><a href="count_by_region.csv">count_by_region.csv</a></li>
        <li><a href="daily_volume.csv">daily_volume.csv</a></li>
        <li><a href="daily_avg_price.csv">daily_avg_price.csv</a></li>
        <li><a href="monthly_volume.csv">monthly_volume.csv</a></li>
        <li><a href="monthly_avg_price.csv">monthly_avg_price.csv</a></li>
        <li><a href="top_municipalities.csv">top_municipalities.csv</a></li>
        <li><a href="top_models_pct.csv">top_models_pct.csv</a></li>
        <li><a href="fuel_distribution_pct.csv">fuel_distribution_pct.csv</a></li>
        <li><a href="count_by_region_pct.csv">count_by_region_pct.csv</a></li>
        <li><a href="daily_volume_pct.csv">daily_volume_pct.csv</a></li>
        <li><a href="monthly_volume_pct.csv">monthly_volume_pct.csv</a></li>
      </ul>
    </section>

  </div>
</body>
</html>'''

with open(REPORT, "w", encoding="utf-8") as f:
    f.write(html)

print(f"✅ Dashboard updated: {REPORT}")
