# JARVIS Repository Audit

## Scope and method

This report records a recursive inventory of tracked repository files and a static cross-module review of the launch path, UI integration points, configuration APIs, optional feature facades, requirements, and regression tests. Findings are limited to what can be established from source inspection. GitHub Actions is used for compile/test validation; live API credentials, Windows GUI behavior, audio hardware, and device-specific runtime behavior are not represented as tested unless a test explicitly covers them.

The audit preserves the existing entry point and feature code. It makes targeted fixes and adds regression tests rather than rewriting subsystems.

## Confirmed fixes in this audit branch

1. **PyQt6 startup diagnostics** — error details join with actual newline characters so installation and DLL guidance is readable instead of printing literal `\\n`.
   [`jarvis.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/jarvis.py)

2. **WhatsApp number formatting** — `open_number_chat` strips non-digit characters with the intended regular expression before building a `wa.me` URL, so inputs such as `+91 (98765) 43210` normalize correctly.
   [`whatsapp_control.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/whatsapp_control.py) · [regression tests](https://github.com/sajinstalin01/Jarvis-ai/blob/main/tests/test_whatsapp_control.py)

3. **HUD avatar dependency** — `numpy` is declared in `requirements.txt`, matching the `core.avatar` / `core.avatar_mesh` imports. Without it the guarded import silently suppresses the avatar and the HUD falls back to the core visualization.
   [`requirements.txt`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/requirements.txt) · [`core/avatar.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/core/avatar.py) · [`core/avatar_mesh.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/core/avatar_mesh.py)

4. **Provider settings argument mismatch** — the UI now passes `providers=` and `sidecar_provider=`, which are the names accepted by `memory.config_manager.save_providers`, instead of storing these values under unrelated keyword keys.
   [`ui.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/ui.py) · [`memory/config_manager.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/memory/config_manager.py)

5. **Wake-word setup facade mismatch** — `core.wake_word` lazily delegates to the existing optional implementation and accepts the `logger=` callback used by the HUD, while retaining the older positional progress callback API.
   [`core/wake_word.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/core/wake_word.py) · [`core/mark_lvi_wake_word.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/core/mark_lvi_wake_word.py) · [regression tests](https://github.com/sajinstalin01/Jarvis-ai/blob/main/tests/test_wake_word_facade.py)

## Known integration gaps left unchanged

These are not described as fixed. They affect parts of the wider repository whose implementation is currently a stub or is not connected to the active `jarvis.py` entry point. Keeping them explicit is safer than replacing them with speculative implementations during a bug-fix pass.

- **Wake-word activation:** the setup/download facade is now connected, but the active `JarvisBridge` still supplies a hard-coded not-enabled state and `_wake_toggle` reports that continuous wake listening is not wired. The HUD can install the optional model, but this audit does not claim hands-free detection is functional. A safe completion needs a microphone-stream lifecycle, detector start/stop, and coordination with push-to-talk/listen-once.
  [`jarvis.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/jarvis.py) · [`ui.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/ui.py)

- **Engine/provider panel:** `providers/registry.py` currently returns an empty provider list and exposes only minimal placeholder functions, while `ui.py` and `core/gemini.py` expect richer registry methods and provider adapter modules. The main entry point currently generates answers through `jarvis_ai.py`; changing this architecture was intentionally kept out of this safe integration patch. The argument mismatch above is fixed, but the broader provider pipeline is not yet implemented end to end.
  [`providers/registry.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/providers/registry.py) · [`core/gemini.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/core/gemini.py) · [`jarvis_ai.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/jarvis_ai.py) · [`ui.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/ui.py)

- **Plugins/actions:** the active bridge and local config compatibility helpers return empty plugin/settings lists. There is a loader scaffold under `core/`, but no top-level `actions/` or `plugins/` implementation directory in the tracked inventory. Plugin UI entries should therefore not be treated as fully operational.
  [`jarvis.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/jarvis.py) · [`memory/config_manager.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/memory/config_manager.py) · [`core/plugin_loader.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/core/plugin_loader.py) · [`core/action_loader.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/core/action_loader.py)

- **Per-device volume fallback:** `core/mark_lvi_audio_devices.py` imports `actions.computer_settings` for fallback system volume operations, but that module is not present in the tracked file inventory. This does not affect the independent active volume control unless that optional device helper path is used.
  [`core/mark_lvi_audio_devices.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/core/mark_lvi_audio_devices.py) · [`jarvis_control.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/jarvis_control.py)

## Regression validation

The workflow runs Python compilation and the unittest suite on Python 3.11. Added tests cover formatted WhatsApp numbers, encoded draft text, invalid-number rejection, and the wake-word facade's expected callback signature. A passing CI run validates the paths covered by those automated checks; it does not substitute for Windows GUI/audio checks or live API tests.

Workflow: [`.github/workflows/python-check.yml`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/.github/workflows/python-check.yml)

## Tracked-file inventory

The links below provide direct access to every file in the recursive Git tree inventoried for this audit, including the added regression tests and this report (links target `main` so they remain stable after merge).


### .github
- [`.github/workflows/python-check.yml`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/.github/workflows/python-check.yml)

### core
- [`core/__init__.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/core/__init__.py)
- [`core/action_loader.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/core/action_loader.py)
- [`core/appidentity.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/core/appidentity.py)
- [`core/audio_devices.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/core/audio_devices.py)
- [`core/avatar.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/core/avatar.py)
- [`core/avatar_mesh.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/core/avatar_mesh.py)
- [`core/confirm.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/core/confirm.py)
- [`core/echo.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/core/echo.py)
- [`core/gemini.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/core/gemini.py)
- [`core/hotkey.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/core/hotkey.py)
- [`core/installer.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/core/installer.py)
- [`core/lazyimport.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/core/lazyimport.py)
- [`core/llm_client.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/core/llm_client.py)
- [`core/mark_lvi_audio_devices.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/core/mark_lvi_audio_devices.py)
- [`core/mark_lvi_confirm.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/core/mark_lvi_confirm.py)
- [`core/mark_lvi_hotkey.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/core/mark_lvi_hotkey.py)
- [`core/mark_lvi_wake_word.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/core/mark_lvi_wake_word.py)
- [`core/outcome.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/core/outcome.py)
- [`core/platform_support.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/core/platform_support.py)
- [`core/plugin_loader.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/core/plugin_loader.py)
- [`core/prompt.txt`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/core/prompt.txt)
- [`core/stt.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/core/stt.py)
- [`core/tts.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/core/tts.py)
- [`core/undo.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/core/undo.py)
- [`core/viseme.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/core/viseme.py)
- [`core/wake_word.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/core/wake_word.py)

### custom_fonts
- [`custom_fonts/.gitkeep`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/custom_fonts/.gitkeep)
- [`custom_fonts/README.md`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/custom_fonts/README.md)

### memory
- [`memory/__init__.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/memory/__init__.py)
- [`memory/config_manager.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/memory/config_manager.py)
- [`memory/memory_manager.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/memory/memory_manager.py)

### providers
- [`providers/__init__.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/providers/__init__.py)
- [`providers/registry.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/providers/registry.py)

### Root files
- [`.env.example`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/.env.example)
- [`.gitignore`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/.gitignore)
- [`CODE_AUDIT.md`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/CODE_AUDIT.md)
- [`LICENSE`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/LICENSE)
- [`README.md`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/README.md)
- [`app_control.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/app_control.py)
- [`app_control_manager.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/app_control_manager.py)
- [`app_permissions.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/app_permissions.py)
- [`auto_update.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/auto_update.py)
- [`elevenlabs_api.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/elevenlabs_api.py)
- [`elevenlabs_manager.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/elevenlabs_manager.py)
- [`font_manager.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/font_manager.py)
- [`jarvis.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/jarvis.py)
- [`jarvis_ai.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/jarvis_ai.py)
- [`jarvis_control.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/jarvis_control.py)
- [`jarvis_legacy.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/jarvis_legacy.py)
- [`jarvis_remote.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/jarvis_remote.py)
- [`jarvis_services.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/jarvis_services.py)
- [`open_command.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/open_command.py)
- [`requirements.txt`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/requirements.txt)
- [`run_linux_mac.sh`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/run_linux_mac.sh)
- [`run_windows.bat`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/run_windows.bat)
- [`ui.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/ui.py)
- [`ui_theme.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/ui_theme.py)
- [`update_config.json`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/update_config.json)
- [`voice_control.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/voice_control.py)
- [`whatsapp_control.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/whatsapp_control.py)

### tests
- [`tests/test_app_control_wiring.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/tests/test_app_control_wiring.py)
- [`tests/test_app_launcher.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/tests/test_app_launcher.py)
- [`tests/test_app_permissions.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/tests/test_app_permissions.py)
- [`tests/test_elevenlabs_api.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/tests/test_elevenlabs_api.py)
- [`tests/test_elevenlabs_integration.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/tests/test_elevenlabs_integration.py)
- [`tests/test_font_manager.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/tests/test_font_manager.py)
- [`tests/test_jarvis_ai.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/tests/test_jarvis_ai.py)
- [`tests/test_jarvis_remote.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/tests/test_jarvis_remote.py)
- [`tests/test_jarvis_services.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/tests/test_jarvis_services.py)
- [`tests/test_open_command.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/tests/test_open_command.py)
- [`tests/test_ui_compat.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/tests/test_ui_compat.py)
- [`tests/test_ui_theme.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/tests/test_ui_theme.py)
- [`tests/test_ui_theme_integration.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/tests/test_ui_theme_integration.py)
- [`tests/test_wake_word_facade.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/tests/test_wake_word_facade.py)
- [`tests/test_whatsapp_control.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/main/tests/test_whatsapp_control.py)



## Follow-up feature additions

- Added `core/api_key_manager.py` for unlimited configured key pools for the currently integrated Groq, Gemini, and ElevenLabs providers, masked live health checks, and safe status classifications.
- Updated `jarvis_ai.py` to try each Groq key and then each Gemini fallback key while keeping the existing single-key call signature.
- Added `memory/evolution.py` for opt-in-toggleable, local, narrow automatic memory updates based on explicit user statements; credentials and sensitive topics are excluded.
- Wired `api status`, `api check`, `api keys`, and `memory auto on|off|status` into the active bridge. Preserved existing API configuration during first-run setup and added key-pool selection to ElevenLabs.
- Added regression tests for key pool loading/masking/status and memory extraction/toggle behavior. CI is still required to verify the commit.
