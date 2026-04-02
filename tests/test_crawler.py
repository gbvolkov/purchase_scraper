from __future__ import annotations

from pathlib import Path

import pytest

from zakupki_crawler.crawler import ZakupkiCrawler
from zakupki_crawler.models import CrawlConfig, DocumentRecord, SearchResult


class FakeDownloadContext:
    def __init__(self, download: object) -> None:
        self.value = download

    def __enter__(self) -> FakeDownloadContext:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        return False


class FakePage:
    def __init__(self, download: object | None = None) -> None:
        self.download = download or object()

    def expect_download(self, timeout: int) -> FakeDownloadContext:
        assert timeout == 30_000
        return FakeDownloadContext(self.download)


def make_crawler(tmp_path: Path) -> ZakupkiCrawler:
    crawler = ZakupkiCrawler(
        CrawlConfig(
            search_url="https://example.com/results",
            downloads_dir=tmp_path / "downloads",
        )
    )
    crawler.pacer.click = lambda *args, **kwargs: None
    crawler._find_download_locator = lambda page, raw_href: object()
    return crawler


def make_document() -> DocumentRecord:
    return DocumentRecord(
        display_name="contract.pdf",
        source_filename="contract.pdf",
        download_url="https://example.com/contract.pdf",
        raw_href="/download/contract.pdf",
    )


def test_download_documents_assigns_local_path_for_existing_file(tmp_path: Path) -> None:
    crawler = make_crawler(tmp_path)
    document = make_document()
    target_path = tmp_path / "downloads" / "123" / "contract.pdf"
    target_path.parent.mkdir(parents=True)
    target_path.write_text("existing", encoding="utf-8")

    crawler._download_documents(object(), "123", [document])

    assert document.local_path == str(target_path)
    assert document.downloaded is False


def test_download_documents_leaves_local_path_empty_when_save_fails(tmp_path: Path) -> None:
    crawler = make_crawler(tmp_path)
    document = make_document()

    def fail_save(download: object, target_path: Path) -> None:
        raise RuntimeError("save failed")

    crawler._save_download = fail_save

    with pytest.raises(RuntimeError, match="save failed"):
        crawler._download_documents(FakePage(), "123", [document])

    assert document.local_path is None
    assert document.downloaded is False

class FakeExpandLocator:
    def __init__(self, page: "FakeExpandPage", index: int) -> None:
        self.page = page
        self.index = index

    def is_visible(self) -> bool:
        return self.index < self.page.visible_expanders

    def element_handle(self, timeout: int) -> object:
        assert timeout == 5_000
        return object()


class FakeExpandLocatorCollection:
    def __init__(self, page: "FakeExpandPage") -> None:
        self.page = page

    def count(self) -> int:
        return self.page.visible_expanders

    def nth(self, index: int) -> FakeExpandLocator:
        return FakeExpandLocator(self.page, index)


class FakeExpandPage:
    def __init__(self, visible_expanders: int) -> None:
        self.visible_expanders = visible_expanders
        self.wait_calls = 0

    def get_by_text(self, text: str, exact: bool = False) -> FakeExpandLocatorCollection:
        assert text == "Показать больше"
        assert exact is True
        return FakeExpandLocatorCollection(self)

    def wait_for_function(self, expression: str, *, arg: object, timeout: int) -> None:
        assert "Показать больше" in expression
        assert arg is not None
        assert timeout == 5_000
        self.wait_calls += 1


class StubDetailPage:
    def __init__(self) -> None:
        self.url = "https://example.com/documents"

    def content(self) -> str:
        return "<html></html>"


class StubSearchPage:
    url = "https://example.com/results"


def test_expand_document_attachments_clicks_all_visible_controls(tmp_path: Path) -> None:
    crawler = make_crawler(tmp_path)
    page = FakeExpandPage(visible_expanders=3)
    clicked_indexes: list[int] = []

    def click(page_obj: FakeExpandPage, locator: FakeExpandLocator, *, post_navigation: bool = True) -> None:
        assert post_navigation is False
        clicked_indexes.append(locator.index)
        page_obj.visible_expanders -= 1

    crawler.pacer.click = click
    crawler.pacer.pause = lambda *args, **kwargs: 0

    crawler._expand_document_attachments(page)

    assert clicked_indexes == [0, 0, 0]
    assert page.visible_expanders == 0
    assert page.wait_calls == 3


def test_process_result_expands_documents_before_parsing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    crawler = make_crawler(tmp_path)
    detail_page = StubDetailPage()
    search_page = StubSearchPage()
    call_order: list[str] = []

    crawler._open_detail_page = lambda page, result: (detail_page, True)
    crawler._close_or_restore_search = lambda *args, **kwargs: None
    crawler._parse_common_page = lambda page, law: ([], {})
    crawler._navigate_notice_tab = (
        lambda page, tab_text: tab_text == "Документы"
    )
    crawler._expand_document_attachments = lambda page: call_order.append("expand")
    crawler._download_documents = lambda page, registry_number, documents: call_order.append("download")

    def fake_parse_documents(html: str, law: str, base_url: str) -> list[DocumentRecord]:
        call_order.append("parse")
        return []

    monkeypatch.setattr("zakupki_crawler.crawler.parse_documents", fake_parse_documents)

    result = SearchResult(
        registry_number="123",
        detail_url="https://example.com/detail",
        raw_href="/detail",
        law="44-FZ",
        notice_type="zk20",
    )

    record = crawler._process_result(search_page, result)

    assert call_order == ["expand", "parse", "download"]
    assert record.crawl_status == "success"
    assert record.documents_url == detail_page.url

