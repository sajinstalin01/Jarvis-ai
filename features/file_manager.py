"""Safe local-first file and folder operations for JARVIS."""
import os, shlex, shutil, zipfile
from datetime import datetime
from pathlib import Path

_SKIP_DIRS={".git",".venv","venv","node_modules","__pycache__","Windows","Program Files","Program Files (x86)","$Recycle.Bin","System Volume Information"}
MAX_SCAN=2500

class FileManager:
    def __init__(self,audit=None):
        self.audit=audit or (lambda action,result="ok":None)
        self.pending_delete=None
        self.pending_organize=None

    @staticmethod
    def path(value): return Path(value).expanduser().resolve()

    @staticmethod
    def parts(value):
        try:
            # Preserve Windows backslashes, stripping only matching quote pairs.
            values=shlex.split(value,posix=False)
            return [v[1:-1] if len(v)>=2 and v[0]==v[-1] and v[0] in {"'",'"'} else v for v in values]
        except ValueError as exc: raise ValueError(f"Invalid quoting: {exc}") from exc

    @staticmethod
    def pair(value):
        if " :: " not in value: raise ValueError('Separate values with " :: " and quote paths containing spaces.')
        a,b=value.split(" :: ",1)
        a,b=a.strip(),b.strip()
        if not a or not b: raise ValueError("Both values are required.")
        # Paths may be quoted to preserve spaces; remove only a matching outer pair.
        def unquote(v):
            return v[1:-1] if len(v)>=2 and v[0]==v[-1] and v[0] in {"'",'"'} else v
        return unquote(a),unquote(b)

    @staticmethod
    def inside(child,parent):
        try: child.resolve().relative_to(parent.resolve()); return True
        except (ValueError,OSError): return False

    def dispatch(self,command):
        s=command.strip()
        if s.casefold() in {"fm","fm help","file manager","file manager help"}: return self.help()
        if not s.casefold().startswith("fm "): return None
        op,_,rest=s[3:].partition(" "); op=op.casefold(); rest=rest.strip()
        if op=="dirs": return self.common_dirs()
        if op=="list": return self.list_dir(rest or "~")
        if op=="search":
            root,q=self.pair(rest); return self.search(root,q)
        if op=="create": return self.create(rest)
        if op in {"rename","copy","move"}:
            a,b=self.pair(rest); return self.transfer(op,a,b)
        if op=="delete":
            return self.delete_confirm(rest[8:].strip()) if rest.casefold().startswith("confirm ") else self.delete_request(rest)
        if op=="organize":
            if rest.casefold()=="confirm": return self.organize_confirm()
            folder,mode=self.pair(rest); return self.organize_request(folder,mode)
        if op=="bulk-copy":
            pattern,dest=self.pair(rest); return self.bulk_copy(pattern,dest)
        if op=="zip":
            source,archive=self.pair(rest); return self.zip_path(source,archive)
        if op=="unzip":
            archive,dest=self.pair(rest); return self.unzip_path(archive,dest)
        return self.help()

    def help(self):
        return """File & Folder Management (quote paths containing spaces):
fm dirs | fm list <folder>
fm search <root> :: <filename glob/name or content:text>
fm create file <path> | fm create folder <path>
fm rename <source> :: <destination> | fm copy <source> :: <destination> | fm move <source> :: <destination>
fm delete <path> (then fm delete confirm <same path>)
fm organize <folder> :: type|date|size (preview, then fm organize confirm)
fm bulk-copy <source glob> :: <existing destination folder>
fm zip <file-or-folder> :: <new archive.zip>
fm unzip <archive.zip> :: <new-or-empty destination>
Delete and bulk organization require a separate confirmation. Search is bounded and skips common system/build/cache directories."""

    def common_dirs(self):
        h=Path.home(); d={"Home":h,"Desktop":h/"Desktop","Downloads":h/"Downloads","Documents":h/"Documents","Pictures":h/"Pictures","Music":h/"Music","Videos":h/"Videos","Temp":Path(os.environ.get("TEMP" if os.name=="nt" else "TMPDIR",str(h/"AppData/Local/Temp" if os.name=="nt" else "/tmp")))}
        return "\n".join(f"{k}: {v} {'(available)' if v.is_dir() else '(not found)'}" for k,v in d.items())

    def list_dir(self,value):
        p=self.path(value)
        if not p.is_dir(): return f"Folder not found: {p}"
        rows=[]
        try:
            entries=sorted(p.iterdir(),key=lambda x:(not x.is_dir(),x.name.casefold()))
            for x in entries[:500]:
                try: size=f"{x.stat().st_size} B" if x.is_file() else "DIR"
                except OSError: size="UNKNOWN"
                rows.append(f"{size:>12}  {x.name}")
        except OSError as exc: return f"Cannot list folder: {exc}"
        return f"{p}\n"+("\n".join(rows) if rows else "(empty folder)")+("\nShowing first 500 entries." if len(rows)>=500 else "")

    def walk(self,root):
        count=0
        for base,dirs,files in os.walk(root,followlinks=False):
            dirs[:]=[d for d in dirs if d not in _SKIP_DIRS and not d.startswith(".") and not (Path(base)/d).is_symlink()]
            for name in files:
                p=Path(base)/name
                if p.is_symlink(): continue
                yield p; count+=1
                if count>=MAX_SCAN: return

    def search(self,root_value,query):
        root=self.path(root_value)
        if not root.is_dir(): return f"Search root is not a folder: {root}"
        query=query.strip()
        if not query: return "Use fm search <root> :: <glob-or-name>."
        content=query[8:] if query.casefold().startswith("content:") else None
        found=[]; scanned=0
        for p in self.walk(root):
            scanned+=1
            try:
                if content is not None:
                    if p.stat().st_size>1_000_000 or p.suffix.casefold() in {".exe",".dll",".bin",".zip",".7z",".rar",".pdf",".png",".jpg",".jpeg",".mp4"}: continue
                    if content.casefold() in p.read_text(encoding="utf-8",errors="ignore").casefold(): found.append(p)
                elif p.match(query) or query.casefold() in p.name.casefold(): found.append(p)
                if len(found)>=100: break
            except OSError: continue
        self.audit("fm.search",f"matches={len(found)}")
        return f"Scanned up to {scanned} files under {root}.\n"+("\n".join(map(str,found)) if found else "No matches found.")+("\nResults capped at 100." if len(found)>=100 else "")

    def create(self,value):
        parts=self.parts(value)
        if len(parts)<2 or parts[0].casefold() not in {"file","folder","dir","directory"}: return "Use fm create file <path> or fm create folder <path>."
        kind=parts[0].casefold(); p=self.path(" ".join(parts[1:]))
        if p.exists(): return f"Already exists: {p}"
        p.parent.mkdir(parents=True,exist_ok=True)
        if kind=="file": p.touch(exist_ok=False)
        else: p.mkdir(parents=True,exist_ok=False)
        self.audit("fm.create",str(p)); return f"Created {'file' if kind=='file' else 'folder'}: {p}"

    def transfer(self,action,src_value,dst_value):
        src,dst=self.path(src_value),self.path(dst_value)
        if not src.exists(): return f"Source not found: {src}"
        if src==dst or self.inside(dst,src): return "Destination cannot be the source itself or a folder inside the source."
        if dst.exists(): return f"Destination already exists: {dst}"
        if action=="rename":
            if not dst.parent.is_dir(): return f"Destination parent folder does not exist: {dst.parent}"
            src.rename(dst)
        elif action=="copy":
            dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copytree(src,dst,symlinks=True) if src.is_dir() else shutil.copy2(src,dst)
        else:
            dst.parent.mkdir(parents=True,exist_ok=True); shutil.move(str(src),str(dst))
        self.audit("fm."+action,f"{src} -> {dst}"); return f"{action.capitalize()} complete: {src} -> {dst}"

    def delete_request(self,value):
        parts=self.parts(value)
        if not parts: return "Use fm delete <path>."
        p=self.path(" ".join(parts))
        if not p.exists(): return f"Path not found: {p}"
        if p==Path(p.anchor) or p==Path.home() or p==Path.cwd(): return "Refusing to delete a drive root, home folder, or current working directory."
        self.pending_delete=p
        return f"CONFIRMATION REQUIRED: delete {'folder and all its contents' if p.is_dir() else 'file'} {p}. To proceed, enter: fm delete confirm {shlex.quote(str(p))}"

    def delete_confirm(self,value):
        parts=self.parts(value)
        if not parts: return "Repeat the exact path shown in the confirmation request."
        p=self.path(" ".join(parts))
        if self.pending_delete is None or p!=self.pending_delete: return "No matching pending deletion. Run fm delete <path> again to request deletion."
        self.pending_delete=None
        if not p.exists(): return "Path no longer exists; nothing deleted."
        if p==Path(p.anchor) or p==Path.home() or p==Path.cwd(): return "Refusing to delete a protected root folder."
        shutil.rmtree(p) if p.is_dir() else p.unlink()
        self.audit("fm.delete",str(p)); return f"Deleted: {p}"

    def organize_plan(self,folder,mode):
        plan=[]
        for p in folder.iterdir():
            if not p.is_file() or p.is_symlink(): continue
            if mode=="type": bucket=p.suffix[1:].lower() or "no_extension"
            elif mode=="date": bucket=datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m")
            else:
                n=p.stat().st_size; bucket="small_under_1mb" if n<1_000_000 else "medium_1mb_to_100mb" if n<100_000_000 else "large_100mb_plus"
            dst=folder/bucket/p.name
            if not dst.exists(): plan.append((p,dst))
        return plan

    def organize_request(self,folder_value,mode):
        folder=self.path(folder_value); mode=mode.casefold().strip()
        if not folder.is_dir(): return f"Folder not found: {folder}"
        if mode not in {"type","date","size"}: return "Choose organize mode: type, date, or size."
        plan=self.organize_plan(folder,mode)
        if not plan: return "No files need organizing (or target names already exist)."
        self.pending_organize=(folder,mode)
        preview="\n".join(f"{a.name} -> {b.parent.name}/{b.name}" for a,b in plan[:30])
        return f"ORGANIZE PREVIEW: {len(plan)} file(s) will be moved into {mode} folders.\n{preview}\n"+(f"... and {len(plan)-30} more.\n" if len(plan)>30 else "")+"To execute, enter: fm organize confirm"

    def organize_confirm(self):
        if not self.pending_organize: return "No pending organization plan. Run fm organize <folder> :: type|date|size first."
        folder,mode=self.pending_organize; self.pending_organize=None; plan=self.organize_plan(folder,mode); moved=0
        for src,dst in plan:
            if dst.exists(): continue
            dst.parent.mkdir(parents=True,exist_ok=True); shutil.move(str(src),str(dst)); moved+=1
        self.audit("fm.organize",f"mode={mode},moved={moved}")
        return f"Organization complete: moved {moved} file(s) into {mode} folders."

    def bulk_copy(self,pattern,dest_value):
        pat=self.path(pattern); dest=self.path(dest_value)
        if not dest.is_dir(): return f"Destination folder must already exist: {dest}"
        matches=[p for p in pat.parent.glob(pat.name) if p.is_file() and not p.is_symlink()][:500]
        if not matches: return "No files matched the source pattern."
        copied=skipped=0
        for p in matches:
            target=dest/p.name
            if target.exists(): skipped+=1; continue
            shutil.copy2(p,target); copied+=1
        self.audit("fm.bulk_copy",f"copied={copied},skipped={skipped}")
        return f"Bulk copy complete: copied {copied}, skipped existing names {skipped} (matched up to 500 files)."

    def zip_path(self,source_value,archive_value):
        src,archive=self.path(source_value),self.path(archive_value)
        if not src.exists(): return f"Source not found: {src}"
        if archive.suffix.casefold()!=".zip": return "Archive path must end in .zip."
        if archive.exists(): return f"Archive already exists: {archive}"
        archive.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED) as z:
            if src.is_file(): z.write(src,src.name)
            else:
                for p in src.rglob("*"):
                    if p.is_file() and not p.is_symlink() and not any(part in _SKIP_DIRS for part in p.parts): z.write(p,p.relative_to(src.parent))
        self.audit("fm.zip",str(archive)); return f"Archive created: {archive}"

    def unzip_path(self,archive_value,dest_value):
        archive,dest=self.path(archive_value),self.path(dest_value)
        if not archive.is_file() or not zipfile.is_zipfile(archive): return f"Valid ZIP archive not found: {archive}"
        if dest.exists() and (not dest.is_dir() or any(dest.iterdir())): return f"Extraction destination must be new or empty: {dest}"
        with zipfile.ZipFile(archive) as z:
            members=z.infolist()
            if len(members)>10000 or sum(x.file_size for x in members)>2_000_000_000: return "Archive exceeds safety limits (10,000 entries or 2 GB expanded size)."
            for item in members:
                if not self.inside((dest/item.filename),dest): return "Archive contains an unsafe path; extraction cancelled."
            dest.mkdir(parents=True,exist_ok=True); z.extractall(dest)
        self.audit("fm.unzip",str(dest)); return f"Extracted {len(members)} entries to: {dest}"
