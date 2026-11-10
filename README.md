# justadestination.com

Static portfolio for justadestination llc. One page, the charter excerpt, and the files an agent or a crawler looks for.

Hosted on GitHub Pages. Every push to `main` runs `build.py` in Actions and deploys the result. Nothing generated is committed.

## Updating the page

Do not edit `index.html`; it does not exist in the repo. Edit `content/` and push. Read `content/README.md` for the entry format and the checks.

```
python3 build.py --check            # lint
python3 build.py --out _site        # build locally; preview with python3 -m http.server --directory _site
python3 build.py --probe --write    # ask every public URL whether it answers today, record it
python3 scripts/release.py          # record a release digest (and CID / timestamp when the tools exist)
```

The build refuses to write if a check fails, and the Actions job fails the same way, so a bad entry never reaches the page.

## What is in the box

- `content/` — one Markdown file per thing we built, plus `site.json` and `banned.txt`
- `templates/page.html` — the page skeleton (hero, mark, door, footer)
- `build.py` — stdlib Python; lints, then renders everything below
- `charter/` — public excerpt of the Mox–Loke agreement
- `INVENTORY.md` — the sift: built, partial, sketch (hand-written; every entry title must appear here)
- `agents.md`, `.well-known/agent-card.json`, `.well-known/agent.json` — notes and A2A cards; no task inbox
- `site.css`, `fonts/`, icons, `robots.txt`, `404.html`, `CNAME`

Generated on every build: `index.html`, `llms.txt`, `sitemap.xml`, `humans.txt`, `portfolio.jsonld` (schema.org), `portfolio.ttl` (DOAP), `.well-known/did.json`, `.well-known/webfinger`, `.well-known/security.txt`, and the agent cards with today's version.

## Machine-readable surfaces

- schema.org JSON-LD in the page head and at `/portfolio.jsonld`: WebSite, Organization, Person, and an ItemList of every entry with a stable `@id`.
- DOAP at `/portfolio.ttl` for the semantic-web crowd.
- microformats2 `h-card` on the body, `rel="me"` on the links that are ours.
- `did:web:justadestination.com` at `/.well-known/did.json`. The private key is not in this repo.
- WebFinger for `acct:loke@justadestination.com`, `security.txt`, `humans.txt`.
- `scripts/release.py` records a digest per release and, when `ipfs` or `ots` are installed, a CID and an OpenTimestamps proof.

## Preview

```
python3 build.py --out _site
python3 -m http.server 8765 --bind 127.0.0.1 --directory _site
```

## Domain

`CNAME` names the apex. DNS is Cloudflare; the apex A records point at GitHub Pages and `www` is a CNAME to `loke-jad.github.io`. Subdomains are unaffected.
