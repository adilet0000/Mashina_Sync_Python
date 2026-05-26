# New DB Assumptions

## Schema Source

No new DB schema files or migrations were found in this repository. The assumptions below are based on prior read-only inspection of the external catalog database schema and should be verified against the owning service before enabling writes.

No credentials are stored in this document.

## Assumed Catalog Tables

- `projects`
- `categories`
- `attributes`
- `attribute_options`
- `category_attributes`
- `listings`
- `listing_attributes`
- `images`
- `listing_counters`
- `listing_promotions`

## Assumed Core Columns

### `listings`

- `id`
- `category_id`
- `user_id`
- `title`
- `description`
- `price`
- `currency`
- `status`
- `created_at`
- `updated_at`
- `slug`
- `upped_at`

### `listing_attributes`

- `listing_id`
- `attribute_id`
- `attribute_options_id`
- `value_text`
- `value_number`
- `value_boolean`
- `value_date`
- `value_json`

Unique key assumed:

```text
(listing_id, attribute_id)
```

### `attribute_options`

- `id`
- `attribute_id`
- `parent_option_id`
- `value`
- `label`
- `old_mysql_id`
- `is_active`

`old_mysql_id` is assumed to be available for some old reference mappings.

### `images`

- `id`
- `listing_id`
- `hash`
- `status`
- `is_blurred`
- `priority`
- `external_url`
- `user_id`
- `created_at`

## Unknowns To Confirm

- Allowed values for `listings.status`.
- Whether `price` must be duplicated into EAV attr `price` for all categories or only cars.
- Required format for `mileage.value_json`.
- Required values for `images.status`, `images.moderated`, `object_name`, `expires_at`.
- Whether hard delete is ever allowed; current migration plan uses deactivate/status update.
- Whether `type_id=30` should map to `parts_supplies` or parent `parts`.
- How tires/wheels dimensions should be represented.
- Whether a dedicated sync mapping table can be added for reliable idempotency.

