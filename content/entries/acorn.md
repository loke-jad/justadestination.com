---
title: A.Corn
section: works
label: Built
url: https://acorn.aggressivelymediocre.me
summary: A hardened, rootless, seven-megabyte web node for self-hosting one site: passwordless claim, CMS, backups, an agent card, and a test harness that proves it.
order: 25
---
A.Corn is the smallest honest web server we could make for a person who wants to host their own site and never think about the server again. It is a single container that runs without root, with a read-only filesystem and every kernel capability dropped, and it still serves a modern single-page app, proxies an API, and refuses to start if its own configuration is wrong. The name is the point: a whole tree in something you can hold.

## What it does today
- Unprivileged Nginx on Alpine, about seven megabytes uncompressed, rendered from environment variables by plain shell with a fail-fast config check at boot.
- A passwordless claim: the first visitor registers a passkey and becomes the operator. Recovery is written down, not improvised.
- A small CMS with server-side state, timestamped backups and restore, a floating badge, and an agent card at the well-known address so other software can find it.
- Eight numbered test suites, run as one command, that attack it the way the internet would: abuse, bad config, image hygiene, a dead backend, load, the claim flow, backups, persistence.
- The TacksForSnacks app is baked in as the first thing it hosts.

## Where it is headed
A domain broker inside the node, so a person can buy the name and point it at the box from the same screen, then a one-click deploy script with an optional chat profile. Hosting it for other people as a service was considered and parked on purpose: the product is the node you keep, not a storefront.
