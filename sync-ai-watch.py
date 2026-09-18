#!/usr/bin/env python3
"""sync-ai-watch: auto-links a new Hermes profile's auth.json the moment it
appears, so a freshly created profile is born already sharing credentials.

Stdlib-only polling watcher (no inotify/watchdog dependency): checks
~/.hermes/profiles/ every few seconds for a directory that doesn't yet have
auth.json symlinked to the canonical shared file, and links it immediately.
"""
from __future__ import annotations
import json
import os
import sys
import time
from pathlib import Path

HERMES_HOME = Path.home() / ".hermes"
PROFILES_DIR = HERMES_HOME / "profiles"
CANONICAL_AUTH = HERMES_HOME / "auth.json"
POLL_SECONDS = 3


def _ensure_canonical_auth() -> Path:
    if not CANONICAL_AUTH.exists():
        CANONICAL_AUTH.write_text(json.dumps({"version": 1, "providers": {}}, indent=2))
        os.chmod(CANONICAL_AUTH, 0o600)
    return CANONICAL_AUTH


def _link_profile(profile_dir: Path, canonical: Path) -> bool:
    """Link one profile's auth.json to canonical; return True if it changed anything."""
    auth_path = profile_dir / "auth.json"
    if auth_path.is_symlink():
        return False  # already linked (correctly or not — sync-ai.py install fixes drift)
    if auth_path.exists():
        # Pre-existing real file (e.g. profile created before this watcher started):
        # merge it in first so nothing is silently dropped, same as sync-ai.py install.
        try:
            profile_data = json.loads(auth_path.read_text(encoding="utf-8-sig"))
        except Exception:
            profile_data = {}
        if isinstance(profile_data, dict) and profile_data:
            try:
                canon_data = json.loads(canonical.read_text(encoding="utf-8-sig"))
            except Exception:
                canon_data = {"version": 1, "providers": {}}
            canon_providers = canon_data.setdefault("providers", {})
            for pid, state in (profile_data.get("providers") or {}).items():
                canon_providers.setdefault(pid, state)
            canon_pool = canon_data.setdefault("credential_pool", {})
            for pid, entries in (profile_data.get("credential_pool") or {}).items():
                existing = canon_pool.setdefault(pid, [])
                existing_ids = {e.get("id") for e in existing if isinstance(e, dict)}
                for entry in entries or []:
                    if isinstance(entry, dict) and entry.get("id") not in existing_ids:
                        existing.append(entry)
            canonical.write_text(json.dumps(canon_data, indent=2))
            os.chmod(canonical, 0o600)
        auth_path.unlink()
    try:
        auth_path.symlink_to(canonical)
        return True
    except OSError:
        return False


def run() -> None:
    canonical = _ensure_canonical_auth()
    known = set()
    print(f"sync-ai-watch: watching {PROFILES_DIR} (canonical: {canonical})", flush=True)
    while True:
        try:
            if PROFILES_DIR.is_dir():
                for entry in PROFILES_DIR.iterdir():
                    if not entry.is_dir() or entry.name in known:
                        continue
                    if (entry / "auth.json").is_symlink():
                        known.add(entry.name)
                        continue
                    if _link_profile(entry, canonical):
                        print(f"sync-ai-watch: linked new profile '{entry.name}'", flush=True)
                    known.add(entry.name)
        except Exception as exc:
            print(f"sync-ai-watch: error: {exc}", file=sys.stderr, flush=True)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    run()
