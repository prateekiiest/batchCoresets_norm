import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_reviewer_package.py"
ZERO = "0" * 64

def digest(value):
    return hashlib.sha256(value).hexdigest()

def write_manifest(path, previous):
    value = {
        "schema_version": 2,
        "created_at_utc": "2026-10-30T00:00:00+00:00",
        "collector_version": "test",
        "git_head": None,
        "previous_manifest_sha256": previous,
        "logs": {},
        "tracked_artifacts_by_extension": {},
        "note": "synthetic test fixture"
    }
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    value["manifest_payload_sha256"] = digest(raw)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return digest(path.read_bytes())

class ReviewerPackageTests(unittest.TestCase):
    def make_package(self, root):
        md = root / "manifests"
        md.mkdir()
        first = write_manifest(md / "manifest-001.json", ZERO)
        write_manifest(md / "manifest-002.json", first)
        (root / "package-index.json").write_text(json.dumps({
            "manifest_files": ["manifest-001.json", "manifest-002.json"],
            "timestamp_proofs": {}
        }), encoding="utf-8")

    def run_verifier(self, root):
        return subprocess.run([sys.executable, str(SCRIPT), str(root)], capture_output=True, text=True)

    def test_valid_chain_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_package(root)
            result = self.run_verifier(root)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("RESULT: PASS", result.stdout)

    def test_tampered_manifest_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_package(root)
            path = root / "manifests" / "manifest-001.json"
            value = json.loads(path.read_text())
            value["note"] = "tampered"
            path.write_text(json.dumps(value))
            result = self.run_verifier(root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("payload digest mismatch", result.stdout)

if __name__ == "__main__":
    unittest.main()
