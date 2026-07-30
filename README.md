# Claude Capture Kit

Capture Claude Code / Cursor traffic on macOS or Windows. Output is delivery-ready JSON.

![Kit running: mitmdump on the left, Claude CLI going through the proxy on the right](img/running.png)

## Download

[Download the latest kit](https://github.com/dongxuny/claude-capture-kit/releases/latest/download/claude-capture-kit.zip) or browse the [Releases page](../../releases).

The kit itself is tiny — just `save_raw.py` and this README. You install `mitmproxy` locally with your platform's package manager.

## ⚠️ Required settings

| Setting | Value |
|---|---|
| Model | `claude-opus-4-6` / `claude-opus-4-7` / `claude-opus-4-8` |
| Thinking effort | `high` / `xhigh` / `max` |

Anything else (Opus 5, Sonnet, `medium` effort, etc.) is not acceptable.

---

## Setup (one-time)

### macOS

```bash
brew install mitmproxy
```

Don't have Homebrew? Run this first: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`.

### Windows

```powershell
winget install mitmproxy.mitmproxy
```

After it finishes, **close this PowerShell window and open a new one** — otherwise `mitmdump` won't be on `PATH` and you'll see `mitmdump: The term 'mitmdump' is not recognized as a cmdlet`.

Don't have winget? On Windows 10/11 it comes preinstalled. Otherwise download from [mitmproxy.org](https://mitmproxy.org/downloads/).

---

## Run it — macOS

Extract the kit zip and open **two Terminal windows** in the extracted folder.

**Terminal A** — start the proxy (keep this window open):

```bash
mitmdump --mode reverse:https://api.anthropic.com --listen-port 47821 -s ./save_raw.py
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

Extract the kit zip and open **two PowerShell windows** in the extracted folder.

**Window A** — start the proxy (keep this window open):

```powershell
mitmdump --mode reverse:https://api.anthropic.com --listen-port 47821 -s .\save_raw.py
```

**Window B** — start Claude:

For **Claude Code CLI**, run in the same PowerShell session:

```powershell
$env:ANTHROPIC_BASE_URL="http://localhost:47821"; claude --model claude-opus-4-8
```

For **Claude Code Desktop / Cursor**, set the env var user-wide, then launch normally from the Start Menu (close any running instance first):

```powershell
# Turn capture ON
[Environment]::SetEnvironmentVariable("ANTHROPIC_BASE_URL", "http://localhost:47821", "User")

# ... close Claude / Cursor if open, then launch them from Start Menu ...

# Turn capture OFF when done (and restart Claude / Cursor)
[Environment]::SetEnvironmentVariable("ANTHROPIC_BASE_URL", $null, "User")
```

Inside Claude, run `/effort high` to switch to high-effort thinking.

For Cursor, also ensure: Settings → Models → paste your Anthropic API key → enable Custom API Key mode. Without this, Cursor uses its own subscription and the proxy captures nothing.

---

## Where the data goes

Every API call is saved into `data/` next to `save_raw.py`, grouped by session:

![Data folder layout: kit folder containing data/{session_id}/{request_id}.json](img/data.png)

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

- **`ConnectionRefused`** — the proxy in window A is not running or crashed.
- **Proxy runs but no logs appear** — Claude wasn't fully quit before relaunching, or `ANTHROPIC_BASE_URL` is mistyped / not set in the current session.
- **Windows: `mitmdump: The term 'mitmdump' is not recognized`** — you're using the same PowerShell window where you ran `winget install`. Close it and open a new one.
- **Windows: `Start-Process: 系统找不到指定文件` / "cannot find the file"** — don't try to path-launch Claude Desktop. Use the persistent env var method above, then launch normally from the Start Menu.
- **Windows: Claude Desktop already open before you set the env var** — close it fully (system tray → quit) and reopen from Start Menu so it picks up the new env var.
- **Cursor traffic missing** — Cursor is on its own subscription. Switch to Custom API Key + Anthropic in settings.
- **Model shows Opus 5** — pass `--model claude-opus-4-8` on the CLI, or pick 4.8 from the model menu in Desktop / Cursor.
