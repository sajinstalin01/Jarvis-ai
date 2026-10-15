"""Unified J.A.R.V.I.S. desktop assistant: original dashboard + V2 voice/app/WhatsApp features."""
from __future__ import annotations
import ast, datetime, operator, os, platform, queue, shutil, socket, subprocess, threading, time, urllib.parse, webbrowser
from pathlib import Path
from tkinter import messagebox
from jarvis_services import JarvisStore, system_metrics, developer_diagnostics, parse_reminder_command
try:
    import customtkinter as ctk
except ImportError as exc:
    raise SystemExit("Missing customtkinter. Run: pip install -r requirements.txt") from exc

ROOT = Path(__file__).resolve().parent
def load_env():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
load_env()
CYAN, BG, PANEL, GREEN, MUTED = "#00D9FF", "#07111F", "#0B1B2C", "#4DFFB5", "#8196AD"

# App aliases are deliberately allow-listed. Values are candidate executable names or paths.
APP_ALIASES = {
    # Windows built-ins
    "notepad": ("notepad.exe",), "calculator": ("calc.exe",), "paint": ("mspaint.exe",),
    "file explorer": ("explorer.exe",), "explorer": ("explorer.exe",),
    "task manager": ("taskmgr.exe",), "settings": ("ms-settings:",),
    "snipping tool": ("SnippingTool.exe", "snippingtool.exe"),
    "powershell": ("powershell.exe",), "terminal": ("wt.exe", "WindowsTerminal.exe"),
    "command prompt": ("cmd.exe",), "cmd": ("cmd.exe",), "control panel": ("control.exe",),
    "device manager": ("devmgmt.msc",), "disk management": ("diskmgmt.msc",),
    "services": ("services.msc",), "event viewer": ("eventvwr.msc",),
    "task scheduler": ("taskschd.msc",), "system information": ("msinfo32.exe",),
    "resource monitor": ("resmon.exe",), "registry editor": ("regedit.exe",),
    "windows security": ("windowsdefender:",), "magnifier": ("magnify.exe",),
    "on screen keyboard": ("osk.exe",), "remote desktop": ("mstsc.exe",), "winver": ("winver.exe",),
    "character map": ("charmap.exe",), "system configuration": ("msconfig.exe",),
    "computer management": ("compmgmt.msc",), "performance monitor": ("perfmon.msc",),
    "disk cleanup": ("cleanmgr.exe",), "directx diagnostic": ("dxdiag.exe",),
    "windows memory diagnostic": ("mdsched.exe",), "programs and features": ("appwiz.cpl",),
    "network connections": ("ncpa.cpl",), "windows firewall": ("firewall.cpl",),
    "sound settings": ("mmsys.cpl",), "mouse settings": ("main.cpl",),
    "internet properties": ("inetcpl.cpl",), "system properties": ("sysdm.cpl",),
    "power options": ("powercfg.cpl",), "fonts": ("control.exe",),
    "local users and groups": ("lusrmgr.msc",), "group policy editor": ("gpedit.msc",),
    "certificate manager": ("certmgr.msc",), "steps recorder": ("psr.exe",),
    "windows installer cleanup": ("cleanmgr.exe",),
    # Browsers
    "chrome": ("chrome.exe", "chrome"), "google chrome": ("chrome.exe", "chrome"),
    "edge": ("msedge.exe", "msedge"), "microsoft edge": ("msedge.exe", "msedge"),
    "firefox": ("firefox.exe", "firefox"), "brave": ("brave.exe", "brave"),
    "opera": ("opera.exe", "opera"), "vivaldi": ("vivaldi.exe", "vivaldi"),
    "arc": ("Arc.exe", "arc"),
    # Development tools
    "vscode": ("Code.exe", "code"), "visual studio code": ("Code.exe", "code"),
    "visual studio": ("devenv.exe",), "android studio": ("studio64.exe", "studio"),
    "pycharm": ("pycharm64.exe", "pycharm"), "intellij idea": ("idea64.exe", "idea"),
    "git bash": ("git-bash.exe", "git-bash"), "github desktop": ("GitHubDesktop.exe", "github"),
    "cursor": ("Cursor.exe", "cursor"), "windsurf": ("Windsurf.exe", "windsurf"),
    "sublime text": ("sublime_text.exe", "subl"),
    "postman": ("Postman.exe", "postman"), "docker desktop": ("Docker Desktop.exe", "docker"),
    "jupyter notebook": ("jupyter-notebook.exe", "jupyter notebook"),
    "anaconda navigator": ("anaconda-navigator.exe", "anaconda-navigator"),
    "mysql workbench": ("MySQLWorkbench.exe", "mysql-workbench"),
    "dbeaver": ("dbeaver.exe", "dbeaver"), "filezilla": ("filezilla.exe", "filezilla"),
    # Media, chat and gaming
    "vlc": ("vlc.exe", "vlc"), "vlc media player": ("vlc.exe", "vlc"),
    "obs": ("obs64.exe", "obs"), "obs studio": ("obs64.exe", "obs"),
    "discord": ("Discord.exe", "discord"), "telegram": ("Telegram.exe", "telegram"),
    "whatsapp": ("WhatsApp.exe", "WhatsApp"), "whatsapp desktop": ("WhatsApp.exe", "WhatsApp"), "spotify": ("Spotify.exe", "spotify"),
    "zoom": ("Zoom.exe", "zoom"), "microsoft teams": ("ms-teams.exe", "Teams.exe"),
    "teams": ("ms-teams.exe", "Teams.exe"), "slack": ("slack.exe", "Slack"),
    "notion": ("Notion.exe", "notion"), "obsidian": ("Obsidian.exe", "obsidian"),
    "dropbox": ("Dropbox.exe", "dropbox"), "onedrive": ("OneDrive.exe", "OneDrive"),
    "google drive": ("GoogleDriveFS.exe", "GoogleDrive"),
    "steam": ("steam.exe", "steam"), "epic games": ("EpicGamesLauncher.exe",),
    # Utilities and creative apps
    "7zip": ("7zFM.exe", "7zFM"), "7-zip": ("7zFM.exe", "7zFM"),
    "winrar": ("WinRAR.exe", "WinRAR"), "notepad++": ("notepad++.exe", "notepad++"),
    "photoshop": ("Photoshop.exe",), "premiere pro": ("Adobe Premiere Pro.exe",),
    "after effects": ("AfterFX.exe",), "gimp": ("gimp.exe", "gimp"),
    "blender": ("blender.exe", "blender"), "audacity": ("audacity.exe", "audacity"),
    "handbrake": ("HandBrake.exe", "HandBrake"), "davinci resolve": ("Resolve.exe",),
    "figma": ("Figma.exe", "figma"),
}
def launch_app(name, search_query=None):
    """Launch an allow-listed desktop app; optionally search from a browser."""
    key = name.strip().lower()
    if key == "whatsapp":
        key = "whatsapp desktop"
    candidates = APP_ALIASES.get(key)
    if not candidates:
        return False, f"'{name}' is not in JARVIS's app shortcuts. Type 'help' to see supported names."

    search_url = (
        "https://www.google.com/search?q=" + urllib.parse.quote(search_query)
        if search_query else None
    )
    browser_keys = {
        "chrome", "google chrome", "edge", "microsoft edge", "firefox",
        "brave", "opera", "vivaldi", "arc"
    }
    if search_query and key not in browser_keys:
        return False, "Search syntax is for browsers. Try: launch chrome search git"

    try:
        if platform.system() == "Windows":
            for candidate in candidates:
                expanded = os.path.expandvars(candidate)
                if expanded.endswith(":") or expanded.endswith("://"):
                    os.startfile(expanded)
                    return True, f"Opening {name}."
                if os.path.isfile(expanded) or shutil.which(expanded):
                    if expanded.lower().endswith((".msc", ".cpl")):
                        os.startfile(expanded)
                    else:
                        args = [expanded]
                        if search_url:
                            args.append(search_url)
                        subprocess.Popen(args, shell=False)
                    return True, (
                        f"Launching {name} and searching for '{search_query}'."
                        if search_query else f"Launching {name}."
                    )
            # Keep the fallback limited to fixed, allow-listed executable names.
            target = candidates[0]
            args = ["cmd", "/c", "start", "", target]
            if search_url:
                args.append(search_url)
            subprocess.Popen(args, shell=False)
            return True, (
                f"Asked Windows to launch {name} and search for '{search_query}'. "
                "If it did not open, check that the app is installed."
                if search_query else
                f"Asked Windows to open {name}. If it did not appear, check whether it is installed."
            )

        if key == "settings":
            if platform.system() == "Darwin":
                subprocess.Popen(["open", "-a", "System Settings"])
            else:
                subprocess.Popen(["xdg-open", "settings://"])
            return True, "Opening system settings."

        target = candidates[-1]
        if platform.system() == "Darwin":
            aliases = {
                "notepad": "TextEdit", "calculator": "Calculator", "paint": "Preview",
                "file explorer": "Finder", "task manager": "Activity Monitor",
                "vscode": "Visual Studio Code", "visual studio code": "Visual Studio Code",
                "android studio": "Android Studio", "telegram": "Telegram",
                "discord": "Discord", "spotify": "Spotify", "vlc": "VLC",
                "whatsapp desktop": "WhatsApp",
            }
            command = ["open", "-a", aliases.get(key, target)]
            if search_url:
                command.extend(["--args", search_url])
            subprocess.Popen(command)
        else:
            aliases = {
                "notepad": "gedit", "calculator": "gnome-calculator", "paint": "pinta",
                "file explorer": "xdg-open", "task manager": "gnome-system-monitor",
                "terminal": "x-terminal-emulator", "chrome": "google-chrome",
                "edge": "microsoft-edge", "whatsapp desktop": "whatsapp-for-linux",
            }
            cmd = aliases.get(key, target)
            if not shutil.which(cmd):
                return False, f"{cmd} was not found. Install it or update the app alias."
            args = [cmd]
            if key == "file explorer":
                args.append(str(Path.home()))
            elif search_url:
                args.append(search_url)
            subprocess.Popen(args)
        return True, (
            f"Launching {name} and searching for '{search_query}'."
            if search_query else f"Launching {name}."
        )
    except Exception as exc:
        return False, f"Couldn't launch {name}: {exc}"

def web_search(query):
    query = query.strip()
    if not query:
        return "Enter a search query."
    webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote(query))
    return "Opened a browser search for: " + query

def safe_calculate(expr):
    ops = {ast.Add:operator.add, ast.Sub:operator.sub, ast.Mult:operator.mul, ast.Div:operator.truediv,
           ast.Pow:operator.pow, ast.Mod:operator.mod, ast.USub:operator.neg, ast.UAdd:operator.pos, ast.FloorDiv:operator.floordiv}
    def ev(n):
        if isinstance(n, ast.Expression): return ev(n.body)
        if isinstance(n, ast.Constant) and type(n.value) in (int,float): return n.value
        if isinstance(n, ast.BinOp) and type(n.op) in ops:
            if isinstance(n.op, ast.Pow) and abs(ev(n.right)) > 10: raise ValueError("Exponent too large")
            return ops[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in ops: return ops[type(n.op)](ev(n.operand))
        raise ValueError("Use numbers and basic arithmetic operators only")
    try:
        result = ev(ast.parse(expr, mode="eval"))
        return f"Calculation result: {result}" if abs(float(result)) <= 1e100 else "Result is too large to display."
    except Exception as e: return f"I couldn't calculate that: {e}"

class JarvisApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark"); ctk.set_default_color_theme("blue")
        self.title("J.A.R.V.I.S. // Unified Stark Desktop"); self.geometry("1440x900"); self.minsize(1080,720); self.configure(fg_color=BG)
        self.events=queue.Queue(); self.busy=False; self.sound=True; self.sr=None; self.tts=None
        self.store=JarvisStore()
        self.wake_enabled=False; self.wake_stop=threading.Event(); self.wake_thread=None
        try:
            import speech_recognition as sr
            self.sr=sr
        except ImportError: pass
        try:
            import pyttsx3
            self.tts=pyttsx3.init(); self.tts.setProperty("rate",180)
        except Exception: pass
        self.grid_columnconfigure(1,weight=1); self.grid_rowconfigure(0,weight=1)
        self.build_ui(); self.clock_tick(); self.after(100,self.poll); self.system_status(); self.splash(); self.animate()
        self.start_gemini_validation(); self.start_groq_validation()
        self.after(2500, self.refresh_telemetry); self.after(5000, self.poll_reminders)
        self.add("J.A.R.V.I.S.","Dashboard ready. AI provider checks are running. Local memory and history are enabled.")

    def build_ui(self):
        side=ctk.CTkFrame(self,width=220,corner_radius=0,fg_color="#081522",border_width=1,border_color="#12334A")
        side.grid(row=0,column=0,sticky="nsew"); side.grid_propagate(False)
        ctk.CTkLabel(side,text="J.A.R.V.I.S.",font=ctk.CTkFont(size=26,weight="bold"),text_color=CYAN).pack(anchor="w",padx=18,pady=(26,2))
        ctk.CTkLabel(side,text="PERSONAL AI INTERFACE",font=ctk.CTkFont(size=10,weight="bold"),text_color=MUTED).pack(anchor="w",padx=20,pady=(0,24))
        for label,fn in [
            ("◈  Dashboard",lambda:self.add("SYSTEM","Dashboard online.")),
            ("✧  AI Assistant",lambda:self.entry.focus_set()),
            ("▤  PC Monitor",lambda:self.open_feature_window("monitor")),
            ("◷  Memory & History",lambda:self.open_feature_window("memory")),
            ("◉  Reminders",lambda:self.open_feature_window("reminders")),
            ("⌘  Workflows",lambda:self.open_feature_window("workflows")),
            ("</>  Developer Mode",lambda:self.open_feature_window("developer")),
            ("◉  WhatsApp",lambda:self.launch_shortcut("WhatsApp")),
            ("⚙  Settings",self.show_settings)]:
            ctk.CTkButton(side,text=label,command=fn,anchor="w",height=42,corner_radius=10,fg_color="transparent",hover_color="#12314A",text_color="#D7E8F4").pack(fill="x",padx=12,pady=4)
        ctk.CTkFrame(side,height=1,fg_color="#17364B").pack(fill="x",padx=14,pady=(20,14))
        ctk.CTkLabel(side,text="CORE STATUS",font=ctk.CTkFont(size=11,weight="bold"),text_color=MUTED).pack(anchor="w",padx=18)
        self.core=ctk.CTkLabel(side,text="● INITIALIZING",text_color="#FFCA71"); self.core.pack(anchor="w",padx=18,pady=(8,4))
        self.ai_status=ctk.CTkLabel(side,text="● AI: CHECKING",text_color=MUTED); self.ai_status.pack(anchor="w",padx=18,pady=4)
        self.groq_status=ctk.CTkLabel(side,text="● GROQ: WAITING",text_color=MUTED); self.groq_status.pack(anchor="w",padx=18,pady=4)
        self.gemini_status=ctk.CTkLabel(side,text="● GEMINI: WAITING",text_color=MUTED); self.gemini_status.pack(anchor="w",padx=18,pady=4)
        ctk.CTkFrame(side,height=1,fg_color="#17364B").pack(fill="x",padx=14,pady=(14,10))
        ctk.CTkLabel(side,text="QUICK STATUS",font=ctk.CTkFont(size=11,weight="bold"),text_color=MUTED).pack(anchor="w",padx=18,pady=(0,5))
        ctk.CTkLabel(side,text="AI providers\nGroq → Gemini fallback\nKeys stay in local .env",justify="left",text_color="#55748A",font=ctk.CTkFont(size=10)).pack(anchor="w",padx=18)
        ctk.CTkLabel(side,text="ALLOW-LISTED APP CONTROL\nWhatsApp sending stays manual.",justify="left",text_color="#55748A",font=ctk.CTkFont(size=10)).pack(side="bottom",anchor="w",padx=18,pady=20)
        main=ctk.CTkFrame(self,fg_color=BG,corner_radius=0); main.grid(row=0,column=1,sticky="nsew",padx=18,pady=16); main.grid_columnconfigure(0,weight=1); main.grid_rowconfigure(1,weight=1)
        head=ctk.CTkFrame(main,fg_color="transparent"); head.grid(row=0,column=0,sticky="ew",pady=(0,12))
        ctk.CTkLabel(head,text="STARK INDUSTRIES / PERSONAL INTELLIGENCE",text_color=MUTED,font=ctk.CTkFont(size=11,weight="bold")).pack(side="left")
        self.date=ctk.CTkLabel(head,text="",text_color=MUTED,font=ctk.CTkFont(size=11)); self.date.pack(side="right",padx=10)
        self.clock=ctk.CTkLabel(head,text="",text_color=CYAN,font=ctk.CTkFont(size=17,weight="bold")); self.clock.pack(side="right")
        body=ctk.CTkFrame(main,fg_color="transparent"); body.grid(row=1,column=0,sticky="nsew"); body.grid_columnconfigure(0,weight=2); body.grid_columnconfigure(1,weight=1); body.grid_rowconfigure(1,weight=1)
        hero=ctk.CTkFrame(body,fg_color=PANEL,border_width=1,border_color="#15415A",corner_radius=18); hero.grid(row=0,column=0,columnspan=2,sticky="ew",pady=(0,14)); hero.grid_columnconfigure(1,weight=1)
        self.reactor=ctk.CTkCanvas(hero,width=140,height=140,bg=PANEL,highlightthickness=0); self.reactor.grid(row=0,column=0,padx=(18,6),pady=12); self.draw_reactor()
        ht=ctk.CTkFrame(hero,fg_color="transparent"); ht.grid(row=0,column=1,sticky="w",padx=18,pady=20)
        ctk.CTkLabel(ht,text="GOOD TO SEE YOU, BOSS.",text_color="#EEF8FF",font=ctk.CTkFont(size=25,weight="bold")).pack(anchor="w")
        ctk.CTkLabel(ht,text="Unified AI, voice and desktop-control console.",text_color=MUTED,font=ctk.CTkFont(size=13)).pack(anchor="w",pady=(5,12))
        ctk.CTkLabel(ht,text="● SYSTEM NOMINAL",text_color=GREEN,fg_color="#10352F",corner_radius=8,font=ctk.CTkFont(size=11,weight="bold"),padx=12,pady=6).pack(anchor="w")
        chat=ctk.CTkFrame(body,fg_color=PANEL,border_width=1,border_color="#14334B",corner_radius=16); chat.grid(row=1,column=0,sticky="nsew",padx=(0,12)); chat.grid_columnconfigure(0,weight=1); chat.grid_rowconfigure(1,weight=1)
        ch=ctk.CTkFrame(chat,fg_color="transparent"); ch.grid(row=0,column=0,sticky="ew",padx=16,pady=(13,5))
        ctk.CTkLabel(ch,text="✧ JARVIS CONSOLE",text_color=CYAN,font=ctk.CTkFont(size=14,weight="bold")).pack(side="left")
        ctk.CTkButton(ch,text="CLEAR",width=60,height=26,command=self.clear_chat,fg_color="#10263A").pack(side="right")
        self.chat=ctk.CTkTextbox(chat,fg_color="#06101B",text_color="#DDEBF5",border_width=1,border_color="#133047",corner_radius=10,wrap="word",font=ctk.CTkFont(size=13)); self.chat.grid(row=1,column=0,sticky="nsew",padx=14,pady=8); self.chat.configure(state="disabled")
        bar=ctk.CTkFrame(chat,fg_color="transparent"); bar.grid(row=2,column=0,sticky="ew",padx=14,pady=(4,14)); bar.grid_columnconfigure(0,weight=1)
        self.entry=ctk.CTkEntry(bar,placeholder_text="Ask JARVIS or enter a command…",height=42,fg_color="#0A1826",border_color="#1C4963"); self.entry.grid(row=0,column=0,sticky="ew",padx=(0,7)); self.entry.bind("<Return>",lambda _e:self.send())
        ctk.CTkButton(bar,text="🎙 VOICE",width=86,height=42,command=self.listen,fg_color="#12435A").grid(row=0,column=1,padx=3)
        self.wake_btn=ctk.CTkButton(bar,text="WAKE: OFF",width=92,height=42,command=self.toggle_wake_word,fg_color="#12435A"); self.wake_btn.grid(row=0,column=2,padx=3)
        self.sound_btn=ctk.CTkButton(bar,text="♪ SOUND ON",width=96,height=42,command=self.toggle_sound,fg_color="#12435A"); self.sound_btn.grid(row=0,column=3,padx=3)
        self.send_btn=ctk.CTkButton(bar,text="TRANSMIT ➤",width=120,height=42,command=self.send,fg_color="#007F9F",hover_color="#009FC4"); self.send_btn.grid(row=0,column=4,padx=(3,0))
        right=ctk.CTkFrame(body,fg_color="transparent"); right.grid(row=1,column=1,sticky="nsew"); right.grid_columnconfigure(0,weight=1)
        tele=ctk.CTkFrame(right,fg_color=PANEL,border_width=1,border_color="#14334B",corner_radius=16); tele.grid(row=0,column=0,sticky="ew",pady=(0,12))
        ctk.CTkLabel(tele,text="SYSTEM TELEMETRY",text_color=CYAN,font=ctk.CTkFont(size=13,weight="bold")).pack(anchor="w",padx=16,pady=(15,10))
        self.telemetry=ctk.CTkLabel(tele,text="Loading…",justify="left",text_color="#B4C9D8",font=ctk.CTkFont(size=12)); self.telemetry.pack(anchor="w",padx=16,pady=(0,16))
        actions=ctk.CTkFrame(right,fg_color=PANEL,border_width=1,border_color="#14334B",corner_radius=16); actions.grid(row=1,column=0,sticky="ew"); actions.grid_columnconfigure((0,1),weight=1)
        ctk.CTkLabel(actions,text="QUICK ACTIONS",text_color=CYAN,font=ctk.CTkFont(size=13,weight="bold")).grid(row=0,column=0,columnspan=2,sticky="w",padx=16,pady=(15,9))
        for i,(label,url) in enumerate([("Open YouTube","https://youtube.com"),("Open Google","https://google.com"),("Open GitHub","https://github.com/sajinstalin01/Jarvis-ai"),("Open Gmail","https://mail.google.com")]):
            ctk.CTkButton(actions,text=label,height=36,fg_color="#10283B",hover_color="#19425A",anchor="w",command=lambda u=url:self.open_url(u)).grid(row=1+i//2,column=i%2,sticky="ew",padx=7,pady=5)
        ctk.CTkLabel(actions,text="Browser shortcuts use your default browser.",text_color="#5F7B90",font=ctk.CTkFont(size=10)).grid(row=3,column=0,columnspan=2,padx=12,pady=(8,13),sticky="w")
        apps=ctk.CTkFrame(right,fg_color=PANEL,border_width=1,border_color="#14334B",corner_radius=16)
        apps.grid(row=2,column=0,sticky="ew",pady=(12,0)); apps.grid_columnconfigure((0,1),weight=1)
        ctk.CTkLabel(apps,text="APP SHORTCUTS",text_color=CYAN,font=ctk.CTkFont(size=13,weight="bold")).grid(row=0,column=0,columnspan=2,sticky="w",padx=16,pady=(13,8))
        for i,name in enumerate(("Notepad","Calculator","File Explorer","Task Manager","Snipping Tool","PowerShell","Chrome","VS Code","Android Studio","VLC","Discord","Telegram","Spotify","WhatsApp","Windows Security","Settings","Zoom","Notion")):
            ctk.CTkButton(apps,text=name,height=31,fg_color="#10283B",hover_color="#19425A",
                          command=lambda n=name:self.launch_shortcut(n)).grid(row=1+i//2,column=i%2,sticky="ew",padx=6,pady=3)
        ctk.CTkLabel(apps,text="More: launch <app name> • Some shortcuts require installation.",text_color="#5F7B90",font=ctk.CTkFont(size=10)).grid(row=10,column=0,columnspan=2,padx=12,pady=(7,12),sticky="w")
        ctk.CTkLabel(main,text="JARVIS // UNIFIED PYTHON EDITION",text_color="#456176",font=ctk.CTkFont(size=10)).grid(row=2,column=0,sticky="ew",pady=(10,0))

    def draw_reactor(self):
        import math
        c=self.reactor
        c.create_oval(12,12,128,128,outline="#12415A",width=2); c.create_oval(22,22,118,118,outline=CYAN,width=2)
        c.create_oval(32,32,108,108,outline="#0785A8",width=1); c.create_oval(43,43,97,97,fill="#063247",outline=CYAN,width=2)
        c.create_oval(52,52,88,88,fill="#00A6D5",outline="#A6F4FF",width=2); c.create_oval(62,62,78,78,fill="#D3FCFF",outline="")
        for a in range(0,360,45):
            c.create_line(70+48*math.cos(math.radians(a)),70+48*math.sin(math.radians(a)),70+56*math.cos(math.radians(a)),70+56*math.sin(math.radians(a)),fill=CYAN,width=2)
    def splash(self):
        self.overlay=ctk.CTkFrame(self,fg_color="#030A12",corner_radius=0); self.overlay.place(relx=0,rely=0,relwidth=1,relheight=1)
        ctk.CTkLabel(self.overlay,text="J.A.R.V.I.S.",font=ctk.CTkFont(size=44,weight="bold"),text_color=CYAN).place(relx=.5,rely=.38,anchor="center")
        ctk.CTkLabel(self.overlay,text="UNIFIED PERSONAL AI // INITIALIZING",text_color=GREEN).place(relx=.5,rely=.48,anchor="center")
        self.progress=ctk.CTkProgressBar(self.overlay,width=320,progress_color=CYAN); self.progress.place(relx=.5,rely=.56,anchor="center"); self.progress.set(0); self.progress_step(0)
    def progress_step(self,n):
        if not self.winfo_exists() or not self.overlay.winfo_exists(): return
        self.progress.set(n/20)
        if n<20:self.after(65,lambda:self.progress_step(n+1))
        else:self.after(350,self.overlay.destroy)
    def animate(self):
        if not self.winfo_exists(): return
        try:self.reactor.itemconfigure(4,outline=CYAN if int(datetime.datetime.now().timestamp()*2)%2 else "#0A526D")
        except Exception:pass
        self.after(400,self.animate)
    def clock_tick(self):
        now=datetime.datetime.now(); self.clock.configure(text=now.strftime("%H:%M:%S")); self.date.configure(text=now.strftime("%a, %d %b %Y")); self.after(1000,self.clock_tick)
    def add(self,who,msg):
        self.chat.configure(state="normal"); self.chat.insert("end",f"[{datetime.datetime.now():%H:%M:%S}] {who}\n{msg}\n\n"); self.chat.see("end"); self.chat.configure(state="disabled")
        try: self.store.save_message(who, msg)
        except Exception: pass
        if self.sound and platform.system()=="Windows":
            try:
                import winsound; winsound.MessageBeep(winsound.MB_OK)
            except Exception:pass
    def clear_chat(self):
        self.chat.configure(state="normal"); self.chat.delete("1.0","end"); self.chat.configure(state="disabled")
    def toggle_sound(self):
        self.sound=not self.sound; self.sound_btn.configure(text="♪ SOUND ON" if self.sound else "♪ SOUND OFF")
    def listen(self):
        if not self.sr:
            self.add("SYSTEM","Voice input requires SpeechRecognition and a compatible PyAudio installation."); return
        def work():
            try:
                recog=self.sr.Recognizer()
                with self.sr.Microphone() as source:
                    self.events.put(("status","Listening…")); recog.adjust_for_ambient_noise(source,duration=.5); audio=recog.listen(source,timeout=6,phrase_time_limit=12)
                self.events.put(("status","Recognizing speech…")); self.events.put(("voice",recog.recognize_google(audio)))
            except Exception as e:self.events.put(("answer",f"Voice input failed: {e}"))
        threading.Thread(target=work,daemon=True).start()
    def speak(self,msg):
        if not self.tts or os.getenv("JARVIS_SPEAK_RESPONSES","false").lower()!="true":return
        def work():
            try:self.tts.say(str(msg)[:1500]); self.tts.runAndWait()
            except Exception:pass
        threading.Thread(target=work,daemon=True).start()
    def send(self):
        if self.busy:return
        prompt=self.entry.get().strip()
        if not prompt:return
        self.entry.delete(0,"end"); self.add("BOSS",prompt); self.busy=True; self.send_btn.configure(state="disabled",text="PROCESSING…")
        threading.Thread(target=self.process,args=(prompt,),daemon=True).start()
    def process(self,prompt):
        try:
            answer=self.command(prompt)
            if answer is None:answer=self.ask_ai(prompt)
        except Exception as e:answer=f"An error occurred: {e}"
        self.events.put(("answer",answer))
    def command(self,text):
        p=text.strip().lower()
        if p in ("help","commands","what can you do"):
            return ("Commands:\n• help, time, date, system info
• remember <text>, memories [search], forget memory <id>, history [search]
• remind me in 10 minutes to <task>; remind me daily/weekly to <task>; reminders; delete reminder <id>
• workflow save <name>: launch chrome; open github; workflow list/run/delete <name>
• dev diagnostics, dev test, dev git status
• wake word: click WAKE: OFF and say 'Hey JARVIS' (SpeechRecognition + PyAudio required)
• help, time, date, system info\n• calculate <math expression>\n• search <query>; open YouTube/Google/GitHub/Gmail/Wikipedia\n• launch <app name> — Windows tools, browsers, developer apps, media apps and utilities\n• Windows tools: launch disk cleanup, launch computer management, launch network connections, launch system properties\n• Apps: launch zoom, launch teams, launch slack, launch notion, launch obsidian, launch cursor, launch docker desktop, launch blender, launch gimp, launch figma, launch postman, launch filezilla\n• examples: launch snipping tool, launch powershell, launch android studio, launch photoshop, launch vlc\n• open whatsapp / launch whatsapp — launches the installed WhatsApp Desktop app only\n• launch chrome search git — launches Chrome and searches Google for git\n• open <app name> / launch <app name>; open <website>; search <query>\n• ask a question for Groq/Gemini AI\n\nConfigure GROQ_API_KEY or GEMINI_API_KEY in .env for AI chat.")
        if p.startswith("remember "):
            try:
                memory_id=self.store.remember(text[9:])
                return f"Saved local memory #{memory_id}. Use 'memories' to view it or 'forget memory {memory_id}' to delete it."
            except Exception as exc:return f"Couldn't save memory: {exc}"
        if p=="memories" or p.startswith("memories "):
            query=text[8:].strip() if len(text)>8 else ""
            rows=self.store.list_memories(query)
            return "\n".join(f"#{r['id']} [{r['created_at'][:16]}] {r['content']}" for r in rows) if rows else "No matching saved memories."
        if p.startswith("forget memory "):
            try:return "Memory deleted." if self.store.forget_memory(int(text.rsplit(" ",1)[1])) else "Memory ID not found."
            except (ValueError,IndexError):return "Usage: forget memory <id>"
        if p=="history" or p.startswith("history "):
            query=text[7:].strip() if len(text)>7 else ""
            rows=self.store.search_history(query,limit=30)
            return "\n".join(f"#{r['id']} [{r['created_at'][:16]}] {r['speaker']}: {r['content'][:220]}" for r in rows) if rows else "No matching conversation history."
        if p.startswith("remind me "):
            try:
                parsed=parse_reminder_command(text)
                if not parsed:return "Use: remind me in 10 minutes to stretch; remind me daily to review; or remind me weekly to back up."
                message,due,recurrence=parsed
                rid=self.store.add_reminder(message,due,recurrence)
                return f"Reminder #{rid} scheduled for {due.astimezone().strftime('%Y-%m-%d %H:%M %Z')} ({recurrence})."
            except Exception as exc:return f"Couldn't schedule reminder: {exc}"
        if p=="reminders":
            rows=self.store.list_reminders()
            return "\n".join(f"#{r['id']} {r['due_at'][:16]} [{r['recurrence']}] {r['message']}" for r in rows) if rows else "No active reminders."
        if p.startswith("delete reminder "):
            try:return "Reminder deleted." if self.store.delete_reminder(int(text.rsplit(" ",1)[1])) else "Reminder ID not found."
            except (ValueError,IndexError):return "Usage: delete reminder <id>"
        if p.startswith("workflow save "):
            try:
                payload=text[len("workflow save "):]
                name,steps_text=payload.split(":",1)
                steps=[part.strip() for part in steps_text.split(";") if part.strip()]
                self.store.save_workflow(name,steps)
                return f"Saved workflow '{name.strip()}' with {len(steps)} step(s). Run it with 'workflow run {name.strip()}'."
            except Exception as exc:return f"Workflow not saved: {exc}. Example: workflow save morning: launch chrome; open gmail"
        if p=="workflow list":
            rows=self.store.list_workflows()
            return "\n".join(f"{r['name']}: {'; '.join(r['steps'])}" for r in rows) if rows else "No saved workflows."
        if p.startswith("workflow delete "):
            name=text[len("workflow delete "):].strip()
            return "Workflow deleted." if self.store.delete_workflow(name) else "Workflow not found."
        if p.startswith("workflow run "):
            name=text[len("workflow run "):].strip()
            workflow=self.store.get_workflow(name)
            if not workflow:return "Workflow not found. Use 'workflow list'."
            self.events.put(("workflow_confirmation",workflow))
            return f"Workflow '{name}' is waiting for your confirmation in the GUI."
        if p in ("dev diagnostics","dev git status"):
            return developer_diagnostics()
        if p=="dev test":
            import py_compile
            try:
                py_compile.compile(str(ROOT/"jarvis.py"),doraise=True)
                py_compile.compile(str(ROOT/"jarvis_services.py"),doraise=True)
                return "Python syntax check passed for jarvis.py and jarvis_services.py."
            except py_compile.PyCompileError as exc:return f"Syntax check failed: {exc}"
        if p in ("hi","hello","hey","hello jarvis","hi jarvis"):return "Hello, Boss. All primary systems are standing by."
        if p=="time" or "what time" in p:return "Local time: "+datetime.datetime.now().strftime("%I:%M:%S %p")
        if p in ("date","today's date","what is today's date") or "what date" in p:return "Today is "+datetime.datetime.now().strftime("%A, %d %B %Y")
        if p in ("system info","computer info","system status"):
            return f"Host: {socket.gethostname()}\nOS: {platform.platform()}\nPython: {platform.python_version()}\nArchitecture: {platform.machine()}\nProcessor: {platform.processor() or 'Not reported'}"
        if p in ("whatsapp", "open whatsapp", "launch whatsapp", "open whatsapp desktop", "launch whatsapp desktop"):
            return launch_app("whatsapp")[1]
        if p.startswith("search "):
            return web_search(text[7:].strip())
        if p.startswith("calculate "):
            return safe_calculate(text[10:].strip())
        if p.startswith("launch ") or p.startswith("open "):
            verb, remainder = text.split(" ", 1)
            remainder = remainder.strip()
            if not remainder:
                return f"Usage: {verb} <app name or website>"
            # Syntax such as "launch chrome search git" or "open chrome search git".
            search_pos = remainder.lower().find(" search ")
            if search_pos >= 0:
                app_name = remainder[:search_pos].strip()
                query = remainder[search_pos + len(" search "):].strip()
                if not query:
                    return "Add search words after 'search'. Example: launch chrome search git"
                ok, message = launch_app(app_name, search_query=query)
                return message
            target = remainder.lower()
            urls = {
                "youtube":"https://youtube.com",
                "google":"https://google.com",
                "github":"https://github.com/sajinstalin01/Jarvis-ai",
                "jarvis github":"https://github.com/sajinstalin01/Jarvis-ai",
                "gmail":"https://mail.google.com",
                "wikipedia":"https://wikipedia.org",
            }
            if target in urls:
                webbrowser.open(urls[target])
                return f"Opening {remainder.title()} in your default browser."
            ok, message = launch_app(remainder)
            return message
        return None
    def ask_ai(self,prompt):
        groq_key=os.getenv("GROQ_API_KEY","").strip(); gemini_key=os.getenv("GEMINI_API_KEY","").strip(); error="GROQ_API_KEY not configured"
        if groq_key:
            try:
                from groq import Groq
                model=os.getenv("GROQ_MODEL","llama-3.3-70b-versatile")
                r=Groq(api_key=groq_key).chat.completions.create(model=model,messages=[{"role":"system","content":"You are JARVIS, a helpful desktop AI. Address the user as Boss. Never claim actions you did not perform."},{"role":"user","content":prompt}],temperature=.7,max_tokens=1200)
                self.events.put(("ai",f"GROQ ({model})")); return r.choices[0].message.content or "No response returned."
            except Exception as e:error=str(e)
        if gemini_key:
            try:
                from google import genai
                model=os.getenv("GEMINI_MODEL","gemini-2.5-flash")
                r=genai.Client(api_key=gemini_key).models.generate_content(model=model,contents="You are JARVIS, a helpful desktop AI. Address the user as Boss. Never claim actions you did not perform.\n"+prompt)
                self.events.put(("ai",f"GEMINI ({model})")); return r.text or "No response returned."
            except Exception as e:return f"Both AI providers failed.\nGroq: {error}\nGemini: {e}"
        self.events.put(("ai","OFFLINE"))
        return "AI isn't configured. Add GROQ_API_KEY or GEMINI_API_KEY to .env.\nGroq status: "+error
    def poll(self):
        try:
            while True:
                kind,msg=self.events.get_nowait()
                if kind=="status":self.core.configure(text="● "+msg[:22].upper(),text_color=GREEN)
                elif kind=="ai":self.ai_status.configure(text="● AI: "+msg,text_color=GREEN if msg!="OFFLINE" else MUTED)
                elif kind=="gemini_validation":
                    if msg=="VALID":
                        self.gemini_status.configure(text="● GEMINI: VALID",text_color=GREEN)
                        self.add("SYSTEM","Gemini API key validated successfully.")
                    elif msg=="INVALID":
                        self.gemini_status.configure(text="● GEMINI: INVALID KEY",text_color="#FF7070")
                        self.add("SYSTEM","Gemini API key validation failed. Check GEMINI_API_KEY in your local .env; the key itself is never displayed.")
                    elif msg=="ERROR":
                        self.gemini_status.configure(text="● GEMINI: CHECK FAILED",text_color="#FFCA71")
                        self.add("SYSTEM","Could not validate Gemini right now (network/API issue). JARVIS will retry through its normal AI fallback when you ask a question.")
                    else:
                        self.gemini_status.configure(text="● GEMINI: NOT CONFIGURED",text_color=MUTED)
                elif kind=="provider_validation":
                    status = self.groq_status if msg[0]=="GROQ" else self.gemini_status
                    label = msg[0]
                    state = msg[1]
                    color = GREEN if state=="VALID" else "#FF7070" if state=="INVALID" else "#FFCA71" if state=="ERROR" else MUTED
                    text_state = {"VALID":"VALID","INVALID":"INVALID KEY","ERROR":"CHECK FAILED","NOT_CONFIGURED":"NOT CONFIGURED"}.get(state,state)
                    status.configure(text=f"● {label}: {text_state}",text_color=color)
                    if state in ("INVALID","ERROR"):
                        self.add("SYSTEM",f"{label.title()} provider check: {text_state}. Check local settings or network; the API key is never shown.")
                elif kind=="workflow_confirmation":
                    workflow=msg
                    approved=messagebox.askyesno("Confirm JARVIS workflow",f"Run workflow '{workflow['name']}'?\n\n"+ "\n".join(workflow["steps"]) + "\n\nOnly run workflows you recognize.")
                    if approved:
                        for step in workflow["steps"]:
                            try:
                                result=self.command(step)
                                self.add("WORKFLOW",f"{step}\n{result or 'Step completed.'}")
                            except Exception as exc:self.add("WORKFLOW",f"{step} failed: {exc}")
                elif kind=="voice":
                    self.entry.delete(0,"end"); self.entry.insert(0,msg); self.send()
                elif kind=="voice_command":
                    self.entry.delete(0,"end"); self.entry.insert(0,msg); self.send()
                else:
                    self.add("J.A.R.V.I.S.",msg); self.busy=False; self.send_btn.configure(state="normal",text="TRANSMIT ➤"); self.speak(msg)
        except queue.Empty:pass
        self.after(100,self.poll)
    def start_gemini_validation(self):
        """Validate the configured Gemini key asynchronously so the GUI never freezes."""
        key = os.getenv("GEMINI_API_KEY", "").strip()
        if not key:
            self.events.put(("gemini_validation", "NOT_CONFIGURED"))
            return
        self.gemini_status.configure(text="● GEMINI: CHECKING…", text_color="#FFCA71")
        def validate():
            try:
                from google import genai
                client = genai.Client(api_key=key)
                # Listing a model sends an authenticated request without generating content.
                next(iter(client.models.list()), None)
                self.events.put(("gemini_validation", "VALID"))
            except Exception as exc:
                message = str(exc).lower()
                invalid_markers = ("api key not valid", "invalid api key", "unauthenticated", "permission_denied", "permission denied", " 400 ", " 401 ", " 403 ")
                self.events.put(("gemini_validation", "INVALID" if any(marker in message for marker in invalid_markers) else "ERROR"))
        threading.Thread(target=validate, name="GeminiKeyValidation", daemon=True).start()

    def start_groq_validation(self):
        key=os.getenv("GROQ_API_KEY","").strip()
        if not key:
            self.events.put(("provider_validation",("GROQ","NOT_CONFIGURED"))); return
        def validate():
            try:
                from groq import Groq
                client=Groq(api_key=key)
                next(iter(client.models.list()),None)
                self.events.put(("provider_validation",("GROQ","VALID")))
            except Exception as exc:
                msg=str(exc).lower()
                invalid=("invalid api key","authentication","unauthorized"," 401 "," 403 ")
                self.events.put(("provider_validation",("GROQ","INVALID" if any(x in msg for x in invalid) else "ERROR")))
        threading.Thread(target=validate,name="GroqKeyValidation",daemon=True).start()

    def toggle_wake_word(self):
        if not self.sr:
            self.add("SYSTEM","Wake-word mode requires SpeechRecognition and compatible PyAudio.")
            return
        self.wake_enabled=not self.wake_enabled
        if self.wake_enabled:
            self.wake_stop.clear()
            self.wake_btn.configure(text="WAKE: ON",fg_color="#176A51")
            self.add("SYSTEM","Wake-word listening enabled. Say 'Hey JARVIS' to activate. Audio recognition uses the configured speech service.")
            self.wake_thread=threading.Thread(target=self.wake_word_loop,name="JarvisWakeWord",daemon=True)
            self.wake_thread.start()
        else:
            self.wake_stop.set()
            self.wake_btn.configure(text="WAKE: OFF",fg_color="#12435A")
            self.add("SYSTEM","Wake-word listening disabled.")

    def wake_word_loop(self):
        recognizer=self.sr.Recognizer()
        waiting_for_command=False
        command_deadline=0.0
        while not self.wake_stop.is_set():
            try:
                with self.sr.Microphone() as source:
                    try: audio=recognizer.listen(source,timeout=2,phrase_time_limit=6)
                    except self.sr.WaitTimeoutError:
                        if waiting_for_command and time.monotonic()>command_deadline:
                            waiting_for_command=False
                            self.events.put(("status","Wake word ready"))
                        continue
                phrase=recognizer.recognize_google(audio).strip()
                lower=phrase.lower()
                if waiting_for_command:
                    self.events.put(("voice_command",phrase)); waiting_for_command=False
                    continue
                marker="hey jarvis"
                if marker in lower or lower.startswith("jarvis"):
                    index=lower.find(marker)
                    remainder=phrase[index+len(marker):].strip(" ,.!?") if index>=0 else phrase[len("jarvis"):].strip(" ,.!?")
                    if remainder:
                        self.events.put(("voice_command",remainder))
                    else:
                        waiting_for_command=True; command_deadline=time.monotonic()+10
                        self.events.put(("status","Say your command"))
            except self.sr.UnknownValueError:
                continue
            except self.sr.RequestError as exc:
                self.events.put(("status","Voice service unavailable"))
                self.events.put(("answer",f"Wake-word recognition service unavailable: {exc}"))
                time.sleep(2)
            except Exception as exc:
                if not self.wake_stop.is_set():
                    self.events.put(("answer",f"Wake-word listener stopped: {exc}"))
                    time.sleep(2)

    def refresh_telemetry(self):
        try:
            data=system_metrics()
            lines=[f"Host: {data['host']}",f"OS: {data['platform']}",f"Python: {data['python']}"]
            if "cpu_percent" in data:
                lines.extend([f"CPU: {data['cpu_percent']:.0f}%",f"RAM: {data['memory_percent']:.0f}% ({data['memory_used_gb']:.1f} GB used)",f"Disk: {data['disk_percent']:.0f}%",f"Network sent/received: {data['network_sent_mb']:.1f}/{data['network_recv_mb']:.1f} MB"])
                if data.get("battery_percent") is not None:lines.append(f"Battery: {data['battery_percent']:.0f}%")
                if data.get("temperatures_c"):lines.append("Sensors: "+", ".join(f"{v:.0f}°C" for v in data["temperatures_c"]))
            elif data.get("metrics_note"):lines.append(data["metrics_note"])
            self.telemetry.configure(text="\n".join(lines))
        except Exception as exc:
            self.telemetry.configure(text=f"Metrics unavailable: {exc}")
        if self.winfo_exists():self.after(5000,self.refresh_telemetry)

    def poll_reminders(self):
        try:
            for reminder in self.store.due_reminders():
                message=f"Reminder #{reminder['id']}: {reminder['message']}"
                self.add("REMINDER",message)
                try:
                    messagebox.showinfo("JARVIS Reminder",message)
                except Exception:pass
        except Exception as exc:self.add("SYSTEM",f"Reminder check failed: {exc}")
        if self.winfo_exists():self.after(15000,self.poll_reminders)

    def open_feature_window(self, kind):
        titles={"monitor":"Live PC Monitor","memory":"Memory & Conversation History","reminders":"Reminders","workflows":"Safe Automation Workflows","developer":"Developer Mode"}
        win=ctk.CTkToplevel(self); win.title("J.A.R.V.I.S. // "+titles.get(kind,"Tools")); win.geometry("760x620"); win.configure(fg_color=BG); win.transient(self)
        win.grid_columnconfigure(0,weight=1); win.grid_rowconfigure(1,weight=1)
        ctk.CTkLabel(win,text=titles.get(kind,"JARVIS Tools"),text_color=CYAN,font=ctk.CTkFont(size=20,weight="bold")).grid(row=0,column=0,sticky="w",padx=18,pady=14)
        output=ctk.CTkTextbox(win,fg_color="#06101B",text_color="#DDEBF5",wrap="word"); output.grid(row=1,column=0,sticky="nsew",padx=18,pady=8)
        controls=ctk.CTkFrame(win,fg_color="transparent"); controls.grid(row=2,column=0,sticky="ew",padx=18,pady=12); controls.grid_columnconfigure(0,weight=1)
        def show(text):
            output.configure(state="normal"); output.delete("1.0","end"); output.insert("end",text); output.configure(state="disabled")
        def entry(placeholder):
            field=ctk.CTkEntry(controls,placeholder_text=placeholder); field.grid(row=0,column=0,sticky="ew",padx=(0,6),pady=4); return field
        def button(label,fn):
            ctk.CTkButton(controls,text=label,command=fn,fg_color="#12435A").grid(row=1,column=0,sticky="ew",pady=4)
        if kind=="monitor":
            def refresh():
                data=system_metrics()
                show("\n".join(f"{key}: {value}" for key,value in data.items()))
            button("Refresh metrics",refresh); refresh()
        elif kind=="memory":
            field=entry("Search history or enter memory text")
            def history():
                rows=self.store.search_history(field.get(),50)
                show("\n\n".join(f"#{r['id']} [{r['created_at']}] {r['speaker']}: {r['content']}" for r in rows) or "No matching history.")
            def memories():
                rows=self.store.list_memories(field.get())
                show("\n\n".join(f"#{r['id']} [{r['created_at']}] {r['content']}" for r in rows) or "No matching memories.")
            def remember():
                try:self.store.remember(field.get()); show("Memory saved locally."); 
                except Exception as exc:show(f"Could not save memory: {exc}")
            def clear():
                if messagebox.askyesno("Clear history","Permanently delete all locally stored conversation history?"):
                    self.store.clear_history(); show("Conversation history cleared. Saved memories were kept.")
            button("Search conversation history",history)
            button("View saved memories",memories)
            button("Save text as memory",remember)
            button("Clear conversation history…",clear)
        elif kind=="reminders":
            field=entry("remind me in 10 minutes to stretch OR remind me daily to review")
            def add_reminder():
                try:
                    parsed=parse_reminder_command(field.get())
                    if not parsed:raise ValueError("Use an explicit supported reminder format.")
                    message,due,recurrence=parsed
                    rid=self.store.add_reminder(message,due,recurrence)
                    show(f"Reminder #{rid} scheduled for {due:%Y-%m-%d %H:%M %Z}.\n\n"+self.reminder_text())
                except Exception as exc:show(f"Could not schedule reminder: {exc}")
            button("Schedule reminder",add_reminder)
            button("Refresh reminder list",lambda:show(self.reminder_text()))
            button("Delete reminder by ID",lambda:self.delete_reminder_dialog(show))
            show(self.reminder_text())
        elif kind=="workflows":
            field=entry("name: launch chrome; open github")
            def save():
                try:
                    name,steps_text=field.get().split(":",1)
                    steps=[x.strip() for x in steps_text.split(";") if x.strip()]
                    self.store.save_workflow(name,steps); show(self.workflow_text())
                except Exception as exc:show(f"Could not save workflow: {exc}")
            button("Save workflow",save)
            button("List workflows",lambda:show(self.workflow_text()))
            button("Run workflow…",lambda:self.run_workflow_dialog(show))
            show(self.workflow_text())
        elif kind=="developer":
            def diagnostics():show(developer_diagnostics())
            def test():
                import py_compile
                try:
                    py_compile.compile(str(ROOT/"jarvis.py"),doraise=True); py_compile.compile(str(ROOT/"jarvis_services.py"),doraise=True)
                    show("Syntax checks passed for jarvis.py and jarvis_services.py.\n\n"+developer_diagnostics())
                except Exception as exc:show(f"Syntax check failed: {exc}")
            button("Run project diagnostics",diagnostics)
            button("Run Python syntax checks",test)
            button("Show Git status and latest commit",diagnostics)
            diagnostics()

    def reminder_text(self):
        rows=self.store.list_reminders()
        return "\n".join(f"#{r['id']} — {r['due_at']} [{r['recurrence']}] — {r['message']}" for r in rows) or "No active reminders."

    def delete_reminder_dialog(self, show):
        dialog=ctk.CTkInputDialog(text="Reminder ID to delete:",title="Delete reminder")
        value=dialog.get_input()
        if value:
            try:show("Reminder deleted." if self.store.delete_reminder(int(value)) else "Reminder ID not found.")
            except ValueError:show("Enter a numeric reminder ID.")

    def workflow_text(self):
        rows=self.store.list_workflows()
        return "\n".join(f"{r['name']}: {'; '.join(r['steps'])}" for r in rows) or "No saved workflows."

    def run_workflow_dialog(self, show):
        workflows=self.store.list_workflows()
        if not workflows:
            show("No saved workflows."); return
        names=[w["name"] for w in workflows]
        dialog=ctk.CTkInputDialog(text="Enter workflow name to run:\n"+", ".join(names),title="Run workflow")
        name=dialog.get_input()
        if name:
            workflow=self.store.get_workflow(name)
            if workflow:self.events.put(("workflow_confirmation",workflow))
            else:show("Workflow not found.")

    def start_gemini_validation(self):
        """Validate the configured Gemini key asynchronously so the GUI never freezes."""
        key = os.getenv("GEMINI_API_KEY", "").strip()
        if not key:
            self.events.put(("provider_validation",("GEMINI","NOT_CONFIGURED")))
            return
        def validate():
            try:
                from google import genai
                client = genai.Client(api_key=key)
                next(iter(client.models.list()), None)
                self.events.put(("provider_validation",("GEMINI","VALID")))
            except Exception as exc:
                message = str(exc).lower()
                invalid_markers = ("api key not valid", "invalid api key", "unauthenticated", "permission_denied", "permission denied", " 400 ", " 401 ", " 403 ")
                state="INVALID" if any(marker in message for marker in invalid_markers) else "ERROR"
                self.events.put(("provider_validation",("GEMINI",state)))
        threading.Thread(target=validate, name="GeminiKeyValidation", daemon=True).start()

    def system_status(self):
        self.core.configure(text="● OPERATIONAL",text_color=GREEN)
        configured=bool(os.getenv("GROQ_API_KEY") or os.getenv("GEMINI_API_KEY"))
        self.ai_status.configure(text="● AI: KEY CONFIGURED" if configured else "● AI: NOT CONFIGURED",text_color=GREEN if configured else MUTED)
    def open_url(self,url):
        webbrowser.open(url); self.add("J.A.R.V.I.S.",f"Opening {url}")
    def launch_shortcut(self, name):
        ok, message = launch_app(name)
        self.add("APP LAUNCHER", message if ok else "⚠ " + message)
    def show_tools(self):
        self.add("TOOLS","Try time, date, system info, calculate <expression>, search <query>, open <app or website>, launch <app>, or launch chrome search git. WhatsApp opens the installed desktop app only; WhatsApp Web search/message helpers are disabled. Arbitrary shell commands are disabled.")
    def show_settings(self):
        self.add("SETTINGS","Configure GROQ_API_KEY, GROQ_MODEL, GEMINI_API_KEY, GEMINI_MODEL and JARVIS_SPEAK_RESPONSES in your local .env. Restart after changing settings.")

if __name__ == "__main__":
    JarvisApp().mainloop()
