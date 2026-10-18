import unittest
from types import SimpleNamespace

from ui_theme import REALISTIC_PALETTE, apply_realistic_theme


class RealisticThemeTests(unittest.TestCase):
    def test_palette_uses_restrained_hud_colors(self):
        self.assertEqual(REALISTIC_PALETTE["BG"], "#080e16")
        self.assertEqual(REALISTIC_PALETTE["PRI"], "#78d5ed")
        self.assertEqual(REALISTIC_PALETTE["ACC"], "#e9a36c")
        self.assertEqual(set(REALISTIC_PALETTE), {
            "BG", "PANEL", "PANEL2", "BORDER", "BORDER_B", "BORDER_A",
            "PRI", "PRI_DIM", "PRI_GHO", "ACC", "ACC2", "GREEN", "GREEN_D",
            "RED", "MUTED_C", "TEXT", "TEXT_DIM", "TEXT_MED", "WHITE", "DARK",
            "BAR_BG",
        })

    def test_palette_applies_before_widgets_are_built(self):
        class Palette:
            BG = "#00060a"
            PRI = "#00d4ff"

        module = SimpleNamespace(
            C=Palette,
            _HUE_LINKED=("BG", "PRI"),
            _PALETTE_DEFAULTS={"BG": "#00060a", "PRI": "#00d4ff"},
            DEFAULT_UI_COLOR="#00d4ff",
        )

        class App:
            def setApplicationName(self, _name):
                pass
            def setStyle(self, _style):
                pass
            def setFont(self, _font):
                pass
            def setStyleSheet(self, _style):
                pass

        apply_realistic_theme(module, App())
        self.assertEqual(Palette.BG, REALISTIC_PALETTE["BG"])
        self.assertEqual(Palette.PRI, REALISTIC_PALETTE["PRI"])
        self.assertEqual(module._PALETTE_DEFAULTS["PRI"], REALISTIC_PALETTE["PRI"])
        self.assertEqual(module.DEFAULT_UI_COLOR, REALISTIC_PALETTE["PRI"])


if __name__ == "__main__":
    unittest.main()
