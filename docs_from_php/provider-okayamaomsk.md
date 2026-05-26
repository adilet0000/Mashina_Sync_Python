# Provider: OkayamaOmsk

Old PHP: `src/Command/OkayamaomskSyncCommand.php` + `src/Service/Sync/OkayamaomskSync.php`.
New Python: `python_app/app/providers/okayamaomsk.py`.

- Feed: `https://baz-on.ru/export/c614/e5dc9/car-kg-parts.csv`
- Format: Windows-1251 CSV, delimiter `;`
- Unique key: `Артикул`
- Grouping: none
- Type: old `type_id=30`
- Price: direct import, currency `1`
- Location: legacy `region=9`, `town=62`
- Other legacy flags: `featured_option=2`, `comment_allowed=2` in raw payload metadata
- Description: provider fields plus delivery/payment text

Command:

```bash
cd python_app
python -m app.cli sync --provider okayamaomsk --dry-run
```
