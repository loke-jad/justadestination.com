# justadestination.com

Static portfolio for justadestination llc. One page, the charter excerpt, and the files an agent looks for.

The live domain still serves the existing Next.js site. This tree does not change that. DNS stays where it is until Loke points it here.

## What is in the box

- `index.html` — the page
- `charter/` — public excerpt of the Mox–Loke agreement, already on the web
- `INVENTORY.md` — the sift: built, partial, sketch
- `robots.txt`, `sitemap.xml`, `llms.txt`
- `agents.md` — instructions for agents
- `.well-known/agent-card.json` — A2A card. It does not advertise a task inbox.
- `.well-known/agent.json` — older card shape, same refusal
- `.well-known/agents` — index of that one agent
- `CNAME` — the domain this tree is for, once DNS says so

## Preview

From this directory:

```
python3 -m http.server 8765 --bind 127.0.0.1
```

Then open http://127.0.0.1:8765/

## GitHub Pages

A new repository. Not `loke-jad/loke-jad.github.io`, which is the ShadeNet / NightCal pages site.

Pages will warn about the custom domain until DNS points at GitHub. That warning is correct. Leave the current site alone until the page is accepted.
