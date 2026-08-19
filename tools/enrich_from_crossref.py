#!/usr/bin/env python3
"""Fill in publisher links and full author lists from Crossref.

Works directly on _data/publications.yml — no BibTeX export needed. For every
entry that is missing a `url`, or whose author list was truncated to "et al."
by Google Scholar, it looks the paper up on Crossref by title and writes back:

    url      https://doi.org/<DOI>, which resolves to the publisher's page
    authors  the complete list, formatted and bolded like the rest of the file

Everything else you have edited by hand — selected, note, preprint, data,
code, venue — is left exactly as it is.

USAGE

    python3 tools/enrich_from_crossref.py --dry-run     # see what it would do
    python3 tools/enrich_from_crossref.py               # write the changes
    python3 tools/enrich_from_crossref.py --details     # also fill empty
                                                        # volume/issue/pages
    python3 tools/enrich_from_crossref.py --force       # re-check entries
                                                        # that already have
                                                        # a url

Crossref asks that you identify yourself; --email puts you in their faster,
more reliable pool. It is optional and is only ever sent to Crossref.

    python3 tools/enrich_from_crossref.py --email you@example.ac.uk

Responses are cached in tools/.crossref-cache.json, so a second run costs
nothing and you can re-run --dry-run freely while reviewing.

WHAT IT WILL NOT DO

Nothing that is not in Crossref gets touched — OpenReview and SSRN entries,
mostly. Those are reported at the end for you to fill by hand. A match also
has to be convincing: the title has to agree and the year has to be within a
year, because a wrong DOI on a publication list is worse than no link.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
PUBS = os.path.join(REPO, "_data", "publications.yml")
CACHE = os.path.join(HERE, ".crossref-cache.json")

# The name formatting rules live in bib_to_yml.py — who gets bolded, which
# surnames need their accents restored. Import them rather than restating
# them, so the two scripts cannot drift apart.
sys.path.insert(0, HERE)
from bib_to_yml import format_authors, norm_title            # noqa: E402


# ---------------------------------------------------------------- Crossref

def load_cache():
    try:
        with open(CACHE, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def save_cache(cache):
    with open(CACHE, "w", encoding="utf-8") as fh:
        json.dump(cache, fh, indent=1, sort_keys=True)


def query(title, email=None, timeout=25):
    """Ask Crossref for the five best matches to a title."""
    params = {
        "query.bibliographic": title,
        "rows": "5",
        "select": "DOI,title,author,container-title,issued,volume,issue,page",
    }
    if email:
        params["mailto"] = email
    url = "https://api.crossref.org/works?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url, headers={"User-Agent": "halflab-site/1.0 (enrich_from_crossref.py)"})
    with urllib.request.urlopen(req, timeout=timeout) as fh:
        return json.load(fh)["message"]["items"]


def pick(items, title, year):
    """The one convincing match, or None.

    Crossref returns loose hits happily, so this insists on the titles
    agreeing and, where we know the year, on it being within one — papers
    move between 'online first' and an issue.
    """
    want = norm_title(title)
    for it in items:
        got = norm_title((it.get("title") or [""])[0])
        if not got:
            continue
        close = got == want or (
            (want in got or got in want)
            and abs(len(got) - len(want)) < 0.25 * max(len(got), len(want))
        )
        if not close:
            continue
        if year:
            parts = (it.get("issued") or {}).get("date-parts") or [[None]]
            got_year = parts[0][0] if parts and parts[0] else None
            if got_year and abs(int(got_year) - int(year)) > 1:
                continue
        return it
    return None


def authors_from(item):
    """Crossref's author objects -> the 'Last, First and Last, First' form
    that format_authors already knows how to render."""
    people = []
    for a in item.get("author") or []:
        if a.get("family"):
            people.append("%s, %s" % (a["family"], a.get("given", "")))
        elif a.get("name"):                      # consortia and groups
            people.append(a["name"])
    return " and ".join(people)


def details_from(item):
    """Volume(issue), pages — matching how the file already writes them."""
    vol = (item.get("volume") or "").strip()
    issue = (item.get("issue") or "").strip()
    page = (item.get("page") or "").strip()
    bits = []
    if vol:
        bits.append("%s(%s)" % (vol, issue) if issue else vol)
    if page:
        bits.append(page)
    return ", ".join(bits)


# ------------------------------------------------------------------- file

FIELD = r"^(    %s: *)(.*)$"


def get_field(block, name):
    m = re.search(FIELD % name, block, re.M)
    return m.group(2).strip() if m else ""


def set_field(block, name, value):
    """Replace a field's value, quoting the way the rest of the file does."""
    if value and (value.startswith(" ") or ":" in value or '"' in value):
        value = '"%s"' % value.replace('"', "'")
    elif value and (value[0] in "&*#{}[]!|>%@`" or value.strip() != value):
        value = '"%s"' % value
    out, n = re.subn(FIELD % name, lambda m: m.group(1) + value, block,
                     count=1, flags=re.M)
    return out if n else block


def main():
    ap = argparse.ArgumentParser(
        description="Fill publisher links and full author lists from Crossref.")
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would change, write nothing")
    ap.add_argument("--force", action="store_true",
                    help="also re-check entries that already have a url")
    ap.add_argument("--details", action="store_true",
                    help="also fill volume/issue/pages where empty")
    ap.add_argument("--email", help="your email, for Crossref's polite pool")
    ap.add_argument("--delay", type=float, default=1.0,
                    help="seconds between requests (default 1)")
    ap.add_argument("--max-authors", type=int, default=25,
                    help="leave the author list alone above this many names "
                         "(default 25)")
    args = ap.parse_args()

    text = open(PUBS, encoding="utf-8").read()

    # Split on the entry marker. `head` is the comment block and the
    # `publications:` key, which must be written back untouched; each body is
    # everything after "  - title: " for one entry, its own title included as
    # the first line.
    SEP = "\n  - title: "
    parts = text.split(SEP)
    if len(parts) < 2:
        sys.exit("Could not find any entries in %s" % PUBS)
    head, bodies = parts[0], parts[1:]

    cache = load_cache()
    changed, skipped, unmatched, oversized, fetched = [], [], [], [], 0

    for i, block in enumerate(bodies):
        # The title is the first line of the body, not an indented field.
        title = block.split("\n", 1)[0].strip().strip('"')
        year = get_field(block, "year")
        url = get_field(block, "url")
        authors = get_field(block, "authors").strip('"')
        truncated = "et al." in authors

        if not title:
            continue
        if url and not truncated and not args.force:
            skipped.append(title)
            continue

        key = norm_title(title)
        if key in cache:
            item = cache[key]
        else:
            print("  [%2d/%d] %s" % (i + 1, len(bodies), title[:64]))
            try:
                items = query(title, args.email)
            except Exception as exc:
                print("        ! lookup failed: %s" % exc)
                unmatched.append((title, str(exc)))
                continue
            fetched += 1
            item = pick(items, title, year)
            cache[key] = item
            save_cache(cache)
            time.sleep(args.delay)

        if not item:
            unmatched.append((title, "no convincing match"))
            continue

        notes = []
        new = block

        doi = item.get("DOI")
        if doi and (not url or args.force):
            link = "https://doi.org/" + doi
            if link != url:
                new = set_field(new, "url", link)
                notes.append("url")

        full = authors_from(item)
        n_authors = len(item.get("author") or [])
        if full and truncated and n_authors > args.max_authors:
            # Crossref lists every member of a consortium after the byline, so
            # a paper credited to "... and the NSPN Consortium" comes back with
            # sixty names; some genuinely have over a hundred. Neither belongs
            # on a publication list, so keep the abbreviated form.
            oversized.append((title, n_authors))
        elif full and truncated:
            formatted = format_authors(full)
            if formatted and "et al." not in formatted:
                new = set_field(new, "authors", formatted)
                notes.append("authors (%d)" % n_authors)

        if args.details and not get_field(block, "details"):
            det = details_from(item)
            if det:
                new = set_field(new, "details", det)
                notes.append("details")

        if notes:
            bodies[i] = new
            changed.append((title, ", ".join(notes)))

    out = head + "".join(SEP + b for b in bodies)

    print("\n" + "=" * 60)
    print("  %d entries updated, %d already complete, %d unmatched"
          % (len(changed), len(skipped), len(unmatched)))
    print("  %d Crossref requests (the rest came from the cache)" % fetched)
    print("=" * 60)
    for t, what in changed:
        print("  + %-52s %s" % (t[:52], what))
    if unmatched:
        print("\n  Not found — fill these in by hand:")
        for t, why in unmatched:
            print("  - %-52s %s" % (t[:52], why))
    if oversized:
        print("\n  Author list left abbreviated (too many names to list):")
        for t, n in oversized:
            print("  . %-52s %d authors" % (t[:52], n))

    if args.dry_run:
        print("\n  --dry-run: nothing written.")
        return
    if not changed:
        print("\n  Nothing to write.")
        return

    backup = PUBS + ".bak"
    open(backup, "w", encoding="utf-8").write(text)
    open(PUBS, "w", encoding="utf-8").write(out)
    print("\n  Written to _data/publications.yml")
    print("  Previous version kept at _data/publications.yml.bak")


if __name__ == "__main__":
    main()
