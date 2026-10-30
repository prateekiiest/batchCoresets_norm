## Automatic macOS research provenance

For a background collector on macOS, see [the installation guide](docs/macos-automatic-provenance.md). From a local Git working tree, run:

```bash
python3 scripts/install_macos_provenance.py
```

The LaunchAgent starts at login, restarts after an unexpected exit, and records saved file states, local Git HEAD changes, and six-hour artifact manifests under the private, Git-ignored `.writing-provenance/` directory. It complements the existing Cursor hooks and VS Code extension. Enable Cursor hooks once with `python3 .cursor/hooks/record_provenance.py --enable`; enable the VS Code extension separately.

Overleaf Git synchronization is captured only after changes are synchronized into the monitored local Git working tree. The collector does not automatically push/pull or store Overleaf credentials.

Verify local event-chain and snapshot integrity:

```bash
python3 scripts/verify_macos_provenance.py --snapshots
```

Generate sanitized reviewer evidence (no raw logs or snapshots):

```bash
python3 scripts/export_public_evidence.py
```

Keep raw logs and snapshots private. A local collector is not tamper-proof against the Mac owner and does not prove authorship, complete research activity, or absence of AI use. See the installation guide for coverage and limitations.

---

# Research Activity Logging and AI-Content Triage

Utilities for maintaining a contemporaneous record of research-draft changes and running lightweight, non-blocking AI-content triage checks in GitHub Actions.

> **Important:** Activity logs, Git history, timestamps, and AI-detector scores are supporting evidence, not proof of authorship or a complete record of how work was produced. AI-detector results can be wrong in both directions.

## Contents

- [Research activity logger](#research-activity-logger)
- [Evidence and checkpoint workflow](#evidence-and-checkpoint-workflow)
- [AI Detector Suite](#ai-detector-suite)
- [Privacy, limitations, and licensing](#privacy-limitations-and-licensing)
- [Repository layout](#repository-layout)

## Research activity logger

The file watcher `scripts/watch_draft.py` records changes to saved files in the `paper/` directory while it is running.

### What it watches and records

Supported extensions:

- Research/text files: `.tex`, `.md`, `.bib`
- Supporting files: `.py`, `.json`, `.csv`, `.txt`

For each observed file change, it appends an entry to `research-log/AUTO_ACTIVITY.jsonl` with the UTC observation timestamp, file path, SHA-256 digest, file size, currently checked-out Git commit, and event type. It also appends a short entry to `research-log/DAILY_LOG.md`.

To mark an explicit decision in a monitored file, include a line such as:

```text
DECISION: Evaluate the selection method under a fixed token budget.
```

The watcher records decision markers in `research-log/DECISIONS.md`, subject to its deduplication logic.

### Run from a terminal

From the repository root:

```bash
python3 scripts/watch_draft.py
```

Leave the process running while editing and stop it with `Ctrl+C` when finished.

### Optional VS Code task

You can create `.vscode/tasks.json` with this task definition:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Research: Start Activity Logging",
      "type": "process",
      "command": "python3",
      "args": ["scripts/watch_draft.py"],
      "options": { "cwd": "${workspaceFolder}" },
      "isBackground": true,
      "problemMatcher": [],
      "runOptions": { "instanceLimit": 1 },
      "presentation": {
        "reveal": "always",
        "panel": "dedicated",
        "clear": false
      }
    }
  ]
}
```

Run it in VS Code with **Cmd+Shift+P** (macOS) or **Ctrl+Shift+P** (Windows/Linux), choose **Tasks: Run Task**, then select **Research: Start Activity Logging**.

### Logger limitations

- It observes **saved-file changes**, not every keystroke or unsaved editor buffer.
- It records only while running; the first run establishes a baseline rather than reconstructing earlier edits.
- Timestamps indicate when the watcher noticed a change, not necessarily the exact time the edit was made.
- It does not automatically commit or push changes, or independently timestamp them.

## Local writing provenance (saved versions and assistance labels)

The separate tool `scripts/provenance.py` is intended to address local draft evolution. Unlike GitHub Actions, it runs on your own machine and keeps its records in the ignored, local-only `.writing-provenance/` directory.

Start it from the repository root before editing:

```bash
python3 scripts/provenance.py watch paper
```

You can pass additional files/directories, for example `python3 scripts/provenance.py watch paper notes/draft.tex`. It records observed saved versions, SHA-256 hashes, snapshots, the current Git HEAD, and missing-file observations. Stop it with `Ctrl+C`. It does not record unsaved keystrokes, recover changes made before it started, or determine whether a change came from an AI tool.

Manual self-reported assistance labels are intentionally not part of the workflow. For supported Cursor Agent/Tab events, use the automatic hooks documented below; activity outside those hooks remains unobserved.\n\nRecords and snapshots stay local and are ignored by Git by default. Back them up securely if you want to retain them; do not publish them unless you intentionally choose to. This is an honest provenance aid, not a surveillance tool or a way to prove authorship.

## Evidence and checkpoint workflow

For important milestones, combine contemporaneous notes, Git history, reproducible experiment records, and independent timestamping.

For the VS Code/Cursor event logs, create a privacy-preserving manifest containing the SHA-256 digest of each available log, then timestamp that manifest with OpenTimestamps:

```bash
python3 -m pip install --user opentimestamps-client
python3 scripts/anchor_provenance.py
```

This validates the event chains first, then submits only a manifest of log hashes (not prompts, responses, or edit contents) to public timestamp calendars. Keep the generated `checkpoints/provenance-anchor-*.json` and matching `.ots` proof. A proof may initially be pending; later run `ots upgrade checkpoints/ACTUAL-MANIFEST.json.ots` and verify it with `ots verify checkpoints/ACTUAL-MANIFEST.json.ots`. Copy both files to storage outside this computer (for example, a separate private cloud account or removable drive). The external timestamp supports that the hashed manifest existed no later than the time anchored by the calendar; it does not prove authorship or that the original log was complete. Do not publish the log files themselves unless you intend to disclose their contents.

1. Install the macOS LaunchAgent once in each local research Git working tree (see [the automatic macOS guide](docs/macos-automatic-provenance.md)).
2. Work normally in Cursor/VS Code and commit code/manuscript changes as you usually do. No daily diary or per-edit manual annotation is required by the automatic collector.
3. The background service polls saved files, observes local Git HEAD changes, and writes private manifests every six hours.
4. Optionally install OpenTimestamps with `python3 -m pip install --user opentimestamps-client`; when `ots` is available, the collector automatically requests timestamps for each generated manifest. Pending proofs still need later upgrade/verification.
5. Generate a sanitized reviewer package with `python3 scripts/export_public_evidence.py`. Inspect it before publishing; never publish `.writing-provenance/` or raw snapshots.
6. Keep selected manifests and their `.ots` proofs outside the working Mac/account.

| Evidence | What it can support |
|---|---|
| Git commits | A recorded sequence of committed changes |
| Signed commits | That a commit signature matches the configured signing key |
| File hashes | That contents match a recorded digest |
| Independent timestamps | Evidence that timestamped data existed by an externally anchored time |
| Experiment logs | A documented link between code, configuration, and reported results |

No one mechanism proves the full history of intellectual work. These practices are most useful in combination.

## AI Detector Suite

The workflow [`.github/workflows/ai-detector-suite.yml`](.github/workflows/ai-detector-suite.yml) runs five complementary checks on **pushes**, **pull requests**, and manual runs via **workflow_dispatch**. The checks are designed as review aids: a flag does not prove AI authorship, and no flag does not prove human authorship.

### Detectors

| Detector | What it checks | Access and cost notes |
|---|---|---|
| Stylometric profile | Descriptive writing-style features: sentence length, lexical diversity, word length, punctuation, uppercase/digit ratios | No extra model; features alone do not classify AI authorship |
| [Lukkinen academic-text detector](https://huggingface.co/Lukkinen/ai-text-detector) | Experimental paragraph-level open model targeting English CS/engineering academic text | MIT model weights; opt-in via Actions variable `ENABLE_LUKKINEN=true`; large download and generic pipeline compatibility unverified |
| [Houtini ai-detect](https://github.com/houtini-ai/ai-detect) | A local text classifier applied to qualifying added prose; workflow selects the smaller `light` model | Open source; downloads model files on the runner |
| [Pangram EditLens](https://github.com/pangramlabs/EditLens) | EditLens score/bucket output for qualifying added prose | Optional gated Hugging Face model; requires accepted model terms and a `HF_TOKEN` secret; **CC BY-NC-SA 4.0, non-commercial only** |
| [Coderbuds ai-detector](https://github.com/coderbuds/ai-detector) | YAML rules for explicit tool attribution in supported commit/PR metadata and added HTML comments | Open-source rules; matches explicit markers rather than inferring AI use from writing style |

### What gets analyzed

The workflow compares the base and head revisions and extracts **added lines** from changed `.tex`, `.md`, `.rst`, `.txt`, `.html`, and `.htm` files. Text-classifier input is limited to files with at least **80 words**, with at most **12 files** and **60,000 characters** considered per run. As a result, a detector can be skipped when no changed file meets the threshold; this is expected and does not by itself indicate a credential or model error. Code files are not passed to the text classifiers.

Coderbuds checks explicit attribution rules against available commit messages/authors, branch and PR metadata, and added HTML comments. It is not a general-purpose detector for unmarked AI assistance.

### Enable Pangram EditLens

1. Sign in to Hugging Face and visit the [EditLens model page](https://huggingface.co/pangram/editlens_roberta-large).
2. Review the access conditions and license, then request/accept gated access if the terms are suitable for your use.
3. Create a read token in [Hugging Face token settings](https://huggingface.co/settings/tokens).
4. In this repository, open **Settings → Secrets and variables → Actions → New repository secret** (or visit [Actions secrets](https://github.com/prateekiiest/research-activity-logger/settings/secrets/actions)).
5. Set the secret name to `HF_TOKEN` and paste the token value into GitHub. **Never commit the token or paste it into an issue, log, or chat.**

Without a token, EditLens is skipped and the other checks can continue. A qualifying text sample and an accepted model/token are separate requirements: a run may skip EditLens because there is no qualifying added prose, even when a secret exists.

**Status note:** The EditLens path is experimental and its model-loading/inference path still needs a successful end-to-end run to be considered verified. A successful workflow setup or the presence of `HF_TOKEN` alone does not establish that inference completed correctly.

### Reports and workflow behavior

- The job adds a readable Markdown report to the Actions run summary.
- It uploads both `ai-detector-report.md` (human-readable) and `ai-detector-report.json` (machine-readable) as the `ai-detector-report-<run-id>` artifact, retained for **30 days**.
- The workflow is non-blocking: detector findings alone do not fail a build, and reports are not committed back to the repository.
- It does not call paid detection APIs.

The Lukkinen integration is experimental because its model card describes a custom mean-pooling architecture; the workflow records load/inference errors rather than treating failures as human-written results. Style statistics are descriptive only. See the [detailed detector guide](docs/ai-detector-suite.md) and the [GitHub Actions runs](https://github.com/prateekiiest/research-activity-logger/actions).

## Privacy, limitations, and licensing

- False positives and false negatives are expected. Do not use detector scores as the sole basis for academic-integrity, employment, or disciplinary decisions.
- EditLens is licensed **CC BY-NC-SA 4.0** and is described here for non-commercial research/analysis only. Review the current model terms before use.
- Inference runs on GitHub-hosted runners. Text supplied to the classifiers is processed in that runner environment, and model weights are downloaded from upstream hosts. Do not run this workflow on confidential material unless that processing is acceptable.
- Because this is a public repository, treat workflow logs and artifacts as potentially visible to people with repository access.
- GitHub Actions usage and cache limits may apply. The workflow caches Hugging Face model files where possible, but a cache miss can require another download.

## Repository layout

```text
.github/workflows/ai-detector-suite.yml  # CI workflow for the detector checks
scripts/ai_detector_suite.py             # Diff extraction, detector orchestration, JSON report
scripts/watch_draft.py                   # Saved-file research activity watcher
scripts/checkpoint.py                    # Research checkpoint generation
docs/ai-detector-suite.md                # Detector setup, licensing, and limitations
research-log/                            # Generated activity/decision logs
checkpoints/                             # Generated checkpoint files (if used)
```

Generated logs and checkpoints may be local or ignored by Git depending on repository configuration. Review `git status` and your project's privacy requirements before committing them.


## VS Code / Cursor unsaved-buffer provenance

The [VS Code/Cursor provenance integration](vscode-provenance/README.md) includes an opt-in VS Code extension for unsaved buffer changes and Cursor hooks for automatically recording supported agent prompts, responses, and Agent/Tab file-edit events. Raw prompts, responses, and edit text are not stored; the hook log contains hashes and metadata. Cursor capture requires a one-time local opt-in (`python3 .cursor/hooks/record_provenance.py --enable`) and can be disabled with `--disable`. This is not universal AI-use detection. Verify local hash chains with `python3 scripts/verify_provenance.py`; for independent verification, externally preserve or sign the final hash.
