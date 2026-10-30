# Cold Turkey macOS storage diagnostic

Run from the repository root on the Mac where Cold Turkey Blocker is installed:

```bash
python3 scripts/diagnose_cold_turkey.py
```

The diagnostic probes two narrowly scoped candidate locations for `data-app.db`: the system-wide Cold Turkey Application Support directory and the current user's Application Support directory. The system-wide location is mentioned in community-maintained material, but Cold Turkey's official documentation does not specify a stable database path or schema; treat it as a candidate, not a guaranteed API.

It prints only whether a candidate exists, file size, modification time, readability, SQLite table names, and column names. It never reads or prints database rows, setting values, URLs, website names, application names, window titles, or browsing history. It does not copy, modify, or upload anything.

Share only the diagnostic JSON output if you want help identifying the statistics schema. Once the installed version's schema is identified and validated, the next change can implement a read-only 15-minute aggregate exporter. Until then, no statistics values are inferred or fabricated.
