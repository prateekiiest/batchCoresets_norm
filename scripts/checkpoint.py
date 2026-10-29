#!/usr/bin/env python3
import argparse, hashlib, json, subprocess
from datetime import datetime, timezone
from pathlib import Path

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="checkpoint")
    args = parser.parse_args()
    root = Path(git("rev-parse", "--show-toplevel")).resolve()
    commit = git("rev-parse", "HEAD")
    status = git("status", "--porcelain")
    files = {}
    tracked = git("ls-files", "-z").split("\0")
    for name in tracked:
        if not name: continue
        path = root / name
        if path.is_file():
            files[name] = sha(path.read_bytes())
    manifest = {
        "schema_version": 1,
        "label": args.label,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": commit,
        "working_tree_status_at_creation": status.splitlines(),
        "tracked_file_sha256": dict(sorted(files.items())),
        "note": "Local checkpoint timestamp is not an independent trusted timestamp."
    }
    raw = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    digest = sha(raw)
    out = root / "checkpoints"
    out.mkdir(exist_ok=True)
    target = out / f"checkpoint-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{digest[:12]}.json"
    target.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Checkpoint: {target.relative_to(root)}")
    print(f"Manifest SHA-256: {digest}")
    print(f"Git commit: {commit}")
    if status:
        print("WARNING: working tree had uncommitted changes at checkpoint time.")
    print("Next: commit the checkpoint, then preserve its hash/receipt externally for independent timestamping.")
if __name__ == "__main__":
    main()
