#!/usr/bin/env python3
"""Audit local research-provenance logs and produce a reviewer-friendly report."""
import argparse, hashlib, json, os, sys, urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
STORE=ROOT/".writing-provenance"
ZERO="0"*64
LOGS={
 "macOS filesystem collector":(STORE/"macos-events.jsonl","sorted"),
 "Cursor hooks":(STORE/"cursor-events.jsonl","sorted"),
 "VS Code extension":(STORE/"vscode-events.jsonl","insertion"),
}

def digest(data): return hashlib.sha256(data).hexdigest()

def verify_log(path, ordering):
    if not path.exists(): return {"present":False,"valid":None,"events":0,"error":None,"records":[]}
    previous,records=ZERO,[]
    try:
        for n,line in enumerate(path.read_text(encoding="utf-8").splitlines(),1):
            if not line.strip(): continue
            e=json.loads(line); stored=e.get("event_hash"); unsigned=dict(e); unsigned.pop("event_hash",None)
            canonical=json.dumps(unsigned,ensure_ascii=False,sort_keys=(ordering=="sorted"),separators=(",",":"))
            if e.get("previous_event_hash")!=previous: raise ValueError(f"previous hash mismatch at line {n}")
            if not isinstance(stored,str) or digest(canonical.encode())!=stored: raise ValueError(f"event hash mismatch at line {n}")
            previous=stored; records.append(e)
    except Exception as exc:
        return {"present":True,"valid":False,"events":len(records),"error":f"{type(exc).__name__}: {exc}","records":records}
    return {"present":True,"valid":True,"events":len(records),"error":None,"final_hash":previous,"records":records}

def summarize():
    logs={name:verify_log(path,order) for name,(path,order) in LOGS.items()}
    types,classes,exts,cursor_types,models=Counter(),Counter(),Counter(),Counter(),Counter()
    times=[]; checked=0; failures=[]
    for name,info in logs.items():
        for e in info["records"]:
            types[e.get("event_type","unknown")]+=1
            classes[e.get("evidence_class","unspecified")]+=1
            if e.get("observed_at_utc"): times.append(e["observed_at_utc"])
            p=e.get("path")
            if isinstance(p,str) and p: exts[Path(p).suffix.lower() or "[no extension]"]+=1
            if name=="Cursor hooks":
                cursor_types[e.get("event_type","unknown")]+=1
                model=e.get("model") or e.get("model_id")
                if model: models[str(model)]+=1
            if name=="macOS filesystem collector" and e.get("snapshot"):
                checked+=1; snap=ROOT/e["snapshot"]
                if not snap.is_file(): failures.append("missing snapshot")
                elif digest(snap.read_bytes())!=e.get("sha256"): failures.append("snapshot hash mismatch")
    present=[n for n,x in logs.items() if x["present"]]
    invalid=[n for n,x in logs.items() if x["present"] and not x["valid"]]
    cursor_ai=sum(v for k,v in cursor_types.items() if any(t in k.lower() for t in ("prompt","agent","tab","generation","response")))
    if invalid or not present: verdict="INCONCLUSIVE — provenance logs are missing or failed integrity checks"
    elif cursor_ai: verdict="AI-TOOL ACTIVITY OBSERVED — Cursor hook events were recorded"
    elif logs["Cursor hooks"]["present"]: verdict="NO CURSOR AI EVENTS OBSERVED IN THIS LOG — this is not evidence that AI was never used"
    else: verdict="INCONCLUSIVE — no Cursor hook log is available; absence of a log cannot establish non-use"
    gaps=[
      "Offline ideation and thoughts are not observable.",
      "Browser literature searches, external chat tools, terminal commands, and other devices are not comprehensively monitored.",
      "Cursor events are visible only when hooks are installed, enabled, and functioning.",
      "Editor hashes and file snapshots do not identify the person or tool that produced text.",
      "Polling can miss edits that occur and revert between scans; Overleaf changes appear only after local synchronization.",
      "A local user can stop or rewrite logs. Hash chains detect inconsistency, not a determined administrator.",
      "AI-text detectors and writing-style scores are not treated as authorship proof."
    ]
    return {
      "generated_at_utc":datetime.now(timezone.utc).isoformat(),"verdict":verdict,
      "integrity":{"logs_present":present,"logs_invalid":invalid,"per_log":{n:{k:v for k,v in x.items() if k!="records"} for n,x in logs.items()},"snapshot_hashes_checked":checked,"snapshot_failures":failures},
      "activity":{"total_observed_events":sum(x["events"] for x in logs.values()),"event_types":dict(sorted(types.items())),"evidence_classes":dict(sorted(classes.items())),"file_extensions_observed":dict(sorted(exts.items())),"first_observed_utc":min(times) if times else None,"last_observed_utc":max(times) if times else None},
      "ai_tool_observations":{"cursor_event_types":dict(sorted(cursor_types.items())),"cursor_model_labels":dict(sorted(models.items())),"cursor_ai_related_event_count":cursor_ai,"interpretation":"A Cursor hook event shows that Cursor emitted that event. It does not quantify AI-generated text. No matching event means only that none appears in the available Cursor log."},
      "coverage_gaps":gaps,
      "scope":"Metadata-only audit. No document contents, prompts, responses, snapshots, absolute paths, or usernames are included."
    }

def ai_review(summary,model):
    key=os.environ.get("OPENAI_API_KEY")
    if not key: raise RuntimeError("--ai-review requires OPENAI_API_KEY")
    prompt=("Act as an independent, cautious research-provenance reviewer. Review only the metadata below. "
      "Never infer non-use from missing events. Return Markdown with executive assessment, AI-use observations, "
      "integrity, coverage gaps, and a qualified verdict. Allowed verdicts: AI-tool activity observed; "
      "No AI-tool activity observed in instrumented logs; non-use not established; Inconclusive. "
      "Do not assign probabilities or accuse the researcher. This is not proof of authorship or universal non-use.\n\n"
      "CONTENT-FREE EVIDENCE SUMMARY:\n"+json.dumps(summary,ensure_ascii=False))
    payload=json.dumps({"model":model,"messages":[{"role":"system","content":"You are a cautious evidence-limited auditor."},{"role":"user","content":prompt}],"temperature":0.1}).encode()
    req=urllib.request.Request("https://api.openai.com/v1/chat/completions",data=payload,headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},method="POST")
    with urllib.request.urlopen(req,timeout=90) as response: data=json.loads(response.read().decode())
    return data["choices"][0]["message"]["content"]

def render(s,ai_text=None,model=None):
    a,i=s["activity"],s["integrity"]
    lines=["# Research Process & AI-Use Evidence Report","","> **Evidence assessment:** "+s["verdict"],"",
      "- Generated (UTC): "+s["generated_at_utc"],"- Observed events: "+str(a["total_observed_events"]),
      "- Observed period: "+str(a["first_observed_utc"])+" to "+str(a["last_observed_utc"]),
      "- Snapshot hashes checked: "+str(i["snapshot_hashes_checked"]),"- Snapshot failures: "+str(len(i["snapshot_failures"])),"",
      "## 1. Executive assessment","",
      "This report summarizes machine-observed research-workspace metadata. It helps reviewers understand the evidence without reading raw JSONL logs. It is not a certification of authorship or proof that AI was never used.","",
      "## 2. Integrity checks","","| Log source | Present | Hash chain | Events |","|---|---:|---:|---:|"]
    for name,x in i["per_log"].items():
        status="Pass" if x["valid"] is True else "Fail" if x["valid"] is False else "Not available"
        lines.append(f"| {name} | {'Yes' if x['present'] else 'No'} | {status} | {x['events']} |")
    lines += ["","## 3. Research activity observed","",
      "- Event categories: "+json.dumps(a["event_types"],sort_keys=True),
      "- Evidence classes: "+json.dumps(a["evidence_classes"],sort_keys=True),
      "- File types observed: "+json.dumps(a["file_extensions_observed"],sort_keys=True),
      "","Counts describe recorded events, not intellectual contribution, quality, or authorship.",
      "","## 4. AI-tool activity assessment","",
      "- Cursor-related event count: **"+str(s["ai_tool_observations"]["cursor_ai_related_event_count"])+"**",
      "- Cursor event types: "+json.dumps(s["ai_tool_observations"]["cursor_event_types"],sort_keys=True),
      "- Model labels observed: "+json.dumps(s["ai_tool_observations"]["cursor_model_labels"],sort_keys=True),
      "",s["ai_tool_observations"]["interpretation"],"","## 5. Coverage limitations",""]
    lines.extend("- "+x for x in s["coverage_gaps"])
    lines += ["","## 6. Verdict and interpretation","", "**"+s["verdict"]+"**","",
      "The conclusion is limited to the instrumented logs available at audit time. A valid hash chain supports internal consistency; it does not prove completeness, immutability, or authorship.",
      "","## 7. Reproducibility","",
      "Run python3 scripts/analyze_research_evidence.py. The machine-readable summary is public-evidence/research-evidence-audit.json. Keep raw logs and snapshots private; inspect generated files before publishing."]
    if ai_text:
        lines += ["","## 8. Independent AI reviewer assessment","","Reviewer model: "+str(model),"",
          "> The optional reviewer receives aggregate event counts and integrity metadata only. It does not receive raw logs, paths, prompts, responses, document contents, or snapshots.","",ai_text]
    return "\n".join(lines)+"\n"

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir",default="public-evidence")
    p.add_argument("--ai-review",action="store_true",help="send content-free aggregate metadata to the OpenAI API")
    p.add_argument("--model",default=os.environ.get("OPENAI_MODEL","gpt-4.1-mini"))
    args=p.parse_args(); summary=summarize(); review=None
    if args.ai_review:
        try: review=ai_review(summary,args.model)
        except Exception as exc: print(f"AI review failed: {type(exc).__name__}: {exc}",file=sys.stderr); raise SystemExit(2)
    out=ROOT/args.output_dir; out.mkdir(parents=True,exist_ok=True)
    (out/"research-evidence-audit.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (out/"research-evidence-report.md").write_text(render(summary,review,args.model if review else None),encoding="utf-8")
    print("Wrote",out/"research-evidence-report.md"); print("Wrote",out/"research-evidence-audit.json"); print(summary["verdict"])

if __name__=="__main__": main()
