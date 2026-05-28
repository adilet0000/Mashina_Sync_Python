# Legacy PHP Audit

## Summary

The legacy Symfony/PHP project does not contain real Doctrine entities, model classes, repositories, migrations, or local business SQL for ads. The sync logic uses runtime associative arrays defined by `BaseSync::FIELD_*`, reads provider feeds/API endpoints, compares them with current ads returned by an old internal API, and writes back through old API endpoints.

No old database tables are mapped in the PHP codebase. The effective legacy model is the `Ad` array plus related `Image`, `Dealer/User`, and `ReferenceData` arrays.

## Entity Table

| Entity | PHP class/file | Old table | Used fields | Relations | Used in | Notes |
|---|---|---|---|---|---|---|
| Doctrine Entity | `src/Entity` | None | None | None | Not used | Directory contains only `.gitignore`; no `@ORM`, attributes, XML/YAML mappings found. |
| Repository | `src/Repository` | None | None | None | Not used | Directory contains only `.gitignore`; no `ServiceEntityRepository` or custom repositories found. |
| Migration | `migrations`, `src/Migrations` | None | None | None | Not used | Only `.gitignore`; no schema migrations for legacy data. |
| `Ad` runtime array | `src/Service/Sync/BaseSync.php`, provider services in `src/Service/Sync/*Sync.php` | Old API entity, no local table | `id`, `external_id`, `type_id`, `name`, `description`, `price`, `old_price`, `currency`, `region`, `town`, `make`, `model`, `year`, `body`, `generation`, `fuel`, `transmission`, `gear_box`, `modification`, `complectation`, `steering_wheel`, `color`, `mileage`, `customs`, `vincode`, `condition`, `phone`, `images`, `external_images`, `tire_*`, `wheel_*`, flags | Logical relation to dealer/user, type/category, reference data, images | All sync commands and services | Main legacy data model. Built from CSV/XML/YML/HTML feeds and compared by `external_id`. |
| `Image` runtime array | `BaseSync::FIELD_IMAGES`, `AutocrmSync::compareImages()` | Old API image entity, no local table | URL, `index|url`, old API `image_id` for current images | Belongs to `Ad` | AutoCRM image sync; generic ad creation | New catalog target maps this to `images.external_url`, `priority`, `hash`. |
| `Dealer/User` API response | `BaseSync::getUser()` | Old API user/dealer, no local table | `dealer.status`, `phones` | Owns ads; supplies contacts | Every sync command validates active dealer | In catalog mode this is replaced by env `SYNC_CATALOG_USER_ID_*`; phone fallback is global `SYNC_CATALOG_PHONES`. |
| `ReferenceData` API/static arrays | `BaseSync::getData()`, `getCarData()`, `SyncData.php` | Old API reference data, no local table | make/model/body/generation/fuel/transmission/gearbox/modification/color/tire/wheel IDs | Used by `Ad` fields | `AutocrmSync`, tire/wheel providers, parts providers | New DB uses `attributes` and `attribute_options`, often via `old_mysql_id`. |
| Sync command/run | `src/Command/*SyncCommand.php`, `SyncLog.php` | None | parsed counts, create/update/delete counts, errors | Calls provider sync service | All `app:sync-*` commands | Operational behavior only; logs to `var/log/sync.log`. |
| Drive community post | `src/Command/DriveParseCommand.php`, `src/Service/DriveService.php` | Old community API entity, no local table | post/media payload | Community posts/media | `app:parse-drive` | Separate from catalog ads sync; not part of current migration scope unless requested. |

## Legacy Runtime Model: `Ad`

Defined by constants in `src/Service/Sync/BaseSync.php`:

- `id`
- `bypass_time_limit`
- `bypass_normalize_name`
- `region`
- `town`
- `type_id`
- `moderated`
- `price`
- `old_price`
- `currency`
- `comment_allowed`
- `external_id`
- `external_images`
- `featured_option`
- `make`
- `model`
- `year`
- `body`
- `generation`
- `fuel`
- `transmission`
- `gear_box`
- `modification`
- `complectation`
- `steering_wheel`
- `color`
- `mileage`
- `customs`
- `vincode`
- `images`
- `phone`
- `name`
- `description`
- `condition`
- `tire_width`
- `tire_height`
- `tire_size`
- `tire_type`
- `wheel_type`
- `wheel_size`
- `wheel_pcd`

## Legacy Type IDs

| Old `type_id` | Meaning inferred from code | Main files |
|---:|---|---|
| `1` | Cars | `AutocrmSync.php`, Toyota/Lexus/Kia commands |
| `30` | Parts | `AutohubSync.php`, `AutolandSync.php`, `BavariaSync.php`, `BanzaimotorsSync.php`, `DetalKgSync.php`, `OkayamaomskSync.php`, `ShredderSync.php` |
| `31` | Tires | `AutoshinaSync.php`, `AllmotorsSync.php`, `BavariaSync.php`, `BanzaimotorsSync.php`, `DetalKgSync.php`, `ShinabarSync.php` |
| `32` | Wheels/disks | `BavariaSync.php`, `BanzaimotorsSync.php`, `ShinabarSync.php` |
| `33` | Accessories/multimedia | `AvtoinstallSync.php` |
| `36` | Commercial parts | `AutohubSync.php`, `ShredderSync.php` |

## Sync Scripts

| Command | Service | Source | Data |
|---|---|---|---|
| `app:sync-allmotors` | `AllmotorsSync` | HTML crawler `allmotors.kg` | parts, tires, accessories |
| `app:sync-autohub` | `AutohubSync` | CSV feed | parts, commercial parts |
| `app:sync-autoland` | `AutolandSync` | CSV feed | parts |
| `app:sync-autoshina` | `AutoshinaSync` | HTML crawler `autoshina.kg` | tires |
| `app:sync-avtoinstall` | `AvtoinstallSync` | CSV feed | accessories/multimedia |
| `app:sync-banzaimotors` | `BanzaimotorsSync` | CSV feeds | parts, tires, wheels |
| `app:sync-bavaria` | `BavariaSync` | CSV feeds | parts, tires, wheels |
| `app:sync-detalkg` | `DetalKgSync` | YML + HTML crawler | parts, tires |
| `app:sync-kia` | `AutocrmSync` | AutoCRM XML | Kia cars; contains legacy debug `print_r/exit` behavior |
| `app:sync-lexus` | `AutocrmSync` | AutoCRM XML | Lexus cars + images |
| `app:sync-okayamaomsk` | `OkayamaomskSync` | CSV feed | parts |
| `app:sync-shinabar` | `ShinabarSync` | CSV feed | tires, wheels |
| `app:sync-shredder` | `ShredderSync` | CSV feed | parts, commercial parts |
| `app:sync-toyota` | `AutocrmSync` | AutoCRM XML | new Toyota cars + images |
| `app:sync-toyota-tradein` | `AutocrmSync` | AutoCRM XML | Toyota trade-in cars + images |
| `app:parse-drive` | `DriveService` | Drive2 HTML crawler | community posts/media; separate from catalog migration |

## Business Logic

- Validate provider dealer through old API `self/info`.
- Fetch current ads from old API `sync/ads`, indexed by `external_id`.
- Read provider feed from CSV/XML/YML/HTML.
- Normalize/sanitize each feed entry.
- Map provider-specific fields to `Ad` fields.
- Map make/model/reference values through `SyncData.php` and old public data APIs.
- Group duplicate feed rows into one ad for several parts providers.
- Compare by provider-specific `$compareFields`.
- Create/update/delete ads in old API.
- For AutoCRM, compare image lists and create/delete images separately.

## Data That Can Be Ignored In Python Rewrite Initially

- Symfony controllers/UI.
- Twig/frontend/webpack assets.
- Doctrine ORM setup, because no entities are present.
- Mailer/security config unless Python app needs them later.
- Drive community parser unless community posts are in migration scope.
