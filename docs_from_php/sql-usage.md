# SQL Usage Audit

## Legacy PHP SQL Usage

Search scope:

- `src/Command`
- `src/Service`
- `config`
- `migrations`
- `src/Entity`
- `src/Repository`

Patterns checked:

- `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `JOIN`
- `mysql_*`
- `mysqli`
- `PDO`
- Doctrine `Connection`, `executeQuery`, `executeStatement`, `executeUpdate`, `fetchAll`
- Doctrine ORM `EntityManager`, `getRepository`, `persist`, `flush`
- query builder calls

Result: no legacy business SQL or direct old DB access was found in the original PHP sync code.

## Doctrine Configuration

`config/packages/doctrine.yaml` configures a MySQL connection:

- driver: `pdo_mysql`
- server version: `5.7`
- URL: `%env(resolve:DATABASE_URL)%`
- ORM mapping dir: `src/Entity`

But no real entities, repositories, or migrations exist. Sync scripts do not use this connection for legacy data.

## Old API Operations Used Instead Of SQL

The legacy sync layer uses HTTP API endpoints from `BaseSync.php`:

| Operation | Endpoint | Method | Purpose |
|---|---|---|---|
| Read current user | `self/info` | `GET` | Validate token/dealer and get phones |
| Read reference data | `public/data` | `GET` | Makes/models/static refs |
| Read car reference data | `public/data/car?...` | `GET` | Generation/body/fuel/transmission/gearbox/modification lookup |
| VIN precheck | `public/report/precheck?vincode=...` | `GET` | Fill missing make/model |
| Read current ads | `sync/ads?...` | `GET` | Current ads by `type_id` and non-empty `external_id` |
| Create ads | `sync/ads/bulk-create` | `POST` | Create old API ads |
| Update ads | `sync/ads/bulk-update` | `PATCH` | Update old API ads |
| Delete ads | `sync/ads/bulk-delete` | `DELETE` | Delete old API ads |
| Create images | `sync/images/bulk-create` | `POST` | Create old API images |
| Delete images | `sync/images/bulk-delete` | `DELETE` | Delete old API images |

## Current Catalog Transition SQL

These SQL statements are not legacy old-DB SQL. They were added for the new catalog target and are protected by dry-run/write flags.

### Read current catalog ads

File: `src/Service/Sync/CatalogListingRepository.php`

Reads `listings`, `listing_attributes`, `attributes`, `attribute_options` by:

- catalog `user_id`;
- catalog `category_id`;
- attr `external_id`.

Purpose: reconstruct legacy-shaped `currentAds` arrays so existing sync diff logic can run against the new DB.

### Read catalog images

File: `src/Service/Sync/CatalogListingRepository.php`

Reads `images` by `listing_id`.

Purpose: reconstruct current image map `[url => image_id]`.

### Read attributes

File: `src/Service/Sync/CatalogReferenceResolver.php`

Reads `attributes`.

Purpose: resolve `attribute_id` by slug.

### Read attribute options

File: `src/Service/Sync/CatalogReferenceResolver.php`

Reads `attribute_options` joined with `attributes`, lazily per attribute slug or option id.

Purpose: resolve old ids through `old_mysql_id`, value matching, and parent chains.

### Future write statements

File: `src/Service/Sync/CatalogListingWriter.php`

Protected by:

```text
SYNC_TARGET=catalog
SYNC_DRY_RUN=0
SYNC_ALLOW_CATALOG_WRITES=1
```

Statements:

- update `listings.status` for deactivation;
- update `images.status` for image deactivation;
- insert/update `listing_attributes` with `ON CONFLICT (listing_id, attribute_id)`;
- insert/update `listings`;
- insert `images`.

These do not run during audit or dry-run.

## Missing Old DB Information

No old DB schema is present in the repository. If there was an old MySQL DB behind the old API, its table structure is not represented in this codebase.

