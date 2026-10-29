
#!/usr/bin/env python3
"""
Automatically checkpoint research files and timestamp checkpoints with
OpenTimestamps (OTS).

Assumptions:
- scripts/checkpoint.py accepts --label.
- Checkpoints are named checkpoint-*.json in the checkpoints/ directory.
- OTS is installed in /Users/prateekchanda/.venvs/ots/bin/ots.

This script does not commit or push to GitHub.
"""

import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Project paths
ROOT = Path(__file__).resolve().parents[1]
CHECKPOINTS = ROOT / "checkpoints"
LOG = ROOT / "research-log" / "OTS_LOG.md"
CHECKPOINT_SCRIPT = ROOT / "scripts" / "checkpoint.py"

# Use your existing OpenTimestamps installation directly.
OTS = Path("/Users/prateekchanda/.venvs/ots/bin/ots")

# Create a checkpoint every 30 minutes.
INTERVAL_SECONDS = 30 * 60


def utc_now():
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def log(message):
    """Write an event to the OTS log and print it to the terminal."""
    timestamp = utc_now()
    line = f"- {timestamp} | {message}\n"

    LOG.parent.mkdir(parents=True, exist_ok=True)

    with LOG.open("a", encoding="utf-8") as file:
        file.write(line)

    print(line, end="", flush=True)


def run(args):
    """Run a command and capture its output."""
    try:
        result = subprocess.run(
            [str(arg) for arg in args],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if result.stdout:
            print(result.stdout, end="", flush=True)
        return result
    except FileNotFoundError as exc:
        log(f"COMMAND NOT FOUND: {args[0]} ({exc})")
        return None
    except OSError as exc:
        log(f"COMMAND ERROR: {args[0]} ({exc})")
        return None


def check_setup():
    """Check required scripts, directories, and the OTS executable."""
    if not CHECKPOINT_SCRIPT.is_file():
        raise SystemExit(f"Missing checkpoint script: {CHECKPOINT_SCRIPT}")

    if not OTS.is_file():
        raise SystemExit(
            f"OTS executable not found: {OTS}\n"
            "Install it with:\n"
            "  /Users/prateekchanda/.venvs/ots/bin/python3 "
            "-m pip install opentimestamps-client"
        )

    CHECKPOINTS.mkdir(parents=True, exist_ok=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)

    result = run([OTS, "--help"])
    if result is None or result.returncode != 0:
        raise SystemExit("OTS could not be launched successfully.")


def create_checkpoint():
    """Create a checkpoint and return newly generated manifests."""
    before = set(CHECKPOINTS.glob("checkpoint-*.json"))

    result = run([
        sys.executable,
        CHECKPOINT_SCRIPT,
        "--label",
        "automatic-checkpoint",
    ])

    if result is None or result.returncode != 0:
        log("CHECKPOINT FAILED; will retry on the next cycle.")
        return []

    after = set(CHECKPOINTS.glob("checkpoint-*.json"))
    new_files = sorted(after - before)

    if new_files:
        for manifest in new_files:
            log(f"Checkpoint created: {manifest.name}")
        return new_files

    log("Checkpoint command completed; no new checkpoint file detected.")
    return []


def timestamp_unstamped_checkpoints():
    """Submit checkpoint manifests that do not yet have an OTS proof."""
    for manifest in sorted(CHECKPOINTS.glob("checkpoint-*.json")):
        proof = Path(str(manifest) + ".ots")

        if proof.exists():
            continue

        log(f"Submitting checkpoint to OTS: {manifest.name}")
        result = run([OTS, "stamp", manifest])

        if result is None or result.returncode != 0:
            log(f"OTS submission failed for {manifest.name}; will retry.")
            continue

        if proof.exists():
            log(
                f"OTS proof file created: {proof.name}. "
                "The timestamp may still be pending."
            )
        else:
            log(
                f"No proof file detected for {manifest.name}; "
                "check the OTS output and retry later."
            )


def upgrade_pending_proofs():
    """Attempt to upgrade and verify existing OTS proofs."""
    for proof in sorted(CHECKPOINTS.glob("checkpoint-*.json.ots")):
        log(f"Attempting OTS upgrade: {proof.name}")
        result = run([OTS, "upgrade", proof])

        if result is None or result.returncode != 0:
            log(f"Upgrade failed or remains pending: {proof.name}")
            continue

        log(f"Upgrade command completed: {proof.name}")

        verify = run([OTS, "verify", proof])

        if verify is not None and verify.returncode == 0:
            log(f"OTS verification command succeeded: {proof.name}")
        else:
            log(
                f"Verification not confirmed for {proof.name}; "
                "check the OTS output and retry later."
            )


def main():
    check_setup()
    log("Automatic OTS checkpoint service started.")

    while True:
        try:
            create_checkpoint()
            timestamp_unstamped_checkpoints()
            upgrade_pending_proofs()

        except KeyboardInterrupt:
            log("Automatic OTS service stopped by user.")
            break

        except Exception as exc:
            log(f"UNEXPECTED ERROR: {type(exc).__name__}: {exc}")

        log(f"Next cycle in {INTERVAL_SECONDS // 60} minutes.")
        try:
            time.sleep(INTERVAL_SECONDS)
        except KeyboardInterrupt:
            log("Automatic OTS service stopped by user.")
            break


if __name__ == "__main__":
    main()
