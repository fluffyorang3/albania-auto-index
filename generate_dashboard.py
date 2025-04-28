#!/usr/bin/env python3
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import os

# -- configuration --
HIST_FILE = "historical_listings.csv"   # accumulated over time (append today_listings.csv daily)
OUT_DIR   = "docs"                      # GitHub Pages serves from here
REPORT    = os.path.join(OUT_DIR, "index.html")

# read data
df = pd.read_csv(HIST_FILE, parse_dates=["scrape_date"])
# normalize price
df["price"] = df["price_value"].astype(float)
# compute age
df["year"] = df["year"].astype(int)
df["age"] = datetime.now().year - df["year"]

# 1) Avg Price by Model & Year → Heatmap
pivot = df.pivot_table(
    index="model", columns="year", values="price",
    aggfunc="mean"
).fillna(0)

plt.figure(figsize=(10,6))
plt.imshow(pivot, aspect="auto", origin="lower")
plt.colorbar(label="Avg Price")
plt.yticks(range(len(pivot.index)), pivot.index)
plt.xticks(range(len(pivot.columns)), pivot.columns, rotation=45)
plt.title("Avg Price by Model & Year")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "heatmap_model_year.png"))
plt.close()

# 2) Depreciation Curve for Top 5 Models
top5 = df["model"].value_counts().head(5).index
plt.figure()
for model in top5:
    sub = df[df["model"]==model].groupby("age")["price"].mean()
    plt.plot(sub.index, sub.values, label=model)
plt.xlabel("Age (years)")
plt.ylabel("Avg Price")
plt.title("Depreciation Curve – Top 5 Models")
plt.legend()
plt.savefig(os.path.join(OUT_DIR, "depreciation_top5.png"))
plt.close()

# 3) Price Distribution Boxplots by Model/Year
# choose a handful of (model, year) with enough data
grouped = df.groupby(["model","year"])
samples = [grp["price"].values
           for (m,y),grp in grouped
           if (m in top5 and len(grp)>=10)]
labels  = [f"{m}-{y}" for (m,y),grp in grouped
           if (m in top5 and len(grp)>=10)]
plt.figure(figsize=(12,6))
plt.boxplot(samples, labels=labels, vert=True)
plt.xticks(rotation=90)
plt.title("Price Distribution (boxplots) for Top Models by Year")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "boxplots.png"))
plt.close()

# 4) Regional Comparison
regions = ["Tirane", "Durres", "Vlore"]
avg_region = df[df["municipality"].isin(regions)].groupby("municipality")["price"].mean()
plt.figure()
avg_region.plot(kind="bar")
plt.ylabel("Avg Price")
plt.title("Avg Price: Tirana vs Durrës vs Vlorë")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "regional_comparison.png"))
plt.close()

# 5) Listings Volume Over Time
daily_counts = df.set_index("scrape_date").resample("W")["listing_url"].count()
plt.figure()
daily_counts.plot()
plt.ylabel("Number of Listings Scraped")
plt.title("Listings Volume Over Time (weekly)")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "volume_over_time.png"))
plt.close()

# Finally, write a simple HTML report
with open(REPORT, "w", encoding="utf-8") as f:
    f.write(f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Auto Listings Dashboard</title></head><body>
<h1>Auto Listings Dashboard</h1>
<p>Generated: {datetime.now().isoformat()}</p>
<h2>1. Avg Price by Model & Year</h2>
<img src="heatmap_model_year.png" width="800"/>
<h2>2. Depreciation Curve – Top 5 Models</h2>
<img src="depreciation_top5.png" width="800"/>
<h2>3. Price Distribution Boxplots</h2>
<img src="boxplots.png" width="800"/>
<h2>4. Regional Comparison</h2>
<img src="regional_comparison.png" width="600"/>
<h2>5. Listings Volume Over Time</h2>
<img src="volume_over_time.png" width="800"/>
</body></html>""")
print("Dashboard generated to", REPORT)
