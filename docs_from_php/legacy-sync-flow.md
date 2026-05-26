# Legacy PHP Sync Flow

The legacy sync process is feed/API driven. It does not read ads from a local Doctrine model or from an old ads database table. Current state comes from old internal HTTP API endpoints, and writes go back through the same API.

## High-Level Flow

```text
Provider feed/API/page
-> provider parser/sanitizer
-> BaseSync associative array using FIELD_* keys
-> current ads from old internal API
-> comparison by external_id and provider compare fields
-> bulk create/update/delete through old internal API
```

For AutoCRM car providers, images have an extra diff step:

```text
AutoCRM XML images
-> FIELD_IMAGES as ["0|url", "1|url", ...]
-> current old API image map: url => image_id
-> compareImages()
-> sync/images/bulk-create or sync/images/bulk-delete
```

## Old Internal API Contract

Base URL is `API_URL` from Symfony parameters. `ApiClient` sends JSON requests through Guzzle with:

- `Content-Type: application/json`
- `auto-auth: Bearer <AUTO_AUTH>`
- per-provider `Authorization: Bearer <PROVIDER_TOKEN>` for authenticated sync endpoints

| Purpose | Endpoint | Method | Request payload/query | Expected response shape | Used by |
|---|---|---|---|---|---|
| Validate current provider account | `self/info` | `GET` | Bearer provider token | `outcome=success`, `data.dealer.status`, `data.phones` | Every sync command |
| Get public reference data | `public/data` | `GET` | None | `outcome=success`, `data` reference arrays | AutoCRM car mapping |
| Get filtered car reference data | `public/data/car?...` | `GET` | Query such as `model_id`, `year`, `generation_id`, `body_id`, `fuel_id`, `transmission_id`, `gear_box_id` | `outcome=success`, `data.generation/body/transmission/gear_box/modification` | AutoCRM car mapping |
| VIN precheck fallback | `public/report/precheck?vincode=<vin>` | `GET` | VIN | `outcome=success`, `data.make`, `data.model` | AutoCRM missing make/model fallback |
| Dealer currency rate | `sync/currency-rate` | `GET` | Bearer provider token | `outcome=success`, `data.rate`; fallback `1` | Toyota trade-in |
| Read current part-like ads | `sync/ads?...` | `GET` | URL-encoded JSON `filter`, JSON `fields`, `limit=200`, `offset` | `outcome=success`, `data.list` keyed by `external_id` | Parts, tire, wheel, accessories providers |
| Read current car ads | `sync/ads?...` | `GET` | Same as above, `type_id = 1` | Same | AutoCRM car providers |
| Bulk create ads | `sync/ads/bulk-create` | `POST` | `{ "ads": [BaseSync ad payloads] }`, chunks of 20 | `outcome=success`, `data.ad_count` | All sync commands |
| Bulk update ads | `sync/ads/bulk-update` | `PATCH` | `{ "ads": [BaseSync ad payloads with id] }`, chunks of 20 | `outcome=success`, `data.ad_count` | All sync commands |
| Bulk delete/disable ads | `sync/ads/bulk-delete` | `DELETE` | `{ "ids": [old ad ids] }`, chunks of 20 | `outcome=success`, `data.ad_count` | All sync commands |
| Bulk create images | `sync/images/bulk-create` | `POST` | `{ "ad_id": old ad id, "images": ["index|url", ...] }` | `outcome=success`, `data.image_count` | AutoCRM car commands |
| Bulk delete images | `sync/images/bulk-delete` | `DELETE` | `{ "ids": [old image ids] }`, chunks of 20 | `outcome=success`, `data.image_count` | AutoCRM car commands |

There is no retry policy. API exceptions are caught in `ApiClient::request()`, and the code tries to decode the error response body as JSON. Commands usually stop on critical feed/API parse failures, but single-row mapping errors often only log and skip the row.

## Current Ads Read Logic

`BaseSync` has three read helpers:

| Helper | Filter | Pagination | Returned key | Used by |
|---|---|---|---|---|
| `getPartAds($token, $fields, $typeIds = null)` | `type_id` in provided ids or between `30` and `37`, `external_id <> ""` | `limit=200`, incrementing `offset` until empty/error | Expected `external_id` | Parts, accessories, tire/wheel providers |
| `getTireAds($token, $fields)` | `type_id = 31`, `external_id <> ""` | Same | Expected `external_id` | Autoshina |
| `getAutoAds($token, $fields)` | `type_id = 1`, `external_id <> ""` | Same | Expected `external_id` | AutoCRM car providers |

The command comparison code assumes `data.list` is an associative array keyed by `external_id`.

## Create / Update / Delete Decision

Every normal command follows this pattern:

1. Read current ads from old API into `$currentAds`.
2. Parse provider input and normalize valid entries into `$syncAds`.
3. Use `$syncAds[$ad[BaseSync::FIELD_EXTERNAL_ID]] = $ad`.
4. For every current external id missing from `$syncAds`, schedule delete: `$adsToDelete[] = current id`.
5. For every sync external id already present, call provider `adsEqual()`. If false, copy current `id` into new payload and schedule update.
6. For every sync external id not present in current ads, schedule create.
7. Log counts.
8. Execute delete, update, create in that order through old API.

Deletes in the legacy method are API `bulk-delete` calls. For the new DB rewrite, this should be interpreted as "provider listing no longer exists in feed" and should generally become deactivate/mark inactive instead of hard delete unless product requirements say otherwise.

## Provider Flows

| Command | Service | Provider source | Parser | Current ads scope | Unique key | Notes |
|---|---|---|---|---|---|---|
| `app:sync-autohub` | `AutohubSync` | Baz-on CSV `https://baz-on.ru/export/c1010/af1b1/mashina-parts.csv` | Windows-1251 CSV, `;` delimiter | old type ids `30..37` | CSV `Артикул`, or comma-joined article ids for grouped rows | Groups rows by name/make/model/year/generation. Commercial makes `setra`, `neoplan`, `man` use type `36`. |
| `app:sync-autoland` | `AutolandSync` | Baz-on CSV `https://baz-on.ru/export/c2095/9d8bf/autolandkg-parts.csv` | Windows-1251 CSV, `;` delimiter | old type ids `30..37` | CSV `Артикул`, or comma-joined grouped ids | Groups by name/make/model. Price imported. New condition only for `Новый` + `Товары из Дордоя`. |
| `app:sync-shredder` | `ShredderSync` | Baz-on CSV `https://baz-on.ru/export/c3846/2bd53/mashinakg-parts.csv` | Windows-1251 CSV, `;` delimiter | old type ids `30..37` | CSV `Артикул`, or comma-joined grouped ids | Similar to Autohub. Price import disabled and price becomes `0`. Commercial makes use type `36`. |
| `app:sync-okayamaomsk` | `OkayamaomskSync` | Baz-on CSV `https://baz-on.ru/export/c614/e5dc9/car-kg-parts.csv` | Windows-1251 CSV, `;` delimiter | old type ids `30..37` | CSV `Артикул` | Region/town overridden to `9`/`62`; `featured_option=2`; description appends delivery/payment text. |
| `app:sync-banzaimotors` | `BanzaimotorsSync` | Baz-on parts CSV and wheel/tire CSV | Windows-1251 CSV, `;` delimiter | parts `30`; tire/wheel `31,32` | CSV `Артикул` | Parts and tire/wheel feeds are processed in one command. Price import disabled for parts and tire/wheels in service code. |
| `app:sync-bavaria` | `BavariaSync` | Baz-on parts CSV and wheel/tire CSV | Windows-1251 CSV, `;` delimiter | parts `30`; tire/wheel `31,32` | CSV `Артикул`, or comma-joined grouped ids for grouped parts | Replaces some makes with default `bmw`; supports tire/wheel fields; tire/wheel price always set from feed. |
| `app:sync-shinabar` | `ShinabarSync` | Baz-on tire/wheel CSV `https://baz-on.ru/export/c1750/bee92/mashina-wheels.csv` | Windows-1251 CSV, `;` delimiter | old type ids `30..37` | CSV `Артикул` | Practically tire-focused: wheel required fields are commented out. Title/description generated from tire manufacturer/dimensions/wear. |
| `app:sync-avtoinstall` | `AvtoinstallSync` | CSV `https://avtoinstall.kg/csvprice_pro/2024-04-11_1712816810_data.csv` | CSV, `;` delimiter | old type ids `30..37` | `_ID_` | Filters `_STOCK_STATUS_ != В наличии` and `_STATUS_ != 1`; type `33`; images include main photo and gallery as `index|url`; supports special price window. |
| `app:sync-allmotors` | `AllmotorsSync` | HTML crawler `https://allmotors.kg/categories/...` | Guzzle + DomCrawler, up to 500 pages per category | old type ids `30..37` | Product slug from `/products/<slug>` | Category slug maps to old type id. Images are proxied through `https://www.mashina.kg/sync/files?...`. Tires parse dimensions from title. |
| `app:sync-autoshina` | `AutoshinaSync` | HTML crawler `https://autoshina.kg/products?...` | Guzzle + DomCrawler, up to 500 pages | old type id `31` | Product id from `/products/<id>` | Tire-only. Requires image, brand, model, width, height, size. Season defaults to summer if missing. |
| `app:sync-detalkg` | `DetalKgSync` | YML/XML parts feed plus HTML tire category crawler | XML decoder + Guzzle/DomCrawler | parts `30`; tires `31` | Parts `@id`; tires parsed `артикул` from detail table | Parts filter `count == 0`; parts price gets +20%; tire pages parse specs, price, description, images. |
| `app:sync-toyota` | `AutocrmSync` | AutoCRM XML `isUsed=0` Toyota feed | XML decoder | cars `1` | VIN | New Toyota cars. Preserves current description and price on update; diffs images separately. |
| `app:sync-toyota-tradein` | `AutocrmSync` | AutoCRM XML `isUsed=1` Toyota feed | XML decoder | cars `1` | VIN | Trade-in cars. Gets dealer currency rate and converts price when currency id is `2`; preserves current price/old_price. |
| `app:sync-lexus` | `AutocrmSync` | AutoCRM XML Lexus feed | XML decoder | cars `1` | VIN | Forces missing make/model in Lexus-specific cases; preserves current price; diffs images separately. |
| `app:sync-kia` | `AutocrmSync` | AutoCRM XML Kia feed | XML decoder | currently `[]` because current API read is commented | VIN; then unique de-dupe by modification + complectation | Contains debug `print_r(...); exit;` before writes. In its current state it does not complete sync writes. |

## Provider Validation And Filtering

| Provider group | Validation/filtering behavior |
|---|---|
| Baz-on parts CSV | `sanitizeEntry()` requires configured required fields and non-empty photos. Photos split by `, `, most services cap at 12. Missing make/model mapping logs an error but does not always skip parts rows. |
| Baz-on tire/wheel CSV | Requires article and tire/wheel basic fields depending on provider. Missing tire dimensions usually logs errors; some services still return payload unless a critical wheel type is missing. |
| Avtoinstall | Requires `_ID_`, `_NAME_`, available stock, active status. Missing gallery falls back to main photo. |
| AutoCRM | Requires VIN and images. Cars are skipped on unresolved make/model/generation/body/fuel/transmission/gearbox/modification/steering/color. |
| HTML crawlers | Missing product detail, image, title, price/spec fields causes page/item to be skipped. Network exceptions are logged and page/item returns empty/null. |
| Detal parts | Skips unavailable rows where `count == '0'`. |

## Known Legacy Weak Spots

- The source of truth is provider feeds and old internal API state, not old DB tables.
- No retries, backoff, timeout tuning, or per-record exception isolation beyond ad hoc `try/catch`.
- `ApiClient::request()` assumes caught exceptions have `getResponse()`.
- Provider-specific logic is split between command and service classes.
- A lot of data is encoded as old numeric ids from `SyncData` and old public API reference data.
- Multi-row grouped parts change `external_id` to comma-joined article ids; this complicates idempotency if grouping changes.
- Kia command currently has debug output and `exit`, so it is not a production-safe sync flow as written.
- Deletes are based solely on absence from the latest provider feed.

