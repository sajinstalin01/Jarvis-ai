# J.A.R.V.I.S. — Unified Iron Man-inspired desktop assistant

**One main application: `jarvis.py`.** The original V1 and V2 features are integrated into this file. The separate `jarvis_v2.py` compatibility file has been removed.

## Features
- Sci-fi CustomTkinter dashboard, animated reactor, loading splash, clock/date, system telemetry, quick links and clear-chat button.
- Sound toggle and optional spoken responses.
- Groq AI with Gemini fallback using keys from local `.env`.
- Local commands: time/date/system info, safe arithmetic calculator, browser search and website shortcuts.
- **Windows app shortcuts:** Notepad, Calculator, Paint, File Explorer, Task Manager, Settings, Snipping Tool, PowerShell, Terminal, Command Prompt, Control Panel, Device Manager, Disk Management, Services, Event Viewer, Task Scheduler, System Information, Resource Monitor, Registry Editor, Windows Security, Magnifier, On-Screen Keyboard and Remote Desktop.
- **Third-party shortcuts:** Chrome, Edge, Firefox, Brave, Opera, Vivaldi, VS Code, Visual Studio, Android Studio, PyCharm, IntelliJ IDEA, Git Bash, GitHub Desktop, VLC, OBS Studio, Discord, Telegram, WhatsApp Web, Spotify, Steam, Epic Games Launcher, 7-Zip, WinRAR, Notepad++, Photoshop, Premiere Pro and After Effects.
- GUI app shortcut panel plus commands like `launch android studio`, `launch photoshop` or `launch snipping tool`. Apps must be installed and registered/on PATH or in a standard location for Windows to find them.
- Optional microphone input with SpeechRecognition and PyAudio; optional spoken responses with pyttsx3.
- WhatsApp Web helper for contact-search guidance and message drafts. It never scrapes private contacts or auto-sends messages.
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
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
python auto_update.py
python jarvis.py
```
Linux/macOS: `bash run_linux_mac.sh`.

## Commands
- `help`, `time`, `date`, `system info`
- `calculate 12 * (8 + 2)`
- `search Python speech recognition`
- `open YouTube`, `open Google`, `open GitHub`, `open Gmail`, `open Wikipedia`
- `launch notepad`, `launch calculator`, `launch snipping tool`, `launch powershell`, `launch device manager`
- `launch chrome`, `launch brave`, `launch vscode`, `launch android studio`, `launch photoshop`, `launch vlc`, `launch discord`, `launch telegram`
- `open whatsapp`, `whatsapp search Sajin`
- `whatsapp message Sajin | Hello, how are you?` (draft only)

## Voice and AI setup
Voice input requires SpeechRecognition, a microphone and compatible PyAudio; recognition uses Google's service and requires internet. Set `JARVIS_SPEAK_RESPONSES=true` for optional spoken replies. Groq is tried first, then Gemini. Keep API keys in local `.env`; never commit real keys.

## Auto-update configuration
The updater settings are in `update_config.json`:
- `enabled`: turn automatic updates on/off.
- `repository`: GitHub repository in `owner/name` format.
- `branch`: branch to update from (normally `main`).
- `git_executable`: optional full path to `git.exe` if Git is not on PATH.
- `watch_interval_seconds`: interval for watch mode (minimum 60 seconds).

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
Keep the JSON valid and use doubled backslashes in Windows paths. If Git is not installed, install Git for Windows first. Run `python auto_update.py` for one check or `python auto_update.py --watch` to keep checking. The updater only fast-forward pulls when the working tree is clean; it does not discard local edits. Restart JARVIS after an update to load changed Python code. The Windows launcher invokes the updater even if `git` is not on PATH, so it can show a helpful setup message.

## Project files
- `jarvis.py` — unified application, voice, AI, app launcher and WhatsApp helper.
- `auto_update.py` — safe updater/watcher.
- `requirements.txt`, `.env.example`, `.gitignore` — dependencies/config.
- `run_windows.bat`, `run_linux_mac.sh` — setup, update and launch.
- `.github/workflows/python-check.yml` — CI syntax check.

**Notes:** Some third-party applications need their own installation and may not be discoverable if installed in a custom folder. Add an executable path to `APP_ALIASES` in `jarvis.py` if needed. JARVIS never executes arbitrary shell commands. WhatsApp sending stays manual.
