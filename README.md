# J.A.R.V.I.S. — Unified Iron Man-inspired desktop assistant

**The main app is now `jarvis.py`**, combining the original V1 dashboard and commands with V2 animations, voice input/output, desktop app controls, AI fallback, and WhatsApp helpers. `jarvis_v2.py` remains as a compatibility launcher.

## Features
- Sci-fi CustomTkinter dashboard, animated reactor, loading splash, clock/date, telemetry, quick links and clear-chat button.
- Sound toggle and optional spoken responses.
- Groq AI with Gemini fallback, configured using local `.env`.
- Local commands: time/date/system info, safe arithmetic calculator, browser search and website shortcuts.
- Allow-listed desktop application launching; arbitrary shell text is never executed.
- Optional microphone input using SpeechRecognition and PyAudio.
- WhatsApp Web contact search guidance and message draft preparation. No private-contact scraping or automatic sending.
- GitHub safe fast-forward updater.

## Quick start (Windows 10/11)
1. Install Python 3.10+ and Git, enabling **Add Python to PATH**.
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
- `launch notepad`, `launch calculator`, `launch paint`, `launch file explorer`, `launch task manager`, `launch chrome`, `launch edge`, `launch firefox`, `launch vscode`
- `open whatsapp`, `whatsapp search Sajin`
- `whatsapp message Sajin | Hello, how are you?` (draft only)

## Voice and AI setup
Voice input requires SpeechRecognition, a microphone and compatible PyAudio; recognition uses Google's service and requires internet. Set `JARVIS_SPEAK_RESPONSES=true` for optional spoken replies. Groq is tried first, then Gemini. Keep API keys in local `.env`; never commit real keys.

## Auto-update
Launchers check for GitHub updates when run from a Git clone. To watch every five minutes: `python auto_update.py --watch --interval 300`. The updater only fast-forward pulls when the working tree is clean; restart the app after an update to load changed Python code. GitHub Actions checks Python syntax on pushes and pull requests.

## Files
- `jarvis.py` — unified application and integrated helpers.
- `jarvis_v2.py` — compatibility launcher for old shortcuts.
- `auto_update.py` — safe updater/watcher.
- `requirements.txt`, `.env.example`, `.gitignore` — dependencies/config.
- `run_windows.bat`, `run_linux_mac.sh` — setup, update and launch.
- `.github/workflows/python-check.yml` — CI syntax check.

Local hardware, installed apps, API keys, microphone and WhatsApp login still need testing on your computer.
