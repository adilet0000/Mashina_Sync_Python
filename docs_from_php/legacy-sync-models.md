# Legacy Sync Runtime Models

This document describes the practical legacy "models" used by the PHP sync scripts. They are not Doctrine entities. The sync layer builds associative arrays at runtime, using `BaseSync::FIELD_*` keys, provider feed rows, and old internal API responses.

## Logical Entities

| Logical entity | Defined by | Source files | Fields | Unique key | Used by scripts | Notes |
|---|---|---|---|---|---|---|
| `Ad` | `BaseSync::FIELD_*` associative array | `src/Service/Sync/BaseSync.php`, all `src/Service/Sync/*Sync.php` | `id`, `external_id`, `type_id`, `name`, `description`, `price`, `currency`, `condition`, `images`, provider-specific vehicle/tire/wheel fields | `external_id` inside provider/account scope | All `app:sync-*` commands | Main runtime model sent to old API create/update endpoints. |
| `ProviderAd` | Raw provider row/XML node/HTML product page | Provider services and commands | Provider-specific fields such as CSV headers, XML tags, scraped DOM values | Provider article/VIN/product slug | Provider parsers | Raw input is sanitized and normalized into `Ad`. |
| `SyncAdPayload` | `bulkCreateAds()`, `bulkUpdateAds()` request body | `src/Service/Sync/BaseSync.php` | `{ ads: [Ad, ...] }`; update payload includes `id` | `id` for update, `external_id` for create comparison | All sync commands | Payload shape for old internal API. |
| `CurrentAdFromOldApi` | `getPartAds()`, `getTireAds()`, `getAutoAds()` response list | `src/Service/Sync/BaseSync.php` | Requested compare fields plus `id`, `external_id`, sometimes `images` | Response array key is expected to be `external_id` | All commands before create/update/delete decision | Source of current state in old implementation. For Python rewrite this becomes current rows from new DB. |
| `AdImage` | `FIELD_IMAGES` and old image API | `BaseSync.php`, `AutocrmSync.php`, provider services | Provider image URL, optional `index|url`, old API `image_id` in current ad image map | URL within ad | AutoCRM image diff; generic ad create | AutoCRM compares image URLs separately and calls image bulk endpoints. |
| `AdLocation` | `FIELD_REGION`, `FIELD_TOWN` | `BaseSync.php`, `OkayamaomskSync.php` | Region id, town id | None | All created ads via defaults; Okayama overrides | Defaults are old reference ids: region `1`, town `2`; Okayama uses `9`/`62`. |
| `AdPrice` | `FIELD_PRICE`, `FIELD_OLD_PRICE`, `FIELD_CURRENCY` | Provider mappers | Numeric price, old price, old currency id | None | Compare/update in many providers | Currency `1` is used for KGS in most providers; AutoCRM commands also use `2` and currency rate conversion for trade-in/Kia. |
| `ProviderStatus` | Provider availability/status fields | Provider `sanitizeEntry()` and mappers | Availability/status text or numeric flags | None | Filtering and featured/stock mapping | Most CSV providers only require non-empty status; Avtoinstall and Detal actively filter unavailable rows. AutoCRM maps availability to `featured_option`. |
| `DealerUser` | Old API `self/info` response | `BaseSync::getUser()` | `dealer.status`, `phones` | API token/account | Every sync command | Commands abort unless token is valid and dealer status is `1`; phones are copied into created/updated ads. |
| `ReferenceData` | Old public data API and `SyncData` static maps | `BaseSync::getData()`, `getCarData()`, `getVincodeData()`, `SyncData.php` | make/model/body/generation/fuel/transmission/gearbox/modification/color/tire/wheel ids | Old reference ids | AutoCRM and provider normalization | Not persisted locally. It is used to convert provider text to old reference ids. |
| `TireWheelSpec` | Tire/wheel fields on `Ad` | `AutoshinaSync.php`, `AllmotorsSync.php`, `DetalKgSync.php`, `ShinabarSync.php`, `BavariaSync.php`, `BanzaimotorsSync.php` | `tire_width`, `tire_height`, `tire_size`, `tire_type`, `wheel_type`, `wheel_size`, `wheel_pcd` | Part of ad content, not unique | Tire/wheel providers | Required for tire ads; wheel fields are partial and often optional. |
| `SyncResult` | Command-local counters and logs | `src/Command/*SyncCommand.php`, `SyncLog.php` | counts of parsed rows, create/update/delete/image actions, execution time, errors | Command run | Console commands | Not a persisted entity. Logged to `var/log/sync.log`. |

## BaseSync Field Definitions

| Field constant | Runtime key | Meaning | Required | Default / fallback | Used in | Transformations and notes |
|---|---|---|---|---|---|---|
| `FIELD_ID` | `id` | Old internal ad id/current row id | Required only for update/delete | Set from current API response before update/delete | All commands | Added to update payload after matching by `external_id`. |
| `FIELD_BYPASS_TIME_LIMIT` | `bypass_time_limit` | Old API processing hint | Optional | `true` from `getDefaultFields()` | All created ads | Never read by sync code after default assignment. |
| `FIELD_BYPASS_NORMALIZE_NAME` | `bypass_normalize_name` | Old API name normalization flag | Optional | No global default; many providers set `true` | AutoCRM, tire/wheel, HTML providers, Detal | Prevents old API from normalizing generated names. |
| `FIELD_REGION` | `region` | Old region reference id | Optional | `1`; Okayama sets `9` | All ad payloads via default | New rewrite should not rely on old region ids without mapping. |
| `FIELD_TOWN` | `town` | Old town reference id | Optional | `2`; Okayama sets `62` | All ad payloads via default | New rewrite should map/replace old city ids. |
| `FIELD_TYPE_ID` | `type_id` | Old ad category/type id | Required for create | Provider mapper sets it | All providers | Known ids: `1` cars, `30` parts, `31` tires, `32` wheels, `33` accessories/multimedia, `36` commercial parts. |
| `FIELD_MODERATED` | `moderated` | Old moderation/status flag | Optional | `1` from defaults | All created ads | Not provider-derived in legacy code. |
| `FIELD_PRICE` | `price` | Price | Conditional | Often provider price; sometimes `0`; Bavaria parts may omit when import disabled | Compare/update/create | Detal parts add 20%; AutoCRM trade-in can divide by dealer currency rate; Avtoinstall may set special price. |
| `FIELD_OLD_PRICE` | `old_price` | Previous/original price | Optional | Usually absent or `null` | Avtoinstall, ToyotaTradein current fields | Avtoinstall sets when active special price is lower than regular price. |
| `FIELD_CURRENCY` | `currency` | Old currency id | Conditional | Usually `1`; AutoCRM commands can set `1` or `2` | Compare/update/create | For non-`1` AutoCRM, price is divided by `currencyRate`. |
| `FIELD_COMMENT_ALLOWED` | `comment_allowed` | Old comment setting | Optional | `3`; Avtoinstall and Okayama set `2`; AutoCRM sets `3` | Create/update payloads | No provider input except hardcoded values. |
| `FIELD_EXTERNAL_ID` | `external_id` | Provider identifier used for idempotency | Required | Provider article/VIN/product slug; grouped ads join ids with commas | All providers | Primary comparison key against current ads. |
| `FIELD_EXTERNAL_IMAGES` | `external_images` | Legacy placeholder for external image data | Not used | None | No active provider use found | Defined in `BaseSync` but not populated in current sync services. |
| `FIELD_FEATURED_OPTION` | `featured_option` | Old stock/featured/availability option | Optional | `1`; Okayama sets `2`; AutoCRM maps availability | AutoCRM, tire/wheel, defaults | AutoCRM also derives `customs` from this value. |
| `FIELD_MAKE` | `make` | Old make reference id | Required for cars, optional for parts | Mapped through `SyncData`/old `public/data` | AutoCRM, parts providers, Allmotors | Missing make is logged; cars abort row on missing make. |
| `FIELD_MODEL` | `model` | Old model reference id | Required for cars, optional for parts | Mapped through `SyncData`/old `public/data` | AutoCRM, parts providers, Allmotors | Missing model is logged; cars abort row on missing model. |
| `FIELD_YEAR` | `year` | Vehicle year | Required for AutoCRM cars | Provider XML value | AutoCRM | Used to query `public/data/car`. |
| `FIELD_BODY` | `body` | Body type id | Required for AutoCRM cars | Inferred from `public/data/car`, provider body, and door count | AutoCRM | Door count remaps generic body ids to more specific ids. |
| `FIELD_GENERATION` | `generation` | Generation id | Required for AutoCRM cars | Inferred from `public/data/car` by model/year/name | AutoCRM | Parts providers use generation text only in names/descriptions/grouping, not as BaseSync field. |
| `FIELD_FUEL` | `fuel` | Fuel type id | Required for AutoCRM cars | Defaults provider engine to `Бензин`; maps `ГБО` custom | AutoCRM | Row is skipped if no id can be resolved. |
| `FIELD_TRANSMISSION` | `transmission` | Drive/transmission id | Required for AutoCRM cars | Inferred from car data or defaults provider drive to `Передний` | AutoCRM | Row is skipped if unresolved. |
| `FIELD_GEAR_BOX` | `gear_box` | Gearbox id | Required for AutoCRM cars | Inferred from car data or provider gearbox/custom map | AutoCRM | Multi-option fallback prefers old ids `2`, `4`, `5`, `1`. |
| `FIELD_MODIFICATION` | `modification` | Vehicle modification id | Required for AutoCRM cars | Inferred from car data, nearest engine volume | AutoCRM | Row is skipped if unresolved. |
| `FIELD_COMPLECTATION` | `complectation` | Trim/complectation text | Optional | Provider XML value | AutoCRM; Kia de-dup key | Kia unique filtering uses modification + complectation. |
| `FIELD_STEERING_WHEEL` | `steering_wheel` | Steering wheel id | Required for AutoCRM cars | Mapped from provider wheel with custom map | AutoCRM | Row is skipped if unresolved. |
| `FIELD_COLOR` | `color` | Color id | Required for AutoCRM cars | Defaults to `Серебряный`; custom color map | AutoCRM | Row is skipped if unresolved. |
| `FIELD_MILEAGE` | `mileage` | Mileage/run | Optional | Provider `run` when present | AutoCRM | No numeric normalization besides direct assignment. |
| `FIELD_CUSTOMS` | `customs` | Customs cleared flag | Optional | AutoCRM sets `1` if `featured_option == 1`, else `0` | AutoCRM | This is a legacy business rule, not provider field. |
| `FIELD_VINCODE` | `vincode` | VIN code | Optional but present for cars | Same as AutoCRM `vin` | AutoCRM | Also used as `external_id`. |
| `FIELD_IMAGES` | `images` | Image list or current image map | Required for most creates | Provider image URLs; sometimes `index|url`; current API returns `url => image_id` map | All providers; image API for AutoCRM | CSV photos split by `, ` and often capped to 12. AutoCRM/Avtoinstall prefix image order as `index|url`. |
| `FIELD_PHONE` | `phone` | Contact phones | Required in created payloads | From old API `self/info` user phones | All providers | No normalization in sync code. |
| `FIELD_NAME` | `name` | Ad title | Required | Provider title or generated from dimensions/make/model | All providers | Some providers ignore name in equality check; generated names use tire/wheel specs. |
| `FIELD_DESCRIPTION` | `description` | Ad description | Required | Provider description/comment or generated details | All providers | Often concatenates provider fields. Some AutoCRM commands preserve old API description on update. |
| `FIELD_CONDITION` | `condition` | Item condition id | Conditional | Parts usually `1`; new items `2`; AutoCRM set by command | All providers | Tire/wheel providers map text through `SyncData::getTireWheelCondition()`. |
| `FIELD_TIRE_WIDTH` | `tire_width` | Tire width id | Required for tire ads | Parsed/mapped from feed or page | Autoshina, Allmotors tire category, Detal tires, Shinabar, Bavaria/Banzai tire feed | Missing required tire params skips row/page in several providers. |
| `FIELD_TIRE_HEIGHT` | `tire_height` | Tire height id | Required for tire ads | Parsed/mapped from feed or page | Tire providers | Same validation as width. |
| `FIELD_TIRE_SIZE` | `tire_size` | Tire rim diameter id | Required for tire ads | Parsed/mapped from feed/page | Tire providers | Often parsed from `Rxx`. |
| `FIELD_TIRE_TYPE` | `tire_type` | Season/type id | Required for tire ads | `1` summer fallback in some providers; custom maps | Tire providers | Autoshina maps `зима`=2, `лето`=1, `в/с`=3; Detal handles spikes. |
| `FIELD_WHEEL_TYPE` | `wheel_type` | Wheel disk type id | Optional/conditional | Mapped from wheel feed if present | Bavaria, Banzaimotors | Unknown wheel type may skip Banzai/Bavaria wheel row. |
| `FIELD_WHEEL_SIZE` | `wheel_size` | Wheel diameter id | Optional/conditional | Mapped from wheel feed if present | Bavaria, Banzaimotors | Logged if unresolved. |
| `FIELD_WHEEL_PCD` | `wheel_pcd` | Wheel bolt pattern id | Optional/conditional | Mapped from wheel feed if present | Bavaria, Banzaimotors | Banzai splits on comma and uses first PCD. |

## Runtime Comparison Rules

| Provider/service | Compare fields | Fields intentionally ignored/preserved |
|---|---|---|
| AutoCRM cars (`Toyota`, `ToyotaTradein`, `Lexus`, `Kia`) | Command-specific `setCompareFields()` | Toyota preserves current description and price on update; Lexus preserves current price; ToyotaTradein preserves current price/old_price and skips update for VIN `WBACW010109C49929`; Kia currently has debug `print_r/exit` and does not reach writes. |
| Parts CSV providers (`Autohub`, `Autoland`, `Shredder`, `Okayamaomsk`, `Banzaimotors`, `Bavaria`) | Usually `name`, `description`, `make`, `model`, sometimes `currency`, `price` | Several `adsEqual()` implementations skip `name`; Bavaria compares `name`. Price compare is disabled by omitting price from compare fields in Autoland/Bavaria. |
| Tire providers (`Autoshina`, `Allmotors`, `Detal`, `Shinabar`, Banzai/Bavaria tire feeds) | `name`, `description`, tire dimensions/type, `currency`, `price` | Missing tire required params skips the item. |
| Accessories (`Avtoinstall`, Allmotors accessories categories) | `name`, `description`, `currency`, `price`, `old_price` for Avtoinstall | Avtoinstall skips `name` in equality check and filters unavailable/inactive rows. |

