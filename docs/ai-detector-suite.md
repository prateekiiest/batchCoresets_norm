# AI detector suite

The GitHub Actions workflow at .github/workflows/ai-detector-suite.yml runs three complementary, best-effort checks on pushes, pull requests, and manual dispatches.

## What runs

1. **Houtini ai-detect**: a local text classifier. The workflow uses its smaller light model to keep downloads and runtime lower. It examines added prose in .tex, .md, .rst, .txt, .html, and .htm files.
2. **Pangram EditLens**: an open-weight text model that reports its normalized score_pred and predicted bucket for changed prose. This model repository is gated on Hugging Face and is licensed CC BY-NC-SA 4.0 for non-commercial use only. It is optional until you explicitly accept the model terms and configure a Hugging Face token.
3. **Coderbuds ai-detector**: open YAML rules that match explicit tool attributions in commit messages, co-author trailers, added HTML comments, PR title/body, branch names, and commit authors. This does not infer AI use from coding style.

The workflow creates a JSON artifact named ai-detector-report-<run id> and adds a short summary to the Actions run. It does not commit reports back to the repository, fail a build merely because a detector flags content, or call paid detection APIs.

## Enable Pangram EditLens

1. Sign in to Hugging Face and open https://huggingface.co/pangram/editlens_roberta-large.
2. Review and accept the gated model terms and the non-commercial-use condition. Do not enable this model for commercial use unless you have separately confirmed that your use is permitted by its license.
3. Create a Hugging Face access token with permission to read the model.
4. In this repository, open **Settings → Secrets and variables → Actions → New repository secret**.
5. Name the secret HF_TOKEN and set its value to that token.

Without this secret, the workflow marks EditLens as skipped and continues with the other two detectors. Do not put the token in source code or commit it to Git.

## Limitations and privacy

- Results are review signals, not proof of who wrote a passage. False positives and false negatives are expected; a negative result does not prove human authorship.
- Coderbuds only matches explicit attribution markers. It cannot reliably detect unmarked AI-assisted work.
- The workflow analyzes newly added prose, with a minimum of 80 words per file and caps on files and characters per run. Code files are not passed to the text classifiers.
- Inference runs on GitHub-hosted runners. Text passed to the models is processed in that runner environment, and model weights are downloaded from their upstream hosts. Do not use this workflow for confidential text unless that processing is acceptable for your project.
- Houtini's lightweight model is downloaded by the runner; the Hugging Face cache may reduce repeated downloads, but GitHub Actions minutes and cache quotas still apply.
- The report artifact is retained for 30 days. Because this repository is public, treat workflow logs and artifacts as potentially visible to people who can access the repository.
- This is a triage aid for research transparency, not an academic-integrity adjudication tool.

Upstream projects: https://github.com/houtini-ai/ai-detect, https://github.com/coderbuds/ai-detector, https://github.com/pangramlabs/EditLens
