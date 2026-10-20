"""Rule-based cross-OEM findings. Every number is computed from the data; nothing is hard-coded narrative."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd

from .bundle import Bundle


@dataclass
class Insight:
    key: str
    headline: str
    detail: str
    metric: str
    metric_label: str
    tone: str  # up | down | warn | neutral
    where: str


# ---------------------------------------------------------------- formatting
def eur(m: float) -> str:
    if m is None or pd.isna(m):
        return "n/a"
    sign = "-" if m < 0 else ""
    m = abs(m)
    return f"{sign}EUR {m / 1000:.1f}bn" if m >= 1000 else f"{sign}EUR {m:,.0f}m"


def pc(x: float, d: int = 0, signed: bool = False) -> str:
    if x is None or pd.isna(x) or np.isinf(x):
        return "n/a"
    return f"{x:+.{d}%}" if signed else f"{x:.{d}%}"


def mw(x: float) -> str:
    if x is None or pd.isna(x):
        return "n/a"
    return f"{x / 1000:.1f} GW" if abs(x) >= 1000 else f"{x:,.0f} MW"


def join_and(items: list[str]) -> str:
    items = [str(i) for i in items]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


SHORT = {"Siemens Gamesa": "Siemens Gamesa"}


# ---------------------------------------------------------------- builders
def insight_growth(b: Bundle) -> Insight | None:
    s = b.scoreboard.dropna(subset=["revenue_yoy"]).sort_values("revenue_yoy", ascending=False)
    if len(s) < 3:
        return None
    top, bot = s.iloc[0], s.iloc[-1]
    growing = s[s["revenue_yoy"] > 0]
    label = b.latest.get("period_label", "latest quarter")
    return Insight(
        key="growth",
        headline=f"{top['oem']} grew revenue fastest in {label} ({pc(top['revenue_yoy'], 0, True)}); {bot['oem']} fell most ({pc(bot['revenue_yoy'], 0, True)})",
        detail=f"{len(growing)} of {len(s)} OEMs grew year on year: " + "; ".join(f"{r.oem} {pc(r.revenue_yoy, 0, True)} to {eur(r.revenue_eur_m)}" for r in s.itertuples())
        + ". Quarters are the calendar April-June 2026 (Siemens Gamesa Q3 FY26, Suzlon Q1 FY27); Siemens Gamesa is nominal growth, Suzlon and GE converted at the 2026 year-to-date rate.",
        metric=pc(top["revenue_yoy"], 0, True), metric_label=f"{top['oem']} revenue growth", tone="up" if len(growing) >= len(s) / 2 else "warn", where="Scoreboard")


def insight_margin(b: Bundle) -> Insight | None:
    s = b.scoreboard.dropna(subset=["margin"])
    if len(s) < 3:
        return None
    improved = s[s["margin"] > s["margin_prior"]]
    loss = s[s["margin"] < 0]
    best = s.sort_values("margin", ascending=False).iloc[0]
    return Insight(
        key="margin",
        headline=f"{len(improved)} of {len(s)} OEMs improved their profit margin year on year; {join_and(loss['oem'].tolist()) or 'none'} still lost money" if len(loss) else f"{len(improved)} of {len(s)} OEMs improved their profit margin year on year and none lost money",
        detail="; ".join(f"{r.oem} {pc(r.margin, 1)} ({r.profit_measure}, {pc(r.margin_prior, 1)} a year earlier)" for r in s.sort_values("margin", ascending=False).itertuples())
        + ". Margin definitions differ (EBIT before special items, EBITDA, profit before special items), so rankings across companies are indicative only.",
        metric=pc(best["margin"], 1), metric_label=f"{best['oem']} margin", tone="up" if len(improved) > len(s) / 2 else "warn", where="Scoreboard")


def insight_orders(b: Bundle) -> Insight | None:
    s = b.scoreboard.dropna(subset=["book_to_bill"])
    if len(s) < 3:
        return None
    above = s[s["book_to_bill"] > 1]
    best = s.sort_values("book_to_bill", ascending=False).iloc[0]
    mw_rows = b.scoreboard.dropna(subset=["orders_mw"])
    mw_txt = ("; reported order intake in MW: " + ", ".join(f"{r.oem} {mw(r.orders_mw)}" + (f" ({pc(r.orders_mw_yoy, 0, True)})" if pd.notna(r.orders_mw_yoy) else "") for r in mw_rows.itertuples())) if len(mw_rows) else ""
    return Insight(
        key="orders",
        headline=f"{join_and(above['oem'].tolist()) if len(above) else 'No OEM'} booked more than it billed in the latest quarter (book-to-bill {best['book_to_bill']:.2f} at {best['oem']})",
        detail="Book-to-bill, orders (turbines plus service where reported) divided by revenue: " + ", ".join(f"{r.oem} {r.book_to_bill:.2f}" for r in s.sort_values("book_to_bill", ascending=False).itertuples()) + mw_txt
        + ". One quarter is noisy; order intake is lumpy.",
        metric=f"{best['book_to_bill']:.2f}", metric_label=f"{best['oem']} book-to-bill", tone="up" if len(above) else "warn", where="Scoreboard")


def insight_backlog(b: Bundle) -> Insight | None:
    s = b.scoreboard.dropna(subset=["backlog_eur_m"]).sort_values("backlog_eur_m", ascending=False)
    if len(s) < 3:
        return None
    top = s.iloc[0]
    extra = ""
    v = (b.latest.get("oems") or {}).get("Vestas", {})
    if v.get("backlog_note"):
        extra = f" Vestas also reports service agreements, bringing its combined backlog to the figure in its release ({v['backlog_note'].split('combined with service agreements ')[-1]})."
    return Insight(
        key="backlog",
        headline=f"{top['oem']} has the largest turbine backlog ({eur(top['backlog_eur_m'])}); cover ranges from {s['backlog_cover_years'].min():.1f} to {s['backlog_cover_years'].max():.1f} years of revenue",
        detail="; ".join(f"{r.oem} {eur(r.backlog_eur_m)} ({r.backlog_cover_years:.1f} years of annualised latest-quarter revenue)" for r in s.itertuples())
        + ". GE's backlog is the end-2025 figure (reported annually only)." + extra,
        metric=eur(top["backlog_eur_m"]), metric_label=f"{top['oem']} backlog", tone="neutral", where="Scoreboard")


def insight_momentum(b: Bundle) -> Insight | None:
    m = b.momentum.dropna(subset=["ltm_growth"]).sort_values("ltm_growth", ascending=False)
    if len(m) < 3:
        return None
    up = m[m["ltm_growth"] > 0]
    top = m.iloc[0]
    return Insight(
        key="momentum",
        headline=f"Announced MW over the last 12 months rose for {len(up)} of {len(m)} OEMs; {top['oem']} is up {pc(top['ltm_growth'], 0)}",
        detail="; ".join(f"{r.oem} {mw(r.ltm_mw)} ({pc(r.ltm_growth, 0, True)}, to {r.as_of:%d %b %Y})" for r in m.itertuples())
        + ". Each OEM is measured to its own latest announced order, and the lists differ in completeness (see coverage), so compare direction rather than level.",
        metric=pc(top["ltm_growth"], 0, True), metric_label=f"{top['oem']} 12-month change", tone="up" if len(up) >= len(m) / 2 else "warn", where="Momentum & Share")


def insight_share(b: Bundle) -> Insight | None:
    s = b.summary
    year = int(s["year"].max() - 1) if s["year"].max() >= pd.Timestamp(b.today).year else int(s["year"].max())
    y = s[s["year"] == year].sort_values("share", ascending=False)
    base = s[s["year"] == year - 3]
    if y.empty:
        return None
    lead = y.iloc[0]
    moves = []
    for r in y.itertuples():
        b0 = base[base["oem"] == r.oem]
        if len(b0):
            moves.append((r.oem, r.share - float(b0["share"].iloc[0])))
    gain = max(moves, key=lambda t: t[1]) if moves else None
    lead_move = dict(moves).get(lead["oem"])
    cnt = s.pivot(index="year", columns="oem", values="orders")
    thin = []
    for oem in cnt.columns:  # lists that stopped growing: orders per year now vs the 2020-2022 average
        before, now = cnt.loc[2020:2022, oem].mean(), cnt.loc[year, oem] if year in cnt.index else np.nan
        if pd.notna(before) and pd.notna(now) and before >= 10 and now < 0.4 * before:
            thin.append(f"{oem} ({int(now)} orders in {year} vs {before:.0f} a year in 2020-2022)")
    return Insight(
        key="share",
        headline=f"{lead['oem']} holds {pc(lead['share'])} of announced MW in {year}" + ((f", {lead_move * 100:+.0f} points since {year - 3}" if lead_move is not None else "") if gain and gain[0] == lead["oem"] else (f"; {gain[0]} gained the most share since {year - 3} ({gain[1] * 100:+.0f} points)" if gain else "")),
        detail=f"Share of announced MW in {year}: " + ", ".join(f"{r.oem} {pc(r.share)} ({mw(r.mw)})" for r in y.itertuples())
        + ". This is a share of what the lists contain, not market share" + (f"; lists that thinned out: {join_and(thin)}" if thin else "") + ".",
        metric=pc(lead["share"]), metric_label=f"{lead['oem']} share of announced MW, {year}", tone="neutral", where="Momentum & Share")


def insight_coverage(b: Bundle) -> Insight | None:
    c = b.coverage
    if c.empty:
        return None
    last = c.sort_values("year").groupby("oem").tail(1)
    return Insight(
        key="coverage",
        headline=f"The announced lists capture {', '.join(f'{pc(r.coverage)} of {r.oem}' for r in last.itertuples())} reported order intake in the latest full year",
        detail="Company-reported intake (MW) vs announced MW: " + "; ".join(f"{r.oem} {r.year}: {mw(r.mw)} vs {mw(r.reported_mw)}" for r in last.itertuples())
        + ". The gap is orders that are never announced individually (undisclosed customers, framework call-offs, service), so announced MW understates volume, more for some OEMs than others.",
        metric=pc(float(last["coverage"].min())), metric_label="lowest list coverage", tone="warn", where="Reported vs Announced")


def insight_product(b: Bundle) -> Insight | None:
    p = b.product
    year = int(p["year"].max())
    cur = p[(p["year"] == year) & (p["mapped_mw"] >= 300) & p["rotor_avg_m"].notna()]
    if len(cur) < 3:
        year -= 1
        cur = p[(p["year"] == year) & (p["mapped_mw"] >= 300) & p["rotor_avg_m"].notna()]
    if len(cur) < 3:
        return None
    cur = cur.sort_values("rotor_avg_m", ascending=False)
    top = b.top_platforms.sort_values("share", ascending=False).iloc[0]
    return Insight(
        key="product",
        headline=f"Average rotor on {year} orders: {', '.join(f'{r.oem} {r.rotor_avg_m:.0f} m' for r in cur.itertuples())}",
        detail=("MW-weighted rotor and rating: " + "; ".join(f"{r.oem} {r.rotor_avg_m:.0f} m / {r.rating_avg_mw:.1f} MW" for r in cur.itertuples())
                + f". Offshore orders lift Vestas and Siemens Gamesa averages. Most concentrated range since {b.since}: {top['oem']}'s {top['platform']} is {pc(top['share'])} of its platform-mapped MW."),
        metric=f"{cur.iloc[0]['rotor_avg_m']:.0f} m", metric_label=f"{cur.iloc[0]['oem']} average rotor", tone="neutral", where="Product Race")


def insight_battles(b: Bundle) -> Insight | None:
    t = b.battles
    if t.empty:
        return None
    contested = t[t["contested"]]
    tight = contested.sort_values("gap_pts").head(3)
    single = t[t["leader_share"] >= 0.9]
    return Insight(
        key="battles",
        headline=f"{len(contested)} of the {len(t)} largest markets since {b.since} are genuinely contested; the closest fights are {join_and(tight['country'].tolist())}",
        detail="Gap between the leader and the runner-up: " + "; ".join(f"{r.country} {r.leader} {pc(r.leader_share)} vs {r.runner_up} {pc(r.runner_up_share)}" for r in tight.itertuples())
        + f". {len(single)} markets are effectively one-supplier ({join_and(single['country'].head(4).tolist())}). Contested = at least two OEMs with 15% or more of announced MW.",
        metric=f"{len(contested)}/{len(t)}", metric_label="contested markets", tone="neutral", where="Market Battles")


def insight_concentration(b: Bundle) -> Insight | None:
    g = b.geo
    d = b.dependence
    if g.empty or d.empty:
        return None
    hi = g[g["countries"] >= 4].sort_values("top3_share", ascending=False)
    single = g[g["countries"] < 4]
    dd = d.sort_values("top5_share", ascending=False).iloc[0]
    return Insight(
        key="concentration",
        headline=(f"{dd['oem']} is the most concentrated on both counts: top 3 countries {pc(hi.iloc[0]['top3_share'])} of announced MW, top 5 customers {pc(dd['top5_share'])} of named MW" if hi.iloc[0]["oem"] == dd["oem"]
                  else f"{hi.iloc[0]['oem']} is the most geographically concentrated (top 3 countries {pc(hi.iloc[0]['top3_share'])}); {dd['oem']} the most dependent on a few customers (top 5 = {pc(dd['top5_share'])})"),
        detail="Top-3 country share of announced MW since " + str(b.since) + ": " + ", ".join(f"{r.oem} {pc(r.top3_share)} ({r.top_country} {pc(r.top_country_share)})" for r in g.itertuples())
        + (f". {join_and(single['oem'].tolist())} sells in {join_and([f'{int(c)} market' + ('s' if c > 1 else '') for c in single['countries']])} only" if len(single) else "")
        + ". Top-5 customer share of named-customer MW: " + ", ".join(f"{r.oem} {pc(r.top5_share)}" for r in d.itertuples()) + ".",
        metric=pc(dd["top5_share"]), metric_label=f"{dd['oem']} top-5 customer share", tone="warn", where="Market Battles")


def insight_shared_customers(b: Bundle) -> Insight | None:
    s = b.shared
    if s.empty:
        return None
    three = s[s["oems"] >= 3]
    top = s.iloc[0]
    oems = [c for c in s.columns if c in ("Vestas", "Nordex", "Siemens Gamesa", "Suzlon", "GE")]
    parts = [f"{o} {mw(top[o])}" for o in oems if top[o] > 0]
    return Insight(
        key="shared_customers",
        headline=f"{len(s)} customers bought from more than one OEM since {b.since}; {top['customer']} is the largest multi-vendor buyer ({mw(top['total_mw'])})",
        detail=f"{top['customer']}: {', '.join(parts)}. {(f"{len(three)} customers bought from three or more OEMs: {join_and(three['customer'].head(5).tolist())}." if len(three) else "No customer bought from three or more OEMs.")} Customers with undisclosed names are excluded, and this is a floor because name matching is exact after cleaning legal suffixes.",
        metric=f"{len(s)}", metric_label="multi-vendor customers", tone="neutral", where="Accounts")


def insight_freshness(b: Bundle) -> Insight | None:
    q = b.quality
    stale = q[q["days_stale"] > 120].sort_values("days_stale", ascending=False)
    worst = q.sort_values("days_stale", ascending=False).iloc[0]
    return Insight(
        key="freshness",
        headline=(f"{join_and(stale['oem'].tolist())} order list{'s are' if len(stale) > 1 else ' is'} more than four months behind" if len(stale) else f"All order lists are within four months of today (oldest: {worst['oem']}, {int(worst['days_stale'])} days)"),
        detail="Latest announced order per OEM: " + "; ".join(f"{r.oem} {r.latest_order:%d %b %Y} ({int(r.days_stale)} days)" for r in q.itertuples())
        + ". Customer names are undisclosed in " + ", ".join(f"{pc(r.customer_undisclosed_recent)} of recent {r.oem} orders" for r in q.sort_values("customer_undisclosed_recent", ascending=False).head(3).itertuples()) + ".",
        metric=f"{int(worst['days_stale'])} days", metric_label=f"{worst['oem']} list age", tone="warn" if len(stale) else "neutral", where="Data Quality")


def insight_price(b: Bundle) -> Insight | None:
    p = b.price
    asp = p[p["basis"] == "Order-intake ASP"]
    if asp.empty:
        return None
    last = asp.sort_values("year").groupby("oem").tail(1).sort_values("eur_m_per_mw", ascending=False)
    v = last[last["oem"] == "Vestas"]
    n = last[last["oem"] == "Nordex"]
    gap = (float(n["eur_m_per_mw"].iloc[0]) / float(v["eur_m_per_mw"].iloc[0]) - 1) if len(v) and len(n) else np.nan
    rev = p[(p["basis"] == "Revenue per delivered MW") & (p["oem"] == "Suzlon")].sort_values("year")
    suz = f" Suzlon does not report a price; revenue per delivered MW (including O&M) is about EUR {rev['eur_m_per_mw'].iloc[-1]:.2f}m, roughly {abs(rev['eur_m_per_mw'].iloc[-1] / float(v['eur_m_per_mw'].iloc[0]) - 1):.0%} below Vestas' order price." if len(rev) and len(v) else ""
    top = last.iloc[0]
    return Insight(
        key="price",
        headline=(f"Turbine order prices (estimates): {', '.join(f'{r.oem} EUR {r.eur_m_per_mw:.2f}m/MW ({r.period})' for r in last.itertuples())}"),
        detail=(f"Estimates based on the company-reported average selling price of new turbine orders. " + (f"Nordex's latest price is {pc(abs(gap))} {'below' if gap < 0 else 'above'} Vestas'. " if pd.notna(gap) else "")
                + "Vestas includes offshore, which lifts its average; Siemens Gamesa's last reported price is onshore only and from 2022." + suz
                + " GE does not disclose MW, so no price can be derived."),
        metric=f"EUR {top['eur_m_per_mw']:.2f}m", metric_label=f"{top['oem']} price per MW", tone="neutral", where="Price per MW")


INSIGHT_BUILDERS: list[Callable[[Bundle], Insight | None]] = [
    insight_growth, insight_margin, insight_orders, insight_price, insight_backlog, insight_momentum, insight_share, insight_coverage,
    insight_product, insight_battles, insight_concentration, insight_shared_customers, insight_freshness,
]


def generate_insights(b: Bundle) -> list[Insight]:
    out = []
    for build in INSIGHT_BUILDERS:
        try:
            item = build(b)
        except Exception:  # a single failing template must not take the page down
            item = None
        if item is not None:
            out.append(item)
    return out


def watchlist(b: Bundle) -> list[str]:
    items: list[str] = []
    for oem, d in (b.latest.get("oems") or {}).items():
        if d.get("guidance"):
            items.append(f"{oem} guidance: {d['guidance']}.")
    q = b.quality
    for r in q[q["days_stale"] > 120].itertuples():
        items.append(f"{r.oem}'s order list ends {r.latest_order:%d %b %Y}; announced-MW comparisons for the latest months understate it.")
    items.append("Q3 2026 results (July-September) are due from Vestas, Nordex, Siemens Energy and GE Vernova in late October to early November; Suzlon follows later.")
    return items
