# Claude Capture Kit

Capture Claude Code / Cursor traffic on macOS or Windows. Output is delivery-ready JSON.

![Kit running: mitmdump on the left, Claude CLI going through the proxy on the right](img/running.png)

## Download

Pick your platform's zip from the [Releases page](../../releases):

- **macOS** → [claude-capture-kit-mac.zip](https://github.com/dongxuny/claude-capture-kit/releases/latest/download/claude-capture-kit-mac.zip) (5KB — you install mitmproxy via Homebrew)
- **Windows** → [claude-capture-kit-win.zip](https://github.com/dongxuny/claude-capture-kit/releases/latest/download/claude-capture-kit-win.zip) (26MB — includes `mitmdump.exe`)

## ⚠️ Required settings

| Setting | Value |
|---|---|
| Model | `claude-opus-4-6` / `claude-opus-4-7` / `claude-opus-4-8` |
| Thinking effort | `high` / `xhigh` / `max` |

Anything else (Opus 5, Sonnet, `medium` effort, etc.) is not acceptable.

---

## Run it — macOS

**One-time**: install mitmproxy.

```bash
brew install mitmproxy
```

Don't have Homebrew? Install it first with `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`.

Then extract the kit zip, `cd` into the folder, and open **two Terminal windows**.

**Terminal A** — start the proxy (keep this window open):

```bash
mitmdump --mode reverse:https://api.anthropic.com --listen-port 47821 -s ./save_raw.py
```

**Terminal B** — start Claude (pick one):

```bash
# Claude Code CLI
ANTHROPIC_BASE_URL=http://localhost:47821 claude --model claude-opus-4-8

# Claude Code Desktop (fully quit it first with pkill -f Claude)
ANTHROPIC_BASE_URL=http://localhost:47821 /Applications/Claude.app/Contents/MacOS/Claude &

# Cursor (fully quit it first with pkill -f Cursor; requires Custom API Key with Anthropic in settings)
ANTHROPIC_BASE_URL=http://localhost:47821 /Applications/Cursor.app/Contents/MacOS/Cursor &
```

Inside Claude, run `/effort high` to switch to high-effort thinking.

## Run it — Windows

Extract the kit zip. It already contains `mitmdump.exe` — no separate install needed.

Open **two PowerShell windows** in the extracted folder.

**Window A** — start the proxy (keep this window open):

```powershell
.\mitmdump.exe --mode reverse:https://api.anthropic.com --listen-port 47821 -s .\save_raw.py
```

If SmartScreen blocks it: right-click `mitmdump.exe` → Properties → check **Unblock** → OK. Or click **More info → Run anyway** on the SmartScreen dialog.

**Window B** — start Claude:

For **Claude Code CLI**:

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
- **macOS: Desktop / Cursor doesn't route through the proxy** — `open -a` sometimes drops env vars. Fully kill the app (`pkill -f Claude`) and launch the binary directly: `ANTHROPIC_BASE_URL=... /Applications/Claude.app/Contents/MacOS/Claude &`.
- **Windows: `Start-Process: 系统找不到指定文件` / "cannot find the file"** — don't try to path-launch Claude Desktop. Use the persistent env var method above, then launch normally from the Start Menu.
- **Windows: Claude Desktop already open before you set the env var** — close it fully (system tray → quit) and reopen from Start Menu so it picks up the new env var.
- **macOS: `mitmdump: command not found`** — `brew install mitmproxy` didn't complete or PATH wasn't refreshed. Open a new Terminal window and try again.
- **Cursor traffic missing** — Cursor is on its own subscription. Switch to Custom API Key + Anthropic in settings.
- **Model shows Opus 5** — pass `--model claude-opus-4-8` on the CLI, or pick 4.8 from the model menu in Desktop / Cursor.
