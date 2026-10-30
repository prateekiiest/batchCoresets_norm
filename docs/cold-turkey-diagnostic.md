# Cold Turkey macOS storage diagnostic

The diagnostic is a first step toward a reliable 15-minute local statistics collector. It is intentionally read-only and does not attempt to export or interpret statistics yet.

## Run

From the repository root on the Mac where Cold Turkey Blocker is installed:

```bash
python3 scripts/diagnose_cold_turkey.py
```

It probes two narrowly scoped candidate locations for `data-app.db`: the system-wide Cold Turkey Application Support directory and the current user's Application Support directory. The system-wide location is reported in community-maintained material, but is not specified by Cold Turkey's official documentation; treat it as a candidate, not a guaranteed API.

## What it prints

- Whether each candidate file exists and is readable
- File size and modification time
- Whether it can be opened as SQLite in read-only/immutable mode
- SQLite table and column names only

It does **not** read or print database rows, settings values, URLs, website names, application names, window titles, or browsing history. It does not copy, modify, or upload any file. Share only the diagnostic JSON output if you want help identifying the statistics schema.

## Why this is not yet the 15-minute exporter

Cold Turkey's official guide documents exporting visible statistics as JSON from the Statistics tab, but does not document a stable public database schema or a statistics-export CLI. The collector must be based on the actual installed version's schema and tested against it before automatic extraction is enabled. Until then, no statistics values are inferred or fabricated.

The eventual collector should use a read-only database connection, extract only aggregates, write local CSV/JSON snapshots every 15 minutes, and keep raw identifiers out of reviewer packages. If the installed database format cannot be safely interpreted, the fallback should be a documented manual export rather than unsupported scraping.
