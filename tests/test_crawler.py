from __future__ import annotations

from pathlib import Path

import pytest

from zakupki_crawler.crawler import ZakupkiCrawler
from zakupki_crawler.models import CrawlConfig, DocumentRecord


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
