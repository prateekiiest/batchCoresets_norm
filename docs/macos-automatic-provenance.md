# Automatic macOS research provenance

A per-project macOS LaunchAgent runs the collector in the background.

## Install

First clone this toolkit, then install its collector into each actual paper/code Git working tree. This copies the four runtime scripts into that project, adds the private evidence directory to its `.gitignore`, and installs a project-specific LaunchAgent:

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

Enable existing Cursor hooks with:

```bash
python3 .cursor/hooks/record_provenance.py --enable
```

Enable the existing VS Code extension once per workspace using the Command Palette. The explicit opt-in is persisted in that workspace and tracking resumes when the extension activates on subsequent starts; use the disable command to revoke it.

For Overleaf Git synchronization, synchronize the Overleaf project into the local Git working tree being monitored. The collector observes the resulting saved files and Git HEAD. If Overleaf is a separate clone, install the LaunchAgent from that clone too. This collector deliberately does not push or pull automatically and does not store Overleaf credentials. Never place tokens in committed remotes, shell history, or logs.

## Public reviewer evidence

Generate a sanitized manifest:

```bash
python3 scripts/export_public_evidence.py
```

By default it groups artifact hashes by extension and omits paths. Use `--include-paths` only if reviewers need to verify individual files. The exporter does not copy raw logs or snapshots. Review output before publication. Keep `.writing-provenance/` private.

## External timestamping

A local manifest is not an independent timestamp. If you install OpenTimestamps, the background collector automatically requests a timestamp for each six-hour manifest:

```bash
python3 -m pip install --user opentimestamps-client
```

The request may remain pending until calendar aggregation completes. Keep the JSON and `.ots` proof outside the Mac as well. To manually anchor a selected manifest:

```bash
python3 -m pip install --user opentimestamps-client
ots stamp .writing-provenance/manifests/ACTUAL-MANIFEST.json
```

Preserve the JSON and matching `.ots` proof off the Mac. A proof may initially be pending; later run `ots upgrade FILE.json.ots` and `ots verify FILE.json.ots`.

## Limitations

This is a user-level service and can be stopped or altered by the Mac owner. Polling can miss intermediate changes that occur and revert between scans. Overleaf events are visible only after synchronization. This is supporting evidence, not tamper-proof monitoring, authorship proof, or proof that AI was never used.
