#!/usr/bin/env python3
"""Read-only Cold Turkey macOS storage diagnostic.

Reports metadata and SQLite schema names only; never reads table rows.
"""
import json
import os
import platform
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOTS = [
    ("system_application_support", Path("/Library/Application Support/Cold Turkey")),
    ("user_application_support", Path.home() / "Library/Application Support/Cold Turkey"),
]
MAX_FILES = 150
MAX_DEPTH = 2

def timestamp(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat()

def inspect_database(path):
    result = {"format": "unknown"}
    try:
        uri = "file:" + quote(str(path), safe="/") + "?mode=ro&immutable=1"
        with sqlite3.connect(uri, uri=True, timeout=2) as db:
            tables = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            result["format"] = "sqlite"
            result["tables"] = [row[0] for row in tables]
            result["columns"] = {}
            for (table,) in tables:
                escaped = table.replace('"', '""')
                cols = db.execute('PRAGMA table_info("' + escaped + '")').fetchall()
                result["columns"][table] = [row[1] for row in cols]
    except Exception as exc:
        result["format"] = "unreadable_or_not_sqlite"
        result["error_type"] = type(exc).__name__
    return result

def inspect_root(label, root):
    result = {"location": label, "exists": root.is_dir(), "files": []}
    if not result["exists"]:
        return result
    entries = []
    try:
        for current, dirs, files in os.walk(root):
            current_path = Path(current)
            depth = len(current_path.relative_to(root).parts)
            dirs[:] = sorted(d for d in dirs if depth < MAX_DEPTH and d not in {
                "Cache", "Caches", "Logs", "GPUCache"
            })
            for filename in files:
                path = current_path / filename
                try:
                    stat = path.stat()
                    entry = {
                        "name": path.name,
                        "relative_directory": str(path.parent.relative_to(root)),
                        "bytes": stat.st_size,
                        "modified_utc": timestamp(stat.st_mtime),
                        "readable": os.access(path, os.R_OK),
                    }
                    if path.suffix.lower() in {".db", ".sqlite", ".sqlite3"}:
                        entry.update(inspect_database(path))
                    elif path.suffix.lower() in {".json", ".plist"}:
                        entry["format"] = path.suffix.lower().lstrip(".")
                    entries.append(entry)
                except OSError as exc:
                    entries.append({"name": filename, "error_type": type(exc).__name__})
                if len(entries) >= MAX_FILES:
                    break
            if len(entries) >= MAX_FILES:
                break
    except OSError as exc:
        result["error_type"] = type(exc).__name__
    result["files"] = sorted(entries, key=lambda x: (x.get("relative_directory", ""), x.get("name", "")))
    result["truncated"] = len(entries) >= MAX_FILES
    return result

def main():
    if platform.system() != "Darwin":
        raise SystemExit("This diagnostic is intended for macOS.")
    print(json.dumps({
        "diagnostic_version": 2,
        "platform": platform.mac_ver()[0],
        "privacy": (
            "No file contents, database rows, settings values, URLs, website names, "
            "application names, window titles, or browsing history are read. "
            "File names and metadata within the Cold Turkey support folders are listed."
        ),
        "locations": [inspect_root(label, root) for label, root in ROOTS],
    }, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
