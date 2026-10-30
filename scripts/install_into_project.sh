#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 1 ]]; then
  echo "Usage: $0 /absolute/path/to/research-git-repository" >&2
  exit 2
fi
SOURCE="$(cd "$(dirname "$0")" && pwd)"
TARGET="$(cd "$1" && pwd)"
if [[ ! -e "$TARGET/.git" ]]; then
  echo "Target must be a local Git working tree: $TARGET" >&2
  exit 2
fi
mkdir -p "$TARGET/scripts"
for name in macos_provenance.py install_macos_provenance.py verify_macos_provenance.py export_public_evidence.py; do
  cp "$SOURCE/$name" "$TARGET/scripts/$name"
done
touch "$TARGET/.gitignore"
if ! grep -qxF '.writing-provenance/' "$TARGET/.gitignore"; then
  printf '\n# Private local research provenance (never commit raw logs or snapshots)\n.writing-provenance/\n' >> "$TARGET/.gitignore"
fi
python3 "$TARGET/scripts/install_macos_provenance.py" --root "$TARGET"
echo "Installed collector for: $TARGET"
echo "The scripts and .gitignore change are in the target working tree; review and commit them."
