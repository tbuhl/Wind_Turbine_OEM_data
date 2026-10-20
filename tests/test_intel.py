"""Tests for the cross-OEM intelligence layer: each analytic is checked against a brute-force calculation on the data."""
from __future__ import annotations

import re

import numpy as np
import pandas as pd
import pytest

from intel import analysis as A
from intel import insights


# ---------------------------------------------------------------- helpers
def test_customer_key_cleaning():
    assert A.customer_key("EnBW AG") == A.customer_key("EnBW") == "enbw"
    assert A.customer_key("OX2 AB") == A.customer_key("Ox2") == "ox2"
    assert A.customer_key("E.ON") == A.customer_key("E.on") == "e on"
    for undisclosed in ("Unknown", "new", "First", None, np.nan, ""):
        assert A.customer_key(undisclosed) == ""


def test_fx_conversion(fx):
    assert A.to_eur(100.0, "EUR", 2024, fx) == 100.0
    assert A.to_eur(108.24, "USD", 2024, fx) == pytest.approx(108.24 / fx.loc[2024, "eur_usd"])
    assert A.to_eur(1000.0, "INR", 2025, fx) == pytest.approx(1000.0 / fx.loc[2025, "eur_inr"])
    assert A.to_eur(10.0, "USD", 2099, fx) == pytest.approx(10.0 / fx["eur_usd"].iloc[-1])  # unknown year falls back to the latest rate
    assert np.isnan(A.to_eur(None, "USD", 2024, fx))
    assert fx["eur_usd"].between(0.9, 1.4).all() and fx["eur_inr"].between(60, 130).all()  # data sanity


def test_prepare_orders_countries(orders):
    assert not orders["country"].str.contains(r"\(", regex=True).any()
    assert (orders["is_mega"] == (orders["size_mw"] >= A.MEGA_MW)).all()


# ---------------------------------------------------------------- shares and momentum
def test_annual_summary_matches_bruteforce(orders):
    s = A.annual_summary(orders)
    assert s["mw"].sum() == pytest.approx(orders["size_mw"].sum())
    row = s[(s["oem"] == "Nordex") & (s["year"] == 2025)].iloc[0]
    g = orders[(orders["oem"] == "Nordex") & (orders["order_year"] == 2025)]
    assert row["mw"] == pytest.approx(g["size_mw"].sum()) and row["orders"] == len(g)
    assert row["top5_share"] == pytest.approx(g["size_mw"].nlargest(5).sum() / g["size_mw"].sum())
    assert np.allclose(s.groupby("year")["share"].sum(), 1.0)
    assert s["top5_share"].between(0, 1.000001).all() and s["mega_share"].between(0, 1.000001).all()


def test_momentum_matches_bruteforce(orders):
    m = A.momentum_table(orders, pd.Timestamp("2026-10-13")).set_index("oem")
    for oem in m.index:
        g = orders[orders["oem"] == oem]
        as_of = g["order_date"].max().normalize()
        cur = g[(g["order_date"] > as_of - pd.DateOffset(years=1)) & (g["order_date"] <= as_of)]["size_mw"].sum()
        prev = g[(g["order_date"] > as_of - pd.DateOffset(years=2)) & (g["order_date"] <= as_of - pd.DateOffset(years=1))]["size_mw"].sum()
        assert m.loc[oem, "ltm_mw"] == pytest.approx(cur) and m.loc[oem, "prior_ltm_mw"] == pytest.approx(prev)
        assert m.loc[oem, "days_stale"] == (pd.Timestamp("2026-10-13") - as_of).days


def test_calendar_to_date_is_a_common_window(orders):
    cut = pd.Timestamp("2026-05-05")
    t = A.calendar_to_date(orders, cut).set_index("oem")
    g = orders[(orders["oem"] == "Vestas") & (orders["order_date"] >= "2026-01-01") & (orders["order_date"] <= cut)]
    assert t.loc["Vestas", "mw"] == pytest.approx(g["size_mw"].sum())
    p = orders[(orders["oem"] == "Vestas") & (orders["order_date"] >= "2025-01-01") & (orders["order_date"] <= "2025-05-05")]
    assert t.loc["Vestas", "prior_mw"] == pytest.approx(p["size_mw"].sum())


# ---------------------------------------------------------------- coverage
def test_reported_intake_and_coverage(economy, orders):
    nd = A.load_nordex_reported()
    rep = A.reported_intake_mw(economy, nd)
    assert set(rep["oem"]) == {"Vestas", "Nordex"}
    assert rep[(rep["oem"] == "Nordex") & (rep["year"] == 2025)]["reported_mw"].iloc[0] == pytest.approx(nd["annual"]["2025"])
    cov = A.coverage_table(A.annual_summary(orders), rep)
    assert np.allclose(cov["coverage"], cov["mw"] / cov["reported_mw"])
    assert cov["coverage"].between(0.2, 1.3).all()  # data sanity: the lists are partial, never wildly above reported intake


# ---------------------------------------------------------------- product
def test_product_table(platforms):
    t = A.product_table(platforms)
    row = t[(t["oem"] == "Nordex") & (t["year"] == 2025)].iloc[0]
    g = platforms[(platforms["oem"] == "Nordex") & (platforms["order_year"] == 2025) & (platforms["slot_mw"] > 0)].dropna(subset=["rotor_m"])
    assert row["rotor_avg_m"] == pytest.approx(np.average(g["rotor_m"], weights=g["slot_mw"]))
    assert row["large_rotor_share"] == pytest.approx(g.loc[g["rotor_m"] >= A.LARGE_ROTOR_M, "slot_mw"].sum() / g["slot_mw"].sum())
    assert t["large_rotor_share"].dropna().between(0, 1).all()
    top = A.top_platforms(platforms, 2024)
    assert (top.groupby("oem")["share"].sum() <= 1.000001).all()


# ---------------------------------------------------------------- geography
def test_country_matrix_and_battles(orders):
    m = A.country_matrix(orders, 2024)
    sel = orders[(orders["order_year"] >= 2024) & ~orders["country"].isin({A.UNKNOWN, A.MULTI})]
    assert m["total"].sum() == pytest.approx(sel["size_mw"].sum())
    assert m["total"].is_monotonic_decreasing
    bt = A.battle_table(m, top=10)
    assert (bt["leader_share"] >= bt["runner_up_share"]).all()
    for r in bt.itertuples():
        row = m.loc[r.country]
        assert r.leader_share == pytest.approx(row[r.leader] / row["total"])
        assert r.contested == (sum((row[o] / row["total"]) >= 0.15 for o in A.OEM_ORDER if o in row.index) >= 2)


def test_geography_profile_and_continents(orders):
    g = A.geography_profile(orders, 2024).set_index("oem")
    assert g["top_country_share"].between(0, 1).all() and (g["top3_share"] >= g["top_country_share"]).all()
    assert g.loc["Suzlon", "countries"] == 1 and g.loc["Suzlon", "hhi"] == pytest.approx(1.0)  # data sanity: Suzlon orders are India-only
    assert np.allclose(A.continent_mix(orders, 2024).sum(axis=1), 1.0)
    mv = A.country_movers(orders, "Nordex")
    assert np.allclose(mv["delta_mw"], mv["mw_current"] - mv["mw_prior"])


# ---------------------------------------------------------------- customers
def test_shared_customers(orders):
    s = A.shared_customers(orders, 2, 2023)
    assert (s["oems"] >= 2).all() and s["total_mw"].is_monotonic_decreasing
    one = s.iloc[0]
    key = A.customer_key(one["customer"])
    sel = orders[(orders["customer_key"] == key) & (orders["order_year"] >= 2023)]
    assert one["total_mw"] == pytest.approx(sel["size_mw"].sum()) and one["oems"] == sel["oem"].nunique()
    d = A.customer_dependence(orders, 2023)
    assert d["top5_share"].between(0, 1).all() and (d["top5_share"] >= d["top_share"]).all()


# ---------------------------------------------------------------- financial and scoreboard
def test_financial_table(economy, fx):
    t = A.financial_table(economy, fx)
    ge = t[(t["oem"] == "GE") & (t["year"] == 2025)].iloc[0]
    raw = economy[(economy["oem"] == "GE") & (economy["year"] == 2025)].set_index("metric")["value"]
    assert ge["revenue_eur_m"] == pytest.approx(raw["revenue_USD_m"] / fx.loc[2025, "eur_usd"])
    assert ge["book_to_bill"] == pytest.approx(raw["orders_order_intake_USD_m"] / raw["revenue_USD_m"])  # a same-currency ratio is unaffected by FX
    v = t[(t["oem"] == "Vestas") & (t["year"] == 2025)].iloc[0]
    assert v["margin"] == pytest.approx(v["profit_eur_m"] / v["revenue_eur_m"])
    assert t.loc[t["oem"] == "Suzlon", "book_to_bill"].isna().all()


def test_scoreboard(fx):
    latest = A.load_latest()
    sb = A.latest_scoreboard(latest, fx).set_index("oem")
    assert set(sb.index) == {"Vestas", "Nordex", "Siemens Gamesa", "Suzlon", "GE"}
    assert sb.loc["Vestas", "revenue_eur_m"] == latest["oems"]["Vestas"]["revenue"]
    assert sb.loc["Suzlon", "revenue_eur_m"] == pytest.approx(latest["oems"]["Suzlon"]["revenue"] * 10 / fx.loc[2026, "eur_inr"])  # crore -> million
    assert sb.loc["GE", "revenue_eur_m"] == pytest.approx(latest["oems"]["GE"]["revenue"] / fx.loc[2026, "eur_usd"])
    assert sb.loc["Nordex", "book_to_bill"] == pytest.approx(latest["oems"]["Nordex"]["orders_value"] / latest["oems"]["Nordex"]["revenue"])
    assert sb["margin"].between(-1, 1).all()


# ---------------------------------------------------------------- price per MW
def test_price_table(economy, fx):
    t = A.price_table(economy, fx)
    assert set(t["basis"]) == {"Order-intake ASP", "Revenue per delivered MW", "Revenue per delivered MW (3-year pooled)"}
    assert t["eur_m_per_mw"].between(0.4, 2.0).all()  # data sanity: a plausible EUR m/MW range
    v = t[(t["oem"] == "Vestas") & (t["basis"] == "Order-intake ASP") & (t["year"] == 2025)]["eur_m_per_mw"].iloc[0]
    raw = economy[(economy["oem"] == "Vestas") & (economy["metric"] == "average MW price [mEUR/MW]") & (economy["year"] == 2025)]["value"].iloc[0]
    assert v == pytest.approx(raw)
    # revenue per delivered MW = sales of projects / deliveries
    e = economy[(economy["oem"] == "Vestas") & (economy["year"] == 2025)].set_index("metric")["value"]
    r = t[(t["oem"] == "Vestas") & (t["basis"] == "Revenue per delivered MW") & (t["year"] == 2025)]["eur_m_per_mw"].iloc[0]
    assert r == pytest.approx(e["sales of projects"] / e["deliveries [MW]"])
    # the pooled value is the sum over three years, not the mean of annual ratios
    ev = economy[(economy["oem"] == "Vestas") & economy["year"].between(2023, 2025)].pivot_table(index="year", columns="metric", values="value")
    pooled = t[(t["oem"] == "Vestas") & (t["basis"] == "Revenue per delivered MW (3-year pooled)") & (t["year"] == 2025)]["eur_m_per_mw"].iloc[0]
    assert pooled == pytest.approx(ev["sales of projects"].sum() / ev["deliveries [MW]"].sum())
    assert "GE" not in set(t["oem"])  # GE does not disclose MW
    n26 = t[(t["oem"] == "Nordex") & (t["year"] == 2026)]["eur_m_per_mw"].iloc[0]
    assert n26 == pytest.approx(4683.1 / 4923)
    s = t[t["oem"] == "Suzlon"].set_index("period")["eur_m_per_mw"]
    assert s["FY2026 (Apr 2025-Mar 2026)"] == pytest.approx(16679 * 10 / 2456 / (0.75 * fx.loc[2025, "eur_inr"] + 0.25 * fx.loc[2026, "eur_inr"]))


# ---------------------------------------------------------------- quality and insights
def test_quality_table(orders, platforms, economy):
    q = A.quality_table(orders, platforms, economy, pd.Timestamp("2026-10-13")).set_index("oem")
    assert q["orders"].sum() == len(orders)
    for col in ("customer_undisclosed", "customer_undisclosed_recent", "country_unknown"):
        assert q[col].between(0, 1).all()
    assert (q["days_stale"] >= 0).all()


def test_insights_generate_and_are_clean(bundle):
    items = insights.generate_insights(bundle)
    assert len(items) >= 10
    keys = [i.key for i in items]
    assert len(keys) == len(set(keys))
    for i in items:
        text = f"{i.headline} {i.detail} {i.metric} {i.metric_label}"
        assert i.headline and i.detail and i.metric and i.where
        assert not re.search(r"(\bnan\b|\bNaN\b|\bNone\b|\binf\b|n/a)", text), (i.key, text)
        assert i.tone in {"up", "down", "warn", "neutral"}
    assert insights.watchlist(bundle)


def test_each_insight_builder_runs_without_swallowed_errors(bundle):
    for build in insights.INSIGHT_BUILDERS:
        assert build(bundle) is not None, build.__name__


def test_formatters():
    assert insights.eur(-438) == "-EUR 438m" and insights.eur(36000) == "EUR 36.0bn"
    assert insights.pc(0.261, 0, True) == "+26%" and insights.mw(3349) == "3.3 GW" and insights.mw(850) == "850 MW"
