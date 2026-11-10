# justadestination llc

This file is for agents. The site is a static portfolio. It does not accept tasks.

## Who

justadestination llc. Loke, and a crew of agents. Public mail: loke@justadestination.com.

## What you may do

- Read https://justadestination.com/ and quote it.
- Read the charter excerpt at https://justadestination.com/charter/.
- Read the sift at https://justadestination.com/INVENTORY.md. It is a working list, not a launch announcement.
- Follow https://shadesr.net for NightCal and Umwelt Horizons.

## What you must not do

- POST a task, a job, or an A2A message to this host. Nothing is listening. A card that names an inbox we do not run would be a lie, so the card does not name one.
- Invent a status, a customer, a metric, or a lesson that the page does not state.
- Treat a folder, a README that says “live,” or a sketch as a shipped product. The page separates those on purpose.
- Ask for, or repeat, network maps, host addresses, credentials, or the internals of the fleet. The public description is deliberately incomplete.

## Discovery

- A2A card (protocol 1.0 shape): `/.well-known/agent-card.json`
- Older card shape: `/.well-known/agent.json`
- Index of public agents: `/.well-known/agents` and `/.well-known/agents.json`
- The only public agent is this portfolio. Its skills are reading, not doing.
- Linked data: `/portfolio.jsonld` (schema.org ItemList, stable `@id` per entry) and `/portfolio.ttl` (DOAP). The same graph is inline in the page head.
- Identity: `did:web:justadestination.com` at `/.well-known/did.json`; WebFinger for `acct:loke@justadestination.com`; `/.well-known/security.txt`; `/humans.txt`.
- Source: https://github.com/loke-jad/justadestination.com. The page is built from `content/` on every push; a failed check blocks the deploy.

## Skills

1. `read-portfolio` — what is live, what is built, what is in the works.
2. `read-charter` — the public excerpt of the Mox–Loke agreement, signed 27 April 2026.
3. `contact` — write to loke@justadestination.com. A person reads it.

## Voice

Short sentences. Name the state of the thing. If a host did not answer, say so. Do not warm a sentence past what the record says.

Page written 9 November 2026, rebuilt as a generated site 10 November 2026.
