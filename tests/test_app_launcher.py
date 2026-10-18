"""Regression tests for the allow-listed desktop app launcher.

Load only the launcher declarations from jarvis_legacy.py so these tests do not
need to initialize the full Tkinter UI on CI.
"""
import ast
import json
import os
import platform
import shutil
import subprocess
import urllib.parse
import webbrowser
import unittest
from functools import lru_cache
from pathlib import Path
from unittest import mock

SOURCE = Path(__file__).resolve().parents[1] / "jarvis_legacy.py"
_TREE = ast.parse(SOURCE.read_text(encoding="utf-8"))
_WANTED = {
    "_start_menu_shortcuts", "find_start_menu_shortcut", "APP_ALIASES",
    "_normalize_app_name", "_find_installed_shortcut", "_start_apps_index",
    "_find_store_app_id", "_launch_store_app", "launch_app",
}
_NODES = [
    node for node in _TREE.body
    if isinstance(node, (ast.FunctionDef, ast.Assign))
    and (
        (isinstance(node, ast.FunctionDef) and node.name in _WANTED)
        or (isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "APP_ALIASES"
            for target in node.targets
        ))
    )
]
_NS = {
    "os": os, "json": json, "platform": platform, "shutil": shutil, "subprocess": subprocess,
    "urllib": urllib, "webbrowser": webbrowser, "Path": Path, "lru_cache": lru_cache,
}
exec(compile(ast.Module(body=_NODES, type_ignores=[]), str(SOURCE), "exec"), _NS)


class AppLauncherRegressionTests(unittest.TestCase):
    def test_name_normalization_handles_spaces_and_punctuation(self):
        normalize = _NS["_normalize_app_name"]
        self.assertEqual(normalize("VS Code"), normalize("vs-code"))
        self.assertEqual(normalize("Android Studio"), normalize("androidstudio"))

    def test_common_productivity_and_ai_apps_are_allow_listed(self):
        aliases = _NS["APP_ALIASES"]
        for name in ("word", "excel", "powerpoint", "outlook", "chatgpt",
                     "copilot", "capcut", "canva", "krita", "inkscape"):
            self.assertIn(name, aliases)

    @mock.patch.dict(os.environ, {"APPDATA": r"C:\Users\Test\AppData\Roaming"})
    def test_windows_start_menu_shortcut_used_for_alias_when_executable_not_on_path(self):
        launch_app = _NS["launch_app"]
        shortcut = Path("C:/FakeStartMenu/Visual Studio Code.lnk")
        with mock.patch.object(platform, "system", return_value="Windows"), \
             mock.patch.dict(_NS, {"_start_menu_shortcuts": lambda: {
                 "visualstudiocode": shortcut, "vscode": shortcut,
             }}), \
             mock.patch.object(os, "startfile", create=True) as startfile, \
             mock.patch.object(shutil, "which", return_value=None), \
             mock.patch.object(subprocess, "Popen") as popen:
            ok, message = launch_app("VS-Code")
        self.assertTrue(ok, message)
        startfile.assert_called_once_with(str(shortcut))
        popen.assert_not_called()

    def test_start_apps_index_parses_store_apps_and_app_ids(self):
        get_index = _NS["_start_apps_index"]
        get_index.cache_clear()
        payload = (
            '[{"Name":"WhatsApp","AppID":"WhatsApp.Package!App"},'
            '{"Name":"Telegram Desktop","AppID":"Telegram.Package!App"}]'
        )
        completed = type("Completed", (), {"returncode": 0, "stdout": payload})()
        with mock.patch.object(platform, "system", return_value="Windows"), \
             mock.patch.object(shutil, "which", return_value="powershell.exe"), \
             mock.patch.object(subprocess, "run", return_value=completed):
            rows = get_index()
        self.assertIn(("WhatsApp", "WhatsApp.Package!App"), rows)
        self.assertIn(("Telegram Desktop", "Telegram.Package!App"), rows)
        get_index.cache_clear()

    def test_store_app_lookup_matches_whatsapp_and_telegram_display_names(self):
        records = [
            ("WhatsApp", "WhatsApp.Package!App"),
            ("Telegram Desktop", "Telegram.Package!App"),
        ]
        with mock.patch.object(platform, "system", return_value="Windows"), \
             mock.patch.dict(_NS, {"_start_apps_index": lambda: records}):
            self.assertEqual(
                _NS["_find_store_app_id"]("whatsapp", _NS["APP_ALIASES"]["whatsapp desktop"]),
                "WhatsApp.Package!App",
            )
            self.assertEqual(
                _NS["_find_store_app_id"]("telegram", _NS["APP_ALIASES"]["telegram"]),
                "Telegram.Package!App",
            )

    def test_launches_store_app_using_explorer_appsfolder(self):
        launch_app = _NS["launch_app"]
        with mock.patch.object(platform, "system", return_value="Windows"), \
             mock.patch.dict(_NS, {
                 "_find_installed_shortcut": lambda *args: None,
                 "_find_store_app_id": lambda *args: "Telegram.Package!App",
             }), \
             mock.patch.object(subprocess, "Popen") as popen:
            ok, message = launch_app("Telegram")
        self.assertTrue(ok, message)
        popen.assert_called_once_with(
            ["explorer.exe", "shell:AppsFolder\\\\Telegram.Package!App"],
            shell=False,
        )

    def test_store_alias_does_not_report_false_success_when_not_installed(self):
        launch_app = _NS["launch_app"]
        with mock.patch.object(platform, "system", return_value="Windows"), \
             mock.patch.dict(_NS, {
                 "_find_installed_shortcut": lambda *args: None,
                 "_find_store_app_id": lambda *args: None,
             }), \
             mock.patch.object(shutil, "which", return_value=None), \
             mock.patch.object(subprocess, "Popen") as popen:
            ok, message = launch_app("WhatsApp")
        self.assertFalse(ok)
        self.assertIn("Could not launch", message)
        popen.assert_not_called()

    def test_msc_alias_uses_mmc_without_shell(self):
        launch_app = _NS["launch_app"]
        with mock.patch.object(platform, "system", return_value="Windows"), \
             mock.patch.dict(_NS, {"_find_installed_shortcut": lambda *args: None}), \
             mock.patch.object(subprocess, "Popen") as popen:
            ok, message = launch_app("Device Manager")
        self.assertTrue(ok, message)
        popen.assert_called_once_with(["mmc.exe", "devmgmt.msc"], shell=False)

    def test_unknown_app_fails_without_executing_user_input(self):
        launch_app = _NS["launch_app"]
        with mock.patch.object(platform, "system", return_value="Windows"), \
             mock.patch.dict(_NS, {"_find_installed_shortcut": lambda *args: None}), \
             mock.patch.object(subprocess, "Popen") as popen:
            ok, message = launch_app("totally-unknown-app")
        self.assertFalse(ok)
        self.assertIn("not found", message)
        popen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
