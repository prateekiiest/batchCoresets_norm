#!/usr/bin/env python3
"""Verify the local macOS collector's event hash chain and saved snapshots."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];LOG=ROOT/".writing-provenance"/"macos-events.jsonl";ZERO="0"*64
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--snapshots",action="store_true");a=ap.parse_args()
    if not LOG.exists():print("No macOS event log found.");return 2
    prev=ZERO;count=0
    for n,line in enumerate(LOG.read_text(encoding="utf-8").splitlines(),1):
        try:e=json.loads(line)
        except Exception:print(f"Invalid JSON at line {n}");return 1
        stored=e.get("event_hash");base=dict(e);base.pop("event_hash",None)
        actual=hashlib.sha256(json.dumps(base,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
        if e.get("previous_event_hash")!=prev or stored!=actual:
            print(f"Hash-chain failure at line {n}");return 1
        if a.snapshots and e.get("snapshot"):
            p=ROOT/e["snapshot"]
            if not p.is_file() or sha(p)!=e.get("sha256"):
                print(f"Snapshot mismatch at line {n}: {e.get('path')}");return 1
        prev=stored;count+=1
    print(f"Valid: {count} events; final event hash {prev}")
    return 0
if __name__=="__main__":sys.exit(main())
