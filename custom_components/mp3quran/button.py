"""Stop-session buttons for MP3 Quran."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MP3 Quran stop buttons (created dynamically per player)."""
    sessions = entry.runtime_data.sessions
    known: dict[str, Mp3QuranStopButton] = {}

    async def _ensure_button(media_player_entity_id: str) -> None:
        if media_player_entity_id in known:
            return
        button = Mp3QuranStopButton(entry, sessions, media_player_entity_id)
        known[media_player_entity_id] = button
        async_add_entities([button])
        _LOGGER.debug("Created stop button for %s", media_player_entity_id)

    sessions.set_button_factory(_ensure_button)


class Mp3QuranStopButton(ButtonEntity):
    """Button that stops an MP3 Quran session on a specific media player."""

    _attr_has_entity_name = True
    _attr_translation_key = "stop_session"
    _attr_icon = "mdi:stop-circle-outline"

    def __init__(
        self,
        entry: ConfigEntry,
        sessions: Any,
        media_player_entity_id: str,
    ) -> None:
        """Initialize the stop button."""
        self._entry = entry
        self._sessions = sessions
        self._media_player_entity_id = media_player_entity_id
        suffix = media_player_entity_id.removeprefix("media_player.")
        self._attr_unique_id = f"{entry.entry_id}_stop_{suffix}"
        # Friendly name includes the player for dashboards.
        self._attr_name = f"Stop MP3 Quran ({suffix.replace('_', ' ').title()})"

    @property
    def available(self) -> bool:
        """Buttons remain available after sessions end (had a session)."""
        return True

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose linked media player and whether a session is active."""
        session = self._sessions.get_session(self._media_player_entity_id)
        return {
            "media_player": self._media_player_entity_id,
            "session_active": session is not None,
            "session": session.as_attr_dict() if session else None,
        }

    @property
    def device_info(self) -> DeviceInfo:
        """Group under the MP3 Quran service device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name="MP3 Quran",
            manufacturer="mp3quran.net",
            model="Media Source",
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_press(self) -> None:
        """Stop the Quran session and current audio on the linked player."""
        await self._sessions.async_stop(
            self._media_player_entity_id, stop_media=True
        )
        self.async_write_ha_state()
