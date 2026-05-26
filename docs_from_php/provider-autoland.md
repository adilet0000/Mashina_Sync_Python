# Provider: Autoland

## Scope

Autoland is the first provider implemented end-to-end in the Python rewrite.

It replaces the legacy PHP flow from:

- `src/Command/AutolandSyncCommand.php`
- `src/Service/Sync/AutolandSync.php`

The Python implementation lives in:

- `python_app/app/providers/autoland.py`
- `python_app/app/services/sync_service.py`
- `python_app/app/mappers/listing_mapper.py`
- `python_app/app/repositories/catalog_listings.py`

## Feed

Default feed URL:

```text
https://baz-on.ru/export/c2095/9d8bf/autolandkg-parts.csv
```

It can be overridden locally:

```env
SYNC_PROVIDER_AUTOLAND_FEED_URL=
```

Format:

- CSV
- delimiter `;`
- encoding `Windows-1251` / `cp1251`

## Unique Key

Autoland uses provider article ids from `Артикул`.

Legacy grouping is preserved:

```text
group key = Наименование + Марка + Модель
```

If a group has multiple rows:

```text
external_id = comma-joined article ids
```

Example:

```text
A-1,A-2,A-3
```

Catalog idempotency key:

```text
source + user_id + category_id + external_id
```

For Autoland:

```text
source = autoland
category_id = 35
legacy type_id = 30
```

## Mapping

| CSV field | LegacyAd field | Catalog target |
|---|---|---|
| `Артикул` | `external_id` | `listing_attributes.external_id` |
| `Марка` | `make` | `listing_attributes.make` option lookup by value/label |
| `Модель` | `model` | `listing_attributes.model` option lookup by value/label |
| `Наименование` | `name` | `listings.title` |
| `Комментарий` or `Наименование` | `description` | `listings.description` |
| `Фото` | `images` | `images.external_url`, `images.hash`, `images.priority` |
| `Новый/БУ` + `Наименование` | `condition` | `listing_attributes.condition` |
| `Цена` | `price` | `listings.price` |
| fixed `1` | `currency` | `listings.currency = KGS` |
| fixed `30` | `type_id` | `listings.category_id = 35` |

Condition rule:

```text
condition = 2 only when:
Новый/БУ == Новый and Наименование == Товары из Дордоя
otherwise condition = 1
```

Phones are read from:

```env
SYNC_CATALOG_PHONES_AUTOLAND
```

Fallback:

```env
SYNC_CATALOG_PHONES
```

Catalog user id is read from:

```env
SYNC_CATALOG_USER_ID_AUTOLAND
```

Fallback:

```env
SYNC_CATALOG_USER_ID
```

## Known Differences

- The legacy PHP code mapped `Марка` and `Модель` through old `SyncData` maps and
  custom arrays.
- The Python rewrite passes make/model values to the catalog reference resolver, which resolves by
  `attribute_options.value` or `attribute_options.label`.
- For grouped rows, Python keeps unique images from all rows in the group. Legacy PHP built the main
  payload from the first row and grouped description/external ids.
- Price is mapped into `listings.price`, but legacy comparison did not use price for Autoland.

## Commands

Dry-run:

```bash
cd python_app
python -m app.cli sync --provider autoland --dry-run
```

Limited dry-run:

```bash
python -m app.cli sync --provider autoland --limit 10 --dry-run
```

Verification mode after writes are explicitly enabled:

```bash
python -m app.cli sync --provider autoland --limit 10 --verify
```

Real writes remain blocked unless all safety flags are enabled:

```env
SYNC_TARGET=catalog
SYNC_DRY_RUN=0
SYNC_ALLOW_CATALOG_WRITES=1
```

Real write command after dry-run review:

```bash
cd python_app
SYNC_DRY_RUN=0 SYNC_ALLOW_CATALOG_WRITES=1 \
python -m app.cli sync --provider autoland --limit 10 --verify --no-dry-run
```

The write path inserts or updates `listings`, upserts `listing_attributes`, inserts or updates
`images`, deactivates images missing from the current feed, and deactivates catalog listings whose
Autoland `external_id` is absent from the current feed.

## Tests

```bash
cd python_app
pytest tests/test_autoland_provider.py
pytest tests/test_sync_service_autoland.py
```
