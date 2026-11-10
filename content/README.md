# How to update the site

Everything on the page comes from this folder. Edit here, run the check, push to `main`. GitHub Actions builds and deploys; a failed check fails the deploy, so the live page cannot go wrong from a bad entry.

```
python3 build.py --check          # lint only, no files written
python3 build.py --out _site      # lint, then build the whole site into _site/ for a local look
python3 build.py --probe          # ask every entry's URL whether it answers today (read-only report)
python3 build.py --probe --write  # same, and record the answer in the entries' front matter
```

The build refuses to write anything if a check fails. Fix the entry, run again.

## One entry, one file

`entries/<slug>.md` is one thing we built. The top is a short header, the rest is the copy.

```
---
title: ChorHaus
section: live            # live | works | workshop | how
label: Live              # the chip text
url: https://chorhaus.aggressivelymediocre.me
live: yes                # green chip; needs url and check
check: 2026-11-10        # last day the url answered 200
note:                    # free text after the chip (optional)
summary: Chores for a shared home, turned into a friendly contest.
order: 20                # sort inside the section, low first
width: full              # full | half  (half = two side by side)
---
Intent paragraph. Why this exists and what it was for.

## What it does today
- One real thing it does.
- Another.

## Where it is headed
What happens next, and when. Honest.
```

Rules the build enforces:

- `title`, `section`, `label`, `summary`, `order` are required.
- `live: yes` needs a `url`. A public `http` url also needs a `check` date, and the chip then says "answered <date>". A site-relative url like `/charter/` needs no date.
- `offline: <date>` (written by `--probe --write`) turns the chip gold and says "public host offline on <date>".
- Nothing in `banned.txt` may appear anywhere. Things we run, fork or tune are not things we built.
- Any entry whose slug or title mentions Symmate may not use the words owner, own, owning, or "refuse to betray". Say "keys you hold" and "bonds and charters".
- No hard-coded "today" dates in copy. Write `{{today}}` and the build fills it in.
- Every entry title must appear in `INVENTORY.md` (that file is still written by hand). If the row there uses a different name, set `inventory: <row name>`. `section: how` entries are exempt.
- `section: workshop` entries are one paragraph and become a table row. Their `label` is the State column.
- `section: how` entries are practice notes; same shape as the others, ordered lists allowed.

Copy supports paragraphs, `## Heading`, `- bullet`, `1. numbered`, `[text](url)`, and `**bold**`. Nothing else, on purpose.

Extra optional keys: `published:` (a date, becomes `datePublished`), `repo:` (an https URL, becomes the DOAP repository), `kind:` (`SoftwareApplication` or `CreativeWork`; inferred otherwise), `category:` and `os:` for schema.org.

## What the build writes

- `index.html` from `templates/page.html` plus the entries, with the schema.org graph inline.
- `portfolio.jsonld` (schema.org ItemList) and `portfolio.ttl` (DOAP): every entry, stable `@id` = page URL + `#slug`.
- `llms.txt`, `sitemap.xml`, `humans.txt`.
- `.well-known/did.json` from `site.json` `did`; `.well-known/webfinger`; `.well-known/security.txt` (expires one year from the build).
- `.well-known/nostr.json` only when `site.json` `nostr_pubkey_hex` is a 64-char hex key.
- `.well-known/agent-card.json` and `agent.json`: only the `version` field, set to today.

`INVENTORY.md`, `agents.md`, `charter/`, `robots.txt`, `404.html`, the css and the fonts are hand-maintained and copied as they are.

## The DID key

`site.json` carries only the public half of the `did:web` key. The Ed25519 private key is a PEM file held by Loke outside the repo. Rotating it means: generate a new keypair, paste the new `publicKeyMultibase` into `site.json`, push. Never commit the private key.

## Adding a project

1. Copy an entry that looks like it. Change the slug.
2. Write it from the project's README and the commit log, not from memory. If a count goes in, note where it came from in `INVENTORY.md`.
3. If it has a public address, add `url:` and run `--probe --write` so the date is real.
4. Add a row to `INVENTORY.md`.
5. `python3 build.py`, open the preview, post the `git diff --stat` for Loke. Do not commit.
