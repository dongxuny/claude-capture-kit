# Claude Capture Kit

Capture Claude Code / Cursor traffic on macOS. Output is delivery-ready JSON.

## Download

Grab your build from the [Releases page](../../releases):

- **Apple Silicon (M1/M2/M3/M4)** → `claude-capture-kit-mac-arm64.zip`
- **Intel Mac** → `claude-capture-kit-mac-x86_64.zip`

Not sure? Run `uname -m` — `arm64` = arm64 build, `x86_64` = x86_64 build.

## ⚠️ Required settings

| Setting | Value |
|---|---|
| Model | `claude-opus-4-6` / `claude-opus-4-7` / `claude-opus-4-8` |
| Thinking effort | `high` / `xhigh` / `max` |

Anything else (Opus 5, Sonnet, `medium` effort, etc.) is not acceptable.

## Run it

Extract the zip, `cd` into the folder, then open **two Terminal windows**.

**Terminal A** — start the proxy (keep this window open):

```bash
./mitmproxy.app/Contents/MacOS/mitmdump \
  --mode reverse:https://api.anthropic.com \
  --listen-port 47821 \
  -s ./save_raw.py
```

**Terminal B** — start Claude (pick one):

```bash
# Claude Code CLI
ANTHROPIC_BASE_URL=http://localhost:47821 claude --model claude-opus-4-8

# Claude Code Desktop (quit it first with Cmd+Q)
ANTHROPIC_BASE_URL=http://localhost:47821 open -a "Claude"

# Cursor (quit it first; requires Custom API Key with Anthropic in settings)
ANTHROPIC_BASE_URL=http://localhost:47821 open -a "Cursor"
```

Inside Claude, run `/effort high` to switch to high-effort thinking.

## Where the data goes

Every API call is saved into `data/` next to `save_raw.py`:

```
data/
└── {session_id}/
    └── {request_id}.json
```

Each file is a single-line, spec-compliant JSON with tokens and Bearer headers auto-redacted.

## Send the data

```bash
zip -r ~/Desktop/capture-$(whoami)-$(date +%Y%m%d).zip data/
```

Send the resulting Desktop zip to whoever collects captures.

## Troubleshooting

- **macOS blocks the app or Terminal can't access Downloads** — move the folder out of `~/Downloads`, then `xattr -cr /path/to/folder`.
- **`ConnectionRefused`** — the proxy in Terminal A is not running or crashed.
- **Proxy runs but no logs appear** — Claude wasn't fully quit before relaunching, or `ANTHROPIC_BASE_URL` is mistyped.
- **Cursor traffic missing** — Cursor is on its own subscription. Switch to Custom API Key + Anthropic in settings.
- **Model shows Opus 5** — pass `--model claude-opus-4-8` on the CLI, or pick 4.8 from the model menu in Desktop / Cursor.
