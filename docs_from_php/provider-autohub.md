# Provider: Autohub

Old PHP: `src/Command/AutohubSyncCommand.php` + `src/Service/Sync/AutohubSync.php`.
New Python: `python_app/app/providers/autohub.py`.

- Feed: `https://baz-on.ru/export/c1010/af1b1/mashina-parts.csv`
- Format: Windows-1251 CSV, delimiter `;`
- Unique key: `Артикул`; grouped rows use comma-joined article ids
- Grouping: `Наименование` + `Марка` + `Модель` + `Год` + `Кузов`
- Type: commercial makes `setra`, `neoplan`, `man` -> old `type_id=36`; otherwise `type_id=30`
- Price: disabled, exported as `0` / currency `1`
- Images: required, capped at 12

Command:

```bash
cd python_app
python -m app.cli sync --provider autohub --dry-run
```
