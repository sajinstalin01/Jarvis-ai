"""Natural-language aliases for supported JARVIS commands.

This module only maps clear requests to existing local commands. It never runs shell
text or grants new operating-system permissions.
"""
import re

_PREFIX = re.compile(r"^(?:(?:hey|hello)\s+)?jarvis[,:!]?\s*", re.I)
_POLITE_START = re.compile(r"^(?:please\s+|could you\s+|can you\s+|would you\s+|kindly\s+)", re.I)
_POLITE_END = re.compile(r"[,.!? ]+(?:please|for me|sir)[.!? ]*$", re.I)


def normalize_natural_command(text: str) -> str | None:
    """Return a supported local command for clear natural-language requests."""
    raw = str(text or "").strip()
    if not raw:
        return None
    raw = _PREFIX.sub("", raw).strip()
    raw = _POLITE_START.sub("", raw).strip()
    raw = _POLITE_END.sub("", raw).strip()
    p = raw.casefold().strip(" .!?")
    direct = {
        "what time is it": "time",
        "tell me the time": "time",
        "what is today's date": "date",
        "what's today's date": "date",
        "what is the date": "date",
        "check my pc": "pc status",
        "check my computer": "pc status",
        "check system status": "pc status",
        "how is my pc doing": "pc status",
        "show system status": "pc status",
        "take a screenshot": "pc screenshot",
        "capture my screen": "pc screenshot",
        "lock my computer": "pc lock",
        "lock my pc": "pc lock",
        "lock the computer": "pc lock",
        "mute my computer": "pc mute",
        "show my tasks": "tasks list",
        "list my tasks": "tasks list",
        "what are my tasks": "tasks list",
        "show overdue tasks": "tasks due",
        "what tasks are overdue": "tasks due",
        "show my reminders": "list reminders",
        "list my reminders": "list reminders",
        "what can you do": "help",
        "show commands": "help",
        "check api status": "api status",
        "check my api keys": "api status",
    }
    if p in direct:
        return direct[p]
    direct.update({
        "show cpu usage": "pc metrics",
        "show system resources": "pc metrics",
        "check hardware usage": "pc metrics",
        "show open windows": "pc windows",
        "list open windows": "pc windows",
        "show connected monitors": "pc monitors",
    })
    if p in direct:
        return direct[p]
    match = re.fullmatch(r"(?:set|change) volume(?: to)? (\d{1,3})(?: percent|%)?", raw, re.I)
    if match and int(match.group(1)) <= 100:
        return "pc volume set " + match.group(1)
    match = re.fullmatch(r"(?:set|change) brightness(?: to)? (\d{1,3})(?: percent|%)?", raw, re.I)
    if match and int(match.group(1)) <= 100:
        return "pc brightness set " + match.group(1)
    match = re.fullmatch(r"(?:switch|set) power plan to (balanced|high performance|power saver)", raw, re.I)
    if match:
        return "pc power plan " + match.group(1).casefold()
    match = re.fullmatch(r"(minimize|maximize|restore|focus|close) (?:window )?(.+)", raw, re.I)
    if match:
        return "pc window " + match.group(1).casefold() + " " + match.group(2).strip()
    match = re.fullmatch(r"(?:open|launch|start)\s+(.+)", raw, re.I)
    if match:
        target = match.group(1).strip().strip('"')
        target = re.sub(r"\s+(?:for me|please|sir)[.!? ]*$", "", target, flags=re.I).strip()
        if target and len(target) <= 160 and not any(c in target for c in "\r\n"):
            verb = "open" if raw.casefold().startswith("open ") else "launch"
            return verb + " " + target
    match = re.fullmatch(r"(?:search for|look up|find information about)\s+(.+)", raw, re.I)
    if match and len(match.group(1).strip()) <= 500:
        return "search " + match.group(1).strip()
    match = re.fullmatch(r"(?:calculate|work out|what is)\s+([0-9(). +*/%^-]+)", raw, re.I)
    if match and re.search(r"\d", match.group(1)):
        return "calculate " + match.group(1).strip()
    match = re.fullmatch(r"(?:add|create) (?:a )?(?:new )?task[: ]+(.+)", raw, re.I)
    if match:
        title = match.group(1).strip()
        if title and len(title) <= 240 and not title.casefold().startswith("due "):
            return "tasks add " + title
    match = re.fullmatch(r"(?:mark|set) task #?(\d+) (?:as )?(?:complete|completed|done)", raw, re.I)
    if match:
        return "tasks done " + match.group(1)
    match = re.fullmatch(r"(?:delete|remove) task #?(\d+)", raw, re.I)
    if match:
        return "tasks delete " + match.group(1)
    return None
