from __future__ import annotations

from pathlib import Path

from zakupki_crawler.parsers import (
    extract_summary_fields,
    parse_common_info,
    parse_documents,
    parse_lots_223,
    parse_search_results,
)


FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parse_search_results_mixed_notices() -> None:
    html = load_fixture("search_results_mixed.html")
    results = parse_search_results(html, "https://zakupki.gov.ru/epz/order/extendedsearch/results.html")

    assert [result.registry_number for result in results] == [
        "32615798809",
        "0334200038321000032",
    ]
    assert results[0].law == "223-FZ"
    assert results[1].law == "44-FZ"
    assert results[1].notice_type == "ea44"


def test_parse_223_common_info_and_summary() -> None:
    html = load_fixture("common_223.html")
    sections = parse_common_info(html, "223-FZ", "https://zakupki.gov.ru/epz/order/notice/notice223/common-info.html?noticeInfoId=19513398")
    summary = extract_summary_fields(html, "223-FZ", sections)

    assert sections[0]["section"] == "Сведения о закупке"
    assert sections[1]["fields"][0]["links"] == [
        "https://zakupki.gov.ru/epz/organization/view223/info.html?agencyId=745742"
    ]
    assert summary["registry_number"] == "32615798809"
    assert summary["status"] == "Подача заявок"
    assert summary["purchase_title"] == "Оказание услуг страхового агента"
    assert summary["customer_name"] == 'ООО "ОПТИМА-ТЕХНОЛОГИИ"'
    assert summary["price_text"] == "20 000 000,00 ₽"
    assert summary["submission_deadline"] == "25.03.2026"


def test_parse_223_lots() -> None:
    html = load_fixture("lots_223.html")
    lots = parse_lots_223(html, "https://zakupki.gov.ru/epz/order/notice/notice223/lot-list.html?noticeInfoId=19513398")

    assert len(lots) == 1
    assert lots[0]["lot_number"] == "1"
    assert lots[0]["lot_title"] == "Оказание услуг страхового агента"
    assert lots[0]["lot_url"] == "https://zakupki.gov.ru/epz/order/notice/notice223/lot/lot-info.html?lotId=21135073"


def test_parse_223_documents() -> None:
    html = load_fixture("documents_223.html")
    documents = parse_documents(
        html,
        "223-FZ",
        "https://zakupki.gov.ru/epz/order/notice/notice223/documents.html?noticeInfoId=19513398",
    )

    assert [document.display_name for document in documents] == [
        "ДОКУМЕНТАЦИЯ ЗП 2026.doc",
        "Обоснование НМЦД.xlsx",
    ]
    assert documents[0].signature_url == "https://zakupki.gov.ru/223/purchase/public/download/signs/render.html?id=109235736&modal=true"
    assert documents[0].posted_at == "16.03.2026 07:56 (МСК)"
    assert documents[0].version == "Действующая"


def test_parse_44_common_info_and_summary() -> None:
    html = load_fixture("common_44.html")
    sections = parse_common_info(html, "44-FZ", "https://zakupki.gov.ru/epz/order/notice/ea44/view/common-info.html?regNumber=0334200038321000032")
    summary = extract_summary_fields(html, "44-FZ", sections)

    assert sections[0]["section"] == "Общая информация о закупке"
    assert summary["registry_number"] == "0334200038321000032"
    assert summary["price_text"] == "2 345 678,90 ₽"
    assert summary["purchase_title"] == "Выполнение работ по текущему ремонту"
    assert summary["customer_name"] == "ФОНД ИМУЩЕСТВА ИРКУТСКОЙ ОБЛАСТИ"
    assert summary["submission_deadline"] == "29.03.2026 09:00"


def test_parse_44_documents() -> None:
    html = load_fixture("documents_44.html")
    documents = parse_documents(
        html,
        "44-FZ",
        "https://zakupki.gov.ru/epz/order/notice/ea44/view/documents.html?regNumber=0334200038321000032",
    )

    assert [document.source_filename for document in documents] == [
        "фото Московская, 20.docx",
        "АД Московская, 20.docx",
    ]
    assert documents[0].signature_url == "https://zakupki.gov.ru/epz/order/notice/signview/listModal.html?attachmentId=95990737"
    assert documents[0].posted_at == "20.03.2026 12:00 (МСК)"
    assert documents[0].version == "1"
