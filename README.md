# J.A.R.V.I.S. — Unified Iron Man-inspired desktop assistant

**One main application: `jarvis.py`.** The original V1 and V2 features are integrated into this file. The separate `jarvis_v2.py` compatibility file has been removed.

## Features
- Redesigned professional dark HUD: deep navy panels, restrained teal/blue accents, refined typography, consistent borders, a cleaner dashboard, animated reactor, loading splash, live clock/date, system telemetry, quick links and clear-chat button.
- Animated HUD with a rotating/pulsing reactor, refined high-contrast panels, loading splash and live telemetry.
- Sound toggle, optional spoken responses, push-to-talk and **continuous turn-by-turn Voice Chat** with microphone listening, AI responses and spoken replies. Voice Chat listens again after the response finishes; click the toggle to stop.
- Groq AI with Gemini fallback using keys from local `.env`; requests include recent conversation turns and saved user memories to support natural follow-ups.
- Local commands: time/date/system info, safe arithmetic calculator, browser search and website shortcuts.
- **PC control:** `pc status`, `pc lock`, `pc mute`, `pc screenshot`; `pc shutdown` and `pc restart` always require confirmation in the desktop GUI and schedule the action after a 10-second delay.
- **Authenticated remote control:** start/stop from the sidebar. Supports remote status, launching an allow-listed app and locking the session. No arbitrary shell, remote file browsing or remote power commands.
- **Expanded Windows shortcuts:** Notepad, Calculator, Paint, File Explorer, Task Manager, Settings, Snipping Tool, PowerShell, Terminal, Command Prompt, Control Panel, Device Manager, Disk Management, Services, Event Viewer, Task Scheduler, System Information, Resource Monitor, Registry Editor, Windows Security, Magnifier, On-Screen Keyboard, Remote Desktop, Character Map, System Configuration, Computer Management, Performance Monitor, Disk Cleanup, DirectX Diagnostic, Windows Memory Diagnostic, Programs and Features, Network Connections, Windows Firewall, Sound Settings, Mouse Settings, Internet Properties, System Properties, Power Options, Local Users and Groups, Group Policy Editor, Certificate Manager and Steps Recorder.
- **Expanded third-party shortcuts:** Chrome, Edge, Firefox, Brave, Opera, Vivaldi, Arc, VS Code, Visual Studio, Android Studio, PyCharm, IntelliJ IDEA, Git Bash, GitHub Desktop, Cursor, Windsurf, Sublime Text, Postman, Docker Desktop, Jupyter Notebook, Anaconda Navigator, MySQL Workbench, DBeaver, FileZilla, VLC, OBS Studio, Discord, Telegram, WhatsApp Desktop, Spotify, Zoom, Microsoft Teams, Slack, Notion, Obsidian, Dropbox, OneDrive, Google Drive, Steam, Epic Games Launcher, 7-Zip, WinRAR, Notepad++, Photoshop, Premiere Pro, After Effects, GIMP, Blender, Audacity, HandBrake, DaVinci Resolve and Figma.
- GUI app shortcut panel now includes Windows Security, Settings, Zoom and Notion in addition to the existing quick-launch buttons. Use commands like `launch computer management`, `launch network connections`, `launch zoom`, `launch teams`, `launch notion`, `launch cursor`, `launch docker desktop`, `launch blender`, `launch gimp`, `launch figma`, `launch postman` or `launch filezilla`. Apps must be installed. JARVIS checks its safe alias list first, then searches Windows Start Menu shortcuts by exact normalized app name; custom executable paths can still be added to `APP_ALIASES`.
- Optional microphone input with SpeechRecognition and PyAudio; optional spoken responses with pyttsx3.
- WhatsApp shortcut launches the installed WhatsApp Desktop application only. WhatsApp Web opening, contact search, and message-draft helper commands are disabled.
- Safe GitHub fast-forward updater and GitHub Actions syntax checks.

## Quick start — Windows 10/11
1. Install Python 3.10+ and Git; enable **Add Python to PATH**.
2. Clone: `git clone https://github.com/sajinstalin01/Jarvis-ai.git`
3. Run `run_windows.bat`.
4. Add your own `GROQ_API_KEY` or `GEMINI_API_KEY` to the local `.env` file.
5. Restart JARVIS after editing `.env`.

Manual setup:
```powershell
git clone https://github.com/sajinstalin01/Jarvis-ai.git
cd Jarvis-ai
py -m venv .venv (cmd)
.venv\Scripts\activate.bat (cmd)
pip install -r requirements.txt
Copy-Item .env.example .env
python auto_update.py
python jarvis.py
```
Linux/macOS: `bash run_linux_mac.sh`.

## Commands
- `help`, `time`, `date`, `system info`
- `pc status`, `pc lock`, `pc mute`, `pc screenshot`, `pc shutdown`, `pc restart`
- `open <app name>` and `launch <app name>`; `open <website>`; `search <query>`
- `calculate 12 * (8 + 2)`
- `search Python speech recognition`
- `open YouTube`, `open Google`, `open GitHub`, `open Gmail`, `open Wikipedia`
- `launch notepad`, `launch calculator`, `launch snipping tool`, `launch powershell`, `launch device manager`
- `launch chrome`, `launch brave`, `launch vscode`, `launch android studio`, `launch photoshop`, `launch vlc`, `launch discord`, `launch telegram`
- `launch disk cleanup`, `launch computer management`, `launch network connections`, `launch system properties`
- `launch zoom`, `launch teams`, `launch slack`, `launch notion`, `launch obsidian`, `launch cursor`, `launch docker desktop`, `launch blender`, `launch gimp`, `launch figma`, `launch postman`, `launch filezilla`
- `open whatsapp` or `launch whatsapp` (opens WhatsApp Desktop only)
- `launch chrome search git` or `open chrome search git` (launches Chrome and searches Google)

## Voice and AI setup
Voice input requires SpeechRecognition, a microphone and compatible PyAudio; recognition uses Google's service and requires internet. Set `JARVIS_SPEAK_RESPONSES=true` for optional spoken replies. Groq is tried first, then Gemini. Keep API keys in local `.env`; never commit real keys.

**AI provider recovery:** JARVIS now defaults to Groq's `openai/gpt-oss-120b`. If your local `.env` still sets the retired `llama-3.3-70b-versatile` model, JARVIS automatically retries with a supported replacement after a model-not-found response. Gemini requests keep a live client reference for the full request and close it only after the response is received. You can override `GROQ_MODEL` and `GEMINI_MODEL` in `.env`; restart JARVIS after changes.

## Remote control (opt-in)

Use **Remote Control** in the sidebar to start or stop the authenticated API. Choose **NO** in the first prompt for loopback-only testing, or **YES** to explicitly allow connections from another device on your trusted local network. JARVIS generates a random bearer token in memory and displays it once; keep it private. The server stops and discards the token when you press the same sidebar button again or close JARVIS.

Authenticated API:
- `GET /api/status` — basic system metrics.
- `POST /api/command` with JSON `{"command":"launch notepad"}` — allow-listed app launch.
- Supported remote commands: `status`, `launch <app>`, `lock screen`.

Include the token in the HTTP `Authorization: Bearer <token>` header. The remote API intentionally rejects shell commands, arbitrary URLs, remote file access, shutdown/restart, and other unrestricted actions. **LAN mode uses plain HTTP, not TLS encryption**: only enable it on a trusted private network, do not forward the port from your router, and stop the server when finished. The token is not persisted to disk. A Windows firewall prompt may appear.

## Conversation memory and real-time voice chat

- JARVIS sends up to 16 recent user/assistant turns from local SQLite history to the AI provider, so follow-up questions can refer to earlier messages.
- Up to 8 recent saved memories are included as user-provided notes. Save them explicitly with `remember <text>`; review with `memories`, search with `memories <term>`, and remove with `forget memory <id>`.
- Use **VOICE CHAT: OFF** in the chat toolbar to enable continuous turn-based voice conversation. JARVIS listens through the microphone, transcribes speech using Google's cloud speech-recognition service, asks Groq/Gemini, speaks the answer with the installed system TTS, then listens for the next turn. Click **VOICE CHAT: ON** to stop.
- This is turn-based voice interaction, not a full-duplex streaming audio call. It requires internet, microphone permission, SpeechRecognition, compatible PyAudio, and pyttsx3/system TTS. Voice recognition sends audio to Google's recognition service; don't enable it for private conversations you don't want processed by that service.
- Conversation history and memories remain in local `jarvis_data/jarvis.sqlite3` and are not uploaded to GitHub. Do not store passwords or API keys in memory.

## Auto-update configuration
The updater settings are in `update_config.json`:
- `enabled`: turn automatic updates on/off.
- `repository`: GitHub repository in `owner/name` format.
- `branch`: branch to update from (normally `main`).
- `git_executable`: optional full path to `git.exe` if Git is not on PATH.
- `watch_interval_seconds`: interval for watch mode (minimum 60 seconds).\n- `local_changes_policy`: `stash_restore` (default) temporarily stashes tracked and untracked edits, updates with fast-forward only, then restores them; `skip` stops if local edits exist.

The updater now searches PATH and common Git for Windows installation folders for `git.exe`. If Git is installed in a custom location, set `git_executable` in `update_config.json`, for example:
```json
{
  "enabled": true,
  "repository": "sajinstalin01/Jarvis-ai",
  "branch": "main",
  "git_executable": "C:\\Program Files\\Git\\cmd\\git.exe",
  "watch_interval_seconds": 300
}
```
Keep the JSON valid and use doubled backslashes in Windows paths. If Git is not installed, install Git for Windows first. Run `python auto_update.py` for one check or `python auto_update.py --watch` to keep checking. The updater only fast-forward pulls. When local edits exist and `local_changes_policy` is `stash_restore`, it first saves tracked and untracked edits to a named Git stash, updates, and then restores those edits. If restoration conflicts, it keeps the stash as a backup and tells you to resolve the conflict; it never intentionally discards those edits. Set `local_changes_policy` to `skip` if you prefer manual handling. Restart JARVIS after an update to load changed Python code. The Windows launcher invokes the updater even if `git` is not on PATH, so it can show a helpful setup message.

## Project files
- `jarvis.py` — unified application, animated HUD, voice, AI, app launcher and local PC controls.
- `jarvis_control.py` — small, explicit local PC-control actions.
- `jarvis_remote.py` — authenticated allow-listed remote API.
- `auto_update.py` — safe updater/watcher.
- `requirements.txt`, `.env.example`, `.gitignore` — dependencies/config.
- `run_windows.bat`, `run_linux_mac.sh` — setup, update and launch.
- `.github/workflows/python-check.yml` — CI syntax check.

**Notes:** Third-party apps are launched through known aliases or exact matching Windows Start Menu shortcuts. Apps installed without Start Menu shortcuts may need an executable path added to `APP_ALIASES` in `jarvis.py`. JARVIS never executes arbitrary shell commands. WhatsApp Web/contact-search/message helper commands are not supported; only the installed desktop app is launched.

## New assistant modules

- **Navigation windows:** PC Monitor, Memory & History, Reminders, Workflows and Developer Mode are available from the sidebar.
- **AI health monitor:** checks configured Groq and Gemini credentials at startup in background threads. Key values are never printed. A network failure is reported separately from a clearly recognized invalid-key response.
- **Optional wake-word listening:** use the `WAKE: OFF` button and enable it to listen for “Hey JARVIS”. It requires SpeechRecognition, microphone access and compatible PyAudio. The current recognizer sends captured speech to Google's speech-recognition service; disable wake mode when not needed.
- **Live PC metrics:** CPU, RAM, disk usage and cumulative network transfer via `psutil`. Battery and temperature sensors appear only when the OS/hardware exposes them.
- **Persistent local memory and history:** messages, saved memories, reminders and workflows use SQLite in `jarvis_data/jarvis.sqlite3`. This directory is ignored by Git and data stays on this computer unless you manually share it. Use the Memory & History window to search, save memories and clear chat history; saved memories are kept when history is cleared.
- **Reminders:** `remind me in 10 minutes to stretch`, `remind me daily to review tasks`, `remind me weekly to back up`, `reminders`, and `delete reminder 1`. Supported repeating schedules are daily and weekly. JARVIS must be running to show a reminder notification.
- **Safe workflows:** `workflow save morning: launch chrome; open gmail`, `workflow list`, `workflow run morning`, and `workflow delete morning`. Only allow-listed launch/open/search command types can be saved, arbitrary URLs and shell commands are rejected, and running a workflow requires confirmation.
- **Developer mode:** `dev diagnostics` and `dev git status` report project syntax, Git status and latest commit. `dev test` runs the local unit tests. It does not execute arbitrary commands.
- **Tests:** run `python -m unittest discover -s tests -v`. GitHub Actions compiles Python files and runs the service tests.

### New commands

```text
remember I prefer dark mode
memories
memories dark
forget memory 1
history Gemini
remind me in 10 minutes to stretch
remind me daily to review tasks
reminders
delete reminder 1
workflow save morning: launch chrome; open gmail
workflow list
workflow run morning
workflow delete morning
dev diagnostics
dev git status
dev test
```

**Privacy and limitations:** Local conversation history and saved memories are stored unencrypted in the local SQLite database. Do not save passwords, API keys or other secrets as memories. The wake-word feature uses cloud speech recognition rather than an offline wake-word engine. Metrics such as temperature are not available on every computer.
