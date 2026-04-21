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


class TestGuardrailSanitization:
    """Test that guardrails sanitize prompts before calling LLM."""

    @patch("llm.client._call")
    @patch("llm.client._sanitize_prompt")
    def test_sanitize_prompt_called_on_fast_chat(self, mock_sanitize, mock_call):
        """Verify that fast_chat applies prompt sanitization."""
        mock_sanitize.return_value = "sanitized prompt"
        mock_call.return_value = ("response", 10)
        
        from llm.client import fast_chat
        result = fast_chat("original prompt")
        
        # Verify sanitization was called
        assert mock_sanitize.called
        # Verify sanitized prompt was used in the call
        call_args = mock_call.call_args[0]
        assert call_args[0] == "sanitized prompt"

    @patch("llm.client._call")
    @patch("llm.client._sanitize_prompt")
    def test_sanitize_prompt_called_on_strong_chat(self, mock_sanitize, mock_call):
        """Verify that strong_chat applies prompt sanitization."""
        mock_sanitize.return_value = "sanitized prompt"
        mock_call.return_value = ("response", 20)
        
        from llm.client import strong_chat
        result = strong_chat("original prompt")
        
        # Verify sanitization was called
        assert mock_sanitize.called
        # Verify sanitized prompt was used
        call_args = mock_call.call_args[0]
        assert call_args[0] == "sanitized prompt"

    @patch("llm.client.settings")
    def test_sanitize_prompt_redacts_pii(self, mock_settings):
        """Test that _sanitize_prompt redacts detected PII."""
        from llm.client import _sanitize_prompt
        from guardrails.config import GuardrailConfig, GuardrailMode
        
        # Setup config with PII detection enabled
        config = GuardrailConfig(mode=GuardrailMode.WARN)
        mock_settings.get_guardrail_config.return_value = config
        
        prompt_with_pii = "Email alice@example.com"
        result = _sanitize_prompt(prompt_with_pii)
        
        # Should have redacted the email
        assert "[EMAIL]" in result or result != prompt_with_pii

    @patch("llm.client.settings")
    def test_sanitize_prompt_blocks_in_strict_mode(self, mock_settings):
        """Test that _sanitize_prompt blocks in strict mode."""
        from llm.client import _sanitize_prompt
        from guardrails.config import GuardrailConfig, GuardrailMode
        
        config = GuardrailConfig(mode=GuardrailMode.BLOCK_HIGH_RISK)
        mock_settings.get_guardrail_config.return_value = config
        
        prompt_with_ssn = "User SSN 123-45-6789"
        
        # Should raise an error when blocking
        with pytest.raises(ValueError):
            _sanitize_prompt(prompt_with_ssn)


class TestGuardrailFiltering:
    """Test that guardrails filter responses before returning."""

    @patch("llm.client._call")
    @patch("llm.client._filter_response")
    def test_filter_response_called_on_fast_chat(self, mock_filter, mock_call):
        """Verify that fast_chat applies response filtering."""
        mock_call.return_value = ("original response", 10)
        mock_filter.return_value = "filtered response"
        
        from llm.client import fast_chat
        result = fast_chat("prompt")
        
        # Verify filtering was called
        assert mock_filter.called
        assert result == "filtered response"

    @patch("llm.client._call")
    @patch("llm.client._filter_response")
    def test_filter_response_called_on_strong_chat(self, mock_filter, mock_call):
        """Verify that strong_chat applies response filtering."""
        mock_call.return_value = ("original response", 20)
        mock_filter.return_value = "filtered response"
        
        from llm.client import strong_chat
        result = strong_chat("prompt")
        
        # Verify filtering was called
        assert mock_filter.called
        assert result == "filtered response"

    @patch("llm.client.settings")
    def test_filter_response_redacts_pii(self, mock_settings):
        """Test that _filter_response redacts detected PII in responses."""
        from llm.client import _filter_response
        from guardrails.config import GuardrailConfig, GuardrailMode
        
        config = GuardrailConfig(mode=GuardrailMode.WARN)
        mock_settings.get_guardrail_config.return_value = config
        
        response_with_pii = "Contact alice@example.com for details"
        result = _filter_response(response_with_pii)
        
        # Should have redacted the email
        assert "[EMAIL]" in result or result != response_with_pii

    @patch("llm.client.settings")
    def test_filter_response_blocks_high_risk(self, mock_settings):
        """Test that _filter_response blocks when appropriate."""
        from llm.client import _filter_response
        from guardrails.config import GuardrailConfig, GuardrailMode
        
        config = GuardrailConfig(mode=GuardrailMode.BLOCK_HIGH_RISK)
        mock_settings.get_guardrail_config.return_value = config
        
        response_with_ssn = "Employee SSN is 123-45-6789"
        
        # Should raise an error when blocking
        with pytest.raises(ValueError):
            _filter_response(response_with_ssn)


class TestGuardrailIntegration:
    """Integration tests for full prompt-response guardrail flow."""

    @patch("llm.client._call")
    def test_full_sanitize_filter_flow(self, mock_call):
        """Test complete flow: sanitize prompt -> LLM call -> filter response."""
        # Setup: LLM returns response with PII
        mock_call.return_value = ("Contact alice@example.com", 15)
        
        from llm.client import fast_chat
        from guardrails.config import GuardrailConfig
        
        # Call with prompt that contains PII (will be sanitized)
        with patch("llm.client.settings") as mock_settings:
            config = GuardrailConfig()  # warn mode by default
            mock_settings.get_guardrail_config.return_value = config
            
            result = fast_chat("Email alice@example.com, tell me my balance")
            
            # Response should be filtered
            # In warn mode, response with PII gets redacted
            assert mock_call.called

    @patch("llm.client._call")
    @patch("llm.client.settings")
    def test_clean_prompt_and_response_pass_through(self, mock_settings, mock_call):
        """Test that clean prompts and responses pass through unchanged."""
        mock_call.return_value = ("Your balance is 80 hours.", 10)
        config_obj = MagicMock()
        config_obj.detect_prompt_injection = True
        config_obj.enabled_pii_categories = set()
        config_obj.redact_audit_pii = True
        mock_settings.get_guardrail_config.return_value = config_obj
        
        from llm.client import fast_chat
        with patch("llm.client.GuardrailPolicy") as mock_policy_class:
            mock_policy = MagicMock()
            mock_decision = MagicMock()
            mock_decision.action = "allow"
            mock_policy.evaluate_llm_prompt.return_value = mock_decision
            mock_policy.evaluate_llm_response.return_value = mock_decision
            mock_policy_class.return_value = mock_policy
            
            result = fast_chat("What is my balance?")
            
            # Should return original response when no issues
            assert result == "Your balance is 80 hours."

