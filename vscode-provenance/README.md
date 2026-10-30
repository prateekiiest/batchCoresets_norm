# Writing Provenance for VS Code / Cursor

Local provenance capture for VS Code document-buffer changes and supported Cursor AI/editor events. Events identify what the instrumented editor reported; they do not establish who authored text.

## One-command setup (macOS)

From the cloned toolkit repository, run:

```bash
bash scripts/setup_research_provenance.sh /absolute/path/to/your/research-git-repository
```

Requirements: macOS, Python 3, Git, Node.js/npm, VS Code, and the VS Code `code` command on PATH. If `code` is missing, in VS Code run **Shell Command: Install 'code' command in PATH**, then rerun the installer.

The script packages and installs this extension, installs the background filesystem/Git collector into the target project, adds `.writing-provenance/` to `.gitignore`, and installs Cursor hooks only if no existing `.cursor/hooks.json` would be overwritten. Existing Cursor hook configuration is left untouched.

After installation, open the target repository in VS Code and run **Writing Provenance: Initialize This Research Workspace** from the Command Palette. Confirm the modal consent prompts. The extension remembers the opt-in across VS Code restarts. Use **Writing Provenance: Disable Tracking** to stop editor capture.

## What is captured

### VS Code

While explicitly enabled, the extension observes document-change events, including unsaved buffers, for configured file extensions. By default it stores relative paths, timestamps, buffer hashes, document versions, change metadata, and dirty/saved state, not document text. Full buffer snapshots are optional and disabled by default.

### Cursor

When project hooks are installed and enabled, supported Cursor events may include agent session start/end, prompt/response metadata, Agent file edits, and inline Tab edits. Prompt/response content and edit text are not written to the hook log; hashes and metadata remain local. Hook coverage depends on Cursor version and execution mode. If the project already has `.cursor/hooks.json`, merge the supplied hook entries manually rather than replacing the existing configuration.

## Evidence classes and limitations

| Evidence class | Meaning | Does not prove |
|---|---|---|
| `editor_observed` | VS Code reported a document buffer/change event | Who authored the text or whether AI was used |
| `editor_or_ai_tool_observed` | Cursor emitted the named hook event | That every changed character came from AI, or that every AI interaction was captured |
| Inference (not an event) | Analysis correlates tool events with subsequent changes | Definitive authorship or causation |

A VS Code-only extension cannot universally detect every AI provider, browser chat, terminal workflow, or third-party extension. Missing events are not proof that AI was not used.

## Privacy defaults

- No telemetry, network calls, automatic uploads, keylogging, clipboard capture, or screenshots.
- No raw document text, prompts, or responses are stored by default.
- Full VS Code buffer snapshots are off by default; enabling them stores confidential text locally.
- Logs live under `.writing-provenance/`, which should remain private and ignored by Git.
- Review generated reports and evidence before sharing.

## Verify and report

From the research repository root:

```bash
python3 scripts/verify_macos_provenance.py --snapshots
python3 scripts/analyze_research_evidence.py
```

The macOS verifier checks available collector event chains and saved snapshot hashes. The analyzer writes a reviewer-friendly Markdown report and a JSON audit summary. These checks support integrity review of available records; they do not prove completeness, immutability, or authorship.

## Disable / uninstall

- VS Code: run **Writing Provenance: Disable Tracking**.
- Cursor hooks: `python3 .cursor/hooks/record_provenance.py --disable`.
- macOS background collector: `python3 scripts/install_macos_provenance.py --uninstall --root /absolute/path/to/project`.

Disabling or uninstalling collection does not delete evidence already recorded. Remove local evidence manually only after deciding whether you need to preserve it.
