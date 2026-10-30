#!/usr/bin/env python3
"""Create a sanitized reviewer manifest; never copy private event logs or snapshots."""
import argparse,hashlib,json,subprocess,shutil
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];STORE=ROOT/".writing-provenance"
def h(p):
    x=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):x.update(b)
    return x.hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--output",default="public-evidence/research-provenance.json");ap.add_argument("--include-paths",action="store_true");a=ap.parse_args()
    check=subprocess.run(["python3",str(ROOT/"scripts"/"verify_macos_provenance.py"),"--snapshots"],cwd=ROOT)
    if check.returncode: raise SystemExit("Private macOS provenance verification failed; export refused.")
    events=STORE/"macos-events.jsonl";counts=Counter();first=last=None
    if events.exists():
        for line in events.read_text().splitlines():
            e=json.loads(line);counts[e.get("event_type","unknown")]+=1;t=e.get("observed_at_utc")
            if t:first=min(first,t) if first else t;last=max(last,t) if last else t
    r=subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,capture_output=True,text=True);commit=r.stdout.strip() if r.returncode==0 else None
    artifacts={}
    r=subprocess.run(["git","ls-files","-z"],cwd=ROOT,capture_output=True)
    if r.returncode==0:
        for n in r.stdout.decode().split("\0"):
            if not n:continue
            p=ROOT/n
            if p.is_file() and not p.is_symlink() and p.stat().st_size<=25*1024*1024:
                key=n if a.include_paths else p.suffix.lower() or "[no-extension]"
                item={"sha256":h(p),"bytes":p.stat().st_size}
                if a.include_paths:artifacts[key]=item
                else:artifacts.setdefault(key,[]).append(item)
    result={"schema_version":1,"generated_at_utc":datetime.now(timezone.utc).isoformat(),"repository_commit":commit,"observed_period":{"first_event_utc":first,"last_event_utc":last},"event_counts":dict(sorted(counts.items())),"tracked_artifacts":artifacts,"private_log_sha256":h(events) if events.exists() else None,"privacy":"No raw event records, prompts, document contents, local absolute paths, usernames, or browser history are included.","coverage_limitations":["Filesystem polling observes saved states, not every keystroke, unsaved buffer, thought, or exact edit time.","Git commits and hashes do not prove authorship or absence of AI assistance.","Overleaf edits are observed only after synchronization into this local Git working tree.","No claim is made about other devices, accounts, or unmonitored channels."]}
    out=ROOT/a.output;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    package=out.parent/"reviewer-package"; md=package/"manifests"; md.mkdir(parents=True,exist_ok=True)
    for stale in md.glob("manifest-*"): stale.unlink()
    manifest_files=[]
    if (STORE/"manifests").exists():
        for candidate in sorted((STORE/"manifests").glob("manifest-*.json")):
            try:
                if json.loads(candidate.read_text(encoding="utf-8")).get("schema_version")==2: manifest_files.append(candidate)
            except Exception: pass
    if not manifest_files: raise SystemExit("No sanitized v2 manifests found. Keep the collector running until it creates a six-hour manifest, then export again.")
    included=[]; proofs={}
    for source in manifest_files:
        shutil.copyfile(source,md/source.name); included.append(source.name)
        proof=source.with_suffix(source.suffix+".ots")
        if proof.is_file():
            shutil.copyfile(proof,md/proof.name); proofs[proof.name]={"sha256":h(proof),"bytes":proof.stat().st_size}
    index={"package_schema_version":1,"generated_at_utc":datetime.now(timezone.utc).isoformat(),"manifest_files":included,"timestamp_proofs":proofs,"privacy":"Only path-redacted manifests and matching OpenTimestamps proof files are included; raw logs and snapshots are excluded."}
    index_path=package/"package-index.json"; index_path.write_text(json.dumps(index,indent=2,sort_keys=True)+"\n")
    ots=shutil.which("ots")
    if ots:
        try:
            subprocess.run([ots,"stamp",str(index_path)],capture_output=True,text=True,timeout=180,check=True)
            proof=index_path.with_suffix(index_path.suffix+".ots")
            if proof.is_file(): print("Timestamped package inventory:",proof.name)
        except Exception as exc: print("WARNING: package inventory timestamp failed:",type(exc).__name__)
    (package/"README.md").write_text("# Sanitized reviewer package\n\nRun python3 scripts/verify_reviewer_package.py public-evidence/reviewer-package for offline manifest integrity checks. Add --verify-timestamps to invoke OpenTimestamps verification when the ots client is installed. See docs/provenance/REVIEWER_GUIDE.md for interpretation and limitations. This package excludes raw logs, snapshots, prompts, responses, document contents, usernames, and paths.\n")
    print("Wrote",out.relative_to(ROOT));print("Wrote",package.relative_to(ROOT));print("Inspect before publishing.")
if __name__=="__main__":main()
