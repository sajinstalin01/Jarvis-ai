"""Confirmation resolver hook for irreversible actions."""
_handler = None
def set_handler(handler):
    global _handler; _handler = handler
def resolve(accepted):
    if _handler: return _handler(bool(accepted))
    return False
