"""Streamlit layout for the OEM Briefing and the OEM Intelligence Lab tabs."""
from __future__ import annotations

import html

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from . import analysis as A
from .bundle import Bundle, build_bundle
from .insights import eur, generate_insights, mw, pc, watchlist

LAB_SECTIONS = ["Momentum & Share", "Reported vs Announced", "Product Race", "Market Battles", "Accounts", "Financial Profile", "Data Quality"]
TONE_COLORS = {"up": "#16A34A", "down": "#DC2626", "warn": "#D97706", "neutral": "#64748B"}


def _mtime(path) -> str:
    return str(path.stat().st_mtime_ns) if path.exists() else "missing"


def _signature(economy, orders, platforms) -> str:
    return "|".join([str(len(orders)), str(orders["order_date"].max()), f"{orders['size_mw'].sum():.1f}", str(len(platforms)), f"{economy['value'].sum():.1f}",
                     _mtime(A.DATA_DIR / "oem_latest_results.json"), _mtime(A.DATA_DIR / "fx_annual.json"), _mtime(A.DATA_DIR / "nordex_reported_intake.json"),
                     str(pd.Timestamp.today().normalize())])


@st.cache_data(show_spinner="Computing the cross-OEM intelligence...")
def _cached_bundle(signature: str, _economy, _orders, _platforms) -> Bundle:  # noqa: ARG001 - signature drives the cache
    return build_bundle(_economy, _orders, _platforms)


def get_bundle(economy, orders, platforms) -> Bundle:
    return _cached_bundle(_signature(economy, orders, platforms), economy, orders, platforms)


# ---------------------------------------------------------------- shared bits
def _template() -> str:
    return "plotly_dark" if st.session_state.get("dark_mode") else "plotly_white"


def _colors() -> dict[str, str]:
    return A.OEM_COLORS


def _show(fig: go.Figure, key: str, height: int = 400) -> None:
    fig.update_layout(template=_template(), height=height, margin=dict(l=8, r=8, t=56, b=8), legend_title_text="")
    st.plotly_chart(fig, width="stretch", key=key)


def _note(text: str) -> None:
    st.caption(text)


def _table(df: pd.DataFrame, label: str) -> None:
    with st.expander(label):
        st.dataframe(df, width="stretch")


def _card(i) -> str:
    color = TONE_COLORS.get(i.tone, TONE_COLORS["neutral"])
    return (
        f"<div class='ox-card' style='border-left:5px solid {color}'>"
        f"<div class='ox-metric' style='color:{color}'>{html.escape(i.metric)}<span>{html.escape(i.metric_label)}</span></div>"
        f"<div class='ox-head'>{html.escape(i.headline)}</div>"
        f"<div class='ox-detail'>{html.escape(i.detail)}</div>"
        f"<div class='ox-where'>{html.escape(i.where)}</div></div>"
    )


def _inject_css() -> None:
    dark = bool(st.session_state.get("dark_mode"))
    bg, border, text, sub = ("#111827", "#334155", "#E5E7EB", "#94A3B8") if dark else ("#FFFFFF", "#E2E8F0", "#0F172A", "#475569")
    st.markdown(
        f"""<style>
        .ox-grid {{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:14px;margin:6px 0 18px 0}}
        .ox-card {{background:{bg};border:1px solid {border};border-radius:10px;padding:14px 16px}}
        .ox-metric {{font-size:1.6rem;font-weight:700;line-height:1.1}}
        .ox-metric span {{display:block;font-size:.72rem;font-weight:500;color:{sub};text-transform:uppercase;letter-spacing:.04em;margin-top:2px}}
        .ox-head {{font-weight:650;color:{text};margin:8px 0 6px 0;font-size:1rem}}
        .ox-detail {{color:{sub};font-size:.86rem;line-height:1.45}}
        .ox-where {{margin-top:8px;font-size:.7rem;color:{sub};text-transform:uppercase;letter-spacing:.06em}}
        .ox-note {{border-left:3px solid {border};padding:6px 12px;color:{sub};font-size:.85rem;margin:4px 0 12px 0}}
        </style>""",
        unsafe_allow_html=True,
    )


def _scope(text: str) -> None:
    st.markdown(f"<div class='ox-note'>{html.escape(text)}</div>", unsafe_allow_html=True)


def _oems(frame: pd.DataFrame) -> list[str]:
    return [o for o in A.OEM_ORDER if o in set(frame["oem"])]


# ======================================================================================
# OEM Briefing
# ======================================================================================
def render_briefing(b: Bundle) -> None:
    _inject_css()
    sb = b.scoreboard
    colors = _colors()
    label = b.latest.get("period_label", "latest quarter")
    st.subheader("OEM Briefing")
    st.caption(
        f"Latest reported quarter for each OEM ({label}; Siemens Gamesa Q3 FY26, Suzlon Q1 FY27) next to what the order lists show. "
        "Everything is computed from the data; the sidebar filters apply to the other tabs, not to this one."
    )

    if not sb.empty:
        t = pd.DataFrame({
            "OEM": sb["oem"], "Period": sb["period"], "Revenue (EUR m)": sb["revenue_eur_m"].round(0), "Revenue y/y": sb["revenue_yoy"],
            "Profit measure": sb["profit_measure"], "Margin": sb["margin"], "Margin a year earlier": sb["margin_prior"],
            "Orders (EUR m)": sb["orders_value_eur_m"].round(0), "Book-to-bill": sb["book_to_bill"].round(2),
            "Order intake (MW)": sb["orders_mw"], "Backlog (EUR m)": sb["backlog_eur_m"].round(0), "Cover (years)": sb["backlog_cover_years"].round(1),
        })
        st.dataframe(
            t, width="stretch", hide_index=True,
            column_config={
                "Revenue y/y": st.column_config.NumberColumn(format="percent"), "Margin": st.column_config.NumberColumn(format="percent"),
                "Margin a year earlier": st.column_config.NumberColumn(format="percent"),
                "Revenue (EUR m)": st.column_config.NumberColumn(format="localized"), "Orders (EUR m)": st.column_config.NumberColumn(format="localized"),
                "Backlog (EUR m)": st.column_config.NumberColumn(format="localized"), "Order intake (MW)": st.column_config.NumberColumn(format="localized"),
            },
        )
        st.caption("Company definitions and currencies differ: GE is the Wind segment of GE Vernova (USD), Siemens Gamesa the segment of Siemens Energy, Suzlon reports in INR. "
                   "Converted to EUR at the average rate of 2026 to date. Orders include service where the company reports it.")

        c1, c2, c3 = st.columns(3)
        with c1:
            d = sb.dropna(subset=["revenue_yoy"])
            fig = px.bar(d, x="oem", y="revenue_yoy", color="oem", color_discrete_map=colors, title="Revenue growth y/y", text=d["revenue_yoy"].map(lambda v: pc(v, 0, True)))
            fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="", yaxis_tickformat=".0%")
            _show(fig, "brief_growth", 340)
        with c2:
            d = sb.dropna(subset=["margin"])
            fig = go.Figure()
            fig.add_bar(x=d["oem"], y=d["margin_prior"], name="Year earlier", marker_color="#94A3B8")
            fig.add_bar(x=d["oem"], y=d["margin"], name="Latest", marker_color=[colors.get(o, "#2F8FCE") for o in d["oem"]])
            fig.update_layout(title="Profit margin (own definition)", barmode="group", yaxis_tickformat=".0%", xaxis_title="", yaxis_title="")
            _show(fig, "brief_margin", 340)
        with c3:
            d = sb.dropna(subset=["book_to_bill"])
            fig = px.bar(d, x="oem", y="book_to_bill", color="oem", color_discrete_map=colors, title="Book-to-bill (latest quarter)", text=d["book_to_bill"].map(lambda v: f"{v:.2f}"))
            fig.add_hline(y=1.0, line_dash="dash", line_color="#64748B")
            fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="")
            _show(fig, "brief_b2b", 340)

    st.subheader("Key findings")
    items = generate_insights(b)
    if items:
        st.markdown("<div class='ox-grid'>" + "".join(_card(i) for i in items) + "</div>", unsafe_allow_html=True)
    st.subheader("What to watch next")
    st.markdown("\n".join(f"- {w}" for w in watchlist(b)))
    with st.expander("How to read this page"):
        st.markdown(
            "- **Latest quarter** figures come from each company's own results release (see `data/oem_latest_results.json` for sources); they are not restated to a common definition.\n"
            "- **Announced MW** comes from each OEM's order list (the per-OEM apps). The lists are not equally complete, so shares are shares of announced MW, not market share.\n"
            "- **Findings** are rule-based: each template pulls its numbers from the tables in the OEM Intelligence Lab tab."
        )


# ======================================================================================
# OEM Intelligence Lab
# ======================================================================================
def render_lab(b: Bundle) -> None:
    _inject_css()
    st.subheader("OEM Intelligence Lab")
    if hasattr(st, "segmented_control"):
        choice = st.segmented_control("Section", LAB_SECTIONS, default=LAB_SECTIONS[0], key="oem_lab_section", label_visibility="collapsed")
    else:
        choice = st.radio("Section", LAB_SECTIONS, horizontal=True, key="oem_lab_section", label_visibility="collapsed")
    choice = choice or LAB_SECTIONS[0]
    {"Momentum & Share": _momentum, "Reported vs Announced": _coverage, "Product Race": _product, "Market Battles": _battles,
     "Accounts": _accounts, "Financial Profile": _financial, "Data Quality": _quality}[choice](b)


def _momentum(b: Bundle) -> None:
    colors = _colors()
    _scope("Full dataset; ignores the sidebar filters. Announced MW only: see 'Reported vs Announced' for how complete each list is.")
    s = b.summary
    first = st.slider("From order year", int(s["year"].min()), int(s["year"].max()) - 1, 2018, key="lab_from")
    s = s[s["year"] >= first]
    c1, c2 = st.columns(2)
    with c1:
        sh = A.share_pivot(s).reset_index().melt(id_vars="year", var_name="oem", value_name="share").dropna()
        fig = px.bar(sh, x="year", y="share", color="oem", color_discrete_map=colors, title="Share of announced MW")
        fig.update_layout(yaxis_tickformat=".0%", xaxis_title="", yaxis_title="", barmode="stack")
        _show(fig, "lab_share", 420)
    with c2:
        fig = px.line(s, x="year", y="mw", color="oem", color_discrete_map=colors, markers=True, title="Announced MW per order year")
        fig.update_layout(xaxis_title="", yaxis_title="MW")
        _show(fig, "lab_mw", 420)
    st.markdown("**Last 12 months and year to date, each OEM to its own latest announced order**")
    m = b.momentum.copy()
    view = pd.DataFrame({"OEM": m["oem"], "Latest order": m["as_of"].dt.date, "Days since": m["days_stale"], "Last 12 months (MW)": m["ltm_mw"].round(0),
                         "Prior 12 months (MW)": m["prior_ltm_mw"].round(0), "12-month change": m["ltm_growth"], "Orders (12m)": m["ltm_orders"],
                         "Year to date (MW)": m["ytd_mw"].round(0), "Same days last year (MW)": m["ytd_prev_mw"].round(0), "YTD change": m["ytd_growth"]})
    st.dataframe(view, width="stretch", hide_index=True, column_config={"12-month change": st.column_config.NumberColumn(format="percent"), "YTD change": st.column_config.NumberColumn(format="percent")})
    cut_default = (m.loc[m["days_stale"] < 200, "as_of"].min() if (m["days_stale"] < 200).any() else m["as_of"].min()).date()
    cut = st.date_input("Common cut-off date for a like-for-like year-to-date comparison", value=cut_default, max_value=pd.Timestamp(b.today).date(), key="lab_cut")
    cd = A.calendar_to_date(b.orders, pd.Timestamp(cut))
    fig = go.Figure()
    fig.add_bar(x=cd["oem"], y=cd["prior_mw"], name=f"1 Jan - {(pd.Timestamp(cut) - pd.DateOffset(years=1)):%d %b %Y}", marker_color="#94A3B8")
    fig.add_bar(x=cd["oem"], y=cd["mw"], name=f"1 Jan - {pd.Timestamp(cut):%d %b %Y}", marker_color=[colors.get(o, "#2F8FCE") for o in cd["oem"]])
    fig.update_layout(title="Announced MW, same calendar window in both years", barmode="group", yaxis_title="MW", xaxis_title="")
    _show(fig, "lab_cut_chart", 380)
    c3, c4 = st.columns(2)
    with c3:
        fig = px.line(s, x="year", y="avg_mw", color="oem", color_discrete_map=colors, markers=True, title="Average announced order size (MW)")
        fig.update_layout(xaxis_title="", yaxis_title="MW")
        _show(fig, "lab_avg", 380)
    with c4:
        fig = px.line(s, x="year", y="mega_share", color="oem", color_discrete_map=colors, markers=True, title=f"Share of MW in orders of {A.MEGA_MW:,.0f} MW or more")
        fig.update_layout(xaxis_title="", yaxis_title="", yaxis_tickformat=".0%")
        _show(fig, "lab_mega", 380)
    _table(s.round(3), "Data table: annual summary per OEM")


def _coverage(b: Bundle) -> None:
    colors = _colors()
    _scope("Full dataset. Only Vestas and Nordex publish order intake in MW; the others report value or no order intake.")
    c = b.coverage
    if c.empty:
        st.info("No reported intake in MW available.")
        return
    c1, c2 = st.columns(2)
    with c1:
        long = c.melt(id_vars=["oem", "year"], value_vars=["mw", "reported_mw"], var_name="basis", value_name="MW")
        long["basis"] = long["basis"].map({"mw": "Announced list", "reported_mw": "Company-reported intake"})
        fig = px.line(long, x="year", y="MW", color="oem", line_dash="basis", color_discrete_map=colors, markers=True, title="Reported intake vs announced MW")
        fig.update_layout(xaxis_title="", yaxis_title="MW")
        _show(fig, "cov_lines", 420)
    with c2:
        fig = px.line(c, x="year", y="coverage", color="oem", color_discrete_map=colors, markers=True, title="Announced list as a share of reported intake")
        fig.update_layout(xaxis_title="", yaxis_title="", yaxis_tickformat=".0%")
        fig.add_hline(y=1.0, line_dash="dash", line_color="#64748B")
        _show(fig, "cov_ratio", 420)
    last = c.sort_values("year").groupby("oem").tail(1)
    st.markdown("**Latest full year:** " + "; ".join(f"{r.oem} {r.year}: list {mw(r.mw)} of {mw(r.reported_mw)} reported ({pc(r.coverage)})" for r in last.itertuples()))
    nd = A.load_nordex_reported()
    q = pd.DataFrame(nd.get("quarterly", []))
    if len(q):
        q = q[q["year"] >= 2024].copy()
        q["quarter_label"] = q["year"].astype(int).astype(str) + " Q" + q["quarter"].astype(int).astype(str)
        fig = px.bar(q, x="quarter_label", y="mw", title="Nordex reported Projects order intake per quarter (MW)", color_discrete_sequence=[colors.get("Nordex", "#F18F01")])
        fig.update_layout(xaxis_title="", yaxis_title="MW")
        _show(fig, "cov_nordex_q", 340)
    st.caption("Why the gap: orders from undisclosed customers, framework call-offs and small orders are not announced one by one. Siemens Gamesa and GE are not shown because they do not publish order intake in MW.")
    _table(c.round(3), "Data table: coverage")


def _product(b: Bundle) -> None:
    colors = _colors()
    _scope("Full dataset; MW-weighted over platform rows with a known rotor or rating.")
    p = b.product[b.product["year"] >= 2015]
    c1, c2 = st.columns(2)
    with c1:
        fig = px.line(p.dropna(subset=["rotor_avg_m"]), x="year", y="rotor_avg_m", color="oem", color_discrete_map=colors, markers=True, title="Average rotor diameter of ordered turbines (m)")
        fig.update_layout(xaxis_title="", yaxis_title="m")
        _show(fig, "prod_rotor", 400)
    with c2:
        fig = px.line(p.dropna(subset=["rating_avg_mw"]), x="year", y="rating_avg_mw", color="oem", color_discrete_map=colors, markers=True, title="Average rated power of ordered turbines (MW)")
        fig.update_layout(xaxis_title="", yaxis_title="MW")
        _show(fig, "prod_rating", 400)
    fig = px.line(p.dropna(subset=["large_rotor_share"]), x="year", y="large_rotor_share", color="oem", color_discrete_map=colors, markers=True, title=f"Share of ordered MW on rotors of {A.LARGE_ROTOR_M:.0f} m or more")
    fig.update_layout(xaxis_title="", yaxis_title="", yaxis_tickformat=".0%")
    _show(fig, "prod_large", 380)
    st.markdown(f"**Leading platforms since {b.since}** (share of each OEM's platform-mapped MW)")
    tp = b.top_platforms.copy()
    tp["rank"] = tp.groupby("oem").cumcount() + 1
    tbl = tp.pivot(index="oem", columns="rank", values="platform").rename(columns=lambda r: f"#{r} platform")
    shr = tp.pivot(index="oem", columns="rank", values="share").rename(columns=lambda r: f"#{r} share").map(lambda v: pc(v))
    both = pd.concat([tbl, shr], axis=1)
    both = both[[c for r in (1, 2, 3) for c in (f"#{r} platform", f"#{r} share") if c in both.columns]].reindex(_oems(tp.assign(oem=tp["oem"])))
    st.dataframe(both, width="stretch")
    st.caption("Vestas and Siemens Gamesa averages include offshore turbines. Platform rows with no stated model are excluded; see Data Quality for how many.")
    _table(b.product.round(3), "Data table: product metrics per OEM and year")


def _battles(b: Bundle) -> None:
    colors = _colors()
    since = st.slider("Orders since year", 2018, int(b.orders["order_year"].max()), b.since, key="bat_since")
    _scope("Full dataset. Announced MW with a single known country; combined-country orders are left out.")
    matrix = A.country_matrix(b.orders, since)
    top_n = st.slider("Countries shown", 8, 30, 15, key="bat_n")
    shown = matrix.head(top_n)
    oems = [c for c in shown.columns if c != "total"]
    long = shown[oems].reset_index().melt(id_vars="country", var_name="oem", value_name="mw")
    fig = px.bar(long, y="country", x="mw", color="oem", orientation="h", color_discrete_map=colors, title=f"Largest markets by announced MW since {since}")
    fig.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="MW", yaxis_title="")
    _show(fig, "bat_bars", max(420, 28 * top_n + 120))
    bt = A.battle_table(matrix, top=top_n)
    view = pd.DataFrame({"Country": bt["country"], "MW": bt["total_mw"].round(0), "Leader": bt["leader"], "Leader share": bt["leader_share"], "Runner-up": bt["runner_up"],
                         "Runner-up share": bt["runner_up_share"], "OEMs present": bt["oems_present"], "Contested": bt["contested"].map({True: "yes", False: ""})})
    st.dataframe(view, width="stretch", hide_index=True, column_config={"Leader share": st.column_config.NumberColumn(format="percent"), "Runner-up share": st.column_config.NumberColumn(format="percent")})
    st.caption("Contested = at least two OEMs with 15% or more of the announced MW in that country.")
    c1, c2 = st.columns(2)
    with c1:
        cm = A.continent_mix(b.orders, since).reset_index().melt(id_vars="oem", var_name="continent", value_name="share")
        fig = px.bar(cm, x="oem", y="share", color="continent", title="Continent mix per OEM", barmode="stack")
        fig.update_layout(yaxis_tickformat=".0%", xaxis_title="", yaxis_title="")
        _show(fig, "bat_cont", 400)
    with c2:
        heat = (matrix.head(top_n)[oems].div(matrix.head(top_n)["total"], axis=0))
        fig = px.imshow(heat, text_auto=".0%", aspect="auto", color_continuous_scale="Blues", title="Share of each market held by each OEM")
        fig.update_layout(coloraxis_showscale=False)
        _show(fig, "bat_heat", 400)
    g = A.geography_profile(b.orders, since)
    st.markdown("**Geographic concentration**")
    st.dataframe(pd.DataFrame({"OEM": g["oem"], "Countries": g["countries"], "Top country": g["top_country"], "Top country share": g["top_country_share"], "Top 3 share": g["top3_share"], "Concentration (HHI)": g["hhi"].round(2)}),
                 width="stretch", hide_index=True, column_config={"Top country share": st.column_config.NumberColumn(format="percent"), "Top 3 share": st.column_config.NumberColumn(format="percent")})
    oem_pick = st.selectbox("Country movers for", _oems(b.orders), key="bat_mover_oem")
    mv = A.country_movers(b.orders, oem_pick)
    if mv["delta_mw"].abs().sum():
        d = pd.concat([mv.head(6), mv.tail(6)]).drop_duplicates().reset_index()
        d["colour"] = np.where(d["delta_mw"] >= 0, "Up", "Down")
        fig = px.bar(d, y="country", x="delta_mw", color="colour", orientation="h", color_discrete_map={"Up": "#16A34A", "Down": "#DC2626"}, title=f"{oem_pick}: change in announced MW, last 12 months vs the 12 before")
        fig.update_layout(yaxis=dict(autorange="reversed"), showlegend=False, xaxis_title="MW", yaxis_title="")
        _show(fig, "bat_movers", 420)
    _table(matrix.round(0), "Data table: announced MW by country and OEM")


def _accounts(b: Bundle) -> None:
    _scope("Full dataset. Customer names are cleaned (legal suffixes and case) and matched exactly; undisclosed customers are excluded.")
    since = st.slider("Orders since year", 2015, int(b.orders["order_year"].max()), b.since, key="acc_since")
    sh = A.shared_customers(b.orders, 2, since)
    d = A.customer_dependence(b.orders, since)
    c1, c2 = st.columns([3, 2])
    with c1:
        st.markdown(f"**Customers that bought from more than one OEM since {since}** ({len(sh)})")
        if sh.empty:
            st.info("No shared customers in this window.")
        else:
            cols = ["customer"] + [c for c in A.OEM_ORDER if c in sh.columns] + ["total_mw", "oems"]
            st.dataframe(sh[cols].rename(columns={"customer": "Customer", "total_mw": "Total MW", "oems": "OEMs"}).round(0), width="stretch", hide_index=True, height=440)
    with c2:
        st.markdown("**Customer dependence**")
        st.dataframe(pd.DataFrame({"OEM": d["oem"], "Named customers": d["customers"], "Top customer": d["top_customer"], "Top share": d["top_share"], "Top 5 share": d["top5_share"]}),
                     width="stretch", hide_index=True, column_config={"Top share": st.column_config.NumberColumn(format="percent"), "Top 5 share": st.column_config.NumberColumn(format="percent")})
    if not sh.empty:
        top = sh.head(12)
        long = top.melt(id_vars="customer", value_vars=[c for c in A.OEM_ORDER if c in top.columns], var_name="oem", value_name="mw")
        long = long[long["mw"] > 0]
        fig = px.bar(long, y="customer", x="mw", color="oem", orientation="h", color_discrete_map=_colors(), title="Largest multi-vendor customers (MW by OEM)")
        fig.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="MW", yaxis_title="")
        _show(fig, "acc_multi", 460)
    und = b.quality.sort_values("customer_undisclosed_recent", ascending=False).head(2)
    st.caption("Multi-vendor buyers are the contestable accounts. Counts are a floor: name matching is exact after cleaning, and many names are undisclosed ("
               + ", ".join(f"{pc(r.customer_undisclosed_recent)} of recent {r.oem} orders" for r in und.itertuples()) + ").")


def _financial(b: Bundle) -> None:
    colors = _colors()
    _scope("Full dataset. Annual figures in EUR m (GE converted from USD at the calendar-year average rate); fiscal years: Siemens Gamesa ends September, Suzlon ends March.")
    f = b.fin
    first = st.slider("From year", int(f["year"].min()), int(f["year"].max()) - 1, 2018, key="fin_from")
    f = f[f["year"] >= first]
    c1, c2 = st.columns(2)
    with c1:
        fig = px.line(f.dropna(subset=["revenue_eur_m"]), x="year", y="revenue_eur_m", color="oem", color_discrete_map=colors, markers=True, title="Revenue (EUR m)")
        fig.update_layout(xaxis_title="", yaxis_title="")
        _show(fig, "fin_rev", 400)
    with c2:
        fig = px.line(f.dropna(subset=["book_to_bill"]), x="year", y="book_to_bill", color="oem", color_discrete_map=colors, markers=True, title="Book-to-bill (order intake / revenue)")
        fig.add_hline(y=1.0, line_dash="dash", line_color="#64748B")
        fig.update_layout(xaxis_title="", yaxis_title="")
        _show(fig, "fin_b2b", 400)
    fig = px.line(f.dropna(subset=["margin"]), x="year", y="margin", color="oem", color_discrete_map=colors, markers=True, title="Profit margin (EBIT / EBITDA / net profit, see table)")
    fig.update_layout(xaxis_title="", yaxis_title="", yaxis_tickformat=".0%")
    _show(fig, "fin_margin", 380)
    measures = f.groupby("oem")["profit_measure"].first()
    st.caption("Profit measure per OEM: " + ", ".join(f"{o} = {m}" for o, m in measures.items()) + ". Suzlon's annual profit and order value are not in the combined dataset. Margins are not like-for-like across companies.")
    _table(f.round(3), "Data table: annual financial profile")


def _quality(b: Bundle) -> None:
    _scope("Full dataset.")
    q = b.quality
    st.subheader("Data quality and comparability")
    view = pd.DataFrame({"OEM": q["oem"], "Orders": q["orders"], "From": q["first_year"], "Latest order": q["latest_order"].dt.date, "Days since": q["days_stale"], "Economy to": q["economy_to"],
                         "Customer undisclosed": q["customer_undisclosed"], "...in recent years": q["customer_undisclosed_recent"], "Platform unknown": q["platform_unknown"],
                         "Country unknown": q["country_unknown"], "Possible duplicates": q["duplicates"]})
    pct = {c: st.column_config.NumberColumn(format="percent") for c in ["Customer undisclosed", "...in recent years", "Platform unknown", "Country unknown"]}
    st.dataframe(view, width="stretch", hide_index=True, column_config=pct)
    st.markdown("**Comparability notes**")
    cnt = b.summary.pivot(index="year", columns="oem", values="orders")
    thin = [f"{o} ({int(cnt[o].iloc[-2])} orders in {int(cnt.index[-2])} vs {cnt.loc[2020:2022, o].mean():.0f} a year in 2020-2022)" for o in cnt.columns
            if cnt.loc[2020:2022, o].mean() >= 10 and cnt[o].iloc[-2] < 0.4 * cnt.loc[2020:2022, o].mean()]
    notes = [
        "Order lists are not equally complete: reported intake in MW is available for Vestas and Nordex only (see Reported vs Announced)."
        + (" Lists that have thinned out: " + "; ".join(thin) + ", so their announced-MW shares understate them." if thin else ""),
        "GE's list is onshore orders announced by press release (plus 1.1 GW of 2025 bookings announced only in aggregate); Wind segment results include offshore and services.",
        "Fiscal years: Siemens Gamesa Oct-Sep, Suzlon Apr-Mar, others calendar year; annual charts label them by the year in which the fiscal year ends.",
        "Currencies: GE in USD and Suzlon in INR are converted at ECB reference-rate averages (data/fx_annual.json); the latest year is year to date.",
        "Segment definitions: GE and Siemens Gamesa are segments of larger groups; their margins are segment measures (EBITDA and profit before special items).",
    ]
    st.markdown("\n".join(f"- {n}" for n in notes))
    with st.expander("Latest-quarter source notes"):
        for oem, d in (b.latest.get("oems") or {}).items():
            st.markdown(f"**{oem}** ({d['period']}): {d.get('source', '')}. {d.get('also', '')}")
        st.caption(f"Retrieved {b.latest.get('retrieved', 'n/a')}.")
