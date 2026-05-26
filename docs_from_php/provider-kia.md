# Provider: Kia

Old PHP: `src/Command/KiaSyncCommand.php` + shared `src/Service/Sync/AutocrmSync.php`.
New Python: `python_app/app/providers/kia.py`.

- Feed: AutoCRM XML
- Unique key: VIN (`vin`)
- Type: old `type_id=1`
- Images: required, ordered `index|url`
- Condition: `4`
- Currency: `2`
- Fallback: missing make becomes `Kia`; VIN prefixes infer Sportage/Stinger like legacy
- De-duplication: sort by `featured_option`, keep first by `modification + complectation`
- Difference: legacy debug `print_r/exit` is intentionally not reproduced

Command:

```bash
cd python_app
python -m app.cli sync --provider kia --dry-run
```
