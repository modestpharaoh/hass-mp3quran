"""Tests for MP3 Quran config and options flow."""

from __future__ import annotations

import pytest

from custom_components.mp3quran.config_flow import Mp3QuranConfigFlow
from custom_components.mp3quran.const import (
    CONF_AUTO_ADVANCE,
    CONF_SORT_LANGUAGE,
    CONF_SURAH_REPEAT,
    DEFAULT_AUTO_ADVANCE,
    DEFAULT_SORT_LANGUAGE,
    DEFAULT_SURAH_REPEAT,
    DOMAIN,
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
            CONF_SORT_LANGUAGE: "arabic",
            CONF_AUTO_ADVANCE: False,
            CONF_SURAH_REPEAT: 3,
        }
    )
    assert result["type"] == "create_entry"
    assert result["title"] == "MP3 Quran"
    assert result["data"] == {}
    assert result["options"][CONF_SORT_LANGUAGE] == "arabic"
    assert result["options"][CONF_AUTO_ADVANCE] is False
    assert result["options"][CONF_SURAH_REPEAT] == 3


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
    assert result["options"][CONF_SORT_LANGUAGE] == DEFAULT_SORT_LANGUAGE
    assert result["options"][CONF_AUTO_ADVANCE] == DEFAULT_AUTO_ADVANCE
    assert result["options"][CONF_SURAH_REPEAT] == DEFAULT_SURAH_REPEAT
    assert DOMAIN == "mp3quran"
