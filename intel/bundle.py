"""One-shot computation of the cross-OEM analytics (so each Streamlit rerun is cheap)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from . import analysis as A

SINCE_RECENT = 2024  # window for geography, product and account views ("recent" = 2024 onwards)


@dataclass
class Bundle:
    today: pd.Timestamp
    orders: pd.DataFrame
    platforms: pd.DataFrame
    economy: pd.DataFrame
    fx: pd.DataFrame
    latest: dict[str, Any]
    summary: pd.DataFrame
    momentum: pd.DataFrame
    reported: pd.DataFrame
    coverage: pd.DataFrame
    product: pd.DataFrame
    top_platforms: pd.DataFrame
    matrix: pd.DataFrame
    battles: pd.DataFrame
    geo: pd.DataFrame
    continents: pd.DataFrame
    shared: pd.DataFrame
    dependence: pd.DataFrame
    fin: pd.DataFrame
    scoreboard: pd.DataFrame
    quality: pd.DataFrame
    price: pd.DataFrame
    since: int = SINCE_RECENT


def build_bundle(economy: pd.DataFrame, orders: pd.DataFrame, platforms: pd.DataFrame, today: pd.Timestamp | None = None) -> Bundle:
    today = (today or pd.Timestamp.today()).normalize()
    o = A.prepare_orders(orders)
    fx = A.load_fx()
    latest = A.load_latest()
    summary = A.annual_summary(o)
    reported = A.reported_intake_mw(economy, A.load_nordex_reported())
    matrix = A.country_matrix(o, SINCE_RECENT)
    return Bundle(
        today=today, orders=o, platforms=platforms, economy=economy, fx=fx, latest=latest, summary=summary,
        momentum=A.momentum_table(o, today), reported=reported, coverage=A.coverage_table(summary, reported),
        product=A.product_table(platforms), top_platforms=A.top_platforms(platforms, SINCE_RECENT), matrix=matrix,
        battles=A.battle_table(matrix), geo=A.geography_profile(o, SINCE_RECENT), continents=A.continent_mix(o, SINCE_RECENT),
        shared=A.shared_customers(o, 2, SINCE_RECENT), dependence=A.customer_dependence(o, SINCE_RECENT),
        fin=A.financial_table(economy, fx), scoreboard=A.latest_scoreboard(latest, fx), quality=A.quality_table(o, platforms, economy, today), price=A.price_table(economy, fx),
    )
