"""Local-first feature pack for JARVIS. Optional dependencies fail gracefully."""
import csv, hashlib, json, os, platform, re, shutil, socket, sqlite3, subprocess, sys, time, urllib.request, zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path

EXTS={".txt",".md",".py",".js",".ts",".json",".yaml",".yml",".toml",".ini",".cfg",".log",".html",".css",".xml",".csv"}
def _read(p,limit=1000000):
    try:
        p=Path(p)
        return p.read_text(encoding="utf-8",errors="replace") if p.is_file() and p.stat().st_size<=limit else ""
    except OSError: return ""
def _inside(p,root):
    try: Path(p).resolve().relative_to(Path(root).resolve()); return True
    except (ValueError,OSError): return False
class FeatureHub:
    def __init__(self,root,bridge=None):
        self.root=Path(root).resolve(); self.bridge=bridge; self.data=self.root/"jarvis_data"; self.data.mkdir(parents=True,exist_ok=True)
        self.dbpath=self.data/"features.sqlite3"; self.projects_file=self.data/"projects.json"; self.workflow_file=self.data/"visual_workflows.json"
        self.plugins=self.root/"plugins"; self.backups=self.data/"backups"; self.staging=self.data/"restore_staging"
        with self.db() as c:
            c.executescript("CREATE TABLE IF NOT EXISTS edges(id INTEGER PRIMARY KEY,src TEXT,rel TEXT,dst TEXT,UNIQUE(src,rel,dst)); CREATE TABLE IF NOT EXISTS files(path TEXT PRIMARY KEY,content TEXT,digest TEXT); CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,at TEXT,action TEXT,result TEXT); CREATE TABLE IF NOT EXISTS timings(id INTEGER PRIMARY KEY,name TEXT,ms REAL);")
    def db(self):
        c=sqlite3.connect(self.dbpath,timeout=10); c.row_factory=sqlite3.Row; return c
    def audit(self,a,r="ok"):
        with self.db() as c: c.execute("INSERT INTO audit(at,action,result) VALUES(?,?,?)",(datetime.now().isoformat(),a,r))
    def dispatch(self,cmd):
        s=str(cmd or "").strip(); p=s.casefold()
        try:
            if p in {"features","feature help","features help"}: return self.help()
            if p in {"vision screenshot","screen capture"}: return self.screenshot()
            if p=="vision ocr" or p.startswith("vision ocr "): return self.ocr(s[10:].strip() if len(s)>10 else "")
            if p.startswith("files index "): return self.index(s[12:].strip())
            if p.startswith("files search "): return self.file_search(s[13:].strip())
            if p.startswith("files summarize "): return self.summarize(s[16:].strip())
            if p in {"network inspect","network status"}: return self.network()
            if p in {"network diagnose","network diagnostics"}: return self.network_diagnose()
            if p in {"dev check","developer workbench"}: return self.dev_check()
            if p.startswith("dev check "): return self.dev_check(s[10:].strip())
            if p.startswith("dev test "): return self.dev_test(s[9:].strip())
            if p.startswith("graph add "): return self.graph_add(s[10:].strip())
            if p.startswith("graph search "): return self.graph_search(s[13:].strip())
            if p in {"graph","graph list"}: return self.graph_search("")
            if p=="security audit": return self.security_audit()
            if p in {"workflow studio","workflow studio list"}: return self.workflow_list()
            if p.startswith("workflow studio add "): return self.workflow_add(s[20:].strip())
            if p.startswith("workflow studio run "): return self.workflow_run(s[20:].strip())
            if p in {"plugins","plugins list","plugin sdk"}: return self.plugin_list()
            if p=="plugins validate": return self.plugin_validate()
            if p.startswith("agent plan "): return self.agent_plan(s[11:].strip())
            if p.startswith("agent mission "): return self.agent_mission(s[14:].strip())
            if p.startswith("agent approve:"): return self.agent_approve(s.split(":",1)[1].strip())
            if p.startswith("models pull "): return self.models_pull(s[12:].strip())
            if p in {"models","models list","models status","local models"}: return self.models_status()
            if p=="models hardware": return self.models_hardware()
            if p.startswith("analyze "): return self.analyze(s[8:].strip())
            if p in {"clipboard read","clipboard inspect"}: return self.clipboard()
            if p.startswith("project add "): return self.project_add(s[12:].strip())
            if p in {"projects","project list"}: return self.project_list()
            if p.startswith("project use "): return self.project_use(s[12:].strip())
            if p.startswith("project index "): return self.project_index(s[14:].strip())
            if p.startswith("find "): return self.find(s[5:].strip())
            if p=="backup create": return self.backup_create()
            if p=="backup status": return self.backup_status()
            if p.startswith("backup restore stage "): return self.restore_stage(s[21:].strip())
            if p in {"profile report","performance report"}: return self.profile()
            if p in {"companion status","companion help"}: return self.companion()
            if p in {"proactive status","proactive check"}: return self.proactive(p.endswith("check"))
            if p in {"proactive on","proactive off"}: return self.proactive_set(p.endswith("on"))
        except Exception as e:
            self.audit("feature-command-error",type(e).__name__)
            return "Feature command failed safely: "+type(e).__name__+": "+str(e)
        return None
    def help(self):
        return """JARVIS feature commands:
vision screenshot / vision ocr [image-path]
files index <folder> / files search <keywords> / files summarize <file>
network inspect / network diagnose
dev check [python-file] / dev test [test-folder]
graph add <source> -> <relation> -> <target> / graph search <words>
security audit
workflow studio add <name>: time; calculate 2 + 2 / workflow studio list / workflow studio run <name>
plugins list / plugins validate
agent plan <task> / agent mission <task> / agent approve: <read-only command>
models status / models hardware / models pull <model>
analyze <csv/json/document> / clipboard read
project add <name>: <folder> / projects / project use <name> / project index <name|active> / find <words>
backup create / backup status / backup restore stage <zip>
profile report / companion status / proactive on|off|status|check
Safety: no arbitrary shell commands, automatic plugin execution, or background screen/clipboard monitoring."""
    def screenshot(self):
        t=time.perf_counter()
        try:
            from PIL import ImageGrab
            folder=self.data/"screenshots"; folder.mkdir(exist_ok=True)
            p=folder/("screen_"+datetime.now().strftime("%Y%m%d_%H%M%S")+".png"); ImageGrab.grab().save(p)
            ms=(time.perf_counter()-t)*1000
            with self.db() as c: c.execute("INSERT INTO timings(name,ms) VALUES(?,?)",("vision.screenshot",ms))
            self.audit("vision.screenshot")
            return f"Saved screenshot locally: {p}\nRun vision ocr {p} to extract text."
        except Exception as e: return f"Screenshot unavailable: {e}. Pillow and a supported desktop session are required."
    def ocr(self,arg):
        p=Path(arg.strip('"')).expanduser() if arg else None
        if p is None:
            fs=sorted((self.data/"screenshots").glob("*.png"),key=lambda x:x.stat().st_mtime,reverse=True) if (self.data/"screenshots").exists() else []
            if not fs: return "No screenshot; run vision screenshot first."
            p=fs[0]
        if not p.is_file(): return "Image not found."
        try:
            from PIL import Image
            import pytesseract
            return pytesseract.image_to_string(Image.open(p)).strip()[:7000] or "No readable text detected."
        except ImportError: return "OCR requires Pillow, pytesseract, and the Tesseract OCR application."
        except Exception as e: return f"OCR failed: {e}"
    def _walk(self,folder):
        p=Path(folder).expanduser()
        if not p.is_absolute(): p=self.root/p
        if not p.is_dir(): raise ValueError("Folder not found.")
        skip={".git",".venv","venv","node_modules","__pycache__","jarvis_data","dist","build"}; n=0
        for base,dirs,files in os.walk(p):
            dirs[:]=[x for x in dirs if x not in skip and not x.startswith(".")]
            for name in files:
                f=Path(base)/name
                try:
                    if f.suffix.lower() in EXTS and f.stat().st_size<=1000000:
                        yield f; n+=1
                        if n>=3000: return
                except OSError: pass
    def index(self,folder):
        t=time.perf_counter(); n=0
        for f in self._walk(folder):
            text=_read(f)
            if not text: continue
            with self.db() as c: c.execute("INSERT INTO files VALUES(?,?,?) ON CONFLICT(path) DO UPDATE SET content=excluded.content,digest=excluded.digest",(str(f.resolve()),text[:200000],hashlib.sha256(text.encode()).hexdigest()))
            n+=1
        ms=(time.perf_counter()-t)*1000
        with self.db() as c: c.execute("INSERT INTO timings(name,ms) VALUES(?,?)",("files.index",ms))
        self.audit("files.index",str(n)); return f"Indexed {n} text files locally in {ms:.0f} ms. Search uses local TF-IDF-style relevance ranking and snippets; no embeddings or cloud upload."
    def file_search(self,q):
        """Rank indexed local files with a dependency-free TF-IDF/BM25-like scorer."""
        stop={"a","an","and","are","as","at","be","by","for","from","how","in","is","it","of","on","or","the","to","was","what","when","where","with"}
        terms=[x.casefold() for x in re.findall(r"[\w.-]+",q) if len(x)>1 and x.casefold() not in stop]
        if not terms: return "Use files search <keywords>."
        with self.db() as c: rows=c.execute("SELECT path,content FROM files").fetchall()
        if not rows: return "No indexed files yet. Run files index <folder>."
        token_re=re.compile(r"[\w.-]{2,}",re.UNICODE)
        docs=[]
        df=Counter()
        for r in rows:
            path=str(r["path"]); content=str(r["content"] or "")
            body_tokens=[t.casefold() for t in token_re.findall(content)]
            path_tokens=[t.casefold() for t in token_re.findall(Path(path).name)]
            counts=Counter(body_tokens)
            for term in set(terms):
                if counts[term] or term in path_tokens: df[term]+=1
            docs.append((path,content,counts,path_tokens,body_tokens))
        scored=[]
        total=len(docs)
        for path,content,counts,path_tokens,body_tokens in docs:
            length=max(1,len(body_tokens)); score=0.0
            for term in set(terms):
                tf=counts[term]
                if tf:
                    idf=1.0+__import__("math").log(1+(total-df[term]+0.5)/(df[term]+0.5))
                    score+=idf*(tf*2.2)/(tf+1.2*(0.25+0.75*length/500.0))
                if term in path_tokens: score+=3.0
            normalized=" ".join(body_tokens)
            phrase=" ".join(terms)
            if len(terms)>1 and phrase in normalized: score+=2.5
            matched=sum(1 for term in set(terms) if counts[term] or term in path_tokens)
            if matched and score>0:
                # Return a compact context window around the earliest matching token.
                lines=content.splitlines()
                snippet=""
                for i,line in enumerate(lines):
                    low=line.casefold()
                    if any(t in low for t in terms):
                        start=max(0,i-1); snippet=" ".join(x.strip() for x in lines[start:min(len(lines),i+2)] if x.strip())
                        break
                if not snippet:
                    snippet=content[:220].replace("\n"," ")
                snippet=re.sub(r"\s+"," ",snippet).strip()[:220]
                scored.append((score,matched,path,snippet))
        scored.sort(key=lambda x:(x[0],x[1],x[2]),reverse=True)
        self.audit("files.search",f"results={min(15,len(scored))}")
        return "\n".join(f"{score:.2f} · {path}\n   {snippet}" for score,_,path,snippet in scored[:15]) or "No indexed matches. Try fewer or different keywords, or run files index <folder>."
    def summarize(self,arg):
        p=Path(arg.strip('"')).expanduser()
        if not p.is_absolute(): p=self.root/p
        if not p.is_file(): return "File not found."
        try:
            if p.suffix.lower()==".pdf":
                from pypdf import PdfReader
                text="\n".join(x.extract_text() or "" for x in PdfReader(str(p)).pages[:30])
            elif p.suffix.lower()==".docx":
                from docx import Document
                text="\n".join(x.text for x in Document(str(p)).paragraphs)
            else: text=_read(p,5000000)
        except ImportError: return "Install optional pypdf or python-docx for PDF/DOCX extraction."
        except Exception as e: return f"Extraction failed: {e}"
        if p.suffix.lower()==".csv": return self.analyze(str(p))
        if not text: return "No readable text found."
        words=re.findall(r"\b[\w'-]+\b",text); lines=[x.strip() for x in text.splitlines() if x.strip()]
        freq=Counter(x.casefold() for x in words if len(x)>4)
        return f"{p.name}: {len(words)} words, {len(lines)} lines\nFrequent terms: "+", ".join(f"{x} ({n})" for x,n in freq.most_common(8))+"\n\nExcerpt:\n"+"\n".join(lines[:12])[:3000]
    def network(self):
        out=[f"Host: {socket.gethostname()}",f"Platform: {platform.platform()}"]
        try: out.append("Local IP: "+socket.gethostbyname(socket.gethostname()))
        except OSError: out.append("Local IP: unavailable")
        try: out.append("DNS lookup: "+socket.getaddrinfo("example.com",443)[0][4][0])
        except OSError: out.append("DNS lookup: failed/offline")
        try:
            import psutil
            out.append("Interfaces: "+", ".join(f"{k}={'up' if v.isup else 'down'}" for k,v in psutil.net_if_stats().items()))
            n=psutil.net_io_counters(); out.extend([f"Bytes sent: {n.bytes_sent}",f"Bytes received: {n.bytes_recv}"])
        except Exception: out.append("Install psutil for interface metrics.")
        return "\n".join(out)
    def network_diagnose(self):
        out=[]
        for host in ("127.0.0.1","1.1.1.1","example.com"):
            try: socket.getaddrinfo(host,None); out.append("PASS · "+host)
            except OSError as e: out.append("FAIL · "+host+": "+str(e))
        return "\n".join(out+["Basic DNS/lookup tests only; no port scanning."])
    def dev_check(self,arg=None):
        ps=[Path(arg).expanduser()] if arg else list(self.root.glob("*.py")); out=[]
        for p in ps[:30]:
            if not p.is_absolute(): p=self.root/p
            if not p.is_file() or p.suffix!=".py": out.append("SKIP · "+str(p)); continue
            try: compile(_read(p),str(p),"exec"); out.append("PASS · "+p.name)
            except SyntaxError as e: out.append(f"FAIL · {p.name}:{e.lineno} · {e}")
        return "\n".join(out) or "No Python files found."
    def dev_test(self,folder="tests"):
        p=Path(folder).expanduser()
        if not p.is_absolute(): p=self.root/p
        if not p.is_dir() or not _inside(p,self.root): return "Test folder must be inside the repository."
        try:
            r=subprocess.run([sys.executable,"-m","unittest","discover","-s",str(p)],cwd=self.root,capture_output=True,text=True,timeout=180)
            self.audit("dev.test",str(r.returncode)); return (r.stdout+"\n"+r.stderr)[-7000:] or f"Exit code {r.returncode}"
        except (OSError,subprocess.SubprocessError) as e: return str(e)
    def graph_add(self,arg):
        x=[v.strip() for v in arg.split("->")]
        if len(x)!=3 or not all(x) or any(len(v)>200 for v in x): return "Use graph add <source> -> <relation> -> <target>."
        with self.db() as c: c.execute("INSERT OR IGNORE INTO edges(src,rel,dst) VALUES(?,?,?)",x)
        return f"Knowledge link saved: {x[0]} —[{x[1]}]→ {x[2]}"
    def graph_search(self,q):
        with self.db() as c:
            if q:
                like="%"+q[:100]+"%"; rows=c.execute("SELECT src,rel,dst FROM edges WHERE src LIKE ? OR rel LIKE ? OR dst LIKE ? ORDER BY id DESC LIMIT 30",(like,like,like)).fetchall()
            else: rows=c.execute("SELECT src,rel,dst FROM edges ORDER BY id DESC LIMIT 30").fetchall()
        return "\n".join(f"{r['src']} —[{r['rel']}]→ {r['dst']}" for r in rows) or "No knowledge links yet."
    def security_audit(self):
        ignore=_read(self.root/".gitignore"); out=[]
        for item in (".env","jarvis_data/","config/api_keys.json","config/app_permissions.json"):
            out.append(("PASS" if item in ignore else "REVIEW")+" · .gitignore "+item)
        if (self.root/".env").exists(): out.append("INFO · local .env exists; values hidden.")
        try:
            r=subprocess.run(["git","ls-files"],cwd=self.root,capture_output=True,text=True,timeout=10); names=r.stdout.splitlines()[:5000] if r.returncode==0 else []
        except OSError: names=[]
        patterns=[re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"]?([A-Za-z0-9_./+=-]{12,})"),re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")]
        found=0
        for name in names:
            p=self.root/name
            if p.suffix.lower() not in EXTS or p.name in {".env","api_keys.json"}: continue
            txt=_read(p,500000)
            if txt and any(rx.search(txt) for rx in patterns):
                out.append("REVIEW · Possible secret-like pattern in "+name+"; value hidden"); found+=1
                if found>=20: break
        if not found: out.append("PASS · No obvious secret patterns in scanned tracked text (heuristic only).")
        out.append("Do not expose the authenticated HTTP remote API publicly.")
        self.audit("security.audit",str(found)); return "\n".join(out)
    def _workflows(self):
        try:
            d=json.loads(_read(self.workflow_file) or "{}"); return d if isinstance(d,dict) else {}
        except ValueError: return {}
    def workflow_list(self):
        d=self._workflows(); return "\n".join(f"{k}: {'; '.join(v.get('steps',[]))}" for k,v in d.items()) or "No workflows saved."
    def workflow_add(self,arg):
        if ":" not in arg: return "Use workflow studio add <name>: time; calculate 2 + 2"
        name,tail=(x.strip() for x in arg.split(":",1)); steps=[x.strip() for x in tail.split(";") if x.strip()]
        def safe(x):
            p=x.casefold()
            return p.startswith(("search ","calculate ","system info","network inspect","files search ","graph search ")) or p in {"time","date","developer diagnostics"}
        if not name or len(name)>80 or not 1<=len(steps)<=20 or not all(safe(x) for x in steps): return "Only 1–20 validated read-only steps are allowed."
        d=self._workflows(); d[name]={"steps":steps,"version":1,"updated_at":datetime.now().isoformat()}
        self.workflow_file.write_text(json.dumps(d,indent=2),encoding="utf-8"); return f"Saved workflow {name} with {len(steps)} read-only steps."
    def workflow_run(self,name):
        w=self._workflows().get(name)
        if not w: return "Workflow not found."
        if not self.bridge: return "Workflow needs the active JARVIS bridge."
        out=[]
        for s in w.get("steps",[]): out.append(str(self.bridge._local_command(s) or "No result"))
        return "\n".join(out)
    def plugin_list(self):
        self.plugins.mkdir(exist_ok=True); out=[]
        for p in sorted(self.plugins.glob("*/manifest.json")):
            try:
                d=json.loads(_read(p,100000)); out.append(f"{d.get('name',p.parent.name)} v{d.get('version','?')} · metadata only")
            except Exception: out.append("INVALID · "+p.parent.name)
        return "\n".join(out) or "No plugins installed. See plugins/README.md. Plugin code is never auto-executed."
    def plugin_validate(self):
        self.plugins.mkdir(exist_ok=True); out=[]
        for p in sorted(self.plugins.glob("*/manifest.json")):
            try:
                d=json.loads(_read(p,100000)); missing={"name","version","description"}-set(d)
                out.append(("FAIL" if missing else "PASS")+" · "+p.parent.name+(": missing "+", ".join(sorted(missing)) if missing else " manifest valid"))
            except Exception as e: out.append(f"FAIL · {p.parent.name}: {e}")
        return "\n".join(out) or "No plugin manifests found."
    def agent_plan(self,task):
        return f"Plan for {task[:300]}:\n1. Clarify scope. 2. Inspect relevant context. 3. Propose reversible steps. 4. Ask before changes. 5. Verify with tests.\nNo actions executed. Use agent approve only for read-only commands."
    def agent_mission(self,task):
        if not self.bridge: return "Multi-agent review needs the active JARVIS bridge."
        try:
            from jarvis_ai import generate_response
            out=[]
            for role,goal in (("Planner","Produce testable steps"),("Risk reviewer","Find risks and approvals needed"),("Verifier","Define objective tests")):
                answer,provider=generate_response(f"You are the {role} agent. {goal}. Do not claim actions were executed. Task: {task[:2000]}",context=[],saved_memories="")
                out.append(f"{role} ({provider}):\n{answer[:2500]}")
            self.audit("agent.mission"); return "Multi-agent advisory review; no tools executed.\n\n"+"\n\n".join(out)
        except Exception as e: return f"Agent review failed: {type(e).__name__}: {e}"
    def agent_approve(self,arg):
        p=arg.casefold()
        if p.startswith(("search ","calculate ")) or p in {"time","date","system info","network inspect"}:
            return self.bridge._local_command(arg) if self.bridge else "No bridge."
        return "Blocked: approvals support only search, calculation, time/date, system info and network inspection."
    def models_status(self):
        try:
            with urllib.request.urlopen("http://127.0.0.1:11434/api/tags",timeout=2) as r: data=json.loads(r.read(1000000))
            return "Ollama reachable.\n"+("\n".join(f"{m.get('name','?')} · {m.get('size',0)//1048576} MiB" for m in data.get("models",[])) or "No local models installed.")
        except Exception: return "Ollama not detected at localhost:11434. Install/start Ollama separately."
    def models_hardware(self):
        try:
            import psutil
            m=psutil.virtual_memory(); return f"{platform.platform()}\nLogical CPUs: {os.cpu_count()}\nRAM: {m.total//(1024**3)} GiB total, {m.available//(1024**3)} GiB available. GPU details depend on vendor tools."
        except Exception: return f"{platform.platform()}\nLogical CPUs: {os.cpu_count()}; install psutil for RAM metrics."
    def models_pull(self,name):
        if not re.fullmatch(r"[A-Za-z0-9_.:/-]{1,120}",name or ""): return "Use models pull <model-name>. Explicitly starts a potentially multi-GB local download."
        req=urllib.request.Request("http://127.0.0.1:11434/api/pull",data=json.dumps({"name":name,"stream":False}).encode(),headers={"Content-Type":"application/json"},method="POST")
        try:
            with urllib.request.urlopen(req,timeout=900) as r: d=json.loads(r.read(2000000))
            self.audit("models.pull",name); return f"Model pull result: {d.get('status','response received')} · {name}"
        except Exception as e: return f"Local Ollama pull failed: {e}"
    def analyze(self,arg):
        p=Path(arg.strip('"')).expanduser()
        if not p.is_absolute(): p=self.root/p
        if p.suffix.lower()==".csv":
            try:
                with p.open(newline="",encoding="utf-8-sig") as f: rows=list(csv.DictReader(f))[:5000]
                if not rows: return "CSV contains no rows."
                out=[f"CSV {p.name}: {len(rows)} rows; columns {', '.join(list(rows[0])[:50])}"]
                for col in list(rows[0])[:20]:
                    nums=[]
                    for row in rows:
                        try: nums.append(float(str(row.get(col,"")).replace(",","")))
                        except (ValueError,TypeError): pass
                    if nums: out.append(f"{col}: min {min(nums):g}, max {max(nums):g}, mean {sum(nums)/len(nums):g}")
                return "\n".join(out)
            except Exception as e: return f"CSV analysis failed: {e}"
        if p.suffix.lower() in {".json",".jsonl"}:
            try:
                d=json.loads(_read(p,5000000))
                return f"JSON object with {len(d)} keys: {', '.join(list(d)[:80])}" if isinstance(d,dict) else f"JSON {type(d).__name__}, {len(d) if hasattr(d,'__len__') else 'scalar'} items"
            except Exception as e: return f"JSON analysis failed: {e}"
        return self.summarize(str(p))
    def clipboard(self):
        try:
            import pyperclip
            text=pyperclip.paste(); self.audit("clipboard.read",str(len(text))); return "Clipboard (one-shot, not stored):\n"+str(text)[:5000]
        except ImportError: return "Optional clipboard package: pip install pyperclip. No continuous monitoring is performed."
        except Exception as e: return f"Clipboard unavailable: {e}"
    def _projects(self):
        try:
            d=json.loads(_read(self.projects_file) or '{"projects":{},"active":""}')
            return d if isinstance(d,dict) and isinstance(d.get("projects"),dict) else {"projects":{},"active":""}
        except ValueError: return {"projects":{},"active":""}
    def project_add(self,arg):
        if ":" not in arg: return "Use project add <name>: <folder>"
        name,folder=(x.strip() for x in arg.split(":",1)); p=Path(folder.strip('"')).expanduser()
        if not p.is_absolute(): p=self.root/p
        if not name or not p.is_dir(): return "Invalid project name/folder."
        d=self._projects(); d["projects"][name]=str(p.resolve()); d["active"]=name; self.projects_file.write_text(json.dumps(d,indent=2),encoding="utf-8")
        return f"Project {name} registered and selected."
    def project_list(self):
        d=self._projects(); return "\n".join(("* " if k==d.get("active") else "  ")+f"{k}: {v}" for k,v in d["projects"].items()) or "No projects registered."
    def project_use(self,name):
        d=self._projects()
        if name not in d["projects"] or not Path(d["projects"][name]).is_dir(): return "Project not found."
        d["active"]=name; self.projects_file.write_text(json.dumps(d,indent=2),encoding="utf-8"); return f"Active project context: {name} · {d['projects'][name]}"
    def project_index(self,name):
        d=self._projects()
        if name.casefold()=="active": name=d.get("active","")
        folder=d["projects"].get(name)
        if not folder or not Path(folder).is_dir(): return "Project not found. Register it with project add <name>: <folder> first."
        # Reindexing is explicit: this reads supported text files locally and never uploads them.
        result=self.index(folder)
        self.audit("project.index",name)
        return f"Project index · {name} ({folder})\n{result}"
    def find(self,q):
        terms=[x.casefold() for x in re.findall(r"[\w.-]+",q) if len(x)>1]
        if not terms: return "Use find <words>."
        out=["Repository · "+p.name for p in self.root.iterdir() if any(t in p.name.casefold() for t in terms)]
        d=self._projects(); out += [f"Project · {k}: {v}" for k,v in d["projects"].items() if any(t in (k+" "+v).casefold() for t in terms)]
        with self.db() as c: rows=c.execute("SELECT path,content FROM files").fetchall()
        for r in rows:
            if any(t in (r["path"]+" "+r["content"]).casefold() for t in terms): out.append("Indexed file · "+r["path"])
            if len(out)>=25: break
        return "\n".join(out[:25]) or "No matches; index a folder first."
    def backup_create(self):
        self.backups.mkdir(parents=True,exist_ok=True); p=self.backups/("jarvis-safe-"+datetime.now().strftime("%Y%m%d-%H%M%S")+".zip")
        top=["README.md","requirements.txt","update_config.json",".gitignore","jarvis.py","jarvis_legacy.py","jarvis_ai.py","jarvis_services.py","jarvis_remote.py","jarvis_control.py","open_command.py","app_control_manager.py","voice_control.py","font_manager.py","elevenlabs_manager.py","ui.py","ui_theme.py","app_permissions.py"]
        with zipfile.ZipFile(p,"w",zipfile.ZIP_DEFLATED) as z:
            for n in top:
                f=self.root/n
                if f.is_file(): z.write(f,n)
            for folder in ("features","tests","core","memory","providers"):
                base=self.root/folder
                if base.is_dir():
                    for f in base.rglob("*"):
                        if f.is_file() and not any(x in {".git", ".venv", "__pycache__", "node_modules"} for x in f.parts) and f.name not in {".env","api_keys.json","app_permissions.json","jarvis.sqlite3","long_term.json"}: z.write(f,str(f.relative_to(self.root)))
            z.writestr("BACKUP-MANIFEST.json",json.dumps({"created_at":datetime.now().isoformat(),"secrets_excluded":True,"restore":"staging only"}))
        self.audit("backup.create",p.name); return f"Safe source backup created: {p}\nSecrets/local databases excluded. Restore with backup restore stage <zip>."
    def backup_status(self):
        self.backups.mkdir(parents=True,exist_ok=True); fs=sorted(self.backups.glob("*.zip"),key=lambda x:x.stat().st_mtime,reverse=True)
        return "\n".join(f"{x.name} · {x.stat().st_size//1024} KiB" for x in fs[:15]) or "No backups yet."
    def restore_stage(self,arg):
        p=Path(arg.strip('"')).expanduser()
        if not p.is_absolute(): p=self.root/p
        if not p.is_file() or p.suffix.lower()!=".zip": return "Backup ZIP not found."
        target=self.staging/datetime.now().strftime("%Y%m%d-%H%M%S"); target.mkdir(parents=True,exist_ok=False)
        try:
            with zipfile.ZipFile(p) as z:
                items=z.infolist()
                if len(items)>3000 or sum(x.file_size for x in items)>100000000: raise ValueError("archive safety limits exceeded")
                for item in items:
                    if "\\" in item.filename: continue
                    n=Path(item.filename)
                    if n.is_absolute() or ".." in n.parts or any(x in {".env","api_keys.json","app_permissions.json","jarvis.sqlite3","long_term.json"} for x in n.parts): continue
                    dest=(target/n).resolve()
                    if not _inside(dest,target): continue
                    if item.is_dir(): dest.mkdir(parents=True,exist_ok=True)
                    else:
                        dest.parent.mkdir(parents=True,exist_ok=True)
                        with z.open(item) as src,dest.open("wb") as dst: shutil.copyfileobj(src,dst)
            return f"Extracted to staging only: {target}\nNo live files were overwritten; inspect before manual restore."
        except Exception as e: shutil.rmtree(target,ignore_errors=True); return f"Restore failed safely: {e}"
    def profile(self):
        with self.db() as c: rows=c.execute("SELECT name,COUNT(*) n,AVG(ms) avg,MAX(ms) mx FROM timings GROUP BY name ORDER BY n DESC LIMIT 25").fetchall()
        return "\n".join(f"{r['name']}: {r['n']} run(s), avg {r['avg']:.1f} ms, max {r['mx']:.1f} ms" for r in rows) or "No timings yet; run files index or vision screenshot."
    def companion(self):
        return "Uses existing authenticated JARVIS remote API. Start with remote server start. Default is loopback; LAN access must be explicitly enabled on a trusted network. Transport is HTTP, not TLS; never expose publicly. A separate Android companion app is not included."
    def proactive_set(self,on):
        (self.data/"proactive_settings.json").write_text(json.dumps({"enabled":bool(on),"updated_at":datetime.now().isoformat()},indent=2),encoding="utf-8")
        return "Proactive suggestions "+("enabled" if on else "disabled")+"; no background monitor started."
    def proactive(self,check=False):
        try: on=bool(json.loads(_read(self.data/"proactive_settings.json") or "{}").get("enabled",False))
        except ValueError: on=False
        out=["Proactive suggestions: "+("enabled" if on else "disabled")]
        if check and on:
            try:
                import pygetwindow
                w=pygetwindow.getActiveWindow(); out.append("Active window: "+str(w.title if w else "(none)")[:250])
            except ImportError: out.append("Optional active-window lookup: pip install pygetwindow.")
            except Exception as e: out.append("Active-window lookup unavailable: "+str(e))
        elif check: out.append("Enable with proactive on before checking.")
        out.append("No background screenshots, keystrokes, or clipboard monitoring.")
        return "\n".join(out)
