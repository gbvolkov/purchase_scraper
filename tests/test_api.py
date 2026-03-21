from __future__ import annotations

import csv
from pathlib import Path

import zakupki_crawler.api as api_module
import zakupki_crawler.crawler as crawler_module
from zakupki_crawler import CrawlConfig, PurchaseRecord, scrape_purchases, write_records_csv


class FakeContext:
    def __init__(self) -> None:
        self.pages: list[object] = []
        self.closed = False

    def new_page(self) -> object:
        return object()

    def close(self) -> None:
        self.closed = True


class FakePlaywrightManager:
    def __enter__(self) -> object:
        return object()

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        return False


def make_record() -> PurchaseRecord:
    return PurchaseRecord(
        registry_number="32615798809",
        law="223-FZ",
        notice_type="notice223",
        search_page_url="https://example.com/results",
        detail_url="https://example.com/detail",
        crawl_status="success",
    )


def test_scrape_purchases_builds_config_and_calls_crawl(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, CrawlConfig] = {}
    records = [make_record()]

    def fake_crawl(config: CrawlConfig) -> list[PurchaseRecord]:
        captured["config"] = config
        return records

    monkeypatch.setattr(api_module, "crawl", fake_crawl)

    result = scrape_purchases(
        "https://example.com/results",
        output_csv=tmp_path / "results.csv",
        downloads_dir=tmp_path / "downloads",
        max_pages=2,
        headless=False,
        min_delay_ms=10,
        max_delay_ms=20,
        long_pause_chance=0.5,
        long_pause_ms=(100, 200),
    )

    assert result == records
    config = captured["config"]
    assert config.search_url == "https://example.com/results"
    assert config.output_csv == tmp_path / "results.csv"
    assert config.downloads_dir == tmp_path / "downloads"
    assert config.max_pages == 2
    assert config.headless is False
    assert config.pacing.min_delay_ms == 10
    assert config.pacing.max_delay_ms == 20
    assert config.pacing.long_pause_chance == 0.5
    assert config.pacing.long_pause_min_ms == 100
    assert config.pacing.long_pause_max_ms == 200


def test_crawl_skips_csv_when_output_csv_is_none(monkeypatch, tmp_path: Path) -> None:
    records = [make_record()]
    fake_context = FakeContext()
    write_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    monkeypatch.setattr(crawler_module, "sync_playwright", lambda: FakePlaywrightManager())
    monkeypatch.setattr(
        crawler_module.ZakupkiCrawler,
        "_launch_context",
        lambda self, playwright, profile_dir: fake_context,
    )
    monkeypatch.setattr(crawler_module.ZakupkiCrawler, "_open_search", lambda self, page: None)
    monkeypatch.setattr(crawler_module.ZakupkiCrawler, "_crawl_search_pages", lambda self, page: records)
    monkeypatch.setattr(
        crawler_module,
        "write_records_csv",
        lambda *args, **kwargs: write_calls.append((args, kwargs)),
    )

    result = crawler_module.crawl(
        CrawlConfig(
            search_url="https://example.com/results",
            output_csv=None,
            downloads_dir=tmp_path / "downloads",
        )
    )

    assert result == records
    assert fake_context.closed is True
    assert (tmp_path / "downloads").exists()
    assert write_calls == []


def test_write_records_csv_creates_readable_csv(tmp_path: Path) -> None:
    output_csv = tmp_path / "results.csv"

    write_records_csv([make_record()], output_csv)

    with output_csv.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert rows == [
        {
            "registry_number": "32615798809",
            "law": "223-FZ",
            "notice_type": "notice223",
            "search_page_url": "https://example.com/results",
            "detail_url": "https://example.com/detail",
            "common_info_url": "",
            "lots_url": "",
            "documents_url": "",
            "status": "",
            "purchase_title": "",
            "customer_name": "",
            "price_text": "",
            "published_at": "",
            "updated_at": "",
            "submission_deadline": "",
            "common_info_json": "[]",
            "lots_json": "[]",
            "documents_json": "[]",
            "document_urls": "",
            "downloaded_files": "",
            "downloads_dir": "",
            "crawl_status": "success",
            "crawl_error": "",
            "crawl_ts_utc": "",
        }
    ]
