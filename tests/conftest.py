"""Shared fixtures: the combined OEM dataset loaded the same way the app loads it."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import app  # noqa: E402
from intel import analysis as A  # noqa: E402
from intel.bundle import build_bundle  # noqa: E402


@pytest.fixture(scope="session")
def data():
    paths = {k: str(v) for k, v in app.resolve_oem_cache_files().items()}
    economy, orders, platforms, issues = app.load_all_oem_data("test", paths)
    assert not issues, issues
    return economy, orders, platforms


@pytest.fixture(scope="session")
def economy(data):
    return data[0]


@pytest.fixture(scope="session")
def orders(data):
    return A.prepare_orders(data[1])


@pytest.fixture(scope="session")
def platforms(data):
    return data[2]


@pytest.fixture(scope="session")
def fx():
    return A.load_fx()


@pytest.fixture(scope="session")
def bundle(data):
    return build_bundle(data[0], data[1], data[2], pd.Timestamp("2026-10-13"))
