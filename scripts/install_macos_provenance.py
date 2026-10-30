#!/usr/bin/env python3
"""Install or remove a per-project macOS LaunchAgent."""
import argparse, hashlib, os, plistlib, subprocess, sys
from pathlib import Path
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=".");ap.add_argument("--uninstall",action="store_true");a=ap.parse_args()
    root=Path(a.root).resolve(); label="org.prateek.research-activity-logger."+hashlib.sha256(str(root).encode()).hexdigest()[:10]; plist=Path.home()/"Library/LaunchAgents"/(label+".plist"); domain=f"gui/{os.getuid()}"
    if a.uninstall:
        subprocess.run(["launchctl","bootout",domain,str(plist)],capture_output=True);plist.unlink(missing_ok=True)
        print("LaunchAgent removed; existing evidence retained.");return
    if not (root/".git").exists():raise SystemExit("Run inside a local Git working tree.")
    script=root/"scripts"/"macos_provenance.py"
    if not script.is_file():raise SystemExit(f"Missing {script}")
    logdir=root/".writing-provenance"/"launchd";logdir.mkdir(parents=True,exist_ok=True,mode=0o700)
    plist.parent.mkdir(parents=True,exist_ok=True)
    payload={"Label":label,"ProgramArguments":[str(Path(sys.executable).resolve()),str(script),"--root",str(root),"--interval","5","--manifest-hours","6"],"WorkingDirectory":str(root),"RunAtLoad":True,"KeepAlive":True,"ProcessType":"Background","StandardOutPath":str(logdir/"stdout.log"),"StandardErrorPath":str(logdir/"stderr.log"),"Umask":63}
    plist.write_bytes(plistlib.dumps(payload,fmt=plistlib.FMT_XML,sort_keys=True));plist.chmod(0o600)
    subprocess.run(["launchctl","bootout",domain,str(plist)],capture_output=True)
    r=subprocess.run(["launchctl","bootstrap",domain,str(plist)],capture_output=True,text=True)
    if r.returncode:raise SystemExit("LaunchAgent load failed: "+r.stderr.strip())
    print("Background collector installed and started.")
    print("Status: launchctl print "+domain+"/"+label)
    print("Uninstall: python3 scripts/install_macos_provenance.py --uninstall")
if __name__=="__main__":main()
