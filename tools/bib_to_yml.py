#!/usr/bin/env python3
"""
Convert a BibTeX file into _data/publications.yml.

WHICH SOURCE TO EXPORT FROM
    ORCID is strongly preferred over Google Scholar.

    Scholar truncates every author list at ten names with "and others", and
    exports no DOIs at all — so titles can't be linked and author lists come
    out incomplete. ORCID's export carries full author lists and DOIs, because
    the records come from Crossref.

    ORCID (recommended)
      1. Sign in at https://orcid.org and open your record.
      2. Works -> the three-dot menu -> "Export works to BibTeX".
      3. Save as  tools/publications.bib

    Zotero / Paperpile / EndNote also work and give the same fields.

    Google Scholar (fallback, lossy)
      Profile -> select all -> Export -> BibTeX.

HOW TO RUN
    python3 tools/bib_to_yml.py tools/publications.bib --merge

    --merge   keep manual edits (url, doi, code, data, selected...) on
              entries that already exist, matched on title. Use this every
              time after the first run.
    --dry-run print the result instead of writing the file.

WHAT IT PRODUCES
    Each entry gets a `url:` used to link the title — the DOI resolver link
    where a DOI exists, otherwise whatever `url` the BibTeX carried.

    Author names become "Váša F" style, lab members are wrapped in ** ** to
    render bold. Edit LAB_MEMBERS below to control who is bolded.

    Joint senior authorship: add a backslash-escaped asterisk after each
    shared senior author (`Smith J\\*, Jones A\\*`) and set
    `note: "\\* joint senior authors"`. The backslash keeps Markdown from
    reading the asterisk as emphasis.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

# --- People whose names should render in bold -------------------------
# Match on surname (case-insensitive). Add new lab members here.
LAB_MEMBERS = [
    "vasa", "baljer", "song", "karoui", "robiolio", "briski",
    "ulett", "wijesinghe",
]

# Surnames that need non-ASCII restored, since Scholar exports mangled forms
NAME_FIXES = {
    "Vasa F": "Váša F",
    "Vertes PE": "Vértes PE",
}

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "_data", "publications.yml")


# ---------------------------------------------------------------- parsing
def strip_braces(s):
    s = s.strip().strip(",").strip()
    while s and s[0] in "{\"" and s[-1] in "}\"":
        s = s[1:-1].strip()
    return s


ACCENTS = {
    "'": "\u0301",   # acute      \'a  -> á
    "`": "\u0300",   # grave
    '"': "\u0308",   # diaeresis  \"o  -> ö
    "^": "\u0302",   # circumflex
    "~": "\u0303",   # tilde
    "v": "\u030c",   # caron      \v s -> š
    ".": "\u0307",   # dot above
    "=": "\u0304",   # macron
    "c": "\u0327",   # cedilla
    "u": "\u0306",   # breve
}


# Standalone LaTeX character commands. Longest first — \aa must be tried
# before \a would be. \i and \j are dotless i/j, used under accents as in
# {\'\i} for í, so these must be resolved BEFORE the accent pass runs.
SPECIALS = [
    ("aa", "å"), ("AA", "Å"), ("ae", "æ"), ("AE", "Æ"),
    ("oe", "œ"), ("OE", "Œ"), ("ss", "ß"),
    ("o", "ø"), ("O", "Ø"), ("l", "ł"), ("L", "Ł"),
    ("i", "i"), ("j", "j"),
]


def unlatex(s):
    """Turn the commoner LaTeX accent forms into real characters.

    Handles all of:  \\'a   \\'{a}   {\\'a}   {\\' a}   \\v s   \\v{s}   {\\v{s}}
    and dotless forms such as  {\\'\\i}  ->  í
    """
    import unicodedata

    # resolve \i, \aa, \o ... first so the accent pass sees plain letters
    for cmd, ch in SPECIALS:
        s = re.sub(r"\\%s(?![a-zA-Z])" % cmd, ch, s)

    def repl(m):
        comb = ACCENTS.get(m.group(1))
        if comb is None:
            return m.group(0)
        return unicodedata.normalize("NFC", m.group(2) + comb)

    pattern = r"\\([\'`\"^~v.=cu])\s*\{?\s*([a-zA-Z])\s*\}?"
    prev = None
    while prev != s:                 # repeat: braces can nest
        prev = s
        s = re.sub(pattern, repl, s)

    s = s.replace("\\&", "&").replace("\\%", "%").replace("\\_", "_")
    s = s.replace("---", "—").replace("--", "–").replace("~", " ")
    s = re.sub(r"\\[a-zA-Z]+", "", s)      # drop any remaining commands
    s = re.sub(r"[{}]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def deaccent(s):
    """'Váša' -> 'vasa', for matching lab member surnames."""
    import unicodedata
    return "".join(
        c for c in unicodedata.normalize("NFKD", s.lower())
        if not unicodedata.combining(c)
    )


def parse_bib(text):
    """Return a list of dicts, one per @entry."""
    entries = []
    for chunk in re.split(r"\n(?=@)", text):
        chunk = chunk.strip()
        if not chunk.startswith("@"):
            continue
        m = re.match(r"@(\w+)\s*\{\s*([^,]*),", chunk)
        if not m:
            continue
        entry = {"_type": m.group(1).lower(), "_key": m.group(2).strip()}
        body = chunk[m.end():]
        # field = value pairs, values possibly brace-nested
        for fm in re.finditer(r"(\w+)\s*=\s*", body):
            name = fm.group(1).lower()
            rest = body[fm.end():].lstrip()
            if not rest:
                continue
            if rest[0] == "{":
                depth, i = 0, 0
                for i, ch in enumerate(rest):
                    if ch == "{":
                        depth += 1
                    elif ch == "}":
                        depth -= 1
                        if depth == 0:
                            break
                val = rest[1:i]
            elif rest[0] == '"':
                j = rest.find('"', 1)
                val = rest[1:j if j > 0 else None]
            else:
                val = re.split(r"[,\n]", rest, 1)[0]
            entry[name] = unlatex(strip_braces(val))
        entries.append(entry)
    return entries


def format_authors(raw):
    """'Vasa, Frantisek and Bullmore, Edward T' -> '**Váša F**, Bullmore ET'."""
    if not raw:
        return ""
    out = []
    for person in re.split(r"\s+and\s+", raw):
        person = person.strip()
        if not person:
            continue
        if person.lower() in ("others", "et al", "et al."):
            out.append("et al.")
            continue
        if "," in person:
            last, first = person.split(",", 1)
        else:
            bits = person.split()
            last, first = (bits[-1], " ".join(bits[:-1])) if len(bits) > 1 else (person, "")
        last, first = last.strip(), first.strip()
        initials = "".join(b[0] for b in re.split(r"[\s\-]+", first) if b)
        name = ("%s %s" % (last, initials)).strip()
        name = NAME_FIXES.get(name, name)
        if any(mem in deaccent(last) for mem in LAB_MEMBERS):
            name = "**%s**" % name
        out.append(name)
    return ", ".join(out)


def venue_of(e):
    for k in ("journal", "booktitle", "publisher", "school", "institution"):
        if e.get(k):
            return e[k]
    return ""


def details_of(e):
    vol, num, pages = e.get("volume", ""), e.get("number", ""), e.get("pages", "")
    bits = ""
    if vol:
        bits += vol
        if num:
            bits += "(%s)" % num
    if pages:
        bits += (", " if bits else "") + pages
    return bits


def yq(s):
    """Quote a string for YAML."""
    if s is None:
        return ""
    return '"%s"' % str(s).replace("\\", "\\\\").replace('"', '\\"')


def norm_title(s):
    return re.sub(r"[^a-z0-9]+", " ", str(s).lower()).strip()


def crossref_doi(title, year=None, email=None, timeout=20):
    """Look up a DOI by title via the Crossref REST API.

    Returns a DOI string, or None if nothing matched confidently. Crossref
    asks that you identify yourself; passing an email puts you in their
    faster, more reliable pool.
    """
    params = {"query.bibliographic": title, "rows": "5",
              "select": "DOI,title,issued"}
    if email:
        params["mailto"] = email
    url = "https://api.crossref.org/works?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url, headers={"User-Agent": "halflab-site/1.0 (bib_to_yml.py)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as fh:
            items = json.load(fh)["message"]["items"]
    except Exception as exc:
        print("      ! Crossref lookup failed: %s" % exc)
        return None

    want = norm_title(title)
    for it in items:
        got = norm_title((it.get("title") or [""])[0])
        if not got:
            continue
        # Require a close title match; Crossref happily returns loose hits,
        # and a wrong DOI is worse than no link at all.
        if got == want or (want in got or got in want) and \
                abs(len(got) - len(want)) < 0.25 * max(len(got), len(want)):
            if year:
                parts = it.get("issued", {}).get("date-parts", [[None]])
                got_year = parts[0][0] if parts and parts[0] else None
                if got_year and abs(int(got_year) - int(year)) > 1:
                    continue
            return it.get("DOI")
    return None


# ---------------------------------------------------------------- output
HEADER = '''# ============================================================
#  PUBLICATIONS
#
#  Generated by tools/bib_to_yml.py from a BibTeX export.
#  To refresh, re-export (ORCID preferred — see the script) and run
#
#      python3 tools/bib_to_yml.py tools/publications.bib --merge
#
#  --merge keeps url / code / data / selected and anything else you
#  added by hand. Without it, the file is rebuilt from scratch.
#
#  FIELDS
#    url       where the title links to. Prefer the publisher page
#              (a https://doi.org/... link resolves there).
#    selected  1, 2, 3 ... marks a paper for the home page, in that
#              order. Leave blank for everything else.
#    note      free text shown after the venue, e.g. footnote for
#              joint senior authorship.
#
#  Joint senior authors: put a backslash-escaped asterisk after each
#  name (Smith J\\*, Jones A\\*) and set note: "\\* joint senior authors".
# ============================================================

publications:
'''

# Fields never overwritten by a re-import when --merge is used.
# There is deliberately no separate `doi` field — a DOI belongs in `url`
# as a https://doi.org/... link, since the title is what gets linked.
KEEP_FIELDS = ["url", "preprint", "pdf", "code", "data", "note", "selected"]


def load_existing(path):
    """Very small reader: pull manual link fields keyed by title."""
    if not os.path.exists(path):
        return {}
    keep, title = {}, None
    for line in open(path, encoding="utf-8"):
        m = re.match(r'\s*-\s*title:\s*"(.*)"\s*$', line)
        if m:
            title = m.group(1).replace('\\"', '"').lower()
            continue
        if title:
            m2 = re.match(r"\s*(%s):\s*(\S.*?)\s*$" % "|".join(KEEP_FIELDS), line)
            if m2 and not m2.group(2).startswith("#"):
                keep.setdefault(title, {})[m2.group(1)] = m2.group(2)
    return keep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bibfile")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--merge", action="store_true",
                    help="preserve url/code/data/selected from the existing file")
    ap.add_argument("--crossref", action="store_true",
                    help="look up missing DOIs by title via the Crossref API")
    ap.add_argument("--email",
                    help="your email, passed to Crossref for a faster queue")
    args = ap.parse_args()

    if not os.path.exists(args.bibfile):
        sys.exit("No such file: %s\nSee the instructions at the top of this script." % args.bibfile)

    entries = parse_bib(open(args.bibfile, encoding="utf-8", errors="replace").read())
    if not entries:
        sys.exit("No BibTeX entries found in %s" % args.bibfile)

    existing = load_existing(OUT) if args.merge else {}

    def year_of(e):
        m = re.search(r"\d{4}", e.get("year", ""))
        return int(m.group()) if m else 0

    entries.sort(key=year_of, reverse=True)

    lines = [HEADER]
    truncated, no_link = [], []

    for e in entries:
        title = e.get("title", "").strip()
        if not title:
            continue
        prev = existing.get(title.lower(), {})
        authors = format_authors(e.get("author", ""))
        if "et al." in authors:
            truncated.append(title)

        # Link target: an explicit url from a previous hand edit wins, then
        # the DOI resolver, then whatever url/eprint the BibTeX carried.
        link = prev.get("url", "").strip()
        if not link:
            if e.get("doi"):
                link = "https://doi.org/%s" % e["doi"].replace("https://doi.org/", "")
            elif e.get("url"):
                link = e["url"]
            elif e.get("eprint") and "arxiv" in e.get("archiveprefix", "").lower():
                link = "https://arxiv.org/abs/%s" % e["eprint"]

        if not link and args.crossref:
            print("   looking up: %s" % title[:66])
            doi = crossref_doi(title, year_of(e) or None, args.email)
            if doi:
                link = "https://doi.org/%s" % doi
                print("      -> %s" % doi)
            else:
                print("      -> no confident match")
            time.sleep(0.4)          # be polite to the API

        if not link:
            no_link.append(title)

        lines.append("")
        lines.append("  - title: %s" % yq(title))
        lines.append("    authors: %s" % yq(authors))
        lines.append("    year: %s" % (year_of(e) or ""))
        lines.append("    venue: %s" % yq(venue_of(e)))
        det = details_of(e)
        lines.append("    details: %s" % (yq(det) if det else ""))
        lines.append("    url: %s" % link)
        for f in KEEP_FIELDS:
            if f == "url":
                continue
            lines.append("    %s: %s" % (f, prev.get(f, "")))

    out = "\n".join(lines) + "\n"

    if args.dry_run:
        print(out)
        return

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(out)
    print("Wrote %d publications to %s" % (len(entries), os.path.relpath(OUT, REPO)))
    if args.merge and existing:
        print("Preserved manual fields on %d existing entries." % len(existing))

    if truncated:
        print("\n  %d entries have truncated author lists ('et al.')." % len(truncated))
        print("  Google Scholar cuts author lists at ten names. Re-export from")
        print("  ORCID to get them in full — see the notes at the top of this script.")
    if no_link:
        print("\n  %d entries have no link." % len(no_link))
        if not args.crossref:
            print("  Re-run with --crossref to look up DOIs by title, e.g.")
            print("      python3 tools/bib_to_yml.py %s --merge --crossref \\"
                  % os.path.relpath(args.bibfile, REPO))
            print("          --email you@kcl.ac.uk")
        else:
            print("  Crossref had no confident match for these — they are")
            print("  probably preprints or conference papers without a DOI.")
        print("  Titles without a `url:` fall back to a Google Scholar search,")
        print("  so every entry on the site stays clickable either way.")


if __name__ == "__main__":
    main()
