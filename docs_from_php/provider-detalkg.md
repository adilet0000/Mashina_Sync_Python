# Provider: DetalKg

Old PHP: `src/Command/DetalKgSyncCommand.php` + `src/Service/Sync/DetalKgSync.php`.
New Python: `python_app/app/providers/detalkg.py`.

- Parts feed: `https://detal.kg/price-yml/6fe6a8a6e6cb710584efc4af0c34ce50.yml`
- Tire source: legacy `https://detal.kg/tires-search/` pages
- Format: safe XML/YML parser via `defusedxml`, tire HTML via BeautifulSoup
- Parts unique key: offer `@id`
- Parts filtering: skip `count == 0`
- Parts price: `price + 20%`, currency `1`
- Parts type/condition: old `type_id=30`, condition `2`
- Tires: old `type_id=31`, condition `2`, featured metadata `1`

Command:

```bash
cd python_app
python -m app.cli sync --provider detalkg --dry-run
```
