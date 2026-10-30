# Reviewer-friendly research evidence report

The local analyzer converts private provenance logs into two readable, sanitized outputs:

- public-evidence/research-evidence-report.md: reviewer-facing narrative.
- public-evidence/research-evidence-audit.json: machine-readable audit summary.

Run it from the monitored project root:

```bash
python3 scripts/analyze_research_evidence.py
```

It verifies available macOS, Cursor, VS Code, and legacy event hash chains; checks saved macOS snapshot hashes; summarizes observed event types and editor activity; and reports the AI-tool events explicitly emitted by the configured Cursor hooks. It does not publish or transmit raw logs, file contents, prompts, responses, snapshots, absolute paths, or usernames.

## Optional independent AI review

The deterministic audit is offline and is the primary source of counts and integrity results. If you want a second, model-generated interpretation of the aggregate report, set an API key and opt in explicitly:

```bash
export OPENAI_API_KEY="..."
python3 scripts/analyze_research_evidence.py --ai-review
```

Optionally select a model with OPENAI_MODEL or --model. The AI reviewer receives only aggregate event counts, event categories, integrity status, coverage limitations, and the qualified deterministic verdict. It does not receive raw logs, file paths, prompts, responses, document contents, or snapshots. The API key is read from the environment and is never written to the report. Review the model provider's data-handling terms before enabling this option. The default offline mode makes no network requests.

The model output is a second opinion, not a forensic finding. The deterministic audit remains authoritative for the computed log counts and chain checks. The model is instructed not to infer non-use from missing records.

## Reading the verdict

Possible outcomes include:

- **AI-tool activity observed:** configured Cursor hooks recorded prompt/agent/response/edit-related events. This is evidence that Cursor emitted those events, not a measurement of how much text was generated.
- **No Cursor AI events observed in this log:** the Cursor log exists but contains no matching event types. This does not establish that AI was never used.
- **Inconclusive:** logs are missing or fail verification, or no Cursor hook log is available.

A missing Cursor log is not equivalent to a verified zero-use record. The system cannot observe offline thinking, all browser activity, external AI services, arbitrary terminal commands, other devices, or work outside monitored folders. A local user can also stop or rewrite local logs. Hash-chain checks establish internal consistency of the records that remain, not completeness or resistance to a determined administrator.

Do not describe this report as proof of human authorship or universal AI non-use. It is a compact, auditable summary of the evidence the instrumentation actually collected. Keep .writing-provenance/ private and inspect both generated outputs before publishing.
