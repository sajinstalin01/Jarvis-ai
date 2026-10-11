"""JARVIS V2: animated desktop AI, voice controls, safe app launcher, WhatsApp helper."""
import os, threading, queue, datetime, platform, socket, webbrowser, urllib.parse
from pathlib import Path
import customtkinter as ctk
from app_control import launch_app, web_search
from whatsapp_control import open_whatsapp, search_contact, prepare_message
from voice_control import VoiceController

ROOT=Path(__file__).resolve().parent
for line in (ROOT/".env").read_text(encoding="utf-8").splitlines() if (ROOT/".env").exists() else []:
    line=line.strip()
    if line and not line.startswith("#") and "=" in line:
        k,v=line.split("=",1); os.environ.setdefault(k.strip(),v.strip().strip('"').strip("'"))
CYAN="#00D9FF"; BG="#07111F"; PANEL="#0B1B2C"; GREEN="#4DFFB5"; MUTED="#8196AD"

class JarvisV2(ctk.CTk):
    def __init__(self):
        super().__init__(); ctk.set_appearance_mode("dark"); ctk.set_default_color_theme("blue")
        self.title("J.A.R.V.I.S. // Stark Desktop"); self.geometry("1240x790"); self.minsize(960,650); self.configure(fg_color=BG)
        self.events=queue.Queue(); self.busy=False; self.sound=True
        self.voice=VoiceController(self.voice_result,lambda s:self.events.put(("status",s)))
        self.grid_columnconfigure(1,weight=1); self.grid_rowconfigure(0,weight=1)
        self.build(); self.clock_tick(); self.after(100,self.poll); self.splash(); self.animate()
        self.add("J.A.R.V.I.S.","Systems online, Boss. Try 'help' to see commands.")
    def build(self):
        side=ctk.CTkFrame(self,width=210,corner_radius=0,fg_color="#081522"); side.grid(row=0,column=0,sticky="ns"); side.grid_propagate(False)
        ctk.CTkLabel(side,text="J.A.R.V.I.S.",font=ctk.CTkFont(size=26,weight="bold"),text_color=CYAN).pack(anchor="w",padx=18,pady=(26,2))
        ctk.CTkLabel(side,text="PERSONAL AI SYSTEM",font=ctk.CTkFont(size=10),text_color=MUTED).pack(anchor="w",padx=20,pady=(0,25))
        for name,fn in [("⌂  Dashboard",lambda:self.add("SYSTEM","Dashboard online.")),("✧  AI Console",lambda:self.entry.focus_set()),("⌘  System Tools",lambda:self.add("TOOLS","Try: launch notepad, launch calculator, system info, search <query>.")),("◉  WhatsApp",lambda:self.add("WHATSAPP","Try: whatsapp search contact name, or whatsapp message Name | text."))]:
            ctk.CTkButton(side,text=name,command=fn,anchor="w",height=42,fg_color="transparent",hover_color="#12314A").pack(fill="x",padx=12,pady=4)
        self.core=ctk.CTkLabel(side,text="● SYSTEM ONLINE",text_color=GREEN,font=ctk.CTkFont(size=12,weight="bold")); self.core.pack(anchor="w",padx=18,pady=(24,8))
        ctk.CTkLabel(side,text="VOICE + DESKTOP CONTROLS\nAllow-listed apps only.\nWhatsApp send stays manual.",justify="left",text_color=MUTED,font=ctk.CTkFont(size=10)).pack(side="bottom",anchor="w",padx=18,pady=20)
        main=ctk.CTkFrame(self,fg_color=BG,corner_radius=0); main.grid(row=0,column=1,sticky="nsew",padx=18,pady=16); main.grid_columnconfigure(0,weight=1); main.grid_rowconfigure(1,weight=1)
        head=ctk.CTkFrame(main,fg_color="transparent"); head.grid(row=0,column=0,sticky="ew",pady=(0,12))
        ctk.CTkLabel(head,text="STARK INDUSTRIES  /  INTELLIGENCE INTERFACE",text_color=MUTED,font=ctk.CTkFont(size=11,weight="bold")).pack(side="left")
        self.clock=ctk.CTkLabel(head,text="",text_color=CYAN,font=ctk.CTkFont(size=17,weight="bold")); self.clock.pack(side="right")
        hero=ctk.CTkFrame(main,fg_color=PANEL,border_width=1,border_color="#15415A",corner_radius=18); hero.grid(row=1,column=0,sticky="nsew"); hero.grid_columnconfigure(0,weight=1); hero.grid_rowconfigure(1,weight=1)
        top=ctk.CTkFrame(hero,fg_color="transparent"); top.grid(row=0,column=0,sticky="ew",padx=18,pady=14)
        self.reactor=ctk.CTkCanvas(top,width=88,height=88,bg=PANEL,highlightthickness=0); self.reactor.pack(side="left",padx=(0,16)); self.reactor.create_oval(7,7,81,81,outline=CYAN,width=3); self.reactor.create_oval(20,20,68,68,outline="#087EA1",width=3); self.reactor.create_oval(32,32,56,56,fill=CYAN,outline="#C7FBFF")
        ctk.CTkLabel(top,text="GOOD TO SEE YOU, BOSS.\nAI CORE READY  •  VOICE ENABLED ON DEMAND",justify="left",text_color="#EAF8FF",font=ctk.CTkFont(size=20,weight="bold")).pack(side="left",anchor="center")
        self.chat=ctk.CTkTextbox(hero,fg_color="#06101B",text_color="#DDEBF5",border_width=1,border_color="#133047",corner_radius=10,wrap="word",font=ctk.CTkFont(size=13)); self.chat.grid(row=1,column=0,sticky="nsew",padx=16,pady=6); self.chat.configure(state="disabled")
        bar=ctk.CTkFrame(hero,fg_color="transparent"); bar.grid(row=2,column=0,sticky="ew",padx=16,pady=(8,16)); bar.grid_columnconfigure(0,weight=1)
        self.entry=ctk.CTkEntry(bar,placeholder_text="Say a command or ask JARVIS…",height=43,fg_color="#0A1826",border_color="#1C4963"); self.entry.grid(row=0,column=0,sticky="ew",padx=(0,7)); self.entry.bind("<Return>",lambda e:self.send())
        ctk.CTkButton(bar,text="🎙 VOICE",width=88,command=self.listen,height=43,fg_color="#12435A").grid(row=0,column=1,padx=4)
        self.soundbtn=ctk.CTkButton(bar,text="♪ SOUND ON",width=95,command=self.toggle_sound,height=43,fg_color="#12435A"); self.soundbtn.grid(row=0,column=2,padx=4)
        ctk.CTkButton(bar,text="TRANSMIT ➤",width=125,command=self.send,height=43,fg_color="#007F9F").grid(row=0,column=3,padx=(4,0))
    def splash(self):
        self.overlay=ctk.CTkFrame(self,fg_color="#030A12",corner_radius=0); self.overlay.place(relx=0,rely=0,relwidth=1,relheight=1)
        ctk.CTkLabel(self.overlay,text="J.A.R.V.I.S.",font=ctk.CTkFont(size=44,weight="bold"),text_color=CYAN).place(relx=.5,rely=.38,anchor="center")
        ctk.CTkLabel(self.overlay,text="PERSONAL AI SYSTEM // INITIALIZING",text_color=GREEN).place(relx=.5,rely=.48,anchor="center")
        self.progress=ctk.CTkProgressBar(self.overlay,width=320,progress_color=CYAN); self.progress.place(relx=.5,rely=.56,anchor="center"); self.progress.set(0); self.progress_step(0)
    def progress_step(self,n):
        if not self.overlay.winfo_exists():return
        self.progress.set(n/20)
        if n<20:self.after(65,lambda:self.progress_step(n+1))
        else:self.after(350,self.overlay.destroy)
    def animate(self):
        if not self.winfo_exists():return
        try:self.reactor.itemconfigure(2,outline=CYAN if int(datetime.datetime.now().timestamp()*2)%2 else "#0A526D")
        except Exception:pass
        self.after(400,self.animate)
    def clock_tick(self):
        self.clock.configure(text=datetime.datetime.now().strftime("%a %d %b  %H:%M:%S")); self.after(1000,self.clock_tick)
    def add(self,who,msg):
        self.chat.configure(state="normal"); self.chat.insert("end",f"[{datetime.datetime.now():%H:%M:%S}] {who}\n{msg}\n\n"); self.chat.see("end"); self.chat.configure(state="disabled")
        if self.sound:
            try:
                if platform.system()=="Windows":
                    import winsound; winsound.MessageBeep(winsound.MB_OK)
            except Exception:pass
    def toggle_sound(self):
        self.sound=not self.sound; self.soundbtn.configure(text="♪ SOUND ON" if self.sound else "♪ SOUND OFF")
    def listen(self):self.voice.listen_once()
    def voice_result(self,text):
        def ui():self.entry.delete(0,"end"); self.entry.insert(0,text); self.send()
        self.after(0,ui)
    def send(self):
        if self.busy:return
        p=self.entry.get().strip()
        if not p:return
        self.entry.delete(0,"end"); self.add("BOSS",p); self.busy=True
        threading.Thread(target=self.process,args=(p,),daemon=True).start()
    def process(self,prompt):
        try:
            answer=self.command(prompt)
            if answer is None:answer=self.ask_ai(prompt)
        except Exception as e:answer=f"Error: {e}"
        self.events.put(("answer",answer))
    def command(self,text):
        p=text.strip().lower()
        if p in ("help","commands"):
            return ("Commands:\n• time / date / system info\n• open whatsapp\n• launch notepad / calculator / paint / file explorer / task manager / chrome / edge / firefox / vscode\n• search <query>\n• whatsapp search <contact>\n• whatsapp message <contact> | <message>\n• ask any question (configure Groq/Gemini API key)")
        if p in ("hi","hello","hey"):return "Hello, Boss. Standing by."
        if p=="time" or "what time" in p:return datetime.datetime.now().strftime("Local time: %I:%M:%S %p")
        if p=="date" or "what date" in p:return datetime.datetime.now().strftime("Today is %A, %d %B %Y")
        if p in ("system info","system status"):
            return f"Host: {socket.gethostname()}\nOS: {platform.platform()}\nPython: {platform.python_version()}\nProcessor: {platform.processor() or 'Unknown'}"
        if p in ("open whatsapp","whatsapp"):return open_whatsapp()
        if p.startswith("whatsapp search "):return search_contact(text[len("whatsapp search "):])
        if p.startswith("whatsapp message "):
            payload=text[len("whatsapp message "):]
            if "|" not in payload:return "Format: whatsapp message Contact Name | your message"
            name,msg=payload.split("|",1); return prepare_message(name,msg)
        if p.startswith("launch "):
            ok,msg=launch_app(text[7:].strip()); return msg
        if p.startswith("search "):
            q=text[7:].strip(); web_search(q); return "Opened a browser search for: "+q
        if p.startswith("open "):
            target=p[5:].strip()
            urls={"youtube":"https://youtube.com","google":"https://google.com","github":"https://github.com/sajinstalin01/Jarvis-ai","gmail":"https://mail.google.com","wikipedia":"https://wikipedia.org"}
            if target in urls:webbrowser.open(urls[target]); return "Opening "+target
        return None
    def ask_ai(self,prompt):
        groq_key=os.getenv("GROQ_API_KEY","").strip(); gemini_key=os.getenv("GEMINI_API_KEY","").strip(); error="Groq key not configured"
        if groq_key:
            try:
                from groq import Groq
                r=Groq(api_key=groq_key).chat.completions.create(model=os.getenv("GROQ_MODEL","llama-3.3-70b-versatile"),messages=[{"role":"system","content":"You are JARVIS, a helpful desktop assistant. Address the user as Boss. Never claim to have taken actions you did not take."},{"role":"user","content":prompt}],max_tokens=1200)
                return r.choices[0].message.content
            except Exception as e:error=str(e)
        if gemini_key:
            try:
                from google import genai
                r=genai.Client(api_key=gemini_key).models.generate_content(model=os.getenv("GEMINI_MODEL","gemini-2.5-flash"),contents="You are JARVIS. Address the user as Boss.\n"+prompt)
                return r.text or "No response returned."
            except Exception as e:return f"AI providers failed. Groq: {error}; Gemini: {e}"
        return "AI is not configured. Add GROQ_API_KEY or GEMINI_API_KEY to your local .env file."
    def poll(self):
        try:
            while True:
                kind,msg=self.events.get_nowait()
                if kind=="status":self.core.configure(text="● "+msg[:25].upper(),text_color=GREEN)
                else:
                    self.add("J.A.R.V.I.S.",msg); self.busy=False
                    if os.getenv("JARVIS_SPEAK_RESPONSES","false").lower()=="true":self.voice.speak(msg)
        except queue.Empty:pass
        self.after(100,self.poll)

if __name__=="__main__": JarvisV2().mainloop()
