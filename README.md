# J.A.R.V.I.S. — Unified Iron Man-inspired desktop assistant

**One main application: `jarvis.py`.** The original V1 and V2 features are integrated into this file. The separate `jarvis_v2.py` compatibility file has been removed.

## Features
- Redesigned professional dark HUD: deep navy panels, restrained teal/blue accents, refined typography, consistent borders, a cleaner dashboard, animated reactor, loading splash, live clock/date, system telemetry, quick links and clear-chat button.
- Realistic titanium-style theme is integrated directly into `ui.py`: softer blue-cyan highlights, warm amber state accents, layered panels, the saved custom interface font, refined scrollbars/tooltips and preserved monospaced telemetry.
- **Font collection:** open **Appearance → Font collection…** to preview and select an interface font, import personal `.ttf`, `.otf`, or `.ttc` files, remove custom font files, and save your choice. Imported fonts are stored locally in `custom_fonts/`; `config/ui_settings.json` stores the selected font family. Custom font binaries and personal settings are excluded from Git.
- **Improved open commands:** `open <app name>` tries the safe app launcher, exact/unique Start Menu shortcuts, and Windows' registered Apps list (`Get-StartApps`) for Microsoft Store apps. Store applications are started by their AppUserModel ID through `explorer.exe shell:AppsFolder\\<AppID>`, including Microsoft Store installs of WhatsApp Desktop and Telegram Desktop. If an alias is not installed, JARVIS reports a failure instead of claiming `cmd start` succeeded. Examples: `open whatsapp`, `open telegram`, `open chrome`, `open android studio`, `open notepad`, `open word`, `open photoshop`, `open gmail`, and `open google.com`. Named site searches work with `open google search <query>`, `open youtube search <query>`, and `open github search <query>`.
- Animated HUD with a rotating/pulsing reactor, refined high-contrast panels, loading splash and live telemetry.
- Sound toggle, optional spoken responses, push-to-talk and **continuous turn-by-turn Voice Chat** with microphone listening, AI responses and spoken replies. Voice Chat listens again after the response finishes; click the toggle to stop.
- Groq AI with Gemini fallback using keys from local `.env`; requests include recent conversation turns and saved user memories to support natural follow-ups.
- Local commands: time/date/system info, safe arithmetic calculator, browser search and website shortcuts.
- **Expanded PC operator:** mouse click/move/scroll/drag, restricted keyboard keys/hotkeys, app-window focus/minimize/maximize/restore/close/move across monitors, monitor enumeration, CPU/RAM/disk/network/GPU telemetry, Windows Wi-Fi/Bluetooth/display/sound settings, master volume and supported brightness, power-plan selection, and shutdown/restart/sleep/logout. Desktop input, window control, system settings and system power are enabled by default inside JARVIS; every action still requires its own confirmation. This does not bypass Windows/UAC or third-party app permissions. Messaging, calls and literal typing remain opt-in. Natural-language shortcuts include “show PC resources”, “open Wi-Fi settings”, “set volume to 50%”, “click at 500,300”, “minimize window Notepad”, and “shut down computer”.
- **Authenticated remote control:** start/stop from the sidebar. Supports remote status, launching an allow-listed app and locking the session. No arbitrary shell, remote file browsing or remote power commands.
- **Expanded Windows shortcuts:** Notepad, Calculator, Paint, File Explorer, Task Manager, Settings, Snipping Tool, PowerShell, Terminal, Command Prompt, Control Panel, Device Manager, Disk Management, Services, Event Viewer, Task Scheduler, System Information, Resource Monitor, Registry Editor, Windows Security, Magnifier, On-Screen Keyboard, Remote Desktop, Character Map, System Configuration, Computer Management, Performance Monitor, Disk Cleanup, DirectX Diagnostic, Windows Memory Diagnostic, Programs and Features, Network Connections, Windows Firewall, Sound Settings, Mouse Settings, Internet Properties, System Properties, Power Options, Local Users and Groups, Group Policy Editor, Certificate Manager and Steps Recorder.
- **Expanded third-party shortcuts:** Chrome, Edge, Firefox, Brave, Opera, Vivaldi, Arc, VS Code, Visual Studio, Android Studio, PyCharm, IntelliJ IDEA, Git Bash, GitHub Desktop, Cursor, Windsurf, Sublime Text, Postman, Docker Desktop, Jupyter Notebook, Anaconda Navigator, MySQL Workbench, DBeaver, FileZilla, VLC, OBS Studio, Discord, Telegram, WhatsApp Desktop, Spotify, Zoom, Microsoft Teams, Slack, Notion, Obsidian, Dropbox, OneDrive, Google Drive, Steam, Epic Games Launcher, 7-Zip, WinRAR, Notepad++, Photoshop, Premiere Pro, After Effects, GIMP, Blender, Audacity, HandBrake, DaVinci Resolve and Figma.
- GUI app shortcut panel now includes Windows Security, Settings, Zoom and Notion in addition to the existing quick-launch buttons. Use commands like `launch computer management`, `launch network connections`, `launch zoom`, `launch teams`, `launch notion`, `launch cursor`, `launch docker desktop`, `launch blender`, `launch gimp`, `launch figma`, `launch postman` or `launch filezilla`. Apps must be installed. JARVIS checks allow-listed aliases, Start Menu shortcuts and registered Store app IDs; it only reports success when a launch target could be handed off. Custom executable paths can still be added to `APP_ALIASES`.
- Optional microphone input with SpeechRecognition and PyAudio; optional spoken responses with pyttsx3.
- **ElevenLabs API suite:** masked API-key setup and validation, account/usage status, voice/model discovery, high-quality text-to-speech, Scribe speech-to-text, sound effects, music generation, multi-voice dialogue, speech-to-speech voice conversion, and background-noise isolation. Generated files are stored in the local, git-ignored `generated_audio/` folder. Each generation task asks for confirmation before using API credits; file uploads require a separate privacy confirmation.
- WhatsApp/Telegram interaction uses opt-in, permission-gated workflows: JARVIS can prepare a message draft/share link, but never chooses a recipient or presses Send. Call preparation only opens the app; you choose the contact and start the call yourself.
- Safe GitHub fast-forward updater and GitHub Actions syntax checks.

## Central Settings Hub

Click the **⚙** header button, then **ALL SETTINGS & FEATURES** to open the categorized settings hub. It groups assistant appearance, AI providers, audio, PC control, system metrics, windows/monitors, permissions, memory, knowledge, projects, tasks, workflows, proactive status, plugins, local models, remote control, security audit, backups and diagnostics.

PC-control permissions for desktop input, window management, system settings and system power are enabled by default for new installs and migrated older permission files. This enables JARVIS's own capability flags only; it cannot grant Windows/UAC or other application permissions. Sensitive actions continue to show a confirmation before execution. GUI actions are initiated on the Qt GUI thread, and chat commands are sent through the queued Qt signal to avoid cross-thread widget access.

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
- `open <app or website>` and `launch <app name>`; `open <site> search <query>`; `search <query>`
- `calculate 12 * (8 + 2)`
- `tasks add <title> | due=YYYY-MM-DD HH:MM`, `tasks list`, `tasks due`, `tasks done <id>`, `tasks delete <id>` (persistent local task tracker; due checks are on demand, not a background notifier)
- `search Python speech recognition`
- `open YouTube`, `open Google`, `open GitHub`, `open Gmail`, `open Wikipedia`
- `launch notepad`, `launch calculator`, `launch snipping tool`, `launch powershell`, `launch device manager`
- `launch chrome`, `launch brave`, `launch vscode`, `launch android studio`, `launch photoshop`, `launch vlc`, `launch discord`, `launch telegram`
- `launch disk cleanup`, `launch computer management`, `launch network connections`, `launch system properties`
- `launch zoom`, `launch teams`, `launch slack`, `launch notion`, `launch obsidian`, `launch cursor`, `launch docker desktop`, `launch blender`, `launch gimp`, `launch figma`, `launch postman`, `launch filezilla`
- `open whatsapp` or `launch whatsapp` (opens WhatsApp Desktop only)
- `launch chrome search git` or `open chrome search git` (launches Chrome and searches Google)

## App discovery and interaction permissions

JARVIS has a local permission manager for supported desktop actions. Run `permissions` to view current settings. Sensitive capabilities are off by default and are stored locally in `config/app_permissions.json` (excluded from Git).

- `apps` or `list apps` lists registered Windows app names; `apps search whatsapp`, `search app telegram`, and `refresh apps` help find an installed app. Then run `open <exact app name>`.
- Desktop input, window control, system settings and system power are enabled by default after the v2 permission migration. Individual actions still ask for confirmation. You do not need `grant permission desktop input`, `grant permission window control`, `grant permission system settings`, or `grant permission system power`. `grant permission read apps` permits reading registered display names only; it does **not** read private chats or app data.
- `grant permission launch apps` and `revoke permission launch apps` control JARVIS app launching.
- `grant permission type text` enables literal foreground typing. Every type action shows a confirmation, minimizes JARVIS, gives you 5 seconds to select the intended app and text field, then types plain text. It does not press Enter, click buttons, or send anything.
- `draft message on whatsapp: Hello` or `draft message on telegram: Hello` opens a message-share/draft link after confirmation. The text is part of the URL and may remain in browser history. You choose the recipient, review the content, and tap Send yourself.
- `prepare call on whatsapp` or `prepare call on telegram` opens that app after confirmation; you choose the contact and start the call manually.
- `grant permission send message`, `grant permission call`, or `grant permission all` enables the relevant JARVIS-side capability after a confirmation dialog. Use `revoke permission <capability>` to turn one off, or `revoke permission all` to disable all app-control capabilities.

**Important limitations:** Windows does not offer JARVIS a universal permission switch for every third-party app. JARVIS cannot grant itself Windows privacy permissions, read all files or private app contents, bypass app security, or silently send messages/place calls. Message and call actions remain user-controlled even when the corresponding JARVIS capability is enabled. These features have been source/CI tested, but actual WhatsApp/Telegram behavior depends on what is installed and registered on your Windows machine.

## ElevenLabs API integration

JARVIS supports major ElevenLabs audio endpoints through a lightweight Python REST client (no extra SDK dependency required). Create an API key from the [ElevenLabs dashboard](https://elevenlabs.io/app/settings/api-keys), then run `elevenlabs configure` and paste it into the masked dialog. The key is validated against the account endpoint and stored only in the local ignored `.env` and `config/api_keys.json` files; never put an API key in a chat command.

Use `elevenlabs help` for the in-app guide. Available commands:

- `elevenlabs status` — test account access and show account/plan details.
- `elevenlabs usage` — read usage and subscription limits returned by the API.
- `elevenlabs voices [search term]` — list/search registered voices and IDs.
- `elevenlabs models` — list text-to-speech models returned for your API key.
- `elevenlabs set-voice <voice_id>` and `elevenlabs set-model <model_id>` — save defaults locally.
- `elevenlabs speak <text>` or `elevenlabs tts <text>` — generate speech and play the result.
- `elevenlabs sfx <prompt>` — generate a short sound effect.
- `elevenlabs music <prompt>` — generate a 30-second music track (access can depend on plan).
- `elevenlabs dialogue <voice_id>: <text> || <voice_id>: <text>` — generate multi-voice dialogue.
- `elevenlabs transcribe "<audio/video path>"` — transcribe a local audio/video file using Scribe v2.
- `elevenlabs isolate "<audio path>"` — isolate speech/audio from background noise.
- `elevenlabs voice-change <voice_id> :: "<audio path>"` — transform recorded speech into an available target voice.

Requests run in background threads so the HUD remains responsive. Generated audio is saved under `generated_audio/` and automatically played for audio-generation commands. The folder is excluded from Git. Account, quota, voice availability, and generation endpoints depend on the API key's permissions and the ElevenLabs plan. Generating speech/music/effects can consume credits, so each generation asks for confirmation. Transcription, isolation, and voice conversion upload the selected local media after a separate confirmation.

### Optional ElevenLabs for normal JARVIS voice

Set `JARVIS_TTS_PROVIDER=elevenlabs` in your local `.env` to speak normal JARVIS responses with the selected ElevenLabs voice. This makes each spoken response an API request and may consume credits; the default remains local `pyttsx3`.

Set `JARVIS_STT_PROVIDER=elevenlabs` to use ElevenLabs Scribe for microphone recognition instead of the default Google Speech Recognition path. This uploads captured microphone audio to ElevenLabs. Keep `JARVIS_STT_PROVIDER=google` unless you explicitly want this data flow.

The default voice/model are `21m00Tcm4TlvDq8ikWAM` and `eleven_multilingual_v2`, respectively. Choose your own voice with the voice listing command. Voice and model IDs can vary by account, and unsupported requests will be reported by the API.

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

## Automatic memory evolution, API key pools, and free-form prompts

JARVIS accepts ordinary typed questions and requests in the chat input; unrecognized safe commands are sent to the configured AI providers. Local action commands remain allow-listed and sensitive operations keep their existing confirmation/permission checks. Do not paste API keys into the chat input.

- **Automatic memory evolution:** high-confidence explicit statements such as "I prefer dark mode", "My name is ...", "I'm building ...", and "I use ..." can update a local SQLite memory. The learner intentionally skips questions, general conversation, secrets/credentials, and sensitive personal topics. Learning can be controlled with `memory auto status`, `memory auto off`, and `memory auto on`. Review/remove entries with `memories` and `forget memory <id>`. Data remains local.
- **Live API health:** `api status` or `api check` makes an authenticated test request for each configured Groq, Gemini, and ElevenLabs key. Reports distinguish valid, invalid, permission/connection failure, rate limiting, and missing credentials. Values are always masked; key contents are never printed.
- **Multiple API keys per provider:** no application-level key-count limit is imposed. Add `GROQ_API_KEY_2`, `GROQ_API_KEY_3`, etc. and corresponding `GEMINI_API_KEY_2` / `ELEVENLABS_API_KEY_2` variables in your local ignored `.env`, or use `"api_keys": {"groq": ["key1", "key2"], "gemini": ["key1", "key2"], "elevenlabs": ["key1", "key2"]}` in ignored local `config/api_keys.json`. Single-key legacy fields continue to work. JARVIS tries the configured Groq key pool before Gemini fallback and uses the first authenticated ElevenLabs key for audio tasks.
- **API commands:** `api keys` lists per-provider key counts without showing secrets; `api status` checks every configured key live.

Health status requires internet access and makes a real request to each service. A valid key does not guarantee unlimited provider quotas, free usage, model access, or permission for every endpoint. Providers are only supported where JARVIS has an adapter; this is not a generic adapter for arbitrary API vendors.

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
- `font_manager.py` — user-owned font collection, import/remove, persistent choice and Appearance menu.
- `open_command.py` — safe parser for named websites, website queries, and app-opening syntax.
- `custom_fonts/` — local storage for imported TTF/OTF/TTC fonts; font binaries are git-ignored.
- `jarvis_control.py` — small, explicit local PC-control actions.
- `jarvis_remote.py` — authenticated allow-listed remote API.
- `auto_update.py` — safe updater/watcher.
- `requirements.txt`, `.env.example`, `.gitignore` — dependencies/config.
- `run_windows.bat`, `run_linux_mac.sh` — setup, update and launch.
- `.github/workflows/python-check.yml` — CI syntax check.

**Notes:** Third-party apps are launched through exact/unique Start Menu shortcuts or registered Windows app IDs. JARVIS never executes arbitrary shell commands. Installed-app discovery shows registered display names only; it does not read private chats, contacts, or arbitrary file contents.

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


## New PyQt6 holographic HUD

The active `jarvis.py` entry point now launches the supplied `ui.py` interface rather than the former CustomTkinter dashboard. The previous dashboard is retained as `jarvis_legacy.py` only as a compatibility source for its allow-listed app-launch and calculator helpers; it is not the active UI.

### First run
1. Update the repository and install dependencies: `python -m pip install -r requirements.txt`.
2. Copy `.env.example` to `.env` if needed, then add `GROQ_API_KEY` and/or `GEMINI_API_KEY`.
3. Start the application with `python jarvis.py`. If no API key is configured, the HUD opens its Gemini setup overlay.
4. UI preferences are saved locally in `config/ui_settings.json`; API setup is stored locally in `config/api_keys.json`. Do not commit either file with real keys.

### Integration notes
- The uploaded HUD is `ui.py`; `jarvis.py` connects its chat callbacks to the existing Groq/Gemini client, SQLite conversation history and memory, app-launch helpers, reminders, system metrics and allow-listed PC actions.
- The HUD uses compatibility modules under `memory/`, `core/` and `providers/` for optional settings panels. The provider pipeline editor remains a compatibility shell; actual AI chat uses the existing Groq-first, Gemini-fallback implementation in `jarvis_ai.py`.
- Push-to-talk uses the optional SpeechRecognition/PyAudio microphone stack. Wake-word activation is not bundled and reports as unavailable rather than pretending to listen.
- The remote API binds to loopback by default and supports status, lock and allow-listed app launch. Do not expose it to the public internet.
- PyQt6 Multimedia may be unavailable on stripped-down installations; the HUD handles that as an optional video feature.


## Advanced Feature Pack

Enter the command "features" in JARVIS chat for the complete command list.

- Vision: "vision screenshot", "vision ocr [image-path]". OCR requires optional Pillow, pytesseract and the Tesseract system application.
- Smart file intelligence: "files index <folder>", "files search <words>", "files summarize <file>". Search is local keyword ranking, not embedding-based semantic search.
- Network intelligence: "network inspect", "network diagnose"; basic DNS/interface checks only, no port scanning.
- Developer workbench: "dev check [file.py]", "dev test [folder]".
- Knowledge graph: "graph add <source> -> <relation> -> <target>", "graph search <words>" stored locally.
- Security center: "security audit" checks ignore rules and scans tracked text for likely secret patterns without printing values.
- Workflow studio: "workflow studio add <name>: time; calculate 2 + 2", "workflow studio list", "workflow studio run <name>". Current workflow runner supports validated read-only steps; no drag-and-drop canvas yet.
- Plugin SDK: "plugins list", "plugins validate"; manifests are validated but untrusted Python is never auto-executed.
- Multi-agent review: "agent mission <task>" requests planner, risk-reviewer and verifier perspectives from the configured AI provider. It makes multiple AI requests and is advisory only. "agent plan <task>" is local-only.
- Local model hub: "models status", "models hardware", "models pull <model>" uses Ollama at localhost:11434. Pulling can download gigabytes and only occurs after explicit command.
- Document/data analyst: "analyze <csv/json/file>" provides numeric CSV summaries, JSON structure and supported text extraction. PDF/DOCX requires optional pypdf/python-docx.
- Clipboard: "clipboard read" reads once; optional pyperclip required. No background clipboard monitor.
- Project context registry: "project add <name>: <folder>", "projects", "project use <name>". Active project is registered locally but is not yet injected into every AI prompt.
- Universal search: "find <words>" searches repo names, registered projects and indexed files.
- Backup/recovery: "backup create", "backup status", "backup restore stage <zip>". Backups exclude secrets/local databases; restore extracts to staging and never overwrites live files automatically.
- Performance profiler: "profile report" shows timings for instrumented operations.
- Cross-device companion: "companion status" documents the existing authenticated remote API. A dedicated Android companion app is not included. The current API uses HTTP; do not expose it publicly.
- Proactive context: "proactive on/off/status/check" optionally queries the active window if pygetwindow is installed. No continuous monitoring.
- Desktop agent: "agent plan" and "agent approve:" provide planning and a small read-only action allow-list; unrestricted mouse/keyboard automation remains disabled pending a platform-specific approval layer.
- Natural voice: existing turn-based voice remains; this feature pack does not claim full-duplex streaming speech.

All feature databases and registries stay under the ignored local jarvis_data folder. Optional dependencies are not required for standard startup.

## Permission-gated PC operator

Windows 10/11 is the primary target. Mouse/keyboard input, window management, system settings navigation and power actions are disabled until individually granted and still ask for confirmation for every action. Operating-system permission and UAC boundaries remain in force.

Grant only the capabilities you need:
- `grant permission desktop input` — mouse, foreground typing, scrolling, dragging and a restricted keyboard/hotkey allow-list.
- `grant permission window control` — focus, minimize, maximize, restore and close a visible window by title.
- `grant permission system settings` — open Wi-Fi, Bluetooth, display, sound, brightness or power settings; adjust volume with media keys.
- `grant permission system power` — confirmed Windows shutdown/restart (10-second delay), sleep or logout.
- `permissions` / `revoke permission system power` — inspect or disable capabilities.

Examples: `pc metrics`, `pc windows`, `pc monitors`, `pc window focus Chrome`, `pc window minimize Notepad`, `pc window move Chrome 0 0 1280 800`, `pc mouse click 500 300`, `pc mouse scroll 4`, `pc mouse drag 100 100 400 300`, `pc keyboard type Hello there`, `pc keyboard hotkey ctrl+c`, `pc keyboard press tab`, `pc settings wifi`, `pc settings bluetooth`, `pc volume up`, `pc power sleep`, `pc control help`.

Install optional dependencies with `python -m pip install -r requirements.txt`. Mouse/keyboard commands use PyAutoGUI's failsafe; moving the pointer to a screen corner can abort an action. GPU telemetry uses `nvidia-smi` if available; display enumeration uses screeninfo. Settings pages open for the user to change manually rather than being silently toggled. Native window management and power controls are Windows-only in this release. JARVIS does not read passwords or private app contents and is not unrestricted unattended remote-control software.

## Permission-gated PC operator

Windows 10/11 is the primary target. Mouse/keyboard input, window management, system settings navigation and power actions are disabled until individually granted and still ask for confirmation for every action. Operating-system permission and UAC boundaries remain in force.

Grant only the capabilities you need: `grant permission desktop input`, `grant permission window control`, `grant permission system settings`, or `grant permission system power`. Use `permissions` to inspect access and `revoke permission system power` to disable power actions.

Examples: `pc metrics`, `pc windows`, `pc monitors`, `pc window focus Chrome`, `pc window minimize Notepad`, `pc mouse click 500 300`, `pc mouse scroll 4`, `pc mouse drag 100 100 400 300`, `pc keyboard type Hello there`, `pc keyboard hotkey ctrl+c`, `pc keyboard press tab`, `pc settings wifi`, `pc settings bluetooth`, `pc volume up`, `pc power sleep`, `pc control help`.

Install optional dependencies with `python -m pip install -r requirements.txt`. PyAutoGUI uses its failsafe; moving the pointer to a screen corner can abort an action. GPU telemetry uses `nvidia-smi` if available; display enumeration uses screeninfo. Settings pages open for the user to change manually. Native window management and power controls are Windows-only in this release. JARVIS does not read passwords or private app contents and is not unrestricted unattended remote-control software.

## Expanded PC operator controls

New commands: `pc volume set 50`, `pc brightness set 60`, `pc power plan balanced`, `pc power plan high performance`, `pc power plan power saver`, `pc window switch Chrome`, and `pc window monitor Chrome 2`. Use `pc monitors` to list display numbers first. Natural-language aliases include “set volume to 45 percent”, “show open windows”, and “switch power plan to balanced”.

Volume level control uses the optional Windows-only `pycaw` package. Brightness uses Windows WMI and only works with compatible monitors. Power-plan switching uses Windows `powercfg`. Wi-Fi and Bluetooth commands open Windows Settings for manual changes rather than bypassing operating-system controls. Each setting change still requires the JARVIS permission and an action confirmation; multi-monitor window placement requires window-control permission.

## JARVIS persona and natural-language routing

The AI prompt now uses a calm, polished British-butler style, addresses the user as **Sir** by default, keeps replies concise, and requires honest action reporting. Clear natural-language requests are mapped to existing local commands before AI chat, including requests to check PC status, take a screenshot, lock the PC, open/launch an app, search, calculate, list tasks/reminders, and mark or remove a task. These aliases reuse existing permissions and safety checks; they do not add arbitrary shell execution or unrestricted computer access.

Examples:
- “Jarvis, check my PC” → `pc status`
- “Could you open Chrome for me?” → `open chrome`
- “Jarvis, show my tasks” → `tasks list`
- “Mark task 3 as complete” → `tasks done 3`
- “Jarvis, search for Python tutorials” → `search Python tutorials`

Irreversible system actions, deleting files, sending messages, installing software, and changing critical settings must remain confirmation-gated. The router is intentionally conservative: unclear requests fall back to normal AI conversation instead of guessing.