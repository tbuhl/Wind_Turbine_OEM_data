"""Cross-OEM analytics (pure pandas): market share, momentum, reported-vs-announced coverage, product race,
market battles, shared customers, annual financial profile and the latest reported quarter.

All order-based measures use *announced* MW (each OEM's order list). Those lists are not equally complete,
so shares are shares of announced MW, never market share. ``coverage_table`` shows how complete each list is.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

OEM_ORDER = ["Vestas", "Nordex", "Siemens Gamesa", "Suzlon", "GE"]
OEM_COLORS = {"Vestas": "#2F8FCE", "Nordex": "#F18F01", "Siemens Gamesa": "#5E8F49", "Suzlon": "#D1495B", "GE": "#9333EA"}
MEGA_MW = 500.0
LARGE_ROTOR_M = 150.0
UNKNOWN = "Unknown"
MULTI = "Multiple countries"
_NOT_A_COUNTRY = {UNKNOWN, MULTI}
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

_NO_CUSTOMER = {"", "unknown", "new", "first", "undisclosed", "nan", "none", "not disclosed", "n/a"}
_SUFFIX = re.compile(r"\b(ltd|limited|gmbh|ag|a/s|as|sa|inc|llc|plc|co|corp|corporation|group|holding|holdings|bv|nv|pvt|private|kg|ab|oy|spa|srl|se|company|the|and|vind)\b")
_ALIASES = {"eolus": "eolus", "enel": "enel green power", "enel green power": "enel green power", "e on": "e on", "eon": "e on"}


# ---------------------------------------------------------------- loading helpers
def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}


def load_fx(path: Path | None = None) -> pd.DataFrame:
    rows = _read_json(path or DATA_DIR / "fx_annual.json").get("rates", [])
    return pd.DataFrame(rows).set_index("year") if rows else pd.DataFrame(columns=["eur_usd", "eur_inr"])


def load_latest(path: Path | None = None) -> dict[str, Any]:
    return _read_json(path or DATA_DIR / "oem_latest_results.json")


def load_nordex_reported(path: Path | None = None) -> dict[str, Any]:
    return _read_json(path or DATA_DIR / "nordex_reported_intake.json")


def to_eur(value: float | None, currency: str, year: int, fx: pd.DataFrame) -> float:
    """Convert at the average daily rate of the calendar year (year to date for the latest year)."""
    if value is None or pd.isna(value):
        return np.nan
    if currency == "EUR":
        return float(value)
    if year not in fx.index:
        year = int(fx.index.max())
    if currency == "USD":
        return float(value) / float(fx.loc[year, "eur_usd"])
    if currency == "INR":  # value in INR million
        return float(value) / float(fx.loc[year, "eur_inr"])
    return np.nan


def customer_key(name: Any) -> str:
    """Spelling-insensitive customer key ('EnBW AG' == 'EnBW'); undisclosed names map to ''."""
    if name is None or pd.isna(name):
        return ""
    s = re.sub(r"[^a-z0-9 ]", " ", str(name).lower().replace("&", " and "))
    s = re.sub(r"\s+", " ", _SUFFIX.sub(" ", s)).strip()
    if s in _NO_CUSTOMER:
        return ""
    return _ALIASES.get(s, s)


def prepare_orders(orders: pd.DataFrame) -> pd.DataFrame:
    o = orders.copy()
    o["customer_key"] = o["customer"].map(customer_key)
    country = o["country"].fillna(UNKNOWN).astype(str).str.replace(r"\s*\(.*\)\s*$", "", regex=True).str.strip()
    o["country"] = country.where(~country.str.contains(r" and |,|/", regex=True), MULTI)
    o["continent"] = o["continent"].fillna(UNKNOWN)
    o["is_mega"] = o["size_mw"] >= MEGA_MW
    return o


# ---------------------------------------------------------------- announced MW: share and momentum
def annual_summary(orders: pd.DataFrame) -> pd.DataFrame:
    """Per OEM and order year: announced MW, orders, share of all announced MW, concentration."""
    rows = []
    for (oem, year), g in orders.groupby(["oem", "order_year"]):
        mw = g["size_mw"].sum()
        top5 = g["size_mw"].nlargest(5).sum()
        rows.append({"oem": oem, "year": int(year), "mw": float(mw), "orders": int(len(g)), "avg_mw": float(g["size_mw"].mean()),
                     "median_mw": float(g["size_mw"].median()), "top5_share": float(top5 / mw) if mw else np.nan,
                     "mega_mw": float(g.loc[g["is_mega"], "size_mw"].sum()), "mega_orders": int(g["is_mega"].sum())})
    t = pd.DataFrame(rows)
    t["share"] = t["mw"] / t.groupby("year")["mw"].transform("sum")
    t["mega_share"] = t["mega_mw"] / t["mw"]
    return t.sort_values(["oem", "year"]).reset_index(drop=True)


def share_pivot(summary: pd.DataFrame, value: str = "share") -> pd.DataFrame:
    return summary.pivot(index="year", columns="oem", values=value).reindex(columns=[o for o in OEM_ORDER if o in set(summary["oem"])])


def momentum_table(orders: pd.DataFrame, today: pd.Timestamp | None = None) -> pd.DataFrame:
    """Last 12 months to each OEM's latest announced order vs the 12 months before, plus staleness."""
    today = today or pd.Timestamp.today().normalize()
    rows = []
    for oem in [o for o in OEM_ORDER if o in set(orders["oem"])]:
        g = orders[orders["oem"] == oem]
        as_of = g["order_date"].max().normalize()
        start, prior = as_of - pd.DateOffset(years=1), as_of - pd.DateOffset(years=2)
        cur = g[(g["order_date"] > start) & (g["order_date"] <= as_of)]
        prev = g[(g["order_date"] > prior) & (g["order_date"] <= start)]
        ytd_cut = lambda y: pd.Timestamp(year=y, month=as_of.month, day=min(as_of.day, 28)) if as_of.month == 2 and as_of.day == 29 else as_of.replace(year=y)  # noqa: E731
        y = as_of.year
        ytd = g[(g["order_year"] == y) & (g["order_date"] <= as_of)]["size_mw"].sum()
        ytd_prev = g[(g["order_year"] == y - 1) & (g["order_date"] <= ytd_cut(y - 1))]["size_mw"].sum()
        rows.append({"oem": oem, "as_of": as_of, "days_stale": int((today - as_of).days), "ltm_mw": float(cur["size_mw"].sum()), "prior_ltm_mw": float(prev["size_mw"].sum()),
                     "ltm_growth": float(cur["size_mw"].sum() / prev["size_mw"].sum() - 1) if prev["size_mw"].sum() else np.nan,
                     "ltm_orders": int(len(cur)), "ytd_mw": float(ytd), "ytd_prev_mw": float(ytd_prev),
                     "ytd_growth": float(ytd / ytd_prev - 1) if ytd_prev else np.nan, "ytd_year": int(y)})
    return pd.DataFrame(rows)


def calendar_to_date(orders: pd.DataFrame, cut: pd.Timestamp) -> pd.DataFrame:
    """Announced MW from 1 Jan to ``cut`` in the cut's year and the same window a year earlier, per OEM (common window)."""
    prev_cut = cut - pd.DateOffset(years=1)
    rows = []
    for oem in [o for o in OEM_ORDER if o in set(orders["oem"])]:
        g = orders[orders["oem"] == oem]
        cur = g[(g["order_date"] >= pd.Timestamp(cut.year, 1, 1)) & (g["order_date"] <= cut)]["size_mw"].sum()
        prev = g[(g["order_date"] >= pd.Timestamp(prev_cut.year, 1, 1)) & (g["order_date"] <= prev_cut)]["size_mw"].sum()
        rows.append({"oem": oem, "mw": float(cur), "prior_mw": float(prev), "growth": float(cur / prev - 1) if prev else np.nan})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- reported intake vs announced list
def reported_intake_mw(economy: pd.DataFrame, nordex: dict[str, Any] | None = None) -> pd.DataFrame:
    """Company-reported order intake in MW per OEM and year, where the company discloses it (Vestas, Nordex)."""
    rows = []
    v = economy[(economy["oem"] == "Vestas") & (economy["metric"] == "Order inkake (MW)")]
    for r in v.dropna(subset=["value"]).itertuples():
        rows.append({"oem": "Vestas", "year": int(r.year), "reported_mw": float(r.value)})
    for year, mw in ((nordex or {}).get("annual") or {}).items():
        rows.append({"oem": "Nordex", "year": int(year), "reported_mw": float(mw)})
    return pd.DataFrame(rows, columns=["oem", "year", "reported_mw"])


def coverage_table(summary: pd.DataFrame, reported: pd.DataFrame) -> pd.DataFrame:
    t = summary[["oem", "year", "mw"]].merge(reported, on=["oem", "year"], how="inner")
    t["coverage"] = t["mw"] / t["reported_mw"]
    return t.sort_values(["oem", "year"]).reset_index(drop=True)


# ---------------------------------------------------------------- product race
def product_table(platforms: pd.DataFrame) -> pd.DataFrame:
    """MW-weighted average rating and rotor, and the share of MW on 150 m-plus rotors, per OEM and order year."""
    rows = []
    p = platforms[platforms["slot_mw"].fillna(0) > 0]
    for (oem, year), g in p.groupby(["oem", "order_year"]):
        r = g.dropna(subset=["rotor_m"])
        m = g.dropna(subset=["mw_rating"])
        rows.append({"oem": oem, "year": int(year),
                     "rotor_avg_m": float(np.average(r["rotor_m"], weights=r["slot_mw"])) if len(r) else np.nan,
                     "rating_avg_mw": float(np.average(m["mw_rating"], weights=m["slot_mw"])) if len(m) else np.nan,
                     "large_rotor_share": float(r.loc[r["rotor_m"] >= LARGE_ROTOR_M, "slot_mw"].sum() / r["slot_mw"].sum()) if len(r) else np.nan,
                     "mapped_mw": float(g["slot_mw"].sum()), "rotor_known_share": float(r["slot_mw"].sum() / g["slot_mw"].sum())})
    return pd.DataFrame(rows)


def top_platforms(platforms: pd.DataFrame, since: int, top: int = 3) -> pd.DataFrame:
    p = platforms[(platforms["order_year"] >= since) & (platforms["slot_mw"].fillna(0) > 0) & (platforms["platform"].fillna(UNKNOWN) != UNKNOWN)]
    g = p.groupby(["oem", "platform"])["slot_mw"].sum().reset_index()
    g["share"] = g["slot_mw"] / g.groupby("oem")["slot_mw"].transform("sum")
    return g.sort_values(["oem", "slot_mw"], ascending=[True, False]).groupby("oem").head(top).reset_index(drop=True)


# ---------------------------------------------------------------- market battles
def country_matrix(orders: pd.DataFrame, since: int) -> pd.DataFrame:
    """Announced MW by country and OEM since a given order year (known single countries only)."""
    o = orders[(orders["order_year"] >= since) & (~orders["country"].isin(_NOT_A_COUNTRY))]
    m = o.pivot_table(index="country", columns="oem", values="size_mw", aggfunc="sum", fill_value=0.0)
    m = m.reindex(columns=[c for c in OEM_ORDER if c in m.columns], fill_value=0.0)
    m["total"] = m.sum(axis=1)
    return m.sort_values("total", ascending=False)


def battle_table(matrix: pd.DataFrame, top: int = 20, min_share: float = 0.15) -> pd.DataFrame:
    rows = []
    oems = [c for c in matrix.columns if c != "total"]
    for country, r in matrix.head(top).iterrows():
        shares = r[oems] / r["total"]
        ranked = shares.sort_values(ascending=False)
        rows.append({"country": country, "total_mw": float(r["total"]), "leader": ranked.index[0], "leader_share": float(ranked.iloc[0]),
                     "runner_up": ranked.index[1] if ranked.iloc[1] > 0 else "-", "runner_up_share": float(ranked.iloc[1]),
                     "oems_present": int((shares > 0).sum()), "contested": bool((shares >= min_share).sum() >= 2),
                     "gap_pts": float(ranked.iloc[0] - ranked.iloc[1])})
    return pd.DataFrame(rows)


def geography_profile(orders: pd.DataFrame, since: int) -> pd.DataFrame:
    """Per OEM: top-3 country share, number of countries, home-market share and Herfindahl index of country mix."""
    o = orders[(orders["order_year"] >= since) & (~orders["country"].isin(_NOT_A_COUNTRY))]
    rows = []
    for oem in [x for x in OEM_ORDER if x in set(o["oem"])]:
        by = o[o["oem"] == oem].groupby("country")["size_mw"].sum().sort_values(ascending=False)
        s = by / by.sum()
        rows.append({"oem": oem, "countries": int(len(by)), "top_country": by.index[0], "top_country_share": float(s.iloc[0]),
                     "top3_share": float(s.head(3).sum()), "hhi": float((s ** 2).sum()), "mw": float(by.sum())})
    return pd.DataFrame(rows)


def continent_mix(orders: pd.DataFrame, since: int) -> pd.DataFrame:
    o = orders[(orders["order_year"] >= since) & (orders["continent"] != UNKNOWN)]
    m = o.pivot_table(index="oem", columns="continent", values="size_mw", aggfunc="sum", fill_value=0.0)
    m = m.div(m.sum(axis=1), axis=0)
    return m.reindex([x for x in OEM_ORDER if x in m.index])


def country_movers(orders: pd.DataFrame, oem: str, as_of: pd.Timestamp | None = None) -> pd.DataFrame:
    g = orders[(orders["oem"] == oem) & (~orders["country"].isin(_NOT_A_COUNTRY))]
    as_of = as_of or g["order_date"].max().normalize()
    start, prior = as_of - pd.DateOffset(years=1), as_of - pd.DateOffset(years=2)
    cur = g[(g["order_date"] > start) & (g["order_date"] <= as_of)].groupby("country")["size_mw"].sum()
    prev = g[(g["order_date"] > prior) & (g["order_date"] <= start)].groupby("country")["size_mw"].sum()
    t = pd.concat([cur.rename("mw_current"), prev.rename("mw_prior")], axis=1).fillna(0.0)
    t["delta_mw"] = t["mw_current"] - t["mw_prior"]
    return t.sort_values("delta_mw", ascending=False)


# ---------------------------------------------------------------- shared customers
def shared_customers(orders: pd.DataFrame, min_oems: int = 2, since: int | None = None) -> pd.DataFrame:
    o = orders[orders["customer_key"] != ""]
    if since:
        o = o[o["order_year"] >= since]
    by = o.pivot_table(index="customer_key", columns="oem", values="size_mw", aggfunc="sum", fill_value=0.0)
    by = by.reindex(columns=[c for c in OEM_ORDER if c in by.columns], fill_value=0.0)
    by["total_mw"] = by.sum(axis=1)
    by["oems"] = (by[[c for c in by.columns if c in OEM_ORDER]] > 0).sum(axis=1)
    name = o.groupby("customer_key")["customer"].agg(lambda s: s.value_counts().index[0])
    by.insert(0, "customer", name.reindex(by.index))
    return by[by["oems"] >= min_oems].sort_values("total_mw", ascending=False).reset_index(drop=True)


def customer_dependence(orders: pd.DataFrame, since: int) -> pd.DataFrame:
    """Per OEM: share of named-customer MW held by the five largest customers."""
    o = orders[(orders["order_year"] >= since) & (orders["customer_key"] != "")]
    rows = []
    for oem in [x for x in OEM_ORDER if x in set(o["oem"])]:
        g = o[o["oem"] == oem].groupby("customer_key")["size_mw"].sum().sort_values(ascending=False)
        rows.append({"oem": oem, "named_mw": float(g.sum()), "customers": int(len(g)), "top5_share": float(g.head(5).sum() / g.sum()),
                     "top_customer": o[(o["oem"] == oem) & (o["customer_key"] == g.index[0])]["customer"].iloc[0], "top_share": float(g.iloc[0] / g.sum())})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- financial profile (annual, EUR)
def financial_table(economy: pd.DataFrame, fx: pd.DataFrame) -> pd.DataFrame:
    """Annual revenue, order intake and a profit measure per OEM in EUR m, with book-to-bill and margin.

    Profit measure differs by company (Vestas EBIT, Nordex EBIT, GE Wind EBITDA, Siemens Gamesa net profit); Suzlon has revenue only.
    """
    def pick(oem: str, metric: str) -> pd.Series:
        e = economy[(economy["oem"] == oem) & (economy["metric"] == metric)].dropna(subset=["value"])
        return e.groupby("year")["value"].mean() if len(e) else pd.Series(dtype=float)

    def conv(s: pd.Series, currency: str, scale: float = 1.0) -> pd.Series:
        return pd.Series({int(y): to_eur(v * scale, currency, int(y), fx) for y, v in s.items()}, dtype=float)

    spec = {
        "Vestas": dict(rev=("revenue (mEUR)", "EUR", 1), orders=("Order intake (bnEUR)", "EUR", 1000), profit=("EBIT", "EUR", 1), measure="EBIT"),
        "Nordex": dict(rev=("Sales", "EUR", 1), orders=("Order intake [M€]", "EUR", 1), profit=("EBIT", "EUR", 1), measure="EBIT"),
        "Siemens Gamesa": dict(rev=("Total revenue (€m)", "EUR", 1), orders=("Total order intake (€m)", "EUR", 1), profit=("net profit", "EUR", 1), measure="Net profit"),
        "Suzlon": dict(rev=("Revenue (mEUR, converted)", "EUR", 1), orders=None, profit=None, measure="n/a"),
        "GE": dict(rev=("revenue_USD_m", "USD", 1), orders=("orders_order_intake_USD_m", "USD", 1), profit=("segment_EBITDA_USD_m", "USD", 1), measure="EBITDA"),
    }
    rows = []
    for oem, sp in spec.items():
        rev = conv(pick(oem, sp["rev"][0]), sp["rev"][1], sp["rev"][2])
        orders = conv(pick(oem, sp["orders"][0]), sp["orders"][1], sp["orders"][2]) if sp["orders"] else pd.Series(dtype=float)
        profit = conv(pick(oem, sp["profit"][0]), sp["profit"][1], sp["profit"][2]) if sp["profit"] else pd.Series(dtype=float)
        for year in sorted(set(rev.index) | set(orders.index) | set(profit.index)):
            r, o_, p_ = rev.get(year, np.nan), orders.get(year, np.nan), profit.get(year, np.nan)
            rows.append({"oem": oem, "year": int(year), "revenue_eur_m": r, "orders_eur_m": o_, "profit_eur_m": p_, "profit_measure": sp["measure"],
                         "book_to_bill": o_ / r if pd.notna(o_) and pd.notna(r) and r else np.nan, "margin": p_ / r if pd.notna(p_) and pd.notna(r) and r else np.nan})
    t = pd.DataFrame(rows).sort_values(["oem", "year"]).reset_index(drop=True)
    t["revenue_growth"] = t.groupby("oem")["revenue_eur_m"].pct_change(fill_method=None)
    return t


# ---------------------------------------------------------------- latest reported quarter
def latest_scoreboard(latest: dict[str, Any], fx: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for oem in OEM_ORDER:
        d = (latest.get("oems") or {}).get(oem)
        if not d:
            continue
        year = int(str(d["period_end"])[:4])
        cur = d["currency"]
        # Suzlon figures are in INR crore (1 crore = 10 million): convert to INR million first
        scale = 10.0 if cur == "INR" else 1.0
        rev = to_eur(d["revenue"] * scale, cur, year, fx)
        profit = to_eur(d["profit"] * scale, cur, year, fx) if d.get("profit") is not None else np.nan
        orders_val = to_eur(d["orders_value"] * scale, cur, year, fx) if d.get("orders_value") is not None else np.nan
        backlog = to_eur(d["backlog_value"] * scale, cur, year, fx) if d.get("backlog_value") is not None else np.nan
        rows.append({
            "oem": oem, "period": d["period"], "currency": cur, "revenue_eur_m": rev, "revenue_yoy": d.get("revenue_yoy"),
            "profit_measure": d["profit_measure"], "profit_eur_m": profit, "margin": d["profit"] / d["revenue"] if d.get("profit") is not None else np.nan,
            "margin_prior": d["profit_prior"] / (d["revenue"] / (1 + d["revenue_yoy"])) if d.get("profit_prior") is not None and d.get("revenue_yoy") is not None else np.nan,
            "orders_value_eur_m": orders_val, "book_to_bill": orders_val / rev if pd.notna(orders_val) and rev else np.nan,
            "orders_mw": d.get("orders_mw"), "orders_mw_yoy": d.get("orders_mw_yoy"), "orders_value_yoy": d.get("orders_value_yoy"),
            "backlog_eur_m": backlog, "backlog_mw": d.get("backlog_mw"), "guidance": d.get("guidance", ""), "source": d.get("source", ""),
        })
    t = pd.DataFrame(rows)
    if len(t):
        t["backlog_cover_years"] = t["backlog_eur_m"] / (t["revenue_eur_m"] * 4)
    return t


# ---------------------------------------------------------------- data quality
def quality_table(orders: pd.DataFrame, platforms: pd.DataFrame, economy: pd.DataFrame, today: pd.Timestamp | None = None) -> pd.DataFrame:
    today = today or pd.Timestamp.today().normalize()
    rows = []
    for oem in [x for x in OEM_ORDER if x in set(orders["oem"])]:
        g = orders[orders["oem"] == oem]
        p = platforms[platforms["oem"] == oem]
        e = economy[economy["oem"] == oem]
        recent = g[g["order_year"] >= g["order_year"].max() - 2]
        rows.append({
            "oem": oem, "orders": int(len(g)), "first_year": int(g["order_year"].min()), "latest_order": g["order_date"].max().normalize(),
            "days_stale": int((today - g["order_date"].max().normalize()).days), "economy_to": int(e["year"].max()) if len(e) else np.nan,
            "customer_undisclosed": float((g["customer_key"] == "").mean()), "customer_undisclosed_recent": float((recent["customer_key"] == "").mean()),
            "country_unknown": float((g["country"] == UNKNOWN).mean()),
            "platform_unknown": float((p["platform"].fillna(UNKNOWN) == UNKNOWN).mean()) if len(p) else np.nan,
            "duplicates": int(g.duplicated(["order_date", "size_mw", "country", "customer"]).sum()),
        })
    return pd.DataFrame(rows)
