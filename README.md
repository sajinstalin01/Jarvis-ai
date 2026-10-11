# J.A.R.V.I.S. V2 — Iron Man-inspired desktop assistant

Python desktop assistant with an animated sci-fi GUI, loading screen, sound toggle, optional microphone voice input, optional spoken responses, Groq/Gemini AI chat, allow-listed app launching, web search, WhatsApp Web helper commands, and GitHub update support.

## Quick start (Windows 10/11)
1. Install Python 3.10+ and Git; enable **Add Python to PATH**.
2. Clone the repository using `git clone https://github.com/sajinstalin01/Jarvis-ai.git` (recommended for updating) or download the ZIP.
3. Run `run_windows.bat`.
4. Edit the created `.env` file and add your own Groq or Gemini key for AI chat.
5. Restart the app after changing `.env`.

Manual setup:
```powershell
git clone https://github.com/sajinstalin01/Jarvis-ai.git
cd Jarvis-ai
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
python auto_update.py
python jarvis_v2.py
```

## GitHub auto-update
- `auto_update.py` fetches `origin/main` and fast-forward pulls new commits only if the working tree is clean.
- The Windows and Linux/macOS launchers check for updates before starting JARVIS.
- To watch for updates every five minutes: `python auto_update.py --watch --interval 300` (minimum interval is 60 seconds).
- The watcher updates files on disk; restart JARVIS to load changed Python code.
- Local edits are never discarded. If the branch diverges or there are uncommitted changes, the updater stops safely and explains why.
- For automatic updating, use a Git clone rather than the ZIP download. Git must be installed and the repository's origin must point to this project.
- GitHub Actions compiles Python source on pushes and pull requests.

## Commands
- `help`, `time`, `date`, `system info`
- `launch notepad`, `launch calculator`, `launch paint`, `launch file explorer`, `launch task manager`, `launch chrome`, `launch edge`, `launch firefox`, `launch vscode`
- `open YouTube`, `open Google`, `open GitHub`, `open Gmail`
- `search Python speech recognition`
- `open whatsapp`
- `whatsapp search Sajin`
- `whatsapp message Sajin | Hello, how are you?`

## Voice
Use the **VOICE** button and grant microphone access. Speech recognition requires a microphone and internet access for Google's speech recognition service. Optional `pyttsx3` voice output can be enabled with `JARVIS_SPEAK_RESPONSES=true` in `.env`. If PyAudio installation fails on Windows, install a compatible PyAudio wheel for your Python version.

## WhatsApp privacy and safety
JARVIS opens WhatsApp Web and helps prepare commands, but it does not scrape private contacts or automatically send messages. Search for the contact inside WhatsApp, verify the exact person, and send the message yourself. WhatsApp Web must already be logged in.

## App control safety
The launcher only supports an explicit allow-list in `app_control.py`; it does not execute arbitrary shell commands. Add an application alias only when you trust the executable.

## API key security
Keep real keys in the local `.env` file. It is excluded by `.gitignore`. Never commit API keys to GitHub. Groq is tried first; Gemini is the fallback.

## Project files
- `jarvis_v2.py` — V2 GUI, AI routing, voice button, command router, loading animation
- `jarvis.py` — original V1 application
- `voice_control.py` — optional microphone and TTS
- `app_control.py` — safe allow-listed desktop app launcher
- `whatsapp_control.py` — WhatsApp Web contact-search/message-draft helper
- `auto_update.py` — safe GitHub fetch/fast-forward updater and watcher
- `requirements.txt` — dependencies
- `.env.example` — settings template
- `run_windows.bat` / `run_linux_mac.sh` — setup and launch scripts
- `.github/workflows/python-check.yml` — syntax checks on GitHub

## Limitations
The code is committed to GitHub, but hardware, installed desktop applications, API keys, voice recognition, and WhatsApp Web login must be tested on your computer.
