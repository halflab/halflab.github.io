# half lab website

Source for the website of the **half lab** — the High and Low Field (Network
Neuroimaging) Laboratory, Department of Neuroimaging, King's College London.

**Live at [halflab.github.io](https://halflab.github.io).**

Jekyll, published by GitHub Pages. Push to `main` and it rebuilds.

---

## Editing the site

| I want to… | Edit this |
|---|---|
| Add or change a team member | `_data/people.yml` |
| Add a publication | `_data/publications.yml` |
| Post a news item | a new file in `_news/` |
| Change the research text, projects or datasets | `_data/research.yml` |
| Add a funder or its logo | `_data/funders.yml` |
| Add software, data or teaching material | `_data/resources.yml` |
| Change the lab name, contact details or menu | `_config.yml` |
| Change colours, spacing or type | `assets/css/style.css` (variables at the top) |

Each of those files has notes in comments at the top. Small changes are easiest
made in the browser: open the file on GitHub, click the pencil, commit.

### Team members

Only `name` and `role` are required. Bios are reproduced as written — any
length, first person or third. `name_native` adds a name in its original script
alongside the Latin one.

Photos are square JPEGs in `assets/img/team/`. To add one, put the original in
`FV_resources/team/` and run:

```
python3 tools/make_team_photos.py
```

It crops to a square centred slightly above the middle, where faces usually are.
`FOCUS` and `ZOOM` at the top of the script override that per photo.

### Publications

What belongs in the list is set out at the top of `_data/publications.yml`.
`tags` (any of `hf`, `lf`, `nn`, `bn`) drive the coloured markers and the filter
buttons; `selected: 1` promotes a paper to the home page.

To fill in publisher links and full author lists from Crossref, double-click
`tools/update_publications.command` in Finder. From the Terminal:

```
python3 tools/enrich_from_crossref.py --dry-run     # report, change nothing
python3 tools/enrich_from_crossref.py               # do it
```

Anything set by hand is left alone, and the previous version is kept as
`publications.yml.bak`.

### News

One Markdown file per post in `_news/`, named `YYYY-MM-DD-short-title.md`, with
`title`, `date` and `summary` between `---` markers at the top. Posts appear in
full on the News page and each also gets its own page.

---

## Running it locally

```
bundle install                      # once
bundle exec jekyll serve --livereload
```

Then <http://localhost:4000>.

---

## Visibility

`noindex` in `_config.yml` adds a `noindex` meta tag and a `robots.txt` that
blocks crawlers, keeping the site out of search results. Set it to `false` to
launch. It is not access control — anyone with the address can read the site.

---

## Layout

```
_config.yml            site settings, menu, contact details, feature flags
_data/
  people.yml           team, alumni, collaborators
  publications.yml     papers, tags, links
  research.yml         overview text, projects and datasets
  funders.yml          funders, logos, acknowledgement
  resources.yml        software, data, teaching, open science statement
  gallery.yml          lab life photos
  highlights.yml       figures at the top of Publications
  scans.yml            the field-strength comparison in the hero
_news/                 one Markdown file per news post
_layouts/              page templates
_includes/             header, footer, Venn diagram, interactive behaviours
assets/
  css/style.css        the whole design system; variables at the top
  img/                 logos, icons, team photos, gallery, figures
tools/                 import and image scripts
_attic/                removed features, kept in case they come back
index.html  research.html  team.html  publications.html
news.html   resources.html 404.html   robots.txt
```

## Tools

| Script | What it does |
|---|---|
| `update_publications.command` | double-click wrapper around the Crossref import |
| `enrich_from_crossref.py` | fills publisher links and full author lists |
| `bib_to_yml.py` | BibTeX export → `publications.yml` |
| `make_team_photos.py` | square, cropped team photos from the originals |
| `make_gallery.py` | imports lab life photos, keeping captions and crops |
| `make_icons.py` | generates the brain and network icons |
