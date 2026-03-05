# Wind Turbine OEM Benchmark Dashboard

Combined Streamlit dashboard comparing Vestas, Nordex, Siemens Gamesa, and Suzlon.

## What This Dashboard Includes
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
- For Streamlit Community Cloud, keep the four `data_cache/*.pkl` files committed in this repository.
