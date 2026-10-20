# Wind Turbine OEM Benchmark Dashboard

Combined Streamlit dashboard comparing Vestas, Nordex, Siemens Gamesa, Suzlon and GE (Vernova Wind).

## What This Dashboard Includes
- `OEM Briefing` (new)
  - Latest reported quarter for all five OEMs side by side (revenue growth, profit margin, book-to-bill, backlog and cover, guidance), converted to EUR.
  - Twelve auto-generated, number-backed findings and a watchlist (guidance, stale order lists, upcoming results).
- `OEM Intelligence Lab` (new, choose a section at the top)
  - `Momentum & Share`: share of announced MW, last-12-month and year-to-date momentum per OEM, a like-for-like cut-off date, order size and mega-order dependence.
  - `Reported vs Announced`: how much of company-reported order intake (MW) each order list captures (Vestas, Nordex).
  - `Price per MW` (new): rough EUR m per MW on two bases - company-reported order-intake price (Vestas, Nordex, Siemens Gamesa onshore to 2022) and revenue per delivered MW (Vestas, Nordex, Siemens Gamesa, Suzlon). GE does not disclose MW.
  - `Product Race`: average rotor and rating of ordered turbines, 150 m-plus rotor share, leading platforms.
  - `Market Battles`: largest markets with leader and runner-up, contested markets, continent mix, geographic concentration, country movers.
  - `Accounts`: customers that bought from more than one OEM, customer dependence.
  - `Financial Profile`: annual revenue, book-to-bill and margin in EUR.
  - `Data Quality`: freshness, undisclosed customers, unknown platforms, comparability notes.
- `Overall Economics`
  - Revenue and order-intake value comparisons (normalized to mEUR where possible).
  - Order backlog comparison where metrics are available.
  - Ordered MW and average order size over time.
- `Sizes and Service`
  - Rotor diameter min/avg/max over time.
  - Turbine MW rating min/avg/max over time.
  - Order size min/avg/max over time.
  - Service contract length min/avg/max over time.
- `Country/Region/Continent`
  - Continent split and evolution by OEM.
  - Top countries with OEM split.
  - OEM -> continent -> region -> country sunburst.
- `Existing Turbine Portfolio`
  - Curated model catalog from official OEM product pages.
  - Rotor vs rated MW scatter and size distributions.
  - Model table with source links.

## Data Inputs
Cross-OEM intelligence data (tracked in `data/`):
- `oem_latest_results.json`: latest reported quarter per OEM (company releases; sources listed per OEM).
- `nordex_reported_intake.json`: Nordex reported Projects order intake in MW (quarterly and annual).
- `price_inputs.json`: Nordex average selling price per MW (results releases) and Suzlon revenue and deliveries for the price comparison.
- `fx_annual.json`: average EUR/USD and EUR/INR per calendar year (ECB reference rates via Frankfurter); the latest year is year to date.

Primary cache files (included in this repo for deployment):
- `data_cache/vestas_parsed_data.pkl`
- `data_cache/nordex_parsed_data.pkl`
- `data_cache/sgre_parsed_data.pkl`
- `data_cache/suzlon_parsed_data.pkl`

Local fallback (for developer workflow):
- `../Vestas_sales/data_cache/vestas_parsed_data.pkl`
- `../nordex_sales/data_cache/nordex_parsed_data.pkl`
- `../SGRE_sales/data_cache/sgre_parsed_data.pkl`
- `../Suzlon_sales/data_cache/suzlon_parsed_data.pkl`

Turbine product catalog:
- `data/oem_turbine_catalog.json`

## Build/Refresh Turbine Catalog From Official Pages
```powershell
python build_turbine_catalog.py
```

Sources used in builder:
- Vestas onshore/offshore product pages
- Nordex product main page
- Siemens Gamesa onshore/offshore pages
- Suzlon S-series turbine pages

## Refresh
```powershell
python tools/sync_caches.py     # copy the latest parsed caches from the per-OEM projects (Vestas from Vestas_sales_claude)
python -m pytest tests -q       # tests for the cross-OEM analytics
```
After syncing, update `data/oem_latest_results.json` when new quarterly results are published.

## Run Locally
```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

If using a local virtual environment:
```powershell
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe -m streamlit run app.py
```

## Notes
- The dashboard shows the latest handled date/year from loaded datasets.
- Economics metrics are mapped by metric-name heuristics; units are normalized where possible.
- If one OEM does not report a metric in the same way, that series is omitted for that OEM.
- For Streamlit Community Cloud, keep the five `data_cache/*.pkl` files committed in this repository.
- Announced MW comes from each OEM's order list. The lists are not equally complete (see `Reported vs Announced`), so shares are shares of announced MW, not market share.
- Revenue and order-intake comparisons convert GE (USD) and Suzlon (INR) to EUR; Siemens Gamesa's fiscal year ends in September and Suzlon's in March.
