# Cold Turkey macOS storage diagnostic

Run from the repository root on the Mac where Cold Turkey Blocker is installed:

```bash
python3 scripts/diagnose_cold_turkey.py
```

The diagnostic inventories file metadata up to two directory levels under these two narrowly scoped locations:

- `/Library/Application Support/Cold Turkey`
- `~/Library/Application Support/Cold Turkey`

It reports filenames, relative directory, size, modification time, readability, and (for SQLite candidates) table and column names. It does not read file contents, database rows, settings values, URLs, website names, application names, window titles, or browsing history. It does not copy, modify, or upload anything. The inventory is capped at 150 files per location and skips common cache/log directories.

**Privacy note:** filenames and timestamps inside the Cold Turkey support folders are included in the output. Review and redact any unexpected sensitive filename before sharing the JSON.

The database path/schema are not a documented stable Cold Turkey API. Treat the results as diagnostic evidence, not a guarantee that a database is supported for automated extraction. Once the installed version's statistics store is identified and validated, the next change can implement a read-only 15-minute aggregate exporter. Until then, no statistics values are inferred or fabricated.
