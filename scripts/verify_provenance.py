#!/usr/bin/env python3
"""Verify SHA-256 event chains written by the VS Code and Cursor provenance tools."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZERO = "0" * 64


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def verify(path, cursor=False):
    if not path.exists():
        print(f"SKIP {path.relative_to(ROOT)}: no log found")
        return True
    previous = ZERO
    count = 0
    with path.open("r", encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                print(f"FAIL {path.relative_to(ROOT)}:{line_no}: invalid JSON")
                return False
            stored = event.get("event_hash")
            if not isinstance(stored, str):
                print(f"FAIL {path.relative_to(ROOT)}:{line_no}: missing event_hash")
                return False
            unsigned = dict(event)
            del unsigned["event_hash"]
            if event.get("previous_event_hash") != previous:
                print(f"FAIL {path.relative_to(ROOT)}:{line_no}: previous hash mismatch")
                return False
            canonical = json.dumps(
                unsigned,
                ensure_ascii=False,
                sort_keys=cursor,
                separators=(",", ":"),
            )
            if digest(canonical) != stored:
                print(f"FAIL {path.relative_to(ROOT)}:{line_no}: event hash mismatch")
                return False
            previous = stored
            count += 1
    print(f"OK {path.relative_to(ROOT)}: {count} event(s), final hash {previous}")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vscode", type=Path, default=ROOT / ".writing-provenance" / "vscode-events.jsonl")
    parser.add_argument("--cursor", type=Path, default=ROOT / ".writing-provenance" / "cursor-events.jsonl")
    args = parser.parse_args()
    ok = verify(args.vscode, cursor=False) and verify(args.cursor, cursor=True)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
