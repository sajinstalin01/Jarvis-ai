# J.A.R.V.I.S. V2 — Iron Man-inspired desktop assistant

Python desktop assistant with an animated sci-fi GUI, loading screen, sound toggle, optional microphone voice input, optional spoken responses, Groq/Gemini AI chat, allow-listed app launching, web search, and WhatsApp Web helper commands.

## Quick start (Windows 10/11)
1. Install Python 3.10+ and enable **Add Python to PATH**.
2. Download/clone this repository.
3. Run `run_windows.bat`.
4. Edit the created `.env` file and add your own Groq or Gemini key for AI chat.
5. Restart the app after changing `.env`.

Manual setup:
```powershell
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
python jarvis_v2.py
```

## Commands
- `help`, `time`, `date`, `system info`
- `launch notepad`, `launch calculator`, `launch paint`, `launch file explorer`, `launch task manager`, `launch chrome`, `launch edge`, `launch firefox`, `launch vscode`
- `open YouTube`, `open Google`, `open GitHub`, `open Gmail`
- `search Python speech recognition`
- `open whatsapp`
- `whatsapp search Sajin`
- `whatsapp message Sajin | Hello, how are you?`

## Voice
Use the **VOICE** button and grant microphone access. Speech recognition requires a microphone and internet access for Google's speech recognition service. The optional `pyttsx3` voice output can be enabled with `JARVIS_SPEAK_RESPONSES=true` in `.env`. On Windows, if PyAudio installation fails, install a compatible PyAudio wheel for your Python version.

## WhatsApp privacy and safety
JARVIS opens WhatsApp Web and helps prepare commands, but it does not scrape private contacts or automatically send messages. Search for the contact inside WhatsApp, verify the exact person, and send the message yourself. This avoids messages going to the wrong person. WhatsApp Web must already be logged in.

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
- `requirements.txt` — dependencies
- `run_windows.bat` — Windows setup and launcher

## Limitations
The app has been committed to GitHub, but it has not been run on your specific Windows PC. Voice hardware, installed desktop applications, AI keys, and WhatsApp Web login need local testing.
