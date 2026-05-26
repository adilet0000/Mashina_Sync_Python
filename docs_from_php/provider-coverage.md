# Provider Coverage

| Provider | Parser | Mapper | Dry-run | Real write | Verify | Tests | Known gaps |
|---|---|---|---|---|---|---|---|
| `autoland` | CSV cp1251 | `LegacyAd` -> catalog | Yes | Via guarded core | Via core | Yes | Live feed previously returned 404 during one dry-run check; URL may need provider confirmation. |
| `autohub` | CSV cp1251 | `LegacyAd` -> catalog | Yes | Via guarded core | Via core | Yes | Legacy `SyncData` exact old id maps are replaced by value-based catalog option resolution. |
| `shredder` | CSV cp1251 | `LegacyAd` -> catalog | Yes | Via guarded core | Via core | Yes | Same reference-resolution caveat as Autohub. |
| `okayamaomsk` | CSV cp1251 | `LegacyAd` -> catalog | Yes | Via guarded core | Via core | Yes | Delivery/payment text is preserved as static appended text from audit. |
| `banzaimotors` | CSV cp1251, two feeds | `LegacyAd` -> catalog | Yes | Via guarded core | Via core | Yes | Tire/wheel reference values are emitted as values; DB option ids depend on catalog reference data. |
| `bavaria` | CSV cp1251, two feeds | `LegacyAd` -> catalog | Yes | Via guarded core | Via core | Yes | Parts price remains omitted/empty like legacy disabled price behavior. |
| `shinabar` | CSV cp1251 | `LegacyAd` -> catalog | Yes | Via guarded core | Via core | Yes | Wheel import remains intentionally skipped because legacy was tire-focused. |
| `avtoinstall` | CSV cp1251 | `LegacyAd` -> catalog | Yes | Via guarded core | Via core | Yes | Special price uses local runtime date, matching legacy intent. |
| `allmotors` | HTML with BeautifulSoup | `LegacyAd` -> catalog | Yes | Via guarded core | Via core | Yes | Live HTML selectors may need adjustment if the site markup changed. |
| `autoshina` | HTML with BeautifulSoup | `LegacyAd` -> catalog | Yes | Via guarded core | Via core | Yes | Live HTML selectors may need adjustment if the site markup changed. |
| `detalkg` | defused XML/YML + HTML | `LegacyAd` -> catalog | Yes | Via guarded core | Via core | Yes | Tire crawler starts with the legacy `tires-search` page; pagination can be expanded after live validation. |
| `toyota` | defused AutoCRM XML | `LegacyAd` -> catalog | Yes | Via guarded core | Via core | Yes | Complex old `SyncData` car-reference inference is replaced by catalog option resolution from values. |
| `toyota_tradein` | defused AutoCRM XML | `LegacyAd` -> catalog | Yes | Via guarded core | Via core | Yes | Dealer currency rate can be supplied by `SYNC_PROVIDER_TOYOTA_TRADEIN_CURRENCY_RATE`; no old API rate call. |
| `lexus` | defused AutoCRM XML | `LegacyAd` -> catalog | Yes | Via guarded core | Via core | Yes | Lexus VIN fallback is preserved for GX. |
| `kia` | defused AutoCRM XML | `LegacyAd` -> catalog | Yes | Via guarded core | Via core | Yes | Legacy debug `print_r/exit` is intentionally not reproduced. |
