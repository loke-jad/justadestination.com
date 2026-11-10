---
title: Fleet Command and the JaD Portal
section: works
label: In daily use
note: by us, behind a sign-in
summary: The control panel for everything we run. Agents may act; nothing counts until a person presses verify.
inventory: Fleet Command
order: 30
---
Fleet Command is the control panel for everything we run: one front door, a directory of every service, a workbench, and a queue of the actions our agents took. The rule it enforces is the one we care most about. An agent may act, but nothing counts until a person looks at the before and after and presses verify.

## What it does today
- Small resident sysadmin agents on every machine that prune a full disk, restart a crashed service, and revive a dead container, within a bounded, whitelisted manifest. No arbitrary remote shell.
- Every autonomous action is recorded with a verified-by field that starts empty.
- A single source of truth for the fleet, published to the hub and mirrored to cloud storage, and an agent-facing MCP server so our assistants can read it too.
- The JaD Portal is the installable face of the same system: an app you add to your phone, gated on the public internet behind single sign-on.

## Where it is headed
The public door exists and is gated. It opens when the review queue has been boring for long enough to trust. This is the part of our stack we would most like to build for someone else.
