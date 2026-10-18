# Vendored MARK LVI core modules

These files are imported from [FatihMakes/Mark-LVI](https://github.com/FatihMakes/Mark-LVI) at pinned revision `4d4035c1b40a3bc796ac63f2f1b6a99bc0dd334d`.

**License:** CC BY-NC 4.0. Copyright remains with the upstream author, FatihMakes. The source license prohibits commercial use and requires attribution. See [upstream LICENSE](https://github.com/FatihMakes/Mark-LVI/blob/4d4035c1b40a3bc796ac63f2f1b6a99bc0dd334d/LICENSE) and [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/legalcode). These vendored files must not be used commercially unless separate permission is obtained.

## Scope and integration status

The files in this directory are preserved in a separate namespace rather than replacing the existing JARVIS HUD modules. Several upstream modules expect MARK LVI's `main.py`, `actions/`, `providers/`, UI callbacks, and configuration schema. They are **not automatically wired into the current `jarvis.py` bridge**; they should be integrated feature-by-feature and tested against this repository before activation.

Vendored source files at this integration branch:
- [`vendor/mark_lvi/core/action_loader.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/integrate-mark-lvi-core/vendor/mark_lvi/core/action_loader.py)
- [`vendor/mark_lvi/core/appidentity.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/integrate-mark-lvi-core/vendor/mark_lvi/core/appidentity.py)
- [`vendor/mark_lvi/core/audio_devices.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/integrate-mark-lvi-core/vendor/mark_lvi/core/audio_devices.py)
- [`vendor/mark_lvi/core/avatar.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/integrate-mark-lvi-core/vendor/mark_lvi/core/avatar.py)
- [`vendor/mark_lvi/core/avatar_mesh.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/integrate-mark-lvi-core/vendor/mark_lvi/core/avatar_mesh.py)
- [`vendor/mark_lvi/core/confirm.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/integrate-mark-lvi-core/vendor/mark_lvi/core/confirm.py)
- [`vendor/mark_lvi/core/echo.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/integrate-mark-lvi-core/vendor/mark_lvi/core/echo.py)
- [`vendor/mark_lvi/core/gemini.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/integrate-mark-lvi-core/vendor/mark_lvi/core/gemini.py)
- [`vendor/mark_lvi/core/hotkey.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/integrate-mark-lvi-core/vendor/mark_lvi/core/hotkey.py)
- [`vendor/mark_lvi/core/installer.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/integrate-mark-lvi-core/vendor/mark_lvi/core/installer.py)
- [`vendor/mark_lvi/core/lazyimport.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/integrate-mark-lvi-core/vendor/mark_lvi/core/lazyimport.py)
- [`vendor/mark_lvi/core/llm_client.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/integrate-mark-lvi-core/vendor/mark_lvi/core/llm_client.py)
- [`vendor/mark_lvi/core/outcome.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/integrate-mark-lvi-core/vendor/mark_lvi/core/outcome.py)
- [`vendor/mark_lvi/core/platform_support.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/integrate-mark-lvi-core/vendor/mark_lvi/core/platform_support.py)
- [`vendor/mark_lvi/core/plugin_loader.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/integrate-mark-lvi-core/vendor/mark_lvi/core/plugin_loader.py)
- [`vendor/mark_lvi/core/prompt.txt`](https://github.com/sajinstalin01/Jarvis-ai/blob/integrate-mark-lvi-core/vendor/mark_lvi/core/prompt.txt)
- [`vendor/mark_lvi/core/stt.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/integrate-mark-lvi-core/vendor/mark_lvi/core/stt.py)
- [`vendor/mark_lvi/core/tts.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/integrate-mark-lvi-core/vendor/mark_lvi/core/tts.py)
- [`vendor/mark_lvi/core/undo.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/integrate-mark-lvi-core/vendor/mark_lvi/core/undo.py)
- [`vendor/mark_lvi/core/viseme.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/integrate-mark-lvi-core/vendor/mark_lvi/core/viseme.py)
- [`vendor/mark_lvi/core/wake_word.py`](https://github.com/sajinstalin01/Jarvis-ai/blob/integrate-mark-lvi-core/vendor/mark_lvi/core/wake_word.py)

Source revision: `4d4035c1b40a3bc796ac63f2f1b6a99bc0dd334d`.
