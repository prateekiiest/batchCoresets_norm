#!/usr/bin/env python3
"""Create an OpenTimestamps proof for the final hashes of local provenance logs.

The manifest contains hashes and metadata only, never the log contents.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGS = {
    "vscode": ROOT / ".writing-provenance" / "vscode-events.jsonl",
    "cursor": ROOT / ".writing-provenance" / "cursor-events.jsonl",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="writing-provenance")
    parser.add_argument(
        "--manifest-only",
        action="store_true",
        help="Write the hash manifest without invoking 'ots stamp'.",
    )
    args = parser.parse_args()

    checked = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_provenance.py")],
        cwd=ROOT,
    )
    if checked.returncode:
        print("Refusing to anchor invalid event logs.", file=sys.stderr)
        return checked.returncode

    included = {
        name: {"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)}
        for name, path in LOGS.items()
        if path.is_file()
    }
    if not included:
        print("No VS Code or Cursor provenance logs found; nothing to anchor.", file=sys.stderr)
        return 2

    manifest = {
        "schema_version": 1,
        "label": args.label,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "algorithm": "SHA-256",
        "logs": included,
        "note": (
            "Contains log hashes, not log contents. Local creation time is not trusted; "
            "the OpenTimestamps proof is the independent timestamp evidence."
        ),
    }
    payload = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    manifest["payload_sha256_before_self_hash"] = hashlib.sha256(payload).hexdigest()

    out_dir = ROOT / "checkpoints"
    out_dir.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = out_dir / f"provenance-anchor-{stamp}-{manifest['payload_sha256_before_self_hash'][:12]}.json"
    target.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Manifest: {target.relative_to(ROOT)}")
    print(f"Manifest file SHA-256: {sha256_file(target)}")
    for name, entry in included.items():
        print(f"{name} log SHA-256: {entry['sha256']}")

    if args.manifest_only:
        print("Manifest-only mode: no external timestamp was requested.")
        return 0

    try:
        ots = subprocess.run(["ots", "stamp", str(target)], cwd=ROOT)
    except FileNotFoundError:
        print(
            "Manifest created, but 'ots' was not found. Install with "
            "'python3 -m pip install --user opentimestamps-client', then run "
            f"'ots stamp {target.relative_to(ROOT)}'.",
            file=sys.stderr,
        )
        return 127
    if ots.returncode:
        print(
            "Manifest created, but external timestamping failed. Retry with "
            f"'ots stamp {target.relative_to(ROOT)}'.",
            file=sys.stderr,
        )
        return ots.returncode
    proof = Path(str(target) + ".ots")
    print(f"Proof file: {proof.relative_to(ROOT)}")
    print("Copy both files to storage outside this computer.")
    print("A proof may initially be pending; later run 'ots upgrade' and 'ots verify'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
