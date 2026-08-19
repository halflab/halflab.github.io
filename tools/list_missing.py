#!/usr/bin/env python3
"""
List publications that still need attention, so you know exactly what to
look up rather than working through all of them.

    python3 tools/list_missing.py

Prints two lists:
  * entries with no `url:` — these show a Crossref search link on the site
    instead of going straight to the publisher;
  * entries whose author list is truncated with "et al." — only a fuller
    source (Zotero or ORCID) can fix these.

Paste the titles into Zotero's "Add Item(s) by Identifier" box once you have
their DOIs, then re-export and run tools/bib_to_yml.py.
"""

import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YML = os.path.join(REPO, "_data", "publications.yml")


def entries(text):
    for block in text.split("\n  - title: ")[1:]:
        title = block.split('"')[1] if '"' in block else "?"
        def field(name):
            m = re.search(r"^    %s:[ \t]*(.*)$" % name, block, re.M)
            return (m.group(1).strip() if m else "")
        yield title, field("year"), field("url"), field("authors")


def main():
    if not os.path.exists(YML):
        raise SystemExit("No _data/publications.yml yet.")
    rows = list(entries(open(YML, encoding="utf-8").read()))

    no_url = [(t, y) for t, y, u, a in rows if not u]
    cut = [(t, y) for t, y, u, a in rows if "et al." in a]

    print("%d publications total\n" % len(rows))

    print("NO LINK (%d) — need a DOI:" % len(no_url))
    for t, y in sorted(no_url, key=lambda r: r[1], reverse=True):
        print("  %s  %s" % (y or "----", t))

    print("\nTRUNCATED AUTHORS (%d) — need a fuller source:" % len(cut))
    for t, y in sorted(cut, key=lambda r: r[1], reverse=True):
        print("  %s  %s" % (y or "----", t))

    print("\nBoth lists shrink to nothing once you import from Zotero or ORCID.")


if __name__ == "__main__":
    main()
