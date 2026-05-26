# Provider: Allmotors

Old PHP: `src/Command/AllmotorsSyncCommand.php` + `src/Service/Sync/AllmotorsSync.php`.
New Python: `python_app/app/providers/allmotors.py`.

- Site: `https://allmotors.kg`
- Format: HTML crawler with BeautifulSoup
- Unique key: product slug from `/products/<slug>`
- Category mapping: legacy category slugs map to old `type_id` values; unknown categories fall back to `30`
- Images: proxied through `https://www.mashina.kg/sync/files?...` like legacy
- Tires: dimensions parsed from title; season defaults to summer when absent
- Price: direct import, currency `1`

Command:

```bash
cd python_app
python -m app.cli sync --provider allmotors --dry-run
```
