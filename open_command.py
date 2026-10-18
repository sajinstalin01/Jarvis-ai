"""Safe parser for JARVIS 'open' commands and supported website shortcuts."""
from __future__ import annotations

import re
import urllib.parse
from urllib.parse import urlsplit

SITE_ALIASES = {
    "google": "google",
    "google.com": "google",
    "www.google.com": "google",
    "youtube": "youtube",
    "youtube.com": "youtube",
    "www.youtube.com": "youtube",
    "youtu.be": "youtube",
    "github": "github",
    "github.com": "github",
    "www.github.com": "github",
    "gmail": "gmail",
    "mail.google.com": "gmail",
    "wikipedia": "wikipedia",
    "wikipedia.org": "wikipedia",
    "www.wikipedia.org": "wikipedia",
}

SITE_URLS = {
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
    "wikipedia": "https://www.wikipedia.org",
}


def parse_open_payload(value: str) -> tuple[str, str | None]:
    """Split 'chrome search weather' into target='chrome', query='weather'."""
    raw = str(value or "").strip()
    if not raw:
        return "", None
    match = re.fullmatch(r"(.+?)\s+search\s+(.+)", raw, flags=re.IGNORECASE | re.DOTALL)
    if match:
        target, query = match.group(1).strip(), match.group(2).strip()
        if target and query:
            return target, query
    return raw, None


def safe_website_url(target: str, query: str | None = None) -> str | None:
    """Return URLs for explicitly allow-listed sites only, or None for other targets."""
    raw = str(target or "").strip().casefold().rstrip("/")
    if not raw:
        return None

    alias_key = raw
    if "://" in raw:
        try:
            parts = urlsplit(raw)
            if parts.scheme not in {"http", "https"} or parts.username or parts.password:
                return None
            if parts.port not in (None, 80, 443):
                return None
            alias_key = (parts.hostname or "").casefold()
        except ValueError:
            return None
    site = SITE_ALIASES.get(alias_key)
    if not site:
        return None

    if not query:
        return SITE_URLS[site]

    q = urllib.parse.quote_plus(str(query).strip())
    if not q:
        return SITE_URLS[site]
    if site == "google":
        return f"https://www.google.com/search?q={q}"
    if site == "youtube":
        return f"https://www.youtube.com/results?search_query={q}"
    if site == "github":
        return f"https://github.com/search?q={q}"
    if site == "wikipedia":
        return f"https://en.wikipedia.org/w/index.php?search={q}"
    if site == "gmail":
        return "https://mail.google.com/mail/u/0/#search/" + urllib.parse.quote(str(query).strip(), safe="")
    return SITE_URLS[site]
