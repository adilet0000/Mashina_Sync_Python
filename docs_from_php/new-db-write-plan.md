# New DB Write Plan

Final decision: do not add a separate provider identity table.

The Python sync writes provider ads directly into the catalog DB:

```text
Provider feed/API/page
-> provider adapter/parser
-> LegacyAd
-> CatalogListingPayload
-> catalog DB diff
-> listings/listing_attributes/images writes
-> verification
```

## Target Tables

| Table | Purpose | Sync usage |
|---|---|---|
| `listings` | Main catalog listing row | `user_id`, `category_id`, `title`, `description`, `price`, `currency`, `status`, `slug`, timestamps |
| `listing_attributes` | EAV attributes for listings | Required `external_id`; optional make/model/condition/phone/etc. |
| `attributes` | Attribute definitions | Resolve attribute ids by `slug` |
| `attribute_options` | Reference/options table | Resolve options by `old_mysql_id` or label/value where possible |
| `images` | Listing images | Insert/reactivate current image URLs and deactivate missing URLs |

The sync does not write `listing_counters`, `listing_promotions`, comments, favorites, offers,
complaints, banners, or any old PHP/internal API tables.

## Approved Identity

Current listings are matched by:

```text
listings.user_id
+ listings.category_id
+ listing_attributes.external_id
```

`external_id` is stored in `listing_attributes.value_text` where `attributes.slug = 'external_id'`.
The provider name remains a runtime/logging label only. The catalog `source` attribute is not used
as provider marker because it is a numeric catalog attribute in the inspected DB.

If more than one DB row has the same `user_id + category_id + external_id`, Python sync logs an
error and skips that identity. It does not update a random duplicate.

## Mapping

| Legacy/normalized field | Catalog target | Notes |
|---|---|---|
| `type_id` | `listings.category_id` | `1->1`, `30->35`, `31->24`, `32->37`, `33->33`, `36->26` |
| `name` | `listings.title` | Fallback generated from provider/external id if missing |
| `description` | `listings.description` | Fallback to title |
| `price` | `listings.price` | Some providers intentionally set `0` when legacy import price was disabled |
| `currency` | `listings.currency` | `1->KGS`, `2->USD` |
| `external_id` | `listing_attributes.external_id` | Required |
| `region` | `listing_attributes.region` | Option lookup when attribute exists |
| `town` | `listing_attributes.city` | Option lookup when attribute exists |
| `make` | `listing_attributes.make` | Option lookup by old id or label/value |
| `model` | `listing_attributes.model` | Option lookup by old id or label/value |
| `generation` | `listing_attributes.generation` | Option lookup by old id or label/value |
| `body` | `listing_attributes.body_type` | Option lookup |
| `fuel` | `listing_attributes.fuel_type` | Option/value lookup |
| `transmission` | `listing_attributes.drive_type` | Option/value lookup |
| `gear_box` | `listing_attributes.gearbox` | Option/value lookup |
| `modification` | `listing_attributes.modification` | Option/value lookup |
| `steering_wheel` | `listing_attributes.steering_wheel` | Option/value lookup |
| `color` | `listing_attributes.color` | Option/value lookup |
| `mileage` | `listing_attributes.mileage` | Stored as `value_json={"value": "...", "suffix": "км"}` |
| `customs` | `listing_attributes.is_customs_cleared` | Depends on catalog attribute type |
| `vincode` | `listing_attributes.vincode` | Direct text |
| `old_price` | `listing_attributes.old_price` | Numeric |
| `phone` | `listing_attributes.phone` | Provider payload or global `SYNC_CATALOG_PHONES` fallback |
| `images` | `images` | Stable hash from normalized `external_url`; preserve `priority` |

Missing attribute slugs are logged and skipped, except `external_id`: missing `external_id`
attribute is a hard error because idempotency depends on it.

Tire/wheel specs are also appended to `listings.description` as a fallback, because the inspected
catalog DB does not currently have all structured tire/wheel attribute slugs. If those slugs are
added later, the same payload will also write structured EAV attributes.

## Upsert Behavior

- New identity: insert `listings`, then upsert attributes, then insert images.
- Existing identity: compare stable fields and update only when content changed.
- Empty provider values do not overwrite existing values unless a required fallback exists.
- `updated_at` changes only when listing core fields, attributes, or images change.
- Missing provider listings are not hard-deleted; their `listings.status` is changed to
  `SYNC_CATALOG_INACTIVE_STATUS`.
- Missing images are not deleted; their `images.status` is changed to
  `SYNC_CATALOG_IMAGE_INACTIVE_STATUS`.

## Safety

Real writes are blocked unless all are true:

```text
SYNC_TARGET=catalog
SYNC_DRY_RUN=0
SYNC_ALLOW_CATALOG_WRITES=1
CLI call does not pass --dry-run
```

Before write, the script prints a password-free DB target summary, provider, user id, categories,
mode, and write flag.

## Verification

`--verify` re-reads affected records and checks:

- listing exists;
- `external_id` attribute exists and matches;
- `user_id` and `category_id` match;
- core listing fields match;
- images exist with expected URL/hash/priority;
- deactivated listings have inactive status.

Verification failures increment `verification_failed_count` and make CLI return a non-zero exit
code.
