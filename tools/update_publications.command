#!/bin/bash
# ============================================================
#  Fill in publisher links and full author lists.
#
#  Double-click this file in Finder. It shows you what it would
#  change, asks before changing anything, and keeps a backup.
#
#  Nothing else is needed — no export, no setup.
# ============================================================

cd "$(dirname "$0")/.." || exit 1

clear
echo "============================================================"
echo "  Publications — filling in links and full author lists"
echo "============================================================"
echo

# macOS ships python3 only once the developer command line tools are there.
if ! command -v python3 >/dev/null 2>&1; then
  echo "  python3 is not installed on this Mac."
  echo
  echo "  Run this once in Terminal, accept the prompt, and wait for it"
  echo "  to finish — then double-click this file again:"
  echo
  echo "      xcode-select --install"
  echo
  read -r -p "  Press return to close. "
  exit 1
fi

echo "  Step 1 of 2 — checking Crossref. Nothing is being changed yet."
echo "  This takes about a minute the first time, and is instant after."
echo

python3 tools/enrich_from_crossref.py --dry-run
STATUS=$?

if [ $STATUS -ne 0 ]; then
  echo
  echo "  Something went wrong above. Nothing has been changed."
  read -r -p "  Press return to close. "
  exit 1
fi

echo
echo "============================================================"
echo "  Step 2 of 2"
echo
echo "  The lines marked + above are what would be written into"
echo "  _data/publications.yml. Your own edits — selected, note,"
echo "  preprint, data, venue — are not touched."
echo "============================================================"
echo
read -r -p "  Apply these changes? [y/N] " REPLY
echo

case "$REPLY" in
  [yY]|[yY][eE][sS])
    python3 tools/enrich_from_crossref.py
    echo
    echo "  Done. The previous version is at:"
    echo "      _data/publications.yml.bak"
    echo
    echo "  Ask Claude to rebuild the preview to see the result."
    ;;
  *)
    echo "  Nothing changed."
    ;;
esac

echo
read -r -p "  Press return to close. "
