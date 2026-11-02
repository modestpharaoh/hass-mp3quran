"""Tests for Lovelace card registration."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from custom_components.mp3quran import async_setup
from custom_components.mp3quran.const import CARD_URL
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.core import HomeAssistant

CARD_RESOURCE = f"{CARD_URL}?v=1.4.5"


def _run_tasks(hass: HomeAssistant) -> None:
    """Run card registration immediately, the way a fully started Home Assistant does."""
    from homeassistant.core import CoreState

    hass.state = CoreState.running
    hass.is_running = True

    def _create_task(coro):
        return asyncio.get_running_loop().create_task(coro)

    hass.async_create_task = _create_task


class _Resources:
    """Minimal Lovelace resource collection."""

    def __init__(self, items=None):
        self.loaded = False
        self.items = list(items or [])

    async def async_get_info(self):
        self.loaded = True
        return {}

    def async_items(self):
        return list(self.items)

    async def async_create_item(self, item):
        stored = {"id": f"res-{len(self.items) + 1}", **item}
        self.items.append(stored)
        return stored

    async def async_update_item(self, item_id, item):
        for stored in self.items:
            if stored["id"] == item_id:
                stored.update(item)
                return stored
        raise KeyError(item_id)


def _lovelace(resources):
    return type("Lovelace", (), {"resource_mode": "storage", "resources": resources})()


@pytest.mark.asyncio
async def test_async_setup_registers_card_once() -> None:
    add_extra_js_url.calls.clear()
    hass = HomeAssistant()
    _run_tasks(hass)

    assert await async_setup(hass, {}) is True
    await asyncio.sleep(0)
    assert await async_setup(hass, {}) is True
    await asyncio.sleep(0)

    assert add_extra_js_url.calls == [CARD_RESOURCE]
    hass.http.async_register_static_paths.assert_awaited_once()
    paths = hass.http.async_register_static_paths.await_args.args[0]
    by_url = {item.url_path: item for item in paths}
    assert set(by_url) == {"/mp3quran", "/mp3quran_brand"}
    assert by_url["/mp3quran"].cache_headers is False
    assert Path(by_url["/mp3quran"].path).name == "www"
    assert (Path(by_url["/mp3quran"].path) / "mp3quran-card.js").is_file()
    assert (Path(by_url["/mp3quran_brand"].path) / "icon.png").is_file()


@pytest.mark.asyncio
async def test_storage_mode_registers_dashboard_resource() -> None:
    add_extra_js_url.calls.clear()
    hass = HomeAssistant()
    _run_tasks(hass)
    resources = _Resources(
        [{"id": "old", "res_type": "module", "url": f"{CARD_URL}?v=1.4.1"}]
    )
    hass.data["lovelace"] = _lovelace(resources)

    assert await async_setup(hass, {}) is True
    await asyncio.sleep(0)

    assert add_extra_js_url.calls == []
    assert resources.items == [
        {"id": "old", "res_type": "module", "url": CARD_RESOURCE}
    ]


@pytest.mark.asyncio
async def test_storage_mode_creates_resource_when_missing() -> None:
    add_extra_js_url.calls.clear()
    hass = HomeAssistant()
    _run_tasks(hass)
    resources = _Resources()
    hass.data["lovelace"] = _lovelace(resources)

    assert await async_setup(hass, {}) is True
    await asyncio.sleep(0)

    assert add_extra_js_url.calls == []
    assert resources.items == [
        {"id": "res-1", "res_type": "module", "url": CARD_RESOURCE}
    ]


@pytest.mark.asyncio
async def test_resource_is_added_when_home_assistant_finishes_starting() -> None:
    add_extra_js_url.calls.clear()
    hass = HomeAssistant()
    hass.is_running = False
    resources = _Resources()
    started = []

    def _listen_once(_event_type, action):
        started.append(action)

    hass.bus.async_listen_once = _listen_once
    hass.async_create_task = lambda coro: asyncio.get_running_loop().create_task(coro)

    assert await async_setup(hass, {}) is True
    assert resources.items == []

    hass.data["lovelace"] = _lovelace(resources)
    result = started[0](None)
    if asyncio.iscoroutine(result):
        await result
    await asyncio.sleep(0)

    assert add_extra_js_url.calls == []
    assert resources.items == [
        {"id": "res-1", "res_type": "module", "url": CARD_RESOURCE}
    ]
