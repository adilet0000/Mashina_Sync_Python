# Mashina.kg Catalog Sync Python

## Project Purpose

This is the Python replacement for the legacy Symfony/PHP catalog ads sync scripts. It reads
provider feeds/pages/API responses, normalizes them into `LegacyAd` DTOs, maps them into catalog
payloads, compares them with existing rows in the new catalog DB, and plans insert/update/deactivate
operations.

The project is intentionally backend/data-sync only.

## What This Replaces

The Python providers replace these legacy commands:

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

Drive community parsing is not part of this rewrite.

Detailed replacement map:

```text
../docs/php-to-python-replacement-map.md
../docs/provider-coverage.md
```

## What Is Not Migrated

This is not an old DB to new DB migration. The old database is not used as business-data source.
The old internal API is not used as the final write target.

New flow:

```text
Provider feed/API/page
-> Python provider adapter/parser
-> LegacyAd DTO
-> CatalogListingPayload
-> read current rows from new catalog DB
-> diff by source + user_id + category_id + external_id
-> guarded insert/update/deactivate
-> optional verification
```

## Architecture

```text
app/
  cli/              Typer CLI entrypoints
  config/           env settings, provider registry, catalog mapping
  db/               SQLAlchemy engine/session, healthcheck, reflection, safety helpers
  dto/              LegacyAd, CatalogListingPayload, SyncResult
  mappers/          LegacyAd -> catalog listing/attribute/image payloads
  providers/        provider adapters and parsing helpers
  repositories/     catalog DB reads/writes and reference resolution
  services/         sync orchestration, diffing, verification
  utils/            logging, hashing, HTTP, normalization, slug helpers
tests/              unit tests and provider fixture tests
```

Write path:

```text
ProviderAdapter.fetch_ads()
-> SyncService.sync_records()
-> ListingMapper.to_catalog_payload()
-> CatalogListingsRepository.get_current_by_provider()
-> DiffService.diff()
-> CatalogListingsRepository insert/update/deactivate methods
-> VerificationService.verify_sync() when --verify is used in write mode
```

## Environment Variables

Required for real catalog use:

```env
CATALOG_DATABASE_URL=postgresql+psycopg://user:password@host:5432/database
SYNC_CATALOG_USER_ID=77
SYNC_CATALOG_PHONES=+996555000111
```

Safety defaults:

```env
SYNC_TARGET=catalog
SYNC_DRY_RUN=1
SYNC_ALLOW_CATALOG_WRITES=0
SYNC_CATALOG_DEFAULT_STATUS=active
SYNC_CATALOG_INACTIVE_STATUS=inactive
SYNC_CATALOG_IMAGE_STATUS=1
SYNC_CATALOG_IMAGE_INACTIVE_STATUS=0
SYNC_BATCH_SIZE=100
SYNC_HTTP_TIMEOUT=30
SYNC_LOG_LEVEL=INFO
```

Provider-specific user IDs and phones are supported:

```env
SYNC_CATALOG_USER_ID_AUTOLAND=
SYNC_CATALOG_PHONES_AUTOLAND=
```

Provider feed/base URL overrides are available in `.env.example`, for example:

```env
SYNC_PROVIDER_AUTOLAND_FEED_URL=
SYNC_PROVIDER_ALLMOTORS_BASE_URL=
SYNC_PROVIDER_TOYOTA_TRADEIN_CURRENCY_RATE=
```

Do not commit real credentials.

## Install

```bash
cd python_app
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Dependencies are modern Python-only packages: SQLAlchemy 2.x, Typer, pydantic-settings, httpx,
BeautifulSoup, defusedxml, pytest, and ruff.

No yarn, npm, webpack, gulp, bower, or composer install is required.

## Healthcheck

Read-only DB connectivity check:

```bash
python -m app.cli healthcheck
```

Read-only required table inspection:

```bash
python -m app.cli inspect-db
```

Expected catalog tables:

- `listings`
- `listing_attributes`
- `attributes`
- `attribute_options`
- `images`
- `listing_counters`
- `listing_promotions`

## Dry-run

Dry-run is enabled by default through `SYNC_DRY_RUN=1`.

```bash
python -m app.cli sync --provider autoland --dry-run --limit 10
python -m app.cli sync --provider autohub --dry-run --limit 10
python -m app.cli sync-all --dry-run --limit 10
```

Dry-run does not write to DB. It prints:

- provider name
- read/valid/skipped counts
- would insert/update/deactivate counts
- would insert/deactivate image counts
- first normalized `LegacyAd` samples
- first `CatalogListingPayload` samples
- first diff samples
- safe DB target preflight when payloads can be mapped

## Real Write

Real writes are blocked unless all conditions are true:

```env
SYNC_TARGET=catalog
SYNC_DRY_RUN=0
SYNC_ALLOW_CATALOG_WRITES=1
```

The CLI must also be called with `--no-dry-run`:

```bash
SYNC_DRY_RUN=0 SYNC_ALLOW_CATALOG_WRITES=1 \
python -m app.cli sync --provider autoland --limit 10 --verify --no-dry-run
```

Before write mode, the sync logs a preflight summary with host, database name, username, provider,
user id, category ids, mode, and write flag. Passwords are never printed.

## Verify Mode

`--verify` is meaningful after real writes. It re-reads affected rows and checks:

- listing exists by provider/source + user_id + category_id + external_id
- `external_id` and `source` attributes exist
- user id and category id
- title, description, price, currency, status
- listing attributes presence and scalar values
- image URL, hash, priority, status, and user id where available
- deactivated listing status

If verification reports mismatches, the CLI returns non-zero.

Dry-run with `--verify` is allowed, but it does not re-read written rows because no write happened.

## Provider List

```bash
python -m app.cli list-providers
```

Implemented providers:

- `allmotors`
- `autohub`
- `autoland`
- `autoshina`
- `avtoinstall`
- `banzaimotors`
- `bavaria`
- `detalkg`
- `kia`
- `lexus`
- `okayamaomsk`
- `shinabar`
- `shredder`
- `toyota`
- `toyota_tradein`

## Sync All

Preview all providers:

```bash
python -m app.cli sync-all --dry-run --limit 10
```

Write all providers only after provider-by-provider dry-runs are approved:

```bash
SYNC_DRY_RUN=0 SYNC_ALLOW_CATALOG_WRITES=1 \
python -m app.cli sync-all --verify --no-dry-run
```

## Manual DB Verification

Manual SQL examples are in:

```text
../docs/manual-db-verification.md
```

It includes queries for:

- listing by provider + external id
- listing attributes
- images
- inactive/deactivated listings
- duplicate external ids
- listings without external id
- images without external URL/hash

## Troubleshooting

`CATALOG_DATABASE_URL is not configured`

: Set `CATALOG_DATABASE_URL` in `.env`.

`catalog writes are disabled`

: Keep this in dry-run mode, or explicitly set `SYNC_DRY_RUN=0` and
  `SYNC_ALLOW_CATALOG_WRITES=1` only after curator approval.

Provider fetch fails

: Confirm the provider feed URL or set the matching `SYNC_PROVIDER_*_FEED_URL` override.
  Some legacy URLs may be stale.

Missing catalog user id

: Set `SYNC_CATALOG_USER_ID` or `SYNC_CATALOG_USER_ID_<PROVIDER>`.

Unresolved catalog references

: Check `attributes` and `attribute_options` in the new catalog DB. The sync logs unresolved
  references and continues unless the required `external_id` attribute is missing.

HTML provider returns no records

: Check if site markup changed for Allmotors, Autoshina, or DetalKg tire pages. Fixture tests cover
  the legacy selector behavior, but live sites can drift.

## Safety Flags

- Dry-run is default.
- Real write requires both env flags and CLI `--no-dry-run`.
- Repository write methods independently check `SYNC_ALLOW_CATALOG_WRITES=1`.
- Old DB is not read or written.
- Old internal API is not a write target.
- Secrets are not printed by DB target logging.
- Frontend and old PHP runtime are not required for this Python sync.

## Checks

```bash
pytest
ruff check .
ruff format --check .
```
