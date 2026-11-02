"""Tests for Lovelace card registration."""

from __future__ import annotations

from pathlib import Path

import pytest

from custom_components.mp3quran import async_setup
from custom_components.mp3quran.const import CARD_URL
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.core import HomeAssistant


@pytest.mark.asyncio
async def test_async_setup_registers_card_once() -> None:
    add_extra_js_url.calls.clear()
    hass = HomeAssistant()

    assert await async_setup(hass, {}) is True
    assert await async_setup(hass, {}) is True

    assert add_extra_js_url.calls == [CARD_URL]
    hass.http.async_register_static_paths.assert_awaited_once()
    paths = hass.http.async_register_static_paths.await_args.args[0]
    by_url = {item.url_path: item for item in paths}
    assert set(by_url) == {"/mp3quran", "/mp3quran_brand"}
    assert by_url["/mp3quran"].cache_headers is False
    assert Path(by_url["/mp3quran"].path).name == "www"
    assert (Path(by_url["/mp3quran"].path) / "mp3quran-card.js").is_file()
    assert (Path(by_url["/mp3quran_brand"].path) / "icon.png").is_file()
