"""Permission-gated PC operator. Desktop actions are confirmed individually."""
import os, platform, re, subprocess
class PCOperator:
 def __init__(self,permissions,confirm): self.permissions,self.confirm=permissions,confirm
 def dispatch(self,command):
  s=str(command or "").strip(); p=s.casefold()
  if p in {"pc control help","pc help"}: return "pc metrics | pc windows | pc monitors; pc window focus|minimize|maximize|restore|close <title>; pc window move <title> <x> <y> <width> <height>; pc mouse click|double click|right click|move <x> <y>; pc mouse scroll <n>; pc mouse drag <x1> <y1> <x2> <y2>; pc keyboard type <text>; pc keyboard press <key>; pc keyboard hotkey <ctrl+c|ctrl+v|ctrl+z|alt+tab|win+d>; pc settings wifi|bluetooth|display|sound|brightness|power; pc volume up|down|mute; pc power shutdown|restart|sleep|logout. Sensitive actions require permissions and per-action confirmation."
  if p in {"pc metrics","pc hardware","pc resources"}: return self.metrics()
  if p in {"pc windows","pc window list","list windows"}: return self.windows()
  if p in {"pc monitors","pc displays"}: return self.monitors()
  m=re.fullmatch(r"pc window move (.+?) (-?\\d+) (-?\\d+) (\\d+) (\\d+)",s,re.I)
  if m:return self.window_move(m.group(1).strip(),*(int(m.group(i)) for i in range(2,6)))
  m=re.fullmatch(r"pc window (minimize|maximize|restore|close|focus) (.+)",s,re.I)
  if m:return self.window_action(m.group(1).casefold(),m.group(2).strip())
  m=re.fullmatch(r"pc mouse (click|double click|right click|move) (-?\d+) (-?\d+)",s,re.I)
  if m:return self.mouse(m.group(1).casefold(),int(m.group(2)),int(m.group(3)))
  m=re.fullmatch(r"pc mouse scroll (-?\d+)",s,re.I)
  if m:return self.scroll(int(m.group(1)))
  m=re.fullmatch(r"pc mouse drag (-?\d+) (-?\d+) (-?\d+) (-?\d+)",s,re.I)
  if m:return self.drag(*(int(m.group(i)) for i in range(1,5)))
  m=re.fullmatch(r"pc keyboard type (.+)",s,re.I|re.S)
  if m:return self.type_text(m.group(1))
  m=re.fullmatch(r"pc keyboard hotkey ([A-Za-z0-9+_-]+)",s,re.I)
  if m:return self.hotkey(m.group(1))
  m=re.fullmatch(r"pc keyboard press ([A-Za-z0-9_+-]+)",s,re.I)
  if m:return self.press_key(m.group(1))
  m=re.fullmatch(r"pc settings? (wifi|wi-fi|bluetooth|display|sound|brightness|power|network)",s,re.I)
  if m:return self.settings(m.group(1).casefold())
  m=re.fullmatch(r"pc volume (up|down|mute)",s,re.I)
  if m:return self.volume(m.group(1).casefold())
  m=re.fullmatch(r"pc power (shutdown|restart|sleep|logout|log out)",s,re.I)
  if m:return self.power(m.group(1).casefold())
  return None
 def approve(self,perm,title,detail):
  if not self.permissions.has(perm):return False,"Permission disabled. Use 'grant permission "+perm.replace("_"," ")+"' first."
  return (True,"") if self.confirm(title,detail+"\n\nProceed?") else (False,"Cancelled; no action was taken.")
 def metrics(self):
  import os,platform,subprocess
  out=[platform.platform(),"Logical CPUs: "+str(os.cpu_count() or "?")]
  try:
   import psutil
   out.append("CPU usage: %.1f%%"%psutil.cpu_percent(interval=.2)); v=psutil.virtual_memory()
   out.append("RAM: %.1f%% used, %.1f/%.1f GiB"%(v.percent,(v.total-v.available)/1024**3,v.total/1024**3))
   for d in psutil.disk_partitions()[:8]:
    try:out.append("Disk %s: %.1f%% used"%(d.device or d.mountpoint,psutil.disk_usage(d.mountpoint).percent))
    except (OSError,PermissionError):pass
   n=psutil.net_io_counters();out.append("Network I/O: sent %.1f MiB, received %.1f MiB"%(n.bytes_sent/1048576,n.bytes_recv/1048576))
  except ImportError:out.append("Install psutil for resource metrics.")
  try:
   g=subprocess.run(["nvidia-smi","--query-gpu=name,utilization.gpu,memory.used,memory.total","--format=csv,noheader"],capture_output=True,text=True,timeout=3)
   out.append("GPU: "+g.stdout.strip()[:500] if g.returncode==0 and g.stdout.strip() else "GPU telemetry unavailable.")
  except (OSError,subprocess.SubprocessError):out.append("GPU: vendor telemetry tool unavailable.")
  return "\n".join(out)
 def winlist(self):
  if platform.system()!="Windows":raise RuntimeError("Native window management currently requires Windows 10/11.")
  import pygetwindow
  return [w for w in pygetwindow.getAllWindows() if str(w.title).strip()]
 def windows(self):
  try:return "\n".join("• "+w.title for w in self.winlist()[:80]) or "No titled windows."
  except Exception as e:return "Window listing unavailable: "+str(e)
 def monitors(self):
  try:
   from screeninfo import get_monitors
   return "\n".join("Display %d: %dx%d at (%d,%d)"%(i+1,m.width,m.height,m.x,m.y) for i,m in enumerate(get_monitors())) or "No displays detected."
  except ImportError:return "Install screeninfo to list displays."
  except Exception as e:return "Display listing unavailable: "+str(e)
 def window_action(self,action,q):
  try:
   if not self.permissions.has("window_control"):return "Permission disabled. Use 'grant permission window control' first."
   matches=[w for w in self.winlist() if q.casefold() in w.title.casefold()]
   if not matches:return "No visible window matched: "+q
   if len(matches)>1:return "Multiple windows matched; use a more specific title: "+", ".join(w.title for w in matches[:8])
   w=matches[0]
   if "jarvis" in w.title.casefold():return "Controlling the JARVIS window itself is blocked."
   ok,msg=self.approve("window_control","Window control",action.title()+" window '"+w.title+"'?")
   if not ok:return msg
   {"minimize":w.minimize,"maximize":w.maximize,"restore":w.restore,"focus":w.activate,"close":w.close}[action]()
   return "Requested "+action+" for '"+w.title+"'."
  except Exception as e:return "Window action unavailable: "+str(e)
 def window_move(self,q,x,y,width,height):
  if width<100 or height<80 or width>10000 or height>10000 or abs(x)>20000 or abs(y)>20000:return "Window geometry outside safe limits."
  try:
   if not self.permissions.has("window_control"):return "Permission disabled. Use 'grant permission window control' first."
   matches=[w for w in self.winlist() if q.casefold() in w.title.casefold()]
   if not matches:return "No visible window matched: "+q
   if len(matches)>1:return "Multiple windows matched; use a more specific title: "+", ".join(w.title for w in matches[:8])
   w=matches[0]
   if "jarvis" in w.title.casefold():return "Controlling the JARVIS window itself is blocked."
   ok,msg=self.approve("window_control","Move/resize window",f"Move '{w.title}' to ({x},{y}), size {width}x{height}?")
   if not ok:return msg
   w.restore();w.moveTo(x,y);w.resizeTo(width,height)
   return "Requested new position for '"+w.title+"'."
  except Exception as e:return "Window positioning unavailable: "+str(e)
 def gui(self):
  import pyautogui
  pyautogui.FAILSAFE=True;pyautogui.PAUSE=.05
  return pyautogui
 def mouse(self,a,x,y):
  try:
   if not self.permissions.has("desktop_input"):return "Permission disabled. Use 'grant permission desktop input' first."
   ok,msg=self.approve("desktop_input","Mouse action",f"{a} at ({x},{y})?")
   if not ok:return msg
   g=self.gui();w,h=g.size()
   if not(0<=x<w and 0<=y<h):return "Coordinates must be inside the reported screen (%dx%d)."%(w,h)
   {"click":lambda:g.click(x,y),"double click":lambda:g.doubleClick(x,y),"right click":lambda:g.rightClick(x,y),"move":lambda:g.moveTo(x,y,duration=.15)}[a]()
   return "Mouse "+a+" action sent."
  except Exception as e:return "Mouse action failed safely: "+str(e)
 def scroll(self,n):
  if n==0 or abs(n)>20:return "Scroll amount must be 1–20 units in either direction."
  try:
   if not self.permissions.has("desktop_input"):return "Permission disabled. Use 'grant permission desktop input' first."
   ok,msg=self.approve("desktop_input","Scroll",f"Scroll {n} units in foreground window?")
   if not ok:return msg
   g=self.gui();g.scroll(n);return "Scroll action sent."
  except Exception as e:return "Scroll failed safely: "+str(e)
 def drag(self,x1,y1,x2,y2):
  try:
   if not self.permissions.has("desktop_input"):return "Permission disabled. Use 'grant permission desktop input' first."
   ok,msg=self.approve("desktop_input","Mouse drag",f"Drag from ({x1},{y1}) to ({x2},{y2})?")
   if not ok:return msg
   g=self.gui();w,h=g.size()
   if not all(0<=x<w and 0<=y<h for x,y in ((x1,y1),(x2,y2))):return "Drag coordinates are outside screen."
   g.moveTo(x1,y1);g.dragTo(x2,y2,duration=.4);return "Drag action sent."
  except Exception as e:return "Drag failed safely: "+str(e)
 def type_text(self,text):
  if not text or len(text)>1000 or "\n" in text or "\r" in text or any(ord(c)<32 and c!="\t" for c in text):return "Text must be 1–1,000 single-line characters."
  try:
   if not self.permissions.has("desktop_input"):return "Permission disabled. Use 'grant permission desktop input' first."
   ok,msg=self.approve("desktop_input","Type text","Type literal text in foreground app?\n\n"+text[:500]+"\n\nJARVIS will not press Enter.")
   if not ok:return msg
   g=self.gui();g.write(text,interval=.01);return "Typed %d characters; Enter was not pressed."%len(text)
  except Exception as e:return "Typing failed safely: "+str(e)
 def hotkey(self,value):
  allowed={"ctrl+c":("ctrl","c"),"ctrl+v":("ctrl","v"),"ctrl+x":("ctrl","x"),"ctrl+a":("ctrl","a"),"ctrl+z":("ctrl","z"),"ctrl+y":("ctrl","y"),"ctrl+s":("ctrl","s"),"ctrl+f":("ctrl","f"),"ctrl+p":("ctrl","p"),"ctrl+tab":("ctrl","tab"),"ctrl+shift+tab":("ctrl","shift","tab"),"alt+tab":("alt","tab"),"shift+tab":("shift","tab"),"win+d":("win","d"),"win+e":("win","e")}
  key="+".join(x.strip().casefold() for x in value.split("+"))
  if key not in allowed:return "Hotkey blocked. Allowed: "+", ".join(sorted(allowed))
  try:
   if not self.permissions.has("desktop_input"):return "Permission disabled. Use 'grant permission desktop input' first."
   ok,msg=self.approve("desktop_input","Keyboard shortcut","Send "+key+" to foreground app?")
   if not ok:return msg
   g=self.gui();g.hotkey(*allowed[key]);return "Sent hotkey "+key+"."
  except Exception as e:return "Hotkey failed safely: "+str(e)
 def press_key(self,value):
  allowed={"enter","tab","esc","escape","space","backspace","delete","up","down","left","right","home","end","pageup","pagedown","f5"};key=value.casefold()
  if key not in allowed:return "Key blocked. Allowed: "+", ".join(sorted(allowed))
  if key=="escape":key="esc"
  try:
   if not self.permissions.has("desktop_input"):return "Permission disabled. Use 'grant permission desktop input' first."
   ok,msg=self.approve("desktop_input","Press key","Press "+key+" in foreground app?")
   if not ok:return msg
   g=self.gui();g.press(key);return "Pressed "+key+"."
  except Exception as e:return "Key press failed safely: "+str(e)
 def settings(self,page):
  if platform.system()!="Windows":return "Settings shortcuts require Windows 10/11."
  uri={"wifi":"ms-settings:network-wifi","wi-fi":"ms-settings:network-wifi","network":"ms-settings:network","bluetooth":"ms-settings:bluetooth","display":"ms-settings:display","sound":"ms-settings:sound","brightness":"ms-settings:display","power":"ms-settings:powersleep"}[page]
  ok,msg=self.approve("system_settings","Open Windows settings","Open "+page+" settings? JARVIS will not toggle settings automatically.")
  if not ok:return msg
  try:os.startfile(uri);return "Opened Windows settings: "+page+". Change it manually."
  except Exception as e:return "Could not open settings: "+str(e)
 def volume(self,action):
  try:
   if not self.permissions.has("system_settings"):return "Permission disabled. Use 'grant permission system settings' first."
   ok,msg=self.approve("system_settings","System volume","Send volume "+action+" key?")
   if not ok:return msg
   g=self.gui();g.press({"up":"volumeup","down":"volumedown","mute":"volumemute"}[action]);return "Sent volume "+action+" key."
  except Exception as e:return "Volume control unavailable: "+str(e)
 def power(self,action):
  action="logout" if action=="log out" else action
  ok,msg=self.approve("system_power","System power action","Request "+action.upper()+"? Save work first.")
  if not ok:return msg
  if platform.system()!="Windows":return "Power actions require Windows 10/11."
  try:
   if action=="sleep":
    import ctypes
    ctypes.windll.powrprof.SetSuspendState(False,True,False);return "Sent Windows sleep request."
   args={"shutdown":["shutdown","/s","/t","10"],"restart":["shutdown","/r","/t","10"],"logout":["shutdown","/l"]}[action]
   r=subprocess.run(args,capture_output=True,text=True,timeout=5,check=False)
   if r.returncode:return "Windows rejected request: "+(r.stderr or r.stdout or str(r.returncode))[:400]
   return "Windows "+action+" requested. Shutdown/restart can be cancelled with shutdown /a during the 10-second delay."
  except Exception as e:return "Power request failed: "+str(e)
