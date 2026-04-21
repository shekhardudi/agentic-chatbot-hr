"""
Tests for llm/client.py — fast_chat and strong_chat wrappers.

Patches the underlying provider call functions so no real API calls are made.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestFastChat:
    @patch("llm.client._call")
    def test_returns_text(self, mock_call):
        mock_call.return_value = ("Hello!", 10)
        from llm.client import fast_chat
        result = fast_chat("Say hello")
        assert result == "Hello!"

    @patch("llm.client._call")
    def test_uses_fast_model(self, mock_call):
        mock_call.return_value = ("response", 5)
        from llm.client import fast_chat, settings
        fast_chat("prompt")
        call_args = mock_call.call_args
        assert call_args[0][2] == settings.llm_fast_model

    @patch("llm.client._call")
    def test_passes_system_prompt(self, mock_call):
        mock_call.return_value = ("ok", 3)
        from llm.client import fast_chat
        fast_chat("user message", system="You are helpful.")
        call_args = mock_call.call_args
        assert call_args[0][1] == "You are helpful."

    @patch("llm.client._call")
    def test_default_system_is_empty_string(self, mock_call):
        mock_call.return_value = ("ok", 3)
        from llm.client import fast_chat
        fast_chat("prompt")
        call_args = mock_call.call_args
        assert call_args[0][1] == ""

    @patch("llm.client._call")
    def test_max_tokens_is_1024(self, mock_call):
        mock_call.return_value = ("ok", 3)
        from llm.client import fast_chat
        fast_chat("prompt")
        call_args = mock_call.call_args
        assert call_args[0][3] == 1024


class TestStrongChat:
    @patch("llm.client._call")
    def test_returns_text(self, mock_call):
        mock_call.return_value = ("Detailed answer.", 50)
        from llm.client import strong_chat
        result = strong_chat("Explain this policy")
        assert result == "Detailed answer."

    @patch("llm.client._call")
    def test_uses_strong_model(self, mock_call):
        mock_call.return_value = ("answer", 20)
        from llm.client import strong_chat, settings
        strong_chat("prompt")
        call_args = mock_call.call_args
        assert call_args[0][2] == settings.llm_strong_model

    @patch("llm.client._call")
    def test_max_tokens_is_2048(self, mock_call):
        mock_call.return_value = ("answer", 20)
        from llm.client import strong_chat
        strong_chat("prompt")
        call_args = mock_call.call_args
        assert call_args[0][3] == 2048

    @patch("llm.client._call")
    def test_passes_system_prompt(self, mock_call):
        mock_call.return_value = ("ok", 3)
        from llm.client import strong_chat
        strong_chat("user message", system="Be precise.")
        call_args = mock_call.call_args
        assert call_args[0][1] == "Be precise."
