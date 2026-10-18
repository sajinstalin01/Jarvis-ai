"""Unified J.A.R.V.I.S. desktop assistant: original dashboard + V2 voice/app/WhatsApp features."""
from __future__ import annotations
import ast, datetime, json, operator, os, platform, queue, shutil, socket, subprocess, threading, time, urllib.parse, webbrowser
from functools import lru_cache
from pathlib import Path
from tkinter import messagebox
from jarvis_services import JarvisStore, system_metrics, developer_diagnostics, parse_reminder_command
from jarvis_ai import generate_response
from jarvis_control import lock_screen, take_screenshot, toggle_mute
from jarvis_remote import JarvisRemoteServer
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
CYAN, BG, PANEL, GREEN, MUTED = "#67E8D5", "#07111F", "#0D1B2A", "#8BE3B0", "#91A5BA"
ACCENT, BORDER, PANEL_ALT, TEXT = "#86A8FF", "#20384D", "#0A1725", "#E8F0F7"
GOLD = "#E6BE78"

# App aliases are deliberately allow-listed. Values are candidate executable names or paths.
@lru_cache(maxsize=1)
def _start_menu_shortcuts():
    """Index installed Windows Start Menu shortcuts once; exact-name matching only."""
    if platform.system() != "Windows":
        return {}
    roots = [
        Path(os.getenv("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
        Path(os.getenv("PROGRAMDATA", r"C:\ProgramData")) / "Microsoft/Windows/Start Menu/Programs",
    ]
    index = {}
    for root in roots:
        try:
            for shortcut in root.rglob("*.lnk"):
                normalized = "".join(ch for ch in shortcut.stem.casefold() if ch.isalnum())
                if normalized and normalized not in index:
                    index[normalized] = shortcut
        except (OSError, PermissionError):
            continue
    return index


@lru_cache(maxsize=1)
def _start_apps_index():
    """Read Windows' registered Start Apps, including packaged Store apps.

    Store apps frequently have no ordinary executable on PATH and may not
    expose a .lnk file. Get-StartApps returns their display name and AppUserModel
    ID, which Explorer can launch through the AppsFolder namespace.
    """
    if platform.system() != "Windows":
        return []
    command = (
        "Get-StartApps | Select-Object Name, AppID | ConvertTo-Json -Compress"
    )
    try:
        powershell = shutil.which("powershell.exe") or "powershell.exe"
        options = {}
        no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if no_window:
            options["creationflags"] = no_window
        result = subprocess.run(
            [powershell, "-NoProfile", "-NonInteractive", "-Command", command],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            timeout=12, check=False, **options
        )
        if result.returncode != 0 or not result.stdout.strip():
            return []
        payload = json.loads(result.stdout.lstrip(chr(0xfeff)))
        rows = payload if isinstance(payload, list) else [payload]
        found = []
        seen = set()
        for row in rows:
            if not isinstance(row, dict):
                continue
            display = str(row.get("Name") or "").strip()
            app_id = str(row.get("AppID") or "").strip()
            if display and app_id and app_id.casefold() not in seen:
                found.append((display, app_id))
                seen.add(app_id.casefold())
        return found
    except (OSError, subprocess.SubprocessError, ValueError, TypeError):
        return []


def _find_store_app_id(name, candidates=()):
    """Resolve an app name/alias to a unique registered Windows Store AppID."""
    if platform.system() != "Windows":
        return None
    requested = str(name or "").strip()
    if not requested:
        return None

    names = [requested]
    for candidate in candidates:
        stem = Path(str(candidate).replace("\\", "/")).stem
        if stem and stem.casefold() not in {"exe", "msc", "cpl"}:
            names.append(stem)

    candidate_set = {str(item).casefold() for item in candidates}
    for alias, values in APP_ALIASES.items():
        if candidate_set.intersection(str(item).casefold() for item in values):
            names.append(alias)

    # Preserve order while eliminating equivalent names.
    unique_names = []
    seen_names = set()
    for item in names:
        key = _normalize_app_name(item)
        if key and key not in seen_names:
            unique_names.append((item, key))
            seen_names.add(key)

    records = _start_apps_index()
    if not records:
        return None

    # An exact registered name has priority over substring matching.
    for _name, key in unique_names:
        matches = {app_id for display, app_id in records
                   if _normalize_app_name(display) == key}
        if len(matches) == 1:
            return next(iter(matches))
        if len(matches) > 1:
            return None

    # Accept versioned/product suffixes only if the result is unambiguous.
    for _name, key in unique_names:
        if len(key) < 4:
            continue
        matches = {app_id for display, app_id in records
                   if key in _normalize_app_name(display)
                   or _normalize_app_name(display) in key}
        if len(matches) == 1:
            return next(iter(matches))
        if len(matches) > 1:
            return None
    return None


def _launch_store_app(app_id):
    """Ask Explorer to activate a registered app using its AppUserModel ID."""
    if platform.system() != "Windows" or not str(app_id or "").strip():
        return False
    app_id = str(app_id).strip()
    # AppIDs are returned by Get-StartApps, not interpolated from user input.
    subprocess.Popen(
        ["explorer.exe", "shell:AppsFolder\\" + app_id],
        shell=False
    )
    return True


def find_start_menu_shortcut(name):
    normalized = "".join(ch for ch in name.casefold() if ch.isalnum())
    return _start_menu_shortcuts().get(normalized)


APP_ALIASES = {
    # Common short names
    "calc": ("calc.exe",), "files": ("explorer.exe",), "tm": ("taskmgr.exe",),
    "taskmgr": ("taskmgr.exe",), "ps": ("powershell.exe",), "wt": ("wt.exe", "WindowsTerminal.exe"),
    "code": ("Code.exe", "code"), "vs code": ("Code.exe", "code"),
    "studio": ("studio64.exe", "studio"), "androidstudio": ("studio64.exe", "studio"),
    "ff": ("firefox.exe", "firefox"), "wa": ("WhatsApp.exe", "WhatsApp"),
    "tg": ("Telegram.exe", "telegram"), "sp": ("Spotify.exe", "spotify"),
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
    # Additional productivity, AI and creative applications; installed Store apps
    # still use the Start Menu shortcut fallback when the executable is unknown.
    "word": ("WINWORD.EXE",), "microsoft word": ("WINWORD.EXE",),
    "excel": ("EXCEL.EXE",), "microsoft excel": ("EXCEL.EXE",),
    "powerpoint": ("POWERPNT.EXE",), "microsoft powerpoint": ("POWERPNT.EXE",),
    "outlook": ("OUTLOOK.EXE",), "microsoft outlook": ("OUTLOOK.EXE",),
    "onenote": ("ONENOTE.EXE",), "microsoft onenote": ("ONENOTE.EXE",),
    "access": ("MSACCESS.EXE",), "microsoft access": ("MSACCESS.EXE",),
    "acrobat": ("Acrobat.exe",), "adobe acrobat": ("Acrobat.exe",),
    "illustrator": ("Illustrator.exe",), "adobe illustrator": ("Illustrator.exe",),
    "lightroom": ("Lightroom.exe",), "adobe lightroom": ("Lightroom.exe",),
    "indesign": ("InDesign.exe",), "adobe indesign": ("InDesign.exe",),
    "creative cloud": ("Creative Cloud.exe",), "adobe creative cloud": ("Creative Cloud.exe",),
    "chatgpt": ("ChatGPT.exe", "chatgpt"), "openai chatgpt": ("ChatGPT.exe", "chatgpt"),
    "copilot": ("Copilot.exe", "copilot"), "microsoft copilot": ("Copilot.exe", "copilot"),
    "capcut": ("CapCut.exe", "CapCut"),
    "canva": ("Canva.exe", "Canva"),
    "krita": ("krita.exe", "krita"), "inkscape": ("inkscape.exe", "inkscape"),
    "shotcut": ("shotcut.exe", "shotcut"), "kdenlive": ("kdenlive.exe", "kdenlive"),
    "bluestacks": ("HD-Player.exe", "BlueStacks"), "ldplayer": ("dnplayer.exe", "LDPlayer"),
}
def _normalize_app_name(value):
    """Normalize names so 'VS Code', 'vs-code', and 'VSCode' match."""
    return "".join(ch for ch in str(value).casefold() if ch.isalnum())


def _find_installed_shortcut(name, candidates=()):
    """Find an exact Start Menu shortcut, then a unique safe partial match."""
    if platform.system() != "Windows":
        return None
    names = [name]
    normalized = _normalize_app_name(name)
    # Try human-friendly names derived from the allow-listed executable names.
    for candidate in candidates:
        stem = Path(str(candidate).replace("\\", "/")).stem
        if stem and stem.casefold() not in {"exe", "msc", "cpl"}:
            names.append(stem)
    # Include aliases sharing one of the same known executable candidates.
    candidate_set = {str(x).casefold() for x in candidates}
    for alias, values in APP_ALIASES.items():
        if candidate_set.intersection(str(x).casefold() for x in values):
            names.append(alias)
    index = _start_menu_shortcuts()
    for item in names:
        key = _normalize_app_name(item)
        if key and key in index:
            return index[key]
    # Partial matching is allowed only when it identifies exactly one shortcut.
    # This supports versioned shortcuts such as "Adobe Photoshop 2025".
    if len(normalized) >= 4:
        matches = {
            path for label, path in index.items()
            if normalized in label or label in normalized
        }
        if len(matches) == 1:
            return next(iter(matches))
    return None


def launch_app(name, search_query=None):
    """Launch an allow-listed app with robust Windows Start Menu fallbacks."""
    requested = str(name or "").strip()
    if not requested:
        return False, "Enter an app name. Example: launch chrome"

    key = requested.casefold().strip()
    normalized_key = _normalize_app_name(requested)
    if normalized_key == "whatsapp":
        key = "whatsapp desktop"

    # Keep aliases allow-listed while accepting punctuation/capitalization variants.
    candidates = APP_ALIASES.get(key)
    if not candidates:
        candidates = next(
            (values for alias, values in APP_ALIASES.items()
             if _normalize_app_name(alias) == normalized_key),
            None,
        )

    search_url = (
        "https://www.google.com/search?q=" + urllib.parse.quote(str(search_query).strip())
        if search_query and str(search_query).strip() else None
    )
    browser_keys = {
        "chrome", "googlechrome", "edge", "microsoftedge", "firefox",
        "brave", "opera", "vivaldi", "arc",
    }
    if search_url and normalized_key not in browser_keys:
        return False, "Search syntax is for browsers. Try: launch chrome search git"

    if platform.system() == "Windows":
        # Prefer the actual installed Start Menu shortcut for Store apps,
        # versioned applications, and apps whose executable is not on PATH.
        shortcut = _find_installed_shortcut(requested, candidates or ())
        if shortcut:
            try:
                os.startfile(str(shortcut))
                if search_url:
                    # Open the search separately; this works for both classic and Store browsers.
                    webbrowser.open(search_url)
                return True, f"Launching installed app '{shortcut.stem}'." + (
                    f" Searching for '{search_query}'." if search_url else ""
                )
            except OSError as exc:
                shortcut_error = str(exc)
            else:
                shortcut_error = ""
        else:
            shortcut_error = ""

        # If there was no usable Start Menu shortcut, ask Windows for the
        # registered AppID. This is the missing path for Microsoft Store apps
        # such as WhatsApp and Telegram Desktop, whose binaries aren't on PATH.
        store_app_id = _find_store_app_id(requested, candidates or ())
        if store_app_id:
            try:
                _launch_store_app(store_app_id)
                if search_url:
                    webbrowser.open(search_url)
                return True, f"Launching installed Store app '{requested}'."
            except (OSError, subprocess.SubprocessError) as exc:
                shortcut_error = (shortcut_error + "; " if shortcut_error else "") + (
                    f"Store activation failed: {exc}"
                )

        if candidates:
            for candidate in candidates:
                expanded = os.path.expandvars(str(candidate))
                try:
                    if expanded.endswith(":") or expanded.endswith("://"):
                        os.startfile(expanded)
                        return True, f"Opening {requested}."
                    if expanded.lower().endswith(".msc"):
                        if os.path.isfile(expanded):
                            os.startfile(expanded)
                        else:
                            subprocess.Popen(["mmc.exe", expanded], shell=False)
                        return True, f"Opening {requested}."
                    if expanded.lower().endswith(".cpl"):
                        subprocess.Popen(["control.exe", expanded], shell=False)
                        return True, f"Opening {requested}."
                    resolved = expanded if os.path.isfile(expanded) else shutil.which(expanded)
                    if resolved:
                        args = [resolved]
                        if search_url:
                            args.append(search_url)
                        subprocess.Popen(args, shell=False)
                        return True, (
                            f"Launching {requested} and searching for '{search_query}'."
                            if search_url else f"Launching {requested}."
                        )
                except (OSError, subprocess.SubprocessError) as exc:
                    shortcut_error = str(exc)

        # Try the Start Menu even when an alias exists but its executable name
        # cannot be resolved. This is the common failure for packaged apps.
        if not shortcut:
            shortcut = _find_installed_shortcut(requested, candidates or ())
            if shortcut:
                try:
                    os.startfile(str(shortcut))
                    if search_url:
                        webbrowser.open(search_url)
                    return True, f"Launching installed app '{shortcut.stem}'."
                except OSError as exc:
                    shortcut_error = str(exc)

        if candidates:
            # Fixed allow-listed targets only; never pass arbitrary user commands.
            target = str(candidates[0])
            try:
                if target.lower().endswith(".msc"):
                    subprocess.Popen(["mmc.exe", target], shell=False)
                elif target.lower().endswith(".cpl"):
                    subprocess.Popen(["control.exe", target], shell=False)
                else:
                    # Do not report success merely because cmd.exe accepted
                    # "start WhatsApp.exe". Windows start is asynchronous and
                    # can return zero even when no application was found.
                    details = []
                    if shortcut_error:
                        details.append(shortcut_error)
                    details.append("no executable or Start Menu shortcut was found")
                    return False, (
                        f"Could not launch '{requested}': " + "; ".join(details) +
                        ". For Microsoft Store apps, verify that the app is installed "
                        "for this Windows account, then try the exact Start Menu name."
                    )
                return True, f"Opening {requested}."
            except (OSError, subprocess.SubprocessError) as exc:
                detail = f" {exc}"
                if shortcut_error:
                    detail += f" (Start Menu: {shortcut_error})"
                return False, f"Couldn't launch {requested}.{detail}"

        return False, (
            f"'{requested}' was not found in JARVIS shortcuts or the Windows Start Menu. "
            "Install it or add an alias."
        )

    # Non-Windows launchers use their platform-native application names.
    if not candidates:
        shortcut = find_start_menu_shortcut(requested)
        if shortcut:
            try:
                os.startfile(str(shortcut))
                return True, f"Launching installed app '{shortcut.stem}'."
            except (AttributeError, OSError) as exc:
                return False, f"Couldn't launch '{requested}': {exc}"
        return False, f"'{requested}' is not in the supported app list."

    try:
        if key == "settings" or normalized_key == "settings":
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
            normalized_aliases = {_normalize_app_name(k): v for k, v in aliases.items()}
            command = ["open", "-a", normalized_aliases.get(normalized_key, target)]
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
            normalized_aliases = {_normalize_app_name(k): v for k, v in aliases.items()}
            cmd = normalized_aliases.get(normalized_key, target)
            if not shutil.which(cmd):
                return False, f"{cmd} was not found. Install it or update the app alias."
            args = [cmd]
            if normalized_key == "fileexplorer":
                args.append(str(Path.home()))
            elif search_url:
                args.append(search_url)
            subprocess.Popen(args)
        return True, (
            f"Launching {requested} and searching for '{search_query}'."
            if search_url else f"Launching {requested}."
        )
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        return False, f"Couldn't launch {requested}: {exc}"

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
        ctk.set_appearance_mode("dark"); ctk.set_default_color_theme("dark-blue")
        self.title("J.A.R.V.I.S. // Unified Stark Desktop"); self.geometry("1440x900"); self.minsize(1080,720); self.configure(fg_color=BG)
        self.events=queue.Queue(); self.busy=False; self.sound=True; self.sr=None; self.tts=None
        self.voice_chat_active=False; self.voice_chat_stop=threading.Event(); self.voice_chat_ready=threading.Event(); self.voice_chat_ready.set()
        self.store=JarvisStore()
        self.remote=JarvisRemoteServer(self.remote_command, self.remote_status)
        self.wake_enabled=False; self.wake_stop=threading.Event(); self.wake_thread=None; self.voice_chat_thread=None
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
        side=ctk.CTkFrame(self,width=220,corner_radius=0,fg_color="#091522",border_width=1,border_color=BORDER)
        side.grid(row=0,column=0,sticky="nsew"); side.grid_propagate(False)
        ctk.CTkLabel(side,text="J.A.R.V.I.S.",font=ctk.CTkFont(size=26,weight="bold"),text_color=CYAN).pack(anchor="w",padx=18,pady=(26,2))
        ctk.CTkLabel(side,text="PERSONAL INTELLIGENCE SYSTEM",font=ctk.CTkFont(size=10,weight="bold"),text_color=MUTED).pack(anchor="w",padx=20,pady=(0,24))
        for label,fn in [
            ("◈  Dashboard",lambda:self.add("SYSTEM","Dashboard online.")),
            ("✧  AI Assistant",lambda:self.entry.focus_set()),
            ("▤  PC Monitor",lambda:self.open_feature_window("monitor")),
            ("⌁  PC Control",self.open_pc_control_window),
            ("◷  Memory & History",lambda:self.open_feature_window("memory")),
            ("◉  Reminders",lambda:self.open_feature_window("reminders")),
            ("⌘  Workflows",lambda:self.open_feature_window("workflows")),
            ("</>  Developer Mode",lambda:self.open_feature_window("developer")),
            ("◎  Remote Control",self.remote_control_setup),
            ("◉  WhatsApp",lambda:self.launch_shortcut("WhatsApp")),
            ("⚙  Settings",self.show_settings)]:
            ctk.CTkButton(side,text=label,command=fn,anchor="w",height=42,corner_radius=10,fg_color="transparent",hover_color="#183248",text_color=TEXT).pack(fill="x",padx=12,pady=4)
        ctk.CTkFrame(side,height=1,fg_color=BORDER).pack(fill="x",padx=14,pady=(20,14))
        ctk.CTkLabel(side,text="CORE STATUS",font=ctk.CTkFont(size=11,weight="bold"),text_color=MUTED).pack(anchor="w",padx=18)
        self.core=ctk.CTkLabel(side,text="● INITIALIZING",text_color=GOLD); self.core.pack(anchor="w",padx=18,pady=(8,4))
        self.ai_status=ctk.CTkLabel(side,text="● AI: CHECKING",text_color=MUTED); self.ai_status.pack(anchor="w",padx=18,pady=4)
        self.groq_status=ctk.CTkLabel(side,text="● GROQ: WAITING",text_color=MUTED); self.groq_status.pack(anchor="w",padx=18,pady=4)
        self.gemini_status=ctk.CTkLabel(side,text="● GEMINI: WAITING",text_color=MUTED); self.gemini_status.pack(anchor="w",padx=18,pady=4)
        ctk.CTkFrame(side,height=1,fg_color=BORDER).pack(fill="x",padx=14,pady=(14,10))
        ctk.CTkLabel(side,text="QUICK STATUS",font=ctk.CTkFont(size=11,weight="bold"),text_color=MUTED).pack(anchor="w",padx=18,pady=(0,5))
        ctk.CTkLabel(side,text="AI providers\nGroq → Gemini fallback\nKeys stay in local .env",justify="left",text_color="#71879C",font=ctk.CTkFont(size=10)).pack(anchor="w",padx=18)
        ctk.CTkLabel(side,text="ALLOW-LISTED APP CONTROL\nWhatsApp sending stays manual.",justify="left",text_color="#71879C",font=ctk.CTkFont(size=10)).pack(side="bottom",anchor="w",padx=18,pady=20)
        main=ctk.CTkFrame(self,fg_color=BG,corner_radius=0); main.grid(row=0,column=1,sticky="nsew",padx=18,pady=16); main.grid_columnconfigure(0,weight=1); main.grid_rowconfigure(1,weight=1)
        head=ctk.CTkFrame(main,fg_color="transparent"); head.grid(row=0,column=0,sticky="ew",pady=(0,12))
        ctk.CTkLabel(head,text="J.A.R.V.I.S.  /  PERSONAL INTELLIGENCE SYSTEM",text_color=MUTED,font=ctk.CTkFont(size=11,weight="bold")).pack(side="left")
        self.date=ctk.CTkLabel(head,text="",text_color=MUTED,font=ctk.CTkFont(size=11)); self.date.pack(side="right",padx=10)
        self.clock=ctk.CTkLabel(head,text="",text_color=CYAN,font=ctk.CTkFont(size=17,weight="bold")); self.clock.pack(side="right")
        body=ctk.CTkFrame(main,fg_color="transparent"); body.grid(row=1,column=0,sticky="nsew"); body.grid_columnconfigure(0,weight=2); body.grid_columnconfigure(1,weight=1); body.grid_rowconfigure(1,weight=1)
        hero=ctk.CTkFrame(body,fg_color=PANEL,border_width=1,border_color=BORDER,corner_radius=18); hero.grid(row=0,column=0,columnspan=2,sticky="ew",pady=(0,14)); hero.grid_columnconfigure(1,weight=1)
        self.reactor=ctk.CTkCanvas(hero,width=140,height=140,bg=PANEL,highlightthickness=0); self.reactor.grid(row=0,column=0,padx=(18,6),pady=12); self.draw_reactor()
        ht=ctk.CTkFrame(hero,fg_color="transparent"); ht.grid(row=0,column=1,sticky="w",padx=18,pady=20)
        ctk.CTkLabel(ht,text="YOUR PERSONAL INTELLIGENCE, READY.",text_color=TEXT,font=ctk.CTkFont(size=25,weight="bold")).pack(anchor="w")
        ctk.CTkLabel(ht,text="Context-aware AI • Desktop telemetry • Voice interface",text_color=MUTED,font=ctk.CTkFont(size=13)).pack(anchor="w",pady=(5,12))
        ctk.CTkLabel(ht,text="● SYSTEM ONLINE  /  MEMORY ACTIVE",text_color=GREEN,fg_color="#12352F",corner_radius=8,font=ctk.CTkFont(size=11,weight="bold"),padx=12,pady=6).pack(anchor="w")
        chat=ctk.CTkFrame(body,fg_color=PANEL,border_width=1,border_color=BORDER,corner_radius=16); chat.grid(row=1,column=0,sticky="nsew",padx=(0,12)); chat.grid_columnconfigure(0,weight=1); chat.grid_rowconfigure(1,weight=1)
        ch=ctk.CTkFrame(chat,fg_color="transparent"); ch.grid(row=0,column=0,sticky="ew",padx=16,pady=(13,5))
        ctk.CTkLabel(ch,text="✧ JARVIS CONSOLE",text_color=CYAN,font=ctk.CTkFont(size=14,weight="bold")).pack(side="left")
        ctk.CTkButton(ch,text="CLEAR",width=60,height=26,command=self.clear_chat,fg_color="#13283A").pack(side="right")
        self.chat=ctk.CTkTextbox(chat,fg_color="#07131F",text_color=TEXT,border_width=1,border_color=BORDER,corner_radius=10,wrap="word",font=ctk.CTkFont(size=13)); self.chat.grid(row=1,column=0,sticky="nsew",padx=14,pady=8); self.chat.configure(state="disabled")
        bar=ctk.CTkFrame(chat,fg_color="transparent"); bar.grid(row=2,column=0,sticky="ew",padx=14,pady=(4,14)); bar.grid_columnconfigure(0,weight=1)
        self.entry=ctk.CTkEntry(bar,placeholder_text="Continue the conversation…",height=44,fg_color=PANEL_ALT,border_color=BORDER); self.entry.grid(row=0,column=0,sticky="ew",padx=(0,7)); self.entry.bind("<Return>",lambda _e:self.send())
        ctk.CTkButton(bar,text="🎙",width=44,height=44,command=self.listen,fg_color="#183B50",hover_color="#23455C").grid(row=0,column=1,padx=3)
        self.voice_chat_btn=ctk.CTkButton(bar,text="VOICE CHAT: OFF",width=112,height=44,command=self.toggle_voice_chat,fg_color="#183B50",hover_color="#23455C"); self.voice_chat_btn.grid(row=0,column=2,padx=3)
        self.wake_btn=ctk.CTkButton(bar,text="WAKE: OFF",width=86,height=44,command=self.toggle_wake_word,fg_color="#183B50"); self.wake_btn.grid(row=0,column=3,padx=3)
        self.sound_btn=ctk.CTkButton(bar,text="SOUND ON",width=64,height=44,command=self.toggle_sound,fg_color="#183B50"); self.sound_btn.grid(row=0,column=4,padx=3)
        self.send_btn=ctk.CTkButton(bar,text="SEND ➤",width=84,height=44,command=self.send,fg_color="#167F89",hover_color="#209CA0"); self.send_btn.grid(row=0,column=5,padx=(3,0))
        right=ctk.CTkFrame(body,fg_color="transparent"); right.grid(row=1,column=1,sticky="nsew"); right.grid_columnconfigure(0,weight=1)
        tele=ctk.CTkFrame(right,fg_color=PANEL,border_width=1,border_color=BORDER,corner_radius=16); tele.grid(row=0,column=0,sticky="ew",pady=(0,12))
        ctk.CTkLabel(tele,text="SYSTEM TELEMETRY",text_color=CYAN,font=ctk.CTkFont(size=13,weight="bold")).pack(anchor="w",padx=16,pady=(15,10))
        self.telemetry=ctk.CTkLabel(tele,text="Loading…",justify="left",text_color="#C3D2DF",font=ctk.CTkFont(size=12)); self.telemetry.pack(anchor="w",padx=16,pady=(0,16))
        actions=ctk.CTkFrame(right,fg_color=PANEL,border_width=1,border_color=BORDER,corner_radius=16); actions.grid(row=1,column=0,sticky="ew"); actions.grid_columnconfigure((0,1),weight=1)
        ctk.CTkLabel(actions,text="QUICK ACTIONS",text_color=CYAN,font=ctk.CTkFont(size=13,weight="bold")).grid(row=0,column=0,columnspan=2,sticky="w",padx=16,pady=(15,9))
        for i,(label,url) in enumerate([("Open YouTube","https://youtube.com"),("Open Google","https://google.com"),("Open GitHub","https://github.com/sajinstalin01/Jarvis-ai"),("Open Gmail","https://mail.google.com")]):
            ctk.CTkButton(actions,text=label,height=36,fg_color="#13283A",hover_color="#23455C",anchor="w",command=lambda u=url:self.open_url(u)).grid(row=1+i//2,column=i%2,sticky="ew",padx=7,pady=5)
        ctk.CTkLabel(actions,text="Browser shortcuts use your default browser.",text_color="#71879C",font=ctk.CTkFont(size=10)).grid(row=3,column=0,columnspan=2,padx=12,pady=(8,13),sticky="w")
        apps=ctk.CTkFrame(right,fg_color=PANEL,border_width=1,border_color=BORDER,corner_radius=16)
        apps.grid(row=2,column=0,sticky="ew",pady=(12,0)); apps.grid_columnconfigure((0,1),weight=1)
        ctk.CTkLabel(apps,text="APP SHORTCUTS",text_color=CYAN,font=ctk.CTkFont(size=13,weight="bold")).grid(row=0,column=0,columnspan=2,sticky="w",padx=16,pady=(13,8))
        for i,name in enumerate(("Notepad","Calculator","File Explorer","Task Manager","Snipping Tool","PowerShell","Chrome","VS Code","Android Studio","VLC","Discord","Telegram","Spotify","WhatsApp","Windows Security","Settings","Zoom","Notion")):
            ctk.CTkButton(apps,text=name,height=31,fg_color="#13283A",hover_color="#23455C",
                          command=lambda n=name:self.launch_shortcut(n)).grid(row=1+i//2,column=i%2,sticky="ew",padx=6,pady=3)
        ctk.CTkLabel(apps,text="More: launch <app name> • Some shortcuts require installation.",text_color="#71879C",font=ctk.CTkFont(size=10)).grid(row=10,column=0,columnspan=2,padx=12,pady=(7,12),sticky="w")
        ctk.CTkLabel(main,text="JARVIS // UNIFIED PYTHON EDITION",text_color="#647B91",font=ctk.CTkFont(size=10)).grid(row=2,column=0,sticky="ew",pady=(10,0))

    def draw_reactor(self):
        import math
        c=self.reactor
        c.create_oval(12,12,128,128,outline="#1E4054",width=2)
        c.create_oval(22,22,118,118,outline=CYAN,width=2)
        c.create_oval(32,32,108,108,outline="#2B9A9A",width=1)
        c.create_oval(43,43,97,97,fill="#103044",outline=CYAN,width=2)
        c.create_oval(52,52,88,88,fill="#3AAFA9",outline=CYAN,width=2)
        c.create_oval(62,62,78,78,fill=TEXT,outline="")
        for a in range(0,360,30):
            x1,y1=70+48*math.cos(math.radians(a)),70+48*math.sin(math.radians(a))
            x2,y2=70+56*math.cos(math.radians(a)),70+56*math.sin(math.radians(a))
            c.create_line(x1,y1,x2,y2,fill=CYAN if a%60==0 else "#356277",width=2)
        self.reactor_arc=c.create_arc(15,15,125,125,start=0,extent=72,style="arc",outline=GOLD,width=3)
        self.reactor_tick=0
    def splash(self):
        self.overlay=ctk.CTkFrame(self,fg_color="#050D17",corner_radius=0); self.overlay.place(relx=0,rely=0,relwidth=1,relheight=1)
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
        try:
            self.reactor_tick=(self.reactor_tick+12)%360
            self.reactor.itemconfigure(self.reactor_arc,start=self.reactor_tick)
            pulse=CYAN if (self.reactor_tick//24)%2==0 else "#357D91"
            self.reactor.itemconfigure(5,outline=pulse)
            self.reactor.itemconfigure(6,fill="#3AAFA9" if pulse==CYAN else "#176176")
        except Exception:
            pass
        self.after(90,self.animate)
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
        self.sound=not self.sound; self.sound_btn.configure(text="SOUND ON" if self.sound else "SOUND OFF")
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
    def speak(self,msg,force=False,on_done=None):
        """Speak responses off the UI thread; voice-chat mode speaks every reply."""
        enabled = force or os.getenv("JARVIS_SPEAK_RESPONSES","false").lower()=="true"
        if not self.tts or not enabled:
            if on_done:on_done()
            return
        def work():
            try:
                self.tts.say(str(msg)[:1500])
                self.tts.runAndWait()
            except Exception:
                pass
            finally:
                if on_done:on_done()
        threading.Thread(target=work,name="JarvisSpeechOutput",daemon=True).start()

    def toggle_voice_chat(self):
        if self.wake_enabled:
            self.wake_enabled=False
            self.wake_stop.set()
            self.wake_btn.configure(text="WAKE: OFF",fg_color="#183B50")
        if not self.sr:
            self.add("SYSTEM","Real-time voice chat needs SpeechRecognition and a compatible PyAudio microphone installation.")
            return
        if not self.tts:
            self.add("SYSTEM","Voice chat needs pyttsx3 and an available Windows text-to-speech voice.")
            return
        self.voice_chat_active = not self.voice_chat_active
        if self.voice_chat_active:
            self.voice_chat_stop.clear()
            self.voice_chat_ready.set()
            self.voice_chat_btn.configure(text="VOICE CHAT: ON",fg_color="#176A51")
            self.add("SYSTEM","Voice chat active. Speak naturally after each reply; click VOICE CHAT: ON to stop. Speech recognition uses Google's cloud service.")
            self.voice_chat_thread=threading.Thread(target=self.voice_chat_loop,name="JarvisRealtimeVoiceChat",daemon=True)
            self.voice_chat_thread.start()
        else:
            self.voice_chat_stop.set()
            self.voice_chat_ready.set()
            self.voice_chat_btn.configure(text="VOICE CHAT: OFF",fg_color="#183B50")
            self.add("SYSTEM","Voice chat stopped.")

    def voice_chat_loop(self):
        recognizer=self.sr.Recognizer()
        recognizer.pause_threshold=0.65
        recognizer.non_speaking_duration=0.35
        while self.voice_chat_active and not self.voice_chat_stop.is_set():
            if not self.voice_chat_ready.wait(timeout=0.25):
                continue
            self.voice_chat_ready.clear()
            if self.busy:
                self.voice_chat_ready.set()
                time.sleep(0.2)
                continue
            try:
                with self.sr.Microphone() as source:
                    self.events.put(("status","VOICE CHAT • LISTENING"))
                    audio=recognizer.listen(source,timeout=3,phrase_time_limit=12)
                self.events.put(("status","VOICE CHAT • THINKING"))
                phrase=recognizer.recognize_google(audio).strip()
                if phrase:
                    self.events.put(("voice_chat_command",phrase))
                    # The UI sets voice_chat_ready only after the answer has been spoken.
                    continue
                self.voice_chat_ready.set()
            except self.sr.WaitTimeoutError:
                self.voice_chat_ready.set()
            except self.sr.UnknownValueError:
                self.voice_chat_ready.set()
            except self.sr.RequestError as exc:
                self.events.put(("answer",f"Voice recognition service unavailable: {exc}"))
                self.voice_chat_ready.wait(timeout=8)
                self.voice_chat_ready.set()
            except Exception as exc:
                if not self.voice_chat_stop.is_set():
                    self.events.put(("answer",f"Voice chat microphone error: {exc}"))
                    self.voice_chat_ready.wait(timeout=5)
                    self.voice_chat_ready.set()
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
        if p in ("pc status", "computer status", "pc monitor"):
            return self.remote_status_text()
        if p in ("pc lock", "lock pc", "lock screen", "lock computer"):
            ok, result = lock_screen()
            return result
        if p in ("pc mute", "mute computer", "toggle mute", "mute volume"):
            ok, result = toggle_mute()
            return result
        if p in ("pc screenshot", "take screenshot", "screenshot"):
            ok, result = take_screenshot()
            return result
        if p in ("pc shutdown", "shutdown pc", "shut down computer", "pc restart", "restart pc", "restart computer"):
            action = "restart" if "restart" in p else "shutdown"
            self.events.put(("pc_confirm", action))
            return f"Please confirm the {action} request in the JARVIS desktop window. If approved, Windows schedules it in 10 seconds."
        if p in ("help","commands","what can you do"):
            return """Commands:
• help, time, date, system info
• calculate <math expression>; search <query>; open YouTube/Google/GitHub/Gmail/Wikipedia
• launch <app name>; launch chrome search git
• pc status, pc lock, pc mute, pc screenshot
• pc shutdown / pc restart (requires desktop confirmation)
• ◎ Remote Control: start/stop an authenticated allow-listed API
• remember <text>, memories [search], forget memory <id>, history [search]
• remind me in 10 minutes to <task>; remind me daily/weekly to <task>; reminders; delete reminder <id>
• workflow save <name>: launch chrome; open github; workflow list/run/delete <name>
• dev diagnostics, dev test, dev git status
• click WAKE: OFF to enable optional wake-word mode; say 'Hey JARVIS'
• click VOICE CHAT: OFF for continuous turn-by-turn spoken conversation
• conversation context and saved memories are supplied to AI for relevant follow-ups
• ask a question for Groq/Gemini AI
API keys stay in your local .env. Wake-word recognition uses the configured speech recognition service."""
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
            import subprocess, sys
            try:
                result=subprocess.run([sys.executable,"-m","unittest","discover","-s","tests","-v"],cwd=ROOT,capture_output=True,text=True,timeout=60)
                output=(result.stdout+"\n"+result.stderr).strip()
                return ("Tests passed.\n" if result.returncode==0 else "Tests failed.\n")+output[-5000:]
            except Exception as exc:return f"Could not run tests: {exc}"
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
        """Answer with recent dialogue and persistent user memories for natural follow-ups."""
        try:
            rows=self.store.search_history("",limit=20)
            # The current user message was saved before the request starts; do not duplicate it.
            if rows and rows[0].get("speaker")=="BOSS" and rows[0].get("content")==prompt:
                rows=rows[1:]
            dialogue=[]
            for row in reversed(rows):
                speaker=row.get("speaker","")
                if speaker=="BOSS":
                    dialogue.append({"role":"user","content":row.get("content","")})
                elif speaker=="J.A.R.V.I.S.":
                    dialogue.append({"role":"assistant","content":row.get("content","")})
            memories=self.store.list_memories(limit=8)
            memory_text="\n".join(f"- {item['content']}" for item in memories)
            answer, provider = generate_response(prompt,context=dialogue[-16:],saved_memories=memory_text)
            self.events.put(("ai", provider))
            return answer
        except Exception as exc:
            self.events.put(("ai", "OFFLINE"))
            return str(exc)

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
                        self.gemini_status.configure(text="● GEMINI: CHECK FAILED",text_color=GOLD)
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
                elif kind=="pc_confirm":
                    action=msg
                    approved=messagebox.askyesno("Confirm PC control",f"Schedule Windows {action} in 10 seconds?\n\nSave your work first. You can cancel using 'shutdown /a' in Windows.")
                    if approved and platform.system()=="Windows":
                        try:
                            args=["shutdown.exe","/r" if action=="restart" else "/s","/t","10"]
                            subprocess.Popen(args,shell=False)
                            self.add("SYSTEM",f"Windows {action} scheduled in 10 seconds. Run 'shutdown /a' to cancel.")
                        except Exception as exc:
                            self.add("SYSTEM",f"Could not schedule {action}: {exc}")
                    elif approved:
                        self.add("SYSTEM","Shutdown/restart scheduling is only implemented on Windows.")
                    else:
                        self.add("SYSTEM",f"{action.title()} cancelled.")
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
                elif kind=="voice_command" or kind=="voice_chat_command":
                    self.entry.delete(0,"end"); self.entry.insert(0,msg); self.send()
                elif kind=="answer":
                    self.add("J.A.R.V.I.S.",msg); self.busy=False; self.send_btn.configure(state="normal",text="SEND ➤")
                    if self.voice_chat_active:
                        self.speak(msg,force=True,on_done=self.voice_chat_ready.set)
                    else:
                        self.speak(msg)
                else:
                    self.add("J.A.R.V.I.S.",msg); self.busy=False; self.send_btn.configure(state="normal",text="SEND ➤"); self.speak(msg)
        except queue.Empty:pass
        self.after(100,self.poll)
    def start_gemini_validation(self):
        """Validate the configured Gemini key asynchronously so the GUI never freezes."""
        key = os.getenv("GEMINI_API_KEY", "").strip()
        if not key:
            self.events.put(("gemini_validation", "NOT_CONFIGURED"))
            return
        self.gemini_status.configure(text="● GEMINI: CHECKING…", text_color=GOLD)
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
        if self.voice_chat_active:
            self.add("SYSTEM","Stop Voice Chat before enabling wake-word mode so only one feature uses the microphone.")
            return
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
            self.wake_btn.configure(text="WAKE: OFF",fg_color="#183B50")
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
        output=ctk.CTkTextbox(win,fg_color=PANEL_ALT,text_color=TEXT,wrap="word"); output.grid(row=1,column=0,sticky="nsew",padx=18,pady=8)
        controls=ctk.CTkFrame(win,fg_color="transparent"); controls.grid(row=2,column=0,sticky="ew",padx=18,pady=12); controls.grid_columnconfigure(0,weight=1)
        def show(text):
            output.configure(state="normal"); output.delete("1.0","end"); output.insert("end",text); output.configure(state="disabled")
        def entry(placeholder):
            field=ctk.CTkEntry(controls,placeholder_text=placeholder); field.grid(row=0,column=0,sticky="ew",padx=(0,6),pady=4); return field
        button_row=[1]
        def button(label,fn):
            ctk.CTkButton(controls,text=label,command=fn,fg_color="#183B50").grid(row=button_row[0],column=0,sticky="ew",pady=4)
            button_row[0]+=1
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
    def open_pc_control_window(self):
        window=ctk.CTkToplevel(self)
        window.title("J.A.R.V.I.S. // PC Control Center")
        window.geometry("560x440")
        window.configure(fg_color=BG)
        window.grid_columnconfigure((0,1),weight=1)
        ctk.CTkLabel(window,text="PC CONTROL CENTER",font=ctk.CTkFont(size=22,weight="bold"),text_color=CYAN).grid(row=0,column=0,columnspan=2,sticky="w",padx=22,pady=(22,4))
        ctk.CTkLabel(window,text="Local actions run on this computer. Power actions always ask for confirmation.",text_color=MUTED,wraplength=500,justify="left").grid(row=1,column=0,columnspan=2,sticky="w",padx=22,pady=(0,18))
        actions=[
            ("System status","pc status"),("Lock screen","pc lock"),
            ("Toggle mute","pc mute"),("Take screenshot","pc screenshot"),
            ("Shut down…","pc shutdown"),("Restart…","pc restart"),
        ]
        for i,(label,command) in enumerate(actions):
            ctk.CTkButton(window,text=label,height=48,fg_color="#13283A",hover_color="#23455C",
                          command=lambda cmd=command:self.run_pc_action(cmd)).grid(
                row=2+i//2,column=i%2,sticky="ew",padx=10,pady=8)
        ctk.CTkLabel(window,text="Screenshots are saved in jarvis_data/screenshots.\nRemote API does not expose power controls or file access.",text_color=MUTED,justify="left").grid(row=5,column=0,columnspan=2,sticky="w",padx=22,pady=14)

    def run_pc_action(self, command):
        if command in ("pc status","pc lock","pc mute","pc screenshot"):
            result=self.command(command)
            self.add("PC CONTROL",result)
        else:
            self.add("PC CONTROL",self.command(command))

    def remote_status(self):
        data=system_metrics()
        return {key:data.get(key) for key in ("host","platform","cpu_percent","memory_percent","memory_used_gb","disk_percent","battery_percent") if key in data}

    def remote_status_text(self):
        data=self.remote_status()
        return "\n".join(f"{key.replace('_',' ').title()}: {value}" for key,value in data.items())

    def remote_command(self, command):
        normalized=command.strip().lower()
        # The remote API is intentionally narrower than local desktop commands.
        if normalized in ("pc lock","lock screen"):
            return lock_screen()[1]
        if normalized.startswith("launch "):
            app=normalized[7:].strip()
            ok,message=launch_app(app)
            return message
        return "Remote command rejected."

    def remote_control_setup(self):
        if self.remote.running:
            self.remote.stop()
            self.add("REMOTE","Remote control server stopped; its access token has been discarded.")
            return
        allow_lan=messagebox.askyesno(
            "JARVIS Remote Control",
            "Enable access from another device on your local network?\n\n"
            "YES = bind to the LAN (trusted network only). The API uses a strong token but plain HTTP, not encryption; do not use on public/untrusted Wi-Fi or expose the port to the internet.\n\n"
            "NO = this computer only (127.0.0.1)."
        )
        try:
            token=self.remote.start(allow_lan=allow_lan)
            host=self.remote.host
            if allow_lan:
                try:
                    lan_ip=socket.gethostbyname(socket.gethostname())
                except OSError:
                    lan_ip="<this-PC-IP>"
                endpoint=f"http://{lan_ip}:{self.remote.port}"
            else:
                endpoint=f"http://127.0.0.1:{self.remote.port}"
            self.add("REMOTE",f"Remote API started at {endpoint}. Token created in memory; only allow-listed commands are accepted.")
            messagebox.showinfo(
                "JARVIS Remote API Ready",
                f"Base URL: {endpoint}\n\nBearer token (copy now; it is shown only once):\n{token}\n\n"
                "Authenticated endpoints:\nGET /api/status\nPOST /api/command with JSON {\"command\":\"launch notepad\"}\n"
                "Allowed remote actions: status, launch <app>, lock screen. Arbitrary shell, power controls and file access are blocked.\n\n"
                "Stop the server using the same sidebar button."
            )
        except Exception as exc:
            self.add("REMOTE",f"Could not start remote control: {exc}")
            messagebox.showerror("Remote Control Error",str(exc))

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
