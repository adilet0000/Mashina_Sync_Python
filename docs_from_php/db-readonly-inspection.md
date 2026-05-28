# Catalog DB Read-Only Inspection

Inspection date: 2026-05-26.

No writes or schema changes were made. Queries used `default_transaction_read_only=on`.

## Databases Seen

- `celery-tasks`
- `mashina-analytics-service`
- `mashina-reports-service`
- `mashina_bank_gateway`
- `mashina_catalog_service`
- `mashina_chat_service`
- `mashina_credit_service`
- `mashina_cronjobs_service`
- `mashina_mbank_proxy_service`
- `mashina_moderation_service`
- `mashina_notification_service`
- `mbank-test`
- `postgres`

## Drive2 Community Parser Tables

No table for Drive2/community posts was found in the catalog DB.

Tables that matched drive/post/community-like names:

- `mashina_mbank_proxy_service.public.user_drive_profile`
- `mbank-test.public.user_drive_profile`
- `mashina-analytics-service.public.example_item_files`

`user_drive_profile` is a profile/counter table:

- `user_id`
- `car_counter`
- `follower_counter`
- `following_counter`
- `car_following_counter`
- `bio`
- `instagram`
- `youtube`

It is not a Drive2 post import table. `mashina_catalog_service.public.comments` is listing comments,
not community posts.

Conclusion: `app:parse-drive` does not have an obvious target in the new catalog DB and should stay
out of scope unless a separate Drive/community service schema is provided.

## Catalog Tables Confirmed

In `mashina_catalog_service`:

- `listings`
- `listing_attributes`
- `attributes`
- `attribute_options`
- `categories`
- `category_attributes`
- `images`
- `listing_counters`
- `listing_promotions`
- plus service tables such as `comments`, `favorites`, `offers`, `complaints`, `banners`

`sync_listing_map` does not exist and is not required by the approved implementation.

## Resolved Schema Questions

| Topic | Inspection result | Impact |
|---|---|---|
| `listings.status` values | Existing values include `active`, `inactive`, `deleted`, `unpaid`, `blocked`, `rejected`, `pending`, `archived`, `processing`, `in_review`. | Defaults `active`/`inactive` are valid existing values. |
| `images.status` values | Existing values include `5`, `3`, `1`, `0`; most rows are `5`. | Env-configured image statuses are still needed; business meaning of values should be confirmed. |
| `images` required columns | Required: `hash`, `status`, `is_blurred`; `listing_id`, `external_url`, `user_id`, `object_name`, `expires_at`, `moderated` are nullable. | Current external URL image insert shape can satisfy DB constraints. |
| `listing_attributes` uniqueness | `UNIQUE (listing_id, attribute_id)` exists. | Current select/update/insert upsert strategy is valid. |
| `attributes.slug` uniqueness | Unique index `attributes_slug_idx` exists. | Resolver by slug is safe. |
| Target category ids | Confirmed: `1=car`, `24=tires`, `26=commercial_parts`, `33=accessories`, `35=parts_supplies`, `37=wheels`. | Current old `type_id` mapping is aligned with DB categories. |
| `type_id=30` mapping | Category `35` is `parts_supplies` under `parts`. | Current `30 -> 35` mapping is correct for generic parts. |
| Price EAV duplication | Attribute `price` exists, but there are currently `0` `listing_attributes` rows for it. | Writing only `listings.price` is aligned with current data. |
| Mileage format | Existing mileage rows use `value_text`, `value_number`, and `value_json={"value": "...", "suffix": "км"}`. | Python writes new mileage values as `value_json={"value": "...", "suffix": "км"}`. |
| Provider identity table | No dedicated sync table exists. | Approved strategy is `user_id + category_id + listing_attributes.external_id`; duplicates in that scope are skipped. |

## Provider Identity Risk

The catalog has an attribute `source`, but it is not a provider string field.

Observed schema:

- `attributes.slug='source'`
- `data_type=INTEGER`
- `input_type=SELECT`

Observed stored values:

- `value_number=1`
- `value_number=2`
- no `attribute_options` rows for `source`

Therefore `source` should not be used to store provider names like `autoland` or `toyota`.

Approved recommendation before enabling real writes:

1. Use `user_id + category_id + listing_attributes.external_id` for idempotency.
2. Do not use the catalog `source` attribute for provider names.
3. If duplicates already exist in the approved identity scope, skip that identity and clean it up
   manually before enabling broad deactivation.

## Tire/Wheel Attribute Gap

These attributes were not found:

- `tire_width`
- `tire_height`
- `tire_size`
- `tire_type`
- `wheel_type`
- `wheel_size`
- `wheel_pcd`

Python providers preserve tire/wheel specs in title/description and DTO fields. Structured catalog
attributes are written only if the target slugs exist in catalog `attributes`; otherwise those
attribute writes are skipped with warnings.
or an approved alternative mapping.
