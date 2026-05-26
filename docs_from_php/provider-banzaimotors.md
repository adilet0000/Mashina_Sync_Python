# Provider: Banzaimotors

Old PHP: `src/Command/BanzaimotorsSyncCommand.php` + `src/Service/Sync/BanzaimotorsSync.php`.
New Python: `python_app/app/providers/banzaimotors.py`.

- Parts feed: `https://baz-on.ru/export/c1483/c8ae6/mashina-parts.csv`
- Tire/wheel feed: `https://baz-on.ru/export/c1483/8fb9b/wheels-wheels.csv`
- Format: Windows-1251 CSV, delimiter `;`
- Unique key: `Артикул`
- Types: parts `30`, tires `31`, wheels `32`
- Price: disabled, exported as `0` / currency `1`
- Images: required, capped at 12
- Tire/wheel specs: emitted as normalized LegacyAd fields for catalog option resolution

Command:

```bash
cd python_app
python -m app.cli sync --provider banzaimotors --dry-run
```
