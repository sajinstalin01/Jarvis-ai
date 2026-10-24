import sys
import types
import unittest
from unittest.mock import Mock, patch

from jarvis_ai import DEFAULT_GROQ_MODEL, generate_response, _gemini_contents


class JarvisAITests(unittest.TestCase):
    def test_default_groq_model_is_current_replacement(self):
        self.assertEqual(DEFAULT_GROQ_MODEL, "openai/gpt-oss-120b")

    def test_retired_groq_model_retries_with_supported_model(self):
        groq_module = types.ModuleType("groq")
        response = types.SimpleNamespace(
            choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="Groq works"))]
        )
        completions = Mock()
        def create(**kwargs):
            if kwargs["model"] == "llama-3.3-70b-versatile":
                raise RuntimeError("404 model_not_found: model does not exist")
            return response
        completions.create.side_effect = create
        fake_client = types.SimpleNamespace(chat=types.SimpleNamespace(completions=completions))
        groq_module.Groq = Mock(return_value=fake_client)
        with patch.dict(sys.modules, {"groq": groq_module}):
            answer, provider = generate_response(
                "hello", groq_key="test-key", gemini_key="",
                groq_model="llama-3.3-70b-versatile",
                context=[{"role": "user", "content": "I prefer concise answers."},
                         {"role": "assistant", "content": "I will keep it concise."}],
                saved_memories="Prefers concise answers",
            )
        self.assertEqual(answer, "Groq works")
        self.assertEqual(provider, "GROQ (openai/gpt-oss-120b)")
        self.assertEqual(completions.create.call_count, 2)
        sent_messages = completions.create.call_args_list[-1].kwargs["messages"]
        self.assertIn("Prefers concise answers", sent_messages[0]["content"])
        self.assertEqual(sent_messages[1]["content"], "I prefer concise answers.")
        self.assertEqual(sent_messages[2]["content"], "I will keep it concise.")
        self.assertEqual(sent_messages[3]["content"], "hello")

    def test_default_groq_key_pool_tries_next_key_after_failure(self):
        groq_module = types.ModuleType("groq")
        response = types.SimpleNamespace(
            choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="Second key worked"))]
        )

        class FakeGroq:
            def __init__(self, api_key):
                self.api_key = api_key
                self.chat = types.SimpleNamespace(
                    completions=types.SimpleNamespace(create=self.create)
                )

            def create(self, **kwargs):
                if self.api_key == "bad-key":
                    raise RuntimeError("HTTP 401 unauthorized")
                return response

        groq_module.Groq = FakeGroq
        with patch.dict(sys.modules, {"groq": groq_module}), patch(
            "core.api_key_manager.get_api_keys",
            side_effect=lambda provider: ["bad-key", "good-key"] if provider == "groq" else [],
        ):
            answer, provider = generate_response("hello", groq_key=None, gemini_key="")
        self.assertEqual(answer, "Second key worked")
        self.assertEqual(provider, f"GROQ ({DEFAULT_GROQ_MODEL})")

    def test_gemini_prompt_contains_recent_context_and_memories(self):
        prompt = _gemini_contents(
            "What about the second option?",
            [{"role": "user", "content": "Compare two laptops."},
             {"role": "assistant", "content": "Option one is faster."}],
            "You are JARVIS. Saved memory: prefers value.",
        )
        self.assertIn("Saved memory: prefers value", prompt)
        self.assertIn("User: Compare two laptops.", prompt)
        self.assertIn("JARVIS: Option one is faster.", prompt)
        self.assertIn("User: What about the second option?", prompt)

    def test_gemini_client_stays_open_during_request_and_closes_after(self):
        google_module = types.ModuleType("google")
        genai_module = types.ModuleType("google.genai")
        state = {"closed": False, "called": False}

        class FakeModels:
            def generate_content(self, **kwargs):
                self_outer = state
                if self_outer["closed"]:
                    raise RuntimeError("Cannot send a request, as the client has been closed.")
                self_outer["called"] = True
                return types.SimpleNamespace(text="Gemini works")

        class FakeClient:
            def __init__(self, api_key):
                self.models = FakeModels()
            def close(self):
                state["closed"] = True

        genai_module.Client = FakeClient
        google_module.genai = genai_module
        with patch.dict(sys.modules, {"google": google_module, "google.genai": genai_module}):
            answer, provider = generate_response("hello", groq_key="", gemini_key="test-key")
        self.assertEqual(answer, "Gemini works")
        self.assertEqual(provider, "GEMINI (gemini-2.5-flash)")
        self.assertTrue(state["called"])
        self.assertTrue(state["closed"])


if __name__ == "__main__":
    unittest.main()
