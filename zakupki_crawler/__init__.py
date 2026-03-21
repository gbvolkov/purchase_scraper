"""Zakupki crawler package."""

from zakupki_crawler.api import build_crawl_config, scrape_purchases
from zakupki_crawler.crawler import crawl, write_records_csv
from zakupki_crawler.models import CrawlConfig, DocumentRecord, PacingConfig, PurchaseRecord, SearchResult

__all__ = [
    "__version__",
    "build_crawl_config",
    "scrape_purchases",
    "crawl",
    "write_records_csv",
    "CrawlConfig",
    "PacingConfig",
    "SearchResult",
    "DocumentRecord",
    "PurchaseRecord",
]

__version__ = "0.1.0"
