# Provider: Toyota

Old PHP: `src/Command/ToyotaSyncCommand.php` + shared `src/Service/Sync/AutocrmSync.php`.
New Python: `python_app/app/providers/toyota.py`.

- Feed: AutoCRM XML `isUsed=0`
- Unique key: VIN (`vin`)
- Type: old `type_id=1`
- Images: required, ordered `index|url`
- Condition: `4`
- Currency: `1`
- Preserve behavior: current description and price are not overwritten on update
- Final target: new catalog DB, not old internal API

Command:

```bash
cd python_app
python -m app.cli sync --provider toyota --dry-run
```
