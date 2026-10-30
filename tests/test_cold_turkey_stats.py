import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import cold_turkey_stats

class ColdTurkeyAggregateTests(unittest.TestCase):
    def make_db(self, path, schema, rows):
        db = sqlite3.connect(path)
        db.execute("PRAGMA journal_mode=WAL")
        for statement in schema:
            db.execute(statement)
        for statement, values in rows:
            db.execute(statement, values)
        db.commit()
        db.close()

    def test_daily_aggregates_exclude_sensitive_identifiers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Cold Turkey"
            out = Path(tmp) / "out"
            root.mkdir()
            self.make_db(root / "data-browser.db", [
                "CREATE TABLE stats(date TEXT, domain TEXT, seconds INTEGER, user TEXT)",
                "CREATE TABLE statsStrict(date TEXT, domain TEXT, seconds INTEGER, user TEXT)",
                "CREATE TABLE statsBlocked(date TEXT, domain TEXT, user TEXT)",
                "CREATE TABLE statsTitle(date TEXT, title TEXT, seconds INTEGER, user TEXT)",
            ], [
                ("INSERT INTO stats VALUES (?, ?, ?, ?)", ("2026-10-30", "private.example", 120, "private-user")),
                ("INSERT INTO stats VALUES (?, ?, ?, ?)", ("2026-10-30", "secret.example", 30, "private-user")),
                ("INSERT INTO statsStrict VALUES (?, ?, ?, ?)", ("2026-10-30", "strict.example", 10, "private-user")),
                ("INSERT INTO statsBlocked VALUES (?, ?, ?)", ("2026-10-30", "blocked.example", "private-user")),
                ("INSERT INTO statsTitle VALUES (?, ?, ?, ?)", ("2026-10-30", "private window title", 999, "private-user")),
            ])
            self.make_db(root / "data-helper.db", [
                "CREATE TABLE statsApp(date TEXT, file TEXT, seconds INTEGER, user TEXT)",
                "CREATE TABLE statsAppStrict(date TEXT, file TEXT, seconds INTEGER, user TEXT)",
                "CREATE TABLE statsBlocked(date TEXT, file TEXT, user TEXT)",
                "CREATE TABLE statsBlockedTime(date TEXT, break INTEGER, seconds INTEGER, user TEXT)",
            ], [
                ("INSERT INTO statsApp VALUES (?, ?, ?, ?)", ("2026-10-30", "private-app", 240, "private-user")),
                ("INSERT INTO statsAppStrict VALUES (?, ?, ?, ?)", ("2026-10-30", "private-app-strict", 20, "private-user")),
                ("INSERT INTO statsBlocked VALUES (?, ?, ?)", ("2026-10-30", "blocked-app", "private-user")),
                ("INSERT INTO statsBlockedTime VALUES (?, ?, ?, ?)", ("2026-10-30", 1, 300, "private-user")),
            ])
            result = cold_turkey_stats.collect(root, out)
            self.assertEqual(result["status"], "ok")
            payload = json.loads((out / "daily-aggregates.json").read_text())
            self.assertEqual(len(payload["daily_aggregates"]), 1)
            row = payload["daily_aggregates"][0]
            self.assertEqual(row["browser_seconds"], 150)
            self.assertEqual(row["browser_strict_seconds"], 10)
            self.assertEqual(row["browser_blocked_events"], 1)
            self.assertEqual(row["app_seconds"], 240)
            self.assertEqual(row["app_strict_seconds"], 20)
            self.assertEqual(row["app_blocked_events"], 1)
            serialized = (out / "daily-aggregates.json").read_text() + (out / "daily-aggregates.csv").read_text()
            for secret in ("private.example", "secret.example", "strict.example",
                           "blocked.example", "private window title", "private-user",
                           "private-app", "private-app-strict"):
                self.assertNotIn(secret, serialized)

    def test_missing_sources_are_reported_without_fabricating_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "empty"
            root.mkdir()
            out = Path(tmp) / "out"
            result = cold_turkey_stats.collect(root, out)
            self.assertEqual(result["status"], "partial")
            payload = json.loads((out / "daily-aggregates.json").read_text())
            self.assertEqual(payload["daily_aggregates"], [])

if __name__ == "__main__":
    unittest.main()
