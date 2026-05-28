# Final Open Questions Before Catalog Write Enablement

Read-only DB inspection was performed on 2026-05-26. See
`docs/db-readonly-inspection.md`.

These items do not block dry-run validation. They do block or constrain real write enablement until
the catalog owner approves the safe default.

| Topic | Still unconfirmed | Safe default implemented |
|---|---|---|
| Provider identity | Resolved by curator/PHP author: no new sync table. `source` attr is not a provider field and is not used. | Match by `user_id + category_id + listing_attributes.external_id`; skip ambiguous duplicates instead of updating a random row. |
| `images.status` business meaning | Existing values are `5`, `3`, `1`, `0`, but meaning is not documented here. | Keep `SYNC_CATALOG_IMAGE_STATUS` and inactive image status configurable. |
| `mileage.value_json` | Shape is now observed: `{"value": "...", "suffix": "км"}`. Python still needs exact car-write formatting before AutoCRM writes. | Keep AutoCRM car writes behind dry-run/limited verification until mileage formatting is aligned. |
| Hard delete policy | Whether hard delete is ever allowed for disappeared provider ads. | Never hard deletes provider listings; deactivates with `SYNC_CATALOG_INACTIVE_STATUS`. |
| Tire/wheel dimensions | Tire/wheel attributes are missing in catalog DB. | Preserve specs in title/description and DTO; structured tire/wheel EAV requires schema/mapping decision. |
| Live provider markup | HTML selectors for Allmotors, Autoshina, and DetalKg tire pages may drift. | Fixture-tested parsers with legacy selectors; live dry-run should be run before writes. |
| Toyota Trade-In currency rate | Old PHP read dealer currency rate from old internal API. | Uses `SYNC_PROVIDER_TOYOTA_TRADEIN_CURRENCY_RATE`, default `1`; no old API dependency. |

## Resolved By Read-Only Inspection

- `listings.status`: `active` and `inactive` exist.
- `type_id=30` mapping: category `35` exists and is `parts_supplies`.
- Other target categories exist: `1=car`, `24=tires`, `26=commercial_parts`,
  `33=accessories`, `37=wheels`.
- `listing_attributes` has `UNIQUE (listing_id, attribute_id)`.
- `attributes.slug` is unique.
- `images` required columns are compatible with the current insert shape.
- Price EAV duplication is not used in current data: `price` attribute has zero rows.
