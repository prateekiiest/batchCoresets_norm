
import hashlib
import json
import time
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
LOG_DIR = ROOT / "research-log"
ACTIVITY = LOG_DIR / "AUTO_ACTIVITY.jsonl"
DAILY = LOG_DIR / "DAILY_LOG.md"
DECISIONS = LOG_DIR / "DECISIONS.md"
STATE = ROOT / ".evidence-watcher-state.json"

EXTENSIONS = {".tex", ".md", ".bib", ".py", ".json", ".csv", ".txt"}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def head():
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT, capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else None


def watched_files():
    return sorted(
        p for p in PAPER.rglob("*")
        if p.is_file() and p.suffix.lower() in EXTENSIONS
        and ".git" not in p.parts
    )


def append_json(path, record):
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def main():
    LOG_DIR.mkdir(exist_ok=True)
    PAPER.mkdir(exist_ok=True)

    if STATE.exists():
        state = json.loads(STATE.read_text())
    else:
        # Establish a baseline; don't claim existing drafts were just edited.
        state = {
            str(p.relative_to(ROOT)): digest(p)
            for p in watched_files()
        }
        STATE.write_text(json.dumps(state, indent=2))
        print("Baseline saved. Subsequent saved changes will be logged.")

    print("Watching paper/ every 3 seconds. Press Ctrl-C to stop.")

    try:
        while True:
            for p in watched_files():
                rel = str(p.relative_to(ROOT))
                sha = digest(p)

                if state.get(rel) == sha:
                    continue

                record = {
                    "timestamp": now(),
                    "path": rel,
                    "sha256": sha,
                    "size_bytes": p.stat().st_size,
                    "git_head": head(),
                    "event": "file_created_or_changed"
                }

                append_json(ACTIVITY, record)
                with DAILY.open("a", encoding="utf-8") as f:
                    f.write(
                        f"- **{record['timestamp']}**: changed `{rel}`; "
                        f"SHA-256 `{sha}`; {record['size_bytes']} bytes.\n"
                    )

                # Only record decisions explicitly written by you.
                for line_no, line in enumerate(
                    p.read_text(encoding="utf-8", errors="replace").splitlines(), 1
                ):
                    marker = "DECISION:"
                    if marker in line:
                        decision = line.split(marker, 1)[1].strip()
                        if decision:
                            key = f"{rel}::{decision}"
                            if key not in state.get("_decisions", []):
                                with DECISIONS.open("a", encoding="utf-8") as f:
                                    f.write(
                                        f"\n- **{now()}** — `{rel}:{line_no}`: "
                                        f"{decision}\n"
                                    )
                                state.setdefault("_decisions", []).append(key)

                state[rel] = sha
                STATE.write_text(json.dumps(state, indent=2))

                print(f"[{record['timestamp']}] Logged {rel}")

            time.sleep(3)

    except KeyboardInterrupt:
        print("\nWatcher stopped. Remember to commit and push your logs.")


if __name__ == "__main__":
    main()
