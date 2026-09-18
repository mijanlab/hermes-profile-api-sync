<div align="center">

# `sync-ai` ◈ hermes-profile-api-sync

**Log in to an AI provider once. Every Hermes profile has it instantly — log out once, it's gone everywhere.**

Real-time • One Shared File • No Cron • No Drift

</div>

## The problem

[Hermes Agent](https://claude-code.nousresearch.com/docs) profiles are isolated on purpose — each has its own skills, memory, sessions, and cron, so a web-design profile never picks up cybersecurity skills. But that isolation extends to AI provider logins too: log in to Anthropic in one profile, and your other 8 profiles still say "not connected."

## The fix

Hermes stores every provider login in one file: `auth.json`. This tool replaces each profile's own `auth.json` with a symlink to a single shared file. There is no copy, no periodic sync job, and nothing to drift — Hermes' own file-locking and atomic writes already work correctly through a symlink, so every profile reads and writes the exact same credentials in real time.

- Log in anywhere → available everywhere, instantly.
- Log out anywhere → gone everywhere, instantly.
- **New profiles are covered automatically too** — a background watcher links a freshly created profile's `auth.json` within seconds, no command needed.
- Per-profile model **choice** (`config.yaml`) is untouched — only the login/credential is shared.
- Survives `hermes update` (nothing here depends on install internals, only on documented file paths).

## Quickstart

```bash
curl -fsSL https://raw.githubusercontent.com/mijanlab/hermes-profile-api-sync/main/install.sh | bash

sync-ai status    # see which profiles are linked
sync-ai install   # one-time: link every profile's auth.json to one shared file
```

That's it. No second command, no cron, no daemon. From now on, `hermes model` / `/login` / `hermes auth add <provider>` / `hermes logout` in any profile applies to all of them.

## Commands

| Command | What it does |
|---|---|
| `sync-ai status` | Shows each profile: linked, real file, or missing |
| `sync-ai install` | Backs up + merges each profile's existing logins, then symlinks it to one shared file |
| `sync-ai uninstall` | Reverts every profile back to its own independent `auth.json` |

## New profiles: fully automatic

`install.sh` also installs `sync-ai-watch` as a systemd service (root only). It polls `~/.hermes/profiles/` every few seconds and links any new profile's `auth.json` the moment it appears — created via CLI, the web UI, or the API, no difference. You never run a command for a new profile.

Not running as root, or no systemd? Just run `sync-ai install` again after creating a profile — it skips anything already linked.

## Safety

- `install` backs up every profile's original `auth.json` under `~/.hermes/backups/` before touching anything.
- Existing logins are merged into the shared file first — nothing is silently dropped.
- `uninstall` is a full, safe unwind at any time.

## What is NOT shared

Skills, memory, sessions, cron, and each profile's chosen model/provider in `config.yaml` stay fully isolated. Only the AI provider credential file (`auth.json`) is shared.
