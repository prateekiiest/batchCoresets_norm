# Writing Provenance for VS Code / Cursor

Automated, local provenance capture for editor buffer changes and Cursor AI/editor events. The system distinguishes events emitted by the editor/tool from inferences about who authored text.

## What is captured automatically

### Cursor hooks

The project hook configuration in `.cursor/hooks.json` records supported Cursor events, including:
- agent session start/end and completion;
- prompt submission (prompt hash and character count only);
- agent response (response hash and character count only);
- Agent file edits and inline Tab edits (file path plus hashes and lengths of old/new text).

**Raw prompts, responses, edit text, tool arguments, shell commands, transcripts, and model reasoning are not written to the provenance log.** Hashes and metadata stay local in `.writing-provenance/cursor-events.jsonl`. Cursor must load/enable the project's hooks for these events to be captured. Hook support can vary by Cursor version and execution mode; check Cursor's Hooks output channel.

### VS Code extension

The extension observes document-change events, including unsaved buffers, while enabled. By default, it stores buffer hashes and metadata, not text. Full buffer snapshots are optional and disabled by default. Tracking is off until you explicitly enable it in the Command Palette, and resets on restart.

## Evidence classes

| Evidence class | Meaning | Does not prove |
|---|---|---|
| `editor_observed` | VS Code reported a document buffer/change event | Who authored the text or whether AI was used |
| `editor_or_ai_tool_observed` | Cursor emitted the named hook event | That every changed character came from AI, or that every AI interaction was captured |
| Inference (not an event) | A downstream analysis correlates AI events with subsequent document changes | Definitive authorship or causal attribution |

There is **no manual AI-use annotation command**. Cursor hooks automatically record only events Cursor exposes. A VS Code-only extension cannot universally detect every AI provider, browser chat, or third-party extension's activity. Provider-specific integration is required for other tools.

## Privacy defaults

- No telemetry, network calls, automatic uploads, keylogging, clipboard capture, screenshots, or raw prompt/response/content logging.
- Cursor prompt and response hashes can still reveal equality across repeated content and are not a substitute for a privacy review. Do not add raw content fields to the hook logger.
- VS Code buffer hashes and change metadata are recorded only while tracking is explicitly enabled.
- Logs live under `.writing-provenance/`, which is ignored by Git. Review logs before sharing them.
- Full VS Code buffer snapshots are off by default; enabling them stores confidential text locally.

## Tamper evidence and verification

Both event logs are append-only JSONL with SHA-256 event hashes linked to the previous event hash. Verify them from the repository root:

```bash
python3 scripts/verify_provenance.py
```

The verifier checks the chain and reports the final hash for each available log. To make the final hash independently verifiable, preserve it somewhere outside the machine or use a trusted signature/timestamp service. A local user with write access can rewrite and re-hash the entire log. A hash chain alone is not a digital signature or trusted timestamp.

## Install / enable

1. Open the repository in Cursor. Review `.cursor/hooks.json` and the hook script before enabling project hooks.
2. Confirm Cursor reports the hooks as loaded in its Hooks interface/output channel. Hook behavior depends on Cursor version and execution mode.
3. For VS Code, open `vscode-provenance/`, press F5 to launch an Extension Development Host, and enable local tracking in the target workspace.
4. Run `python3 scripts/verify_provenance.py` to check existing logs.

## Limitations

- Cursor hooks observe only supported hook events, not every possible AI interaction or every model provider.
- Hook events and document changes can be correlated, but timing alone does not prove the origin of every character.
- The extension records document-change events, not individual keystrokes.
- Observation timestamps are not guaranteed edit timestamps.
- This is provenance evidence, not an AI detector, authorship proof, or guarantee that logs are impossible to alter.
