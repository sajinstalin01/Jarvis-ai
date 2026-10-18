import unittest

from open_command import parse_open_payload, safe_website_url


class OpenCommandTests(unittest.TestCase):
    def test_parse_application_with_search_query(self):
        self.assertEqual(
            parse_open_payload("Chrome search Android Studio"),
            ("Chrome", "Android Studio"),
        )

    def test_plain_application_has_no_query(self):
        self.assertEqual(parse_open_payload("Android Studio"), ("Android Studio", None))

    def test_named_website_aliases_are_supported(self):
        self.assertEqual(safe_website_url("gmail"), "https://mail.google.com")
        self.assertEqual(safe_website_url("https://www.google.com/"), "https://www.google.com")
        self.assertEqual(safe_website_url("github.com", "open pull request"), "https://github.com/search?q=open+pull+request")
        self.assertEqual(safe_website_url("youtube", "JARVIS tutorial"), "https://www.youtube.com/results?search_query=JARVIS+tutorial")

    def test_arbitrary_urls_are_not_opened_by_the_site_shortcut_router(self):
        self.assertIsNone(safe_website_url("https://example.org"))
        self.assertIsNone(safe_website_url("https://google.com.example.org"))
        self.assertIsNone(safe_website_url("javascript://google.com"))
        self.assertIsNone(safe_website_url("https://google.com:8443"))


if __name__ == "__main__":
    unittest.main()
