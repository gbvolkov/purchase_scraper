from __future__ import annotations

import argparse
from pathlib import Path

from zakupki_crawler.api import scrape_purchases
from zakupki_crawler.utils import parse_ms_range


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Playwright-only crawler for zakupki.gov.ru")
    parser.add_argument("search_url", help="Search results URL to crawl")
    parser.add_argument("--output-csv", type=Path, default=Path("results.csv"))
    parser.add_argument("--downloads-dir", type=Path, default=Path("downloads"))
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--headless", dest="headless", action="store_true", default=True)
    parser.add_argument("--headed", dest="headless", action="store_false")
    parser.add_argument("--min-delay-ms", type=int, default=600)
    parser.add_argument("--max-delay-ms", type=int, default=2200)
    parser.add_argument("--long-pause-chance", type=float, default=0.12)
    parser.add_argument("--long-pause-ms", default="2500-5000")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    long_pause_min_ms, long_pause_max_ms = parse_ms_range(args.long_pause_ms)

    scrape_purchases(
        search_url=args.search_url,
        output_csv=args.output_csv,
        downloads_dir=args.downloads_dir,
        max_pages=args.max_pages,
        headless=args.headless,
        min_delay_ms=args.min_delay_ms,
        max_delay_ms=args.max_delay_ms,
        long_pause_chance=args.long_pause_chance,
        long_pause_ms=(long_pause_min_ms, long_pause_max_ms),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
