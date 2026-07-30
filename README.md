# Claude Capture Kit

Capture Claude Code / Cursor traffic on macOS or Windows. Output is delivery-ready JSON.

## Download

Direct links to the latest release:

- **macOS Apple Silicon** (M1/M2/M3/M4) → [claude-capture-kit-mac-arm64.zip](https://github.com/dongxuny/claude-capture-kit/releases/latest/download/claude-capture-kit-mac-arm64.zip)
- **macOS Intel** → [claude-capture-kit-mac-x86_64.zip](https://github.com/dongxuny/claude-capture-kit/releases/latest/download/claude-capture-kit-mac-x86_64.zip)
- **Windows 10/11 (x64)** → [claude-capture-kit-win.zip](https://github.com/dongxuny/claude-capture-kit/releases/latest/download/claude-capture-kit-win.zip)

Not sure which Mac? Run `uname -m` — `arm64` = arm64 build, `x86_64` = x86_64 build.

Or browse all versions on the [Releases page](../../releases).

## ⚠️ Required settings

| Setting | Value |
|---|---|
| Model | `claude-opus-4-6` / `claude-opus-4-7` / `claude-opus-4-8` |
| Thinking effort | `high` / `xhigh` / `max` |

Anything else (Opus 5, Sonnet, `medium` effort, etc.) is not acceptable.

---

## Run it — macOS

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

# Claude Code Desktop (Cmd+Q it first)
ANTHROPIC_BASE_URL=http://localhost:47821 open -a "Claude"

# Cursor (Cmd+Q it first; requires Custom API Key with Anthropic in settings)
ANTHROPIC_BASE_URL=http://localhost:47821 open -a "Cursor"
```

Inside Claude, run `/effort high` to switch to high-effort thinking.

## Run it — Windows

Extract the zip, `cd` into the folder in **PowerShell**, then open **two PowerShell windows**.

**Window A** — start the proxy (keep this window open):

```powershell
.\mitmdump.exe `
  --mode reverse:https://api.anthropic.com `
  --listen-port 47821 `
  -s .\save_raw.py
```

**Window B** — start Claude (pick one):

```powershell
# Claude Code CLI
$env:ANTHROPIC_BASE_URL="http://localhost:47821"; claude --model claude-opus-4-8

# Claude Code Desktop (close it first)
$env:ANTHROPIC_BASE_URL="http://localhost:47821"; Start-Process "$env:LOCALAPPDATA\claude\Claude.exe"

# Cursor (close it first; requires Custom API Key with Anthropic in settings)
$env:ANTHROPIC_BASE_URL="http://localhost:47821"; Start-Process "$env:LOCALAPPDATA\Programs\cursor\Cursor.exe"
```

Inside Claude, run `/effort high` to switch to high-effort thinking.

---

## Where the data goes

Every API call is saved into `data/` next to `save_raw.py`:

```
data/
└── {session_id}/
    └── {request_id}.json
```

Each file is a single-line, spec-compliant JSON with tokens and Bearer headers auto-redacted.

## Send the data

**macOS**:

```bash
zip -r ~/Desktop/capture-$(whoami)-$(date +%Y%m%d).zip data/
```

**Windows** (PowerShell):

```powershell
Compress-Archive -Path .\data -DestinationPath "$env:USERPROFILE\Desktop\capture-$env:USERNAME-$(Get-Date -Format 'yyyyMMdd').zip"
```

Send the resulting Desktop zip to whoever collects captures.

## Troubleshooting

- **macOS blocks the app / "Terminal wants to access Downloads"** — move the folder out of `~/Downloads`, then `xattr -cr /path/to/folder`.
- **Windows SmartScreen blocks `mitmdump.exe`** — click **More info → Run anyway**. Or right-click the file → Properties → **Unblock**.
- **`ConnectionRefused`** — the proxy in window A is not running or crashed.
- **Proxy runs but no logs appear** — Claude wasn't fully quit before relaunching, or `ANTHROPIC_BASE_URL` is mistyped.
- **Cursor traffic missing** — Cursor is on its own subscription. Switch to Custom API Key + Anthropic in settings.
- **Model shows Opus 5** — pass `--model claude-opus-4-8` on the CLI, or pick 4.8 from the model menu in Desktop / Cursor.
