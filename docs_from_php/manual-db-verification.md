# Manual Catalog DB Verification

Replace `:provider`, `:external_id`, `:user_id`, `:category_id`, and `:listing_id` before running.

Important: read-only inspection on 2026-05-26 showed that catalog attribute `source`
is numeric and is not a provider-name field. Do not verify provider ownership through
`attributes.slug = 'source'`.

The safest provider lookup requires the recommended `sync_listing_map` table. Until
that table exists, fallback checks can only search by `user_id + category_id + external_id`
and cannot prove provider ownership if several providers share the same user/category.

## Find Listing By Provider And External ID With sync_listing_map

```sql
SELECT l.*, m.source AS provider, m.external_id
FROM sync_listing_map m
JOIN listings l ON l.id = m.listing_id
WHERE m.source = :provider
  AND m.external_id = :external_id
  AND m.user_id = :user_id
  AND m.category_id = :category_id;
```

## Fallback: Find Listing By External ID

```sql
SELECT l.*
FROM listings l
JOIN listing_attributes la_ext ON la_ext.listing_id = l.id
JOIN attributes a_ext ON a_ext.id = la_ext.attribute_id
WHERE a_ext.slug = 'external_id'
  AND la_ext.value_text = :external_id
  AND l.user_id = :user_id
  AND l.category_id = :category_id;
```

## View Listing Attributes

```sql
SELECT
  a.slug,
  la.attribute_options_id,
  ao.value AS option_value,
  ao.label AS option_label,
  ao.old_mysql_id,
  la.value_text,
  la.value_number,
  la.value_boolean,
  la.value_date,
  la.value_json
FROM listing_attributes la
JOIN attributes a ON a.id = la.attribute_id
LEFT JOIN attribute_options ao ON ao.id = la.attribute_options_id
WHERE la.listing_id = :listing_id
ORDER BY a.slug;
```

## View Listing Images

```sql
SELECT
  id,
  listing_id,
  external_url,
  hash,
  priority,
  status,
  is_blurred,
  user_id,
  created_at
FROM images
WHERE listing_id = :listing_id
ORDER BY priority ASC, id ASC;
```

## View Inactive Provider Listings With sync_listing_map

```sql
SELECT
  l.id,
  l.title,
  l.status,
  l.updated_at,
  m.external_id
FROM sync_listing_map m
JOIN listings l ON l.id = m.listing_id
WHERE m.source = :provider
  AND m.user_id = :user_id
  AND m.category_id = :category_id
  AND l.status = :inactive_status
ORDER BY l.updated_at DESC;
```

## Fallback: View Inactive Listings By User/Category

```sql
SELECT
  l.id,
  l.title,
  l.status,
  l.updated_at,
  la_ext.value_text AS external_id
FROM listings l
JOIN listing_attributes la_ext ON la_ext.listing_id = l.id
JOIN attributes a_ext ON a_ext.id = la_ext.attribute_id
WHERE a_ext.slug = 'external_id'
  AND l.user_id = :user_id
  AND l.category_id = :category_id
  AND l.status = :inactive_status
ORDER BY l.updated_at DESC;
```

## Check Duplicate External IDs With sync_listing_map

```sql
SELECT
  m.source AS provider,
  m.user_id,
  m.category_id,
  m.external_id,
  COUNT(*) AS duplicate_count,
  ARRAY_AGG(m.listing_id ORDER BY m.listing_id) AS listing_ids
FROM sync_listing_map m
GROUP BY m.source, m.user_id, m.category_id, m.external_id
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC;
```

## Fallback: Check Duplicate External IDs By User/Category

```sql
SELECT
  l.user_id,
  l.category_id,
  la_ext.value_text AS external_id,
  COUNT(*) AS duplicate_count,
  ARRAY_AGG(l.id ORDER BY l.id) AS listing_ids
FROM listings l
JOIN listing_attributes la_ext ON la_ext.listing_id = l.id
JOIN attributes a_ext ON a_ext.id = la_ext.attribute_id
WHERE a_ext.slug = 'external_id'
GROUP BY l.user_id, l.category_id, la_ext.value_text
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC;
```

## Check Listings Without External ID

```sql
SELECT l.id, l.user_id, l.category_id, l.title, l.status
FROM listings l
LEFT JOIN listing_attributes la_ext
  ON la_ext.listing_id = l.id
 AND la_ext.attribute_id = (SELECT id FROM attributes WHERE slug = 'external_id' LIMIT 1)
WHERE la_ext.id IS NULL
   OR COALESCE(la_ext.value_text, '') = '';
```

## Check Images Without URL Or Hash

```sql
SELECT id, listing_id, external_url, hash, status, priority
FROM images
WHERE COALESCE(external_url, '') = ''
   OR COALESCE(hash, '') = '';
```

## Optional sync_listing_map Check

```sql
SELECT source, user_id, category_id, external_id, listing_id
FROM sync_listing_map
WHERE source = :provider
  AND user_id = :user_id
  AND category_id = :category_id
ORDER BY updated_at DESC
LIMIT 50;
```
