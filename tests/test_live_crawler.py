from __future__ import annotations

import csv
import os
from pathlib import Path

import pytest
from playwright.sync_api import Error, sync_playwright

from zakupki_crawler.crawler import crawl
from zakupki_crawler.models import CrawlConfig, PacingConfig


pytestmark = pytest.mark.live


LIVE_223_URL = (
    "https://zakupki.gov.ru/epz/order/extendedsearch/results.html?"
    "morphology=on&search-filter=%D0%94%D0%B0%D1%82%D0%B5+%D1%80%D0%B0%D0%B7%D0%BC%D0%B5%D1%89%D0%B5%D0%BD%D0%B8%D1%8F&"
    "pageNumber=1&sortDirection=false&recordsPerPage=_10&showLotsInfoHidden=false&sortBy=UPDATE_DATE&"
    "fz44=on&fz223=on&af=on&currencyIdGeneral=-1&okpd2Ids=8890766%2C8873940&okpd2IdsCodes=66.22.10.000%2C65&"
    "gws=%D0%92%D1%8B%D0%B1%D0%B5%D1%80%D0%B8%D1%82%D0%B5+%D1%82%D0%B8%D0%BF+%D0%B7%D0%B0%D0%BA%D1%83%D0%BF%D0%BA%D0%B8"
)
LIVE_44_URL = (
    "https://zakupki.gov.ru/epz/order/extendedsearch/results.html?"
    "searchString=0362200006126000010&morphology=on&search-filter=%D0%94%D0%B0%D1%82%D0%B5+"
    "%D1%80%D0%B0%D0%B7%D0%BC%D0%B5%D1%89%D0%B5%D0%BD%D0%B8%D1%8F&sortBy=UPDATE_DATE&sortDirection=false&"
    "recordsPerPage=_10&showLotsInfoHidden=false&fz44=on"
)


def _ensure_browser_available() -> None:
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            browser.close()
    except Error as exc:
        pytest.skip(f"Chromium is not installed for Python Playwright: {exc}")


skip_live = pytest.mark.skipif(
    os.getenv("LIVE_ZAKUPKI") != "1",
    reason="Set LIVE_ZAKUPKI=1 to run live browser tests",
)


def _fast_pacing() -> PacingConfig:
    return PacingConfig(
        min_delay_ms=1,
        max_delay_ms=2,
        long_pause_chance=0,
        long_pause_min_ms=1,
        long_pause_max_ms=1,
    )


@skip_live
def test_live_223_end_to_end(tmp_path: Path) -> None:
    _ensure_browser_available()
    output_csv = tmp_path / "results-223.csv"
    downloads_dir = tmp_path / "downloads-223"
    records = crawl(
        CrawlConfig(
            search_url=LIVE_223_URL,
            output_csv=output_csv,
            downloads_dir=downloads_dir,
            max_pages=1,
            headless=True,
            pacing=_fast_pacing(),
        )
    )

    assert records
    first = records[0]
    assert first.registry_number == "32615798809"
    assert first.crawl_status == "success"
    assert first.lots_json != "[]"
    assert first.downloaded_files

    with output_csv.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["registry_number"] == "32615798809"


@skip_live
def test_live_44_end_to_end(tmp_path: Path) -> None:
    _ensure_browser_available()
    output_csv = tmp_path / "results-44.csv"
    downloads_dir = tmp_path / "downloads-44"
    records = crawl(
        CrawlConfig(
            search_url=LIVE_44_URL,
            output_csv=output_csv,
            downloads_dir=downloads_dir,
            max_pages=1,
            headless=True,
            pacing=_fast_pacing(),
        )
    )

    assert records
    first = records[0]
    assert first.registry_number == "0362200006126000010"
    assert first.crawl_status == "success"
    assert first.lots_json == "[]"
    assert first.downloaded_files
