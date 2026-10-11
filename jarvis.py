"""Unified J.A.R.V.I.S. desktop assistant: original dashboard + V2 voice/app/WhatsApp features."""
from __future__ import annotations
import ast, datetime, operator, os, platform, queue, shutil, socket, subprocess, threading, urllib.parse, webbrowser
from pathlib import Path
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

APP_ALIASES = {"notepad":"notepad.exe", "calculator":"calc.exe", "paint":"mspaint.exe",
 "file explorer":"explorer.exe", "task manager":"taskmgr.exe", "chrome":"chrome",
 "edge":"msedge", "firefox":"firefox", "vscode":"code", "visual studio code":"code"}
def launch_app(name):
    key = name.strip().lower()
    if key == "settings" and platform.system() == "Windows":
        try: os.startfile("ms-settings:"); return True, "Opening Windows Settings."
        except Exception as e: return False, str(e)
    if key == "whatsapp":
        webbrowser.open("https://web.whatsapp.com/"); return True, "Opening WhatsApp Web."
    target = APP_ALIASES.get(key)
    if not target: return False, "App isn't in JARVIS's safe launch list."
    try:
        if platform.system() == "Windows":
            subprocess.Popen(["cmd", "/c", "start", "", target], shell=False)
        elif platform.system() == "Darwin":
            aliases = {"notepad":"TextEdit", "calculator":"Calculator", "paint":"Preview",
                       "file explorer":"Finder", "task manager":"Activity Monitor", "vscode":"Visual Studio Code"}
            subprocess.Popen(["open", "-a", aliases.get(key, target)])
        else:
            aliases = {"notepad":"gedit", "calculator":"gnome-calculator", "paint":"pinta",
                       "file explorer":"xdg-open", "task manager":"gnome-system-monitor"}
            cmd = aliases.get(key, target)
            if not shutil.which(cmd): return False, f"{cmd} was not found."
            subprocess.Popen([cmd, str(Path.home())] if key == "file explorer" else [cmd])
        return True, f"Launching {name}."
    except Exception as e: return False, f"Couldn't launch {name}: {e}"

def web_search(query):
    webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote(query))
def whatsapp_open():
    webbrowser.open("https://web.whatsapp.com/")
    return "WhatsApp Web opened. Sign in if needed, then find the exact contact."
def whatsapp_search(name):
    name = name.strip()
    if not name: return "Usage: whatsapp search <contact name>"
    webbrowser.open("https://web.whatsapp.com/")
    return f"WhatsApp Web opened. Search for '{name}' inside WhatsApp and verify the person. Private contacts are not read."
def whatsapp_message(contact, message):
    if not contact.strip() or not message.strip(): return "Format: whatsapp message <contact> | <message>"
    return f"Draft for {contact.strip()} (NOT SENT):\n\n{message.strip()}\n\nSelect and verify the contact in WhatsApp, then send manually."

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
        self.title("J.A.R.V.I.S. // Unified Stark Desktop"); self.geometry("1320x830"); self.minsize(980,670); self.configure(fg_color=BG)
        self.events=queue.Queue(); self.busy=False; self.sound=True; self.sr=None; self.tts=None
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
        self.add("J.A.R.V.I.S.","All core systems online, Boss. Type 'help' to see commands.")

    def build_ui(self):
        side=ctk.CTkFrame(self,width=220,corner_radius=0,fg_color="#081522",border_width=1,border_color="#12334A")
        side.grid(row=0,column=0,sticky="nsew"); side.grid_propagate(False)
        ctk.CTkLabel(side,text="J.A.R.V.I.S.",font=ctk.CTkFont(size=26,weight="bold"),text_color=CYAN).pack(anchor="w",padx=18,pady=(26,2))
        ctk.CTkLabel(side,text="PERSONAL AI INTERFACE",font=ctk.CTkFont(size=10,weight="bold"),text_color=MUTED).pack(anchor="w",padx=20,pady=(0,24))
        for label,fn in [("◈  Dashboard",lambda:self.add("SYSTEM","Dashboard online.")),("✧  AI Assistant",lambda:self.entry.focus_set()),("⌘  System Tools",self.show_tools),("◉  WhatsApp",lambda:self.add("WHATSAPP","Try whatsapp search <name> or whatsapp message <name> | <text>")),("⚙  Settings",self.show_settings)]:
            ctk.CTkButton(side,text=label,command=fn,anchor="w",height=42,corner_radius=10,fg_color="transparent",hover_color="#12314A",text_color="#D7E8F4").pack(fill="x",padx=12,pady=4)
        ctk.CTkFrame(side,height=1,fg_color="#17364B").pack(fill="x",padx=14,pady=(20,14))
        ctk.CTkLabel(side,text="CORE STATUS",font=ctk.CTkFont(size=11,weight="bold"),text_color=MUTED).pack(anchor="w",padx=18)
        self.core=ctk.CTkLabel(side,text="● INITIALIZING",text_color="#FFCA71"); self.core.pack(anchor="w",padx=18,pady=(8,4))
        self.ai_status=ctk.CTkLabel(side,text="● AI: CHECKING",text_color=MUTED); self.ai_status.pack(anchor="w",padx=18,pady=4)
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
        self.sound_btn=ctk.CTkButton(bar,text="♪ SOUND ON",width=96,height=42,command=self.toggle_sound,fg_color="#12435A"); self.sound_btn.grid(row=0,column=2,padx=3)
        self.send_btn=ctk.CTkButton(bar,text="TRANSMIT ➤",width=120,height=42,command=self.send,fg_color="#007F9F",hover_color="#009FC4"); self.send_btn.grid(row=0,column=3,padx=(3,0))
        right=ctk.CTkFrame(body,fg_color="transparent"); right.grid(row=1,column=1,sticky="nsew"); right.grid_columnconfigure(0,weight=1)
        tele=ctk.CTkFrame(right,fg_color=PANEL,border_width=1,border_color="#14334B",corner_radius=16); tele.grid(row=0,column=0,sticky="ew",pady=(0,12))
        ctk.CTkLabel(tele,text="SYSTEM TELEMETRY",text_color=CYAN,font=ctk.CTkFont(size=13,weight="bold")).pack(anchor="w",padx=16,pady=(15,10))
        self.telemetry=ctk.CTkLabel(tele,text="Loading…",justify="left",text_color="#B4C9D8",font=ctk.CTkFont(size=12)); self.telemetry.pack(anchor="w",padx=16,pady=(0,16))
        actions=ctk.CTkFrame(right,fg_color=PANEL,border_width=1,border_color="#14334B",corner_radius=16); actions.grid(row=1,column=0,sticky="ew"); actions.grid_columnconfigure((0,1),weight=1)
        ctk.CTkLabel(actions,text="QUICK ACTIONS",text_color=CYAN,font=ctk.CTkFont(size=13,weight="bold")).grid(row=0,column=0,columnspan=2,sticky="w",padx=16,pady=(15,9))
        for i,(label,url) in enumerate([("Open YouTube","https://youtube.com"),("Open Google","https://google.com"),("Open GitHub","https://github.com/sajinstalin01/Jarvis-ai"),("Open Gmail","https://mail.google.com")]):
            ctk.CTkButton(actions,text=label,height=36,fg_color="#10283B",hover_color="#19425A",anchor="w",command=lambda u=url:self.open_url(u)).grid(row=1+i//2,column=i%2,sticky="ew",padx=7,pady=5)
        ctk.CTkLabel(actions,text="Browser shortcuts use your default browser.",text_color="#5F7B90",font=ctk.CTkFont(size=10)).grid(row=3,column=0,columnspan=2,padx=12,pady=(8,13),sticky="w")
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
            return ("Commands:\n• help, time, date, system info\n• calculate <math expression>\n• search <query>; open YouTube/Google/GitHub/Gmail/Wikipedia\n• launch notepad/calculator/paint/file explorer/task manager/chrome/edge/firefox/vscode\n• open whatsapp; whatsapp search <contact>\n• whatsapp message <contact> | <message> (draft only)\n• ask a question for Groq/Gemini AI\n\nConfigure GROQ_API_KEY or GEMINI_API_KEY in .env for AI chat.")
        if p in ("hi","hello","hey","hello jarvis","hi jarvis"):return "Hello, Boss. All primary systems are standing by."
        if p=="time" or "what time" in p:return "Local time: "+datetime.datetime.now().strftime("%I:%M:%S %p")
        if p in ("date","today's date","what is today's date") or "what date" in p:return "Today is "+datetime.datetime.now().strftime("%A, %d %B %Y")
        if p in ("system info","computer info","system status"):
            return f"Host: {socket.gethostname()}\nOS: {platform.platform()}\nPython: {platform.python_version()}\nArchitecture: {platform.machine()}\nProcessor: {platform.processor() or 'Not reported'}"
        if p in ("open whatsapp","whatsapp"):return whatsapp_open()
        if p.startswith("whatsapp search "):return whatsapp_search(text[len("whatsapp search "):])
        if p.startswith("whatsapp message "):
            payload=text[len("whatsapp message "):]
            if "|" not in payload:return "Format: whatsapp message <contact> | <message>"
            contact,msg=payload.split("|",1); return whatsapp_message(contact,msg)
        if p.startswith("launch "):return launch_app(text[7:].strip())[1]
        if p.startswith("search "):
            q=text[7:].strip()
            if not q:return "Enter a query after 'search'."
            web_search(q); return "Opened a browser search for: "+q
        if p.startswith("calculate "):return safe_calculate(text[10:].strip())
        if p.startswith("open "):
            target=p[5:].strip()
            urls={"youtube":"https://youtube.com","google":"https://google.com","github":"https://github.com/sajinstalin01/Jarvis-ai","jarvis github":"https://github.com/sajinstalin01/Jarvis-ai","gmail":"https://mail.google.com","wikipedia":"https://wikipedia.org"}
            if target in urls:webbrowser.open(urls[target]); return f"Opening {target.title()} in your default browser."
            return "Unknown shortcut. Try YouTube, Google, GitHub, Gmail, or Wikipedia."
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
                elif kind=="voice":
                    self.entry.delete(0,"end"); self.entry.insert(0,msg); self.send()
                else:
                    self.add("J.A.R.V.I.S.",msg); self.busy=False; self.send_btn.configure(state="normal",text="TRANSMIT ➤"); self.speak(msg)
        except queue.Empty:pass
        self.after(100,self.poll)
    def system_status(self):
        self.telemetry.configure(text=f"Host: {socket.gethostname()}\nOS: {platform.platform()}\nPython: {platform.python_version()}\nArchitecture: {platform.machine()}\nProcessor: {platform.processor() or 'Unknown'}")
        self.core.configure(text="● OPERATIONAL",text_color=GREEN)
        configured=bool(os.getenv("GROQ_API_KEY") or os.getenv("GEMINI_API_KEY"))
        self.ai_status.configure(text="● AI: KEY CONFIGURED" if configured else "● AI: NOT CONFIGURED",text_color=GREEN if configured else MUTED)
    def open_url(self,url):
        webbrowser.open(url); self.add("J.A.R.V.I.S.",f"Opening {url}")
    def show_tools(self):
        self.add("TOOLS","Try time, date, system info, calculate <expression>, search <query>, launch <app>, or WhatsApp helper commands. Arbitrary shell commands are disabled.")
    def show_settings(self):
        self.add("SETTINGS","Configure GROQ_API_KEY, GROQ_MODEL, GEMINI_API_KEY, GEMINI_MODEL and JARVIS_SPEAK_RESPONSES in your local .env. Restart after changing settings.")

if __name__ == "__main__":
    JarvisApp().mainloop()
