#!/usr/bin/env python3
"""Read-only Cold Turkey macOS storage diagnostic.

Prints only candidate-file metadata and SQLite schema identifiers. It never
reads table rows, setting values, URLs, application names, or browsing history.
"""
import json
import os
import platform
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

CANDIDATES = [
    Path("/Library/Application Support/Cold Turkey/data-app.db"),
    Path.home() / "Library/Application Support/Cold Turkey/data-app.db",
]

def inspect(path):
    item = {"candidate": path.name, "exists": path.is_file()}
    if not item["exists"]:
        return item
    stat = path.stat()
    item.update({
        "bytes": stat.st_size,
        "modified_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "readable": os.access(path, os.R_OK),
    })
    try:
        uri = "file:" + quote(str(path), safe="/") + "?mode=ro&immutable=1"
        with sqlite3.connect(uri, uri=True, timeout=2) as db:
            tables = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            item["format"] = "sqlite"
            item["tables"] = [row[0] for row in tables]
            item["columns"] = {}
            for (table,) in tables:
                escaped = table.replace('"', '""')
                cols = db.execute('PRAGMA table_info("' + escaped + '")').fetchall()
                item["columns"][table] = [row[1] for row in cols]
    except Exception as exc:
        item["format"] = "unreadable_or_not_sqlite"
        item["error_type"] = type(exc).__name__
    return item

def main():
    if platform.system() != "Darwin":
        raise SystemExit("This diagnostic is intended for macOS.")
    print(json.dumps({
        "diagnostic_version": 1,
        "platform": platform.mac_ver()[0],
        "privacy": "No database rows or personal activity data are read or printed.",
        "candidates": [inspect(path) for path in CANDIDATES],
    }, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
