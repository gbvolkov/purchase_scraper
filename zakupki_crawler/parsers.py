from __future__ import annotations

from html import unescape
from typing import Any

from bs4 import BeautifulSoup, Tag

from zakupki_crawler.models import DocumentRecord, SearchResult
from zakupki_crawler.utils import classify_notice_url, clean_text, extract_digits, join_url


def parse_search_results(html: str, base_url: str) -> list[SearchResult]:
    soup = BeautifulSoup(html, "html.parser")
    results: list[SearchResult] = []
    seen: set[str] = set()

    for anchor in soup.select('a[href*="/epz/order/notice/"][href*="common-info"]'):
        href = anchor.get("href")
        if not href:
            continue

        detail_url = join_url(base_url, href)
        if not detail_url:
            continue

        notice_kind = classify_notice_url(detail_url)
        law = notice_kind[0] if notice_kind else "unsupported"
        notice_type = notice_kind[1] if notice_kind else "unknown"
        registry_number = extract_digits(anchor.get_text(" ", strip=True))
        if not registry_number or registry_number in seen:
            continue

        seen.add(registry_number)
        results.append(
            SearchResult(
                registry_number=registry_number,
                detail_url=detail_url,
                raw_href=href,
                law=law,
                notice_type=notice_type,
            )
        )

    return results


def parse_common_info(html: str, law: str, base_url: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    if law == "223-FZ":
        return _parse_223_common_sections(soup, base_url)
    if law == "44-FZ":
        return _parse_44_common_sections(soup, base_url)
    return []


def extract_summary_fields(html: str, law: str, sections: list[dict[str, Any]]) -> dict[str, str | None]:
    soup = BeautifulSoup(html, "html.parser")
    field_lookup = flatten_section_fields(sections)

    summary = {
        "registry_number": _extract_registry_number(soup) or field_lookup.get("Реестровый номер извещения"),
        "status": _first_selector_text(
            soup,
            [
                ".registry-entry__header-mid__title",
                ".cardMainInfo__sectionStage",
                ".cardMainInfo__stage",
            ],
        ),
        "purchase_title": (
            _find_labeled_value(soup, "Объект закупки")
            or field_lookup.get("Наименование закупки")
            or field_lookup.get("Наименование объекта закупки")
        ),
        "customer_name": (
            _find_labeled_value(soup, "Заказчик")
            or field_lookup.get("Наименование организации")
            or field_lookup.get("Размещение осуществляет")
        ),
        "price_text": (
            _find_labeled_value(soup, "Начальная цена")
            or _find_labeled_value(soup, "Начальная (максимальная) цена контракта")
            or _find_labeled_value(soup, "Начальная (максимальная) цена договора")
        ),
        "published_at": (
            _find_labeled_value(soup, "Размещено")
            or field_lookup.get("Дата размещения извещения")
            or field_lookup.get("Дата размещения")
        ),
        "updated_at": _find_labeled_value(soup, "Обновлено")
        or field_lookup.get("Дата размещения текущей редакции извещения"),
        "submission_deadline": (
            field_lookup.get("\u0414\u0430\u0442\u0430 \u0438 \u0432\u0440\u0435\u043c\u044f \u043e\u043a\u043e\u043d\u0447\u0430\u043d\u0438\u044f \u0441\u0440\u043e\u043a\u0430 \u043f\u043e\u0434\u0430\u0447\u0438 \u0437\u0430\u044f\u0432\u043e\u043a")
            or _find_labeled_value(soup, "\u041e\u043a\u043e\u043d\u0447\u0430\u043d\u0438\u0435 \u043f\u043e\u0434\u0430\u0447\u0438 \u0437\u0430\u044f\u0432\u043e\u043a")
            or field_lookup.get("\u0414\u0430\u0442\u0430 \u0438 \u0432\u0440\u0435\u043c\u044f \u043e\u043a\u043e\u043d\u0447\u0430\u043d\u0438\u044f \u0441\u0440\u043e\u043a\u0430 \u043f\u043e\u0434\u0430\u0447\u0438 \u0437\u0430\u044f\u0432\u043e\u043a (\u043f\u043e \u043c\u0435\u0441\u0442\u043d\u043e\u043c\u0443 \u0432\u0440\u0435\u043c\u0435\u043d\u0438 \u0437\u0430\u043a\u0430\u0437\u0447\u0438\u043a\u0430)")
            or field_lookup.get("\u0414\u0430\u0442\u0430 \u043e\u043a\u043e\u043d\u0447\u0430\u043d\u0438\u044f \u0441\u0440\u043e\u043a\u0430 \u043f\u043e\u0434\u0430\u0447\u0438 \u0437\u0430\u044f\u0432\u043e\u043a")
        ),
    }

    if law == "44-FZ" and not summary["purchase_title"]:
        summary["purchase_title"] = field_lookup.get("Наименование объекта закупки")

    return summary


def parse_lots_223(html: str, base_url: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table.table")
    if table is None:
        return []

    header_row = table.select_one("thead tr")
    if header_row is None:
        return []

    headers = [clean_text(th.get_text(" ", strip=True)) for th in header_row.find_all("th")]
    lots: list[dict[str, str]] = []

    for row in table.select("tbody > tr"):
        classes = row.get("class", [])
        if "hidden-tr" in classes or "d-none" in classes:
            continue

        cells = row.find_all("td", recursive=False)
        if not cells:
            continue

        lot_data: dict[str, str] = {}
        first_link = cells[0].find("a", href=True)
        first_text = clean_text(cells[0].get_text(" ", strip=True))
        if first_link:
            href = first_link.get("href")
            parts = [clean_text(part) for part in first_link.stripped_strings]
            if parts:
                lot_data["lot_number"] = parts[0]
                if len(parts) > 1:
                    lot_data["lot_title"] = clean_text(" ".join(parts[1:]))
            if href:
                lot_data["lot_url"] = join_url(base_url, href) or href
        if "lot_number" not in lot_data:
            lot_data["lot_number"] = extract_digits(first_text)
        if "lot_title" not in lot_data:
            lot_data["lot_title"] = first_text

        for index, header in enumerate(headers):
            if index >= len(cells):
                continue
            lot_data[header] = clean_text(cells[index].get_text(" ", strip=True))

        lots.append(lot_data)

    return lots


def parse_documents(html: str, law: str, base_url: str) -> list[DocumentRecord]:
    soup = BeautifulSoup(html, "html.parser")
    records: list[DocumentRecord] = []
    seen: set[str] = set()

    for link in soup.select("a[href]"):
        href = link.get("href", "")
        absolute_url = join_url(base_url, href)
        if not absolute_url or not _is_download_href(absolute_url):
            continue
        if absolute_url in seen:
            continue
        seen.add(absolute_url)

        metadata = _extract_document_metadata(link)
        records.append(
            DocumentRecord(
                display_name=_extract_document_name(link, law),
                source_filename=_extract_source_filename(link),
                download_url=absolute_url,
                raw_href=href,
                signature_url=_extract_signature_url(link, base_url, law),
                posted_at=metadata.get("Размещено") or metadata.get("Дата размещения"),
                version=metadata.get("Редакция") or metadata.get("Версия"),
                metadata=metadata,
            )
        )

    return records


def flatten_section_fields(sections: list[dict[str, Any]]) -> dict[str, str]:
    flattened: dict[str, str] = {}
    for section in sections:
        for field in section.get("fields", []):
            title = clean_text(field.get("title"))
            value = clean_text(field.get("value"))
            if title and value and title not in flattened:
                flattened[title] = value
    return flattened


def _parse_223_common_sections(soup: BeautifulSoup, base_url: str) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for section in soup.select("section.common-text"):
        caption = section.select_one(".common-text__caption")
        title = clean_text(caption.get_text(" ", strip=True) if caption else "")
        if not title:
            continue

        fields: list[dict[str, Any]] = []
        for row in section.select(".row > .col-9"):
            title_tag = row.select_one(".common-text__title")
            value_tag = row.select_one(".common-text__value")
            if not title_tag or not value_tag:
                continue
            fields.append(_build_field(title_tag, value_tag, base_url))

        sections.append({"section": title, "fields": fields})

    return sections


def _parse_44_common_sections(soup: BeautifulSoup, base_url: str) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for block in soup.select(".row.blockInfo"):
        block_title = block.select_one(".blockInfo__title")
        section_title = clean_text(block_title.get_text(" ", strip=True) if block_title else "")
        if not section_title:
            continue

        fields: list[dict[str, Any]] = []
        for section in block.select("section.blockInfo__section"):
            title_tag = section.select_one(".section__title")
            value_tag = section.select_one(".section__info")
            if not title_tag or not value_tag:
                continue
            fields.append(_build_field(title_tag, value_tag, base_url))

        sections.append({"section": section_title, "fields": fields})

    return sections


def _build_field(title_tag: Tag, value_tag: Tag, base_url: str) -> dict[str, Any]:
    return {
        "title": clean_text(title_tag.get_text(" ", strip=True)),
        "value": clean_text(value_tag.get_text(" ", strip=True)),
        "links": [
            join_url(base_url, anchor.get("href")) or anchor.get("href")
            for anchor in value_tag.select("a[href]")
        ],
    }


def _extract_registry_number(soup: BeautifulSoup) -> str | None:
    selectors = [
        '.registry-entry__header-mid__number a[href]',
        '.registry-entry__header-mid__number a[href=""]',
    ]
    for selector in selectors:
        link = soup.select_one(selector)
        if link is None:
            continue
        digits = extract_digits(link.get_text(" ", strip=True))
        if digits:
            return digits
    return None


def _find_labeled_value(soup: BeautifulSoup, label: str) -> str | None:
    pairs = [
        ("registry-entry__body-title", "registry-entry__body-value"),
        ("price-block__title", "price-block__value"),
        ("data-block__title", "data-block__value"),
        ("common-text__title", "common-text__value"),
        ("section__title", "section__info"),
    ]
    normalized_label = clean_text(label)

    for title_class, value_class in pairs:
        for title_tag in soup.select(f".{title_class}"):
            if clean_text(title_tag.get_text(" ", strip=True)) != normalized_label:
                continue
            value_tag = title_tag.find_next_sibling(class_=value_class)
            if value_tag is None and isinstance(title_tag.parent, Tag):
                value_tag = title_tag.parent.select_one(f".{value_class}")
            if value_tag is not None:
                return clean_text(value_tag.get_text(" ", strip=True))

    return None


def _first_selector_text(soup: BeautifulSoup, selectors: list[str]) -> str | None:
    for selector in selectors:
        tag = soup.select_one(selector)
        if tag is None:
            continue
        text = clean_text(tag.get_text(" ", strip=True))
        if text:
            return text
    return None


def _is_download_href(url: str) -> bool:
    return "/purchase/public/download/download.html" in url or "/filestore/public/1.0/download/" in url


def _extract_document_name(link: Tag, law: str) -> str:
    candidates = (
        (link.get_text(" ", strip=True), link.get("title"), link.get("data-tooltip"))
        if law == "44-FZ"
        else (link.get("title"), link.get("data-tooltip"), link.get_text(" ", strip=True))
    )
    for candidate in candidates:
        cleaned = _clean_document_label(candidate)
        if cleaned:
            return cleaned
    return "download"


def _extract_source_filename(link: Tag) -> str | None:
    for candidate in (link.get("title"), link.get("data-tooltip")):
        cleaned = _clean_document_label(candidate)
        if cleaned:
            return cleaned
    return None


def _clean_document_label(raw: str | None) -> str:
    if not raw:
        return ""
    text = BeautifulSoup(unescape(raw), "html.parser").get_text(" ", strip=True)
    text = clean_text(text)
    if text.startswith("Просмотреть ЭП"):
        return ""
    return text


def _extract_signature_url(link: Tag, base_url: str, law: str) -> str | None:
    for ancestor in [link.parent, *list(link.parents)[:4]]:
        if not isinstance(ancestor, Tag):
            continue
        for candidate in ancestor.select("a[href]"):
            href = candidate.get("href")
            if not href or href == link.get("href"):
                continue
            absolute = join_url(base_url, href)
            if not absolute:
                continue
            if law == "223-FZ" and "/download/signs/" in absolute:
                return absolute
            if law == "44-FZ" and "attachmentId=" in absolute:
                return absolute
    return None


def _extract_document_metadata(link: Tag) -> dict[str, str]:
    for ancestor in link.parents:
        if not isinstance(ancestor, Tag):
            continue
        metadata = _extract_metadata_pairs(ancestor)
        if {"Размещено", "Дата размещения", "Редакция", "Версия"} & metadata.keys():
            return metadata
    return {}


def _extract_metadata_pairs(container: Tag) -> dict[str, str]:
    pairs: dict[str, str] = {}
    selectors = [
        ("attachment__text", "attachment__value"),
        ("section__attrib", "section__value"),
    ]
    for title_class, value_class in selectors:
        for title_tag in container.select(f".{title_class}"):
            title = clean_text(title_tag.get_text(" ", strip=True))
            if not title:
                continue
            value_tag = title_tag.find_next_sibling(class_=value_class)
            if value_tag is None and isinstance(title_tag.parent, Tag):
                value_tag = title_tag.parent.select_one(f".{value_class}")
            if value_tag is None:
                continue
            value = clean_text(value_tag.get_text(" ", strip=True))
            if value and title not in pairs:
                pairs[title] = value
    return pairs
