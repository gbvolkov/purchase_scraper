from __future__ import annotations

import csv
import random
import shutil
import tempfile
from collections.abc import Iterable
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from playwright.sync_api import BrowserContext, Download, Error, Locator, Page, sync_playwright

from zakupki_crawler.models import CrawlConfig, DocumentRecord, PurchaseRecord, SearchResult
from zakupki_crawler.parsers import (
    extract_summary_fields,
    parse_common_info,
    parse_documents,
    parse_lots_223,
    parse_search_results,
)
from zakupki_crawler.pacing import HumanPacer
from zakupki_crawler.utils import dedupe_filename, json_dumps, sanitize_filename


CSV_FIELDNAMES = [
    "registry_number",
    "law",
    "notice_type",
    "search_page_url",
    "detail_url",
    "common_info_url",
    "lots_url",
    "documents_url",
    "status",
    "purchase_title",
    "customer_name",
    "price_text",
    "published_at",
    "updated_at",
    "submission_deadline",
    "common_info_json",
    "lots_json",
    "documents_json",
    "document_urls",
    "downloaded_files",
    "downloads_dir",
    "crawl_status",
    "crawl_error",
    "crawl_ts_utc",
]


def write_records_csv(records: Iterable[PurchaseRecord], output_csv: Path | str) -> None:
    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        for record in records:
            writer.writerow(asdict(record))


class ZakupkiCrawler:
    def __init__(self, config: CrawlConfig, rng: random.Random | None = None) -> None:
        self.config = config
        self.rng = rng or random.Random()
        self.pacer = HumanPacer(config.pacing, rng=self.rng)

    def run(self) -> list[PurchaseRecord]:
        records: list[PurchaseRecord] = []
        self.config.downloads_dir.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(prefix="zakupki-profile-") as profile_dir:
            with sync_playwright() as playwright:
                context = self._launch_context(playwright, Path(profile_dir))
                try:
                    page = context.pages[0] if context.pages else context.new_page()
                    self._open_search(page)
                    records = self._crawl_search_pages(page)
                finally:
                    context.close()

        if self.config.output_csv is not None:
            write_records_csv(records, self.config.output_csv)
        return records

    def _launch_context(self, playwright: Any, profile_dir: Path) -> BrowserContext:
        try:
            return playwright.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=self.config.headless,
                accept_downloads=True,
                locale=self.config.locale,
                timezone_id=self.config.timezone_id,
                user_agent=self.config.user_agent,
                viewport={
                    "width": self.config.viewport_width,
                    "height": self.config.viewport_height,
                },
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                ],
            )
        except Error as exc:
            raise RuntimeError(
                "Failed to launch Chromium via Playwright. Install the browser with "
                "`playwright install chromium` and retry."
            ) from exc

    def _open_search(self, page: Page) -> None:
        page.goto(self.config.search_url, wait_until="domcontentloaded", timeout=45_000)
        self._wait_for_search_results(page)
        self.pacer.post_navigation_pause()

    def _crawl_search_pages(self, search_page: Page) -> list[PurchaseRecord]:
        records: list[PurchaseRecord] = []
        seen_registry_numbers: set[str] = set()
        current_page_index = 1

        while True:
            self._wait_for_search_results(search_page)
            results = parse_search_results(search_page.content(), search_page.url)
            fresh_results = [result for result in results if result.registry_number not in seen_registry_numbers]

            for result in fresh_results:
                seen_registry_numbers.add(result.registry_number)
                records.append(self._process_result(search_page, result))
                self.pacer.between_purchase_pause()

            if self.config.max_pages and current_page_index >= self.config.max_pages:
                break
            if not self._go_to_next_page(search_page):
                break
            current_page_index += 1

        return records

    def _process_result(self, search_page: Page, result: SearchResult) -> PurchaseRecord:
        search_url_before = search_page.url
        record = PurchaseRecord(
            registry_number=result.registry_number,
            law=result.law,
            notice_type=result.notice_type,
            search_page_url=search_url_before,
            detail_url=result.detail_url,
            crawl_ts_utc=datetime.now(UTC).isoformat(),
        )

        if result.law == "unsupported":
            record.crawl_status = "failed"
            record.crawl_error = f"Unsupported notice family for URL: {result.detail_url}"
            return record

        detail_page, opened_new_tab = self._open_detail_page(search_page, result)
        try:
            errors: list[str] = []
            sections, summary = self._parse_common_page(detail_page, result.law)
            record.common_info_url = detail_page.url
            record.status = summary.get("status")
            record.purchase_title = summary.get("purchase_title")
            record.customer_name = summary.get("customer_name")
            record.price_text = summary.get("price_text")
            record.published_at = summary.get("published_at")
            record.updated_at = summary.get("updated_at")
            record.submission_deadline = summary.get("submission_deadline")
            record.common_info_json = json_dumps(sections)

            lots: list[dict[str, str]] = []
            if result.law == "223-FZ":
                try:
                    if self._navigate_notice_tab(detail_page, "Список лотов"):
                        record.lots_url = detail_page.url
                        lots = parse_lots_223(detail_page.content(), detail_page.url)
                except Exception as exc:
                    errors.append(f"lots: {exc}")
            record.lots_json = json_dumps(lots)

            documents: list[DocumentRecord] = []
            try:
                if self._navigate_notice_tab(detail_page, "Документы"):
                    record.documents_url = detail_page.url
                    documents = parse_documents(detail_page.content(), result.law, detail_page.url)
                    self._download_documents(detail_page, result.registry_number, documents)
            except Exception as exc:
                errors.append(f"documents: {exc}")

            record.documents_json = json_dumps([asdict(document) for document in documents])
            record.document_urls = "\n".join(document.download_url for document in documents)
            record.downloaded_files = "\n".join(
                document.local_path for document in documents if document.local_path
            )
            record.downloads_dir = str(self.config.downloads_dir / result.registry_number)

            if errors:
                record.crawl_status = "partial"
                record.crawl_error = " | ".join(errors)
            else:
                record.crawl_status = "success"
        except Exception as exc:
            record.crawl_status = "failed"
            record.crawl_error = str(exc)
        finally:
            self._close_or_restore_search(detail_page, search_page, search_url_before, opened_new_tab)

        return record

    def _parse_common_page(self, page: Page, law: str) -> tuple[list[dict[str, object]], dict[str, str | None]]:
        if "/common-info.html" not in page.url:
            self._navigate_notice_tab(page, "Общая информация")
        self._wait_for_notice_content(page)
        html = page.content()
        sections = parse_common_info(html, law, page.url)
        summary = extract_summary_fields(html, law, sections)
        return sections, summary

    def _download_documents(self, page: Page, registry_number: str, documents: list[DocumentRecord]) -> None:
        if not documents:
            return

        purchase_dir = self.config.downloads_dir / registry_number
        purchase_dir.mkdir(parents=True, exist_ok=True)
        used_names: set[str] = set()

        for document in documents:
            requested_name = sanitize_filename(document.source_filename or document.display_name)
            target_name = dedupe_filename(requested_name, used_names)
            target_path = purchase_dir / target_name

            if target_path.exists():
                document.local_path = str(target_path)
                document.downloaded = False
                continue

            locator = self._find_download_locator(page, document.raw_href)
            with page.expect_download(timeout=30_000) as download_info:
                self.pacer.click(page, locator, post_navigation=False)
            download = download_info.value
            self._save_download(download, target_path)
            document.local_path = str(target_path)
            document.downloaded = True

    def _save_download(self, download: Download, target_path: Path) -> None:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = target_path.with_suffix(target_path.suffix + ".part")
        download.save_as(str(temp_path))
        shutil.move(str(temp_path), str(target_path))

    def _find_download_locator(self, page: Page, raw_href: str) -> Locator:
        escaped = raw_href.replace("\\", "\\\\").replace('"', '\\"')
        locator = page.locator(f'a[href="{escaped}"]').first
        if locator.count() == 0:
            raise RuntimeError(f"Unable to find document link for href {raw_href}")
        return locator

    def _open_detail_page(self, search_page: Page, result: SearchResult) -> tuple[Page, bool]:
        locator = self._find_result_locator(search_page, result)
        self.pacer.pause()
        self.pacer.prepare_locator_click(search_page, locator)

        detail_page = search_page.context.new_page()
        detail_page.goto(result.detail_url, wait_until="domcontentloaded", timeout=45_000)
        self._wait_for_notice_content(detail_page)
        self.pacer.post_navigation_pause()
        return detail_page, True

    def _find_result_locator(self, page: Page, result: SearchResult) -> Locator:
        locator = page.locator(".registry-entry__header-mid__number a").filter(
            has_text=f"№ {result.registry_number}"
        ).first
        if locator.count():
            return locator

        locator = page.get_by_role("link", name=f"№ {result.registry_number}").first
        if locator.count():
            return locator

        escaped = result.raw_href.replace("\\", "\\\\").replace('"', '\\"')
        locator = page.locator(f'a[href="{escaped}"]').filter(has_text=result.registry_number).first
        if locator.count():
            return locator

        raise RuntimeError(f"Unable to locate search result link for {result.registry_number}")

    def _wait_for_new_page(self, context: BrowserContext, existing_pages: set[Page]) -> Page | None:
        deadline = datetime.now().timestamp() + 10
        while datetime.now().timestamp() < deadline:
            for page in context.pages:
                if page not in existing_pages:
                    return page
            self.pacer.sleep_func(0.1)
        return None

    def _navigate_notice_tab(self, page: Page, tab_text: str) -> bool:
        tabs = page.locator(".tabsNav")
        locator = tabs.get_by_role("link", name=tab_text).first
        if locator.count() == 0:
            return False

        href = locator.get_attribute("href") or ""
        if href and href in page.url:
            return True

        self.pacer.click(page, locator, post_navigation=False)
        page.wait_for_load_state("domcontentloaded", timeout=30_000)
        self._wait_for_notice_content(page)
        self.pacer.post_navigation_pause()
        return True

    def _go_to_next_page(self, page: Page) -> bool:
        selectors = [
            'a[title="Следующая страница"]',
            'a[aria-label="Следующая страница"]',
            'a[rel="next"]',
            'a:has-text("Следующая")',
        ]
        locator = None
        for selector in selectors:
            candidate = page.locator(selector).first
            if candidate.count():
                locator = candidate
                break

        if locator is None:
            return False

        self.pacer.between_page_pause()
        self.pacer.click(page, locator, post_navigation=False)
        page.wait_for_load_state("domcontentloaded", timeout=30_000)
        self._wait_for_search_results(page)
        self.pacer.post_navigation_pause()
        return True

    def _close_or_restore_search(
        self,
        detail_page: Page,
        search_page: Page,
        expected_search_url: str,
        opened_new_tab: bool,
    ) -> None:
        if opened_new_tab:
            detail_page.close()
            search_page.bring_to_front()
            self._wait_for_search_results(search_page)
            return

        while detail_page.url != expected_search_url:
            detail_page.go_back(wait_until="domcontentloaded", timeout=30_000)
            if "/extendedsearch/results.html" in detail_page.url:
                break
        self._wait_for_search_results(search_page)

    def _wait_for_search_results(self, page: Page) -> None:
        page.wait_for_selector('a[href*="common-info"]', timeout=30_000)

    def _wait_for_notice_content(self, page: Page) -> None:
        page.wait_for_selector(".tabsNav, .card-common, .blockInfo", timeout=30_000)


def crawl(config: CrawlConfig) -> list[PurchaseRecord]:
    return ZakupkiCrawler(config).run()

