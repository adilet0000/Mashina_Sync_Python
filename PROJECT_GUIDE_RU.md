# Mashina.kg Sync Python: понятная карта проекта

Этот проект - новая Python-версия старых PHP/Symfony sync-скриптов Mashina.kg.

Главная задача проекта: брать объявления из внешних provider feeds/API/HTML-страниц, приводить их к единому формату и синхронизировать с новой catalog DB.

Это не frontend, не UI и не миграция старой БД в новую. Старый PHP использовался как источник понимания бизнес-логики, но новая версия должна работать самостоятельно на Python.

## Что проект делает

Проект выполняет такой поток:

```text
Provider feed/API/page
-> Python provider adapter/parser
-> LegacyAd DTO
-> CatalogListingPayload
-> чтение текущих объявлений из новой catalog DB
-> сравнение текущих и новых данных
-> insert/update/deactivate listings
-> insert/deactivate images
-> upsert listing_attributes
-> dry-run/report/verify
```

Пример: Autoland отдает CSV-фид. Python скачивает CSV, парсит строки, группирует их по legacy-правилам, создает внутренние `LegacyAd`, маппит их в catalog payload и дальше решает, что надо создать, обновить, оставить без изменений или деактивировать.

## Что проект заменяет

Python-проект заменяет legacy PHP console commands:

- `app:sync-allmotors`
- `app:sync-autohub`
- `app:sync-autoland`
- `app:sync-autoshina`
- `app:sync-avtoinstall`
- `app:sync-banzaimotors`
- `app:sync-bavaria`
- `app:sync-detalkg`
- `app:sync-kia`
- `app:sync-lexus`
- `app:sync-okayamaomsk`
- `app:sync-shinabar`
- `app:sync-shredder`
- `app:sync-toyota`
- `app:sync-toyota-tradein`

Drive2/community parser не перенесен, потому что это не catalog ads sync. В новой БД не найдена отдельная таблица под Drive2 community posts.

## Что проект не делает

Проект не делает:

- не поднимает старый Symfony/PHP runtime;
- не использует старый PHP frontend;
- не запускает yarn/npm/webpack/composer;
- не мигрирует старые данные из old DB;
- не пишет в старый internal API;
- не использует старые PHP Bearer tokens для записи;
- не делает real write в catalog DB без специальных safety flags.

## Почему в Python нет старых токенов

В старом PHP `.env` provider-токены использовались для старого Mashina internal API:

```text
GET    self/info
GET    sync/ads
POST   sync/ads/bulk-create
PATCH  sync/ads/bulk-update
DELETE sync/ads/bulk-delete
POST   sync/images
DELETE sync/images
```

Новая Python-версия не пишет через этот old API. Она должна писать напрямую в новую catalog DB. Поэтому вместо старых токенов нужны:

- `CATALOG_DATABASE_URL` - подключение к новой catalog DB;
- `SYNC_CATALOG_USER_ID` или `SYNC_CATALOG_USER_ID_<PROVIDER>` - от имени какого catalog user создавать объявления;
- `SYNC_CATALOG_PHONES` или `SYNC_CATALOG_PHONES_<PROVIDER>` - телефоны для объявлений;
- `SYNC_PROVIDER_*_FEED_URL` - URL фида provider-а, если его надо переопределить;
- safety flags для запрета случайной записи.

## Главные папки

```text
.
├── app/             основной Python-код
├── tests/           unit/integration-like тесты без real DB writes
├── docs/            короткая документация внутри нового проекта
├── docs_from_php/   документы аудита legacy PHP и новой БД
├── README.md        основная инструкция запуска
├── PROJECT_GUIDE_RU.md  этот файл
├── pyproject.toml   зависимости, настройки pytest/ruff, entrypoint
├── .env.example     шаблон env без секретов
└── .env             локальные реальные настройки, не коммитить
```

## Корневые файлы

### `README.md`

Основная техническая инструкция на английском: назначение проекта, команды запуска, dry-run, real write, verify mode, safety flags.

### `PROJECT_GUIDE_RU.md`

Русская карта проекта. Объясняет простыми словами, что есть где и как все связано.

### `pyproject.toml`

Описывает Python-пакет и зависимости.

Основные зависимости:

- `SQLAlchemy 2.x` - работа с catalog DB;
- `psycopg` - PostgreSQL driver;
- `pydantic-settings` - загрузка `.env`;
- `Typer` - CLI-команды;
- `httpx` - скачивание provider feeds/pages;
- `beautifulsoup4` - HTML parsing;
- `defusedxml` - безопасный XML/YML parsing;
- `pytest` - тесты;
- `ruff` - lint/format check.

### `.env.example`

Шаблон env-переменных без секретов. Его можно копировать в `.env`.

### `.env`

Локальные реальные настройки. Может содержать DB URL, user ids, phones, feed URL overrides. Не должен попадать в git.

## Папка `app/`

Это основной код приложения.

```text
app/
├── cli/
├── config/
├── db/
├── dto/
├── mappers/
├── models/
├── providers/
├── repositories/
├── services/
├── sync/
└── utils/
```

## `app/cli/` - CLI-команды

### `app/cli/__init__.py`

Делает папку Python package. Логики почти нет.

### `app/cli/__main__.py`

Позволяет запускать CLI так:

```bash
python -m app.cli ...
```

### `app/cli/main.py`

Точка входа CLI. Подключает Typer-приложение.

### `app/cli/commands.py`

Главный файл CLI-команд.

Команды:

```bash
python -m app.cli healthcheck
python -m app.cli inspect-db
python -m app.cli list-providers
python -m app.cli sync --provider autoland --dry-run --limit 10
python -m app.cli sync-all --dry-run --limit 10
```

Что делает:

- загружает settings;
- включает logging;
- запускает healthcheck/inspect-db/list-providers/sync/sync-all;
- передает управление в `SyncService`;
- возвращает non-zero exit code при критичных ошибках.

## `app/config/` - настройки и mapping

### `app/config/__init__.py`

Package marker.

### `app/config/settings.py`

Главный загрузчик `.env`.

Отвечает за:

- `CATALOG_DATABASE_URL`;
- `SYNC_TARGET`;
- `SYNC_DRY_RUN`;
- `SYNC_ALLOW_CATALOG_WRITES`;
- статусы listings/images;
- batch size;
- HTTP timeout;
- provider feed URL overrides;
- provider-specific user ids;
- provider-specific phones.

Важная деталь: пустые optional env значения игнорируются как `None`, чтобы строки вида `SYNC_CATALOG_USER_ID_AUTOLAND=` не ломали запуск.

### `app/config/providers.py`

Registry provider-ов.

Здесь перечислены provider keys:

- `autohub`
- `autoland`
- `shredder`
- `okayamaomsk`
- `banzaimotors`
- `bavaria`
- `shinabar`
- `avtoinstall`
- `allmotors`
- `autoshina`
- `detalkg`
- `toyota`
- `toyota_tradein`
- `lexus`
- `kia`

Используется командой `list-providers` и `sync-all`.

### `app/config/catalog_mapping.py`

Mapping старых legacy fields в catalog attributes.

Примеры:

- old `type_id=30` -> catalog category `35` (`parts_supplies`);
- old currency `1` -> `KGS`;
- old currency `2` -> `USD`;
- `make` -> attribute slug `make`;
- `model` -> `model`;
- `external_id` -> `external_id`;
- `phone` -> `phone`.

Если надо поменять соответствие старого поля и новой catalog DB, начинать смотреть нужно отсюда.

## `app/db/` - подключение к БД и безопасность

### `app/db/__init__.py`

Package marker.

### `app/db/session.py`

Создает SQLAlchemy engine/session для catalog DB.

Использует `CATALOG_DATABASE_URL`.

### `app/db/health.py`

Проверка подключения к DB.

Используется CLI-командой:

```bash
python -m app.cli healthcheck
```

### `app/db/reflection.py`

Read-only inspection catalog DB.

Проверяет наличие таблиц:

- `listings`
- `listing_attributes`
- `attributes`
- `attribute_options`
- `images`
- `listing_counters`
- `listing_promotions`

Используется командой:

```bash
python -m app.cli inspect-db
```

### `app/db/safety.py`

Safety checks перед записью.

Реальная запись разрешается только если одновременно:

```env
SYNC_TARGET=catalog
SYNC_DRY_RUN=0
SYNC_ALLOW_CATALOG_WRITES=1
```

И CLI вызван без `--dry-run`, например с `--no-dry-run`.

Также этот слой печатает DB host/name/user без пароля.

### `app/db/models.py`

Минимальные DB/table модели или placeholder для SQLAlchemy-структур. Основная работа с SQL сейчас находится в repositories.

## `app/dto/` - внутренние структуры данных

DTO - это простые объекты для передачи данных между слоями.

### `app/dto/__init__.py`

Package marker.

### `app/dto/legacy_ad.py`

`LegacyAd` - нормализованное объявление в старом legacy-смысле.

Это практическая замена PHP associative array из `BaseSync::FIELD_*`.

Содержит поля:

- `source`
- `external_id`
- `type_id`
- `name`
- `description`
- `price`
- `old_price`
- `currency`
- `region`
- `town`
- `make`
- `model`
- `year`
- `body`
- `fuel`
- `gear_box`
- `phone`
- `images`
- tire/wheel fields
- `raw`
- `errors`
- `warnings`

Provider adapter-ы создают именно `LegacyAd`.

### `app/dto/catalog_payload.py`

`CatalogListingPayload` - то, что уже готово для записи в новую catalog DB.

Содержит:

- `source`
- `external_id`
- `user_id`
- `category_id`
- `title`
- `description`
- `price`
- `currency`
- `status`
- `attributes`
- `images`
- `raw_legacy_ad`

Идея: provider parsing отделен от DB mapping. Provider ничего не должен знать о SQL.

### `app/dto/sync_result.py`

`SyncResult` - итог запуска sync.

Считает:

- сколько записей прочитано;
- сколько валидных;
- сколько пропущено;
- сколько было бы создано/обновлено/деактивировано;
- сколько реально создано/обновлено/деактивировано;
- сколько images добавлено/деактивировано;
- warnings/errors;
- verification result.

## `app/mappers/` - преобразование DTO в catalog payload

### `app/mappers/__init__.py`

Package marker.

### `app/mappers/listing_mapper.py`

Главный mapper:

```text
LegacyAd -> CatalogListingPayload
```

Отвечает за:

- выбор `user_id`;
- mapping `type_id -> category_id`;
- title/description fallback;
- price/currency mapping;
- статус по умолчанию;
- сбор attributes;
- сбор images.

Если provider уже создает `LegacyAd`, дальше почти вся общая логика идет через этот mapper.

### `app/mappers/attribute_mapper.py`

Маппит legacy fields в catalog attributes.

Примеры:

- `external_id`;
- `make`;
- `model`;
- `condition`;
- `phone`;
- `region`;
- `city`;
- `old_price`;
- `vincode`.

Также решает, какое значение положить в `value_text`, `value_number`, `value_boolean`, `value_json` или `attribute_options_id`.

### `app/mappers/image_mapper.py`

Маппит старые image formats в payload для таблицы `images`.

Поддерживает старые форматы:

```text
plain_url
index|url
```

На выходе дает:

- `external_url`;
- `priority`;
- stable `hash`;
- `status`;
- `is_blurred`;
- `user_id`.

## `app/providers/` - адаптеры provider-ов

Provider adapter отвечает только за получение и парсинг данных provider-а. Он не должен писать в DB.

### `app/providers/__init__.py`

Подключает provider modules.

### `app/providers/base.py`

Базовый интерфейс provider-а.

Каждый provider должен уметь вернуть список `LegacyAd`.

### `app/providers/common.py`

Общие helper-функции для provider parsing:

- очистка строк;
- разбор CSV;
- разбор цен;
- split images;
- ordered images;
- HTML helpers;
- простая статистика parsing-а.

### `app/providers/bazon.py`

Общий код для provider-ов, которые используют Baz-on CSV.

Используется несколькими provider-ами:

- Autohub;
- Shredder;
- Banzaimotors;
- Bavaria;
- Shinabar;
- OkayamaOmsk частично.

Содержит общую CSV-логику, grouping, mapping parts/tires/wheels.

### `app/providers/autoland.py`

Autoland provider.

Источник: CSV feed.

Особенности:

- cp1251/windows-1251 encoding;
- delimiter `;`;
- группировка по `name/make/model`;
- `Артикул` -> `external_id`;
- grouped external ids соединяются через comma;
- `type_id=30`;
- currency `KGS`;
- images обязательны;
- condition по legacy-правилу.

### `app/providers/autohub.py`

Autohub provider.

Источник: Baz-on CSV parts.

Особенности:

- grouping by name/make/model/year/generation;
- commercial makes `setra/neoplan/man` -> `type_id=36`;
- остальные parts -> `type_id=30`;
- price import disabled, price обычно `0`;
- max 12 images.

### `app/providers/shredder.py`

Shredder provider.

Похож на Autohub:

- Baz-on parts CSV;
- commercial makes -> `type_id=36`;
- price disabled;
- max 12 images.

### `app/providers/okayamaomsk.py`

OkayamaOmsk provider.

Источник: CSV parts.

Особенности:

- no grouping;
- `region=9`;
- `town=62`;
- `featured_option=2`;
- `comment_allowed=2`;
- price direct;
- description дополняется delivery/payment текстом.

### `app/providers/banzaimotors.py`

Banzai Motors provider.

Источники:

- parts CSV;
- tires/wheels CSV.

Особенности:

- parts -> `type_id=30`;
- tires -> `type_id=31`;
- wheels -> `type_id=32`;
- price import disabled для parts;
- specs tires/wheels сохраняются в DTO;
- max 12 images.

### `app/providers/bavaria.py`

Bavaria provider.

Источники:

- parts CSV;
- tires/wheels CSV.

Особенности:

- parts grouping by name/make/model/year/generation;
- makes `depo/bosch/дубликат` заменяются на default BMW;
- parts price disabled/omitted по legacy;
- tires/wheels price direct.

### `app/providers/shinabar.py`

Shinabar provider.

Источник: tire/wheel CSV.

Особенности:

- de-duplicate by `Артикул`;
- mostly tire-focused;
- tire dimensions required;
- condition required;
- price/currency direct.

### `app/providers/avtoinstall.py`

Avtoinstall provider.

Источник: CSV.

Особенности:

- фильтр `_STOCK_STATUS_ == В наличии`;
- фильтр `_STATUS_ == 1`;
- `_ID_` -> `external_id`;
- `type_id=33`;
- `condition=2`;
- images main + gallery как ordered list;
- description очищается от HTML;
- special price window logic.

### `app/providers/allmotors.py`

Allmotors provider.

Источник: HTML crawler.

Особенности:

- categories map to type_id;
- product slug -> external_id;
- price import enabled;
- tires parse dimensions from title;
- unknown category логируется и fallback -> `type_id=30`.

### `app/providers/autoshina.py`

Autoshina provider.

Источник: HTML crawler.

Особенности:

- tire-only;
- `type_id=31`;
- product id from URL;
- image required;
- brand/model required;
- tire width/height/size required;
- season defaults to summer;
- condition `2`.

### `app/providers/detalkg.py`

DetalKg provider.

Источники:

- YML/XML parts feed;
- HTML tire pages.

Особенности:

- parts external_id = offer `@id`;
- skip if count is `0`;
- parts price +20%;
- parts `type_id=30`, condition `2`;
- tires parse article/specs/price/description/images;
- tires `type_id=31`, condition `2`, featured `1`.

### `app/providers/autocrm.py`

Общий AutoCRM XML provider.

Используется для:

- Toyota;
- Toyota Trade-In;
- Lexus;
- Kia.

Особенности:

- XML parsing через safe parser;
- VIN -> external_id;
- cars -> `type_id=1`;
- ordered images;
- car reference fields;
- provider-specific preserve policies.

### `app/providers/toyota.py`

Toyota provider поверх AutoCRM.

Особенности:

- `isUsed=0`;
- VIN -> external_id;
- `type_id=1`;
- images required.

### `app/providers/toyota_tradein.py`

Toyota Trade-In provider поверх AutoCRM.

Особенности:

- `isUsed=1`;
- VIN -> external_id;
- currency rate через `SYNC_PROVIDER_TOYOTA_TRADEIN_CURRENCY_RATE`;
- legacy behavior по price/old_price сохранен насколько возможно без old API.

### `app/providers/lexus.py`

Lexus provider поверх AutoCRM.

Особенности:

- Lexus-specific make/model fallback;
- preserve current price по legacy-поведению;
- image diff by URL.

### `app/providers/kia.py`

Kia provider поверх AutoCRM.

Особенности:

- VIN first;
- затем de-dupe by `modification + complectation`;
- сортировка по featured option;
- legacy debug `print_r/exit` не повторяется.

## `app/repositories/` - работа с catalog DB

Repositories - единственное место, где должен жить SQL/DB access.

### `app/repositories/__init__.py`

Package marker.

### `app/repositories/catalog_listings.py`

Главный repository для listings.

Отвечает за:

- чтение текущих объявлений provider-а;
- lookup по external_id;
- insert listing;
- update listing;
- deactivate listing;
- upsert listing attributes;
- image insert/deactivate helpers;
- поддержку `sync_listing_map`, если таблица появится;
- fallback lookup через EAV `external_id`.

Важная деталь: provider identity должен храниться в `sync_listing_map`. Catalog attribute `source` не является provider marker, поэтому provider нельзя писать в EAV `source`.

### `app/repositories/catalog_references.py`

Resolver catalog references.

Отвечает за:

- найти attribute id по slug;
- найти option по `attribute_slug + old_mysql_id`;
- найти option по value/label;
- учитывать parent option, если нужно;
- кешировать lookup-и;
- логировать unresolved references.

### `app/repositories/catalog_images.py`

Repository/helper для images.

Отвечает за:

- чтение images listing-а;
- подготовку image SQL операций;
- deactivation missing images.

## `app/services/` - бизнес-оркестрация

### `app/services/__init__.py`

Package marker.

### `app/services/sync_service.py`

Главный orchestrator sync-процесса.

Делает:

1. выбирает provider adapter;
2. скачивает provider records;
3. получает `LegacyAd`;
4. маппит в `CatalogListingPayload`;
5. читает текущие rows из catalog DB;
6. вызывает diff;
7. в dry-run печатает planned changes;
8. в write mode вызывает repository write methods;
9. вызывает verification, если включен `--verify`;
10. возвращает `SyncResult`.

Если нужно понять весь flow, начинать нужно с этого файла.

### `app/services/diff_service.py`

Сравнивает current DB state и новый payload.

Решает:

- insert;
- update;
- unchanged;
- deactivate;
- image_insert;
- image_deactivate.

Не должен сравнивать volatile поля вроде `updated_at`.

### `app/services/verification_service.py`

Проверка после real write.

Re-read affected listings и проверяет:

- listing существует;
- external_id сохранен;
- user_id/category_id корректны;
- title/description/price/currency/status совпадают;
- attributes сохранены;
- images сохранены/деактивированы;
- deactivate status корректный.

Если verification failed, команда должна возвращать ошибку.

## `app/utils/` - общие утилиты

### `app/utils/__init__.py`

Package marker.

### `app/utils/logging.py`

Настройка стандартного logging.

### `app/utils/normalization.py`

Нормализация строк, external_id, provider values.

### `app/utils/hashing.py`

Stable hash для image URL и других deterministic keys.

### `app/utils/http.py`

HTTP helpers для скачивания feeds/pages.

### `app/utils/slug.py`

Генерация slug для listing, если schema требует slug.

## `app/models/` и `app/sync/`

### `app/models/__init__.py`

Пока package marker. Может использоваться позже, если появятся отдельные domain models.

### `app/sync/__init__.py`

Пока package marker. Основная sync-логика сейчас находится в `app/services/`.

## `tests/` - тесты

Тесты можно запускать без новой БД. Они используют fixtures и mocks.

### `tests/fixtures/autoland.csv`

CSV fixture для Autoland parser tests.

### `tests/test_autoland_provider.py`

Проверяет Autoland:

- cp1251 CSV parsing;
- grouping;
- condition rule;
- image splitting;
- mapping в listing payload.

### `tests/test_remaining_providers.py`

Проверяет остальные provider-ы:

- parser behavior;
- mapper behavior;
- required field skip;
- dedup/grouping;
- dry-run через mocked repository.

### `tests/test_mapping.py`

Проверяет mapping:

- currency;
- type_id -> category_id;
- basic payload mapping.

### `tests/test_diff_service.py`

Проверяет diff logic:

- insert;
- update;
- unchanged;
- deactivate;
- image changes.

### `tests/test_catalog_references.py`

Проверяет reference resolver с mocked DB.

### `tests/test_repository_sql.py`

Проверяет SQL-related поведение repository без real production write.

### `tests/test_repository_write_core.py`

Проверяет core write methods на controlled test setup/mocks.

### `tests/test_sync_service_autoland.py`

Проверяет dry-run sync flow для Autoland через mocked repository.

### `tests/test_verification_service.py`

Проверяет verification logic.

### `tests/test_write_safety.py`

Проверяет safety flags:

- real write заблокирован по умолчанию;
- пароль не печатается;
- запись разрешается только при правильной комбинации flags.

### `tests/test_hashing.py`

Проверяет stable hashing.

## `docs/`

Короткая документация внутри нового проекта.

### `docs/README.md`

Дополнительная внутренняя справка по проекту.

## `docs_from_php/`

Документы, перенесенные из legacy audit. Это reference, а не runtime-код.

Самые важные файлы:

- `legacy-audit.md` - аудит старого PHP-проекта;
- `legacy-sync-models.md` - практические legacy models/runtime structures;
- `legacy-sync-flow.md` - старый flow PHP sync;
- `field-mapping-old-runtime.md` - mapping provider fields -> BaseSync FIELD_*;
- `migration-plan.md` - общий план переноса;
- `new-db-assumptions.md` - предположения по новой DB;
- `new-db-open-questions.md` - вопросы по новой DB;
- `db-readonly-inspection.md` - результаты read-only осмотра новой DB;
- `final-open-questions.md` - что еще надо подтвердить перед writes;
- `manual-db-verification.md` - SQL для ручной проверки;
- `recommended-db-migrations.sql` - рекомендуемая миграция `sync_listing_map`, не применять автоматически;
- `provider-coverage.md` - покрытие provider-ов;
- `php-to-python-replacement-map.md` - какие PHP commands чем заменены;
- `provider-*.md` - описание каждого provider-а.

## Как запустить проверки без БД

```bash
cd /.../mashina_sync_python
source .venv/bin/activate

python -m pytest -q
ruff check .
ruff format --check .
python -m app.cli list-providers
```

Эти команды проверяют код, provider parsing, mapping, diff, safety и CLI registry без подключения к catalog DB.

## Как проверить с БД, но без записи

В `.env` нужно указать минимум:

```env
CATALOG_DATABASE_URL=postgresql+psycopg://user:password@host:port/dbname
SYNC_TARGET=catalog
SYNC_DRY_RUN=1
SYNC_ALLOW_CATALOG_WRITES=0
SYNC_CATALOG_USER_ID=123
SYNC_CATALOG_PHONES=+996XXXXXXXXX
```

Проверки:

```bash
python -m app.cli healthcheck
python -m app.cli inspect-db
python -m app.cli sync --provider autoland --dry-run --limit 10
python -m app.cli sync-all --dry-run --limit 10
```

Dry-run не пишет в DB.

## Как включается real write

Real write заблокирован по умолчанию.

Для записи нужны все условия:

```env
SYNC_TARGET=catalog
SYNC_DRY_RUN=0
SYNC_ALLOW_CATALOG_WRITES=1
```

И CLI должен быть вызван без dry-run:

```bash
python -m app.cli sync --provider autoland --limit 10 --verify --no-dry-run
```

Перед массовой записью обязательно делать provider-by-provider dry-run и limited write.

## Минимальный `.env` для валидного dry-run

```env
APP_ENV=local

CATALOG_DATABASE_URL=postgresql+psycopg://user:password@host:port/dbname

SYNC_TARGET=catalog
SYNC_DRY_RUN=1
SYNC_ALLOW_CATALOG_WRITES=0

SYNC_CATALOG_USER_ID=123
SYNC_CATALOG_PHONES=+996XXXXXXXXX

SYNC_CATALOG_DEFAULT_STATUS=active
SYNC_CATALOG_INACTIVE_STATUS=inactive
SYNC_CATALOG_IMAGE_STATUS=1
SYNC_CATALOG_IMAGE_INACTIVE_STATUS=0

SYNC_BATCH_SIZE=100
SYNC_HTTP_TIMEOUT=30
SYNC_LOG_LEVEL=INFO
```

Если у provider-ов разные владельцы в catalog:

```env
SYNC_CATALOG_USER_ID_AUTOLAND=123
SYNC_CATALOG_PHONES_AUTOLAND=+996XXXXXXXXX

SYNC_CATALOG_USER_ID_TOYOTA=124
SYNC_CATALOG_PHONES_TOYOTA=+996YYYYYYYYY
```

## Что нужно решить перед production write

Главный нерешенный вопрос: provider identity.

В новой production DB нужно иметь таблицу `sync_listing_map`, потому что attribute `source` не является provider marker. Именно эта таблица надежно связывает:

```text
provider + user_id + category_id + external_id -> listing_id
```

без отдельной таблицы сложно.

Рекомендуемое решение описано в:

```text
docs_from_php/recommended-db-migrations.sql
```

Пока это не применено/не подтверждено на целевой DB, безопасно делать:

- tests;
- healthcheck;
- inspect-db;
- dry-run;
- limited verification planning.

Широкий real write/deactivate лучше не включать.

## Куда смотреть для изменений

### Добавить нового provider-а

1. Создать файл в `app/providers/<provider>.py`.
2. Унаследоваться от base adapter.
3. Вернуть список `LegacyAd`.
4. Добавить provider в `app/config/providers.py`.
5. Добавить env-поля в `app/config/settings.py`, если нужны URLs/phones/user ids.
6. Добавить тесты в `tests/`.
7. Обновить docs.

### Изменить mapping старого поля в новую DB

Смотреть:

- `app/config/catalog_mapping.py`;
- `app/mappers/listing_mapper.py`;
- `app/mappers/attribute_mapper.py`.

### Изменить работу с images

Смотреть:

- `app/mappers/image_mapper.py`;
- `app/repositories/catalog_images.py`;
- `app/repositories/catalog_listings.py`.

### Изменить SQL/write logic

Смотреть:

- `app/repositories/catalog_listings.py`;
- `app/repositories/catalog_references.py`;
- `app/db/safety.py`.

### Изменить общий sync flow

Смотреть:

- `app/services/sync_service.py`;
- `app/services/diff_service.py`;
- `app/services/verification_service.py`.

### Изменить CLI

Смотреть:

- `app/cli/commands.py`.

### Изменить env/config

Смотреть:

- `app/config/settings.py`;
- `.env.example`;
- `README.md`.

## Текущий статус проекта

На момент последней проверки:

```text
pytest: 57 passed
ruff check: passed
ruff format --check: passed
list-providers: works
```

Проект готов для dry-run проверки с catalog DB.

Для production write нужно сначала подтвердить provider identity strategy, желательно через `sync_listing_map`.
