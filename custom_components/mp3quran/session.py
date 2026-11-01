"""Playback session manager for auto-advance and surah repeat."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING

from homeassistant.components.media_player import (
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_CONTENT_TYPE,
    DOMAIN as MEDIA_PLAYER_DOMAIN,
    SERVICE_PLAY_MEDIA,
    MediaPlayerState,
)
from homeassistant.const import ATTR_ENTITY_ID, STATE_IDLE, STATE_OFF, STATE_UNAVAILABLE
from homeassistant.core import Event, HomeAssistant, callback

from .const import MIME_TYPE_MP3

if TYPE_CHECKING:
    from collections.abc import Callable

    from .api import Catalog, Moshaf, Reciter
    from .coordinator import Mp3QuranCoordinator

_LOGGER = logging.getLogger(__name__)

_IDLE_STATES = {STATE_IDLE, STATE_OFF, MediaPlayerState.IDLE, MediaPlayerState.OFF}


@dataclass(slots=True)
class PlaybackSession:
    """Active continuous-playback session for one media player."""

    entity_id: str
    reciter_id: int
    moshaf_id: int
    surah: int
    auto_advance: bool
    surah_repeat: int
    plays_remaining: int
    expected_url: str
    active: bool = True


class PlaybackSessionManager:
    """Track and advance Quran playback sessions on media players."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: Mp3QuranCoordinator,
    ) -> None:
        """Initialize the session manager."""
        self.hass = hass
        self.coordinator = coordinator
        self._sessions: dict[str, PlaybackSession] = {}
        self._unsub: Callable[[], None] | None = hass.bus.async_listen(
            "state_changed",
            self._async_on_state_changed,
        )
        self._advancing: set[str] = set()

    @callback
    def async_unload(self) -> None:
        """Stop listening for state changes."""
        if self._unsub:
            self._unsub()
            self._unsub = None
        self._sessions.clear()

    @property
    def catalog(self) -> Catalog:
        """Return the current catalog."""
        return self.coordinator.data

    def get_session(self, entity_id: str) -> PlaybackSession | None:
        """Return the active session for a media player, if any."""
        return self._sessions.get(entity_id)

    async def async_start(
        self,
        entity_id: str,
        reciter: Reciter,
        moshaf: Moshaf,
        surah: int,
        *,
        auto_advance: bool,
        surah_repeat: int,
        play: bool = True,
    ) -> PlaybackSession:
        """Start or replace a playback session and optionally play now."""
        if not moshaf.has_surah(surah):
            raise ValueError(f"Surah {surah} is not available for this moshaf")

        url = moshaf.audio_url(surah)
        session = PlaybackSession(
            entity_id=entity_id,
            reciter_id=reciter.id,
            moshaf_id=moshaf.id,
            surah=surah,
            auto_advance=auto_advance,
            surah_repeat=max(1, surah_repeat),
            plays_remaining=max(1, surah_repeat),
            expected_url=url,
        )
        self._sessions[entity_id] = session
        _LOGGER.debug(
            "Started session on %s: reciter=%s moshaf=%s surah=%s repeat=%s advance=%s",
            entity_id,
            reciter.id,
            moshaf.id,
            surah,
            session.surah_repeat,
            auto_advance,
        )
        if play:
            await self._async_play_url(entity_id, url)
        return session

    def stop(self, entity_id: str) -> None:
        """Clear the session for a media player."""
        removed = self._sessions.pop(entity_id, None)
        if removed:
            _LOGGER.debug("Stopped session on %s", entity_id)

    def maybe_attach_from_url(
        self,
        entity_id: str,
        url: str,
        *,
        auto_advance: bool,
        surah_repeat: int,
    ) -> PlaybackSession | None:
        """Best-effort attach a session when Media Browser starts a known URL."""
        if not auto_advance and surah_repeat <= 1:
            return None
        if entity_id in self._sessions:
            existing = self._sessions[entity_id]
            if existing.expected_url == url and existing.active:
                return existing

        match = self.catalog.find_by_audio_url(url) if self.catalog else None
        if match is None:
            return None
        reciter, moshaf, surah = match
        session = PlaybackSession(
            entity_id=entity_id,
            reciter_id=reciter.id,
            moshaf_id=moshaf.id,
            surah=surah,
            auto_advance=auto_advance,
            surah_repeat=max(1, surah_repeat),
            plays_remaining=max(1, surah_repeat),
            expected_url=url,
        )
        self._sessions[entity_id] = session
        _LOGGER.debug("Attached session from media browser URL on %s", entity_id)
        return session

    async def _async_on_state_changed(self, event: Event) -> None:
        """Handle media player state changes for active sessions."""
        entity_id = event.data.get("entity_id")
        if not entity_id or not entity_id.startswith("media_player."):
            return

        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")
        if new_state is None:
            return

        media_id = new_state.attributes.get(ATTR_MEDIA_CONTENT_ID)
        if isinstance(media_id, str) and "mp3quran" in media_id:
            # Opportunistically attach when playing from Media Browser.
            options = self.coordinator.entry.options
            from .const import (
                CONF_AUTO_ADVANCE,
                CONF_SURAH_REPEAT,
                DEFAULT_AUTO_ADVANCE,
                DEFAULT_SURAH_REPEAT,
            )

            self.maybe_attach_from_url(
                entity_id,
                media_id,
                auto_advance=options.get(CONF_AUTO_ADVANCE, DEFAULT_AUTO_ADVANCE),
                surah_repeat=int(
                    options.get(CONF_SURAH_REPEAT, DEFAULT_SURAH_REPEAT)
                ),
            )

        session = self._sessions.get(entity_id)
        if session is None or not session.active:
            return
        if entity_id in self._advancing:
            return

        old_state_val = old_state.state if old_state else None
        new_state_val = new_state.state

        # Detect end of track: was playing, now idle/off.
        was_playing = old_state_val in {
            MediaPlayerState.PLAYING,
            "playing",
        }
        now_idle = new_state_val in _IDLE_STATES or new_state_val == STATE_UNAVAILABLE
        if not (was_playing and now_idle):
            return

        # Prefer matching expected URL; some players clear media_content_id on idle.
        current_id = None
        if old_state is not None:
            current_id = old_state.attributes.get(ATTR_MEDIA_CONTENT_ID)
        if current_id and current_id != session.expected_url:
            # Different media finished; drop our session.
            _LOGGER.debug(
                "Ignoring idle on %s; media mismatch (%s != %s)",
                entity_id,
                current_id,
                session.expected_url,
            )
            return

        await self._async_advance(session)

    async def _async_advance(self, session: PlaybackSession) -> None:
        """Repeat current surah or advance to the next one."""
        if session.entity_id in self._advancing:
            return
        self._advancing.add(session.entity_id)
        try:
            session.plays_remaining -= 1
            if session.plays_remaining > 0:
                _LOGGER.debug(
                    "Repeating surah %s on %s (%s remaining)",
                    session.surah,
                    session.entity_id,
                    session.plays_remaining,
                )
                await self._async_play_url(session.entity_id, session.expected_url)
                return

            if not session.auto_advance:
                _LOGGER.debug(
                    "Session complete on %s (auto-advance disabled)",
                    session.entity_id,
                )
                self.stop(session.entity_id)
                return

            catalog = self.catalog
            if catalog is None:
                self.stop(session.entity_id)
                return
            reciter = catalog.get_reciter(session.reciter_id)
            if reciter is None:
                self.stop(session.entity_id)
                return
            moshaf = reciter.get_moshaf(session.moshaf_id)
            if moshaf is None:
                self.stop(session.entity_id)
                return

            next_surah = moshaf.next_surah(session.surah)
            if next_surah is None:
                _LOGGER.debug(
                    "Reached last surah on %s; ending session",
                    session.entity_id,
                )
                self.stop(session.entity_id)
                return

            url = moshaf.audio_url(next_surah)
            session.surah = next_surah
            session.expected_url = url
            session.plays_remaining = session.surah_repeat
            _LOGGER.debug(
                "Advancing to surah %s on %s",
                next_surah,
                session.entity_id,
            )
            await self._async_play_url(session.entity_id, url)
        finally:
            self._advancing.discard(session.entity_id)

    async def _async_play_url(self, entity_id: str, url: str) -> None:
        """Send play_media for a direct audio URL."""
        await self.hass.services.async_call(
            MEDIA_PLAYER_DOMAIN,
            SERVICE_PLAY_MEDIA,
            {
                ATTR_ENTITY_ID: entity_id,
                ATTR_MEDIA_CONTENT_ID: url,
                ATTR_MEDIA_CONTENT_TYPE: MIME_TYPE_MP3,
            },
            blocking=True,
        )
