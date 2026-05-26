# Provider: Autoshina

Old PHP: `src/Command/AutoshinaSyncCommand.php` + `src/Service/Sync/AutoshinaSync.php`.
New Python: `python_app/app/providers/autoshina.py`.

- Site: `https://autoshina.kg`
- Format: HTML crawler with BeautifulSoup
- Unique key: product id from `/products/<id>`
- Type: old `type_id=31`
- Required: image, brand, model, tire width, tire height, tire size
- Season: defaults to summer when missing
- Condition: `2`
- Price: direct import, currency `1`

Command:

```bash
cd python_app
python -m app.cli sync --provider autoshina --dry-run
```
