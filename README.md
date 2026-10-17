# J.A.R.V.I.S. — Unified Iron Man-inspired desktop assistant

**One main application: `jarvis.py`.** The original V1 and V2 features are integrated into this file. The separate `jarvis_v2.py` compatibility file has been removed.

## Features
- Sci-fi CustomTkinter dashboard, animated reactor, loading splash, clock/date, system telemetry, quick links and clear-chat button.
- Sound toggle and optional spoken responses.
- Groq AI with Gemini fallback using keys from local `.env`.
- Local commands: time/date/system info, safe arithmetic calculator, browser search and website shortcuts.
- **Expanded Windows shortcuts:** Notepad, Calculator, Paint, File Explorer, Task Manager, Settings, Snipping Tool, PowerShell, Terminal, Command Prompt, Control Panel, Device Manager, Disk Management, Services, Event Viewer, Task Scheduler, System Information, Resource Monitor, Registry Editor, Windows Security, Magnifier, On-Screen Keyboard, Remote Desktop, Character Map, System Configuration, Computer Management, Performance Monitor, Disk Cleanup, DirectX Diagnostic, Windows Memory Diagnostic, Programs and Features, Network Connections, Windows Firewall, Sound Settings, Mouse Settings, Internet Properties, System Properties, Power Options, Local Users and Groups, Group Policy Editor, Certificate Manager and Steps Recorder.
- **Expanded third-party shortcuts:** Chrome, Edge, Firefox, Brave, Opera, Vivaldi, Arc, VS Code, Visual Studio, Android Studio, PyCharm, IntelliJ IDEA, Git Bash, GitHub Desktop, Cursor, Windsurf, Sublime Text, Postman, Docker Desktop, Jupyter Notebook, Anaconda Navigator, MySQL Workbench, DBeaver, FileZilla, VLC, OBS Studio, Discord, Telegram, WhatsApp Desktop, Spotify, Zoom, Microsoft Teams, Slack, Notion, Obsidian, Dropbox, OneDrive, Google Drive, Steam, Epic Games Launcher, 7-Zip, WinRAR, Notepad++, Photoshop, Premiere Pro, After Effects, GIMP, Blender, Audacity, HandBrake, DaVinci Resolve and Figma.
- GUI app shortcut panel now includes Windows Security, Settings, Zoom and Notion in addition to the existing quick-launch buttons. Use commands like `launch computer management`, `launch network connections`, `launch zoom`, `launch teams`, `launch notion`, `launch cursor`, `launch docker desktop`, `launch blender`, `launch gimp`, `launch figma`, `launch postman` or `launch filezilla`. Apps must be installed and discoverable by Windows, or their executable paths must be added to `APP_ALIASES`.
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
- `jarvis.py` — unified application, voice, AI, app launcher and WhatsApp Desktop launcher.
- `auto_update.py` — safe updater/watcher.
- `requirements.txt`, `.env.example`, `.gitignore` — dependencies/config.
- `run_windows.bat`, `run_linux_mac.sh` — setup, update and launch.
- `.github/workflows/python-check.yml` — CI syntax check.

**Notes:** Some third-party applications need their own installation and may not be discoverable if installed in a custom folder. Add an executable path to `APP_ALIASES` in `jarvis.py` if needed. JARVIS never executes arbitrary shell commands. WhatsApp Web/contact-search/message helper commands are not supported; only the installed desktop app is launched.

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
