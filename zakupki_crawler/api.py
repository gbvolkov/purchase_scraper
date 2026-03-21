from __future__ import annotations

from pathlib import Path

from zakupki_crawler.crawler import crawl
from zakupki_crawler.models import CrawlConfig, DEFAULT_USER_AGENT, PacingConfig, PurchaseRecord


def build_crawl_config(
    search_url: str,
    *,
    output_csv: Path | str | None = None,
    downloads_dir: Path | str = Path("downloads"),
    max_pages: int | None = None,
    headless: bool = True,
    min_delay_ms: int = 600,
    max_delay_ms: int = 2200,
    long_pause_chance: float = 0.12,
    long_pause_ms: tuple[int, int] = (2500, 5000),
    locale: str = "ru-RU",
    timezone_id: str = "Europe/Moscow",
    viewport_width: int = 1536,
    viewport_height: int = 960,
    user_agent: str = DEFAULT_USER_AGENT,
) -> CrawlConfig:
    long_pause_min_ms, long_pause_max_ms = long_pause_ms
    return CrawlConfig(
        search_url=search_url,
        output_csv=output_csv,
        downloads_dir=downloads_dir,
        max_pages=max_pages,
        headless=headless,
        pacing=PacingConfig(
            min_delay_ms=min_delay_ms,
            max_delay_ms=max_delay_ms,
            long_pause_chance=long_pause_chance,
            long_pause_min_ms=long_pause_min_ms,
            long_pause_max_ms=long_pause_max_ms,
        ),
        locale=locale,
        timezone_id=timezone_id,
        viewport_width=viewport_width,
        viewport_height=viewport_height,
        user_agent=user_agent,
    )


def scrape_purchases(
    search_url: str,
    *,
    output_csv: Path | str | None = None,
    downloads_dir: Path | str = Path("downloads"),
    max_pages: int | None = None,
    headless: bool = True,
    min_delay_ms: int = 600,
    max_delay_ms: int = 2200,
    long_pause_chance: float = 0.12,
    long_pause_ms: tuple[int, int] = (2500, 5000),
    locale: str = "ru-RU",
    timezone_id: str = "Europe/Moscow",
    viewport_width: int = 1536,
    viewport_height: int = 960,
    user_agent: str = DEFAULT_USER_AGENT,
) -> list[PurchaseRecord]:
    config = build_crawl_config(
        search_url,
        output_csv=output_csv,
        downloads_dir=downloads_dir,
        max_pages=max_pages,
        headless=headless,
        min_delay_ms=min_delay_ms,
        max_delay_ms=max_delay_ms,
        long_pause_chance=long_pause_chance,
        long_pause_ms=long_pause_ms,
        locale=locale,
        timezone_id=timezone_id,
        viewport_width=viewport_width,
        viewport_height=viewport_height,
        user_agent=user_agent,
    )
    return crawl(config)


__all__ = ["build_crawl_config", "scrape_purchases"]
