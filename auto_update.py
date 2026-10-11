"""Safe, configurable GitHub updater for JARVIS.

Settings live in update_config.json. The updater locates Git even when git.exe is
not on PATH, and never overwrites uncommitted local edits.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "update_config.json"
STATE_PATH = ROOT / ".jarvis_update_state.json"


def log(message: str) -> None:
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{stamp}] {message}", flush=True)


def load_config() -> dict:
    defaults = {
        "enabled": True,
        "repository": "sajinstalin01/Jarvis-ai",
        "branch": "main",
        "git_executable": "",
        "watch_interval_seconds": 300,
    }
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as handle:
            user_config = json.load(handle)
        if not isinstance(user_config, dict):
            raise ValueError("The top-level JSON value must be an object.")
        defaults.update(user_config)
    except FileNotFoundError:
        log("update_config.json is missing; using built-in defaults.")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        log(f"Could not read update_config.json: {exc}")
        raise
    defaults["repository"] = str(defaults.get("repository", "")).strip()
    defaults["branch"] = str(defaults.get("branch", "main")).strip() or "main"
    defaults["git_executable"] = str(defaults.get("git_executable", "")).strip()
    try:
        defaults["watch_interval_seconds"] = max(
            60, int(defaults.get("watch_interval_seconds", 300))
        )
    except (TypeError, ValueError):
        defaults["watch_interval_seconds"] = 300
    return defaults


def find_git(configured_path: str = "") -> str | None:
    """Find git.exe via config, PATH, or common Windows installation folders."""
    candidates: list[str] = []
    if configured_path:
        candidates.append(os.path.expandvars(os.path.expanduser(configured_path)))

    path_git = shutil.which("git")
    if path_git:
        candidates.append(path_git)

    if os.name == "nt":
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        candidates.extend([
            str(Path(program_files) / "Git" / "cmd" / "git.exe"),
            str(Path(program_files) / "Git" / "bin" / "git.exe"),
            str(Path(program_files_x86) / "Git" / "cmd" / "git.exe"),
            str(Path(local_app_data) / "Programs" / "Git" / "cmd" / "git.exe"),
            str(Path(local_app_data) / "Programs" / "Git" / "bin" / "git.exe"),
        ])

    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate).resolve())
    return None


def git(git_executable: str, *args: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            [git_executable, *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=90,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"Git executable could not be started: {git_executable}. "
            "Install Git for Windows or set git_executable in update_config.json."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Git command timed out: git {' '.join(args)}") from exc


def save_state(commit: str) -> None:
    try:
        STATE_PATH.write_text(
            json.dumps({
                "last_checked": datetime.now().isoformat(timespec="seconds"),
                "commit": commit,
            }, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        log(f"Note: could not save update state: {exc}")


def check_once(config: dict, git_executable: str) -> bool:
    if not config.get("enabled", True):
        log("Automatic updates are disabled in update_config.json.")
        return True

    if not (ROOT / ".git").exists():
        log("This folder is not a Git checkout. Clone the repository first.")
        log("Expected repository: https://github.com/" + config["repository"] + ".git")
        return False

    branch = config["branch"]
    remote_name = "origin"

    rem = git(git_executable, "remote", "get-url", remote_name)
    if rem.returncode:
        log("No origin remote is configured. Set it with: git remote add origin "
            "https://github.com/" + config["repository"] + ".git")
        return False

    status = git(git_executable, "status", "--porcelain")
    if status.returncode:
        log("Unable to inspect Git status: " + status.stderr.strip())
        return False
    if status.stdout.strip():
        log("Local changes detected. Update skipped to protect your files.")
        log("Commit or stash your changes, then run the updater again.")
        return False

    fetch = git(git_executable, "fetch", remote_name, branch)
    if fetch.returncode:
        log("Git fetch failed: " + (fetch.stderr.strip() or fetch.stdout.strip()))
        return False

    local_result = git(git_executable, "rev-parse", "HEAD")
    remote_result = git(git_executable, "rev-parse", f"{remote_name}/{branch}")
    if local_result.returncode or remote_result.returncode:
        log("Could not resolve local or remote commit. Check the configured branch.")
        return False

    local = local_result.stdout.strip()
    remote = remote_result.stdout.strip()
    if not local or not remote:
        log("Could not resolve local or remote commit.")
        return False

    ancestor = git(
        git_executable, "merge-base", "--is-ancestor", "HEAD", f"{remote_name}/{branch}"
    )
    if ancestor.returncode == 1:
        diverged = git(
            git_executable, "merge-base", "--is-ancestor",
            f"{remote_name}/{branch}", "HEAD"
        )
        if diverged.returncode == 0:
            log(f"Local branch is ahead of {remote_name}/{branch}; no update needed.")
        else:
            log(f"Local branch diverged from {remote_name}/{branch}. No changes applied.")
            log("Resolve the Git history manually before updating.")
        return False
    if ancestor.returncode != 0:
        log("Could not safely compare local and remote branches.")
        return False

    if local == remote:
        log("Already up to date.")
        save_state(local)
        return True

    pull = git(git_executable, "pull", "--ff-only", remote_name, branch)
    if pull.returncode:
        log("Fast-forward update failed safely: " + (pull.stderr.strip() or pull.stdout.strip()))
        return False

    new_head = git(git_executable, "rev-parse", "HEAD").stdout.strip()
    log(f"Updated JARVIS successfully: {local[:8]} -> {new_head[:8]}")
    log("Restart JARVIS to load the updated Python code.")
    save_state(new_head)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Safely update JARVIS from GitHub")
    parser.add_argument("--watch", action="store_true", help="check repeatedly for updates")
    parser.add_argument("--interval", type=int, default=None, help="watch interval in seconds")
    args = parser.parse_args()

    try:
        config = load_config()
    except (OSError, json.JSONDecodeError, ValueError):
        log("Fix update_config.json JSON syntax, then try again.")
        return 2

    git_executable = find_git(config["git_executable"])
    if not git_executable:
        log("Git was not found. The updater could not run any Git commands.")
        log("Install Git for Windows: https://git-scm.com/download/win")
        log("Or edit update_config.json and set git_executable to the full path, e.g.:")
        log(r'  "git_executable": "C:\\Program Files\\Git\\cmd\\git.exe"')
        log("Then run: python auto_update.py")
        return 2

    version = git(git_executable, "--version")
    if version.returncode:
        log("The configured Git executable did not run: " + version.stderr.strip())
        return 2
    log(f"Using {version.stdout.strip()} ({git_executable})")

    if not args.watch:
        try:
            return 0 if check_once(config, git_executable) else 1
        except RuntimeError as exc:
            log(str(exc))
            return 2

    interval = max(60, args.interval if args.interval is not None
                   else config["watch_interval_seconds"])
    log(f"Watching {config['repository']} / {config['branch']} every {interval} seconds. Ctrl+C to stop.")
    try:
        while True:
            try:
                check_once(config, git_executable)
            except RuntimeError as exc:
                log(str(exc))
            time.sleep(interval)
    except KeyboardInterrupt:
        log("Update watcher stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
