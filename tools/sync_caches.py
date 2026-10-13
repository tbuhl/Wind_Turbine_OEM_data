"""Copy the latest parsed caches (and Nordex reported intake) from the sibling per-OEM projects into this repo.

Usage: python tools/sync_caches.py
Vestas is taken from Vestas_sales_claude when present (the maintained Vestas app), else Vestas_sales.
"""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARENT = ROOT.parent

SOURCES = {
    "data_cache/vestas_parsed_data.pkl": [PARENT / "Vestas_sales_claude/data_cache/vestas_parsed_data.pkl", PARENT / "Vestas_sales/data_cache/vestas_parsed_data.pkl"],
    "data_cache/nordex_parsed_data.pkl": [PARENT / "nordex_sales/data_cache/nordex_parsed_data.pkl"],
    "data_cache/sgre_parsed_data.pkl": [PARENT / "SGRE_sales/data_cache/sgre_parsed_data.pkl"],
    "data_cache/suzlon_parsed_data.pkl": [PARENT / "Suzlon_sales/data_cache/suzlon_parsed_data.pkl"],
    "data_cache/ge_parsed_data.pkl": [PARENT / "GE_sales/data_cache/ge_parsed_data.pkl"],
    "data/nordex_reported_intake.json": [PARENT / "nordex_sales/data/nordex_reported_intake.json"],
}


def main() -> None:
    for target, candidates in SOURCES.items():
        src = next((c for c in candidates if c.exists()), None)
        if src is None:
            print(f"missing: {target}")
            continue
        shutil.copy2(src, ROOT / target)
        print(f"{target} <- {src}")


if __name__ == "__main__":
    main()
