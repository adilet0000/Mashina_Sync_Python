# New DB Write Plan For Python Sync

This plan describes the Python rewrite target behavior. It is not an old DB migration. Provider feeds/API/pages remain the source of truth; old internal API is only a reference for legacy behavior.

```text
Provider feed/API/page
  -> Python provider adapter/parser
  -> normalized internal DTO
  -> compare with current records in NEW catalog DB
  -> insert/update/disable in NEW catalog DB
  -> log, dry-run, verify
```

## Scope Before Coding

Old PHP scripts to replace:

| Legacy command | Legacy provider/service | Python provider key |
|---|---|---|
| `app:sync-autohub` | `AutohubSync` | `autohub` |
| `app:sync-autoland` | `AutolandSync` | `autoland` |
| `app:sync-shredder` | `ShredderSync` | `shredder` |
| `app:sync-okayamaomsk` | `OkayamaomskSync` | `okayamaomsk` |
| `app:sync-banzaimotors` | `BanzaimotorsSync` | `banzaimotors` |
| `app:sync-bavaria` | `BavariaSync` | `bavaria` |
| `app:sync-shinabar` | `ShinabarSync` | `shinabar` |
| `app:sync-avtoinstall` | `AvtoinstallSync` | `avtoinstall` |
| `app:sync-allmotors` | `AllmotorsSync` | `allmotors` |
| `app:sync-autoshina` | `AutoshinaSync` | `autoshina` |
| `app:sync-detalkg` | `DetalKgSync` | `detalkg` |
| `app:sync-toyota` | `AutocrmSync` | `toyota` |
| `app:sync-toyota-tradein` | `AutocrmSync` | `toyota_tradein` |
| `app:sync-lexus` | `AutocrmSync` | `lexus` |
| `app:sync-kia` | `AutocrmSync` | `kia` |

Python files expected during implementation:

```text
python_app/
  app/
    cli/main.py
    config/settings.py
    db/session.py
    db/models.py
    providers/base.py
    providers/<provider_name>.py
    sync/normalizer.py
    sync/diff.py
    sync/service.py
    sync/result.py
    repositories/ads_repository.py
    mappers/ad_mapper.py
    verification/db_verifier.py
    utils/logging.py
  tests/
```

New DB write targets:

- `listings`
- `listing_attributes`
- `images`
- optionally a new `sync_listing_map` table or equivalent unique sync index, if the catalog service allows schema changes

Assumptions used:

- The new DB is the catalog-service PostgreSQL schema documented in `docs/new-db-assumptions.md`.
- Known catalog mapping comes from the prior PHP catalog dry-run prototype: `CatalogSyncConfig`, `CatalogListingPayloadMapper`, `CatalogListingRepository`, `CatalogListingWriter`.
- `listings.id` is a generated primary key.
- `listing_attributes` supports `ON CONFLICT (listing_id, attribute_id)`.
- `attribute_options.old_mysql_id` exists for many old reference ids.
- No old DB ads data is used.

Information still missing:

- Confirmed DDL, exact nullability, indexes, enum/check constraints, status values, and whether this project may add a sync mapping table or index.
- Confirmed tire/wheel attributes in catalog schema.
- Confirmed source/provider identity storage in the new DB.
- Confirmed image lifecycle columns such as `moderated`, `object_name`, `expires_at`, if required by actual schema.

Open questions are tracked separately in `docs/new-db-open-questions.md`.

## Read-Only Inspection Correction

Read-only inspection of `mashina_catalog_service` on 2026-05-26 changed one important
assumption:

- `sync_listing_map` does not exist.
- Catalog attribute `source` exists, but it is numeric (`value_number=1/2`) and has no
  provider-name options.
- Therefore `attributes.slug='source'` must not be used to store provider keys such as
  `autoland`, `toyota`, or `kia`.

Production-safe provider idempotency still requires `sync_listing_map` or another
approved provider identity table/column. Without that, fallback matching is limited to
`user_id + category_id + external_id`, which cannot prove provider ownership if providers
share the same catalog user/category.

## Target Tables

The table details below are based on currently available project context, not an authoritative migration file.

| Table | Purpose | Required columns for sync | Nullable/optional columns used by sync | Unique constraints / indexes relevant to sync | Relations |
|---|---|---|---|---|---|
| `listings` | Main ad/listing row | `id`, `category_id`, `user_id`, `title`, `description`, `status`, `created_at`, `updated_at` | `price`, `currency`, `slug`, `upped_at` | PK `id`; recommended index `(user_id, category_id, status)`; no confirmed provider unique key | `category_id -> categories.id`, `user_id -> users.id` or auth-service user table |
| `listing_attributes` | EAV attributes for listing details and legacy ids | `listing_id`, `attribute_id` | `attribute_options_id`, `value_text`, `value_number`, `value_boolean`, `value_date`, `value_json`, `created_at`, `updated_at` | Assumed unique `(listing_id, attribute_id)`; recommended index `(attribute_id, value_text)` for `external_id` lookup | `listing_id -> listings.id`, `attribute_id -> attributes.id`, `attribute_options_id -> attribute_options.id` |
| `images` | Listing media/images | `id`, `listing_id`, `status`, `priority`, `created_at` | `hash`, `external_url`, `user_id`, `is_blurred` | PK `id`; recommended unique/index `(listing_id, external_url)` for active images; index `(listing_id, status)` | `listing_id -> listings.id`, `user_id -> users.id` |
| `attributes` | Attribute dictionary | `id`, `slug` | `data_type`, `input_type` | Unique `slug` is assumed/needed | Referenced by `listing_attributes.attribute_id` |
| `attribute_options` | Attribute option dictionary | `id`, `attribute_id`, `value` | `label`, `parent_option_id`, `old_mysql_id`, `is_active` | Recommended index `(attribute_id, old_mysql_id)` and `(attribute_id, value, parent_option_id)` | Referenced by `listing_attributes.attribute_options_id`; parent chain by `parent_option_id` |
| `categories` | Category dictionary | `id`, `slug` | parent/category metadata | Unique `slug` is assumed/needed | Referenced by `listings.category_id` |
| `listing_counters` | Counters/views/favorites | none in initial sync | all | Not written initially | May be created by catalog service defaults/triggers |
| `listing_promotions` | Promotion state | none in initial sync | all | Not written initially | Existing promotions must not be overwritten by sync |
| `sync_listing_map` | Proposed reliable provider identity table | `provider`, `external_id`, `listing_id`, `category_id`, `user_id`, `last_seen_at`, `created_at`, `updated_at` | `source_hash`, `last_payload_json`, `last_error` | Recommended unique `(provider, external_id)` or `(provider, category_id, external_id)`; index `listing_id` | `listing_id -> listings.id`; optional but strongly recommended |

If `sync_listing_map` cannot be added, the fallback identity is:

```text
listings.user_id + listings.category_id + listing_attributes[external_id].value_text
```

That fallback is workable only when the provider owns the configured user/category scope. It
does not fully prevent duplicates under concurrent runs and cannot safely identify rows by
provider if multiple providers share one user/category. Do not use `listing_attributes.source`
as a provider marker in this DB.

## Old Runtime To New DB Mapping

| BaseSync FIELD_* / normalized field | New DB table | New DB column | Transformation | Required | Default/Fallback | Notes |
|---|---|---|---|---|---|---|
| `provider` | `sync_listing_map` or app-level identity | `provider` | Python provider key such as `autohub`, `toyota` | Yes | CLI/provider config | If no table exists, used only in repository filters/logs and optionally namespaced into `external_id`. |
| `FIELD_ID` | `listings` | `id` | DB-generated on insert; read for updates | Existing only | None | Never supplied by provider. |
| `FIELD_TYPE_ID` | `listings` | `category_id` | Old type map: `1->1`, `30->35`, `31->24`, `32->37`, `33->33`, `36->26` | Yes | Skip row if unknown | `30->35 parts_supplies` needs confirmation. |
| `FIELD_NAME` / normalized `title` | `listings` | `title` | Trim string | Yes | `Imported listing <external_id>` | Provider-specific preserve policy may protect manual titles if requested later. |
| `FIELD_DESCRIPTION` | `listings` | `description` | Trim/string cleanup from provider | Yes | Fallback to title | Toyota legacy preserved description on update; keep as provider policy until confirmed. |
| `FIELD_PRICE` | `listings` | `price` | Parse numeric; provider-specific markup/conversion before mapping | No | `NULL` or provider default `0` when legacy did that | For car listings also write attr `price` if attribute exists. |
| `FIELD_CURRENCY` | `listings` | `currency` | `1 -> KGS`, `2 -> USD`; strings normalized uppercase | No | `KGS` | Unknown value logs warning and falls back to `KGS`. |
| `FIELD_MODERATED` / normalized active flag | `listings` | `status` | `1` means default active status; non-active -> draft | Yes | `active` for returned valid provider ads | Exact allowed statuses must be confirmed. |
| removed/missing provider ad | `listings` | `status`, `updated_at` | Set status to inactive/deleted configured value | Yes for removed current rows | `inactive` assumption | Soft disable only; no hard delete in initial rewrite. |
| `created_at` | `listings` | `created_at` | DB/server timestamp | Yes on insert | `now()` | Never changed after insert. |
| `updated_at` | `listings` | `updated_at` | DB/server timestamp when listing or attrs/images changed | Yes | `now()` | Avoid updates when payload has no diff. |
| `synced_at` / `last_seen_at` | `sync_listing_map` or optional attr | `last_seen_at` | Set every time provider ad is seen | Yes if map table exists | `now()` | If no map table exists, consider adding `synced_at` attribute or rely on run-local seen set. |
| `FIELD_EXTERNAL_ID` | `listing_attributes` and `sync_listing_map` | `value_text` for attr `external_id`; `external_id` in map table | Trim string, preserve grouped comma ids from legacy grouping | Yes | Skip invalid/missing | Primary provider ad key. Must not be empty. |
| `FIELD_REGION` | `listing_attributes` | `attribute_options_id` for attr `region` | Lookup option by `old_mysql_id` | No | Legacy default `1` if provider normalizer includes it | Parent not required. |
| `FIELD_TOWN` | `listing_attributes` | `attribute_options_id` for attr `city` | Lookup option by `old_mysql_id`; parent should be resolved from region | No | Legacy default `2` if present | Needs city option confirmation. |
| `FIELD_PHONE` | `listing_attributes` | `value_text` for attr `phone` | Join list to string or keep configured provider phones | No | Provider/user config | Old API phones are replaced by Python config/new owner account data. |
| `FIELD_CONDITION` | `listing_attributes` | `attribute_options_id` for attr `condition` | Lookup by option value or old id depending catalog data | No | Provider default from normalizer | Exact option values need confirmation. |
| `FIELD_COMMENT_ALLOWED` | `listing_attributes` | `attribute_options_id` for attr `comment_permission` | Lookup by option value | No | Legacy default `3` | Can be omitted if attribute missing. |
| `FIELD_FEATURED_OPTION` | `listing_attributes` | `attribute_options_id` for attr `featured_option` | Lookup by option value/old id | No | Legacy default `1` | AutoCRM availability maps here. |
| `FIELD_MAKE` | `listing_attributes` | `attribute_options_id` for attr `make` | Lookup `attribute_options.old_mysql_id` | Conditional | Omit for parts if unresolved; cars should skip if unresolved | Parent not required. |
| `FIELD_MODEL` | `listing_attributes` | `attribute_options_id` for attr `model` | Lookup `old_mysql_id`, preferably with parent make | Conditional | Omit for parts if unresolved; cars should skip if unresolved | Parent chain should be enforced. |
| `FIELD_YEAR` | `listing_attributes` | `value_number` for attr `year` | Integer/numeric | Cars yes | Skip car if missing | Validate plausible year range before write. |
| `FIELD_BODY` | `listing_attributes` | `attribute_options_id` for attr `body_type` | Lookup by `old_mysql_id`, parent model when possible | Cars yes | Skip car if unresolved | AutoCRM may remap by door count. |
| `FIELD_GENERATION` | `listing_attributes` | `attribute_options_id` for attr `generation` | Lookup by `old_mysql_id`, parent body/model chain | Cars yes | Skip car if unresolved | Parts use generation only in text, not this attr. |
| `FIELD_FUEL` | `listing_attributes` | `attribute_options_id` for attr `fuel_type` | Lookup by normalized value/parent chain or old id if available | Cars yes | Provider default `Бензин` before mapping | Resolver must handle missing `old_mysql_id`. |
| `FIELD_TRANSMISSION` | `listing_attributes` | `attribute_options_id` for attr `drive_type` | Lookup by normalized value/parent chain | Cars yes | Provider fallback `Передний` before mapping | Name mismatch risk. |
| `FIELD_GEAR_BOX` | `listing_attributes` | `attribute_options_id` for attr `gearbox` | Lookup by normalized value/parent chain | Cars yes | Provider inference before mapping | Name mismatch risk. |
| `FIELD_MODIFICATION` | `listing_attributes` | `attribute_options_id` for attr `modification` | Lookup by `old_mysql_id` with parent chain | Cars yes | Skip if unresolved | Critical for AutoCRM. |
| `FIELD_COMPLECTATION` | `listing_attributes` | `value_text` for attr `complectation_text` | Direct text | No | Omit if empty | Kia duplicate logic uses it. |
| `FIELD_STEERING_WHEEL` | `listing_attributes` | `attribute_options_id` for attr `steering_wheel` | Lookup by normalized value/old id | Cars yes | Skip if unresolved | AutoCRM required. |
| `FIELD_COLOR` | `listing_attributes` | `attribute_options_id` for attr `color` | Lookup by normalized value/old id | Cars yes | AutoCRM default `Серебряный` before mapping | Option ids must be confirmed. |
| `FIELD_MILEAGE` | `listing_attributes` | `value_json` for attr `mileage` | Store as `{"raw": value}` until final format confirmed | No | Omit if empty | Open question: expected JSON format. |
| `FIELD_CUSTOMS` | `listing_attributes` | `attribute_options_id` or boolean for attr `is_customs_cleared` | Current prototype treats as option lookup; may need boolean | No | AutoCRM derives from `featured_option` | Needs schema/attribute type confirmation. |
| `FIELD_VINCODE` | `listing_attributes` | `value_text` for attr `vincode` | Direct VIN | Cars yes | Same as `external_id` for AutoCRM | Validate non-empty. |
| `FIELD_OLD_PRICE` | `listing_attributes` | `value_number` for attr `old_price` | Numeric or null | No | Null if no special price | Avtoinstall/ToyotaTradein. |
| `FIELD_IMAGES` / normalized images | `images` | `external_url`, `priority`, `hash`, `status`, `user_id`, `created_at` | Normalize `index|url` to priority/url; hash `sha1(url)` for preview | No but most providers require images before normalization | Empty images should not wipe existing unless provider policy says full replacement | Prefer diff by `external_url`, not wholesale replace. |
| `FIELD_TIRE_WIDTH` | TBD | TBD | Current schema has no confirmed attr | Tires yes | Store in description only until schema confirmed | Do not silently invent attribute ids. |
| `FIELD_TIRE_HEIGHT` | TBD | TBD | Current schema has no confirmed attr | Tires yes | Store in description only until schema confirmed | Open question. |
| `FIELD_TIRE_SIZE` | TBD | TBD | Current schema has no confirmed attr | Tires yes | Store in description only until schema confirmed | Open question. |
| `FIELD_TIRE_TYPE` | TBD | TBD | Current schema has no confirmed attr | Tires yes | Store in description only until schema confirmed | Open question. |
| `FIELD_WHEEL_TYPE` | TBD | TBD | Current schema has no confirmed attr | Wheels conditional | Store in description only until schema confirmed | Open question. |
| `FIELD_WHEEL_SIZE` | TBD | TBD | Current schema has no confirmed attr | Wheels conditional | Store in description only until schema confirmed | Open question. |
| `FIELD_WHEEL_PCD` | TBD | TBD | Current schema has no confirmed attr | Wheels conditional | Store in description only until schema confirmed | Open question. |

## Provider Identity Strategy

### Provider/source identifier

Use a stable lowercase provider key:

```text
autohub, autoland, shredder, okayamaomsk, banzaimotors, bavaria,
shinabar, avtoinstall, allmotors, autoshina, detalkg,
toyota, toyota_tradein, lexus, kia
```

This provider key must be part of sync identity. Provider-specific user ids may also be configured, but `user_id` alone is not a safe provider identity if several providers share the same catalog user.

### Provider ad external ID

Use normalized `external_id` from the provider:

- AutoCRM: VIN.
- Baz-on CSV feeds: `Артикул`.
- HTML crawlers: product id/slug.
- Detal tires: parsed article from detail page.
- Grouped legacy parts: comma-joined article ids, matching legacy behavior.

Invalid external ids:

- Empty/null external id: skip record and log `invalid_external_id`.
- Non-scalar external id: convert only if deterministic; otherwise skip.
- External id longer than target column constraints: skip until max length is confirmed, or store full value in mapping table with `text`.

### Storage options

Preferred production-safe storage:

```text
sync_listing_map(provider, external_id, category_id, user_id, listing_id)
```

Recommended unique constraint:

```text
UNIQUE (provider, external_id)
```

If the same provider can legitimately emit the same external id for different categories, use:

```text
UNIQUE (provider, category_id, external_id)
```

Fallback without schema changes:

```text
listings.user_id + listings.category_id + listing_attributes.external_id
```

Fallback risk: no confirmed provider marker or unique constraint prevents duplicates. Mitigations:

- run one provider sync at a time;
- use PostgreSQL advisory lock per provider;
- pre-load current rows before writes;
- require a dedicated `user_id` per provider/category where possible;
- after write, verify duplicate external ids and fail the run if found.

If provider ad arrives again:

- find existing listing by provider identity;
- compare normalized mapped payload with DB state;
- update only changed fields;
- set `last_seen_at/synced_at` if such storage exists;
- keep `created_at` and stable ownership fields unchanged.

## Upsert Strategy

### New ad

1. Validate normalized DTO.
2. Resolve category and required attributes/options.
3. Insert `listings`.
4. Insert/upsert `listing_attributes`, including `external_id`.
5. Insert active `images` rows for normalized image URLs.
6. Insert `sync_listing_map` row if table exists.
7. Return touched table counts.

### Existing ad

1. Load current listing row, attributes, and active images.
2. Build desired mapped payload.
3. Compute diff.
4. If no diff, count as `unchanged`; update only `last_seen_at/synced_at` if using sync map.
5. If changed, update only changed `listings` columns and changed attrs/images.
6. Reactivate listing if it was inactive and provider sent it again.

### Fields always updated when changed

- `listings.category_id` if provider type/category changed and category is valid.
- `listings.title`, unless provider policy says manual title should be preserved.
- `listings.description`, unless provider policy says manual description should be preserved.
- `listings.price`, `listings.currency`.
- `listings.status` for active/reactivated provider records.
- EAV attributes derived from provider fields.
- Image priority/status/url diff.
- `updated_at` only when listing/attrs/images actually changed.
- `last_seen_at/synced_at` every time the provider record is seen, if storage exists.

### Fields never overwritten by sync

- `listings.id`.
- `listings.created_at`.
- `listing_counters`.
- `listing_promotions`.
- Human moderation/review fields not explicitly owned by sync.
- `slug`, unless product confirms it should be regenerated.
- `user_id`, unless a provider ownership migration is explicitly requested.

### Fields updated only when provider value is not empty

- Optional attrs: phone, old_price, mileage, complectation, VIN for non-car categories.
- Reference attrs for parts: make/model/body/generation if provider mapping failed.
- Images: if provider normalizer returns an empty image list because images are missing, skip the record or preserve current images according to provider policy; do not wipe images accidentally.

### Provider-specific preserve policies

Legacy behavior included manual preservation:

- Toyota: preserved current description and price on update.
- Lexus: preserved current price on update.
- ToyotaTradein: preserved current price and old_price; skipped one hardcoded VIN.
- Kia: command currently exits before writes.

Python should implement preserve policies in provider config, not hidden inside the generic repository. These policies must be confirmed before enabling real writes.

### Disable behavior for missing ads

After parsing the full provider feed:

1. Build set of seen provider external ids.
2. Load active current listings for the same provider/category/user scope.
3. Any current listing not seen is scheduled for soft disable.
4. Set `listings.status` to configured inactive/deleted value and update `updated_at`.
5. Set `sync_listing_map.last_seen_at` unchanged and optionally `disabled_at=now()` if column exists.
6. Do not delete rows from `listings`, `listing_attributes`, or `images` in initial implementation.

## Comparison Strategy

### Load current ads from new DB

Preferred with mapping table:

```sql
SELECT l.*, m.provider, m.external_id, m.last_seen_at, ...
FROM sync_listing_map m
JOIN listings l ON l.id = m.listing_id
WHERE m.provider = :provider
  AND l.category_id = ANY(:category_ids)
```

Fallback without mapping table:

```sql
SELECT l.*, ext.value_text AS external_id, la.*, a.slug, ao.old_mysql_id, ao.value
FROM listings l
JOIN listing_attributes ext
  ON ext.listing_id = l.id
 AND ext.attribute_id = :external_id_attribute_id
LEFT JOIN listing_attributes la ON la.listing_id = l.id
LEFT JOIN attributes a ON a.id = la.attribute_id
LEFT JOIN attribute_options ao ON ao.id = la.attribute_options_id
WHERE l.user_id = :user_id
  AND l.category_id = ANY(:category_ids)
  AND ext.value_text IS NOT NULL
  AND ext.value_text <> ''
```

### Compare fields

Compare canonicalized mapped payloads, not raw provider rows:

- Listing scalar fields: category, title, description, price, currency, status.
- Attributes by slug: value column, resolved option id, normalized number/text/json.
- Images: active image URLs and priority.

Avoid unnecessary updates:

- Normalize whitespace and numeric types before diff.
- Treat missing optional provider field as "no update" when configured.
- Use stable ordering for images and attributes.
- If using `sync_listing_map.source_hash`, skip detailed diff when hash matches and status is already active.

### Images/media diff

Do not use the PHP prototype's wholesale image replacement as final behavior. Use diff:

- Existing active image by `external_url` remains unchanged if URL and priority match.
- New provider URL creates an `images` row.
- Existing URL with changed priority updates `priority`.
- Existing active DB URL missing from provider feed becomes inactive/deleted if provider image list is authoritative.
- Empty provider image list must not disable all images unless provider policy says the item is valid without images.

### Removed ads

Removed means:

```text
current active provider listing exists in DB
AND external_id was not seen in this successful provider run
```

Do not disable ads if provider fetch failed or parsing produced no records due to an upstream error. A zero-record provider run should be treated as failed unless the provider explicitly supports empty feeds.

### Duplicates

Within one provider run:

- Exact duplicate external id with same payload: keep one, count duplicate skipped.
- Same external id with conflicting payload: use provider-specific resolver or fail that record; do not randomly overwrite.
- Providers with legacy grouping must group before identity is finalized.

In DB:

- Preferred: unique map/index prevents duplicates.
- Fallback: verification must query duplicate `(user_id, category_id, external_id)` rows and report errors.

## Transaction Strategy

Provider/network fetch happens outside DB transactions.

Recommended write boundary:

- Batch size: 100 normalized records by default; configurable.
- One DB transaction per batch.
- Within the batch, use savepoints/nested transactions per record so one bad record can be skipped without rolling back the whole batch when safe.
- Disable operations run after successful upserts for the provider, in their own transaction.

Rollback behavior:

- Mapping/validation error for one record: skip record, log error, continue.
- Reference option not found for required car field: skip record.
- DB integrity error for one record: rollback savepoint, mark failed, continue if the transaction remains usable.
- Systemic DB error/connection failure: rollback full batch and retry.

Retry behavior:

- Provider failures: retry GET/feed requests up to 3 times with exponential backoff and jitter; if still failing, abort provider run and do not disable missing ads.
- DB transient failures: retry the failed batch up to 2 times; if still failing, abort provider run and report failed batch.
- Deterministic validation failures are not retried.

Concurrency:

- Use PostgreSQL advisory lock per provider key before write phase.
- Do not allow two runs for the same provider to write concurrently.
- Parallel runs for different providers are allowed only if identity constraints are confirmed.

## Verification Strategy

Every sync run must output:

| Metric | Meaning |
|---|---|
| `provider` | Provider key/name |
| `provider_records_read` | Raw records/pages/items read from provider |
| `normalized_records_valid` | Records that became valid normalized DTOs |
| `records_invalid_skipped` | Invalid rows/pages skipped before DB diff |
| `records_inserted` | New listings inserted |
| `records_updated` | Existing listings changed |
| `records_unchanged` | Existing listings with no diff |
| `records_disabled` | Existing listings soft-disabled because missing from provider feed |
| `records_failed` | Records that failed during mapping/write |
| `table_rows_touched` | Per-table counts for `listings`, `listing_attributes`, `images`, `sync_listing_map` |
| `warnings` | Non-fatal mapping/status/schema warnings |
| `errors` | Fatal or per-record errors |

### `--dry-run`

Must not write to DB.

Dry-run must show:

- planned inserts/updates/disables;
- table row counts that would be touched;
- sample insert payloads;
- sample update diffs;
- sample disable ids/external ids;
- warnings for unresolved optional mappings;
- fatal blockers for unresolved required mappings.

Dry-run may read from the new DB to compare current state.

### `--verify`

After real writes, re-read affected records from the new DB and verify:

- every inserted/updated provider identity can be found;
- required listing fields are saved: category, user, title, description, status;
- required `external_id` attribute exists and matches;
- unique key has no duplicates;
- `status` is active for seen records and inactive for disabled records;
- `updated_at` changed for updated/disabled records;
- `created_at` remains stable for updates;
- image URLs and priorities match desired payload;
- required attributes for cars are present.

Verification mismatches must be logged as errors and reflected in non-zero command exit code.

### `--limit N`

Limits provider records after parsing or during provider adapter iteration. Intended for safe testing:

```bash
python -m app.cli sync --provider autohub --limit 10 --dry-run
```

The command must not disable missing ads when `--limit` is used, because the run is intentionally partial.

### `--provider PROVIDER_NAME`

Runs one provider only:

```bash
python -m app.cli sync --provider autohub --dry-run
python -m app.cli sync --provider toyota --verify
```

`sync-all` should iterate configured providers and aggregate results.

### `--debug-record EXTERNAL_ID`

For one provider external id, output:

- raw provider record if available;
- full normalized DTO;
- mapped DB payload;
- DB row before update;
- planned diff;
- DB row after update when not dry-run;
- verification result for that record.

`--debug-record` must not disable any records.

## Python Architecture

| File/class | Responsibility |
|---|---|
| `app/cli/main.py` | Thin Typer CLI; parse flags, select providers, call sync service, render result, set exit code |
| `app/config/settings.py` | Env/config: DB URLs, provider URLs/tokens if needed, user ids, default statuses, batch sizes, dry-run defaults |
| `app/db/session.py` | SQLAlchemy engine/session factories for new DB; old DB connection remains optional for health only, not business source |
| `app/db/models.py` | SQLAlchemy table models or reflected table definitions for catalog tables |
| `app/providers/base.py` | `ProviderAdapter` protocol/base class: fetch, parse, normalize, provider key, category scope, preserve policy |
| `app/providers/<provider_name>.py` | Provider-specific feed/API/HTML parsing and validation |
| `app/sync/normalizer.py` | Shared normalization helpers and `NormalizedAd` DTO validation |
| `app/mappers/ad_mapper.py` | Convert `NormalizedAd` to `CatalogListingPayload`, attribute payloads, image payloads |
| `app/repositories/ads_repository.py` | All DB reads/writes/upserts/diff helper queries for listings/attrs/images/map |
| `app/sync/diff.py` | Pure diff logic between desired payload and current DB projection |
| `app/sync/service.py` | Orchestrates provider run, batching, transactions, dry-run, disable missing, verification call |
| `app/sync/result.py` | Result dataclasses/counters, per-table touched counts, error/warning records |
| `app/verification/db_verifier.py` | Re-read affected rows and validate persisted state after writes |
| `app/utils/logging.py` | Structured console/file logging setup |
| `tests/` | Unit tests for mapping/diff/provider normalization and repository tests with test DB or mocks |

Separation rules:

- Provider parsing does not import repository/write code.
- Mapper does not execute SQL.
- Repository contains SQLAlchemy queries only; no provider-specific business decisions.
- CLI contains no business logic.
- Verification is separate from write logic.

## Implementation Order

1. Phase 1: DB schema understanding and write plan.
2. Phase 2: Python skeleton if not already created.
3. Phase 3: normalized DTO for ads.
4. Phase 4: repository for reading/writing ads in new DB.
5. Phase 5: one provider adapter, recommended first provider: `autohub` or `avtoinstall` because they are feed-based and simpler than HTML/AutoCRM.
6. Phase 6: dry-run sync for one provider.
7. Phase 7: real DB write for one provider only after curator approves write plan and schema assumptions.
8. Phase 8: `--verify` mode.
9. Phase 9: port remaining providers/scripts.
10. Phase 10: tests and cleanup.

## Safe Initial Provider Choice

Recommended first real provider after approval: `avtoinstall` or `autohub`.

- `avtoinstall`: simple single CSV, explicit active/in-stock filters, no old make/model reference dependency.
- `autohub`: representative Baz-on parts feed but includes make/model mapping and grouped ad behavior.

Do not start with:

- `kia`, because legacy command exits before writing.
- `allmotors`, `autoshina`, or `detalkg` tire crawler, because HTML crawling and tire/wheel schema questions add risk.
- AutoCRM cars, because they require the most complete reference-data mapping.
