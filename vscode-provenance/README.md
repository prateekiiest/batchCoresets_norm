# Writing Provenance for VS Code / Cursor

Local, opt-in evidence for document-buffer changes (including unsaved edits) and explicit AI-interaction annotations.

## Privacy defaults
- Tracking is **off until explicitly enabled** with the Command Palette command **Writing Provenance: Enable Local Tracking** and a modal consent prompt.
- Tracking is enabled only for the current editor window and resets on restart.
- No network requests, telemetry, keylogging, clipboard capture, screenshots, prompt capture, or automatic uploads.
- By default, records hashes and metadata, not text: workspace-relative path, observation time, editor document version, dirty/saved state, character count, and change-size metadata.
- Full buffer snapshots are **off by default**. The optional setting writingProvenance.storeBufferSnapshots can store confidential text locally.
- Logs live under .writing-provenance/ and should remain untracked and private.

## Install for development
1. Open vscode-provenance/ in VS Code or Cursor.
2. Install @vscode/vsce as a developer tool and run vsce package, or press F5 to launch an Extension Development Host.
3. Install the generated VSIX using **Extensions: Install from VSIX...**.
4. In the target workspace, run **Writing Provenance: Enable Local Tracking**.
5. Use **Writing Provenance: Record AI Interaction (Self-Reported)** to add a manual AI-use annotation.

No runtime dependencies beyond the VS Code API and Node.js built-ins.

## Evidence classes
| Evidence class | Meaning | Does not prove |
|---|---|---|
| editor_observed | The extension observed a buffer state or editor event while enabled | Who authored text, exact edit time, or AI use |
| user_self_reported | A user manually recorded an AI interaction | That it occurred exactly as described or that text came from that tool |
| External anchor | A separately retained signature/timestamp or trusted platform record | The entire intellectual history or intent |

There is no universal VS Code API for observing every Cursor, Copilot, ChatGPT, or browser AI interaction. AI annotations are manual, not automatic; provider-specific integration would be required for stronger observed evidence.

## Tamper evidence
Events are JSON Lines in .writing-provenance/vscode-events.jsonl. Each record hashes its JSON fields and the preceding event hash. Run **Writing Provenance: Verify Local Event Log** to detect common edits, deletions, or reordering.

**Limit:** a local user with write access can rewrite the entire log and recompute the chain. The hash chain is not a digital signature, trusted timestamp, or proof that a self-report is true. For stronger evidence, preserve the final log hash outside the machine or use an independently operated timestamp/signature service.

## Limitations
- Records document-change events, not individual keystrokes.
- Unsaved buffers are observed, but default logs retain only hashes, not text. A reviewer needs the exact buffer to compare it to the hash.
- Timestamps are observation times, not guaranteed edit times.
- Only configured extensions are tracked. Multi-root workspaces use the first workspace folder.
- This is a provenance aid, not an authorship detector or proof of authorship.
