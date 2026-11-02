"""The MP3 Quran integration."""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, Platform
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import CARD_URL, DOMAIN
from .coordinator import Mp3QuranCoordinator
from .services import async_register_services, async_unregister_services
from .session import PlaybackSessionManager

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]


@dataclass(slots=True)
class Mp3QuranRuntimeData:
    """Runtime data attached to the config entry."""

    coordinator: Mp3QuranCoordinator
    sessions: PlaybackSessionManager


type Mp3QuranConfigEntry = ConfigEntry[Mp3QuranRuntimeData]


_STATIC_READY = "static_ready"
_CARD_RESOURCE_READY = "card_resource_ready"


def _card_url() -> str:
    """Return the card URL, including the integration version for cache busting."""
    root = Path(__file__).parent
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    return f"{CARD_URL}?v={manifest['version']}"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up from YAML (config entry only) and register the Lovelace card."""
    await _async_register_static(hass)
    _schedule_card_resource(hass)
    return True


def _ha_has_started(hass: HomeAssistant) -> bool:
    """Return True only after startup, not while Home Assistant is still starting.

    hass.is_running is already true during startup, which is too early for the
    Lovelace resource list.
    """
    return getattr(hass, "state", None) is CoreState.running


def _schedule_card_resource(hass: HomeAssistant) -> None:
    """Register the dashboard resource once Lovelace storage is available."""
    if _ha_has_started(hass):
        hass.async_create_task(_async_register_card(hass))
        return

    async def _on_started(_event) -> None:
        await _async_register_card(hass)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _on_started)


async def _async_register_static(hass: HomeAssistant) -> None:
    """Serve the card script and icon."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(_STATIC_READY):
        return
    root = Path(__file__).parent
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig("/mp3quran", str(root / "www"), False),
            StaticPathConfig("/mp3quran_brand", str(root / "brand"), False),
        ]
    )
    domain_data[_STATIC_READY] = True


async def _async_register_card(hass: HomeAssistant) -> None:
    """Add the card to the dashboard resource list.

    That is the same list HACS uses, shown under Settings, Dashboards,
    Resources. Lovelace loads it with the dashboard. The extra-js fallback is
    only for YAML mode, where that list is read-only.
    """
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(_CARD_RESOURCE_READY):
        return

    card_url = _card_url()
    lovelace = hass.data.get("lovelace")
    resources = getattr(lovelace, "resources", None)
    if getattr(lovelace, "resource_mode", None) != "storage" or resources is None:
        _LOGGER.warning(
            "MP3 Quran card was not added to dashboard resources because "
            "Lovelace storage resources are not available yet"
        )
        add_extra_js_url(hass, card_url)
        domain_data[_CARD_RESOURCE_READY] = True
        return

    try:
        if not getattr(resources, "loaded", True):
            await resources.async_get_info()
        for item in resources.async_items():
            url = str(item.get("url", ""))
            if url.split("?", 1)[0] != CARD_URL:
                continue
            if url != card_url:
                await resources.async_update_item(
                    item["id"], {"res_type": "module", "url": card_url}
                )
                _LOGGER.info("Updated MP3 Quran dashboard resource %s", card_url)
            domain_data[_CARD_RESOURCE_READY] = True
            return
        await resources.async_create_item({"res_type": "module", "url": card_url})
        _LOGGER.info("Registered MP3 Quran dashboard resource %s", card_url)
        domain_data[_CARD_RESOURCE_READY] = True
    except Exception:
        _LOGGER.exception(
            "Could not register the MP3 Quran card as a dashboard resource"
        )
        add_extra_js_url(hass, card_url)


async def async_setup_entry(hass: HomeAssistant, entry: Mp3QuranConfigEntry) -> bool:
    """Set up MP3 Quran from a config entry."""
    coordinator = Mp3QuranCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    sessions = PlaybackSessionManager(hass, coordinator)
    entry.runtime_data = Mp3QuranRuntimeData(
        coordinator=coordinator,
        sessions=sessions,
    )

    async_register_services(hass, coordinator, sessions)
    if _ha_has_started(hass):
        await _async_register_card(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    _LOGGER.info(
        "MP3 Quran media source ready (%s reciters)",
        len(coordinator.data.reciters),
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: Mp3QuranConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    entry.runtime_data.sessions.async_unload()

    other_entries = [
        item
        for item in hass.config_entries.async_entries(DOMAIN)
        if item.entry_id != entry.entry_id
    ]
    if not other_entries:
        async_unregister_services(hass)

    return unload_ok


async def _async_update_listener(
    hass: HomeAssistant, entry: Mp3QuranConfigEntry
) -> None:
    """Handle options updates by reloading the entry."""
    await hass.config_entries.async_reload(entry.entry_id)
