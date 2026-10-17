"""Wake-word hooks are disabled until an optional wake engine is installed."""
def is_ready(): return False
def install_and_download(progress=None): return False, "Wake-word engine is not bundled with this repository yet."
