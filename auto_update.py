"""Safe GitHub updater for JARVIS.
Fetches changes and fast-forward pulls only when the local working tree is clean.
Never discards or overwrites uncommitted local edits.
"""
from __future__ import annotations
import argparse, json, subprocess, sys, time
from pathlib import Path
from datetime import datetime

ROOT=Path(__file__).resolve().parent
STATE=ROOT/".jarvis_update_state.json"

def git(*args):
    return subprocess.run(["git",*args],cwd=ROOT,text=True,capture_output=True,timeout=90)

def log(message):
    stamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{stamp}] {message}",flush=True)

def check_once():
    if not (ROOT/".git").exists():
        log("This folder is not a Git checkout. Clone the repository first.")
        return False
    rem=git("remote","get-url","origin")
    if rem.returncode:
        log("No origin remote is configured.")
        return False
    status=git("status","--porcelain")
    if status.returncode:
        log("Unable to inspect Git status: "+status.stderr.strip()); return False
    if status.stdout.strip():
        log("Local changes detected. Update skipped to protect your edits. Commit/stash them, then retry.")
        return False
    fetch=git("fetch","origin","main")
    if fetch.returncode:
        log("Git fetch failed: "+(fetch.stderr.strip() or fetch.stdout.strip())); return False
    local=git("rev-parse","HEAD").stdout.strip()
    remote=git("rev-parse","origin/main").stdout.strip()
    if not local or not remote:
        log("Could not resolve local or origin/main commit."); return False
    ancestor=git("merge-base","--is-ancestor","HEAD","origin/main")
    if ancestor.returncode==1:
        log("Local branch diverged from origin/main. No changes applied; resolve manually.")
        return False
    if ancestor.returncode not in (0,):
        log("Could not safely compare branches."); return False
    if local==remote:
        log("Already up to date.")
        save_state(local)
        return True
    pull=git("pull","--ff-only","origin","main")
    if pull.returncode:
        log("Fast-forward update failed safely: "+(pull.stderr.strip() or pull.stdout.strip()))
        return False
    newhead=git("rev-parse","HEAD").stdout.strip()
    log("Updated JARVIS successfully: "+local[:8]+" -> "+newhead[:8])
    save_state(newhead)
    return True

def save_state(commit):
    try: STATE.write_text(json.dumps({"last_checked":datetime.now().isoformat(timespec="seconds"),"commit":commit},indent=2),encoding="utf-8")
    except OSError: pass

def main():
    parser=argparse.ArgumentParser(description="Safely update JARVIS from origin/main")
    parser.add_argument("--watch",action="store_true",help="check repeatedly for new commits")
    parser.add_argument("--interval",type=int,default=300,help="watch interval in seconds (minimum 60)")
    args=parser.parse_args()
    if not args.watch:
        return 0 if check_once() else 1
    interval=max(60,args.interval)
    log(f"Watching origin/main every {interval} seconds. Ctrl+C to stop.")
    try:
        while True:
            check_once()
            time.sleep(interval)
    except KeyboardInterrupt:
        log("Update watcher stopped.")
    return 0

if __name__=="__main__":
    sys.exit(main())
