"""The MP3 Quran integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .coordinator import Mp3QuranCoordinator
from .services import async_register_services, async_unregister_services
from .session import PlaybackSessionManager

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


@dataclass(slots=True)
class Mp3QuranRuntimeData:
    """Runtime data attached to the config entry."""

    coordinator: Mp3QuranCoordinator
    sessions: PlaybackSessionManager


type Mp3QuranConfigEntry = ConfigEntry[Mp3QuranRuntimeData]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up from YAML (config entry only)."""
    return True


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
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    _LOGGER.info(
        "MP3 Quran media source ready (%s reciters)",
        len(coordinator.data.reciters),
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: Mp3QuranConfigEntry) -> bool:
    """Unload a config entry."""
    entry.runtime_data.sessions.async_unload()

    other_entries = [
        item
        for item in hass.config_entries.async_entries(DOMAIN)
        if item.entry_id != entry.entry_id
    ]
    if not other_entries:
        async_unregister_services(hass)

    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: Mp3QuranConfigEntry
) -> None:
    """Handle options updates by reloading the entry."""
    await hass.config_entries.async_reload(entry.entry_id)
