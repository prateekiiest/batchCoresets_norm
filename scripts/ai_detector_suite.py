#!/usr/bin/env python3
"""Non-blocking AI-content triage: Houtini, Pangram EditLens, and Coderbuds rules."""
import argparse, json, os, re, subprocess, tempfile
from pathlib import Path

TEXT_EXTS = {".tex", ".md", ".rst", ".txt", ".html", ".htm"}
MIN_WORDS, MAX_FILES, MAX_CHARS = 80, 12, 60000

def git(*args):
    p = subprocess.run(["git", *args], text=True, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, errors="replace")
    if p.returncode:
        raise RuntimeError("git command failed: " + p.stderr[-400:])
    return p.stdout

def count_words(s):
    return len(re.findall(r"\b[\w'-]+\b", s))

def commits(base, head):
    if base and set(base) != {"0"}:
        return git("rev-list", "--reverse", base + ".." + head).split()
    return [head]

def diff_paths(base, head):
    if base and set(base) != {"0"}:
        out = git("diff", "--name-only", "--diff-filter=ACMRT", base, head)
    else:
        out = git("diff-tree", "--no-commit-id", "--name-only", "-r", head)
    return [p for p in out.splitlines() if Path(p).suffix.lower() in TEXT_EXTS]

def added_text(path, base, head):
    if base and set(base) != {"0"}:
        diff = git("diff", "--no-ext-diff", "--no-color", "--unified=0", base, head, "--", path)
    else:
        diff = git("show", "--format=", "--no-ext-diff", "--no-color", "--unified=0", head, "--", path)
    return "\n".join(x[1:] for x in diff.splitlines()
                     if x.startswith("+") and not x.startswith("+++")).strip()

def metadata(shas):
    msgs, authors = [], []
    for sha in shas:
        msgs.append(git("show", "-s", "--format=%B", sha))
        authors.append(git("show", "-s", "--format=%an <%ae> | %cn <%ce>", sha).strip())
    return msgs, authors

def coderbuds(rules_dir, messages, authors, added, branch, title, body, labels):
    try:
        import yaml
    except Exception as e:
        return [{"status": "error", "detail": "PyYAML unavailable: " + str(e)}]
    findings = []
    categories = {
        "commit_footers": "\n".join(messages) + "\n" + body,
        "co_author_attributions": "\n".join(messages),
        "html_comments": added,
        "text_patterns": "\n".join([title, body] + messages),
        "branch_patterns": branch,
        "labels": labels,
    }
    rules_dir = Path(rules_dir)
    files = sorted(list(rules_dir.glob("*.yml")) + list(rules_dir.glob("*.yaml")))
    if not files:
        return [{"status": "error", "detail": "No Coderbuds YAML rules found"}]
    for file in files:
        try:
            rule = yaml.safe_load(file.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        tool = rule.get("tool") or {}
        name = tool.get("name") or tool.get("id") or file.stem
        markers = rule.get("explicit_markers") or {}
        for category, haystack in categories.items():
            group = markers.get(category) or []
            if isinstance(group, dict):
                group = [group]
            for m in group:
                if not isinstance(m, dict) or not m.get("pattern"):
                    continue
                try:
                    pat = str(m["pattern"]) if m.get("regex") else re.escape(str(m["pattern"]))
                    if re.search(pat, haystack, re.I):
                        findings.append({"tool": name, "category": category,
                            "confidence": m.get("confidence"),
                            "indicator": m.get("description", "Explicit marker matched"),
                            "rule_file": file.name})
                except re.error:
                    pass
        for m in markers.get("bot_authors") or []:
            if not isinstance(m, dict):
                continue
            for author in authors:
                hit = bool(m.get("email") and str(m["email"]).lower() in author.lower())
                hit |= bool(m.get("username") and str(m["username"]).lower() in author.lower())
                for key in ("email_pattern", "name_pattern"):
                    if m.get(key):
                        try: hit |= bool(re.search(str(m[key]), author, re.I))
                        except re.error: pass
                if hit:
                    findings.append({"tool": name, "category": "bot_authors",
                        "confidence": m.get("confidence"),
                        "indicator": m.get("description", "Bot author matched"),
                        "rule_file": file.name})
    return findings

def numeric_scores(obj, prefix=""):
    found = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = (prefix + "." + str(k)) if prefix else str(k)
            if isinstance(v, (int, float)) and re.search(r"score|prob|ai", str(k), re.I):
                found.append({"field": key, "value": v})
            else:
                found.extend(numeric_scores(v, key))
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:30]):
            found.extend(numeric_scores(v, prefix + "[" + str(i) + "]"))
    return found

def houtini(snippets):
    out = {"detector": "houtini-ai-detect", "status": "skipped", "files": []}
    check = subprocess.run(["bash", "-lc", "command -v ai-detect"], capture_output=True, text=True)
    if check.returncode:
        return {"detector": "houtini-ai-detect", "status": "error", "detail": "ai-detect executable missing"}
    out["status"] = "ok"
    for path, text in snippets:
        tmp = None
        try:
            with tempfile.NamedTemporaryFile("w", suffix=Path(path).suffix or ".txt",
                                             encoding="utf-8", delete=False) as f:
                f.write(text); tmp = f.name
            p = subprocess.run(["ai-detect", "--model", "light", "--json", "--file", tmp],
                               capture_output=True, text=True, errors="replace", timeout=300)
            item = {"path": path, "word_count": count_words(text), "returncode": p.returncode}
            try:
                item["reported_scores"] = numeric_scores(json.loads(p.stdout))
            except Exception:
                m = re.search(r"Model AI score:\s*([0-9.]+%?)\s*(?:-\s*([A-Z ]+))?", p.stdout, re.I)
                if m:
                    item["model_ai_score"] = m.group(1)
                    if m.group(2): item["label"] = m.group(2).strip()
            if p.returncode:
                item["error"] = p.stderr[-300:]; out["status"] = "partial"
            out["files"].append(item)
        except Exception as e:
            out["status"] = "partial"; out["files"].append({"path": path, "error": str(e)})
        finally:
            if tmp and Path(tmp).exists(): Path(tmp).unlink()
    return out

def pangram(snippets):
    out = {"detector": "pangram-editlens", "status": "skipped", "files": []}
    if not snippets:
        out["detail"] = "No changed prose met the minimum length threshold."
        return out
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    if not token:
        out["detail"] = "HF_TOKEN secret missing; accept the gated model terms and add the secret to enable EditLens."
        return out
    try:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        model_id = "pangram/editlens_roberta-large"
        tok = AutoTokenizer.from_pretrained(model_id, token=token)
        model = AutoModelForSequenceClassification.from_pretrained(model_id, token=token)
        model.eval(); out["status"] = "ok"
        for path, text in snippets:
            inputs = tok(text, return_tensors="pt", truncation=True, max_length=512)
            with torch.no_grad():
                probs = torch.softmax(model(**inputs).logits[0], dim=-1)
                n = int(probs.shape[-1])
                score = sum(float(probs[i]) * i / max(1, n - 1) for i in range(n))
                bucket = int(torch.argmax(probs).item())
            out["files"].append({"path": path, "word_count": count_words(text),
                "score_pred": round(score, 4), "bucket_pred": bucket, "num_buckets": n,
                "interpretation": "Normalized EditLens score; not a probability of AI authorship."})
    except Exception as e:
        out["status"] = "error"; out["detail"] = str(e)[:700]
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--rules-dir", default="vendor/coderbuds-ai-detector/rules")
    ap.add_argument("--report", default="ai-detector-report.json")
    ap.add_argument("--markdown-report", default="ai-detector-report.md")
    a = ap.parse_args()
    base, head = a.base.strip(), a.head.strip() or "HEAD"
    shas = commits(base, head)
    messages, authors = metadata(shas)
    snippets, total = [], 0
    for path in diff_paths(base, head):
        text = added_text(path, base, head)
        if count_words(text) < MIN_WORDS or len(snippets) >= MAX_FILES or total >= MAX_CHARS:
            continue
        text = text[:MAX_CHARS-total]
        snippets.append((path, text)); total += len(text)
    branch = os.environ.get("PR_BRANCH") or os.environ.get("GITHUB_REF_NAME", "")
    findings = coderbuds(a.rules_dir, messages, authors,
        "\n".join(t for _, t in snippets), branch,
        os.environ.get("PR_TITLE", ""), os.environ.get("PR_BODY", ""),
        os.environ.get("PR_LABELS", ""))
    detectors = [
        {"detector": "coderbuds-ai-detector", "status": "ok" if not any(f.get("status") == "error" for f in findings) else "error",
         "findings": [f for f in findings if not f.get("status")] ,
         "errors": [f for f in findings if f.get("status") == "error"]},
        houtini(snippets), pangram(snippets)
    ]
    report = {"schema_version": 1, "repository": os.environ.get("GITHUB_REPOSITORY", ""),
        "event": os.environ.get("GITHUB_EVENT_NAME", ""), "base": base or None, "head": head,
        "commit_count": len(shas), "changed_prose_files_scored": len(snippets),
        "prose_word_count_scored": sum(count_words(t) for _, t in snippets),
        "disclaimer": "Triage only, not proof of authorship. False positives and false negatives are expected. Coderbuds matches explicit attribution markers only. EditLens is CC BY-NC-SA 4.0, non-commercial only.",
        "detectors": detectors}
    Path(a.report).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = ["# AI Detector Suite Report", "",
        f"- Repository: {report['repository'] or 'local run'}",
        f"- Event: {report['event'] or 'local run'}",
        f"- Base revision: {base or 'not specified'}",
        f"- Head revision: {head}",
        f"- Commits examined: {len(shas)}",
        f"- Added prose files scored: {len(snippets)}",
        f"- Added prose words scored: {sum(count_words(t) for _, t in snippets)}",
        "", "> **Interpretation:** These results are triage signals, not proof of authorship. False positives and false negatives are expected.", "",
        "## Detector status", ""]
    for d in detectors:
        lines.append("### " + d["detector"])
        lines.append("")
        lines.append("- **Status:** " + d.get("status", "unknown"))
        if d.get("detail"): lines.append("- **Details:** " + d["detail"].replace("\n", " "))
        for f in d.get("findings", [])[:25]:
            lines.append("- **Rule match:** " + str(f.get("tool", "rule")) + " — " + str(f.get("indicator", f.get("category", "match"))))
        for f in d.get("files", []):
            score = f.get("model_ai_score", f.get("score_pred", "see JSON report"))
            lines.append("- **" + f.get("path", "?") + "** (" + str(f.get("word_count", "?")) + " words): score " + str(score))
            if f.get("label") is not None: lines.append("  - Label: " + str(f["label"]))
            if f.get("bucket_pred") is not None: lines.append("  - Predicted bucket: " + str(f["bucket_pred"]))
            if f.get("error"): lines.append("  - Error: " + str(f["error"]).replace("\n", " "))
        lines.append("")
    lines.extend(["## Limitations", "",
        "- A skipped detector may mean no qualifying changed prose was found, not necessarily a setup failure.",
        "- Coderbuds detects explicit attribution markers; it does not detect all AI-assisted content.",
        "- EditLens scores are not probabilities of AI authorship.",
        "- Do not use this report as the sole basis for academic-integrity or disciplinary decisions.", ""])
    Path(a.markdown_report).write_text("\n".join(lines), encoding="utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f: f.write("\n".join(lines) + "\n")
    print(json.dumps({"report": a.report, "markdown_report": a.markdown_report,
        "commits": len(shas), "prose_files": len(snippets),
        "coderbuds_findings": len([f for f in findings if not f.get("status")]),
        "statuses": {d["detector"]: d.get("status") for d in detectors}}, indent=2))

if __name__ == "__main__":
    main()
