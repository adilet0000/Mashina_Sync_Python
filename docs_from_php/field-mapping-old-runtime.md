# Old Runtime Field Mapping

This document maps provider inputs to `BaseSync::FIELD_*` runtime fields used by the PHP sync scripts. It intentionally does not describe Doctrine entities, because the legacy sync layer does not use Doctrine models for ads.

## Provider Field Mapping

| Provider | Provider field | BaseSync FIELD_* | Transformation | Required | Notes |
|---|---|---|---|---|---|
| Base defaults | none | `FIELD_BYPASS_TIME_LIMIT` | Set to `true` by `getDefaultFields()` | No | Included on all new runtime payloads. |
| Base defaults | none | `FIELD_REGION` | Default `1` | No | Okayama overrides. |
| Base defaults | none | `FIELD_TOWN` | Default `2` | No | Okayama overrides. |
| Base defaults | none | `FIELD_MODERATED` | Default `1` | No | Provider-independent. |
| Base defaults | none | `FIELD_COMMENT_ALLOWED` | Default `3` | No | Some providers override to `2`. |
| Base defaults | none | `FIELD_FEATURED_OPTION` | Default `1` | No | AutoCRM/Okayama override. |
| Autohub | `Артикул` | `FIELD_EXTERNAL_ID` | Trimmed string | Yes | If grouped, multiple ids are joined by comma. |
| Autohub | `Марка` | `FIELD_TYPE_ID`, `FIELD_MAKE` | Commercial makes `setra/neoplan/man` map to type `36`; otherwise type `30` and make id via `SyncData::getMakeId()` | Yes | Missing make id is logged but row can still return payload. |
| Autohub | `Модель` | `FIELD_MODEL` | `SyncData::getModelId()` with custom make/model map | Yes | Only mapped when make id exists. |
| Autohub | `Наименование`, `Кузов` | `FIELD_NAME` | Name plus generation for non-commercial parts; name plus make/model for commercial parts | Yes | `FIELD_NAME` is ignored in equality comparison. |
| Autohub | `Наименование`, `Марка`, `Модель`, `Кузов`, `Двигатель`, `Год`, `Верх/Низ`, `Перед/Зад`, `Лев/Прав`, `Цвет`, `Комментарий` | `FIELD_DESCRIPTION` | Concatenated text; grouped ads enumerate each row | Mixed | Description is compared. |
| Autohub | `Фото` | `FIELD_IMAGES` | Split by `, `, capped to 12 | Yes | Empty/missing photos skip row. |
| Autohub | `Цена` | `FIELD_PRICE`, `FIELD_CURRENCY` | Price imported only if `$importPrice=true`; currently false, so price `0`, currency `1` | No | Compare fields include price/currency. |
| Autohub | none | `FIELD_CONDITION`, `FIELD_PHONE` | Condition hardcoded `1`; phones from `self/info` | No | Status field is not mapped. |
| Autoland | `Артикул` | `FIELD_EXTERNAL_ID` | Trimmed string; grouped ids joined by comma | Yes | Grouping by name/make/model. |
| Autoland | `Марка`, `Модель` | `FIELD_MAKE`, `FIELD_MODEL` | `SyncData` mapping with provider custom map | `Марка` yes, `Модель` optional in sanitizer | Compare fields include make/model. |
| Autoland | `Наименование` | `FIELD_NAME` | Direct title | Yes | Equality skips `FIELD_NAME`. |
| Autoland | `Комментарий` or `Наименование` | `FIELD_DESCRIPTION` | Comment if present, otherwise name; grouped ads enumerate rows | No | Description is compared. |
| Autoland | `Фото` | `FIELD_IMAGES` | Split by `, ` | Yes | Empty photos skip row. |
| Autoland | `Новый/БУ`, `Наименование` | `FIELD_CONDITION` | `2` only when condition is `Новый` and name is `Товары из Дордоя`, otherwise `1` | No | Legacy hardcoded rule. |
| Autoland | `Цена` | `FIELD_PRICE`, `FIELD_CURRENCY` | Direct price, currency `1` | No | Price not in compare fields for Autoland. |
| Shredder | `Артикул` | `FIELD_EXTERNAL_ID` | Trimmed string; grouped ids joined by comma | Yes | Similar to Autohub. |
| Shredder | `Марка` | `FIELD_TYPE_ID`, `FIELD_MAKE` | Commercial makes use type `36`; otherwise type `30` and `SyncData` make id | Yes | Missing required field causes skip. |
| Shredder | `Модель` | `FIELD_MODEL` | `SyncData::getModelId()` | Yes | Missing model mapping logs error. |
| Shredder | `Наименование`, `Марка`, `Модель`, `Кузов`, `Двигатель`, `Год`, position fields, `Цвет`, `Комментарий` | `FIELD_NAME`, `FIELD_DESCRIPTION` | Generated title/description | Mixed | Name is ignored in equality. |
| Shredder | `Фото` | `FIELD_IMAGES` | Split by `, `, capped to 12 | Yes | Empty photos skip row. |
| Shredder | `Цена` | `FIELD_PRICE`, `FIELD_CURRENCY` | `$importPrice=false`, so price `0`, currency `1` | No | Compare fields include price/currency. |
| Okayamaomsk | `Артикул` | `FIELD_EXTERNAL_ID` | Trimmed string | Yes | No grouping. |
| Okayamaomsk | `Марка`, `Модель` | `FIELD_MAKE`, `FIELD_MODEL` | `SyncData` mapping with provider custom map | Yes | Missing mapping is logged. |
| Okayamaomsk | none | `FIELD_REGION`, `FIELD_TOWN`, `FIELD_FEATURED_OPTION`, `FIELD_COMMENT_ALLOWED` | Hardcoded region `9`, town `62`, featured `2`, comments `2` | No | Distinguishes Okayama account/location. |
| Okayamaomsk | `Наименование`, `Кузов` | `FIELD_NAME` | Name plus generation | Yes name | Name ignored in equality. |
| Okayamaomsk | Many part fields plus static delivery/payment text | `FIELD_DESCRIPTION` | Generated multi-line description | Mixed | Includes article and long informational text. |
| Okayamaomsk | `Фото` | `FIELD_IMAGES` | Split by `, `, capped to 12 | Yes | Empty photos skip row. |
| Okayamaomsk | `Цена` | `FIELD_PRICE`, `FIELD_CURRENCY` | Direct price, currency `1` | No | Price is compared. |
| Banzaimotors parts | `Артикул` | `FIELD_EXTERNAL_ID` | Trimmed string | Yes | Parts feed only; no grouping in command. |
| Banzaimotors parts | `Марка`, `Модель` | `FIELD_MAKE`, `FIELD_MODEL` | `SyncData` mapping with custom map | Yes | Type hardcoded `30`. |
| Banzaimotors parts | `Наименование`, `Кузов`, other part fields | `FIELD_NAME`, `FIELD_DESCRIPTION` | Generated text | Mixed | Compare fields include make/model, price/currency. |
| Banzaimotors parts | `Фото` | `FIELD_IMAGES` | Split by `, `, capped to 12 | Yes | Empty photos skip row. |
| Banzaimotors parts | `Цена` | `FIELD_PRICE`, `FIELD_CURRENCY` | `$importPrice=false`, so price `0`, currency `1` | No | Same service flag also affects tire/wheel price path. |
| Banzaimotors tire/wheel | `Тип (диск, шина, колесо)` | `FIELD_TYPE_ID` | `шина` => `31`, all other supported types => `32` | Yes for wheel feed processing | Command skips rows without this field. |
| Banzaimotors tire/wheel | `Артикул` | `FIELD_EXTERNAL_ID` | Trimmed string | Yes | Main idempotency key. |
| Banzaimotors tire/wheel | `Тип диска`, `Диаметр диска`, `PCD диска` | `FIELD_WHEEL_TYPE`, `FIELD_WHEEL_SIZE`, `FIELD_WHEEL_PCD` | Mapped through `SyncData`, with replacement maps and first PCD value | Conditional | Unknown wheel type returns null; other unknown wheel attrs log errors. |
| Banzaimotors tire/wheel | `Ширина профиля шины`, `Высота профиля шины`, `Посадочный диаметр шины`, `Сезон шины...` | `FIELD_TIRE_WIDTH`, `FIELD_TIRE_HEIGHT`, `FIELD_TIRE_SIZE`, `FIELD_TIRE_TYPE` | Mapped through `SyncData`, season custom map | Conditional for tires | Missing attrs log errors. |
| Banzaimotors tire/wheel | `Новое/БУ` | `FIELD_CONDITION` | `SyncData::getTireWheelCondition()` | Conditional | Missing condition logs error. |
| Banzaimotors tire/wheel | tire/wheel manufacturer/style/wear/year/comment | `FIELD_NAME`, `FIELD_DESCRIPTION` | Generated tire/wheel text | Mixed | `FIELD_FEATURED_OPTION=1`. |
| Banzaimotors tire/wheel | `Фото` | `FIELD_IMAGES` | Split by `, `, capped to 12 | Yes | Empty photos skip row. |
| Banzaimotors tire/wheel | `Цена` | `FIELD_PRICE`, `FIELD_CURRENCY` | `$importPrice=false`, so price `0`, currency `1` | No | Legacy code does not import tire/wheel price here. |
| Bavaria parts | `Артикул` | `FIELD_EXTERNAL_ID` | Trimmed string; grouped ids joined by comma | Yes | Grouping by name/make/model/year/generation. |
| Bavaria parts | `Марка` | `FIELD_MAKE` | Replace `depo`, `bosch`, `дубликат` with default `bmw`; then `SyncData` mapping | Yes | Type `30`, bypass name normalization. |
| Bavaria parts | `Модель` | `FIELD_MODEL` | `SyncData` mapping; known unknown model names can leave model null without logging | Yes | Compare fields include make/model, not price. |
| Bavaria parts | `Наименование`, `Кузов`, `Номер`, other part fields | `FIELD_NAME`, `FIELD_DESCRIPTION` | Generated title/description; year trailing `-` stripped in descriptions | Mixed | Bavaria equality compares `FIELD_NAME`. |
| Bavaria parts | `Фото` | `FIELD_IMAGES` | Split by `, `, capped to 12 | Yes | Empty photos skip row. |
| Bavaria parts | `Цена` | `FIELD_PRICE`, `FIELD_CURRENCY` | `$importPrice=false`; service does not set price/currency for parts when false | No | Price/currency not compared for Bavaria parts. |
| Bavaria tire/wheel | `Тип (диск, шина, колесо)` | `FIELD_TYPE_ID` | `шина` => `31`, other supported wheel types => `32` | Yes | Processed from separate wheel/tire CSV. |
| Bavaria tire/wheel | wheel/tire spec columns | `FIELD_WHEEL_*`, `FIELD_TIRE_*` | Mapped through `SyncData` and custom maps | Conditional | Unknown wheel type returns null; missing tire attrs log errors. |
| Bavaria tire/wheel | `Цена` | `FIELD_PRICE`, `FIELD_CURRENCY` | Direct price, currency `1` | Yes-ish | Tire/wheel path always sets price. |
| Bavaria tire/wheel | `Фото`, `Новое/БУ`, title/comment/spec fields | `FIELD_IMAGES`, `FIELD_CONDITION`, `FIELD_NAME`, `FIELD_DESCRIPTION`, `FIELD_FEATURED_OPTION` | Photos split/capped; condition via `SyncData`; generated title/description; featured `1` | Mixed | Uses same compare fields as Bavaria service, which only include name/description/make/model. |
| Shinabar | `Артикул` | `FIELD_EXTERNAL_ID` | Trimmed string | Yes | Command de-duplicates raw rows by article. |
| Shinabar | `Тип (диск, шина, колесо)` | `FIELD_TYPE_ID` | `шина` => `31`, otherwise `32` | Optional in sanitizer but used by mapper | CSV comments indicate wheel data is not complete. |
| Shinabar | `Ширина профиля шины`, `Высота профиля шины`, `Посадочный диаметр шины`, `Сезон шины...` | `FIELD_TIRE_WIDTH`, `FIELD_TIRE_HEIGHT`, `FIELD_TIRE_SIZE`, `FIELD_TIRE_TYPE` | Mapped through `SyncData`; season custom map | Yes for current required fields | Missing required raw values skips row; unresolved ids log errors. |
| Shinabar | `Новое/БУ` | `FIELD_CONDITION` | `SyncData::getTireWheelCondition()` | Yes | Missing mapping logs error. |
| Shinabar | `Производитель шины`, tire dimensions, season | `FIELD_NAME` | Generated title if name is absent/logic branch triggers | Conditional | Current code uses generated title when `KEY_NAME` is not in entry or non-empty. |
| Shinabar | `Производитель шины`, `Износ шин`, `Количество в комплекте`, `Комментарий` | `FIELD_DESCRIPTION` | Generated description or comment | Conditional | `FIELD_FEATURED_OPTION=1`. |
| Shinabar | `Цена`, `Фото` | `FIELD_PRICE`, `FIELD_CURRENCY`, `FIELD_IMAGES` | Direct price, currency `1`; photos split by `, ` | Photos optional in sanitizer but mapper expects field | Compare fields include price/currency and tire attrs. |
| Avtoinstall | `_ID_` | `FIELD_EXTERNAL_ID` | Trimmed string | Yes | Main key. |
| Avtoinstall | `_STOCK_STATUS_`, `_STATUS_` | none / row filter | Only `_STOCK_STATUS_ == В наличии` and `_STATUS_ == 1` pass | Yes for active row | Unavailable/inactive rows are skipped before mapping. |
| Avtoinstall | `_NAME_` | `FIELD_NAME` | Direct | Yes | Name ignored in equality. |
| Avtoinstall | `_DESCRIPTION_`, `_ATTRIBUTES_` | `FIELD_DESCRIPTION` | Strip tags, collapse line breaks, HTML decode; attributes split by lines and `|` into grouped text | No | Description compared. |
| Avtoinstall | `_IMAGE_`, `_IMAGES_` | `FIELD_IMAGES` | Main image plus gallery; URL filename encoded; output as `index|url` | At least one image | Empty gallery falls back to main photo. |
| Avtoinstall | `_PRICE_`, `_SPECIAL_` | `FIELD_PRICE`, `FIELD_OLD_PRICE`, `FIELD_CURRENCY` | Direct price; if special window active and special lower, price=special, old_price=regular; currency `1` | No | Dates interpreted in `Asia/Bishkek`. |
| Avtoinstall | none | `FIELD_TYPE_ID`, `FIELD_COMMENT_ALLOWED`, `FIELD_CONDITION`, `FIELD_FEATURED_OPTION`, `FIELD_PHONE` | Type `33`, comments `2`, condition `2`, featured `1`, phones from old API | No | Accessories/multimedia. |
| Allmotors | category slug | `FIELD_TYPE_ID`, `FIELD_CONDITION` | Slug map: tires `31`, many parts `30`, accessories `33`; condition `2` for oils/filters and batteries, else `1` | Yes | Unknown category logs error and falls back to `30`. |
| Allmotors | product URL slug | `FIELD_EXTERNAL_ID` | `/products/<slug>` stripped to slug | Yes | Main key. |
| Allmotors | product gallery links | `FIELD_IMAGES` | Source URL transformed to `https://www.mashina.kg/sync/files?ext=<ext>&url=<base>` | Yes | Missing images skip product. |
| Allmotors | `h1.name` | `FIELD_NAME`, `FIELD_MAKE`, `FIELD_MODEL` | If title contains comma, first part is parsed into make/model via `SyncData`; last comma part becomes name | Yes | Make/model optional depending parse success. |
| Allmotors | tire title pattern | `FIELD_TIRE_WIDTH`, `FIELD_TIRE_HEIGHT`, `FIELD_TIRE_SIZE`, `FIELD_TIRE_TYPE` | Regex `###/##/R##`; season words map to custom ids; default tire type `1` | Required for `shiny-diski` | Missing tire dimensions skip tire product. |
| Allmotors | `span.price` | `FIELD_PRICE`, `FIELD_CURRENCY` | Remove ` сом`; currency `1` | Yes when price import enabled | `$importPrice=true`. |
| Allmotors | description paragraph | `FIELD_DESCRIPTION` | Strip tags; fallback full title | No | Phones from old API. |
| Autoshina | product id from list URL | `FIELD_EXTERNAL_ID` | `/products/<id>` stripped | Yes | Current ads scope is type `31`. |
| Autoshina | image `src` | `FIELD_IMAGES` | Prefix with `https://autoshina.kg` | Yes | Missing image skips product. |
| Autoshina | brand/model headings | `FIELD_NAME` | Brand + model, later appends normalized tire dimensions | Yes | Missing brand/model skips product. |
| Autoshina | param `Ширина` | `FIELD_TIRE_WIDTH` | Parse after `: `, normalize `.00`, `.0`, `.50`, map through `SyncData` | Yes | Missing/unmapped skips product. |
| Autoshina | param `Высота` | `FIELD_TIRE_HEIGHT` | Parse after `: `, map through `SyncData` | Yes | Missing/unmapped skips product. |
| Autoshina | param `Диаметр диска` | `FIELD_TIRE_SIZE` | Parse after `: `, map through `SyncData` | Yes | Missing/unmapped skips product. |
| Autoshina | param `Сезонность` | `FIELD_TIRE_TYPE` | `зима` => `2`, `лето` => `1`, `в/с` => `3`; fallback `1` | No | Missing type defaults to summer. |
| Autoshina | param `Цена` | `FIELD_PRICE`, `FIELD_CURRENCY` | Strip `.00` and commas; currency `1` | Conditional | `$importPrice=true`. |
| Autoshina | description block | `FIELD_DESCRIPTION` | Strip tags | No | Condition hardcoded `2`; type `31`; bypass name normalization. |
| DetalKg parts | offer `@id` | `FIELD_EXTERNAL_ID` | Trimmed XML attribute | Yes | Main parts key. |
| DetalKg parts | offer `count` | none / row filter | `count == '0'` skips row | Yes for active row | Availability is not mapped to field. |
| DetalKg parts | offer `picture` | `FIELD_IMAGES` | Scalar coerced to list; capped to 12 | Yes | Empty photos skip row. |
| DetalKg parts | offer `price` | `FIELD_PRICE`, `FIELD_CURRENCY` | `intval(price + price * 0.2)`, currency `1` | No | Adds 20% markup. |
| DetalKg parts | offer `name` | `FIELD_NAME` | Removes `!`, backslashes, escaped `<`; truncates to 75 chars | Yes | Bypass name normalization. |
| DetalKg parts | offer `description` | `FIELD_DESCRIPTION` | Removes backslashes/`!`, decodes escaped `<` | Yes | Condition `2`, type `30`. |
| DetalKg tires | detail table `артикул` | `FIELD_EXTERNAL_ID` | Parsed from tire spec table | Yes | Returned as array keyed by external id. |
| DetalKg tires | detail table `размерность`, `ширина`, `диаметр`, `сезонность`, `шипы` | `FIELD_TIRE_WIDTH`, `FIELD_TIRE_HEIGHT`, `FIELD_TIRE_SIZE`, `FIELD_TIRE_TYPE` | Maps table labels through `$paramsFields` and `SyncData`; spikes force tire type `шипованные` | Yes | Missing any tire spec skips tire. |
| DetalKg tires | `h1`, spec names | `FIELD_NAME` | Page title plus reconstructed tire size | Yes | Requires title. |
| DetalKg tires | tire description and extra spec rows | `FIELD_DESCRIPTION` | Strip HTML, append unhandled parameters | Yes | Missing description skips tire. |
| DetalKg tires | price block | `FIELD_PRICE`, `FIELD_CURRENCY` | Strip non-digits; currency `1` | Yes | Type `31`, condition `2`, featured `1`. |
| DetalKg tires | image tags | `FIELD_IMAGES` | Prefix site URL; remove `tire_no_photo` images | No | Images are added only if not empty. |
| AutoCRM Toyota/Lexus/Kia/Tradein | `vin` | `FIELD_EXTERNAL_ID`, `FIELD_VINCODE` | Direct VIN | Yes | Main car key and VIN field. |
| AutoCRM Toyota/Lexus/Kia/Tradein | `images.image` | `FIELD_IMAGES` | Scalar coerced to list; output as `index|url` | Yes | Missing images skips row. |
| AutoCRM Toyota/Lexus/Kia/Tradein | `mark_id`, `folder_id` | `FIELD_MAKE`, `FIELD_MODEL` | Old public data lookup; Lexus/Kia fallback from client/VIN; VIN precheck fallback | Yes | Missing resolved ids skips row. |
| AutoCRM Toyota/Lexus/Kia/Tradein | `year`, `modification_id` | `FIELD_YEAR`, `FIELD_GENERATION` | Year direct; generation inferred from `public/data/car` or matched by name | Yes | Missing generation skips row. |
| AutoCRM Toyota/Lexus/Kia/Tradein | `body_type`, `doors_count` | `FIELD_BODY` | Infer body from car data or provider body; door count remaps body ids | Yes | Missing body skips row. |
| AutoCRM Toyota/Lexus/Kia/Tradein | `engine_type` | `FIELD_FUEL` | Default empty to `Бензин`; old reference lookup with custom `ГБО` | Yes | Missing id skips row. |
| AutoCRM Toyota/Lexus/Kia/Tradein | `drive` | `FIELD_TRANSMISSION` | Infer from car data or default empty to `Передний`; old reference lookup | Yes | Missing id skips row. |
| AutoCRM Toyota/Lexus/Kia/Tradein | `gearbox` | `FIELD_GEAR_BOX` | Infer from car data, preferred ids `2`, `4`, `5`, `1`; custom map for text | Yes | Missing id skips row. |
| AutoCRM Toyota/Lexus/Kia/Tradein | `engine_volume` | `FIELD_MODIFICATION` | If multiple modifications, choose closest engine volume in cc to volume parsed from modification name | Yes | Missing modification skips row. |
| AutoCRM Toyota/Lexus/Kia/Tradein | `wheel` | `FIELD_STEERING_WHEEL` | Custom map `левый`=>1, `правый`=>2 | Yes | Missing id skips row. |
| AutoCRM Toyota/Lexus/Kia/Tradein | `color` | `FIELD_COLOR` | Default empty to `Серебряный`; old reference/custom map | Yes | Missing id skips row. |
| AutoCRM Toyota/Lexus/Kia/Tradein | `run` | `FIELD_MILEAGE` | Direct assignment when present | No | No numeric cleanup. |
| AutoCRM Toyota/Lexus/Kia/Tradein | `complectation_name` | `FIELD_COMPLECTATION` | Direct assignment when present | No | Kia uses this for de-duplication. |
| AutoCRM Toyota/Lexus/Kia/Tradein | `availability` | `FIELD_FEATURED_OPTION`, `FIELD_CUSTOMS` | Old reference lookup/custom map; fallback `1`; customs `1` only when featured option `1` | No | `в наличии`=>1, `на заказ`=>3 custom map. |
| AutoCRM Toyota/Lexus/Kia/Tradein | command settings | `FIELD_CONDITION`, `FIELD_CURRENCY` | Condition/currency set by command: Toyota/Lexus/Kia condition `4`, Tradein condition `1`; currency varies | Yes | Not provider fields. |
| AutoCRM Toyota/Lexus/Kia/Tradein | `price` | `FIELD_PRICE` | Direct if currency `1`; otherwise `intval(price / currencyRate)` | Yes | ToyotaTradein gets rate from `sync/currency-rate`; Kia sets rate `1`. |
| AutoCRM Toyota/Lexus/Kia/Tradein | `description`, `extras` | `FIELD_DESCRIPTION` | Description overrides extras; extras gets comma spacing fix | No | Toyota/Lexus/Tradein may preserve current description/price on update. |

## Provider Sources

| Provider | Source file(s) | Endpoint/feed path | Format | Status handling | Image handling |
|---|---|---|---|---|---|
| Autohub | `src/Command/AutohubSyncCommand.php`, `src/Service/Sync/AutohubSync.php` | `https://baz-on.ru/export/c1010/af1b1/mashina-parts.csv` | CSV Windows-1251, `;` | `Статус` is sanitized as optional but not mapped | `Фото` required, split by `, `, max 12 |
| Autoland | `AutolandSyncCommand.php`, `AutolandSync.php` | `https://baz-on.ru/export/c2095/9d8bf/autolandkg-parts.csv` | CSV Windows-1251, `;` | `Статус` optional only | `Фото` required, split by `, ` |
| Shredder | `ShredderSyncCommand.php`, `ShredderSync.php` | `https://baz-on.ru/export/c3846/2bd53/mashinakg-parts.csv` | CSV Windows-1251, `;` | `Статус` optional only | `Фото` required, split by `, `, max 12 |
| Okayamaomsk | `OkayamaomskSyncCommand.php`, `OkayamaomskSync.php` | `https://baz-on.ru/export/c614/e5dc9/car-kg-parts.csv` | CSV Windows-1251, `;` | `Статус` optional only | `Фото` required, split by `, `, max 12 |
| Banzaimotors | `BanzaimotorsSyncCommand.php`, `BanzaimotorsSync.php` | parts `https://baz-on.ru/export/c1483/c8ae6/mashina-parts.csv`; wheels `https://baz-on.ru/export/c1483/8fb9b/wheels-wheels.csv` | CSV Windows-1251, `;` | Optional only | `Фото` required, split by `, `, max 12 |
| Bavaria | `BavariaSyncCommand.php`, `BavariaSync.php` | parts `https://baz-on.ru/export/c935/01051/mashina-bavariab-parts.csv`; wheels `https://baz-on.ru/export/c935/77e63/disk-wheels.csv` | CSV Windows-1251, `;` | Optional only | `Фото` required, split by `, `, max 12 |
| Shinabar | `ShinabarSyncCommand.php`, `ShinabarSync.php` | `https://baz-on.ru/export/c1750/bee92/mashina-wheels.csv` | CSV Windows-1251, `;` | Required non-empty `Статус`, but not mapped | `Фото` optional in sanitizer but mapper expects it |
| Avtoinstall | `AvtoinstallSyncCommand.php`, `AvtoinstallSync.php` | `https://avtoinstall.kg/csvprice_pro/2024-04-11_1712816810_data.csv` | CSV, `;` | Requires `_STOCK_STATUS_ = В наличии` and `_STATUS_ = 1` | Main image plus gallery, ordered `index|url` |
| Allmotors | `AllmotorsSyncCommand.php`, `AllmotorsSync.php` | `https://allmotors.kg/categories/<slug>` and product pages | HTML | Absence from crawl means delete | Product gallery links proxied via mashina sync file endpoint |
| Autoshina | `AutoshinaSyncCommand.php`, `AutoshinaSync.php` | `https://autoshina.kg/products?...` and product pages | HTML | Absence from crawl means delete | Single product image required |
| DetalKg | `DetalKgSyncCommand.php`, `DetalKgSync.php` | YML `https://detal.kg/price-yml/6fe6a8a6e6cb710584efc4af0c34ce50.yml`; tire category pages | XML/YML + HTML | Parts skip `count == 0`; tire absence from crawl means delete | Parts `picture`; tire page image list with no-photo filtering |
| Toyota | `ToyotaSyncCommand.php`, `AutocrmSync.php` | `https://autos.autocrm.ru/api/auto-ru/feed?id=...&isUsed=0` | XML | `availability` maps to featured option/customs | `images.image` required, ordered `index|url`, separate image diff |
| ToyotaTradein | `ToyotaTradeinSyncCommand.php`, `AutocrmSync.php` | `https://autos.autocrm.ru/api/auto-ru/feed?id=...&isUsed=1` | XML | Same as Toyota | Same as Toyota |
| Lexus | `LexusSyncCommand.php`, `AutocrmSync.php` | `https://autos.autocrm.ru/api/auto-ru/feed?id=...&isUsed=0` | XML | Same as Toyota | Same as Toyota |
| Kia | `KiaSyncCommand.php`, `AutocrmSync.php` | `https://autos.autocrm.ru/api/auto-ru/feed?id=...&isUsed=0` | XML | Same as Toyota | Same as Toyota; current command exits before write |

## Unique Keys And Duplicate Handling

| Provider | Unique key | Duplicate/group behavior |
|---|---|---|
| AutoCRM Toyota/Lexus/ToyotaTradein | VIN (`vin`) | Last feed row with same VIN wins in `$syncAds`; images are diffed by URL. |
| AutoCRM Kia | VIN first, then `modification + complectation` de-dupe | Sorts by `featured_option`, keeps first ad for modification/complectation key, but command currently exits before syncing. |
| Baz-on simple parts | `Артикул` | Banzai/Okayama keep one row per article. |
| Autohub/Shredder grouped parts | Group key from name/make/model/year/generation | If group has multiple rows, first row forms main payload; `external_id` becomes comma-joined article ids and description enumerates rows. |
| Autoland grouped parts | Group key from name/make/model | Same comma-joined grouped `external_id`. |
| Bavaria grouped parts | Group key from name/make/model/year/generation | Same grouped `external_id`. |
| Tire/wheel CSV providers | `Артикул` | One ad per article. |
| HTML crawlers | Product slug/id | One ad per product page. |
| DetalKg tires | Parsed tire article | `crawlTireDetailPages()` returns map keyed by parsed external id. |

