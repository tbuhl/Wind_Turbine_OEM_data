from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

APP_TITLE = "Wind Turbine OEM Benchmark Dashboard"
APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent

OEM_CACHE_PATH_CANDIDATES = {
    "Vestas": [
        APP_DIR / "data_cache" / "vestas_parsed_data.pkl",
        PROJECT_ROOT / "Vestas_sales" / "data_cache" / "vestas_parsed_data.pkl",
    ],
    "Nordex": [
        APP_DIR / "data_cache" / "nordex_parsed_data.pkl",
        PROJECT_ROOT / "nordex_sales" / "data_cache" / "nordex_parsed_data.pkl",
    ],
    "Siemens Gamesa": [
        APP_DIR / "data_cache" / "sgre_parsed_data.pkl",
        PROJECT_ROOT / "SGRE_sales" / "data_cache" / "sgre_parsed_data.pkl",
    ],
    "Suzlon": [
        APP_DIR / "data_cache" / "suzlon_parsed_data.pkl",
        PROJECT_ROOT / "Suzlon_sales" / "data_cache" / "suzlon_parsed_data.pkl",
    ],
}

TURBINE_CATALOG_FILE = APP_DIR / "data" / "oem_turbine_catalog.json"

OEM_COLORS = {
    "Vestas": "#2F8FCE",
    "Nordex": "#F18F01",
    "Siemens Gamesa": "#5E8F49",
    "Suzlon": "#D1495B",
}


def apply_page_style(dark_mode: bool) -> None:
    if dark_mode:
        text_color = "#f5f7fb"
        muted_color = "#a6b3c3"
        bg_main = (
            "radial-gradient(1200px 620px at 96% -12%, rgba(250, 204, 21, 0.16) 0%, rgba(250, 204, 21, 0) 52%),"
            "radial-gradient(900px 520px at -4% 18%, rgba(16, 185, 129, 0.18) 0%, rgba(16, 185, 129, 0) 48%),"
            "linear-gradient(180deg, #090d16 0%, #0d1424 100%)"
        )
        bg_sidebar = "linear-gradient(180deg, rgba(11, 17, 31, 0.95) 0%, rgba(8, 12, 22, 0.98) 100%)"
        header_bg = "rgba(9, 14, 26, 0.82)"
        header_border = "rgba(250, 204, 21, 0.20)"
        card_bg = "rgba(17, 24, 39, 0.62)"
        card_border = "rgba(148, 163, 184, 0.28)"
        card_shadow = "0 24px 56px rgba(0, 0, 0, 0.48), 0 8px 18px rgba(0, 0, 0, 0.25)"
        card_glow = "rgba(250, 204, 21, 0.26)"
        frame_border = "rgba(148, 163, 184, 0.25)"
        metric_label_color = "#d5deea"
        metric_value_color = "#ffffff"
        metric_delta_color = "#f8fafc"
        tab_bg = "rgba(17, 24, 39, 0.66)"
        tab_active_bg = "linear-gradient(120deg, rgba(234, 179, 8, 0.30), rgba(16, 185, 129, 0.28))"
        tab_hover_bg = "rgba(30, 41, 59, 0.80)"
        tab_border = "rgba(148, 163, 184, 0.25)"
        tab_active_border = "rgba(250, 204, 21, 0.40)"
        tab_text_color = "#d7e0ec"
        tab_active_text_color = "#ffffff"
        input_bg = "rgba(15, 23, 42, 0.78)"
        input_border = "rgba(148, 163, 184, 0.30)"
        input_focus = "rgba(250, 204, 21, 0.42)"
        accent_start = "#facc15"
        accent_end = "#10b981"
        link_color = "#a7f3d0"
        link_hover = "#fde047"
        chart_wrap_bg = "rgba(17, 24, 39, 0.56)"
        chart_wrap_border = "rgba(148, 163, 184, 0.25)"
    else:
        text_color = "#0f172a"
        muted_color = "#475569"
        bg_main = (
            "radial-gradient(1200px 620px at 94% -10%, rgba(250, 204, 21, 0.28) 0%, rgba(250, 204, 21, 0) 50%),"
            "radial-gradient(1000px 540px at -8% 20%, rgba(52, 211, 153, 0.24) 0%, rgba(52, 211, 153, 0) 46%),"
            "linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%)"
        )
        bg_sidebar = "linear-gradient(180deg, rgba(255, 255, 255, 0.88) 0%, rgba(248, 250, 252, 0.94) 100%)"
        header_bg = "rgba(255, 255, 255, 0.78)"
        header_border = "rgba(15, 23, 42, 0.10)"
        card_bg = "rgba(255, 255, 255, 0.66)"
        card_border = "rgba(15, 23, 42, 0.10)"
        card_shadow = "0 26px 52px rgba(2, 6, 23, 0.12), 0 8px 18px rgba(2, 6, 23, 0.08)"
        card_glow = "rgba(16, 185, 129, 0.20)"
        frame_border = "rgba(15, 23, 42, 0.11)"
        metric_label_color = "#334155"
        metric_value_color = "#0f172a"
        metric_delta_color = "#0f172a"
        tab_bg = "rgba(255, 255, 255, 0.72)"
        tab_active_bg = "linear-gradient(120deg, rgba(254, 240, 138, 0.74), rgba(167, 243, 208, 0.72))"
        tab_hover_bg = "rgba(255, 255, 255, 0.90)"
        tab_border = "rgba(15, 23, 42, 0.12)"
        tab_active_border = "rgba(16, 185, 129, 0.44)"
        tab_text_color = "#334155"
        tab_active_text_color = "#0f172a"
        input_bg = "rgba(255, 255, 255, 0.80)"
        input_border = "rgba(15, 23, 42, 0.14)"
        input_focus = "rgba(16, 185, 129, 0.36)"
        accent_start = "#eab308"
        accent_end = "#10b981"
        link_color = "#0f766e"
        link_hover = "#a16207"
        chart_wrap_bg = "rgba(255, 255, 255, 0.58)"
        chart_wrap_border = "rgba(15, 23, 42, 0.11)"

    st.markdown(
        f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito+Sans:wght@400;600;700;800&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,300..700,0..1,-50..200');
@import url('https://fonts.googleapis.com/icon?family=Material+Icons');

html, body, .stApp {{
  font-family: 'Nunito Sans', sans-serif;
  color: {text_color};
}}

.stApp {{
  background: {bg_main};
  background-attachment: fixed;
}}

.block-container {{
  padding-top: 1.2rem;
  padding-bottom: 2rem;
}}

h1, h2, h3, h4, h5, h6 {{
  letter-spacing: -0.01em;
  font-weight: 700;
}}

h1 {{
  font-weight: 800;
  background-image: linear-gradient(110deg, {accent_start} 0%, {accent_end} 56%, {text_color} 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}}

p, span, label, li {{
  color: {text_color};
}}

a {{
  color: {link_color};
  text-decoration-color: {link_color};
}}

a:hover {{
  color: {link_hover};
  text-decoration-color: {link_hover};
}}

section[data-testid="stSidebar"] {{
  background: {bg_sidebar};
  border-right: 1px solid {frame_border};
  backdrop-filter: blur(9px);
}}

section[data-testid="stSidebar"] * {{
  color: {text_color};
}}

[data-testid="stHeader"],
[data-testid="stToolbar"] {{
  background: {header_bg} !important;
  border-bottom: 1px solid {header_border} !important;
  backdrop-filter: blur(12px);
}}

[data-testid="stDecoration"] {{
  background: transparent !important;
}}

/* Keep material icons rendered as icons (avoid ligature text like keyboard_double_arrow_right). */
[class*="material-icons"],
[class*="material-symbols"],
[data-testid="stHeader"] button span,
[data-testid="stToolbar"] button span,
[data-testid="collapsedControl"] span,
[data-testid="stSidebarCollapseButton"] span,
[data-testid="stSidebarNav"] button span,
button[aria-label*="sidebar"] span,
button[aria-label*="Sidebar"] span,
button[title*="sidebar"] span,
button[title*="Sidebar"] span {{
  font-family: "Material Symbols Rounded", "Material Symbols Outlined", "Material Icons" !important;
  font-feature-settings: "liga" 1, "calt" 1;
  -webkit-font-feature-settings: "liga" 1, "calt" 1;
  font-weight: normal;
  font-style: normal;
  letter-spacing: normal;
  text-transform: none;
}}

section[data-testid="stSidebar"] div[data-baseweb="select"] > div,
section[data-testid="stSidebar"] div[data-baseweb="input"] > div,
section[data-testid="stSidebar"] div[data-testid="stNumberInput"] input,
section[data-testid="stSidebar"] div[data-testid="stTextInput"] input {{
  background: {input_bg};
  border: 1px solid {input_border};
  color: {text_color};
  border-radius: 10px;
}}

section[data-testid="stSidebar"] div[data-baseweb="select"] > div:focus-within,
section[data-testid="stSidebar"] div[data-baseweb="input"] > div:focus-within,
section[data-testid="stSidebar"] div[data-testid="stNumberInput"] input:focus,
section[data-testid="stSidebar"] div[data-testid="stTextInput"] input:focus {{
  border-color: {input_focus} !important;
  box-shadow: 0 0 0 2px {input_focus} !important;
}}

section[data-testid="stSidebar"] div[data-testid="stLinkButton"] > a,
section[data-testid="stSidebar"] .stLinkButton > a {{
  width: calc(100% - 0.5rem) !important;
  margin: 0.2rem 0.25rem !important;
  justify-content: center !important;
  text-align: center !important;
  border-radius: 0.65rem !important;
  font-weight: 700 !important;
}}

div[data-testid="stAlert"],
div[data-testid="stDataFrame"] {{
  background: radial-gradient(65% 80% at 50% 0%, {card_glow} 0%, rgba(255,255,255,0) 100%), {card_bg};
  border: 1px solid {card_border};
  border-radius: 14px;
  box-shadow: {card_shadow};
  backdrop-filter: blur(8px);
}}

div[data-testid="stMetric"] {{
  background: radial-gradient(65% 80% at 50% 0%, {card_glow} 0%, rgba(255,255,255,0) 100%), {card_bg};
  border: 1px solid {card_border};
  border-radius: 14px;
  padding: 0.45rem 0.82rem;
  box-shadow: {card_shadow};
  backdrop-filter: blur(8px);
}}

div[data-testid="stMetric"] div[data-testid="stMetricLabel"] {{
  color: {metric_label_color} !important;
  font-weight: 700 !important;
}}

div[data-testid="stMetric"] div[data-testid="stMetricValue"] {{
  color: {metric_value_color} !important;
  letter-spacing: -0.01em;
}}

div[data-testid="stMetricDelta"] {{
  color: {metric_delta_color} !important;
  font-size: 0.72rem !important;
  line-height: 1.05 !important;
}}

div[data-testid="stPlotlyChart"] {{
  background: radial-gradient(65% 80% at 50% 0%, {card_glow} 0%, rgba(255,255,255,0) 100%), {chart_wrap_bg};
  border: 1px solid {chart_wrap_border};
  border-radius: 16px;
  padding: 0.35rem 0.45rem 0.2rem 0.45rem;
  box-shadow: {card_shadow};
  backdrop-filter: blur(8px);
}}

.stTabs [data-baseweb="tab-list"] {{
  gap: 0.4rem;
  padding-bottom: 0.1rem;
}}

.stTabs [data-baseweb="tab"] {{
  background: {tab_bg};
  border: 1px solid {tab_border};
  color: {tab_text_color} !important;
  border-radius: 11px 11px 0 0;
  padding-top: 0.42rem;
  padding-bottom: 0.48rem;
  transition: all 0.18s ease;
}}

.stTabs [data-baseweb="tab"]:hover {{
  background: {tab_hover_bg};
  border-color: {tab_active_border};
  transform: translateY(-1px);
}}

.stTabs [data-baseweb="tab"][aria-selected="true"] {{
  background: {tab_active_bg} !important;
  color: {tab_active_text_color} !important;
  border-color: {tab_active_border} !important;
  box-shadow: 0 10px 24px rgba(2, 6, 23, 0.18);
}}

[data-testid="stCaptionContainer"] p,
[data-testid="stCaptionContainer"] span,
.small-note {{
  color: {muted_color} !important;
}}

.freshness-wrap {{
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  margin: 0.2rem 0 0.55rem 0;
}}

.freshness-badge {{
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.32rem 0.58rem;
  border-radius: 999px;
  border: 1px solid {frame_border};
  font-size: 0.78rem;
  line-height: 1.15;
  white-space: nowrap;
}}
</style>
        """,
        unsafe_allow_html=True,
    )


def plotly_template() -> str:
    return "plotly_dark" if st.session_state.get("dark_mode", False) else "plotly_white"


def metric_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def pick_metric(metrics: list[str], token_options: list[list[str]]) -> str | None:
    for tokens in token_options:
        for metric in metrics:
            key = metric_key(metric)
            if all(token in key for token in tokens):
                return metric
    return None


def ensure_columns(frame: pd.DataFrame, defaults: dict[str, Any]) -> pd.DataFrame:
    out = frame.copy()
    for col, default in defaults.items():
        if col not in out.columns:
            out[col] = default
    return out


def file_signature(path: Path) -> str:
    if not path.exists():
        return f"{path}::missing"
    stat = path.stat()
    return f"{path.resolve()}::{stat.st_mtime_ns}::{stat.st_size}"


def resolve_oem_cache_files() -> dict[str, Path]:
    resolved: dict[str, Path] = {}
    for oem, candidates in OEM_CACHE_PATH_CANDIDATES.items():
        found = None
        for path in candidates:
            if path.exists():
                found = path
                break
        resolved[oem] = found if found is not None else candidates[0]
    return resolved


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    color = str(hex_color).strip().lstrip("#")
    if len(color) != 6:
        return f"rgba(100,116,139,{alpha})"
    try:
        r = int(color[0:2], 16)
        g = int(color[2:4], 16)
        b = int(color[4:6], 16)
    except ValueError:
        return f"rgba(100,116,139,{alpha})"
    return f"rgba({r},{g},{b},{alpha})"


@st.cache_data(show_spinner=False)
def load_all_oem_data(_signature: str, cache_paths: dict[str, str]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[str]]:
    economy_frames: list[pd.DataFrame] = []
    order_frames: list[pd.DataFrame] = []
    platform_frames: list[pd.DataFrame] = []
    issues: list[str] = []

    for oem, path_txt in cache_paths.items():
        path = Path(path_txt)
        if not path.exists():
            issues.append(f"Missing cache for {oem}: `{path}`")
            continue

        try:
            payload = pd.read_pickle(path)
        except Exception as exc:
            issues.append(f"Could not read cache for {oem}: {exc}")
            continue

        if not isinstance(payload, dict):
            issues.append(f"Invalid cache payload format for {oem}: `{path}`")
            continue

        economy = payload.get("economy", pd.DataFrame(columns=["metric", "year", "value"]))
        orders = payload.get("orders", pd.DataFrame())
        platforms = payload.get("platforms", pd.DataFrame())

        if not isinstance(economy, pd.DataFrame):
            economy = pd.DataFrame(columns=["metric", "year", "value"])
        if not isinstance(orders, pd.DataFrame):
            orders = pd.DataFrame()
        if not isinstance(platforms, pd.DataFrame):
            platforms = pd.DataFrame()

        economy = ensure_columns(
            economy,
            {
                "metric": "Unknown",
                "year": np.nan,
                "value": np.nan,
            },
        )
        orders = ensure_columns(
            orders,
            {
                "order_id": "",
                "sheet_name": "",
                "sheet_year": np.nan,
                "order_date": pd.NaT,
                "order_year": np.nan,
                "order_quarter": np.nan,
                "country": "Unknown",
                "region": "Unknown",
                "continent": "Unknown",
                "service_scheme": "Unknown",
                "service_time_years": np.nan,
                "customer": "Unknown",
                "size_mw": np.nan,
                "delivery_days": np.nan,
            },
        )
        platforms = ensure_columns(
            platforms,
            {
                "order_id": "",
                "sheet_year": np.nan,
                "order_year": np.nan,
                "country": "Unknown",
                "region": "Unknown",
                "continent": "Unknown",
                "service_scheme": "Unknown",
                "service_time_years": np.nan,
                "customer": "Unknown",
                "slot": np.nan,
                "platform": "Unknown",
                "turbines_qty": np.nan,
                "rotor_m": np.nan,
                "mw_rating": np.nan,
                "slot_mw": np.nan,
            },
        )

        economy["oem"] = oem
        orders["oem"] = oem
        platforms["oem"] = oem

        economy["year"] = pd.to_numeric(economy["year"], errors="coerce")
        economy["value"] = pd.to_numeric(economy["value"], errors="coerce")

        orders["order_year"] = pd.to_numeric(orders["order_year"], errors="coerce")
        orders["size_mw"] = pd.to_numeric(orders["size_mw"], errors="coerce")
        orders["service_time_years"] = pd.to_numeric(orders["service_time_years"], errors="coerce")
        orders["delivery_days"] = pd.to_numeric(orders["delivery_days"], errors="coerce")
        orders["order_date"] = pd.to_datetime(orders["order_date"], errors="coerce")

        platforms["order_year"] = pd.to_numeric(platforms["order_year"], errors="coerce")
        platforms["rotor_m"] = pd.to_numeric(platforms["rotor_m"], errors="coerce")
        platforms["mw_rating"] = pd.to_numeric(platforms["mw_rating"], errors="coerce")
        platforms["slot_mw"] = pd.to_numeric(platforms["slot_mw"], errors="coerce")
        platforms["service_time_years"] = pd.to_numeric(platforms["service_time_years"], errors="coerce")

        order_frames.append(orders)
        economy_frames.append(economy)
        platform_frames.append(platforms)

    economy_all = pd.concat(economy_frames, ignore_index=True) if economy_frames else pd.DataFrame(columns=["metric", "year", "value", "oem"])
    orders_all = pd.concat(order_frames, ignore_index=True) if order_frames else pd.DataFrame()
    platforms_all = pd.concat(platform_frames, ignore_index=True) if platform_frames else pd.DataFrame()

    return economy_all, orders_all, platforms_all, issues


@st.cache_data(show_spinner=False)
def load_cache_freshness(_signature: str, cache_paths: dict[str, str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for oem, path_txt in cache_paths.items():
        path = Path(path_txt)
        row: dict[str, Any] = {
            "oem": oem,
            "cache_generated_utc": pd.NaT,
            "latest_order_date": pd.NaT,
            "latest_order_year": np.nan,
            "file_modified_local": pd.NaT,
            "source_location": "repo" if APP_DIR in path.parents else "external",
        }
        if path.exists():
            row["file_modified_local"] = pd.to_datetime(path.stat().st_mtime, unit="s", errors="coerce")
            try:
                payload = pd.read_pickle(path)
                if isinstance(payload, dict):
                    row["cache_generated_utc"] = pd.to_datetime(payload.get("generated_utc"), errors="coerce", utc=True)
                    orders = payload.get("orders")
                    if isinstance(orders, pd.DataFrame) and not orders.empty:
                        order_dates = pd.to_datetime(orders.get("order_date"), errors="coerce")
                        if not order_dates.dropna().empty:
                            row["latest_order_date"] = order_dates.max()
                        order_year = pd.to_numeric(orders.get("order_year"), errors="coerce")
                        if not order_year.dropna().empty:
                            row["latest_order_year"] = float(order_year.max())
            except Exception:
                pass
        rows.append(row)
    return pd.DataFrame(rows)


def render_data_freshness_badges(freshness: pd.DataFrame) -> None:
    if freshness is None or freshness.empty:
        return
    parts: list[str] = []
    for row in freshness.itertuples(index=False):
        oem = str(row.oem)
        color = OEM_COLORS.get(oem, "#64748B")
        generated = pd.to_datetime(row.cache_generated_utc, errors="coerce", utc=True)
        modified = pd.to_datetime(row.file_modified_local, errors="coerce")
        latest_order = pd.to_datetime(row.latest_order_date, errors="coerce")
        latest_year = row.latest_order_year

        if pd.notna(generated):
            cache_txt = generated.strftime("%Y-%m-%d %H:%M UTC")
        elif pd.notna(modified):
            cache_txt = modified.strftime("%Y-%m-%d %H:%M")
        else:
            cache_txt = "-"

        if pd.notna(latest_order):
            order_txt = latest_order.strftime("%Y-%m-%d")
        elif pd.notna(latest_year):
            order_txt = str(int(float(latest_year)))
        else:
            order_txt = "-"

        parts.append(
            f"<span class='freshness-badge' style='border-color:{hex_to_rgba(color, 0.55)};"
            f"background:{hex_to_rgba(color, 0.14)};'>"
            f"<strong>{oem}</strong> cache: {cache_txt} | latest order: {order_txt}"
            "</span>"
        )
    if parts:
        st.markdown("**Data Freshness**")
        st.markdown("<div class='freshness-wrap'>" + "".join(parts) + "</div>", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def load_turbine_catalog(_signature: str) -> tuple[pd.DataFrame, str | None, list[str]]:
    if not TURBINE_CATALOG_FILE.exists():
        return pd.DataFrame(), None, []

    try:
        payload = json.loads(TURBINE_CATALOG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return pd.DataFrame(), None, []

    models = payload.get("models", [])
    if not isinstance(models, list):
        return pd.DataFrame(), payload.get("generated_utc"), payload.get("failed_sources", [])

    df = pd.DataFrame(models)
    if df.empty:
        return df, payload.get("generated_utc"), payload.get("failed_sources", [])

    for col in ["rotor_diameter_m", "rated_power_mw"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "source_urls" not in df.columns:
        df["source_urls"] = [[] for _ in range(len(df))]

    return df, payload.get("generated_utc"), payload.get("failed_sources", [])


def metric_series(economy_oem: pd.DataFrame, token_options: list[list[str]], scale: float = 1.0) -> pd.DataFrame:
    if economy_oem.empty:
        return pd.DataFrame(columns=["year", "value"])

    metrics = sorted(economy_oem["metric"].dropna().astype(str).unique().tolist(), key=metric_key)
    chosen = pick_metric(metrics, token_options)
    if chosen is None:
        return pd.DataFrame(columns=["year", "value"])

    out = economy_oem[economy_oem["metric"] == chosen][["year", "value"]].copy()
    out = out.dropna(subset=["year", "value"])
    if out.empty:
        return pd.DataFrame(columns=["year", "value"])

    out["year"] = pd.to_numeric(out["year"], errors="coerce")
    out["value"] = pd.to_numeric(out["value"], errors="coerce") * scale
    out = out.dropna(subset=["year", "value"])
    out["year"] = out["year"].astype(int)
    out = out.groupby("year", as_index=False)["value"].mean()
    return out


def build_economy_comparison(economy: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []

    for oem, frame in economy.groupby("oem"):
        econ = frame.copy()

        revenue_tokens_map = {
            "Vestas": [["revenue", "meur"], ["revenue"]],
            "Nordex": [["gross", "revenue"], ["revenue"]],
            "Siemens Gamesa": [["total", "revenue"], ["revenue"]],
            "Suzlon": [["revenue", "meur", "converted"], ["revenue", "converted"], ["revenue", "meur"]],
        }
        revenue_tokens = revenue_tokens_map.get(oem, [["revenue", "meur"], ["revenue"]])
        revenue = metric_series(econ, revenue_tokens, scale=1.0)
        if not revenue.empty:
            revenue["oem"] = oem
            revenue["metric_name"] = "Revenue (mEUR, as reported)"
            rows.append(revenue)

        intake_map: dict[str, tuple[list[list[str]], float]] = {
            "Vestas": ([["order", "intake", "bneur"], ["order", "intake"]], 1000.0),
            "Nordex": ([["order", "intake", "m"], ["order", "intake", "eur"]], 1.0),
            "Siemens Gamesa": (
                [["total", "order", "intake"], ["firm", "order", "intake"], ["order", "intake", "eur"]],
                1.0,
            ),
        }
        if oem in intake_map:
            intake_tokens, intake_scale = intake_map[oem]
            intake = metric_series(econ, intake_tokens, scale=intake_scale)
            if not intake.empty:
                intake["oem"] = oem
                intake["metric_name"] = "Order intake value (mEUR, normalized)"
                rows.append(intake)

        if oem == "Vestas":
            wind = metric_series(econ, [["order", "backlog", "wind", "bneur"]], scale=1000.0)
            svc = metric_series(econ, [["order", "backlog", "service", "bneur"]], scale=1000.0)
            backlog = wind.merge(svc, on="year", how="outer", suffixes=("_wind", "_svc"))
            if not backlog.empty:
                backlog["value"] = backlog[["value_wind", "value_svc"]].fillna(0.0).sum(axis=1)
                backlog = backlog[["year", "value"]]
                backlog["oem"] = oem
                backlog["metric_name"] = "Order backlog value (mEUR, combined)"
                rows.append(backlog)
        elif oem == "Nordex":
            total = metric_series(econ, [["order", "backlog", "total", "meur"]], scale=1.0)
            if not total.empty:
                total["oem"] = oem
                total["metric_name"] = "Order backlog value (mEUR, combined)"
                rows.append(total)
            else:
                projects = metric_series(econ, [["order", "backlog", "projects", "meur"]], scale=1.0)
                service = metric_series(econ, [["order", "backlog", "service", "meur"]], scale=1.0)
                backlog = projects.merge(service, on="year", how="outer", suffixes=("_proj", "_svc"))
                if not backlog.empty:
                    backlog["value"] = backlog[["value_proj", "value_svc"]].fillna(0.0).sum(axis=1)
                    backlog = backlog[["year", "value"]]
                    backlog["oem"] = oem
                    backlog["metric_name"] = "Order backlog value (mEUR, combined)"
                    rows.append(backlog)
        elif oem == "Siemens Gamesa":
            # SGRE backlog metrics are treated as bEUR in source sheet and normalized to mEUR here.
            onshore = metric_series(econ, [["order", "backlog", "onshore"]], scale=1000.0)
            offshore = metric_series(econ, [["order", "backlog", "offshore"]], scale=1000.0)
            service = metric_series(econ, [["order", "backlog", "service"]], scale=1000.0)
            backlog = onshore.merge(offshore, on="year", how="outer", suffixes=("_on", "_off"))
            if not backlog.empty:
                backlog = backlog.merge(service, on="year", how="outer")
                backlog["value"] = backlog[["value_on", "value_off", "value"]].fillna(0.0).sum(axis=1)
                backlog = backlog[["year", "value"]]
                backlog["oem"] = oem
                backlog["metric_name"] = "Order backlog value (mEUR, combined)"
                rows.append(backlog)

    if not rows:
        return pd.DataFrame(columns=["year", "value", "oem", "metric_name"])

    out = pd.concat(rows, ignore_index=True)
    out = out.dropna(subset=["year", "value"])
    out["year"] = pd.to_numeric(out["year"], errors="coerce").astype(int)
    return out


def build_yearly_order_stats(orders: pd.DataFrame) -> pd.DataFrame:
    if orders.empty:
        return pd.DataFrame(
            columns=[
                "oem",
                "order_year",
                "ordered_mw",
                "orders",
                "avg_order_mw",
                "min_order_mw",
                "max_order_mw",
                "avg_service_years",
                "min_service_years",
                "max_service_years",
            ]
        )

    out = (
        orders.groupby(["oem", "order_year"], as_index=False)
        .agg(
            ordered_mw=("size_mw", "sum"),
            orders=("order_id", "nunique"),
            avg_order_mw=("size_mw", "mean"),
            min_order_mw=("size_mw", "min"),
            max_order_mw=("size_mw", "max"),
            avg_service_years=("service_time_years", "mean"),
            min_service_years=("service_time_years", "min"),
            max_service_years=("service_time_years", "max"),
        )
        .sort_values(["oem", "order_year"])
    )
    return out


def build_platform_size_stats(platforms: pd.DataFrame) -> pd.DataFrame:
    if platforms.empty:
        return pd.DataFrame(
            columns=[
                "oem",
                "order_year",
                "rotor_avg_m",
                "rotor_min_m",
                "rotor_max_m",
                "mw_avg",
                "mw_min",
                "mw_max",
            ]
        )

    rows: list[dict[str, Any]] = []
    for (oem, year), grp in platforms.groupby(["oem", "order_year"]):
        rotor_valid = grp[["rotor_m", "slot_mw"]].dropna(subset=["rotor_m"])
        rating_valid = grp[["mw_rating", "slot_mw"]].dropna(subset=["mw_rating"])

        rotor_avg = np.nan
        rotor_min = np.nan
        rotor_max = np.nan
        if not rotor_valid.empty:
            w = rotor_valid["slot_mw"].where(rotor_valid["slot_mw"] > 0, 1.0).fillna(1.0)
            rotor_avg = float(np.average(rotor_valid["rotor_m"], weights=w))
            rotor_min = float(rotor_valid["rotor_m"].min())
            rotor_max = float(rotor_valid["rotor_m"].max())

        mw_avg = np.nan
        mw_min = np.nan
        mw_max = np.nan
        if not rating_valid.empty:
            w = rating_valid["slot_mw"].where(rating_valid["slot_mw"] > 0, 1.0).fillna(1.0)
            mw_avg = float(np.average(rating_valid["mw_rating"], weights=w))
            mw_min = float(rating_valid["mw_rating"].min())
            mw_max = float(rating_valid["mw_rating"].max())

        rows.append(
            {
                "oem": oem,
                "order_year": int(year),
                "rotor_avg_m": rotor_avg,
                "rotor_min_m": rotor_min,
                "rotor_max_m": rotor_max,
                "mw_avg": mw_avg,
                "mw_min": mw_min,
                "mw_max": mw_max,
            }
        )

    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values(["oem", "order_year"])


def latest_data_caption(economy: pd.DataFrame, orders: pd.DataFrame, platforms: pd.DataFrame, catalog_generated: str | None) -> str:
    econ_year = pd.to_numeric(economy.get("year"), errors="coerce").dropna().max() if not economy.empty else np.nan
    order_year = pd.to_numeric(orders.get("order_year"), errors="coerce").dropna().max() if not orders.empty else np.nan
    platform_year = pd.to_numeric(platforms.get("order_year"), errors="coerce").dropna().max() if not platforms.empty else np.nan
    order_date = pd.to_datetime(orders.get("order_date"), errors="coerce").max() if not orders.empty else pd.NaT

    econ_txt = str(int(econ_year)) if pd.notna(econ_year) else "-"
    order_txt = str(int(order_year)) if pd.notna(order_year) else "-"
    platform_txt = str(int(platform_year)) if pd.notna(platform_year) else "-"
    order_date_txt = order_date.strftime("%Y-%m-%d") if pd.notna(order_date) else "-"
    catalog_txt = catalog_generated or "-"

    return (
        f"Latest handled data -> Economy year: {econ_txt}; "
        f"Order year: {order_txt}; Platform year: {platform_txt}; "
        f"Latest order date: {order_date_txt}; Turbine catalog snapshot (UTC): {catalog_txt}."
    )


def plot_line(data: pd.DataFrame, x: str, y: str, color: str, title: str, y_title: str, line_dash: str | None = None) -> None:
    if data.empty:
        st.info(f"No data available for: {title}")
        return

    fig = px.line(
        data,
        x=x,
        y=y,
        color=color,
        line_dash=line_dash,
        markers=True,
        template=plotly_template(),
        color_discrete_map=OEM_COLORS,
        title=title,
        height=420,
    )
    fig.update_layout(margin=dict(l=8, r=8, t=56, b=8), yaxis_title=y_title, legend_title_text="")
    st.plotly_chart(fig, width="stretch")


def render_overall_tab(economy: pd.DataFrame, orders: pd.DataFrame) -> None:
    st.subheader("Overall Economics and OEM Comparison")

    if orders.empty:
        st.warning("No order rows left after filters.")
        return

    summary = (
        orders.groupby("oem", as_index=False)
        .agg(
            ordered_mw=("size_mw", "sum"),
            orders=("order_id", "nunique"),
            avg_order_mw=("size_mw", "mean"),
            avg_service_years=("service_time_years", "mean"),
            countries=("country", "nunique"),
        )
        .sort_values("ordered_mw", ascending=False)
    )

    for _, row in summary.iterrows():
        oem = str(row["oem"])
        cols = st.columns(5)
        cols[0].metric(f"{oem} Ordered MW", f"{row['ordered_mw']:,.0f}")
        cols[1].metric(f"{oem} Orders", f"{int(row['orders'])}")
        cols[2].metric(f"{oem} Avg Order MW", f"{row['avg_order_mw']:,.1f}")
        avg_service = row["avg_service_years"]
        cols[3].metric(f"{oem} Avg Service Years", "-" if pd.isna(avg_service) else f"{avg_service:,.1f}")
        cols[4].metric(f"{oem} Countries", f"{int(row['countries'])}")

    econ_comp = build_economy_comparison(economy)

    c1, c2 = st.columns(2)
    with c1:
        plot_line(
            econ_comp[econ_comp["metric_name"] == "Revenue (mEUR, as reported)"],
            "year",
            "value",
            "oem",
            "Revenue Comparison",
            "mEUR",
        )
    with c2:
        plot_line(
            econ_comp[econ_comp["metric_name"] == "Order intake value (mEUR, normalized)"],
            "year",
            "value",
            "oem",
            "Order Intake Value Comparison",
            "mEUR",
        )

    backlog = econ_comp[econ_comp["metric_name"] == "Order backlog value (mEUR, combined)"]
    if not backlog.empty:
        plot_line(backlog, "year", "value", "oem", "Order Backlog Value Comparison", "mEUR")

    yearly = build_yearly_order_stats(orders)
    d1, d2 = st.columns(2)
    with d1:
        plot_line(yearly, "order_year", "ordered_mw", "oem", "Ordered MW by Year", "MW")
    with d2:
        plot_line(yearly, "order_year", "avg_order_mw", "oem", "Average Order Size by Year", "MW / order")


def render_sizes_tab(orders: pd.DataFrame, platforms: pd.DataFrame) -> None:
    st.subheader("Rotor/MW Sizes, Order Sizes, and Service Length")

    yearly = build_yearly_order_stats(orders)
    platform_yearly = build_platform_size_stats(platforms)

    stat_options = ["Average", "Min", "Max"]
    stat_view = st.radio(
        "Show statistics",
        options=["All", "Average", "Min", "Max"],
        index=0,
        horizontal=True,
        help="Filter all size/service charts by statistic type.",
    )
    selected_stats = stat_options if stat_view == "All" else [stat_view]

    if platform_yearly.empty:
        st.info("No platform size data available for current filters.")
    else:
        rotor_long = platform_yearly.melt(
            id_vars=["oem", "order_year"],
            value_vars=["rotor_min_m", "rotor_avg_m", "rotor_max_m"],
            var_name="stat",
            value_name="rotor_m",
        )
        rotor_long["stat"] = rotor_long["stat"].map(
            {
                "rotor_min_m": "Min",
                "rotor_avg_m": "Average",
                "rotor_max_m": "Max",
            }
        )
        rotor_long = rotor_long.dropna(subset=["rotor_m"])
        rotor_long = rotor_long[rotor_long["stat"].isin(selected_stats)]
        plot_line(
            rotor_long,
            "order_year",
            "rotor_m",
            "oem",
            "Rotor Diameter Over Time (Min/Avg/Max)",
            "Rotor diameter (m)",
            line_dash="stat",
        )

        mw_long = platform_yearly.melt(
            id_vars=["oem", "order_year"],
            value_vars=["mw_min", "mw_avg", "mw_max"],
            var_name="stat",
            value_name="mw_rating",
        )
        mw_long["stat"] = mw_long["stat"].map(
            {
                "mw_min": "Min",
                "mw_avg": "Average",
                "mw_max": "Max",
            }
        )
        mw_long = mw_long.dropna(subset=["mw_rating"])
        mw_long = mw_long[mw_long["stat"].isin(selected_stats)]
        plot_line(
            mw_long,
            "order_year",
            "mw_rating",
            "oem",
            "Turbine MW Rating Over Time (Min/Avg/Max)",
            "MW rating",
            line_dash="stat",
        )

    if yearly.empty:
        st.info("No order size data available for current filters.")
        return

    order_size_long = yearly.melt(
        id_vars=["oem", "order_year"],
        value_vars=["min_order_mw", "avg_order_mw", "max_order_mw"],
        var_name="stat",
        value_name="order_size",
    )
    order_size_long["stat"] = order_size_long["stat"].map(
        {
            "min_order_mw": "Min",
            "avg_order_mw": "Average",
            "max_order_mw": "Max",
        }
    )
    order_size_long = order_size_long.dropna(subset=["order_size"])
    order_size_long = order_size_long[order_size_long["stat"].isin(selected_stats)]
    order_cap = 2000.0
    order_plot = order_size_long.copy()
    order_plot["order_size_plot"] = order_plot["order_size"].clip(upper=order_cap)
    fig_order = px.line(
        order_plot,
        x="order_year",
        y="order_size_plot",
        color="oem",
        line_dash="stat",
        markers=True,
        template=plotly_template(),
        color_discrete_map=OEM_COLORS,
        title="Order Size Over Time (Min/Avg/Max, capped at 2000 MW)",
        height=420,
    )
    over_cap = order_size_long[
        (order_size_long["oem"] == "Siemens Gamesa")
        & (pd.to_numeric(order_size_long["order_size"], errors="coerce") > order_cap)
    ].copy()
    if not over_cap.empty:
        over_cap["label"] = over_cap["stat"].astype(str) + ": ↑ " + over_cap["order_size"].map(lambda v: f"{float(v):,.0f}")
        fig_order.add_trace(
            go.Scatter(
                x=over_cap["order_year"],
                y=[order_cap] * len(over_cap),
                mode="markers+text",
                text=over_cap["label"],
                textposition="top center",
                marker=dict(
                    size=13,
                    symbol="triangle-up",
                    color=OEM_COLORS.get("Siemens Gamesa", "#3A5A40"),
                    line=dict(width=1, color="#ffffff"),
                ),
                name="Siemens > 2000 MW (actual)",
                showlegend=True,
            )
        )
    fig_order.update_layout(
        margin=dict(l=8, r=8, t=56, b=8),
        yaxis_title="MW / order",
        yaxis_range=[0, order_cap],
        legend_title_text="",
    )
    st.plotly_chart(fig_order, width="stretch")

    service_long = yearly.melt(
        id_vars=["oem", "order_year"],
        value_vars=["min_service_years", "avg_service_years", "max_service_years"],
        var_name="stat",
        value_name="service_years",
    )
    service_long["stat"] = service_long["stat"].map(
        {
            "min_service_years": "Min",
            "avg_service_years": "Average",
            "max_service_years": "Max",
        }
    )
    service_long = service_long.dropna(subset=["service_years"])
    service_long = service_long[service_long["stat"].isin(selected_stats)]
    if service_long.empty:
        st.info("No service length data available for current filters.")
    else:
        plot_line(
            service_long,
            "order_year",
            "service_years",
            "oem",
            "Service Contract Length Over Time (Min/Avg/Max)",
            "Years",
            line_dash="stat",
        )


def render_geo_tab(orders: pd.DataFrame) -> None:
    st.subheader("Country / Region / Continent Spread")

    if orders.empty:
        st.info("No order rows available for geography views.")
        return

    geo = orders.copy()
    for col in ["continent", "region", "country"]:
        geo[col] = geo[col].fillna("Unknown").astype(str)

    continent = (
        geo.groupby(["continent", "oem"], as_index=False)["size_mw"]
        .sum()
        .sort_values("size_mw", ascending=False)
    )
    fig_cont = px.bar(
        continent,
        x="continent",
        y="size_mw",
        color="oem",
        barmode="group",
        template=plotly_template(),
        color_discrete_map=OEM_COLORS,
        title="MW by Continent and OEM",
        height=430,
    )
    fig_cont.update_layout(margin=dict(l=8, r=8, t=56, b=8), yaxis_title="Ordered MW", legend_title_text="")
    st.plotly_chart(fig_cont, width="stretch")

    year_continent = (
        geo.groupby(["oem", "order_year", "continent"], as_index=False)["size_mw"]
        .sum()
        .sort_values(["oem", "order_year"])
    )
    fig_area = px.area(
        year_continent,
        x="order_year",
        y="size_mw",
        color="continent",
        facet_col="oem",
        facet_col_wrap=2,
        template=plotly_template(),
        title="Continent Mix Over Time by OEM",
        height=520,
    )
    fig_area.for_each_annotation(
        lambda ann: ann.update(
            text=ann.text.replace("oem=", ""),
            font=dict(size=16, color=ann.font.color if ann.font and ann.font.color else None),
            y=(ann.y - 0.025) if ann.y is not None else ann.y,
        )
    )
    fig_area.update_layout(margin=dict(l=8, r=8, t=56, b=8), yaxis_title="Ordered MW", legend_title_text="")
    st.plotly_chart(fig_area, width="stretch")

    top_countries = (
        geo.groupby("country", as_index=False)["size_mw"]
        .sum()
        .sort_values("size_mw", ascending=False)
        .head(15)["country"]
        .tolist()
    )

    country_comp = (
        geo[geo["country"].isin(top_countries)]
        .groupby(["country", "oem"], as_index=False)["size_mw"]
        .sum()
        .sort_values("size_mw", ascending=False)
    )
    fig_country = px.bar(
        country_comp,
        x="size_mw",
        y="country",
        color="oem",
        orientation="h",
        barmode="group",
        template=plotly_template(),
        color_discrete_map=OEM_COLORS,
        title="Top Countries by Ordered MW (OEM Split)",
        height=560,
    )
    fig_country.update_layout(margin=dict(l=8, r=8, t=56, b=8), xaxis_title="Ordered MW", legend_title_text="")
    st.plotly_chart(fig_country, width="stretch")

    tree = (
        geo.groupby(["oem", "continent", "region", "country"], as_index=False)["size_mw"]
        .sum()
        .sort_values("size_mw", ascending=False)
    )
    fig_tree = px.sunburst(
        tree,
        path=["oem", "continent", "region", "country"],
        values="size_mw",
        color="oem",
        color_discrete_map=OEM_COLORS,
        template=plotly_template(),
        title="OEM -> Continent -> Region -> Country (Ordered MW)",
        height=680,
    )
    fig_tree.update_layout(margin=dict(l=8, r=8, t=56, b=8))
    st.plotly_chart(fig_tree, width="stretch")


def render_turbine_portfolio_tab(catalog: pd.DataFrame, catalog_generated: str | None, failed_sources: list[str], selected_oems: list[str]) -> None:
    st.subheader("Current Turbine Portfolio and Key Specs")

    if catalog.empty:
        st.warning(
            "No turbine catalog data found. Run `python build_turbine_catalog.py` to fetch current OEM pages and generate `data/oem_turbine_catalog.json`."
        )
        return

    cat = catalog.copy()
    cat = cat[cat["oem"].isin(selected_oems)]

    seg_expanded = cat.assign(segment_item=cat["segment"].astype(str).str.split(", ")).explode("segment_item")
    segment_options = sorted(seg_expanded["segment_item"].dropna().unique().tolist())
    selected_segments = st.multiselect("Segments", options=segment_options, default=segment_options)
    if selected_segments:
        seg_expanded = seg_expanded[seg_expanded["segment_item"].isin(selected_segments)]

    filtered = seg_expanded.drop_duplicates(subset=["oem", "model"]).copy()
    rotor_floor_m = 100.0
    filtered = filtered[(filtered["rotor_diameter_m"].isna()) | (filtered["rotor_diameter_m"] >= rotor_floor_m)].copy()

    st.markdown(
        f"<div class='small-note'>Catalog snapshot (UTC): {catalog_generated or '-'} | Models shown: {len(filtered):,}</div>",
        unsafe_allow_html=True,
    )
    st.caption(f"Rotor diameter filter applied: >= {rotor_floor_m:.0f} m.")
    if failed_sources:
        st.warning("Could not refresh some sources: " + "; ".join(failed_sources))

    oem_counts = filtered.groupby("oem", as_index=False).agg(models=("model", "nunique"))
    stat_cols = st.columns(max(1, len(oem_counts)))
    for col, row in zip(stat_cols, oem_counts.itertuples(index=False), strict=False):
        col.metric(f"{row.oem} models", f"{int(row.models)}")

    scatter_data = filtered.dropna(subset=["rotor_diameter_m", "rated_power_mw"]).copy()
    if scatter_data.empty:
        st.info("No rows with both rotor diameter and rated power in selected turbine portfolio.")
    else:
        segment_symbol_map = {
            "Onshore": "circle",
            "Offshore": "circle",
        }
        ctrl1, ctrl2, ctrl3 = st.columns([1.3, 1.2, 1.0])
        scatter_view = ctrl1.radio(
            "Scatter view",
            options=["Combined", "Facet by OEM"],
            index=0,
            horizontal=True,
            key="turbine_scatter_view",
        )
        label_mode = ctrl2.selectbox(
            "Labels",
            options=["Hover only (clean)", "Outliers only", "All models"],
            index=0,
            key="turbine_scatter_labels",
        )
        marker_size = ctrl3.slider("Marker size", min_value=7, max_value=16, value=10, key="turbine_scatter_marker_size")

        scatter_plot = scatter_data.copy()
        if label_mode == "All models":
            scatter_plot["label"] = scatter_plot["model"].astype(str)
        elif label_mode == "Outliers only":
            x_thr = float(scatter_plot["rotor_diameter_m"].quantile(0.90))
            y_thr = float(scatter_plot["rated_power_mw"].quantile(0.90))
            mask = (scatter_plot["rotor_diameter_m"] >= x_thr) | (scatter_plot["rated_power_mw"] >= y_thr)
            scatter_plot["label"] = np.where(mask, scatter_plot["model"].astype(str), "")
        else:
            scatter_plot["label"] = ""

        base_kwargs = {
            "x": "rotor_diameter_m",
            "y": "rated_power_mw",
            "hover_data": ["model", "platform", "segment_item", "oem"],
            "template": plotly_template(),
            "title": "Rotor Diameter vs Rated Power (Current Portfolio)",
        }
        if label_mode != "Hover only (clean)":
            base_kwargs["text"] = "label"

        if scatter_view == "Facet by OEM":
            fig_scatter = px.scatter(
                scatter_plot,
                color="oem",
                color_discrete_map=OEM_COLORS,
                symbol="segment_item",
                symbol_map=segment_symbol_map,
                facet_col="oem",
                facet_col_wrap=2,
                height=620,
                **base_kwargs,
            )
            fig_scatter.for_each_annotation(lambda ann: ann.update(text=ann.text.replace("oem=", "")))
            fig_scatter.update_xaxes(matches="x")
            fig_scatter.update_yaxes(matches="y")
        else:
            fig_scatter = px.scatter(
                scatter_plot,
                color="oem",
                color_discrete_map=OEM_COLORS,
                symbol="segment_item",
                symbol_map=segment_symbol_map,
                height=580,
                **base_kwargs,
            )

        fig_scatter.update_traces(marker=dict(size=marker_size, opacity=0.86, line=dict(width=0.8, color="rgba(15,23,42,0.30)")))
        seen_oems: set[str] = set()
        for trace in fig_scatter.data:
            raw_name = str(getattr(trace, "name", ""))
            parts = [p.strip() for p in raw_name.split(",") if p.strip()]
            oem_name = ""
            segment_name = ""
            for part in parts:
                low = part.lower()
                if low.startswith("oem="):
                    oem_name = part.split("=", 1)[1].strip()
                elif low.startswith("segment_item=") or low.startswith("segment="):
                    segment_name = part.split("=", 1)[1].strip()
                elif not oem_name:
                    oem_name = part
                elif not segment_name:
                    segment_name = part
            if not segment_name:
                lname = raw_name.lower()
                if "offshore" in lname:
                    segment_name = "Offshore"
                elif "onshore" in lname:
                    segment_name = "Onshore"

            is_offshore = segment_name.lower() == "offshore"
            trace.marker.line.color = "#1D4ED8" if is_offshore else "rgba(15,23,42,0.30)"
            trace.marker.line.width = 2.8 if is_offshore else 0.8

            legend_oem = oem_name or raw_name
            if legend_oem in seen_oems:
                trace.showlegend = False
            else:
                trace.showlegend = True
                trace.name = legend_oem
                seen_oems.add(legend_oem)

        if label_mode != "Hover only (clean)":
            fig_scatter.update_traces(textposition="top center", textfont=dict(size=10))

        x_min = float(scatter_plot["rotor_diameter_m"].min())
        x_max = float(scatter_plot["rotor_diameter_m"].max())
        y_min = float(scatter_plot["rated_power_mw"].min())
        y_max = float(scatter_plot["rated_power_mw"].max())
        x_pad = max(2.0, (x_max - x_min) * 0.05)
        y_pad = max(0.2, (y_max - y_min) * 0.07)

        fig_scatter.update_layout(
            margin=dict(l=8, r=8, t=56, b=8),
            xaxis_title="Rotor diameter (m)",
            yaxis_title="Rated power (MW)",
            legend_title_text="",
        )
        fig_scatter.update_xaxes(range=[x_min - x_pad, x_max + x_pad], showgrid=True, zeroline=False)
        fig_scatter.update_yaxes(range=[max(0.0, y_min - y_pad), y_max + y_pad], showgrid=True, zeroline=False)
        st.caption("Default view is optimized for readability. Offshore models are shown with thick blue outlines.")
        st.plotly_chart(fig_scatter, width="stretch")

    c1, c2 = st.columns(2)
    with c1:
        rotor_hist = filtered.dropna(subset=["rotor_diameter_m"])
        if not rotor_hist.empty:
            fig_rotor = px.histogram(
                rotor_hist,
                x="rotor_diameter_m",
                color="oem",
                nbins=16,
                barmode="overlay",
                opacity=0.75,
                template=plotly_template(),
                color_discrete_map=OEM_COLORS,
                title="Rotor Diameter Distribution",
                height=420,
            )
            fig_rotor.update_layout(margin=dict(l=8, r=8, t=56, b=8), legend_title_text="")
            st.plotly_chart(fig_rotor, width="stretch")

    with c2:
        power_hist = filtered.dropna(subset=["rated_power_mw"])
        if not power_hist.empty:
            fig_power = px.histogram(
                power_hist,
                x="rated_power_mw",
                color="oem",
                nbins=16,
                barmode="overlay",
                opacity=0.75,
                template=plotly_template(),
                color_discrete_map=OEM_COLORS,
                title="Rated Power Distribution",
                height=420,
            )
            fig_power.update_layout(margin=dict(l=8, r=8, t=56, b=8), legend_title_text="")
            st.plotly_chart(fig_power, width="stretch")

    table = filtered[["oem", "segment_item", "platform", "model", "rotor_diameter_m", "rated_power_mw", "power_class", "source_urls"]].copy()
    table = table.rename(columns={"segment_item": "segment"})
    table["source_urls"] = table["source_urls"].apply(lambda urls: "\n".join(urls) if isinstance(urls, list) else "")
    table = table.sort_values(["oem", "segment", "rotor_diameter_m", "rated_power_mw", "model"])
    st.dataframe(table, width="stretch", hide_index=True)

    source_set: set[str] = set()
    for urls in filtered["source_urls"].tolist():
        if isinstance(urls, list):
            source_set.update(urls)

    st.markdown("**Source pages used for current turbine portfolio extraction**")
    for url in sorted(source_set):
        st.markdown(f"- [{url}]({url})")


def render_information_page() -> None:
    st.subheader("Information")
    st.markdown("**Data source**")
    st.write("This dashboard is build on public available data.")

    st.markdown("**How to use and navigate**")
    st.write(
        "Use the sidebar filters to narrow years, OEMs, and minimum order size."
    )
    st.write(
        "Navigate tabs from high-level trends (Overall Economics) to deep dives (Sizes/Service, Geography, and Existing Turbine Portfolio)."
    )

    st.markdown("**Disclaimer**")
    st.write(
        "This dashboard is provided for informational purposes only. Data is compiled from public sources and may contain gaps, delays, or inaccuracies."
    )
    st.write(
        "Always verify critical figures with official company reporting before using the information for financial, legal, strategic, or investment decisions."
    )
    st.write(
        'The data and dashboard are provided "as is" without warranties of any kind. I make no guarantees of accuracy, completeness, or fitness for a particular purpose.'
    )
    st.write(
        "Use at your own risk. I am not responsible or liable for any losses or damages arising from use of the data or dashboard."
    )

    st.markdown("**Sources and attribution**")
    st.write(
        "All figures are compiled manually from public investor communications (press releases/announcements), annual reports, and official product pages for Vestas, Nordex, Siemens Gamesa, and Suzlon."
    )
    st.write("Each datapoint should be verified against the original source documents.")

    st.markdown("**No affiliation / no endorsement**")
    st.write(
        "This is an unofficial, independent dashboard and is not affiliated with, endorsed by, or sponsored by Vestas, Nordex, Siemens Gamesa, or Suzlon."
    )

    st.markdown("**IP and rights**")
    st.write(
        "The dataset in this repository is my own compilation (selection/structure) based on publicly available sources."
    )
    st.write("Underlying source documents remain the property of their respective owners.")

    st.markdown("**About me**")
    st.write(
        "Thomas Buhl is a wind-energy engineering leader with 20+ years across research and industry, including professor/department-head and director/VP roles."
    )
    st.write(
        "He combines deep technical expertise in wind turbine design and optimization with international people leadership and strategy execution."
    )


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="W", layout="wide")
    if "dark_mode" not in st.session_state:
        st.session_state["dark_mode"] = False
    st.sidebar.toggle("Dark mode", key="dark_mode")
    dark_mode = bool(st.session_state.get("dark_mode", False))
    apply_page_style(dark_mode)

    cache_paths = resolve_oem_cache_files()
    signature = "|".join(file_signature(path) for path in cache_paths.values())
    cache_paths_txt = {oem: str(path) for oem, path in cache_paths.items()}
    economy_all, orders_all, platforms_all, issues = load_all_oem_data(signature, cache_paths_txt)
    cache_freshness = load_cache_freshness(signature, cache_paths_txt)

    catalog_signature = file_signature(TURBINE_CATALOG_FILE)
    turbine_catalog, catalog_generated, failed_sources = load_turbine_catalog(catalog_signature)

    st.title(APP_TITLE)
    st.caption("Combined benchmark from Vestas, Nordex, Siemens Gamesa, and Suzlon parsed dashboard datasets.")
    render_data_freshness_badges(cache_freshness)

    if issues:
        for issue in issues:
            st.warning(issue)

    if orders_all.empty:
        st.error("No parsed order data available. Ensure OEM cache files exist and contain parsable rows.")
        return

    oem_options = sorted(orders_all["oem"].dropna().unique().tolist())
    year_series = pd.to_numeric(orders_all["order_year"], errors="coerce").dropna()
    y_min = int(year_series.min())
    y_max = int(year_series.max())

    st.sidebar.header("Global Filters")
    selected_oems = st.sidebar.multiselect("OEMs", options=oem_options, default=oem_options)
    year_range = st.sidebar.slider("Order year range", min_value=y_min, max_value=y_max, value=(y_min, y_max))

    size_series = pd.to_numeric(orders_all["size_mw"], errors="coerce")
    min_size = float(size_series.min()) if size_series.notna().any() else 0.0
    max_size = float(size_series.max()) if size_series.notna().any() else 1.0
    mw_floor = st.sidebar.slider("Minimum order MW", min_value=min_size, max_value=max_size, value=min_size)

    st.sidebar.divider()
    st.sidebar.markdown("**OEM Deep Dive**")
    st.sidebar.link_button("Vestas all details", "https://vestas.streamlit.app", use_container_width=True)
    st.sidebar.link_button("Nordex all details", "https://nordex.streamlit.app", use_container_width=True)
    st.sidebar.link_button("SGRE all details", "https://siemens-gamesa.streamlit.app", use_container_width=True)
    st.sidebar.link_button("Suzlon all details", "https://suzlon.streamlit.app", use_container_width=True)

    orders_f = orders_all[
        (orders_all["oem"].isin(selected_oems))
        & (orders_all["order_year"].between(year_range[0], year_range[1]))
        & (orders_all["size_mw"].fillna(0.0) >= mw_floor)
    ].copy()

    economy_f = economy_all[
        (economy_all["oem"].isin(selected_oems))
        & (economy_all["year"].between(year_range[0], year_range[1]))
    ].copy()

    platforms_f = platforms_all[
        (platforms_all["oem"].isin(selected_oems))
        & (platforms_all["order_year"].between(year_range[0], year_range[1]))
    ].copy()

    if not orders_f.empty:
        valid_ids = set(orders_f["order_id"].dropna().tolist())
        platforms_f = platforms_f[platforms_f["order_id"].isin(valid_ids)]

    st.caption(latest_data_caption(economy_all, orders_all, platforms_all, catalog_generated))

    if orders_f.empty:
        st.warning("No rows left after filters. Adjust year/OEM/MW filters.")
        return

    tabs = st.tabs(
        [
            "Overall Economics",
            "Sizes and Service",
            "Country/Region/Continent",
            "Existing Turbine Portfolio",
            "Information",
        ]
    )

    with tabs[0]:
        render_overall_tab(economy_f, orders_f)

    with tabs[1]:
        render_sizes_tab(orders_f, platforms_f)

    with tabs[2]:
        render_geo_tab(orders_f)

    with tabs[3]:
        render_turbine_portfolio_tab(turbine_catalog, catalog_generated, failed_sources, selected_oems)

    with tabs[4]:
        render_information_page()


if __name__ == "__main__":
    main()
