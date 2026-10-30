#!/usr/bin/env bash
# One-command macOS setup for a single research Git working tree.
set -euo pipefail
if [[ $# -ne 1 ]]; then
  echo "Usage: bash scripts/setup_research_provenance.sh /path/to/research-git-repository" >&2
  exit 2
fi
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This one-command installer currently supports macOS only." >&2
  exit 2
fi
TOOL_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="$(cd "$1" && pwd)"
if [[ ! -e "$TARGET/.git" ]]; then
  echo "Target must already be a Git working tree: $TARGET" >&2
  exit 2
fi
if ! command -v code >/dev/null 2>&1; then
  echo "VS Code's 'code' command is not on PATH. In VS Code, run 'Shell Command: Install code command in PATH', then rerun this installer." >&2
  exit 2
fi
if ! command -v npx >/dev/null 2>&1; then
  echo "Node.js/npm (including npx) is required to package the VS Code extension." >&2
  exit 2
fi
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
echo "[1/3] Packaging the local VS Code extension..."
(
  cd "$TOOL_ROOT/vscode-provenance"
  npx --yes @vscode/vsce package --no-dependencies --out "$TMP_DIR/writing-provenance.vsix"
)
echo "[2/3] Installing the extension into VS Code..."
code --install-extension "$TMP_DIR/writing-provenance.vsix" --force
echo "[3/3] Installing the background collector and safe project integrations..."
bash "$TOOL_ROOT/scripts/install_into_project.sh" "$TARGET"
echo
echo "Setup completed for: $TARGET"
echo "In VS Code, open this project and run:"
echo "  Writing Provenance: Initialize This Research Workspace"
echo "Confirm the consent dialog to start editor metadata capture. Reload VS Code if the command is not yet visible."
echo "No raw editor text is stored by default. Review the evidence before sharing it."
