# Provider: Shinabar

Old PHP: `src/Command/ShinabarSyncCommand.php` + `src/Service/Sync/ShinabarSync.php`.
New Python: `python_app/app/providers/shinabar.py`.

- Feed: `https://baz-on.ru/export/c1750/bee92/mashina-wheels.csv`
- Format: Windows-1251 CSV, delimiter `;`
- Unique key: `Артикул`
- De-duplication: last row per article wins
- Type: tire-focused, old `type_id=31`
- Required: tire width, height, size, season/type, condition, availability, images
- Price: direct import, currency `1`

Command:

```bash
cd python_app
python -m app.cli sync --provider shinabar --dry-run
```
