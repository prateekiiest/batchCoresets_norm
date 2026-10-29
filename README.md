# ICML Research Evidence Starter

A paper-specific workspace template for keeping a contemporaneous, reviewable record of research development.

**Scope:** this template helps preserve dated notes, Git history, experiment provenance, and checkpoint hashes. It does not prove that AI was never used, and it must not be presented as an AI-free certificate.

## 1. Start a new private GitHub repository

1. On GitHub, create a **private** repository for the paper, for example `icml-research-record`.
2. Do not add a README or license on GitHub if you plan to push this template as the initial commit.
3. Download/unzip this template, open its folder in VS Code, then run:

```bash
git init
git add .
git commit -m "Initialize research record"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPO.git
git push -u origin main
```

Replace the remote URL with your actual repository URL.

## 2. Set up signed commits (recommended)

GitHub supports SSH-signed commits. Follow GitHub's current documentation to create an SSH signing key, add it to your GitHub account as a **signing key**, and configure Git:

```bash
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/YOUR_SIGNING_KEY.pub
git config --global commit.gpgsign true
```

Make a test commit and check that GitHub displays it as Verified. Keep your private signing key private. Signed commits authenticate a key's signature; they do not independently prove when the underlying research was first done or who wrote the content.

## 3. Use the VS Code workspace

Open this folder in VS Code. Use the integrated terminal and commit small, meaningful updates regularly.

Suggested cadence:
- Start and end each research session by updating `research-log/DAILY_LOG.md`.
- Record hypotheses before running experiments in `research-log/IDEA_LOG.md`.
- Put each experiment's config, commit SHA, seed, environment, and result pointer in `experiments/`.
- Save manuscript versions and decisions in Git, but never commit private data, credentials, or confidential reviewer material.
- After a meaningful milestone, run the checkpoint script.

## 4. Create and verify a checkpoint

```bash
python3 scripts/checkpoint.py --label "first-hypothesis"
python3 scripts/verify_checkpoint.py checkpoints/checkpoint-*.json
```

A checkpoint records the current Git commit and SHA-256 hashes of tracked files. Commit the checkpoint file in a later commit. For stronger independent timestamp evidence, publish the checkpoint hash to a trusted timestamping or transparency service and preserve the returned receipt. This starter does **not** automatically submit to an external service.

## 5. GitHub Actions

A workflow under `.github/workflows/` validates JSON experiment records and checkpoint files on push and pull request. GitHub Actions logs provide a remote record that a workflow ran on a particular commit; they do not prove the research was performed without AI.

## 6. Suggested reviewer evidence bundle

If appropriate for the venue and your disclosure obligations, prepare:
- repository URL and commit history;
- selected signed commits and their verification status;
- checkpoint manifests and any independent timestamp receipts;
- experiment configurations, seeds, commit hashes, and reproducibility instructions;
- concise explanation of the logging scope and limitations.

Do not flood reviewers with raw logs. Share only what is relevant and safe to disclose. Do not claim stronger guarantees than the evidence supports.

## What this can and cannot show

**Can show:** a repository contains certain content at particular commits; signatures verify against configured public keys; checkpoint hashes match the files supplied; GitHub Actions ran tests on recorded commits.

**Cannot show:** that AI was never used, that all ideation occurred in the repository, that a local machine was never tampered with, or that a commit timestamp is an independently trusted timestamp.

This is a workflow template, not forensic certification or a substitute for following the conference's current AI-use and disclosure policy.
