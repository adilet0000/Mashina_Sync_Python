# Provider: Lexus

Old PHP: `src/Command/LexusSyncCommand.php` + shared `src/Service/Sync/AutocrmSync.php`.
New Python: `python_app/app/providers/lexus.py`.

- Feed: AutoCRM XML
- Unique key: VIN (`vin`)
- Type: old `type_id=1`
- Images: required, ordered `index|url`
- Condition: `4`
- Currency: `1`
- Fallback: missing make becomes `Lexus`; VIN fourth char `J` can infer model `GX`
- Preserve behavior: current price is not overwritten on update

Command:

```bash
cd python_app
python -m app.cli sync --provider lexus --dry-run
```
