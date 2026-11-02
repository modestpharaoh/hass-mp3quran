"""Tests for MP3 Quran config and options flow."""

from __future__ import annotations

import pytest

from custom_components.mp3quran.config_flow import Mp3QuranConfigFlow
from custom_components.mp3quran.const import (
    CONF_DISPLAY_LANGUAGE,
    CONF_SURAH_REPEAT,
    DEFAULT_AUTO_ADVANCE,
    DEFAULT_DISPLAY_LANGUAGE,
    DEFAULT_SURAH_REPEAT,
    DOMAIN,
    get_display_language,
)


@pytest.mark.asyncio
async def test_user_step_creates_entry() -> None:
    flow = Mp3QuranConfigFlow()
    flow.hass = None  # type: ignore[assignment]

    form = await flow.async_step_user(user_input=None)
    assert form["type"] == "form"
    assert form["step_id"] == "user"

    result = await flow.async_step_user(
        {
            CONF_DISPLAY_LANGUAGE: "arabic",
            CONF_SURAH_REPEAT: 3,
        }
    )
    assert result["type"] == "create_entry"
    assert result["title"] == "MP3 Quran"
    assert result["data"] == {}
    assert result["options"][CONF_DISPLAY_LANGUAGE] == "arabic"
    assert CONF_SURAH_REPEAT in result["options"]
    assert result["options"][CONF_SURAH_REPEAT] == 3
    assert "auto_advance" not in result["options"]


@pytest.mark.asyncio
async def test_single_instance_abort() -> None:
    flow = Mp3QuranConfigFlow()
    flow._async_current_entries = lambda: [object()]  # type: ignore[method-assign]
    result = await flow.async_step_user()
    assert result["type"] == "abort"
    assert result["reason"] == "single_instance_allowed"


@pytest.mark.asyncio
async def test_defaults_on_empty_submit() -> None:
    flow = Mp3QuranConfigFlow()
    result = await flow.async_step_user({})
    assert result["type"] == "create_entry"
    assert result["options"][CONF_DISPLAY_LANGUAGE] == DEFAULT_DISPLAY_LANGUAGE
    assert result["options"][CONF_SURAH_REPEAT] == DEFAULT_SURAH_REPEAT
    assert "auto_advance" not in result["options"]
    assert DEFAULT_AUTO_ADVANCE is False
    assert DOMAIN == "mp3quran"


def test_legacy_sort_language_option() -> None:
    assert get_display_language({"sort_language": "arabic"}) == "arabic"
    assert get_display_language({"display_language": "english"}) == "english"
    assert get_display_language({}) == DEFAULT_DISPLAY_LANGUAGE
