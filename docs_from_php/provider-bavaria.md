# Provider: Bavaria

Old PHP: `src/Command/BavariaSyncCommand.php` + `src/Service/Sync/BavariaSync.php`.
New Python: `python_app/app/providers/bavaria.py`.

- Parts feed: `https://baz-on.ru/export/c935/01051/mashina-bavariab-parts.csv`
- Tire/wheel feed: `https://baz-on.ru/export/c935/77e63/disk-wheels.csv`
- Format: Windows-1251 CSV, delimiter `;`
- Unique key: `Артикул`; grouped parts use comma-joined article ids
- Grouping: parts by `Наименование` + `Марка` + `Модель` + `Год` + `Кузов`
- Make fallback: `depo`, `bosch`, `дубликат` -> `bmw`
- Types: parts `30`, tires `31`, wheels `32`
- Price: parts omitted when disabled; tire/wheel price direct, currency `1`
- Images: required, capped at 12

Command:

```bash
cd python_app
python -m app.cli sync --provider bavaria --dry-run
```
