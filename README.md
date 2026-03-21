# zakupki-crawler

CLI-краулер для `zakupki.gov.ru` на Python и Playwright. Инструмент принимает URL страницы результатов поиска ЕИС, проходит по найденным закупкам, собирает общую информацию, документы, а для `223-ФЗ` дополнительно парсит список лотов и сохраняет результат в CSV.

## Что умеет

- открывает страницу выдачи ЕИС по готовому `search_url`;
- извлекает закупки из поисковой выдачи и обходит несколько страниц подряд;
- определяет семейство извещения:
  - `223-FZ` для URL вида `.../notice223/...`;
  - `44-FZ` для URL вида `.../notice/*44/view/...`;
- парсит вкладку `Общая информация`;
- парсит вкладку `Документы` и скачивает вложения в локальную папку;
- для `223-FZ` парсит вкладку `Список лотов`;
- записывает итог в `UTF-8 BOM` CSV, чтобы файл корректно открывался в Excel.

## Ограничения

- На вход нужен именно URL страницы результатов поиска, а не карточки одной закупки.
- Поддерживаются только семейства извещений, которые распознаются из URL как `223-ФЗ` и `44-ФЗ`.
- Лоты сейчас извлекаются только для `223-ФЗ`. Для `44-ФЗ` поле `lots_json` останется пустым (`[]`).
- Если часть данных не удалось собрать, запись помечается как `partial`; если закупка не обработана, как `failed`.
- Краулер использует Chromium через Playwright. Без установленного браузера запуск завершится ошибкой.

## Требования

- Python `3.13+`
- Chromium для Playwright

## Установка

### Вариант 1. Через `uv`

```powershell
uv sync --all-groups
uv run playwright install chromium
```

### Вариант 2. Через `pip`

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[dev]
python -m playwright install chromium
```

## Быстрый старт

Пример запуска для готовой страницы результатов поиска:

```powershell
zakupki-crawl "https://zakupki.gov.ru/epz/order/extendedsearch/results.html?..." `
  --output-csv results.csv `
  --downloads-dir downloads `
  --max-pages 1
```

Если пакет не установлен как консольная команда:

```powershell
python -m zakupki_crawler.cli "https://zakupki.gov.ru/epz/order/extendedsearch/results.html?..."
```

Для отладки можно открыть браузер в видимом режиме:

```powershell
zakupki-crawl "https://zakupki.gov.ru/epz/order/extendedsearch/results.html?..." --headed
```

## Использование как библиотеки

Для встраивания в другой проект можно импортировать пакет и вызвать функцию напрямую, без CLI:

```python
from zakupki_crawler import scrape_purchases

records = scrape_purchases(
    "https://zakupki.gov.ru/epz/order/extendedsearch/results.html?...",
    max_pages=1,
    downloads_dir="downloads",
)

first_record = records[0]
print(first_record.registry_number)
print(first_record.purchase_title)
```

По умолчанию при таком вызове CSV не создается, а функция возвращает `list[PurchaseRecord]`.
Если нужен CSV в том же формате, передайте `output_csv="results.csv"`.

Для более тонкой настройки можно использовать низкоуровневый API:

```python
from zakupki_crawler import CrawlConfig, PacingConfig, crawl

records = crawl(
    CrawlConfig(
        search_url="https://zakupki.gov.ru/epz/order/extendedsearch/results.html?...",
        output_csv=None,
        downloads_dir="downloads",
        max_pages=1,
        pacing=PacingConfig(min_delay_ms=200, max_delay_ms=500),
    )
)
```
## Параметры CLI

| Аргумент | По умолчанию | Описание |
| --- | --- | --- |
| `search_url` | обязательный | URL страницы результатов поиска ЕИС |
| `--output-csv` | `results.csv` | путь к итоговому CSV |
| `--downloads-dir` | `downloads` | корневая папка для скачанных документов |
| `--max-pages` | без ограничения | сколько страниц выдачи обработать |
| `--headless` | `true` | запуск Chromium без UI |
| `--headed` | `false` | запуск Chromium с UI |
| `--min-delay-ms` | `600` | минимальная задержка между действиями |
| `--max-delay-ms` | `2200` | максимальная задержка между действиями |
| `--long-pause-chance` | `0.12` | вероятность длинной дополнительной паузы |
| `--long-pause-ms` | `2500-5000` | диапазон длинной паузы в миллисекундах |

## Что появляется на выходе

После выполнения краулер создает:

- CSV-файл, например `results.csv`;
- папку с документами, сгруппированными по реестровому номеру:
  - `downloads/<registry_number>/...`

### Основные поля CSV

- `registry_number` - реестровый номер извещения;
- `law` - семейство закупки (`223-FZ` или `44-FZ`);
- `notice_type` - тип notice из URL;
- `detail_url`, `common_info_url`, `lots_url`, `documents_url` - посещенные страницы;
- `status`, `purchase_title`, `customer_name`, `price_text`;
- `published_at`, `updated_at`, `submission_deadline`;
- `common_info_json` - секции и поля вкладки `Общая информация`;
- `lots_json` - список лотов для `223-ФЗ`;
- `documents_json` - список документов с метаданными, URL подписи и локальными путями;
- `document_urls` - список ссылок на документы;
- `downloaded_files` - локальные пути скачанных файлов;
- `downloads_dir` - каталог документов для конкретной закупки;
- `crawl_status` - `success`, `partial` или `failed`;
- `crawl_error` - текст ошибки, если она была;
- `crawl_ts_utc` - время обхода в UTC.

JSON-поля хранятся строкой в одной ячейке CSV. Это удобно для последующей загрузки в pandas, DuckDB или отдельный JSON-парсинг.

## Пример структуры проекта

```text
zakupki_crawler/
  api.py          # публичный Python API для вызова из кода
  cli.py          # CLI и разбор аргументов
  crawler.py      # основной сценарий обхода и опциональной записи CSV
  models.py       # dataclass-модели конфигурации и результата
  pacing.py       # имитация "человеческих" пауз и кликов
  parsers.py      # HTML-парсеры выдачи, карточки, лотов и документов
  utils.py        # вспомогательные функции
tests/
  fixtures/       # HTML-снимки страниц ЕИС
  test_parsers.py
  test_pacing.py
  test_live_crawler.py
```

## Тесты

Быстрая локальная проверка:

```powershell
uv run pytest -q tests
```

Интеграционные live-тесты обращаются к реальному `zakupki.gov.ru`, поэтому запускаются только при явном флаге окружения:

```powershell
$env:LIVE_ZAKUPKI = "1"
uv run pytest -q tests\test_live_crawler.py
```

Если Chromium для Python Playwright не установлен, live-тесты будут пропущены.

## Как работает обход

1. Краулер открывает страницу выдачи и ждет появления ссылок на карточки закупок.
2. Для каждой новой закупки открывается отдельная вкладка с карточкой.
3. Из вкладки `Общая информация` извлекаются секции и краткая сводка.
4. Для `223-ФЗ` дополнительно читается вкладка `Список лотов`.
5. Из вкладки `Документы` извлекаются ссылки и метаданные, после чего файлы скачиваются локально.
6. Результаты записываются в CSV после завершения обхода, если задан `output_csv`.

## Полезные замечания

- Повторно существующие файлы не скачиваются заново.
- Имена файлов очищаются от недопустимых для Windows символов.
- Профиль браузера создается во временной директории и удаляется после завершения работы.
- Локаль браузера по умолчанию `ru-RU`, таймзона `Europe/Moscow`.

## Лицензия

В репозитории лицензия отдельно не указана. При необходимости добавьте `LICENSE` и политику использования данных ЕИС.


