"""Services for MP3 Quran continuous playback."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_AUTO_ADVANCE,
    ATTR_MOSHAF_ID,
    ATTR_RECITER_ID,
    ATTR_SURAH,
    ATTR_SURAH_REPEAT,
    CONF_AUTO_ADVANCE,
    CONF_SURAH_REPEAT,
    DEFAULT_AUTO_ADVANCE,
    DEFAULT_SURAH_REPEAT,
    DOMAIN,
    MAX_SURAH_REPEAT,
    MIN_SURAH_REPEAT,
    SERVICE_PLAY,
    SERVICE_STOP,
)
from .coordinator import Mp3QuranCoordinator
from .session import PlaybackSessionManager

PLAY_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Required(ATTR_RECITER_ID): vol.Coerce(int),
        vol.Optional(ATTR_MOSHAF_ID): vol.Coerce(int),
        vol.Optional(ATTR_SURAH, default=1): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=114)
        ),
        vol.Optional(ATTR_AUTO_ADVANCE): cv.boolean,
        vol.Optional(ATTR_SURAH_REPEAT): vol.All(
            vol.Coerce(int),
            vol.Range(min=MIN_SURAH_REPEAT, max=MAX_SURAH_REPEAT),
        ),
    }
)

STOP_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
    }
)


def async_register_services(
    hass: HomeAssistant,
    coordinator: Mp3QuranCoordinator,
    sessions: PlaybackSessionManager,
) -> None:
    """Register domain services once."""

    async def async_handle_play(call: ServiceCall) -> None:
        """Start continuous playback on one or more media players."""
        catalog = coordinator.data
        if catalog is None:
            raise HomeAssistantError("MP3 Quran catalog is not ready")

        reciter_id = call.data[ATTR_RECITER_ID]
        reciter = catalog.get_reciter(reciter_id)
        if reciter is None:
            raise HomeAssistantError(f"Unknown reciter_id: {reciter_id}")

        moshaf_id = call.data.get(ATTR_MOSHAF_ID)
        moshaf = (
            reciter.get_moshaf(moshaf_id)
            if moshaf_id is not None
            else reciter.default_moshaf()
        )
        if moshaf is None:
            raise HomeAssistantError("No moshaf available for this reciter")

        surah = call.data[ATTR_SURAH]
        if not moshaf.has_surah(surah):
            raise HomeAssistantError(
                f"Surah {surah} is not available for moshaf {moshaf.id}"
            )

        options = coordinator.entry.options
        auto_advance = call.data.get(
            ATTR_AUTO_ADVANCE,
            options.get(CONF_AUTO_ADVANCE, DEFAULT_AUTO_ADVANCE),
        )
        surah_repeat = call.data.get(
            ATTR_SURAH_REPEAT,
            options.get(CONF_SURAH_REPEAT, DEFAULT_SURAH_REPEAT),
        )

        for entity_id in call.data[ATTR_ENTITY_ID]:
            await sessions.async_start(
                entity_id,
                reciter,
                moshaf,
                surah,
                auto_advance=bool(auto_advance),
                surah_repeat=int(surah_repeat),
            )

    async def async_handle_stop(call: ServiceCall) -> None:
        """Stop continuous playback sessions."""
        for entity_id in call.data[ATTR_ENTITY_ID]:
            sessions.stop(entity_id)

    if not hass.services.has_service(DOMAIN, SERVICE_PLAY):
        hass.services.async_register(
            DOMAIN,
            SERVICE_PLAY,
            async_handle_play,
            schema=PLAY_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_STOP):
        hass.services.async_register(
            DOMAIN,
            SERVICE_STOP,
            async_handle_stop,
            schema=STOP_SCHEMA,
        )


def async_unregister_services(hass: HomeAssistant) -> None:
    """Unregister domain services when the last entry unloads."""
    for service in (SERVICE_PLAY, SERVICE_STOP):
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)
