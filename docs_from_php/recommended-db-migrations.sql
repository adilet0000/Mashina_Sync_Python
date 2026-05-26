-- Recommended optional migration for robust provider sync idempotency.
-- Do not apply automatically. Review in the owning catalog service first.

CREATE TABLE IF NOT EXISTS sync_listing_map (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(100) NOT NULL,
    user_id BIGINT NOT NULL,
    category_id BIGINT NOT NULL,
    external_id VARCHAR(255) NOT NULL,
    listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source, user_id, category_id, external_id)
);

CREATE INDEX IF NOT EXISTS idx_sync_listing_map_listing_id
    ON sync_listing_map (listing_id);

-- These indexes support the EAV fallback lookup when sync_listing_map is absent.
CREATE INDEX IF NOT EXISTS idx_attributes_slug
    ON attributes (slug);

CREATE INDEX IF NOT EXISTS idx_listing_attributes_listing_attribute
    ON listing_attributes (listing_id, attribute_id);

CREATE INDEX IF NOT EXISTS idx_listing_attributes_attribute_text
    ON listing_attributes (attribute_id, value_text);

-- The Python repository uses ON CONFLICT for idempotent attribute/image writes.
-- Add only if equivalent unique constraints do not already exist.
CREATE UNIQUE INDEX IF NOT EXISTS uq_listing_attributes_listing_attribute
    ON listing_attributes (listing_id, attribute_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_images_listing_hash
    ON images (listing_id, hash);
