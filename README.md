# half lab website

Source for the website of the **half lab** — the High and Low Field (Network
Neuroimaging) Laboratory, Department of Neuroimaging, King's College London.

**Live at [halflab.github.io](https://halflab.github.io).**

Built with [Jekyll](https://jekyllrb.com) and published by GitHub Pages. There
is no build step to run and nothing to install: push to `main` and the site
rebuilds itself within a minute or two.

You don't need to know Jekyll to maintain it. Almost everything you would want
to change is plain text in `_data/`, and every one of those files explains
itself in comments at the top.

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

The simplest way to make a small change is in the browser: open the file on
GitHub, click the pencil, edit, and commit. The site rebuilds on its own.

### Team members

Add a block to the `people:` list. Only `name` and `role` are required;
`bio`, `email`, `photo`, `scholar`, `orcid`, `github`, `bluesky` and `website`
are all optional, and a person with no photo shows as an initials placeholder.

Bios are reproduced exactly as their author wrote them — any length, any number
of paragraphs, first person or third. `name_native` adds a name in its original
script alongside the Latin one.

Photos live in `assets/img/team/` as square JPEGs, about 600×600. To add one,
put the original in `FV_resources/team/` and run:

```
python3 tools/make_team_photos.py
```

It crops to a square centred slightly above the middle — where faces usually
are — and writes the file the site expects. `FOCUS` and `ZOOM` at the top of
that script override the crop per photo when the guess is wrong.

When someone leaves, move them to the `alumni:` list at the foot of the file.

### Publications

What belongs in the list is documented at the top of `_data/publications.yml`:
work by anyone currently in the lab, published while they were here, where the
subject is relevant to what the lab does. Nothing is added automatically.

To add a paper by hand, copy an existing entry. `tags` (any of `hf`, `lf`,
`nn`, `bn`) drive the coloured markers and the filter buttons; `selected: 1`
promotes a paper to the home page.

To fill in publisher links and complete author lists from Crossref, double-click
`tools/update_publications.command` in Finder — it shows what it would change
and asks before changing anything. From the Terminal it's:

```
python3 tools/enrich_from_crossref.py --dry-run     # report, change nothing
python3 tools/enrich_from_crossref.py               # do it
```

Anything already set by hand is left alone, and the previous version is kept as
`publications.yml.bak`.

### News

One Markdown file per post in `_news/`, named `YYYY-MM-DD-short-title.md`, with
`title`, `date` and `summary` at the top between `---` markers. Everything below
is the body. Posts appear in full on the News page and each also gets its own
page.

---

## Running it locally

Not required — editing on GitHub and letting it build is fine. But to see
changes as you type:

```
bundle install                      # once
bundle exec jekyll serve --livereload
```

Then open <http://localhost:4000>.

---

## Visibility

`_config.yml` has a `noindex` flag. While it is `true` the site carries a
`noindex` meta tag and a `robots.txt` that blocks crawlers — it stays out of
search results, which is what you want while it is being reviewed. Set it to
`false` to launch.

It is not access control: the site is readable by anyone with the address.
GitHub Pages cannot restrict an organisation site to members of the
organisation on any plan.

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
tools/                 import and image scripts (see below)
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

---

## Outstanding

- [ ] Fill the two grant references in `_data/funders.yml`, then set
      `show_acknowledgement: true` — the funding statement is hidden until then
- [ ] One publication has no strand tags and so appears only in the unfiltered
      list
- [ ] Check the accessibility work by hand — screen reader on the Venn diagram
      and the team dialogs, keyboard order through the header and hero
- [ ] Add Isuru's current position (`now:`) in the alumni list
- [ ] Lab Bluesky and Scholar links in `_config.yml`
- [ ] Set `noindex: false` at launch
