-- Safe production-oriented migration for Python catalog sync identity.
--
-- Purpose:
--   Store provider identity separately from catalog EAV attributes:
--   source/provider + user_id + category_id + external_id -> listing_id.
--
-- Scope:
--   This migration creates only one new table and indexes on that new table.
--   It does not alter listings, listing_attributes, images, attributes, or
--   attribute_options.
--
-- Why this is safe:
--   - existing catalog rows are not updated;
--   - existing catalog table columns are not changed;
--   - existing catalog indexes/constraints are not changed;
--   - existing server code can ignore this table;
--   - ON DELETE CASCADE only removes sync map rows when a linked listing is deleted.
--
-- Review before applying:
--   - run on staging/local dump first;
--   - apply during low-traffic window if production is very write-heavy;
--   - do not apply the broader recommended-db-migrations.sql to production without
--     separate review, because that file also proposes indexes on existing tables.

BEGIN;

CREATE TABLE IF NOT EXISTS sync_listing_map (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(100) NOT NULL,
    user_id BIGINT NOT NULL,
    category_id INTEGER NOT NULL,
    external_id TEXT NOT NULL,
    listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_sync_listing_map_source_not_empty
        CHECK (BTRIM(source) <> ''),
    CONSTRAINT chk_sync_listing_map_external_id_not_empty
        CHECK (BTRIM(external_id) <> '')
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_sync_listing_map_identity
    ON sync_listing_map (source, user_id, category_id, external_id);

CREATE INDEX IF NOT EXISTS idx_sync_listing_map_listing_id
    ON sync_listing_map (listing_id);

CREATE INDEX IF NOT EXISTS idx_sync_listing_map_source_user_category
    ON sync_listing_map (source, user_id, category_id);

COMMIT;

