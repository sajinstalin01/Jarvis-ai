"""Allow-listed desktop app launcher. Never executes arbitrary shell text."""
import os, platform, subprocess, shutil, webbrowser
from urllib.parse import quote

APP_ALIASES={
 "notepad": ("notepad.exe",),
 "calculator": ("calc.exe",),
 "paint": ("mspaint.exe",),
 "file explorer": ("explorer.exe",),
 "task manager": ("taskmgr.exe",),
 "settings": ("ms-settings:",),
 "chrome": ("chrome",),
 "edge": ("msedge",),
 "firefox": ("firefox",),
 "vscode": ("code",),
 "visual studio code": ("code",),
 "whatsapp": ("whatsapp",),
}
def launch_app(name):
    key=name.strip().lower()
    if key not in APP_ALIASES: return False, "App isn't in the safe launch list. Add an alias in app_control.py if you trust it."
    target=APP_ALIASES[key][0]
    try:
        if key=="settings" and platform.system()=="Windows":
            os.startfile(target); return True,"Opening Windows Settings."
        if key=="whatsapp":
            webbrowser.open("https://web.whatsapp.com/")
            return True,"Opening WhatsApp Web. Sign in if needed and use its search bar to choose a contact."
        if platform.system()=="Windows":
            subprocess.Popen(["cmd","/c","start","",target],shell=False)
        elif platform.system()=="Darwin":
            subprocess.Popen(["open","-a",target])
        else:
            if not shutil.which(target): return False,f"{target} was not found. Install it or update app_control.py."
            subprocess.Popen([target])
        return True,f"Launching {name}."
    except Exception as e: return False,f"Couldn't launch {name}: {e}"
def web_search(query):
    webbrowser.open("https://www.google.com/search?q="+quote(query))
