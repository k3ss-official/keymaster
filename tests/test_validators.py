"""Smoke tests for key validators (no live API calls)."""

from unittest.mock import patch, MagicMock

import pytest


def _make_resp(status: int) -> MagicMock:
    m = MagicMock()
    m.status_code = status
    return m


# ── Anthropic ────────────────────────────────────────────────────────────

def test_anthropic_validate_ok():
    from rotators.api.anthropic import Rotator
    with patch("httpx.get", return_value=_make_resp(200)):
        ok, msg = Rotator().validate("sk-test")
    assert ok
    assert msg == "OK"


def test_anthropic_validate_fail():
    from rotators.api.anthropic import Rotator
    with patch("httpx.get", return_value=_make_resp(401)):
        ok, msg = Rotator().validate("bad-key")
    assert not ok
    assert "401" in msg


# ── OpenAI ───────────────────────────────────────────────────────────────

def test_openai_validate_ok():
    from rotators.api.openai import Rotator
    with patch("httpx.get", return_value=_make_resp(200)):
        ok, msg = Rotator().validate("sk-test")
    assert ok


# ── OpenRouter ───────────────────────────────────────────────────────────

def test_openrouter_validate_ok():
    from rotators.api.openrouter import Rotator
    with patch("httpx.get", return_value=_make_resp(200)):
        ok, msg = Rotator().validate("sk-or-test")
    assert ok


# ── GitHub PAT ───────────────────────────────────────────────────────────

def test_github_pat_validate_ok():
    from rotators.api.github_pat import Rotator
    with patch("httpx.get", return_value=_make_resp(200)):
        ok, msg = Rotator().validate("ghp_test")
    assert ok


# ── Tavily ───────────────────────────────────────────────────────────────

def test_tavily_validate_ok():
    from rotators.api.tavily import Rotator
    with patch("httpx.post", return_value=_make_resp(200)):
        ok, msg = Rotator().validate("tvly-test")
    assert ok


# ── Gemini ───────────────────────────────────────────────────────────────

def test_gemini_validate_ok():
    from rotators.api.gemini import Rotator
    with patch("httpx.get", return_value=_make_resp(200)):
        ok, msg = Rotator().validate("AIza-test")
    assert ok
