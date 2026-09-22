# Keymaster 🔑

Automated API key rotation system for k3ss-official infrastructure.
**Owned by Janet (MBP guardian).**

## What it does

1. **Audits** — scans 1Password vaults (`hermes-agent`, `Developer`) for items tagged `keymaster-rotate`
2. **Rotates** — creates fresh credentials per provider, validates them, then revokes the old ones when the provider allows it
3. **Validates** — fires a cheap test call to confirm each key works
4. **Writes back** — updates 1Password vault items via the `op` CLI
5. **Reports** — sends a rotation summary to Telegram (`@Rae_plex_bot`)
6. **Glass-break** — pushes a GPG-encrypted snapshot to a private GitHub vault repo

## Architecture

```
keymaster/
├── keymaster.py           # CLI entry point (`keymaster` console script)
├── core/
│   ├── inventory.py       # Scans 1P vaults, builds provider registry
│   ├── runner.py          # Orchestrates audit / validate / rotate
│   ├── vault.py           # 1Password read/write via op CLI
│   ├── glass_break.py     # Encrypted backup to GitHub
│   └── notify.py          # Telegram reporting
├── rotators/
│   ├── api/               # Providers with management APIs
│   └── browser/           # Providers requiring Playwright
├── scripts/               # install + launchd wrappers (Janet MBP)
└── tests/                 # mocked unit tests (no live credentials)
```

## Quick start (Janet / MBP)

```bash
bash scripts/install.sh
# edit .env — never commit real secrets
python keymaster.py --list-providers
python keymaster.py --audit                 # inventory only (needs `op signin`)
python keymaster.py --validate              # cheap ping per key
python keymaster.py --rotate --dry-run      # plan only — no live rotate / vault write
python keymaster.py --rotate                # LIVE cycle
python keymaster.py --provider openai --rotate --dry-run
```

After editable install you can also run `keymaster ...` instead of `python keymaster.py ...`.

### Safety flags

| Flag / env | Effect |
|------------|--------|
| `--dry-run` | No provider rotate calls, no vault writes, no glass-break, no Telegram |
| `KEYMASTER_DRY_RUN=true` | Same as `--dry-run` for all commands |
| `--provider NAME` | Limit audit / validate / rotate to one provider |

**Never** run a live `--rotate` in CI. Tests use mocks only.

## Requirements

- Python 3.11+
- 1Password CLI (`op`) with an authenticated session (`op signin`)
- Playwright Chromium (`scripts/install.sh` handles this)
- GnuPG (`gpg`) for glass-break encryption
- Telegram bot token + chat ID (reporting)
- GitHub PAT with access to the glass-break vault repo

## 1Password item shape

For each rotatable secret in `hermes-agent` or `Developer`:

1. Tag the item with `keymaster-rotate`
2. Add a text field labeled `provider` whose value matches a rotator name (e.g. `openai`)
3. Keep the API secret in a **CONCEALED** field (password / credential)

## Providers

| Provider | Method | Module | Notes |
|----------|--------|--------|-------|
| `anthropic` | API | `rotators.api.anthropic` | Create → validate → delete old |
| `openai` | API | `rotators.api.openai` | Org API keys endpoint |
| `openrouter` | API | `rotators.api.openrouter` | Create → validate → delete old |
| `github_pat` | API | `rotators.api.github_pat` | Fine-grained PAT, 90-day expiry |
| `huggingface` | API | `rotators.api.huggingface` | Write token named `keymaster-rotated` |
| `tavily` | API | `rotators.api.tavily` | Single regenerate call (old key dies immediately) |
| `gemini` | API | `rotators.api.gemini` | Needs `GOOGLE_CLOUD_PROJECT` + admin access token for rotate |
| `deepseek` | Browser | `rotators.browser.deepseek` | Playwright; needs logged-in session on MBP |
| `meta` | Browser | `rotators.browser.meta` | Playwright; portal selectors are brittle |
| `telegram_bot` | Browser | `rotators.browser.telegram_bot` | BotFather via Telegram Web |

## launchd (MBP)

Plists under `scripts/` point at `/Users/janet/dev/keymaster/...`. Adjust paths if the clone lives elsewhere, then:

```bash
cp scripts/com.k3ss.janet.keymaster.plist ~/Library/LaunchAgents/
cp scripts/com.k3ss.janet.keymaster-validate.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.k3ss.janet.keymaster.plist
launchctl load ~/Library/LaunchAgents/com.k3ss.janet.keymaster-validate.plist
```

Rotate runs at 03:00; validate at 09:00 (local time).

## Development / tests

```bash
python3 -m pip install -e ".[dev]"
pytest
```

Tests mock HTTP and never call production APIs or touch real vaults.

## Gaps that need Janet’s MBP to verify

These cannot be fully proven in this environment without secrets / GUI sessions:

| Gap | How to verify on the MBP |
|-----|--------------------------|
| `op` inventory against real vaults | `op signin` then `python keymaster.py --audit` |
| Live API rotate for each provider | `--provider <name> --rotate` **once**, confirm vault + Telegram |
| Browser rotators (DeepSeek, Meta, Telegram) | Ensure Chromium session is logged in; run single-provider rotate; selectors may need updates if portals changed |
| Glass-break push | Set `GLASS_BREAK_*` in `.env`, run one live rotate, confirm `snapshots/*.json.gpg` in the vault repo |
| launchd paths | Confirm plist `ProgramArguments` match the clone path |

## License / ownership

Internal k3ss-official tooling. Janet (MBP guardian) owns operations and vault access.
