---
title: Webcraft
section: works
label: Built
url: https://webcraft.justadestination.com
offline: 2026-11-10
summary: Agents build a small business a website from a short intake, take payment, and hand over a control panel with a site brain.
order: 20
---
Webcraft builds a website for a small business that wants to look like itself and does not have a studio budget. You answer a short intake. A small crew of agents researches the business, designs it, builds it, and takes payment. An optional domain comes with it. It is also the on-ramp we designed for a shop to get its own Symmate: the site brain that answers your customers is the start of a companion. Grok did the implementation, and the credits say so.

## What it does today
- The whole path is written: intake, research, design, build, checkout, provisioning, and a control panel where the business edits theme and sections and talks to its site brain.
- Four named agents hand the work along, routed through our own model proxy, with a tenant runtime that gives each site its own persistent agent.
- A readiness review hardened the provision route and the fallback page, and left the fix in writing.

## Where it is headed
A unit-test suite on the provision path, where the end-to-end scripts currently stand guard alone, and a host that answers. The product is for shops that cannot afford a miss, so it goes back up when both are true.
