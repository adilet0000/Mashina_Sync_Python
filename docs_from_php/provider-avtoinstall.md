# Provider: Avtoinstall

Old PHP: `src/Command/AvtoinstallSyncCommand.php` + `src/Service/Sync/AvtoinstallSync.php`.
New Python: `python_app/app/providers/avtoinstall.py`.

- Feed: `https://avtoinstall.kg/csvprice_pro/2024-04-11_1712816810_data.csv`
- Format: CSV, delimiter `;`
- Unique key: `_ID_`
- Filtering: `_STOCK_STATUS_ == В наличии` and `_STATUS_ == 1`
- Type: old `type_id=33`
- Condition: `2`
- Images: main image plus gallery, output as ordered `index|url`
- Description: HTML stripped/decoded, attributes appended
- Price: direct import with legacy special price window logic, currency `1`

Command:

```bash
cd python_app
python -m app.cli sync --provider avtoinstall --dry-run
```
