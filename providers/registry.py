"""Registry interface for optional provider settings.

The active chat backend is jarvis_ai.py (Groq with Gemini fallback). This empty
registry keeps the optional pipeline editor honest until providers are added.
"""
def discover(kind): return []
def get_declaration(provider_id): return None
