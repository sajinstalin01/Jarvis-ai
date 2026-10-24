"""Regression tests for the WhatsApp draft-link helper."""
import unittest
from unittest.mock import patch

import whatsapp_control


class WhatsAppControlTests(unittest.TestCase):
    @patch("whatsapp_control.webbrowser.open", return_value=True)
    def test_formatted_international_phone_is_normalized(self, open_url):
        ok, message = whatsapp_control.open_number_chat("+91 (98765) 43210")
        self.assertTrue(ok, message)
        self.assertEqual(open_url.call_args.args[0], "https://wa.me/919876543210")

    @patch("whatsapp_control.webbrowser.open", return_value=True)
    def test_message_text_is_url_encoded(self, open_url):
        ok, message = whatsapp_control.open_number_chat("+91 98765 43210", "Hello world!")
        self.assertTrue(ok, message)
        self.assertIn("?text=Hello%20world%21", open_url.call_args.args[0])

    @patch("whatsapp_control.webbrowser.open")
    def test_invalid_number_is_rejected_without_opening_browser(self, open_url):
        ok, _message = whatsapp_control.open_number_chat("123-45")
        self.assertFalse(ok)
        open_url.assert_not_called()


if __name__ == "__main__":
    unittest.main()
