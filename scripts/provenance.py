#!/usr/bin/env python3
"""Local, opt-in provenance log for saved draft versions.

This records observed file versions and user-entered assistance annotations.
It cannot detect AI use automatically or observe unsaved keystrokes.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / ".writing-provenance"
SNAPSHOTS = STORE / "snapshots"
EVENTS = STORE / "events.jsonl"
ANNOTATIONS = STORE / "annotations.jsonl"
EXTENSIONS = {".tex", ".md", ".rst", ".txt", ".bib", ".html", ".htm"}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git_head():
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
            capture_output=True, text=True
        ).stdout.strip()
    except Exception:
        return None


def candidates(paths):
    found = set()
    for raw in paths:
        p = Path(raw)
        if not p.is_absolute():
            p = ROOT / p
        if p.is_file() and p.suffix.lower() in EXTENSIONS:
            found.add(p.resolve())
        elif p.is_dir():
            found.update(q.resolve() for q in p.rglob("*")
                         if q.is_file() and q.suffix.lower() in EXTENSIONS
                         and STORE not in q.parents and ".git" not in q.parts)
    return sorted(found)


def relative(path):
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def append(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def watch(args):
    STORE.mkdir(parents=True, exist_ok=True)
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    state_path = STORE / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    print("Local provenance watcher running. Ctrl-C stops it.")
    print("Only saved files are observed; records stay in ignored .writing-provenance/.")
    print("Watched paths:", ", ".join(args.paths))
    try:
        while True:
            present = set()
            for path in candidates(args.paths):
                rel = relative(path)
                present.add(rel)
                data = path.read_bytes()
                digest = sha(data)
                previous = state.get(rel, {}).get("sha256")
                if previous == digest:
                    continue
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
                snap_name = f"{stamp}_{digest[:12]}_{path.name}"
                snap_path = SNAPSHOTS / snap_name
                snap_path.write_bytes(data)
                event = {
                    "observed_at_utc": now(),
                    "path": rel,
                    "event": "baseline" if previous is None else "saved_version_changed",
                    "sha256": digest,
                    "previous_sha256": previous,
                    "size_bytes": len(data),
                    "snapshot": str(snap_path.relative_to(ROOT)),
                    "git_head": git_head(),
                    "note": "Observation time, not guaranteed edit time; AI assistance is not inferred."
                }
                append(EVENTS, event)
                state[rel] = {"sha256": digest, "snapshot": event["snapshot"]}
                state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
                print(f"[{event['observed_at_utc']}] {event['event']}: {rel}")
            for rel in list(state):
                if rel.startswith("_"):
                    continue
                path = ROOT / rel
                if rel not in present and path.is_relative_to(ROOT):
                    append(EVENTS, {
                        "observed_at_utc": now(), "path": rel, "event": "file_missing",
                        "previous_sha256": state[rel].get("sha256"),
                        "git_head": git_head(),
                        "note": "File missing at observation time; this does not establish why it disappeared."
                    })
                    del state[rel]
                    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
            time.sleep(max(1, args.interval))
    except KeyboardInterrupt:
        print("\nWatcher stopped.")


def annotate(args):
    if args.label not in {"human_written", "ai_assisted", "ai_generated_then_edited", "unknown"}:
        raise SystemExit("Invalid label.")
    path = Path(args.file)
    if not path.is_absolute():
        path = ROOT / path
    if not path.is_file():
        raise SystemExit(f"File not found: {path}")
    data = path.read_bytes()
    append(ANNOTATIONS, {
        "recorded_at_utc": now(),
        "path": relative(path.resolve()),
        "file_sha256": sha(data),
        "label": args.label,
        "note": args.note,
        "git_head": git_head(),
        "self_reported": True,
        "warning": "Self-reported annotation; not independently verified."
    })
    print(f"Annotation saved locally for {relative(path.resolve())} ({args.label}).")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    w = sub.add_parser("watch", help="Record saved versions while running")
    w.add_argument("paths", nargs="*", default=["paper"], help="Files/directories; defaults to paper/")
    w.add_argument("--interval", type=int, default=3, help="Polling interval in seconds (minimum 1)")
    w.set_defaults(func=watch)
    a = sub.add_parser("annotate", help="Add a self-reported assistance label for the current file")
    a.add_argument("file")
    a.add_argument("--label", required=True,
                   choices=["human_written", "ai_assisted", "ai_generated_then_edited", "unknown"])
    a.add_argument("--note", default="", help="Optional note; avoid storing sensitive prompt content")
    a.set_defaults(func=annotate)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
