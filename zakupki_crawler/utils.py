from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse


INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
WHITESPACE_RE = re.compile(r"\s+")
NOTICE_44_RE = re.compile(r"/epz/order/notice/([^/]*44)/view/")


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = unescape(value).replace("\xa0", " ")
    return WHITESPACE_RE.sub(" ", normalized).strip()


def join_url(base_url: str, maybe_relative: str | None) -> str | None:
    if not maybe_relative:
        return None
    return urljoin(base_url, maybe_relative)


def json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def sanitize_filename(filename: str) -> str:
    cleaned = clean_text(filename)
    cleaned = INVALID_FILENAME_CHARS.sub("_", cleaned).rstrip(". ")
    return cleaned or "download"


def dedupe_filename(candidate: str, used_names: set[str]) -> str:
    path = Path(candidate)
    stem = path.stem
    suffix = path.suffix
    name = candidate
    index = 2
    while name.lower() in used_names:
        name = f"{stem} ({index}){suffix}"
        index += 1
    used_names.add(name.lower())
    return name


def extract_digits(text: str) -> str:
    return "".join(ch for ch in text if ch.isdigit())


def classify_notice_url(url: str) -> tuple[str, str] | None:
    if "/notice223/" in url:
        return ("223-FZ", "notice223")

    match = NOTICE_44_RE.search(url)
    if match:
        return ("44-FZ", match.group(1))

    return None


def get_notice_query_value(url: str) -> str | None:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    if "noticeInfoId" in query:
        return query["noticeInfoId"][0]
    if "regNumber" in query:
        return query["regNumber"][0]
    return None


def parse_ms_range(raw: str) -> tuple[int, int]:
    parts = raw.split("-", maxsplit=1)
    if len(parts) != 2:
        raise ValueError("Range must be formatted as min-max")
    start = int(parts[0])
    end = int(parts[1])
    if start > end:
        raise ValueError("Range start cannot be greater than range end")
    return start, end
