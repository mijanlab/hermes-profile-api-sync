#!/usr/bin/env python3
"""hermes-profile-api-sync v2: real-time shared AI provider credentials.

install   - back up + replace every profile's auth.json with a symlink to the
            default profile's auth.json (one real file = one source of truth)
status    - show which profiles are linked / real files / missing
uninstall - replace every symlink with an independent real copy again
"""
from __future__ import annotations
import json
import os
import shutil
import sys
import time
from pathlib import Path

HERMES_HOME = Path.home() / ".hermes"
PROFILES_DIR = HERMES_HOME / "profiles"
CANONICAL_AUTH = HERMES_HOME / "auth.json"
BACKUP_ROOT = HERMES_HOME / "backups"


def _profile_dirs():
    if not PROFILES_DIR.is_dir():
        return []
    return sorted(p for p in PROFILES_DIR.iterdir() if p.is_dir())


def _timestamp():
    return time.strftime("%Y%m%d%H%M%S")


def _ensure_canonical_auth():
    if not CANONICAL_AUTH.exists():
        CANONICAL_AUTH.write_text(json.dumps({"version": 1, "providers": {}}, indent=2))
        os.chmod(CANONICAL_AUTH, 0o600)
    return CANONICAL_AUTH


def _merge_into_canonical(profile_auth: Path, canonical: Path):
    """Fold a profile's existing providers/credential_pool into the canonical file
    before the profile's own auth.json is replaced by a symlink, so nobody's
    existing login is silently dropped."""
    try:
        profile_data = json.loads(profile_auth.read_text(encoding="utf-8-sig"))
    except Exception:
        return
    if not isinstance(profile_data, dict):
        return
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
    if not canon_data.get("active_provider") and profile_data.get("active_provider"):
        canon_data["active_provider"] = profile_data["active_provider"]
    canonical.write_text(json.dumps(canon_data, indent=2))
    os.chmod(canonical, 0o600)


def cmd_install():
    canonical = _ensure_canonical_auth()
    profiles = _profile_dirs()
    if not profiles:
        print("No profiles found under", PROFILES_DIR)
        return
    backup_dir = BACKUP_ROOT / f"pre-symlink-{_timestamp()}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    linked, already, skipped = [], [], []
    for profile in profiles:
        auth_path = profile / "auth.json"
        if auth_path.is_symlink():
            already.append(profile.name)
            continue
        if auth_path.exists():
            shutil.copy2(auth_path, backup_dir / f"{profile.name}.auth.json")
            _merge_into_canonical(auth_path, canonical)
            auth_path.unlink()
        try:
            auth_path.symlink_to(canonical)
            linked.append(profile.name)
        except OSError as exc:
            skipped.append((profile.name, str(exc)))
    print(f"Canonical credential file: {canonical}")
    print(f"Backups saved to: {backup_dir}")
    print(f"Linked ({len(linked)}): {', '.join(linked) or '-'}")
    if already:
        print(f"Already linked ({len(already)}): {', '.join(already)}")
    if skipped:
        print(f"Skipped ({len(skipped)}):")
        for name, err in skipped:
            print(f"  {name}: {err}")


def cmd_status():
    canonical = CANONICAL_AUTH.resolve() if CANONICAL_AUTH.exists() else CANONICAL_AUTH
    for profile in _profile_dirs():
        auth_path = profile / "auth.json"
        if auth_path.is_symlink():
            target = auth_path.resolve()
            state = "LINKED (ok)" if target == canonical else f"LINKED (points elsewhere: {target})"
        elif auth_path.exists():
            state = "real file (not shared)"
        else:
            state = "missing"
        print(f"{profile.name:28s} {state}")


def cmd_uninstall():
    profiles = _profile_dirs()
    backup_dir = BACKUP_ROOT / f"pre-uninstall-{_timestamp()}"
    reverted = []
    for profile in profiles:
        auth_path = profile / "auth.json"
        if not auth_path.is_symlink():
            continue
        target = auth_path.resolve()
        backup_dir.mkdir(parents=True, exist_ok=True)
        data = target.read_bytes() if target.exists() else b"{}"
        auth_path.unlink()
        auth_path.write_bytes(data)
        os.chmod(auth_path, 0o600)
        reverted.append(profile.name)
    if reverted:
        print(f"Reverted to independent copies ({len(reverted)}): {', '.join(reverted)}")
    else:
        print("No symlinked profiles found; nothing to revert.")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "install":
        cmd_install()
    elif cmd == "status":
        cmd_status()
    elif cmd == "uninstall":
        cmd_uninstall()
    else:
        print(__doc__)
        sys.exit(0 if cmd in ("-h", "--help") else 1)


if __name__ == "__main__":
    main()
