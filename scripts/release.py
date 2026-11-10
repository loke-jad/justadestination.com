#!/usr/bin/env python3
"""Record a release of the site: content digest, git commit, and (when the tools exist)
an IPFS CID and an OpenTimestamps proof.

    python3 scripts/release.py            # build to _site, append to releases.json, stamp if possible

Optional tools, used only if found on PATH:
  ipfs  (kubo)              -> adds _site and records the CIDv1
  ots   (opentimestamps)    -> stamps the digest; proof lands in proofs/<date>.ots

Nothing here needs a wallet, a token, or a contract.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "_site"
RELEASES = ROOT / "releases.json"
PROOFS = ROOT / "proofs"


def run(*cmd: str, cwd: Path = ROOT) -> str:
    return subprocess.check_output(cmd, cwd=cwd, text=True).strip()


def tree_digest(folder: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(folder.rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(folder)).encode())
            h.update(b"\0")
            h.update(p.read_bytes())
            h.update(b"\0")
    return h.hexdigest()


def main() -> int:
    if subprocess.call([sys.executable, str(ROOT / "build.py"), "--out", str(SITE)]) != 0:
        return 1
    day = dt.date.today().isoformat()
    rec: dict = {"date": day, "sha256": tree_digest(SITE)}
    try:
        rec["commit"] = run("git", "rev-parse", "HEAD")
        rec["dirty"] = bool(run("git", "status", "--porcelain", "--", "content", "templates", "build.py"))
    except Exception:  # noqa: BLE001
        pass
    if shutil.which("ipfs"):
        rec["cid"] = run("ipfs", "add", "-rQ", "--cid-version", "1", str(SITE))
        print("ipfs cid", rec["cid"])
    else:
        print("ipfs not on PATH; no CID recorded")
    if shutil.which("ots"):
        PROOFS.mkdir(exist_ok=True)
        digest_file = PROOFS / f"{day}.sha256"
        digest_file.write_text(rec["sha256"] + "\n")
        subprocess.check_call(["ots", "stamp", str(digest_file)])
        rec["ots"] = f"proofs/{day}.sha256.ots"
        print("stamped", rec["ots"], "(run `ots upgrade` in a few hours to get the Bitcoin attestation)")
    else:
        print("ots not on PATH; no timestamp recorded")
    releases = json.loads(RELEASES.read_text()) if RELEASES.exists() else []
    releases.append(rec)
    RELEASES.write_text(json.dumps(releases, indent=2) + "\n")
    print("recorded release", rec["sha256"][:12], "in releases.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
