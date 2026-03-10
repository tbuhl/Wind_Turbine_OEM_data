from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

DATA_DIR = Path(__file__).resolve().parent / "data"
OUT_FILE = DATA_DIR / "oem_turbine_catalog.json"

SOURCES = [
    {
        "oem": "Vestas",
        "segment": "Onshore",
        "platform": "Onshore Portfolio",
        "url": "https://www.vestas.com/en/energy-solutions/onshore-wind-turbines",
    },
    {
        "oem": "Vestas",
        "segment": "Onshore",
        "platform": "Enventus Platform",
        "url": "https://www.vestas.com/en/energy-solutions/onshore-wind-turbines/enventus-platform",
    },
    {
        "oem": "Vestas",
        "segment": "Onshore",
        "platform": "4 MW Platform",
        "url": "https://www.vestas.com/en/energy-solutions/onshore-wind-turbines/4-mw-platform",
    },
    {
        "oem": "Vestas",
        "segment": "Onshore",
        "platform": "2 MW Platform",
        "url": "https://www.vestas.com/en/energy-solutions/onshore-wind-turbines/2-mw-platform",
    },
    {
        "oem": "Vestas",
        "segment": "Offshore",
        "platform": "Offshore Portfolio",
        "url": "https://www.vestas.com/en/energy-solutions/offshore-wind-turbines",
    },
    {
        "oem": "Vestas",
        "segment": "Offshore",
        "platform": "V236-15MW",
        "url": "https://www.vestas.com/en/energy-solutions/offshore-wind-turbines/V236-15MW",
    },
    {
        "oem": "Nordex",
        "segment": "Onshore",
        "platform": "Product Portfolio",
        "url": "https://www.nordex-online.com/en/product/product-main-page/",
    },
    {
        "oem": "Siemens Gamesa",
        "segment": "Onshore",
        "platform": "Onshore Portfolio",
        "url": "https://www.siemensgamesa.com/global/en/home/products-and-services/onshore.html",
    },
    {
        "oem": "Siemens Gamesa",
        "segment": "Offshore",
        "platform": "Offshore Portfolio",
        "url": "https://www.siemensgamesa.com/global/en/home/products-and-services/offshore.html",
    },
    {
        "oem": "Suzlon",
        "segment": "Onshore",
        "platform": "S-Series Platform",
        "url": "https://www.suzlon.com/in-en/energy-solutions/s111-wind-turbine-generator",
    },
    {
        "oem": "Suzlon",
        "segment": "Onshore",
        "platform": "S-Series Platform",
        "url": "https://www.suzlon.com/in-en/energy-solutions/s120-wind-turbine-generator",
    },
    {
        "oem": "Suzlon",
        "segment": "Onshore",
        "platform": "S-Series Platform",
        "url": "https://www.suzlon.com/in-en/energy-solutions/s128-wind-turbine-generator",
    },
    {
        "oem": "Suzlon",
        "segment": "Onshore",
        "platform": "S-Series Platform",
        "url": "https://www.suzlon.com/in-en/energy-solutions/s133-wind-turbine-generator",
    },
    {
        "oem": "Suzlon",
        "segment": "Onshore",
        "platform": "S-Series Platform",
        "url": "https://www.suzlon.com/in-en/energy-solutions/s144-wind-turbine-generator",
    },
    {
        "oem": "GE",
        "segment": "Onshore",
        "platform": "3 MW Platform",
        "url": "https://www.gevernova.com/wind-power/wind-turbines/onshore-wind-turbines-3mw",
    },
    {
        "oem": "GE",
        "segment": "Onshore",
        "platform": "4 MW Platform",
        "url": "https://www.gevernova.com/wind-power/wind-turbines/onshore-wind-turbines-4mw",
    },
    {
        "oem": "GE",
        "segment": "Onshore",
        "platform": "6 MW Platform",
        "url": "https://www.gevernova.com/wind-power/wind-turbines/onshore-wind-turbines-6mw",
    },
    {
        "oem": "GE",
        "segment": "Offshore",
        "platform": "Haliade-X Portfolio",
        "url": "https://www.gevernova.com/wind-power/wind-turbines/offshore-wind-turbines",
    },
    {
        "oem": "GE",
        "segment": "Offshore",
        "platform": "Haliade-X",
        "url": "https://www.gevernova.com/news/press-releases/ge-haliade-x-14-7mw-220-turbine-obtains-full-dnv-type-certificate",
    },
]

VESTAS_RE = re.compile(r"\bV\d{2,3}[\-/]\d{1,2}(?:\.\d+)?(?:MW)?\b", re.IGNORECASE)
NORDEX_RE = re.compile(r"\b(?:N|AW|S)\d{2,3}(?:/[0-9NXx\.]+)?\b")
SGRE_RE = re.compile(r"\bSG\s?\d{1,2}(?:\.\d+)?-\d{2,3}(?:\s?DD)?\b", re.IGNORECASE)
SUZLON_URL_MODEL_RE = re.compile(r"/s(\d{2,3})-wind-turbine-generator", re.IGNORECASE)
GE_ONSHORE_RE = re.compile(r"\b(\d{1,2}(?:\.\d+)?)\s*MW[-\s]*(\d{2,3})m\b", re.IGNORECASE)
GE_HALIADE_RE = re.compile(r"\bHaliade[-\s]?X[^0-9]{0,30}(\d{1,2}(?:\.\d+)?)\s*MW[-\s]*(\d{2,3})(?:m)?\b", re.IGNORECASE)
GE_MW_220_RE = re.compile(r"\b(\d{1,2}(?:\.\d+)?)\s*MW[-\s]*(22\d)(?:m)?\b", re.IGNORECASE)

SUZLON_POWER_RANGE_BY_ROTOR = {
    111: (2.0, 2.2),
    120: (2.0, 2.2),
    128: (2.5, 2.8),
    133: (2.5, 3.1),
    144: (2.8, 3.2),
}

SUZLON_FALLBACK_BY_ROTOR = {
    111: [2.1],
    120: [2.1],
    128: [2.6, 2.7],
    133: [2.6, 3.0],
    144: [3.0, 3.15],
}


def fetch_html(url: str) -> str:
    resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    return resp.text


def parse_vestas_model(raw: str) -> tuple[str, float | None, float | None, str | None]:
    text = raw.upper().replace("MW", "").replace("/", "-")
    text = re.sub(r"[^A-Z0-9\-.]", "", text)
    m = re.fullmatch(r"V(\d{2,3})-(\d{1,2}(?:\.\d+)?)", text)
    if not m:
        return text, None, None, None
    rotor = float(m.group(1))
    power_label = m.group(2)
    if "." not in power_label:
        power_label = f"{power_label}.0"
    power = float(m.group(2))
    return f"V{int(rotor)}-{power_label}", rotor, power, None


def parse_nordex_model(raw: str) -> tuple[str, float | None, float | None, str | None]:
    text = raw.upper().strip()
    text = re.sub(r"[^A-Z0-9/\-.]", "", text)

    m_kw = re.fullmatch(r"([A-Z]{1,3})(\d{2,3})/(\d{4})", text)
    if m_kw:
        rotor = float(m_kw.group(2))
        power = float(m_kw.group(3)) / 1000.0
        return f"{m_kw.group(1)}{int(rotor)}/{m_kw.group(3)}", rotor, power, None

    m_class = re.fullmatch(r"([A-Z]{1,3})(\d{2,3})/(\d)\.X", text)
    if m_class:
        rotor = float(m_class.group(2))
        power_class = f"{m_class.group(3)}.X"
        return f"{m_class.group(1)}{int(rotor)}/{power_class}", rotor, float(m_class.group(3)), power_class

    m_class = re.fullmatch(r"([A-Z]{1,3})(\d{2,3})/(\d(?:\.\d)?)X", text)
    if m_class:
        rotor = float(m_class.group(2))
        power_class = f"{m_class.group(3)}X"
        return f"{m_class.group(1)}{int(rotor)}/{power_class}", rotor, float(m_class.group(3)), power_class

    m_exact = re.fullmatch(r"([A-Z]{1,3})(\d{2,3})/(\d(?:\.\d)?)", text)
    if m_exact:
        rotor = float(m_exact.group(2))
        power = float(m_exact.group(3))
        return f"{m_exact.group(1)}{int(rotor)}/{power:.1f}", rotor, power, None

    m_rotor = re.fullmatch(r"([A-Z]{1,3})(\d{2,3})", text)
    if m_rotor:
        rotor = float(m_rotor.group(2))
        return f"{m_rotor.group(1)}{int(rotor)}", rotor, None, None

    return text, None, None, None


def parse_sgre_model(raw: str) -> tuple[str, float | None, float | None, str | None]:
    text = re.sub(r"\s+", " ", raw.upper()).strip()
    m = re.fullmatch(r"SG\s*(\d{1,2}(?:\.\d+)?)\-(\d{2,3})(?:\s*DD)?", text)
    if not m:
        return text, None, None, None
    power = float(m.group(1))
    rotor = float(m.group(2))
    suffix = " DD" if "DD" in text else ""
    model = f"SG {power:.1f}-{int(rotor)}{suffix}"
    return model, rotor, power, None


def format_power_label(power: float) -> str:
    text = f"{power:.2f}".rstrip("0").rstrip(".")
    if "." not in text:
        text = f"{text}.0"
    return text


def extract_suzlon_models(source: dict[str, str], html: str) -> list[dict[str, Any]]:
    url = source["url"]
    m = SUZLON_URL_MODEL_RE.search(url)
    if not m:
        return []

    rotor_i = int(m.group(1))
    rotor = float(rotor_i)
    low, high = SUZLON_POWER_RANGE_BY_ROTOR.get(rotor_i, (1.0, 6.0))

    raw_powers = re.findall(r"\b([1-9](?:\.\d{1,2})?)\s*MW\b", html, re.IGNORECASE)
    values = sorted({round(float(v), 2) for v in raw_powers if low <= float(v) <= high})
    if not values:
        values = SUZLON_FALLBACK_BY_ROTOR.get(rotor_i, [])

    rows: list[dict[str, Any]] = []
    for power in values:
        model = f"S{rotor_i}-{format_power_label(power)}"
        rows.append(
            {
                "oem": "Suzlon",
                "segment": source["segment"],
                "platform": source["platform"],
                "model": model,
                "rotor_diameter_m": rotor,
                "rated_power_mw": float(power),
                "power_class": None,
                "source_url": url,
            }
        )
    return rows


def extract_ge_models(source: dict[str, str], html: str) -> list[dict[str, Any]]:
    segment = source["segment"]
    platform = source["platform"]
    url = source["url"]
    rows: list[dict[str, Any]] = []

    if segment == "Onshore":
        pairs = {(float(power), float(rotor)) for power, rotor in GE_ONSHORE_RE.findall(html)}
        for power, rotor in sorted(pairs):
            if not (1.0 <= power <= 10.0 and 80.0 <= rotor <= 220.0):
                continue
            model = f"GE {format_power_label(power)}-{int(rotor)}"
            rows.append(
                {
                    "oem": "GE",
                    "segment": segment,
                    "platform": platform,
                    "model": model,
                    "rotor_diameter_m": rotor,
                    "rated_power_mw": power,
                    "power_class": None,
                    "source_url": url,
                }
            )
        return rows

    # Offshore: first prioritize explicit "Haliade-X X MW-YYY" pattern,
    # then fallback to generic "X MW-220" occurrences in official GE pages.
    pairs = {(float(power), float(rotor)) for power, rotor in GE_HALIADE_RE.findall(html)}
    if not pairs:
        pairs = {(float(power), float(rotor)) for power, rotor in GE_MW_220_RE.findall(html)}

    for power, rotor in sorted(pairs):
        if not (8.0 <= power <= 20.0 and 160.0 <= rotor <= 260.0):
            continue
        model = f"Haliade-X {format_power_label(power)}-{int(rotor)}"
        rows.append(
            {
                "oem": "GE",
                "segment": segment,
                "platform": platform,
                "model": model,
                "rotor_diameter_m": rotor,
                "rated_power_mw": power,
                "power_class": None,
                "source_url": url,
            }
        )
    return rows


def allow_by_segment(oem: str, segment: str, rated_power_mw: float | None) -> bool:
    if rated_power_mw is None:
        return True
    if oem == "Vestas" and segment == "Onshore" and rated_power_mw >= 8.0:
        return False
    if oem == "Siemens Gamesa" and segment == "Onshore" and rated_power_mw >= 8.0:
        return False
    if oem == "Siemens Gamesa" and segment == "Offshore" and rated_power_mw < 8.0:
        return False
    if oem == "GE" and segment == "Onshore" and rated_power_mw >= 8.0:
        return False
    if oem == "GE" and segment == "Offshore" and rated_power_mw < 8.0:
        return False
    return True


def extract_models(source: dict[str, str], html: str) -> list[dict[str, Any]]:
    oem = source["oem"]
    segment = source["segment"]
    platform = source["platform"]
    url = source["url"]

    if oem == "Vestas":
        matches = set(VESTAS_RE.findall(html))
        parser = parse_vestas_model
    elif oem == "Nordex":
        matches = set(NORDEX_RE.findall(html))
        parser = parse_nordex_model
    elif oem == "Suzlon":
        return extract_suzlon_models(source, html)
    elif oem == "GE":
        return extract_ge_models(source, html)
    else:
        matches = set(SGRE_RE.findall(html))
        parser = parse_sgre_model

    rows: list[dict[str, Any]] = []
    for raw in matches:
        model, rotor, power, power_class = parser(raw)
        if not allow_by_segment(oem, segment, power):
            continue
        rows.append(
            {
                "oem": oem,
                "segment": segment,
                "platform": platform,
                "model": model,
                "rotor_diameter_m": rotor,
                "rated_power_mw": power,
                "power_class": power_class,
                "source_url": url,
            }
        )
    return rows


def merge_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str], dict[str, Any]] = {}

    for row in rows:
        key = (row["oem"], row["model"])
        if key not in merged:
            merged[key] = {
                "oem": row["oem"],
                "model": row["model"],
                "segment": row["segment"],
                "platform": row["platform"],
                "rotor_diameter_m": row["rotor_diameter_m"],
                "rated_power_mw": row["rated_power_mw"],
                "power_class": row["power_class"],
                "source_urls": [row["source_url"]],
            }
            continue

        base = merged[key]
        if row["segment"] not in base["segment"]:
            base["segment"] = f"{base['segment']}, {row['segment']}"
        if row["platform"] not in base["platform"]:
            base["platform"] = f"{base['platform']}, {row['platform']}"
        if row["source_url"] not in base["source_urls"]:
            base["source_urls"].append(row["source_url"])

        if base["rotor_diameter_m"] is None and row["rotor_diameter_m"] is not None:
            base["rotor_diameter_m"] = row["rotor_diameter_m"]
        if base["rated_power_mw"] is None and row["rated_power_mw"] is not None:
            base["rated_power_mw"] = row["rated_power_mw"]
        if base["power_class"] is None and row["power_class"] is not None:
            base["power_class"] = row["power_class"]

    out = list(merged.values())
    out.sort(key=lambda r: (r["oem"], r["segment"], r["rotor_diameter_m"] or 0.0, r["model"]))
    return out


def build_catalog() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    failed: list[str] = []

    for src in SOURCES:
        try:
            html = fetch_html(src["url"])
        except Exception:
            failed.append(src["url"])
            continue
        rows.extend(extract_models(src, html))

    merged = merge_rows(rows)
    payload = {
        "generated_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "sources": SOURCES,
        "failed_sources": failed,
        "models": merged,
    }
    return payload


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = build_catalog()
    OUT_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_FILE}")
    print(f"Model rows: {len(payload['models'])}")
    if payload["failed_sources"]:
        print("Failed sources:")
        for url in payload["failed_sources"]:
            print(f"- {url}")


if __name__ == "__main__":
    main()
