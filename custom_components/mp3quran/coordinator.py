"""Data update coordinator for MP3 Quran."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import Catalog, Mp3QuranApi, Mp3QuranApiError
from .const import DEFAULT_UPDATE_INTERVAL_HOURS, DOMAIN

_LOGGER = logging.getLogger(__name__)


class Mp3QuranCoordinator(DataUpdateCoordinator[Catalog]):
    """Fetch and cache the mp3quran catalog."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(hours=DEFAULT_UPDATE_INTERVAL_HOURS),
        )
        self.entry = entry
        self.api = Mp3QuranApi(async_get_clientsession(hass))

    async def _async_update_data(self) -> Catalog:
        """Fetch the latest catalog from the API."""
        try:
            return await self.api.fetch_catalog()
        except Mp3QuranApiError as err:
            raise UpdateFailed(str(err)) from err
