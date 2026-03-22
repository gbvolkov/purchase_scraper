from __future__ import annotations

from pathlib import Path

from zakupki_crawler.parsers import (
    extract_summary_fields,
    parse_common_info,
    parse_documents,
    parse_lots_223,
    parse_search_results,
)
from zakupki_crawler.utils import classify_notice_url


FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_classify_notice_url_current_families() -> None:
    assert classify_notice_url(
        "https://zakupki.gov.ru/epz/order/notice/notice223/common-info.html?noticeInfoId=19543004"
    ) == ("223-FZ", "notice223")
    assert classify_notice_url(
        "https://zakupki.gov.ru/epz/order/notice/ea20/view/common-info.html?regNumber=0242100000126000036"
    ) == ("44-FZ", "ea20")
    assert classify_notice_url(
        "https://zakupki.gov.ru/epz/order/notice/zk20/view/common-info.html?regNumber=0362200006126000010"
    ) == ("44-FZ", "zk20")
    assert classify_notice_url(
        "https://zakupki.gov.ru/epz/order/notice/ok20/view/common-info.html?regNumber=0249100000326000051"
    ) == ("44-FZ", "ok20")


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
    sections = parse_common_info(
        html,
        "44-FZ",
        "https://zakupki.gov.ru/epz/order/notice/zk20/view/common-info.html?regNumber=0362200006126000010",
    )
    summary = extract_summary_fields(html, "44-FZ", sections)

    assert sections[0]["section"] == "Общая информация о закупке"
    assert summary["registry_number"] == "0362200006126000010"
    assert summary["price_text"] == "14 323,82 ₽"
    assert summary["purchase_title"] == "Оказание услуг по обязательному страхованию гражданской ответственности владельцев автотранспортных средств"
    assert summary["customer_name"] == (
        "ГОСУДАРСТВЕННОЕ БЮДЖЕТНОЕ ОБЩЕОБРАЗОВАТЕЛЬНОЕ УЧРЕЖДЕНИЕ СВЕРДЛОВСКОЙ ОБЛАСТИ "
        '"ЕКАТЕРИНБУРГСКАЯ ШКОЛА-ИНТЕРНАТ № 10, РЕАЛИЗУЮЩАЯ АДАПТИРОВАННЫЕ ОСНОВНЫЕ '
        'ОБЩЕОБРАЗОВАТЕЛЬНЫЕ ПРОГРАММЫ"'
    )
    assert summary["submission_deadline"] == "27.03.2026 08:00 (МСК+2)"


def test_parse_44_documents() -> None:
    html = load_fixture("documents_44.html")
    documents = parse_documents(
        html,
        "44-FZ",
        "https://zakupki.gov.ru/epz/order/notice/zk20/view/documents.html?regNumber=0362200006126000010",
    )

    assert [document.display_name for document in documents] == [
        "Обоснование начальной (максимальной) цены контракта",
        "Проект государственного контракта",
    ]
    assert [document.source_filename for document in documents] == [
        "Обоснование НМЦК.doc",
        "Проект контракта ОСАГО.doc",
    ]
    assert documents[0].signature_url == "https://zakupki.gov.ru/epz/order/notice/signview/listModal.html?attachmentId=210444525"
    assert documents[0].posted_at == "20.03.2026 22:39 (МСК+2)"
    assert documents[0].version == "Действующая"
