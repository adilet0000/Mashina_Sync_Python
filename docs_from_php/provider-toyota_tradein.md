# Provider: Toyota Trade-In

Old PHP: `src/Command/ToyotaTradeinSyncCommand.php` + shared `src/Service/Sync/AutocrmSync.php`.
New Python: `python_app/app/providers/toyota_tradein.py`.

- Feed: AutoCRM XML `isUsed=1`
- Unique key: VIN (`vin`)
- Type: old `type_id=1`
- Images: required, ordered `index|url`
- Condition: `1`
- Currency: `2`; optional `SYNC_PROVIDER_TOYOTA_TRADEIN_CURRENCY_RATE`
- Preserve behavior: current price and old_price are not overwritten on update
- Legacy special skip VIN `WBACW010109C49929` is documented but not hard-coded yet

Command:

```bash
cd python_app
python -m app.cli sync --provider toyota_tradein --dry-run
```
