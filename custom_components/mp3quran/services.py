"""Services for MP3 Quran continuous playback."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.service import async_extract_entity_ids

from .const import (
    ATTR_AUTO_ADVANCE,
    ATTR_LOOP,
    ATTR_MOSHAF_ID,
    ATTR_RECITER_ID,
    ATTR_SURAH,
    ATTR_SURAH_REPEAT,
    CONF_SURAH_REPEAT,
    DEFAULT_AUTO_ADVANCE,
    DEFAULT_LOOP,
    DEFAULT_SURAH_REPEAT,
    DOMAIN,
    MAX_SURAH_REPEAT,
    MIN_SURAH_REPEAT,
    SERVICE_NEXT_SURAH,
    SERVICE_PLAY,
    SERVICE_PREVIOUS_SURAH,
    SERVICE_STOP,
)
from .coordinator import Mp3QuranCoordinator
from .session import PlaybackSessionManager

# ALLOW_EXTRA so HA target fields (device_id / area_id) are not rejected by voluptuous.
PLAY_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Required(ATTR_RECITER_ID): vol.Coerce(int),
        vol.Optional(ATTR_MOSHAF_ID): vol.Coerce(int),
        vol.Optional(ATTR_SURAH, default=1): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=114)
        ),
        vol.Optional(ATTR_AUTO_ADVANCE, default=DEFAULT_AUTO_ADVANCE): cv.boolean,
        vol.Optional(ATTR_LOOP, default=DEFAULT_LOOP): cv.boolean,
        vol.Optional(ATTR_SURAH_REPEAT): vol.All(
            vol.Coerce(int),
            vol.Range(min=MIN_SURAH_REPEAT, max=MAX_SURAH_REPEAT),
        ),
    },
    extra=vol.ALLOW_EXTRA,
)

STOP_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
    },
    extra=vol.ALLOW_EXTRA,
)


def async_register_services(
    hass: HomeAssistant,
    coordinator: Mp3QuranCoordinator,
    sessions: PlaybackSessionManager,
) -> None:
    """Register domain services once."""

    async def _entity_ids(call: ServiceCall) -> list[str]:
        """Resolve media_player targets from entity/device/area selection."""
        extracted: set[str] = set()

        # Newer HA: async_extract_entity_ids(service_call)
        # Older HA: async_extract_entity_ids(hass, service_call)
        try:
            extracted.update(await async_extract_entity_ids(call))
        except TypeError:
            try:
                extracted.update(await async_extract_entity_ids(hass, call))
            except Exception:  # noqa: BLE001
                extracted = set()
        except Exception:  # noqa: BLE001
            extracted = set()

        raw = call.data.get(ATTR_ENTITY_ID)
        if raw:
            extracted.update([raw] if isinstance(raw, str) else list(raw))

        extracted.update(_media_players_from_registry(hass, call.data))

        media_players = sorted(
            entity_id
            for entity_id in extracted
            if isinstance(entity_id, str) and entity_id.startswith("media_player.")
        )
        if not media_players:
            raise HomeAssistantError(
                "No media_player target found. Select a media player entity "
                "(or a device that includes one)."
            )
        return media_players

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
        auto_advance = call.data.get(ATTR_AUTO_ADVANCE, DEFAULT_AUTO_ADVANCE)
        loop = call.data.get(ATTR_LOOP, DEFAULT_LOOP)
        surah_repeat = call.data.get(
            ATTR_SURAH_REPEAT,
            options.get(CONF_SURAH_REPEAT, DEFAULT_SURAH_REPEAT),
        )

        for entity_id in await _entity_ids(call):
            await sessions.async_start(
                entity_id,
                reciter,
                moshaf,
                surah,
                auto_advance=bool(auto_advance),
                surah_repeat=int(surah_repeat),
                loop=bool(loop),
            )

    async def async_handle_stop(call: ServiceCall) -> None:
        """Stop continuous playback sessions and current audio."""
        for entity_id in await _entity_ids(call):
            await sessions.async_stop(entity_id, stop_media=True)

    async def _handle_skip(call: ServiceCall, step: int) -> None:
        """Move each targeted session to the neighboring surah."""
        for entity_id in await _entity_ids(call):
            try:
                await sessions.async_skip(entity_id, step=step)
            except ValueError as err:
                raise HomeAssistantError(str(err)) from err

    async def async_handle_next(call: ServiceCall) -> None:
        """Play the next surah in the active session."""
        await _handle_skip(call, 1)

    async def async_handle_previous(call: ServiceCall) -> None:
        """Play the previous surah in the active session."""
        await _handle_skip(call, -1)

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
    if not hass.services.has_service(DOMAIN, SERVICE_NEXT_SURAH):
        hass.services.async_register(
            DOMAIN,
            SERVICE_NEXT_SURAH,
            async_handle_next,
            schema=STOP_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_PREVIOUS_SURAH):
        hass.services.async_register(
            DOMAIN,
            SERVICE_PREVIOUS_SURAH,
            async_handle_previous,
            schema=STOP_SCHEMA,
        )


def _as_id_list(value: Any) -> list[str]:
    """Normalize a target id field to a list of strings."""
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    return [item for item in value if isinstance(item, str)]


def _media_players_from_registry(hass: HomeAssistant, data: dict[str, Any]) -> set[str]:
    """Expand device_id / area_id targets to media_player entity ids."""
    device_ids = _as_id_list(data.get("device_id"))
    area_ids = _as_id_list(data.get("area_id"))
    if not device_ids and not area_ids:
        return set()

    try:
        registry = er.async_get(hass)
    except Exception:  # noqa: BLE001 - tests without a registry
        return set()

    found: set[str] = set()
    entities = registry.entities

    def _add(entry: Any) -> None:
        entity_id = getattr(entry, "entity_id", "")
        if not entity_id.startswith("media_player."):
            return
        if getattr(entry, "disabled_by", None):
            return
        found.add(entity_id)

    for device_id in device_ids:
        getter = getattr(entities, "get_entries_for_device_id", None)
        entries = getter(device_id) if getter else []
        for entry in entries:
            _add(entry)

    for area_id in area_ids:
        getter = getattr(entities, "get_entries_for_area_id", None)
        entries = getter(area_id) if getter else []
        for entry in entries:
            _add(entry)

    return found


def async_unregister_services(hass: HomeAssistant) -> None:
    """Unregister domain services when the last entry unloads."""
    for service in (
        SERVICE_PLAY,
        SERVICE_STOP,
        SERVICE_NEXT_SURAH,
        SERVICE_PREVIOUS_SURAH,
    ):
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)
