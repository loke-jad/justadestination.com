#!/usr/bin/env python3
"""Build justadestination.com from content/.

    python3 build.py --check              lint only
    python3 build.py --out _site          lint, then write the whole site into _site/ (what CI deploys)
    python3 build.py                      same, into the repo root (generated files are git-ignored)
    python3 build.py --probe              report which entry URLs answer today (read-only)
    python3 build.py --probe --write      same, and record the result in the entries

Standard library only. Read content/README.md for the entry format.

Outputs: index.html, llms.txt, sitemap.xml, humans.txt, portfolio.jsonld, portfolio.ttl,
.well-known/did.json, .well-known/webfinger, .well-known/security.txt, .well-known/nostr.json
(only when a key is set), and the two agent cards with today's version. With --out, the
hand-maintained static files (css, fonts, charter, icons, robots, CNAME, agents.md,
INVENTORY.md, 404.html, .nojekyll) are copied alongside.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
ENTRIES = CONTENT / "entries"
TEMPLATE = ROOT / "templates" / "page.html"

SECTIONS = ("live", "works", "workshop", "how")
REQUIRED = ("title", "section", "label", "summary", "order")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SYMMATE_BAD = re.compile(r"\bowner(?:s|ship)?\b|\bowning\b|\bowned\b|\bowns\b|refuse to betray", re.I)

# Hand-maintained files copied into --out as they are.
STATIC = [
    "site.css", "fonts", "charter", "404.html", "robots.txt", "CNAME", ".nojekyll",
    "agents.md", "AGENTS.md", "INVENTORY.md", "README.md",
    "favicon.png", "apple-touch-icon.png", "icon-1024.png",
    ".well-known/agents", "releases.json", "proofs",
]


# ---------------------------------------------------------------- content

class Entry:
    def __init__(self, path: Path):
        self.path = path
        self.slug = path.stem
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            raise ValueError(f"{path.name}: no front matter")
        head, _, body = text[4:].partition("\n---\n")
        self.meta: dict[str, str] = {}
        for line in head.splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            key, _, value = line.partition(":")
            value = value.split(" #", 1)[0].strip()
            self.meta[key.strip()] = value
        self.body = body.strip("\n")

    def get(self, key: str, default: str = "") -> str:
        return self.meta.get(key, default)

    @property
    def is_live(self) -> bool:
        return self.get("live").lower() in ("yes", "true")

    @property
    def is_symmate(self) -> bool:
        return "symmate" in (self.slug + self.get("title")).lower()

    @property
    def public_url(self) -> str:
        u = self.get("url")
        return u if u.startswith("http") else ""

    @property
    def modified(self) -> str:
        return self.get("check") or self.get("offline") or ""

    def text_for_lint(self) -> str:
        return "\n".join(self.meta.values()) + "\n" + self.body


def load_entries() -> list[Entry]:
    return [Entry(p) for p in sorted(ENTRIES.glob("*.md"))]


def load_site() -> dict:
    return json.loads((CONTENT / "site.json").read_text(encoding="utf-8"))


def load_banned() -> list[str]:
    out = []
    for line in (CONTENT / "banned.txt").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line)
    return out


# ---------------------------------------------------------------- dates

def today() -> str:
    return dt.date.today().isoformat()


def long_date(iso: str) -> str:
    d = dt.date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%B')} {d.year}"


def plus_one_year(iso: str) -> str:
    d = dt.date.fromisoformat(iso)
    return d.replace(year=d.year + 1).isoformat()


# ---------------------------------------------------------------- markdown subset

INLINE_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
INLINE_BOLD = re.compile(r"\*\*(.+?)\*\*")


def inline(text: str) -> str:
    text = html.escape(text, quote=False)
    text = INLINE_LINK.sub(lambda m: f'<a href="{html.escape(m.group(2), quote=True)}">{m.group(1)}</a>', text)
    text = INLINE_BOLD.sub(r"<strong>\1</strong>", text)
    return text


def plain(text: str) -> str:
    """Markdown subset to plain text, for descriptions in data files."""
    text = INLINE_LINK.sub(r"\1", text)
    return INLINE_BOLD.sub(r"\1", text)


def md_to_html(body: str, indent: str = "      ") -> str:
    """Paragraphs, ## headings (h4), - bullets, 1. numbered, inline links and bold."""
    out: list[str] = []
    para: list[str] = []
    lst: list[str] = []
    lst_tag = ""

    def flush_para():
        if para:
            out.append(f"{indent}<p>{inline(' '.join(para))}</p>")
            para.clear()

    def flush_list():
        nonlocal lst_tag
        if lst:
            cls = ' class="practices"' if lst_tag == "ol" else ""
            out.append(f"{indent}<{lst_tag}{cls}>")
            out.extend(f"{indent}  <li>{inline(item)}</li>" for item in lst)
            out.append(f"{indent}</{lst_tag}>")
            lst.clear()
            lst_tag = ""

    for raw in body.splitlines():
        line = raw.rstrip()
        if not line.strip():
            flush_para(); flush_list(); continue
        if line.startswith("## "):
            flush_para(); flush_list()
            out.append(f"{indent}<h4>{inline(line[3:].strip())}</h4>")
        elif line.startswith("- "):
            flush_para()
            if lst_tag and lst_tag != "ul":
                flush_list()
            lst_tag = "ul"; lst.append(line[2:].strip())
        elif re.match(r"^\d+\. ", line):
            flush_para()
            if lst_tag and lst_tag != "ol":
                flush_list()
            lst_tag = "ol"; lst.append(re.sub(r"^\d+\. ", "", line).strip())
        else:
            flush_list()
            para.append(line.strip())
    flush_para(); flush_list()
    return "\n".join(out)


# ---------------------------------------------------------------- lint

def check(entries: list[Entry], site: dict) -> list[str]:
    errors: list[str] = []
    banned = load_banned()
    inventory = (ROOT / "INVENTORY.md").read_text(encoding="utf-8") if (ROOT / "INVENTORY.md").exists() else ""
    slugs = set()
    for e in entries:
        n = e.path.name
        if e.slug in slugs:
            errors.append(f"{n}: duplicate slug")
        slugs.add(e.slug)
        for key in REQUIRED:
            if not e.get(key):
                errors.append(f"{n}: missing {key}")
        if e.get("section") not in SECTIONS:
            errors.append(f"{n}: section must be one of {', '.join(SECTIONS)}")
        if not e.get("order", "0").isdigit():
            errors.append(f"{n}: order must be an integer")
        if e.get("width", "full") not in ("full", "half"):
            errors.append(f"{n}: width must be full or half")
        for key in ("check", "offline", "published"):
            v = e.get(key)
            if v and not DATE_RE.match(v):
                errors.append(f"{n}: {key} must be YYYY-MM-DD")
            if v and DATE_RE.match(v) and key != "published" and v > today():
                errors.append(f"{n}: {key} is in the future")
        if e.is_live and not e.get("url"):
            errors.append(f"{n}: live: yes needs a url")
        if e.is_live and e.public_url and not e.get("check"):
            errors.append(f"{n}: live: yes with a public url needs a check date (run --probe --write)")
        if e.is_live and e.get("offline"):
            errors.append(f"{n}: cannot be both live and offline")
        if e.get("repo") and not e.get("repo").startswith("https://"):
            errors.append(f"{n}: repo must be an https url")
        if e.get("section") == "workshop" and ("\n\n" in e.body or e.body.startswith("## ")):
            errors.append(f"{n}: workshop entries are one paragraph")
        low = e.text_for_lint().lower()
        for word in banned:
            if word.lower() in low:
                errors.append(f"{n}: contains banned name '{word}'")
        if e.is_symmate:
            m = SYMMATE_BAD.search(e.text_for_lint())
            if m:
                errors.append(f"{n}: Symmate copy uses '{m.group(0)}' (say keys you hold / bonds and charters)")
        inv_name = e.get("inventory") or e.get("title")
        if e.get("section") != "how" and inv_name and inv_name not in inventory:
            errors.append(f"{n}: '{inv_name}' is not in INVENTORY.md (add a row, or set inventory: to the row's name)")
    site_text = json.dumps(site).lower()
    for word in banned:
        if word.lower() in site_text:
            errors.append(f"site.json: contains banned name '{word}'")
    for key in ("name", "domain", "email", "tagline", "lede", "description", "sections", "door", "footer"):
        if key not in site:
            errors.append(f"site.json: missing {key}")
    if site.get("did", {}).get("public_key_multibase", "").startswith("z6Mk") is False and site.get("did"):
        errors.append("site.json: did.public_key_multibase must be an Ed25519 multibase key (z6Mk...)")
    if not TEMPLATE.exists():
        errors.append("templates/page.html is missing")
    return errors


def check_graph(out: Path) -> list[str]:
    """Parse the generated data files. Uses rdflib when it is installed; otherwise JSON only."""
    errors: list[str] = []
    try:
        json.loads((out / "portfolio.jsonld").read_text(encoding="utf-8"))
        json.loads((out / ".well-known" / "did.json").read_text(encoding="utf-8"))
        json.loads((out / ".well-known" / "webfinger").read_text(encoding="utf-8"))
    except Exception as ex:  # noqa: BLE001
        errors.append(f"generated JSON does not parse: {ex}")
    try:
        import rdflib  # type: ignore
    except ImportError:
        return errors
    g = rdflib.Graph()
    try:
        g.parse(out / "portfolio.ttl", format="turtle")
        g.parse(out / "portfolio.jsonld", format="json-ld")
    except Exception as ex:  # noqa: BLE001
        errors.append(f"rdflib could not parse the graph: {ex}")
    return errors


# ---------------------------------------------------------------- page

def status_line(e: Entry) -> str:
    chip = f'<span class="pill{" live" if e.is_live else ""}">{html.escape(e.get("label"))}</span>'
    bits = [chip]
    url = e.get("url")
    if url and e.is_live and not url.startswith("/"):
        bits.append(f'<a href="{html.escape(url, True)}">{html.escape(url.split("//", 1)[-1].rstrip("/"))}</a>')
    if e.get("note"):
        bits.append(f"<span>{inline(e.get('note'))}</span>")
    if e.is_live and e.get("check"):
        bits.append(f"<span>answered {long_date(e.get('check'))}</span>")
    elif e.get("offline"):
        bits.append(f"<span>public host offline on {long_date(e.get('offline'))}</span>")
    return '<p class="status">' + " ".join(bits) + "</p>"


def render_article(e: Entry, indent: str = "    ") -> str:
    i2 = indent + "  "
    return "\n".join([
        f'{indent}<article id="{html.escape(e.slug)}">',
        f"{i2}<h3>{inline(e.get('title'))}</h3>",
        f"{i2}{status_line(e)}",
        md_to_html(e.body, i2),
        f"{indent}</article>",
    ])


def render_workshop(entries: list[Entry], section: dict) -> str:
    rows = []
    for e in entries:
        rows.append("\n".join([
            "          <tr>",
            f'            <th scope="row" id="{html.escape(e.slug)}">{inline(e.get("title"))}</th>',
            f"            <td>{inline(e.get('label'))}</td>",
            f"            <td>{inline(e.body.strip())}</td>",
            "          </tr>",
        ]))
    return "\n".join([
        '    <div class="shelf-wrap">',
        "      <table>",
        f"        <caption>{inline(section.get('caption', ''))}</caption>",
        "        <thead>",
        "          <tr>",
        '            <th scope="col">Name</th>',
        '            <th scope="col">State</th>',
        '            <th scope="col">What it is</th>',
        "          </tr>",
        "        </thead>",
        "        <tbody>",
        *rows,
        "        </tbody>",
        "      </table>",
        "    </div>",
    ])


def flush_halves(halves: list[Entry]) -> str:
    inner = "\n\n".join(render_article(e, "      ") for e in halves)
    return f'    <div class="grid">\n{inner}\n    </div>\n'


def by_section(entries: list[Entry], sid: str) -> list[Entry]:
    return sorted((e for e in entries if e.get("section") == sid), key=lambda e: int(e.get("order")))


def render_sections(entries: list[Entry], site: dict) -> str:
    out = []
    for section in site["sections"]:
        sid = section["id"]
        members = by_section(entries, sid)
        out.append(f'    <h2 id="{sid}" tabindex="-1">{inline(section["title"])}</h2>')
        out.append(f'    <p class="section-lede">{inline(section["lede"])}</p>')
        if sid == "workshop":
            out.append(render_workshop(members, section))
        else:
            halves: list[Entry] = []
            for e in members:
                if e.get("width", "full") == "half":
                    halves.append(e)
                    continue
                if halves:
                    out.append(flush_halves(halves)); halves = []
                out.append(render_article(e))
                out.append("")
            if halves:
                out.append(flush_halves(halves))
        out.append("")
    return "\n".join(out).rstrip()


def fill(template: str, values: dict[str, str]) -> str:
    for k, v in values.items():
        template = template.replace("{{" + k + "}}", v)
    left = re.findall(r"{{\w+}}", template)
    if left:
        raise ValueError(f"unfilled placeholders: {sorted(set(left))}")
    return template


def render_page(entries: list[Entry], site: dict, day: str) -> str:
    t = TEMPLATE.read_text(encoding="utf-8")
    ld = long_date(day)
    nav = "\n".join(f'            <li><a href="#{s["id"]}">{inline(s["title"])}</a></li>' for s in site["sections"])
    nav += f'\n            <li><a href="#door">{inline(site["door"]["title"])}</a></li>'
    intro = "\n".join(f"      <p>{inline(p.replace('{{today}}', ld))}</p>" for p in site["intro"])
    door = "\n".join(f"      <p>{inline(p)}</p>" for p in site["door"]["text"])
    links = []
    for l in site["footer_links"]:
        rel = ' rel="me"' if l.get("me") else ""
        cls = f' class="{l["class"]}"' if l.get("class") else ""
        links.append(f'        <li><a{cls}{rel} href="{html.escape(l["href"], True)}">{inline(l["text"])}</a></li>')
    graph = json.dumps(jsonld_graph(entries, site, day), indent=2, ensure_ascii=False)
    graph = "\n".join("  " + line for line in graph.splitlines())
    return fill(t, {
        "name": html.escape(site["name"]),
        "domain": site["domain"],
        "description": html.escape(site["description"], True),
        "tagline": html.escape(site["tagline"]),
        "lede": html.escape(site["lede"]),
        "email": site["email"],
        "theme_color": site.get("theme_color", "#1C2A2E"),
        "jsonld": graph,
        "nav": nav,
        "intro": intro,
        "sections": render_sections(entries, site),
        "door_title": inline(site["door"]["title"]),
        "door_text": door,
        "footer": inline(site["footer"].replace("{{today}}", ld)),
        "footer_links": "\n".join(links),
    })


# ---------------------------------------------------------------- linked data

def entry_kind(e: Entry) -> str:
    if e.get("kind"):
        return e.get("kind")
    if e.get("section") == "how" or e.slug == "charter":
        return "CreativeWork"
    return "SoftwareApplication"


def entry_iri(site: dict, e: Entry) -> str:
    return f"{site['domain']}/#{e.slug}"


def jsonld_graph(entries: list[Entry], site: dict, day: str) -> dict:
    dom = site["domain"]
    org_id, person_id, site_id = f"{dom}/#org", f"{dom}/#loke", f"{dom}/#website"
    person = site.get("person", {})
    org = {
        "@type": "Organization", "@id": org_id,
        "name": site["name"], "url": dom + "/", "email": site["email"],
        "logo": f"{dom}/apple-touch-icon.png",
        "areaServed": "Sonoma County, California",
        "founder": {"@id": person_id},
        "knowsAbout": site.get("knows_about", []),
    }
    if site.get("did", {}).get("id"):
        org["identifier"] = {"@type": "PropertyValue", "propertyID": "DID", "value": site["did"]["id"]}
    if site.get("github"):
        org["sameAs"] = [site["github"]]
    who = {"@type": "Person", "@id": person_id, "name": person.get("name", "Loke"),
           "email": site["email"], "worksFor": {"@id": org_id}, "url": dom + "/"}
    if person.get("same_as"):
        who["sameAs"] = person["same_as"]
    website = {"@type": "WebSite", "@id": site_id, "url": dom + "/", "name": site["name"],
               "description": site["description"], "publisher": {"@id": org_id},
               "dateModified": day, "inLanguage": "en"}
    items = []
    position = 0
    for section in site["sections"]:
        for e in by_section(entries, section["id"]):
            position += 1
            node = {
                "@type": entry_kind(e), "@id": entry_iri(site, e),
                "name": e.get("title"), "description": plain(e.get("summary")),
                "creator": {"@id": org_id}, "isAccessibleForFree": True,
                "dateModified": e.modified or day,
                "keywords": [section["title"], e.get("label")],
            }
            if e.public_url:
                node["url"] = e.public_url
            elif e.get("url"):
                node["url"] = dom + e.get("url")
            if e.get("published"):
                node["datePublished"] = e.get("published")
            if e.get("repo"):
                node["codeRepository"] = e.get("repo")
            if entry_kind(e) == "SoftwareApplication":
                node["applicationCategory"] = e.get("category", "Software")
                node["operatingSystem"] = e.get("os", "Web")
            items.append({"@type": "ListItem", "position": position, "item": node})
    portfolio = {"@type": "ItemList", "@id": f"{dom}/#portfolio", "name": "Portfolio",
                 "numberOfItems": len(items), "itemListElement": items}
    return {"@context": "https://schema.org", "@graph": [website, org, who, portfolio]}


def ttl_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'


def render_turtle(entries: list[Entry], site: dict, day: str) -> str:
    dom = site["domain"]
    person = site.get("person", {})
    lines = [
        "@prefix doap: <http://usefulinc.com/ns/doap#> .",
        "@prefix foaf: <http://xmlns.com/foaf/0.1/> .",
        "@prefix dcterms: <http://purl.org/dc/terms/> .",
        "@prefix schema: <https://schema.org/> .",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
        "",
        f"<{dom}/#org> a foaf:Organization, schema:Organization ;",
        f"  foaf:name {ttl_str(site['name'])} ;",
        f"  foaf:homepage <{dom}/> ;",
        f"  foaf:mbox <mailto:{site['email']}> ;",
        f"  foaf:member <{dom}/#loke> .",
        "",
        f"<{dom}/#loke> a foaf:Person ;",
        f"  foaf:name {ttl_str(person.get('name', 'Loke'))} ;",
        f"  foaf:mbox <mailto:{site['email']}> ;",
        f"  foaf:homepage <{dom}/> .",
        "",
    ]
    for section in site["sections"]:
        for e in by_section(entries, section["id"]):
            iri = entry_iri(site, e)
            kind = "doap:Project" if entry_kind(e) == "SoftwareApplication" else "schema:CreativeWork"
            lines.append(f"<{iri}> a {kind} ;")
            lines.append(f"  doap:name {ttl_str(e.get('title'))} ;")
            lines.append(f"  doap:shortdesc {ttl_str(plain(e.get('summary')))} ;")
            if e.public_url:
                lines.append(f"  doap:homepage <{e.public_url}> ;")
            if e.get("repo"):
                lines.append(f"  doap:repository [ a doap:GitRepository ; doap:location <{e.get('repo')}> ] ;")
            lines.append(f"  doap:developer <{dom}/#org> ;")
            lines.append(f"  doap:maintainer <{dom}/#loke> ;")
            lines.append(f"  dcterms:subject {ttl_str(section['title'])} ;")
            lines.append(f"  schema:creativeWorkStatus {ttl_str(e.get('label'))} ;")
            lines.append(f'  dcterms:modified "{e.modified or day}"^^xsd:date .')
            lines.append("")
    lines.append(f"<{dom}/> a foaf:Document ; dcterms:modified \"{day}\"^^xsd:date ; foaf:primaryTopic <{dom}/#org> .")
    return "\n".join(lines) + "\n"


def render_did(site: dict) -> str:
    did = site["did"]
    did_id = did["id"]
    key_id = f"{did_id}#key-1"
    doc = {
        "@context": ["https://www.w3.org/ns/did/v1", "https://w3id.org/security/suites/ed25519-2020/v1"],
        "id": did_id,
        "verificationMethod": [{
            "id": key_id, "type": "Ed25519VerificationKey2020", "controller": did_id,
            "publicKeyMultibase": did["public_key_multibase"],
        }],
        "authentication": [key_id],
        "assertionMethod": [key_id],
        "service": [
            {"id": f"{did_id}#website", "type": "LinkedDomains", "serviceEndpoint": site["domain"] + "/"},
            {"id": f"{did_id}#a2a", "type": "A2AAgentCard", "serviceEndpoint": site["domain"] + "/.well-known/agent-card.json"},
            {"id": f"{did_id}#portfolio", "type": "LinkedData", "serviceEndpoint": site["domain"] + "/portfolio.jsonld"},
        ],
    }
    return json.dumps(doc, indent=2) + "\n"


def render_webfinger(site: dict) -> str:
    dom = site["domain"]
    host = dom.split("//", 1)[-1]
    user = site["email"].split("@", 1)[0]
    doc = {
        "subject": f"acct:{user}@{host}",
        "aliases": [dom + "/", dom + "/#loke"],
        "links": [
            {"rel": "http://webfinger.net/rel/profile-page", "type": "text/html", "href": dom + "/"},
            {"rel": "http://webfinger.net/rel/avatar", "type": "image/png", "href": dom + "/icon-1024.png"},
            {"rel": "describedby", "type": "application/ld+json", "href": dom + "/portfolio.jsonld"},
        ],
    }
    if site.get("did", {}).get("id"):
        doc["links"].append({"rel": "self", "type": "application/did+json", "href": dom + "/.well-known/did.json"})
    return json.dumps(doc, indent=2) + "\n"


def render_security_txt(site: dict, day: str) -> str:
    dom = site["domain"]
    return "\n".join([
        f"Contact: mailto:{site['email']}",
        f"Expires: {plus_one_year(day)}T00:00:00.000Z",
        "Preferred-Languages: en",
        f"Canonical: {dom}/.well-known/security.txt",
        f"Policy: {dom}/agents.md",
        "",
    ])


def render_humans(site: dict, day: str) -> str:
    person = site.get("person", {})
    return "\n".join([
        "/* TEAM */",
        f"  {person.get('name', 'Loke')}, and a crew of AI agents",
        f"  Contact: {site['email']}",
        "  Location: Sonoma County, California",
        "",
        "/* SITE */",
        f"  Last update: {day}",
        "  Language: English",
        "  Built with: Python (stdlib), plain HTML and CSS, Inter and JetBrains Mono",
        f"  Source: {site.get('github', '')}",
        "  Standards: schema.org JSON-LD, DOAP Turtle, microformats2 h-card, WebFinger, did:web, security.txt",
        "",
    ])


def render_nostr(site: dict) -> str | None:
    hexkey = site.get("nostr_pubkey_hex", "")
    if not re.fullmatch(r"[0-9a-f]{64}", hexkey or ""):
        return None
    user = site["email"].split("@", 1)[0]
    return json.dumps({"names": {user: hexkey}}, indent=2) + "\n"


def render_llms(entries: list[Entry], site: dict) -> str:
    dom = site["domain"]
    lines = [f"# {site['name']}", "", f"> {site['description'].split('. ', 1)[0]}. Static site. No task endpoint.", ""]
    lines += [f"- [{l['text']}]({l['href']})" for l in site["llms_links"]]
    lines += [f"- [Portfolio as linked data]({dom}/portfolio.jsonld)", f"- [Portfolio as DOAP]({dom}/portfolio.ttl)"]
    for section in site["sections"]:
        for e in by_section(entries, section["id"]):
            if e.is_live and e.public_url:
                lines.append(f"- [{e.get('title')}]({e.public_url})")
    lines += ["", f"Mail: {site['email']}", ""]
    return "\n".join(lines)


def render_sitemap(site: dict, day: str) -> str:
    urls = ["/", "/charter/", "/agents.md", "/portfolio.jsonld", "/portfolio.ttl"]
    body = "\n".join(
        f"  <url>\n    <loc>{site['domain']}{u}</loc>\n    <lastmod>{day}</lastmod>\n  </url>" for u in urls
    )
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{body}\n</urlset>\n'


def bump_card_version(path: Path, day: str) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["version"] = day.replace("-0", ".").replace("-", ".")
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


# ---------------------------------------------------------------- probe

def probe(entries: list[Entry], write: bool) -> int:
    day = today()
    bad = 0
    for e in entries:
        url = e.public_url
        if not url:
            continue
        req = urllib.request.Request(url, headers={"User-Agent": "justadestination-site-probe/1 (+https://justadestination.com)"})
        try:
            with urllib.request.urlopen(req, timeout=12) as r:
                code = r.status
        except urllib.error.HTTPError as ex:
            code = ex.code
        except Exception:  # noqa: BLE001
            code = 0
        ok = code == 200
        print(f"{'ok ' if ok else 'BAD'} {code:>3} {url}  ({e.path.name})")
        if not ok:
            bad += 1
        if write:
            text = e.path.read_text(encoding="utf-8")
            head, sep, body = text[4:].partition("\n---\n")
            lines = [l for l in head.splitlines() if not re.match(r"^(check|offline|live):", l)]
            if ok:
                lines += ["live: yes", f"check: {day}"]
            else:
                if e.get("check"):
                    lines.append(f"check: {e.get('check')}")
                lines.append(f"offline: {day}")
            e.path.write_text("---\n" + "\n".join(lines) + "\n---\n" + body, encoding="utf-8")
    return bad


# ---------------------------------------------------------------- write

def write_site(entries: list[Entry], site: dict, day: str, out: Path) -> list[str]:
    out.mkdir(parents=True, exist_ok=True)
    wk = out / ".well-known"
    wk.mkdir(exist_ok=True)
    written = []

    def put(rel: str, text: str):
        p = out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        written.append(rel)

    put("index.html", render_page(entries, site, day))
    put("llms.txt", render_llms(entries, site))
    put("sitemap.xml", render_sitemap(site, day))
    put("humans.txt", render_humans(site, day))
    put("portfolio.jsonld", json.dumps(jsonld_graph(entries, site, day), indent=2, ensure_ascii=False) + "\n")
    put("portfolio.ttl", render_turtle(entries, site, day))
    put(".well-known/webfinger", render_webfinger(site))
    put(".well-known/security.txt", render_security_txt(site, day))
    if site.get("did", {}).get("id"):
        put(".well-known/did.json", render_did(site))
    nostr = render_nostr(site)
    if nostr:
        put(".well-known/nostr.json", nostr)
    for name in ("agent-card.json", "agent.json"):
        src = ROOT / ".well-known" / name
        if src.exists():
            put(f".well-known/{name}", bump_card_version(src, day))

    if out.resolve() != ROOT.resolve():
        for rel in STATIC:
            src = ROOT / rel
            if not src.exists():
                continue
            dst = out / rel
            if src.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            written.append(rel)
    return written


# ---------------------------------------------------------------- main

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="lint only")
    ap.add_argument("--probe", action="store_true", help="fetch every entry url and report")
    ap.add_argument("--write", action="store_true", help="with --probe: record results in the entries")
    ap.add_argument("--out", type=Path, default=None, help="write the site here instead of the repo root")
    ap.add_argument("--date", default=None, help="override today's date (YYYY-MM-DD)")
    args = ap.parse_args(argv)

    entries = load_entries()
    site = load_site()
    day = args.date or today()

    if args.probe:
        bad = probe(entries, args.write)
        if args.write:
            entries = load_entries()
        print(f"{bad} address(es) did not answer 200")

    errors = check(entries, site)
    if errors:
        print("CHECK FAILED", file=sys.stderr)
        for err in errors:
            print("  " + err, file=sys.stderr)
        return 1
    print(f"check ok: {len(entries)} entries")
    if args.check or (args.probe and not args.write):
        return 0

    out = args.out or ROOT
    written = write_site(entries, site, day, out)
    errors = check_graph(out)
    if errors:
        print("GRAPH CHECK FAILED", file=sys.stderr)
        for err in errors:
            print("  " + err, file=sys.stderr)
        return 1
    print(f"wrote {len(written)} paths to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
