from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
)


@dataclass(slots=True)
class PacingConfig:
    min_delay_ms: int = 600
    max_delay_ms: int = 2200
    long_pause_chance: float = 0.12
    long_pause_min_ms: int = 2500
    long_pause_max_ms: int = 5000

    def __post_init__(self) -> None:
        if self.min_delay_ms < 0 or self.max_delay_ms < 0:
            raise ValueError("Delay values must be non-negative")
        if self.min_delay_ms > self.max_delay_ms:
            raise ValueError("min_delay_ms cannot be greater than max_delay_ms")
        if not 0 <= self.long_pause_chance <= 1:
            raise ValueError("long_pause_chance must be between 0 and 1")
        if self.long_pause_min_ms < 0 or self.long_pause_max_ms < 0:
            raise ValueError("Long pause values must be non-negative")
        if self.long_pause_min_ms > self.long_pause_max_ms:
            raise ValueError("long_pause_min_ms cannot be greater than long_pause_max_ms")


@dataclass(slots=True)
class CrawlConfig:
    search_url: str
    output_csv: Path | str | None = Path("results.csv")
    downloads_dir: Path | str = Path("downloads")
    max_pages: int | None = None
    headless: bool = True
    pacing: PacingConfig = field(default_factory=PacingConfig)
    locale: str = "ru-RU"
    timezone_id: str = "Europe/Moscow"
    viewport_width: int = 1536
    viewport_height: int = 960
    user_agent: str = DEFAULT_USER_AGENT

    def __post_init__(self) -> None:
        if self.output_csv is not None and not isinstance(self.output_csv, Path):
            self.output_csv = Path(self.output_csv)
        if not isinstance(self.downloads_dir, Path):
            self.downloads_dir = Path(self.downloads_dir)
        if self.max_pages is not None and self.max_pages <= 0:
            raise ValueError("max_pages must be positive")


@dataclass(slots=True)
class SearchResult:
    registry_number: str
    detail_url: str
    raw_href: str
    law: str
    notice_type: str


@dataclass(slots=True)
class DocumentRecord:
    display_name: str
    source_filename: str | None
    download_url: str
    raw_href: str
    signature_url: str | None = None
    posted_at: str | None = None
    version: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    local_path: str | None = None
    downloaded: bool = False


@dataclass(slots=True)
class PurchaseRecord:
    registry_number: str
    law: str
    notice_type: str
    search_page_url: str
    detail_url: str
    common_info_url: str | None = None
    lots_url: str | None = None
    documents_url: str | None = None
    status: str | None = None
    purchase_title: str | None = None
    customer_name: str | None = None
    price_text: str | None = None
    published_at: str | None = None
    updated_at: str | None = None
    submission_deadline: str | None = None
    common_info_json: str = "[]"
    lots_json: str = "[]"
    documents_json: str = "[]"
    document_urls: str = ""
    downloaded_files: str = ""
    downloads_dir: str = ""
    crawl_status: str = "failed"
    crawl_error: str = ""
    crawl_ts_utc: str = ""
