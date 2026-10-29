#!/usr/bin/env python3
import hashlib, json, subprocess, sys
from pathlib import Path

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def main():
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python3 scripts/verify_checkpoint.py checkpoints/checkpoint-....json")
    failed = False
    for arg in sys.argv[1:]:
        p = Path(arg)
        try:
            manifest = json.loads(p.read_text())
        except Exception as e:
            print(f"FAIL {p}: cannot read JSON: {e}")
            failed = True
            continue
        commit = manifest.get("git_commit")
        try:
            subprocess.check_call(["git", "cat-file", "-e", f"{commit}^{{commit}}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            print(f"WARNING {p}: commit {commit} is not present in this clone")
        missing, mismatched = [], []
        for name, expected in manifest.get("tracked_file_sha256", {}).items():
            file = Path(name)
            if not file.exists():
                missing.append(name)
            elif sha(file.read_bytes()) != expected:
                mismatched.append(name)
        if missing or mismatched:
            print(f"FAIL {p}")
            if missing: print("  Missing:", ", ".join(missing))
            if mismatched: print("  Hash mismatch:", ", ".join(mismatched))
            failed = True
        else:
            print(f"PASS {p}: {len(manifest.get('tracked_file_sha256', {}))} tracked file hashes match current working tree")
            print("  Note: this compares against the current working tree, not a historical checkout.")
    raise SystemExit(1 if failed else 0)
if __name__ == "__main__": main()
