# Migration Plan: PHP Sync To Python Catalog Sync

## What We Migrate

Migrate backend/data-sync behavior, not the old Symfony UI:

- provider feed readers;
- normalization and validation rules;
- legacy `Ad` field mapping;
- reference data mapping;
- diff logic by `external_id`;
- image sync logic;
- logging and dry-run behavior;
- idempotent writes to new catalog DB.

## What We Do Not Migrate Initially

- Twig/UI/frontend assets.
- Symfony controllers unrelated to sync.
- Old Doctrine configuration with empty entities.
- Old API write endpoints as target storage.
- Drive community parser unless explicitly included later.
- Old scheduler/cron infrastructure unless external deployment requires it.

## New DB Mapping

Target DB is assumed to be the catalog service schema.

| Legacy model/field | New table/field | Notes |
|---|---|---|
| `Ad` | `listings` + `listing_attributes` | Main split: base listing row + EAV attributes |
| `Image` | `images` | `external_url`, `priority`, `hash` |
| `type_id` | `listings.category_id` | via mapping in `CatalogSyncConfig` |
| `name` | `listings.title` | direct |
| `description` | `listings.description` | direct |
| `price` | `listings.price`; for cars also attr `price` | direct numeric |
| `currency` | `listings.currency` | old `1 -> KGS`, `2 -> USD` |
| `external_id` | attr `external_id` | required for idempotency |
| `region` | attr `region` | option lookup by `old_mysql_id` |
| `town` | attr `city` | option lookup by `old_mysql_id` |
| `make` | attr `make` | option lookup by `old_mysql_id` |
| `model` | attr `model` | option lookup by `old_mysql_id` and parent |
| `generation` | attr `generation` | option lookup by `old_mysql_id` and parent |
| `body` | attr `body_type` | option lookup by `old_mysql_id` and parent |
| `fuel` | attr `fuel_type` | value/parent lookup |
| `transmission` | attr `drive_type` | value/parent lookup |
| `gear_box` | attr `gearbox` | value/parent lookup |
| `modification` | attr `modification` | option lookup by `old_mysql_id` and parent |
| `steering_wheel` | attr `steering_wheel` | value lookup |
| `color` | attr `color` | value lookup |
| `mileage` | attr `mileage` | `value_json={"value": "...", "suffix": "км"}` |
| `customs` | attr `is_customs_cleared` | needs business confirmation |
| `vincode` | attr `vincode` | direct text |
| `old_price` | attr `old_price` | numeric |
| `phone` | attr `phone` | from provider payload or global `SYNC_CATALOG_PHONES` fallback |

## Type Mapping

| Old `type_id` | New category |
|---:|---|
| `1` | `car` / id `1` |
| `30` | `parts_supplies` / id `35` |
| `31` | `tires` / id `24` |
| `32` | `wheels` / id `37` |
| `33` | `accessories` / id `33` |
| `36` | `commercial_parts` / id `26` |

`type_id=30` must be confirmed. If generic parts should use parent `parts`, change the category mapping.

## Fields Requiring Transformation

- `currency`: old numeric ID to `KGS`/`USD`.
- `type_id`: old numeric ID to catalog category.
- reference IDs: old IDs to `attribute_options.id` using `old_mysql_id` when available.
- `fuel`, `drive_type`, `gearbox`, `color`, `condition`: require value/label matching when `old_mysql_id` is absent.
- images: normalize URL formats and `index|url` to `external_url` + `priority`.
- grouped ads: several old item ids can be joined into one comma-separated `external_id`.

## Fields Requiring Defaults

- `listings.user_id`: from `SYNC_CATALOG_USER_ID_<CLIENT>` or `SYNC_CATALOG_USER_ID`.
- `listings.status`: default from `SYNC_CATALOG_DEFAULT_STATUS`, currently `active` for moderated ads and `draft` fallback.
- `images.status`: default from `SYNC_CATALOG_IMAGE_STATUS`, currently `1`.
- `images.is_blurred`: default `false`.
- `description`: fallback to title if missing.
- `title`: fallback generated from `external_id` if missing.

## Fields Without Direct Mapping

The inspected catalog schema has no direct attributes for:

- `tire_width`
- `tire_height`
- `tire_size`
- `tire_type`
- `wheel_type`
- `wheel_size`
- `wheel_pcd`

Structured search/filtering for these fields still requires schema support. Until then Python
preserves the values in listing description and attempts EAV writes only when matching attribute
slugs exist.

Long-term options:

1. add catalog attributes;
2. keep them as description-only fields;
3. confirm another service owns these fields.

## Idempotency Strategy

Approved key:

```text
user_id + category_id + listing_attributes.external_id
```

Current catalog schema has `external_id` as an EAV attribute, so current lookup joins:

```text
listings
  -> listing_attributes external_id
```

No new sync table is required. If multiple catalog rows have the same
`user_id + category_id + external_id`, Python sync treats them as ambiguous duplicates and skips
that identity instead of updating a random listing.

## Python Architecture Proposal

```text
python_app/
  app/
    config/
      settings.py
    db/
      session.py
      models.py
    repositories/
      legacy_feeds.py
      catalog_listings.py
      catalog_references.py
    mappers/
      listing_mapper.py
      image_mapper.py
    services/
      sync_service.py
      diff_service.py
    sync/
      providers/
        autoland.py
        autohub.py
        autocrm.py
        ...
    cli/
      __main__.py
      commands.py
    utils/
      logging.py
      normalization.py
  tests/
  docs/
  pyproject.toml
  README.md
```

Recommended stack:

- Python 3.11+ or 3.12+
- SQLAlchemy 2.x
- Alembic only if this project owns new migrations
- Pydantic settings / pydantic-settings
- python-dotenv if needed for local dev
- Typer or argparse for CLI
- pytest
- ruff
- standard `logging`

## Target Flow

```text
Provider feed
  -> LegacyFeedRepository / parser
  -> LegacyAd DTO
  -> Mapper
  -> CatalogListingPayload
  -> CatalogRepository read current state
  -> DiffService
  -> SyncService
  -> CatalogRepository upsert/deactivate/images
```

## Implementation Phases

1. Phase 1: Legacy audit.
2. Phase 2: New Python project skeleton.
3. Phase 3: DB connection layer.
4. Phase 4: Models/repositories.
5. Phase 5: Mappers.
6. Phase 6: Sync services.
7. Phase 7: CLI commands.
8. Phase 8: Tests.
9. Phase 9: Validation against old/new DB.
10. Phase 10: Cleanup and documentation.

## Risks

- Old DB schema is absent; old API may hide important fields.
- Catalog status values need confirmation.
- Catalog has no strong unique sync key unless a mapping table is added.
- Tire/wheel fields are not represented as catalog attributes.
- Some provider parsers are fragile HTML scrapers.
- `KiaSyncCommand` contains debug behavior in legacy code.
