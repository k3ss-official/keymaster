# Keymaster 🔑

Automated API key rotation system for k3ss-official infrastructure.

## What it does

1. **Audits** — scans 1Password vaults (hermes-agent, Developer) for tracked API keys
2. **Rotates** — burns old keys and creates fresh credentials per provider
3. **Validates** — fires a cheap test call to confirm each new key works
4. **Writes back** — updates 1Password vault items via `op` CLI
5. **Reports** — sends rotation summary to Telegram @Rae_plex_bot
6. **Glass-break** — pushes encrypted backup to private GitHub repo

## Architecture

```
keymaster/
├── core/
│   ├── inventory.py       # Scans 1P vaults, builds provider registry
│   ├── runner.py          # Orchestrates full rotation cycle
│   ├── vault.py           # 1Password read/write via op CLI
│   ├── glass_break.py     # Encrypted backup to GitHub
│   └── notify.py          # Telegram reporting
├── rotators/
│   ├── api/               # Providers with management APIs
│   │   ├── anthropic.py
│   │   ├── openai.py
│   │   ├── openrouter.py
│   │   ├── github_pat.py
│   │   ├── huggingface.py
│   │   ├── tavily.py
│   │   └── gemini.py
│   └── browser/           # Providers requiring Playwright
│       ├── deepseek.py
│       ├── meta.py
│       └── telegram_bot.py
├── scripts/
│   ├── install.sh
│   ├── janet-keymaster-rotate.sh
│   ├── janet-keymaster-validate.sh
│   └── *.plist            # launchd agents
└── tests/
```

## Quick start

```bash
bash scripts/install.sh
cp .env.example .env && $EDITOR .env
python keymaster.py --audit      # dry-run inventory check
python keymaster.py --rotate     # live rotation
python keymaster.py --validate   # validate keys without rotating
```

## Requirements

- Python 3.11+
- 1Password CLI (`op`) — authenticated session
- Playwright (`pip install playwright && playwright install chromium`)
- Telegram bot token + chat ID
- GitHub PAT for glass-break vault

## Providers

| Provider | Method | Notes |
|----------|--------|-------|
| Anthropic | API | Deletes old, creates new |
| OpenAI | API | Deletes old, creates new |
| OpenRouter | API | Deletes old, creates new |
| GitHub PAT | API | Deletes old, creates new fine-grained PAT |
| HuggingFace | API | Deletes old, creates new |
| Tavily | API | Deletes old, creates new |
| Gemini | API | Deletes old, creates new |
| DeepSeek | Browser | Playwright-based |
| Meta AI | Browser | Playwright-based |
| Telegram Bot | Browser | Regenerates via BotFather |
