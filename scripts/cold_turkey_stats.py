#!/usr/bin/env python3
"""Read-only, privacy-preserving daily aggregates from Cold Turkey SQLite stores.

Only dates, summed seconds, and blocked-event counts are written. Domain,
application/file, title, and user fields are never selected or exported.
"""
import argparse
import csv
import json
import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

DEFAULT_ROOT = Path("/Library/Application Support/Cold Turkey")
METRICS = (
    "browser_seconds",
    "browser_strict_seconds",
    "browser_blocked_events",
    "app_seconds",
    "app_strict_seconds",
    "app_blocked_events",
)
SOURCES = {
    "data-browser.db": {
        "stats": ("browser_seconds", "sum"),
        "statsStrict": ("browser_strict_seconds", "sum"),
        "statsBlocked": ("browser_blocked_events", "count"),
    },
    "data-helper.db": {
        "statsApp": ("app_seconds", "sum"),
        "statsAppStrict": ("app_strict_seconds", "sum"),
        "statsBlocked": ("app_blocked_events", "count"),
    },
}
NOTES = [
    "Only daily sums of seconds and counts of blocked rows are retained.",
    "Domain, application/file, title, and user columns are never selected.",
    "Title-level tables and statsBlockedTime are excluded.",
    "Regular and strict-mode tables are reported separately, not combined.",
]

def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def read_only_connection(path):
    # mode=ro honours SQLite WAL files; do not use immutable=1, which can
    # ignore uncheckpointed WAL records. query_only adds another write guard.
    uri = "file:" + quote(str(path), safe="/") + "?mode=ro"
    db = sqlite3.connect(uri, uri=True, timeout=5)
    db.execute("PRAGMA query_only=ON")
    return db

def aggregate_one(db_path, table_specs, daily):
    result = {"file": db_path.name, "status": "missing", "tables": {}}
    if not db_path.is_file():
        return result
    try:
        with closing(read_only_connection(db_path)) as db:
            names = {row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
            result["status"] = "ok"
            for table, (metric, operation) in table_specs.items():
                if table not in names:
                    result["tables"][table] = "missing_table"
                    continue
                # The SQL identifiers come only from this fixed allowlist.
                if operation == "sum":
                    query = 'SELECT date, SUM(COALESCE(seconds, 0)) FROM "' + table + '" GROUP BY date'
                else:
                    query = 'SELECT date, COUNT(*) FROM "' + table + '" GROUP BY date'
                try:
                    for date_value, amount in db.execute(query):
                        if date_value is None:
                            continue
                        date_key = str(date_value)
                        daily.setdefault(date_key, {key: 0 for key in METRICS})
                        daily[date_key][metric] += int(amount or 0)
                    result["tables"][table] = "aggregated"
                except sqlite3.Error as exc:
                    result["tables"][table] = "query_error:" + type(exc).__name__
    except (sqlite3.Error, OSError) as exc:
        result["status"] = "read_error:" + type(exc).__name__
    return result

def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp_name = tempfile.mkstemp(prefix=".cold-turkey-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp_name, 0o600)
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass

def collect(root=DEFAULT_ROOT, output_dir=None):
    root = Path(root)
    output_dir = Path(output_dir) if output_dir else Path.cwd() / ".writing-provenance" / "cold-turkey"
    daily = {}
    sources = []
    for filename, table_specs in SOURCES.items():
        sources.append(aggregate_one(root / filename, table_specs, daily))
    collected_at = utc_now()
    rows = [{"date": date, **values} for date, values in sorted(daily.items())]
    payload = {
        "schema_version": 1,
        "collected_at_utc": collected_at,
        "collection_interval_seconds": 900,
        "source_status": sources,
        "daily_aggregates": rows,
        "privacy": "Daily aggregate seconds and blocked-row counts only; no domain, application/file, title, or user identifiers.",
        "interpretation_notes": NOTES,
    }
    json_path = output_dir / "daily-aggregates.json"
    csv_path = output_dir / "daily-aggregates.csv"
    atomic_write(json_path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
    import io
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=("date",) + METRICS)
    writer.writeheader()
    writer.writerows(rows)
    atomic_write(csv_path, buffer.getvalue())
    try:
        output_dir.chmod(0o700)
    except OSError:
        pass
    return {
        "status": "ok" if all(s["status"] == "ok" for s in sources) else "partial",
        "days": len(rows),
        "source_count": len(sources),
        "json": str(json_path),
        "csv": str(csv_path),
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", default=str(DEFAULT_ROOT))
    parser.add_argument("--output-dir", default=".writing-provenance/cold-turkey")
    args = parser.parse_args()
    result = collect(args.source_dir, args.output_dir)
    print(json.dumps({k: v for k, v in result.items() if k not in {"json", "csv"}}, sort_keys=True))
    if result["status"] != "ok":
        raise SystemExit(1)

if __name__ == "__main__":
    main()
