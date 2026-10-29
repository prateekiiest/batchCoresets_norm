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

## Evidence and checkpoint workflow

For important milestones, combine contemporaneous notes, Git history, reproducible experiment records, and independent timestamping.

1. Start the logger before the research session.
2. Update `IDEA_LOG.md`, `DAILY_LOG.md`, and `DECISIONS.md` where relevant.
3. Commit meaningful changes with descriptive messages and push them to the appropriate remote repository.
4. Generate a checkpoint:

   ```bash
   python3 scripts/checkpoint.py --label "experiment-milestone"
   ```

5. Stamp the actual checkpoint JSON file produced by the script:

   ```bash
   ots stamp checkpoints/ACTUAL-CHECKPOINT-FILENAME.json
   ```

   Replace the example filename with the generated filename. Keep both the JSON checkpoint and its `.ots` proof. A pending OpenTimestamps proof is not yet a completed independent timestamp.
6. When verifying a historical file hash, check out the relevant recorded Git commit first. Retain copies of important records and proofs outside the working directory.

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
4. In this repository, open **Settings → Secrets and variables → Actions → New repository secret** (or visit [Actions secrets](https://github.com/prateekiiest/batchCoresets_norm/settings/secrets/actions)).
5. Set the secret name to `HF_TOKEN` and paste the token value into GitHub. **Never commit the token or paste it into an issue, log, or chat.**

Without a token, EditLens is skipped and the other checks can continue. A qualifying text sample and an accepted model/token are separate requirements: a run may skip EditLens because there is no qualifying added prose, even when a secret exists.

**Status note:** The EditLens path is experimental and its model-loading/inference path still needs a successful end-to-end run to be considered verified. A successful workflow setup or the presence of `HF_TOKEN` alone does not establish that inference completed correctly.

### Reports and workflow behavior

- The job adds a readable Markdown report to the Actions run summary.
- It uploads both `ai-detector-report.md` (human-readable) and `ai-detector-report.json` (machine-readable) as the `ai-detector-report-<run-id>` artifact, retained for **30 days**.
- The workflow is non-blocking: detector findings alone do not fail a build, and reports are not committed back to the repository.
- It does not call paid detection APIs.

The Lukkinen integration is experimental because its model card describes a custom mean-pooling architecture; the workflow records load/inference errors rather than treating failures as human-written results. Style statistics are descriptive only. See the [detailed detector guide](docs/ai-detector-suite.md) and the [GitHub Actions runs](https://github.com/prateekiiest/batchCoresets_norm/actions).

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
