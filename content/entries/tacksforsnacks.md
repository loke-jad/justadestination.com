---
title: TacksForSnacks
section: works
label: Built
summary: An encrypted image vault with a chat room attached. Photos are scrubbed before they leave the browser; the room is end-to-end encrypted and runs on a server you deploy with one command.
order: 28
---
TacksForSnacks is a place to share pictures with people you trust and nobody else. Every image is stripped of its hidden location and camera data in the browser before it is uploaded, the galleries live in an encrypted vault, and the chat beside them is an end-to-end encrypted Matrix room on a server that you run. It started as a way to trade snapshots for snacks among friends, and it stayed that friendly.

## What it does today
- A single-page app with an EXIF scrubber built in, so the file that leaves your device has no coordinates, no serial numbers, and no timestamps you did not choose.
- A Matrix homeserver in the same stack for the room, and TackBot, a small admin bot that keeps house: bans, audit log, and the dull work.
- One-command deployment on any Docker host, timestamped JSON backups from the command line or the admin panel, and a restore that works even when the web container is down.
- Admin settings, galleries, uploads and the bot's memory all live in host volumes, so a crash or a move loses nothing.

## Where it is headed
It ships inside A.Corn as the first hosted app, and gets a public address when that node does. Until then it is a complete stack that runs anywhere Docker runs.
