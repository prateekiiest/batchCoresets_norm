#!/usr/bin/env python3
"""Background macOS collector for saved research files and Git HEAD changes."""
import argparse, hashlib, json, os, subprocess, time, uuid
from datetime import datetime, timezone
from pathlib import Path

EXTS={".tex",".bib",".md",".rst",".txt",".py",".ipynb",".r",".jl",".js",".ts",".tsx",".jsx",".json",".yaml",".yml",".toml",".ini",".cfg",".sh",".bash",".zsh",".sql",".csv",".tsv",".jsonl",".log",".pdf",".png",".jpg",".jpeg",".svg",".eps",".webp",".html",".htm",".css",".xml"}
EXCLUDED={".git",".writing-provenance",".venv","venv","__pycache__","node_modules",".ipynb_checkpoints",".tox",".mypy_cache",".pytest_cache","data","datasets","vendor"}
MAX_BYTES=25*1024*1024
ZERO="0"*64

def now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds")
def digest(data): return hashlib.sha256(data).hexdigest()
def filehash(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

class Collector:
    def __init__(self,root,interval,hours):
        self.root=Path(root).resolve(); self.store=self.root/".writing-provenance"
        self.snap=self.store/"snapshots"; self.events=self.store/"macos-events.jsonl"
        self.statefile=self.store/"macos-state.json"; self.manifests=self.store/"manifests"
        for p in (self.store,self.snap,self.manifests):
            p.mkdir(parents=True,exist_ok=True,mode=0o700)
            try:p.chmod(0o700)
            except OSError:pass
        self.state=json.loads(self.statefile.read_text()) if self.statefile.exists() else {"files":{},"git_head":None}
        self.interval=max(2,interval); self.manifest_interval=max(1,hours)*3600; self.last_manifest=0

    def append(self,fields):
        prev=ZERO
        if self.events.exists():
            try:
                with self.events.open("rb") as f:
                    f.seek(0,2); size=f.tell(); f.seek(max(0,size-65536))
                    lines=f.read().decode("utf-8","replace").splitlines()
                    if lines:prev=json.loads(lines[-1]).get("event_hash",ZERO)
            except Exception:prev="CHAIN_READ_ERROR"
        e={"schema":"research-activity/v1","observed_at_utc":now(),"event_id":str(uuid.uuid4()),**fields,"previous_event_hash":prev}
        e["event_hash"]=digest(json.dumps(e,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode())
        with self.events.open("a",encoding="utf-8") as f:f.write(json.dumps(e,sort_keys=True,ensure_ascii=False)+"\n")
        try:self.events.chmod(0o600)
        except OSError:pass

    def scan(self):
        seen=set()
        for dp,dirs,names in os.walk(self.root):
            dirs[:]=[d for d in dirs if d not in EXCLUDED and not d.startswith(".Trash")]
            for name in names:
                p=Path(dp)/name
                if p.suffix.lower() not in EXTS and name not in {"Makefile","Dockerfile","requirements.txt","environment.yml"}:continue
                try:
                    if p.is_symlink() or p.stat().st_size>MAX_BYTES:continue
                    rel=p.relative_to(self.root).as_posix(); data=p.read_bytes()
                except OSError:continue
                seen.add(rel); h=digest(data); old=self.state["files"].get(rel)
                if old and old["sha256"]==h:continue
                stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
                snap=self.snap/f"{stamp}_{h[:12]}_{p.name}"
                snap.write_bytes(data)
                try:snap.chmod(0o600)
                except OSError:pass
                self.append({"event_type":"file_baseline" if old is None else "saved_file_version","evidence_class":"filesystem_observed","path":rel,"sha256":h,"previous_sha256":old.get("sha256") if old else None,"size_bytes":len(data),"snapshot":snap.relative_to(self.root).as_posix(),"interpretation":"Saved file state observed by polling; not a keystroke or exact edit-time record."})
                self.state["files"][rel]={"sha256":h,"snapshot":snap.relative_to(self.root).as_posix()}
        for rel,old in list(self.state["files"].items()):
            if rel not in seen:
                self.append({"event_type":"file_absent_at_scan","evidence_class":"filesystem_observed","path":rel,"previous_sha256":old.get("sha256"),"interpretation":"Previously observed file absent at scan time; reason unknown."})
                del self.state["files"][rel]
        try:
            r=subprocess.run(["git","rev-parse","HEAD"],cwd=self.root,capture_output=True,text=True,timeout=5)
            if r.returncode==0:
                head=r.stdout.strip()
                if head!=self.state.get("git_head"):
                    self.append({"event_type":"git_head_observed","evidence_class":"git_observed","commit":head,"previous_commit":self.state.get("git_head"),"interpretation":"Locally observed Git HEAD; does not establish authorship."})
                    self.state["git_head"]=head
        except (OSError,subprocess.SubprocessError):pass
        tmp=self.statefile.with_suffix(".tmp"); tmp.write_text(json.dumps(self.state,sort_keys=True,indent=2)+"\n")
        try:tmp.chmod(0o600)
        except OSError:pass
        tmp.replace(self.statefile)

    def manifest(self):
        logs={}
        for name,p in (("macos",self.events),("cursor",self.store/"cursor-events.jsonl"),("vscode",self.store/"vscode-events.jsonl"),("legacy",self.store/"events.jsonl")):
            if p.is_file():logs[name]={"sha256":filehash(p),"bytes":p.stat().st_size}
        artifacts={}
        try:
            r=subprocess.run(["git","ls-files","-z"],cwd=self.root,capture_output=True,check=True)
            for n in r.stdout.decode().split("\0"):
                if n:
                    p=self.root/n
                    if p.is_file() and not p.is_symlink() and p.stat().st_size<=MAX_BYTES:artifacts[n]={"sha256":filehash(p),"bytes":p.stat().st_size}
        except Exception:pass
        m={"schema_version":1,"created_at_utc":now(),"git_head":self.state.get("git_head"),"logs":logs,"tracked_artifacts":artifacts,"note":"Local manifest; independently timestamp its hash for external time evidence."}
        m["manifest_payload_sha256"]=digest(json.dumps(m,sort_keys=True,separators=(",",":")).encode())
        out=self.manifests/f"manifest-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
        out.write_text(json.dumps(m,sort_keys=True,indent=2)+"\n")
        try:out.chmod(0o600)
        except OSError:pass
        self.append({"event_type":"manifest_created","evidence_class":"local_manifest","path":out.relative_to(self.root).as_posix(),"sha256":filehash(out),"interpretation":"Local manifest; timestamp is not independently trusted."})

    def run(self):
        print(f"Research provenance running for {self.root}",flush=True)
        while True:
            self.scan()
            if time.monotonic()-self.last_manifest>=self.manifest_interval:
                self.manifest(); self.last_manifest=time.monotonic()
            time.sleep(self.interval)

def main():
    p=argparse.ArgumentParser();p.add_argument("--root",default=".");p.add_argument("--interval",type=int,default=5);p.add_argument("--manifest-hours",type=int,default=6);a=p.parse_args()
    try:Collector(a.root,a.interval,a.manifest_hours).run()
    except KeyboardInterrupt:print("Collector stopped.")
if __name__=="__main__":main()
