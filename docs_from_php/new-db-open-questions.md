# New DB Open Questions

The Python sync can be designed now, but real writes should stay disabled until these points are confirmed by the catalog DB/service owner.

Read-only inspection was performed on 2026-05-26. Results are summarized in
`docs/db-readonly-inspection.md`; unresolved write blockers are summarized in
`docs/final-open-questions.md`.

## Schema And Constraints

| Area | Question | Why it matters | Safe assumption until confirmed |
|---|---|---|---|
| Authoritative DDL | Where is the real catalog schema/migration source? | Current repository has no new DB migrations/schema files. | Treat `docs/new-db-assumptions.md` and catalog prototype classes as provisional. |
| `listings.status` | What values are allowed? `active`, `inactive`, `draft`, numeric enum, or PostgreSQL enum? | Sync must activate and disable listings correctly. | Use configurable strings, default `active` and `inactive`, but block real writes until confirmed. |
| `images.status` | What values are allowed? | Image insert/disable must not violate constraints. | Use configurable integers, default `1` active and `0` inactive, but verify before writes. |
| `images` required columns | Are `moderated`, `object_name`, `expires_at`, or other columns required? | Current prototype inserts only `listing_id`, `hash`, `status`, `is_blurred`, `priority`, `external_url`, `created_at`, `user_id`. | Do not enable image writes until required columns are confirmed. |
| `listing_attributes` uniqueness | Is `UNIQUE (listing_id, attribute_id)` guaranteed? | Attribute upsert depends on it. | Required for implementation; otherwise use explicit select/update/insert. |
| Attribute slug uniqueness | Is `attributes.slug` unique? | Mapper resolves attributes by slug. | Assume unique, but verify in schema/read-only query. |
| Category slug/id mapping | Are category ids `1`, `35`, `24`, `37`, `33`, `26` stable? | Wrong category ids put listings into wrong catalog section. | Keep mapping in config and require verification against DB. |
| `type_id=30` mapping | Should old parts type `30` map to category `35 parts_supplies` or a parent parts category? | Most providers are parts providers. | Use current prototype mapping `30 -> 35` only in dry-run until confirmed. |
| Tire/wheel attributes | Do catalog attributes exist for width/height/size/type/PCD? | Tire/wheel providers cannot be fully represented without these fields. | Preserve specs in title/description and mark structured fields as unmapped until confirmed. |
| `mileage` format | What JSON shape is expected for mileage? | Current prototype stores `{"raw": value}`. | Keep raw JSON wrapper in dry-run; confirm before car writes. |
| `is_customs_cleared` type | Is it an option attr or boolean attr? | Current prototype treats it like option lookup. | Block real AutoCRM writes until attribute type is confirmed. |

## Provider Identity And Idempotency

| Area | Question | Why it matters | Safe assumption until confirmed |
|---|---|---|---|
| Provider/source storage | Resolved: do not use catalog `source` attr for provider names. | `source` is a numeric catalog attribute, not provider marker. | Provider name remains an application/runtime label only. |
| New sync table allowed | Resolved: do not add a new sync table. | The catalog already stores listing identity via EAV `external_id`. | Match by `user_id + category_id + listing_attributes.external_id`. |
| Unique key scope | Resolved: uniqueness is `user_id + category_id + external_id`. | Same article ids may appear across categories. | Detect duplicates in that scope and skip ambiguous rows. |
| Grouped legacy external ids | Should grouped comma-joined external ids stay as legacy behavior? | Grouping changes can create new identities and disable old grouped rows. | Preserve legacy grouping for equivalent behavior, but log grouping decisions. |
| Missing/invalid external id | Should any provider allow fallback keys? | Bad keys create duplicates. | Skip records with missing external id. |

## Write Ownership

| Area | Question | Why it matters | Safe assumption until confirmed |
|---|---|---|---|
| `user_id` source | Which catalog user owns each provider's listings? | `listings.user_id` is required. | Configure `SYNC_CATALOG_USER_ID_<PROVIDER>`; never infer from old API in final Python rewrite. |
| Manual edits | Which fields can users edit manually and should sync preserve? | Legacy preserved price/description for some AutoCRM providers. | Implement provider-specific preserve policies and start conservative. |
| Promotions/counters | Should sync touch `listing_counters` or `listing_promotions`? | Updating these could break catalog behavior. | Do not write these tables. |
| Slug generation | Does DB/service generate `slug`, or must sync set it? | Missing required slug could break inserts. | Do not set slug unless schema requires it; confirm before writes. |
| Moderation workflow | Should synced ads go straight active or draft/pending moderation? | Status affects public visibility. | Make status configurable per provider; default active only after approval. |

## Verification

| Area | Question | Why it matters | Safe assumption until confirmed |
|---|---|---|---|
| Required post-write checks | What checks does curator expect beyond row counts? | Verification output must prove data was written correctly. | Implement `--verify` to re-read affected rows, required fields, unique keys, statuses, timestamps, images. |
| Allowed read-only checks | Can the sync run read catalog metadata before writes in production? | Reference resolution requires reads from `attributes`, `attribute_options`, `categories`. | Reads are required; writes remain guarded by dry-run/approval. |
| Test database | Is there a staging DB for first real write? | Avoid testing against production. | Use dry-run and limited provider runs until staging write is approved. |

## Provider-Specific Questions

| Provider/group | Question | Safe assumption |
|---|---|---|
| AutoCRM Toyota/Lexus/Tradein | Should legacy manual price/description preservation remain? | Preserve legacy behavior through provider policies. |
| Kia | Should the debug `print_r/exit` legacy behavior be fixed and enabled, or excluded initially? | Exclude from first real writes; implement only after requirements are confirmed. |
| HTML crawlers | Are Allmotors/Autoshina/Detal HTML pages stable enough for production sync? | Port after feed-based providers and add robust retry/parser tests. |
| DetalKg parts | Is +20% price markup still required? | Preserve legacy behavior until business owner says otherwise. |
| Removed ads | Should missing provider ads be disabled immediately or after N missed runs? | Initial plan disables after successful full run; consider grace period if feeds are unreliable. |
