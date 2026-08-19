# half lab website

Source for the **High and Low Field (Network Neuroimaging) Laboratory** website.

Built with [Jekyll](https://jekyllrb.com), hosted on GitHub Pages. You do not
need to know Jekyll to maintain it — almost everything you'll want to change
lives in three plain-text files in `_data/`.

---

## Quick start: the five things you'll actually do

| I want to… | Edit this file |
|---|---|
| Add or change a team member | `_data/people.yml` |
| Add a publication | `_data/publications.yml` |
| Post a news item | new file in `_news/` |
| Change research descriptions | `_data/research.yml` |
| Add a funder or its logo | `_data/funders.yml` |
| Add software, data or teaching material | `_data/resources.yml` |
| Change lab name, email, address, menu | `_config.yml` |

Every one of those files has instructions in comments at the top. You can edit
them directly in the GitHub web interface — click the file, click the pencil
icon, make your change, click "Commit changes". The site rebuilds itself within
a minute or two.

---

## Adding a team member

Open `_data/people.yml` and add a block to the `people:` list:

```yaml
  - name: Jane Doe
    role: PhD Student
    photo: jane.jpg       # put the file in assets/img/team/
    bio: Studies cortical microstructure at 7T.
    email: jane.doe@kcl.ac.uk
    scholar: https://scholar.google.com/citations?user=XXXX
    orcid: 0000-0002-1234-5678
    github: janedoe
    bluesky: janedoe.bsky.social
    website: https://janedoe.com
```

Only `name` and `role` are required — leave anything else blank or delete the
line. If there's no photo yet the site shows a neat initials placeholder, so
you can add people before you have pictures.

**Order on the page** is simply the order in the file. Everyone is shown
identically, in one grid, with no sub-headings — clicking a photo or name
opens that person's bio.

**Photos:** square, roughly 600×600 px, saved as `.jpg`, put in
`assets/img/team/`. Keep files under ~300 KB so pages load quickly.

When someone leaves, move them to the `alumni:` list at the bottom of the file.

---

## Publications

### Filling in links and full author lists (do this first)

The list currently has two gaps: 35 entries have no link, and 28 have author
lists that Google Scholar truncated to "et al.". Both can be filled from
Crossref in one go, without re-exporting anything:

**The easy way:** in Finder, open the `tools` folder and double-click
**`update_publications.command`**. It shows you what it would change, asks
before changing anything, and keeps a backup. Nothing else to install.

If you prefer the Terminal:

```
cd "path/to/half-lab_website"
python3 tools/enrich_from_crossref.py --dry-run
```

That prints what it would change and writes nothing. When the list looks
right, run it again without `--dry-run`. It edits `_data/publications.yml` in
place — everything you have set by hand (`selected`, `note`, `preprint`,
`data`, `venue`) is left alone — and keeps the previous version as
`publications.yml.bak`.

Useful flags:

- `--email you@kcl.ac.uk` — Crossref's polite pool, faster and more reliable.
  The address goes to Crossref and nowhere else.
- `--details` — also fill in empty volume/issue/page.
- `--force` — re-check entries that already have a link.

It takes about a minute for the whole list (one request per second, which is
what Crossref asks for) and caches every response, so re-running is instant.

A match has to be convincing before it is used: the title has to agree and
the year has to be within one. Anything it cannot match confidently is listed
at the end for you to fill by hand — expect the OpenReview and SSRN entries,
which are not in Crossref.

### Importing from Zotero (recommended)

Zotero gives complete author lists *and* DOIs, which is what the site needs —
Google Scholar gives neither reliably.

**One-off setup: build the library from DOIs**

1. In Zotero, make a collection called something like `half lab`.
2. Click the **magic wand** in the toolbar ("Add Item(s) by Identifier").
3. Paste DOIs — **one per line, as many as you like at once**. Zotero fetches
   the full record for each. Same box accepts PMIDs, ISBNs and arXiv IDs.

To get the DOIs to paste, the quickest route is your ORCID record or Scholar
profile; or run `tools/list_missing.py` (below), which prints every entry on
the site that still has no link, so you can look those up alone.

**Every time you publish something new**

1. Add the paper to the collection with the magic wand and its DOI.
2. Right-click the collection → **Export Collection…** → format **BibTeX**
   → save as `tools/publications.bib`.
3. Run:

```bash
python3 tools/bib_to_yml.py tools/publications.bib --merge
```

That rewrites `_data/publications.yml` with linked titles and full author
lists. `--merge` keeps everything you have edited by hand — the `selected`
flags, the OpenNeuro data link and so on.

Set Zotero's **Better BibTeX** plugin aside; the built-in BibTeX export is
enough here.

---

### Importing from Google Scholar (fallback)

Scholar has no API and blocks automated access, so the list can't be pulled
automatically — but exporting takes about thirty seconds, and there's a script
that does the rest.

1. Open your [Scholar profile](https://scholar.google.com/citations?user=wnLacTkAAAAJ&hl=en)
   while signed in.
2. Tick the checkbox at the top of the article list to select all. If you have
   more than 100 papers, click **Show more** and tick again.
3. **Export → BibTeX**, and save the file as `tools/scholar.bib`.
4. Run:

```bash
python3 tools/bib_to_yml.py tools/scholar.bib --merge
```

That rewrites `_data/publications.yml`. The `--merge` flag preserves any DOIs,
preprint links, code links or tags you added by hand, matching on title — so
you can re-import whenever you publish something without losing your edits.

Scholar's BibTeX doesn't include DOIs, so `doi:` comes through empty. Fill in
the ones you care about; they'll survive future imports.

The script bolds lab members' names automatically. To change who gets bolded,
edit the `LAB_MEMBERS` list near the top of `tools/bib_to_yml.py`.

Scholar profiles usually need pruning — they pick up duplicates, preprints
alongside their published versions, and the occasional misattribution. Delete
entries you don't want; they won't come back unless they're still in the `.bib`.

### Adding a publication by hand

Open `_data/publications.yml` and add a block at the top:

```yaml
  - title: "Title of the paper"
    authors: "**Váša F**, Coauthor A, Coauthor B"
    year: 2026
    venue: "Nature Neuroscience"
    details: "29(4), 512–524"
    doi: 10.1038/s41593-026-01234-5
    preprint: https://www.biorxiv.org/content/10.1101/2026.01.01.123456
    code: https://github.com/halflab/paper-code
```

Wrap lab members' names in `**double asterisks**` to bold them. Papers are
grouped by year automatically — you don't need to sort them.

> ⚠️ **Before going public:** the three publications currently in that file
> were drafted from memory as design examples. Running the Scholar import
> above replaces them entirely, which is the easiest way to be rid of them.

---

## Posting news

Create a file in `_news/` named `YYYY-MM-DD-short-title.md`:

```markdown
---
title: "New paper out in PNAS"
date: 2026-09-14
summary: "One-sentence summary shown on the news list and home page."
image: /assets/img/news/figure.png   # optional
---

The body of the post, written in Markdown. **Bold**, *italic*,
[links](https://example.com) and lists all work.
```

The date in the filename and the `date:` line should match. The four most
recent posts appear on the home page automatically.

Delete `_news/2026-08-01-lab-website-launched.md` once you have real posts.

---

## Funder logos

`_data/funders.yml` lists the Gates Foundation, UKRI and the NIHR Maudsley BRC.
Until you add logo files, each shows as a clean text wordmark; drop a file into
`assets/img/funders/` and set the `logo:` line, and the image replaces the text
automatically.

All three funders have brand guidelines and require their own official artwork —
re-drawn or re-coloured versions aren't permitted, so the logos have to be
downloaded from source. Each entry in the file has a `brand:` line pointing at
the right download page. Prefer SVG; otherwise PNG with a transparent
background, around 400 px wide.

Funders also usually specify exact acknowledgement wording. Replace the
`acknowledgement:` text at the bottom of the file with what each one requires.

---

## Changing colours and fonts

All colours and fonts are defined as variables at the top of
`assets/css/style.css`, in the `:root { ... }` block. Change a value there and
it updates everywhere on the site.

The current palette is taken directly from the logo:

| | Hex | Used for |
|---|---|---|
| Charcoal | `#4d4d4d` | logo body, headings, nav |
| Red | `#cf4832` | "high field" accent |
| Blue | `#1e73a6` | "low field" accent |

Fonts are [Quicksand](https://fonts.google.com/specimen/Quicksand) for headings
and navigation (the closest free match to the logo lettering) and
[Nunito Sans](https://fonts.google.com/specimen/Nunito+Sans) for body text.
Both load from Google Fonts.

---

## Moving to the final URL

This repo is currently a prototype. The `_config.yml` file has two settings
that control URLs:

```yaml
baseurl: ""
url: ""
```

**While prototyping in a private repo** (e.g. `frantisekvasa/halflab-prototype`),
set:

```yaml
baseurl: "/halflab-prototype"     # must match the repo name exactly
url: "https://frantisekvasa.github.io"
```

**Once the site lives at `halflab.github.io`**, set both back to empty:

```yaml
baseurl: ""
url: "https://halflab.github.io"
```

Every link and image on the site uses `relative_url`, so changing those two
lines is the only thing needed — nothing else has to be touched.

### Getting `halflab.github.io` as the address

GitHub only serves a repo at `<name>.github.io` when `<name>` is the owner's
username or organisation name. Since your username is `frantisekvasa`, you'll
need a **free GitHub organisation** called `halflab`:

1. GitHub → your profile menu → **Your organizations** → **New organization** →
   choose the Free plan, name it `halflab`.
2. Inside that org, create a **public** repo named exactly `halflab.github.io`.
3. Push this site's files to it.
4. Repo → **Settings** → **Pages** → set Source to *Deploy from a branch*,
   branch `main`, folder `/ (root)`.
5. Set `baseurl: ""` and `url: "https://halflab.github.io"` in `_config.yml`.

The site appears at `https://halflab.github.io` within a couple of minutes.

An organisation also lets you add lab members as collaborators so they can
update their own entries.

---

## Publishing the prototype

```bash
cd "half-lab_website"
git init
git add .
git commit -m "Initial site"
git branch -M main
git remote add origin https://github.com/frantisekvasa/halflab.github.io.git
git push -u origin main
```

Then enable Pages: repo → **Settings** → **Pages** → Source: *Deploy from a
branch*, branch `main`, folder `/ (root)`.

> Note: GitHub Pages on a **private** repo requires a paid plan. If you want to
> keep the prototype private and just preview it locally, use the instructions
> below instead.

---

## Previewing locally (optional)

Not required — you can edit on GitHub and let it build. But if you want to see
changes instantly before committing:

```bash
# one-off setup (macOS)
brew install ruby
gem install bundler
bundle install

# every time
bundle exec jekyll serve --livereload
```

Then open <http://localhost:4000>. Pages refresh as you save.

---

## Repository layout

```
_config.yml              site settings, menu, contact details
_data/
  people.yml             team members  ← edit this
  publications.yml       papers (generated by tools/bib_to_yml.py)
  research.yml           overview, approaches, datasets ← edit this
  funders.yml            funders, logos, acknowledgement
  resources.yml          software, data, teaching
tools/
  bib_to_yml.py          Scholar BibTeX → publications.yml
  scholar.bib            your Scholar export (you add this)
_news/                   one Markdown file per news post
_layouts/                page templates (rarely edited)
_includes/               header and footer (rarely edited)
assets/
  css/style.css          all styling; variables at the top
  img/                   logos, favicon
  img/team/              team photos
  img/research/          figures for research themes
  img/news/              images for news posts
index.html               Home
research.html            Research
team.html                Team
publications.html        Publications
news.html                News index
resources.html           Resources
404.html                 not-found page
logos/                   original logo files (not published)
```

---

## Still to do

- [ ] Run `tools/enrich_from_crossref.py` to fill the missing links and
      author lists (see above), then prune the list
- [ ] Check the research text in `_data/research.yml` — especially BONO (TBC)
- [ ] Add photos and bios for everyone in `_data/people.yml`
- [ ] **Funding acknowledgement** — the text is drafted in `_data/funders.yml`
      from UKRI and NIHR Maudsley BRC guidance, but it is hidden on the site
      because the two grant references in it are placeholders. Fill those in,
      check the funder list, then set `show_acknowledgement: true`
- [ ] Add Isuru's current position (`now:`) in the alumni list
- [ ] Add lab Bluesky / Scholar links in `_config.yml`
- [ ] Confirm the institution and address in `_config.yml` are correct
- [ ] Decide on the final URL and update `baseurl` / `url`. **`url` is now
      set to `https://halflab.github.io`** — social previews and the sitemap
      depend on it being right, so change it if the address changes
- [ ] Create the `halflab` GitHub organisation, then re-add the lab account to
      `_data/resources.yml` (removed for now: it was a dead link)
