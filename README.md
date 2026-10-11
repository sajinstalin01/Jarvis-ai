# J.A.R.V.I.S. — Iron Man-inspired AI Desktop GUI

A Python desktop assistant with a futuristic cyan-on-dark dashboard, reactor graphic, live clock, system telemetry, chat console, browser shortcuts, local commands, and optional Groq/Gemini AI chat.

## Features
- Sci-fi HUD-style desktop GUI built with CustomTkinter
- Responsive chat interface; AI requests run in a background thread
- Optional Groq AI with Gemini fallback
- Local commands: `help`, `time`, `date`, `system info`, `open YouTube`, `open GitHub`, `search <query>`, `calculate <expression>`
- Live clock, OS/Python/host information, browser quick actions
- API keys stored in a local `.env` file and excluded from Git
- Does not silently execute arbitrary shell commands or destructive system actions

## Quick start on Windows
1. Install Python 3.10+ and enable **Add Python to PATH**.
2. Download or clone this repository.
3. Double-click `run_windows.bat`.
4. The first launch installs dependencies and creates `.env` from `.env.example`.
5. Open `.env`, add a Groq and/or Gemini API key, save, and restart the app.

## Manual setup
```powershell
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
python jarvis.py
```

macOS/Linux: run `bash run_linux_mac.sh`.

## AI configuration
```env
GROQ_API_KEY=your_groq_key_here
GROQ_MODEL=llama-3.3-70b-versatile
GEMINI_API_KEY=your_gemini_key_here
GEMINI_MODEL=gemini-2.5-flash
```
Groq is tried first; Gemini is the fallback. Either provider is optional, and built-in commands work offline. Never place real API keys in source code or commit `.env` to GitHub. Revoke and rotate any key that has been exposed.

## Example commands
- `help`
- `time`
- `system info`
- `open YouTube`
- `search Python customtkinter`
- `calculate (25 * 4) / 2`
- `Explain Python threading simply`

## Troubleshooting
- `No module named customtkinter`: activate the virtual environment and run `pip install -r requirements.txt`.
- AI provider errors: check the key, model name, internet connection, and package installation.
- Local commands work but AI does not: configure one of the API keys in `.env` and restart.

## Files
- `jarvis.py` — app and GUI
- `requirements.txt` — dependencies
- `.env.example` — AI provider settings template
- `.gitignore` — keeps keys and virtual environments out of Git
- `run_windows.bat` / `run_linux_mac.sh` — launch scripts

## License
MIT; see `LICENSE`.
