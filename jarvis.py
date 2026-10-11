"""JARVIS AI desktop assistant — Python + customtkinter UI."""
from __future__ import annotations
import os, threading, queue, datetime, platform, socket, webbrowser, ast, operator, urllib.parse
from pathlib import Path

try:
    import customtkinter as ctk
except ImportError as exc:
    raise SystemExit("Install dependencies first: pip install -r requirements.txt") from exc

APP_DIR = Path(__file__).resolve().parent
ENV_FILE = APP_DIR / ".env"
def load_env():
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line=line.strip()
            if line and not line.startswith("#") and "=" in line:
                k,v=line.split("=",1)
                os.environ.setdefault(k.strip(),v.strip().strip('"').strip("'"))
load_env()

CYAN="#00D9FF"; BG="#07111F"; PANEL="#0B1B2C"; MUTED="#8196AD"; GREEN="#4DFFB5"

class JarvisApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark"); ctk.set_default_color_theme("blue")
        self.title("J.A.R.V.I.S. | AI Desktop System")
        self.geometry("1320x820"); self.minsize(1000,680); self.configure(fg_color=BG)
        self.events=queue.Queue(); self.busy=False
        self._build_ui(); self._clock_tick(); self.after(100,self._poll_events)
        self._system_status(); self._welcome()

    def _build_ui(self):
        self.grid_columnconfigure(1,weight=1); self.grid_rowconfigure(0,weight=1)
        side=ctk.CTkFrame(self,width=220,corner_radius=0,fg_color="#081522",border_width=1,border_color="#12334A")
        side.grid(row=0,column=0,sticky="nsew"); side.grid_propagate(False)
        ctk.CTkLabel(side,text="J.A.R.V.I.S.",font=ctk.CTkFont(size=25,weight="bold"),text_color=CYAN).pack(padx=18,pady=(28,0),anchor="w")
        ctk.CTkLabel(side,text="PERSONAL AI INTERFACE",font=ctk.CTkFont(size=10,weight="bold"),text_color=MUTED).pack(padx=20,pady=(2,24),anchor="w")
        for title,fn in [("◈   Dashboard",self._show_dashboard),("✧   AI Assistant",self._focus_chat),("⌘   System Tools",self._show_tools),("⚙   Settings",self._show_settings)]:
            ctk.CTkButton(side,text=title,command=fn,anchor="w",height=42,corner_radius=10,fg_color="transparent",hover_color="#12314A",text_color="#D7E8F4").pack(fill="x",padx=12,pady=4)
        ctk.CTkFrame(side,height=1,fg_color="#17364B").pack(fill="x",padx=14,pady=(24,14))
        ctk.CTkLabel(side,text="CORE STATUS",font=ctk.CTkFont(size=11,weight="bold"),text_color=MUTED).pack(anchor="w",padx=18)
        self.core_label=ctk.CTkLabel(side,text="●  INITIALIZING",text_color="#FFCA71",font=ctk.CTkFont(size=12,weight="bold")); self.core_label.pack(anchor="w",padx=18,pady=(8,4))
        self.ai_label=ctk.CTkLabel(side,text="●  AI: NOT CONFIGURED",text_color=MUTED,font=ctk.CTkFont(size=12)); self.ai_label.pack(anchor="w",padx=18,pady=4)
        ctk.CTkLabel(side,text="LOCAL-FIRST CONTROLS\nActions ask before launch.",justify="left",text_color="#55748A",font=ctk.CTkFont(size=10)).pack(side="bottom",anchor="w",padx=18,pady=20)

        main=ctk.CTkFrame(self,fg_color=BG,corner_radius=0); main.grid(row=0,column=1,sticky="nsew",padx=18,pady=16)
        main.grid_columnconfigure(0,weight=1); main.grid_rowconfigure(1,weight=1)
        header=ctk.CTkFrame(main,fg_color="transparent"); header.grid(row=0,column=0,sticky="ew",pady=(0,14))
        ctk.CTkLabel(header,text="STARK INDUSTRIES  /  PERSONAL ASSISTANT",text_color=MUTED,font=ctk.CTkFont(size=11,weight="bold")).pack(side="left")
        self.clock=ctk.CTkLabel(header,text="--:--:--",text_color=CYAN,font=ctk.CTkFont(size=18,weight="bold")); self.clock.pack(side="right",padx=8)
        self.date=ctk.CTkLabel(header,text="",text_color=MUTED,font=ctk.CTkFont(size=11)); self.date.pack(side="right",padx=10)

        content=ctk.CTkFrame(main,fg_color="transparent"); content.grid(row=1,column=0,sticky="nsew")
        content.grid_columnconfigure(0,weight=2); content.grid_columnconfigure(1,weight=1); content.grid_rowconfigure(1,weight=1)
        hero=ctk.CTkFrame(content,fg_color=PANEL,border_width=1,border_color="#15415A",corner_radius=18)
        hero.grid(row=0,column=0,columnspan=2,sticky="ew",pady=(0,14)); hero.grid_columnconfigure(1,weight=1)
        self.arc=ctk.CTkCanvas(hero,width=140,height=140,bg=PANEL,highlightthickness=0); self.arc.grid(row=0,column=0,padx=(18,6),pady=12); self._draw_reactor()
        hero_text=ctk.CTkFrame(hero,fg_color="transparent"); hero_text.grid(row=0,column=1,sticky="w",padx=18,pady=20)
        ctk.CTkLabel(hero_text,text="GOOD TO SEE YOU, BOSS.",text_color="#EEF8FF",font=ctk.CTkFont(size=25,weight="bold")).pack(anchor="w")
        ctk.CTkLabel(hero_text,text="Your desktop intelligence interface is ready.",text_color=MUTED,font=ctk.CTkFont(size=13)).pack(anchor="w",pady=(5,12))
        ctk.CTkLabel(hero_text,text="● SYSTEM NOMINAL",text_color=GREEN,fg_color="#10352F",corner_radius=8,font=ctk.CTkFont(size=11,weight="bold"),padx=12,pady=6).pack(anchor="w")

        chat=ctk.CTkFrame(content,fg_color=PANEL,border_width=1,border_color="#14334B",corner_radius=16)
        chat.grid(row=1,column=0,sticky="nsew",padx=(0,12)); chat.grid_columnconfigure(0,weight=1); chat.grid_rowconfigure(1,weight=1)
        chathead=ctk.CTkFrame(chat,fg_color="transparent"); chathead.grid(row=0,column=0,sticky="ew",padx=16,pady=(13,5))
        ctk.CTkLabel(chathead,text="✧  JARVIS CONSOLE",text_color=CYAN,font=ctk.CTkFont(size=14,weight="bold")).pack(side="left")
        ctk.CTkButton(chathead,text="CLEAR",width=60,height=26,fg_color="#10263A",hover_color="#193C55",command=self._clear_chat,font=ctk.CTkFont(size=10)).pack(side="right")
        self.chatbox=ctk.CTkTextbox(chat,fg_color="#06101B",text_color="#DDEBF5",border_width=1,border_color="#133047",corner_radius=10,wrap="word",font=ctk.CTkFont(size=13))
        self.chatbox.grid(row=1,column=0,sticky="nsew",padx=14,pady=8); self.chatbox.configure(state="disabled")
        inputrow=ctk.CTkFrame(chat,fg_color="transparent"); inputrow.grid(row=2,column=0,sticky="ew",padx=14,pady=(4,14)); inputrow.grid_columnconfigure(0,weight=1)
        self.entry=ctk.CTkEntry(inputrow,placeholder_text="Ask JARVIS something…",height=42,fg_color="#0A1826",border_color="#1C4963")
        self.entry.grid(row=0,column=0,sticky="ew",padx=(0,8)); self.entry.bind("<Return>",lambda e:self._send())
        self.send_btn=ctk.CTkButton(inputrow,text="TRANSMIT  ➤",width=125,height=42,fg_color="#007F9F",hover_color="#009FC4",command=self._send); self.send_btn.grid(row=0,column=1)

        right=ctk.CTkFrame(content,fg_color="transparent"); right.grid(row=1,column=1,sticky="nsew"); right.grid_columnconfigure(0,weight=1)
        syscard=ctk.CTkFrame(right,fg_color=PANEL,border_width=1,border_color="#14334B",corner_radius=16); syscard.grid(row=0,column=0,sticky="ew",pady=(0,12))
        ctk.CTkLabel(syscard,text="SYSTEM TELEMETRY",text_color=CYAN,font=ctk.CTkFont(size=13,weight="bold")).pack(anchor="w",padx=16,pady=(15,10))
        self.telemetry=ctk.CTkLabel(syscard,text="Loading…",justify="left",text_color="#B4C9D8",font=ctk.CTkFont(size=12)); self.telemetry.pack(anchor="w",padx=16,pady=(0,16))
        actions=ctk.CTkFrame(right,fg_color=PANEL,border_width=1,border_color="#14334B",corner_radius=16); actions.grid(row=1,column=0,sticky="ew"); actions.grid_columnconfigure((0,1),weight=1)
        ctk.CTkLabel(actions,text="QUICK ACTIONS",text_color=CYAN,font=ctk.CTkFont(size=13,weight="bold")).grid(row=0,column=0,columnspan=2,sticky="w",padx=16,pady=(15,9))
        for i,(label,url) in enumerate([("Open YouTube","https://youtube.com"),("Open Google","https://google.com"),("Open GitHub","https://github.com/sajinstalin01/Jarvis-ai"),("Open Gmail","https://mail.google.com")]):
            ctk.CTkButton(actions,text=label,command=lambda u=url:self._open_url(u),height=36,fg_color="#10283B",hover_color="#19425A",anchor="w").grid(row=1+i//2,column=i%2,sticky="ew",padx=7,pady=5)
        ctk.CTkLabel(actions,text="Browser shortcuts open in your default browser.",text_color="#5F7B90",font=ctk.CTkFont(size=10)).grid(row=3,column=0,columnspan=2,padx=12,pady=(8,13),sticky="w")
        ctk.CTkLabel(main,text="JARVIS // PERSONAL DESKTOP AI  •  PYTHON EDITION  •  v1.0",text_color="#456176",font=ctk.CTkFont(size=10)).grid(row=2,column=0,sticky="ew",pady=(10,0))

    def _draw_reactor(self):
        import math
        c=self.arc
        c.create_oval(12,12,128,128,outline="#12415A",width=2); c.create_oval(22,22,118,118,outline=CYAN,width=2)
        c.create_oval(32,32,108,108,outline="#0785A8",width=1); c.create_oval(43,43,97,97,fill="#063247",outline=CYAN,width=2)
        c.create_oval(52,52,88,88,fill="#00A6D5",outline="#A6F4FF",width=2); c.create_oval(62,62,78,78,fill="#D3FCFF",outline="")
        for a in range(0,360,45):
            x1=70+48*math.cos(math.radians(a)); y1=70+48*math.sin(math.radians(a))
            x2=70+56*math.cos(math.radians(a)); y2=70+56*math.sin(math.radians(a))
            c.create_line(x1,y1,x2,y2,fill=CYAN,width=2)

    def _clock_tick(self):
        now=datetime.datetime.now(); self.clock.configure(text=now.strftime("%H:%M:%S")); self.date.configure(text=now.strftime("%a, %d %b %Y")); self.after(1000,self._clock_tick)
    def _append(self,speaker,message):
        self.chatbox.configure(state="normal"); self.chatbox.insert("end",f"[{datetime.datetime.now():%H:%M:%S}]  {speaker}\n{message}\n\n"); self.chatbox.see("end"); self.chatbox.configure(state="disabled")
    def _welcome(self):
        self._append("J.A.R.V.I.S.","Systems online. I am ready, Boss.\nTry: help, time, date, system info, open YouTube, open GitHub, or ask a question after configuring an AI provider.")
    def _clear_chat(self):
        self.chatbox.configure(state="normal"); self.chatbox.delete("1.0","end"); self.chatbox.configure(state="disabled")
    def _send(self):
        if self.busy:return
        prompt=self.entry.get().strip()
        if not prompt:return
        self.entry.delete(0,"end"); self._append("BOSS",prompt); self.busy=True; self.send_btn.configure(state="disabled",text="PROCESSING…")
        threading.Thread(target=self._process_prompt,args=(prompt,),daemon=True).start()
    def _process_prompt(self,prompt):
        try:
            answer=self._local_command(prompt)
            if answer is None:answer=self._ask_ai(prompt)
        except Exception as exc:answer=f"An error occurred: {exc}\nCheck .env, settings, and installed packages."
        self.events.put(answer)
    def _local_command(self,prompt):
        p=prompt.strip().lower()
        if p in {"help","commands","what can you do"}:
            return ("Available commands:\n• help, time, date, system info\n• open YouTube, Google, GitHub, Gmail, Wikipedia\n• search <query> — opens a browser search\n• calculate <math expression> — safe arithmetic\n• ask a question — sends it to the configured AI provider\n\nAdd GEMINI_API_KEY or GROQ_API_KEY to your local .env file for AI chat.")
        if p in {"hi","hello","hey","hello jarvis","hi jarvis"}:return "Hello, Boss. All primary systems are standing by. What shall we work on?"
        if p in {"time","what time is it"} or "what time" in p:return "Local time: "+datetime.datetime.now().strftime("%I:%M:%S %p")
        if p in {"date","what is today's date","today's date"} or "what date" in p:return "Today is "+datetime.datetime.now().strftime("%A, %d %B %Y")
        if p in {"system info","computer info","system status"}:return self._system_text()
        if p.startswith("open "):
            target=p[5:].strip()
            urls={"youtube":"https://youtube.com","google":"https://google.com","github":"https://github.com","jarvis github":"https://github.com/sajinstalin01/Jarvis-ai","gmail":"https://mail.google.com","wikipedia":"https://wikipedia.org"}
            if target in urls:
                self.after(0,lambda u=urls[target]:webbrowser.open(u)); return f"Opening {target.title()} in your default browser."
            return "For safety, supported shortcuts are YouTube, Google, GitHub, Gmail, and Wikipedia."
        if p.startswith("search "):
            query=prompt[7:].strip()
            if query:
                self.after(0,lambda q=query:webbrowser.open("https://www.google.com/search?q="+urllib.parse.quote(q)))
                return f"Searching the web for: {query}"
        if p.startswith("calculate "):
            expr=prompt[10:].strip()
            ops={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv,ast.Pow:operator.pow,ast.Mod:operator.mod,ast.USub:operator.neg,ast.UAdd:operator.pos,ast.FloorDiv:operator.floordiv}
            def ev(n):
                if isinstance(n,ast.Expression):return ev(n.body)
                if isinstance(n,ast.Constant) and type(n.value) in (int,float):return n.value
                if isinstance(n,ast.BinOp) and type(n.op) in ops:
                    if isinstance(n.op,ast.Pow) and abs(ev(n.right))>10:raise ValueError("Exponent too large")
                    return ops[type(n.op)](ev(n.left),ev(n.right))
                if isinstance(n,ast.UnaryOp) and type(n.op) in ops:return ops[type(n.op)](ev(n.operand))
                raise ValueError("Use numbers and basic operators only")
            try:
                result=ev(ast.parse(expr,mode="eval"))
                if abs(float(result))>1e100:return "That result is too large to display."
                return f"Calculation result: {result}"
            except Exception as exc:return f"I couldn't calculate that: {exc}"
        return None
    def _ask_ai(self,prompt):
        groq_key=os.getenv("GROQ_API_KEY","").strip(); gemini_key=os.getenv("GEMINI_API_KEY","").strip()
        groq_error="GROQ_API_KEY not configured"
        if groq_key:
            try:
                from groq import Groq
                client=Groq(api_key=groq_key)
                model=os.getenv("GROQ_MODEL","llama-3.3-70b-versatile")
                response=client.chat.completions.create(model=model,messages=[{"role":"system","content":"You are JARVIS, a helpful and clear desktop AI assistant. Address the user as Boss. Never claim you performed actions you did not perform."},{"role":"user","content":prompt}],temperature=0.7,max_tokens=1200)
                self.after(0,lambda m=model:self.ai_label.configure(text=f"●  AI: GROQ ({m})",text_color=GREEN))
                return response.choices[0].message.content or "I couldn't generate a response."
            except Exception as exc:groq_error=str(exc)
        if gemini_key:
            try:
                from google import genai
                client=genai.Client(api_key=gemini_key); model=os.getenv("GEMINI_MODEL","gemini-2.5-flash")
                response=client.models.generate_content(model=model,contents=f"You are JARVIS, a helpful desktop AI assistant. Address the user as Boss. Never claim you performed actions you did not perform.\n\nUser: {prompt}")
                self.after(0,lambda m=model:self.ai_label.configure(text=f"●  AI: GEMINI ({m})",text_color=GREEN))
                return response.text or "I couldn't generate a response."
            except Exception as exc:return f"Both AI providers failed.\nGroq: {groq_error}\nGemini: {exc}\n\nCheck API keys, model names, internet connection, and installed packages."
        self.after(0,lambda:self.ai_label.configure(text="●  AI: OFFLINE",text_color=MUTED))
        return "AI provider not configured. Local commands work without an API key.\n\nCopy .env.example to .env and add a Groq or Gemini API key. Restart the app after editing it.\nGroq: "+groq_error
    def _poll_events(self):
        try:
            while True:
                message=self.events.get_nowait(); self._append("J.A.R.V.I.S.",message); self.busy=False; self.send_btn.configure(state="normal",text="TRANSMIT  ➤")
        except queue.Empty:pass
        self.after(100,self._poll_events)
    def _system_text(self):
        return f"Host: {socket.gethostname()}\nOS: {platform.system()} {platform.release()}\nPython: {platform.python_version()}\nArchitecture: {platform.machine()}\nProcessor: {platform.processor() or 'Not reported'}"
    def _system_status(self):
        self.telemetry.configure(text=self._system_text()); self.core_label.configure(text="●  OPERATIONAL",text_color=GREEN)
    def _open_url(self,url):
        webbrowser.open(url); self._append("J.A.R.V.I.S.",f"Opening {url}")
    def _focus_chat(self):self.entry.focus_set()
    def _show_dashboard(self):self._append("J.A.R.V.I.S.","Dashboard online. Use the console for requests.")
    def _show_tools(self):self._append("J.A.R.V.I.S.","Tools: time, date, system info, calculate <expression>, search <query>, and browser shortcuts. Destructive system commands are intentionally disabled.")
    def _show_settings(self):self._append("J.A.R.V.I.S.","Configure AI in the local .env file: GROQ_API_KEY, GROQ_MODEL, GEMINI_API_KEY, GEMINI_MODEL. Restart after editing.")

if __name__=="__main__":
    JarvisApp().mainloop()
