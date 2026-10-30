# Automatic macOS research provenance

A per-project macOS LaunchAgent runs the collector in the background.

## Install

First clone this toolkit, then install its collector into each actual paper/code Git working tree. This copies the runtime scripts, including the reviewer evidence analyzer, into that project, adds the private evidence directory to its `.gitignore`, installs the Cursor hooks and opts them in if the target has no existing Cursor hook configuration, and installs a project-specific LaunchAgent. If you already have `.cursor/hooks.json`, the helper leaves it untouched; merge the hook entries manually:

```bash
git clone -b macos-automatic-provenance https://github.com/prateekiiest/research-activity-logger.git ~/research-activity-logger
bash ~/research-activity-logger/scripts/install_into_project.sh /absolute/path/to/your/paper-repository
bash ~/research-activity-logger/scripts/install_into_project.sh /absolute/path/to/your/code-repository
```

If paper and code already live in the same Git working tree, run the helper once. To install manually from inside a target project after copying the scripts, run `python3 scripts/install_macos_provenance.py`.

It installs a project-specific LaunchAgent under `~/Library/LaunchAgents/` (the label is derived from the absolute project path), starts immediately, restarts after an unexpected exit, and starts at login. You can install it separately in multiple paper/code Git working trees; each gets its own agent and private evidence directory.

Check status:

```bash
launchctl list | grep research-activity-logger
tail -f .writing-provenance/launchd/stderr.log
```

Uninstall without deleting evidence:

```bash
python3 scripts/install_macos_provenance.py --uninstall --root /absolute/path/to/that/project
```

## Captured activity

The collector observes saved file states (manuscript, notes, source, configuration, experiment logs, PDFs and figures), local Git HEAD changes, and periodic manifests. It stores private file snapshots and hash-chained event records under `.writing-provenance/`. It skips common dataset/cache/vendor directories and files larger than 25 MiB.

It does not capture keystrokes, clipboard, screenshots, browser history, prompts, responses, unsaved buffers, thoughts, terminal commands, or experiments' full runtime state. It cannot determine who authored a change or whether AI was used.

## Cursor, VS Code and Overleaf

The project helper enables Cursor hooks when it safely installs a new hook configuration. If you merged hooks manually, enable them with `python3 .cursor/hooks/record_provenance.py --enable`. The filesystem collector captures saved changes regardless of editor; the VS Code extension is optional and adds unsaved-buffer hashes. Enable that extension once per workspace using the Command Palette. The explicit opt-in is persisted in that workspace and tracking resumes when the extension activates on subsequent starts; use the disable command to revoke it.

For Overleaf Git synchronization, synchronize the Overleaf project into the local Git working tree being monitored. The collector observes the resulting saved files and Git HEAD. If Overleaf is a separate clone, install the LaunchAgent from that clone too. This collector deliberately does not push or pull automatically and does not store Overleaf credentials. Never place tokens in committed remotes, shell history, or logs.

## Sanitized reviewer evidence package

Generate the reviewer-facing package:

```bash
python3 scripts/export_public_evidence.py
```

This writes `public-evidence/reviewer-package/` with path-redacted periodic manifests and matching `.ots` proof files when present. It does not include raw event logs, snapshots, prompts, responses, document contents, usernames, or file paths. Keep `.writing-provenance/` private and inspect all generated files before publication.

The installer copies the offline verifier to `scripts/verify_reviewer_package.py`, the reviewer guide to `docs/provenance/REVIEWER_GUIDE.md`, and the schema to `schemas/reviewer-manifest-v2.schema.json`.

Run the offline integrity check:

```bash
python3 scripts/verify_reviewer_package.py public-evidence/reviewer-package
```

It validates manifest payload digests, previous-manifest links, and package inventory using Python's standard library. A PASS establishes consistency of the supplied records, not completeness or authorship.

## External timestamping

Install OpenTimestamps before or during collection:

```bash
python3 -m pip install --user opentimestamps-client
```

When the `ots` executable is available on the shell PATH, the collector attempts to timestamp each six-hour path-redacted manifest. The LaunchAgent inherits the PATH from the environment in which it was installed. If you install OpenTimestamps after the collector, ensure `command -v ots` works in Terminal and reinstall the LaunchAgent with `python3 scripts/install_macos_provenance.py --root .` so its environment is refreshed. This request may remain pending while calendar servers aggregate the commitment. The package exporter copies matching proofs, but does not upgrade them automatically.

To upgrade a pending proof while online:

```bash
ots upgrade .writing-provenance/manifests/ACTUAL-MANIFEST.json.ots
```

Then export the reviewer package again. A reviewer can request proof verification with:

```bash
python3 scripts/verify_reviewer_package.py public-evidence/reviewer-package --verify-timestamps
```

Offline manifest checks do not require network access. OpenTimestamps verification may require network access or locally available Bitcoin header data, depending on proof state and client version. Only describe a timestamp as externally verified after the verifier reports a successful OpenTimestamps verification. A proof file's presence alone is not sufficient.

See [Reviewer guide](reviewer-guide.md) and [Evidence schema](evidence-schema.md) for package interpretation and field definitions.

## Limitations

This is a user-level service and can be stopped or altered by the Mac owner. Polling can miss intermediate changes that occur and revert between scans. Overleaf events are visible only after synchronization. This is supporting evidence, not tamper-proof monitoring, authorship proof, or proof that AI was never used.
