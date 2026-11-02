"""Playback session manager for auto-advance and surah repeat."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Coroutine
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.media_player import (
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_CONTENT_TYPE,
    ATTR_MEDIA_DURATION,
    ATTR_MEDIA_POSITION,
    DOMAIN as MEDIA_PLAYER_DOMAIN,
    SERVICE_MEDIA_STOP,
    SERVICE_PLAY_MEDIA,
    MediaPlayerState,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    EVENT_CALL_SERVICE,
    SERVICE_TURN_OFF,
    STATE_IDLE,
    STATE_OFF,
    STATE_UNAVAILABLE,
)
from homeassistant.core import Event, HomeAssistant, callback

from .const import (
    DEFAULT_AUTO_ADVANCE,
    DEFAULT_SURAH_REPEAT,
    END_OF_TRACK_RATIO,
    END_OF_TRACK_SLACK_SECONDS,
    MIME_TYPE_MP3,
    get_display_language,
)

_LOGGER = logging.getLogger(__name__)


def _same_track(content_id: str, expected_url: str, surah: int) -> bool:
    """Return True if a reported content id is still this surah.

    Cast sometimes rewrites the URL. VLC often leaves content id empty.
    """
    if content_id == expected_url:
        return True
    needle = f"{surah:03d}.mp3"
    return needle in content_id

_IDLE_STATES = {STATE_IDLE, STATE_OFF, MediaPlayerState.IDLE, MediaPlayerState.OFF}
_USER_STOP_SERVICES = {SERVICE_MEDIA_STOP, SERVICE_TURN_OFF, "media_pause"}
ATTR_MEDIA_EXTRA = "extra"

ListenerCallback = Callable[[], None]
AsyncButtonFactory = Callable[[str], Awaitable[None] | Coroutine[Any, Any, None]]


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
    title: str = ""
    artist: str = ""
    active: bool = True
    # Cached progress while playing (many players clear attrs before idle).
    last_position: float | None = None
    last_duration: float | None = None
    max_position: float = 0.0
    # Ignore end-of-track until the player has actually started this URL.
    # Stops double-advance when VLC/Cast emit extra idle events.
    pending_play: bool = False
    user_interrupted: bool = False

    def as_attr_dict(self) -> dict[str, Any]:
        """Return a serializable attribute dict for sensors."""
        return {
            "reciter_id": self.reciter_id,
            "moshaf_id": self.moshaf_id,
            "surah": self.surah,
            "auto_advance": self.auto_advance,
            "surah_repeat": self.surah_repeat,
            "plays_remaining": self.plays_remaining,
            "url": self.expected_url,
            "title": self.title,
            "artist": self.artist,
        }


class PlaybackSessionManager:
    """Track and advance Quran playback sessions on media players."""

    def __init__(self, hass: HomeAssistant, coordinator: Any) -> None:
        """Initialize the session manager."""
        self.hass = hass
        self.coordinator = coordinator
        self._sessions: dict[str, PlaybackSession] = {}
        self._unsub_state = hass.bus.async_listen(
            "state_changed",
            self._async_on_state_changed,
        )
        self._unsub_service = hass.bus.async_listen(
            EVENT_CALL_SERVICE,
            self._async_on_call_service,
        )
        self._advancing: set[str] = set()
        self._stopping: set[str] = set()
        self._listeners: list[ListenerCallback] = []
        self._ensure_stop_button: AsyncButtonFactory | None = None

    @callback
    def async_unload(self) -> None:
        """Stop listening for state changes."""
        if self._unsub_state:
            self._unsub_state()
            self._unsub_state = None
        if self._unsub_service:
            self._unsub_service()
            self._unsub_service = None
        self._sessions.clear()
        self._notify_listeners()

    @property
    def catalog(self) -> Any:
        """Return the current catalog."""
        return self.coordinator.data

    @property
    def sessions(self) -> dict[str, PlaybackSession]:
        """Return active sessions keyed by media_player entity_id."""
        return self._sessions

    def async_add_listener(self, listener: ListenerCallback) -> Callable[[], None]:
        """Register a callback invoked when sessions change."""

        @callback
        def _remove() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        self._listeners.append(listener)
        return _remove

    def set_button_factory(self, factory: AsyncButtonFactory) -> None:
        """Register a factory that ensures a stop button exists for a player."""
        self._ensure_stop_button = factory

    def get_session(self, entity_id: str) -> PlaybackSession | None:
        """Return the active session for a media player, if any."""
        return self._sessions.get(entity_id)

    def _notify_listeners(self) -> None:
        for listener in list(self._listeners):
            listener()

    def _metadata_for(
        self, reciter: Any, moshaf: Any, surah: int
    ) -> tuple[str, str, str]:
        """Build url, title, and artist for a surah."""
        language = get_display_language(self.coordinator.entry.options)
        url = moshaf.audio_url(surah)
        surah_info = self.catalog.surahs.get(surah) if self.catalog else None
        if surah_info is not None:
            title = surah_info.display_title(language)
        else:
            title = f"{surah:03d}"
        artist = reciter.localized_name(language)
        moshaf_name = moshaf.localized_name(language)
        if moshaf_name:
            artist = f"{artist} · {moshaf_name}"
        return url, title, artist

    async def async_start(
        self,
        entity_id: str,
        reciter: Any,
        moshaf: Any,
        surah: int,
        *,
        auto_advance: bool,
        surah_repeat: int,
        play: bool = True,
    ) -> PlaybackSession:
        """Start or replace a playback session and optionally play now."""
        if not moshaf.has_surah(surah):
            raise ValueError(f"Surah {surah} is not available for this moshaf")

        url, title, artist = self._metadata_for(reciter, moshaf, surah)
        session = PlaybackSession(
            entity_id=entity_id,
            reciter_id=reciter.id,
            moshaf_id=moshaf.id,
            surah=surah,
            auto_advance=auto_advance,
            surah_repeat=max(1, surah_repeat),
            plays_remaining=max(1, surah_repeat),
            expected_url=url,
            title=title,
            artist=artist,
            pending_play=play,
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
        if self._ensure_stop_button is not None:
            await self._ensure_stop_button(entity_id)
        self._notify_listeners()
        if play:
            try:
                # blocking=True on first play surfaces Chromecast/URL errors.
                await self._async_play_url(
                    entity_id, url, title=title, artist=artist, blocking=True
                )
            except Exception:
                self.stop(entity_id)
                raise
        return session

    async def async_stop(
        self, entity_id: str, *, stop_media: bool = True
    ) -> None:
        """Clear the session and optionally stop media playback."""
        self._stopping.add(entity_id)
        removed = self._sessions.pop(entity_id, None)
        if removed:
            _LOGGER.debug("Stopped session on %s", entity_id)
            self._notify_listeners()
        try:
            if stop_media:
                await self.hass.services.async_call(
                    MEDIA_PLAYER_DOMAIN,
                    SERVICE_MEDIA_STOP,
                    {ATTR_ENTITY_ID: entity_id},
                    blocking=False,
                )
        finally:
            self._stopping.discard(entity_id)

    def stop(self, entity_id: str) -> None:
        """Clear session without stopping media (interrupt / unload / tests)."""
        if self._sessions.pop(entity_id, None):
            _LOGGER.debug("Cleared session on %s", entity_id)
            self._notify_listeners()

    def maybe_attach_from_url(
        self,
        entity_id: str,
        url: str,
        *,
        auto_advance: bool = DEFAULT_AUTO_ADVANCE,
        surah_repeat: int = DEFAULT_SURAH_REPEAT,
    ) -> PlaybackSession | None:
        """Best-effort attach when continuous play is explicitly requested."""
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
        _, title, artist = self._metadata_for(reciter, moshaf, surah)
        session = PlaybackSession(
            entity_id=entity_id,
            reciter_id=reciter.id,
            moshaf_id=moshaf.id,
            surah=surah,
            auto_advance=auto_advance,
            surah_repeat=max(1, surah_repeat),
            plays_remaining=max(1, surah_repeat),
            expected_url=url,
            title=title,
            artist=artist,
        )
        self._sessions[entity_id] = session
        _LOGGER.debug("Attached session from media browser URL on %s", entity_id)
        self._notify_listeners()
        return session

    @staticmethod
    def _is_natural_track_end(
        *,
        position: float | None,
        duration: float | None,
        max_position: float = 0.0,
        user_interrupted: bool,
    ) -> bool:
        """Return True if idle should advance / complete the surah cycle."""
        if user_interrupted:
            return False
        if position is None or duration is None:
            # No progress info (ESPHome, some Cast idle events): natural end.
            return True
        try:
            position_f = float(position)
            duration_f = float(duration)
            max_f = float(max_position or 0)
        except (TypeError, ValueError):
            return True
        if duration_f <= 0:
            return True
        if max(position_f, max_f) >= duration_f - END_OF_TRACK_SLACK_SECONDS:
            return True
        if duration_f and max(position_f, max_f) / duration_f >= END_OF_TRACK_RATIO:
            return True
        # Position stuck at ~0 means the player never reported progress
        # (typical Chromecast). Do not treat that as a mid-track stop.
        if max_f < 15 and position_f < 15:
            return True
        return False

    def _cache_progress(self, session: PlaybackSession, state: Any) -> None:
        """Remember last known position/duration while playing."""
        if state is None:
            return
        attrs = state.attributes or {}
        position = attrs.get(ATTR_MEDIA_POSITION)
        duration = attrs.get(ATTR_MEDIA_DURATION)
        try:
            if position is not None:
                position_f = float(position)
                session.last_position = position_f
                if position_f > session.max_position:
                    session.max_position = position_f
            if duration is not None:
                session.last_duration = float(duration)
        except (TypeError, ValueError):
            return

    async def _async_on_call_service(self, event: Event) -> None:
        """Mark sessions interrupted when HA stops/pauses/turns off a player."""
        domain = event.data.get("domain")
        service = event.data.get("service")
        if domain != MEDIA_PLAYER_DOMAIN:
            return
        service_data = event.data.get("service_data") or {}
        entity_ids = service_data.get(ATTR_ENTITY_ID)
        if entity_ids is None:
            return
        if isinstance(entity_ids, str):
            entity_ids = [entity_ids]
        if service == "media_play":
            for entity_id in entity_ids:
                session = self._sessions.get(entity_id)
                if session is not None:
                    session.user_interrupted = False
            return
        if service not in _USER_STOP_SERVICES:
            return
        # Ignore stops we initiated ourselves while clearing a session.
        for entity_id in entity_ids:
            if entity_id in self._stopping or entity_id in self._advancing:
                continue
            session = self._sessions.get(entity_id)
            if session is None:
                continue
            _LOGGER.debug(
                "User stop service %s on %s; will not auto-advance",
                service,
                entity_id,
            )
            session.user_interrupted = True

    async def _async_on_state_changed(self, event: Event) -> None:
        """Handle media player state changes for active sessions."""
        entity_id = event.data.get("entity_id")
        if not entity_id or not entity_id.startswith("media_player."):
            return

        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")
        if new_state is None:
            return

        session = self._sessions.get(entity_id)
        if session is None or not session.active:
            return
        if entity_id in self._stopping:
            return

        # Cache progress while playing / buffering so mid-stop still has data.
        new_state_val = new_state.state
        if new_state_val in {
            MediaPlayerState.PLAYING,
            "playing",
            "paused",
            getattr(MediaPlayerState, "PAUSED", "paused"),
        }:
            session.pending_play = False
            self._cache_progress(session, new_state)
        if old_state is not None and old_state.state in {
            MediaPlayerState.PLAYING,
            "playing",
        }:
            self._cache_progress(session, old_state)

        old_state_val = old_state.state if old_state else None
        was_playing = old_state_val in {
            MediaPlayerState.PLAYING,
            "playing",
        }
        # Treat paused→idle and playing→idle; also playing→off.
        left_active = old_state_val in {
            MediaPlayerState.PLAYING,
            "playing",
            "paused",
        }
        now_idle = new_state_val in _IDLE_STATES or new_state_val == STATE_UNAVAILABLE
        if not (left_active and now_idle):
            return
        # Extra idle events while the next URL is still starting must not advance again.
        if session.pending_play or entity_id in self._advancing:
            return

        if not was_playing and old_state_val == "paused" and session.user_interrupted:
            # Paused then idle after user stop service — clear without advance.
            self.stop(entity_id)
            return

        current_id = None
        if old_state is not None:
            current_id = old_state.attributes.get(ATTR_MEDIA_CONTENT_ID)
        if current_id and not _same_track(current_id, session.expected_url, session.surah):
            _LOGGER.debug(
                "Different media finished on %s (%s != %s); clearing session",
                entity_id,
                current_id,
                session.expected_url,
            )
            self.stop(entity_id)
            return

        position = session.last_position
        duration = session.last_duration
        # Prefer last cached values; fall back to old_state attrs.
        if old_state is not None:
            attrs = old_state.attributes or {}
            if position is None:
                try:
                    if attrs.get(ATTR_MEDIA_POSITION) is not None:
                        position = float(attrs[ATTR_MEDIA_POSITION])
                except (TypeError, ValueError):
                    pass
            if duration is None:
                try:
                    if attrs.get(ATTR_MEDIA_DURATION) is not None:
                        duration = float(attrs[ATTR_MEDIA_DURATION])
                except (TypeError, ValueError):
                    pass

        if not self._is_natural_track_end(
            position=position,
            duration=duration,
            max_position=session.max_position,
            user_interrupted=session.user_interrupted,
        ):
            _LOGGER.debug(
                "User interrupted playback on %s (pos=%s dur=%s interrupted=%s)",
                entity_id,
                position,
                duration,
                session.user_interrupted,
            )
            self.stop(entity_id)
            return

        await self._async_advance(session)

    async def _async_advance(self, session: PlaybackSession) -> None:
        """Repeat current surah or advance to the next one."""
        if session.entity_id in self._advancing:
            return
        self._advancing.add(session.entity_id)
        try:
            session.plays_remaining -= 1
            session.user_interrupted = False
            session.last_position = None
            session.last_duration = None
            session.max_position = 0.0
            session.pending_play = True
            if session.plays_remaining > 0:
                _LOGGER.debug(
                    "Repeating surah %s on %s (%s remaining)",
                    session.surah,
                    session.entity_id,
                    session.plays_remaining,
                )
                await self._async_play_url(
                    session.entity_id,
                    session.expected_url,
                    title=session.title,
                    artist=session.artist,
                    blocking=False,
                )
                self._notify_listeners()
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

            url, title, artist = self._metadata_for(reciter, moshaf, next_surah)
            session.surah = next_surah
            session.expected_url = url
            session.title = title
            session.artist = artist
            session.plays_remaining = session.surah_repeat
            _LOGGER.debug(
                "Advancing to surah %s on %s",
                next_surah,
                session.entity_id,
            )
            await self._async_play_url(
                session.entity_id,
                url,
                title=title,
                artist=artist,
                blocking=False,
            )
            self._notify_listeners()
        finally:
            self._advancing.discard(session.entity_id)

    async def async_skip(self, entity_id: str, *, step: int) -> None:
        """Jump the active session to the next or previous surah and play it."""
        session = self._sessions.get(entity_id)
        if session is None or not session.active:
            raise ValueError("No active MP3 Quran session on this media player")
        if entity_id in self._advancing:
            return

        catalog = self.catalog
        if catalog is None:
            raise ValueError("MP3 Quran catalog is not ready")
        reciter = catalog.get_reciter(session.reciter_id)
        if reciter is None:
            raise ValueError("Reciter for this session is no longer available")
        moshaf = reciter.get_moshaf(session.moshaf_id)
        if moshaf is None:
            raise ValueError("Moshaf for this session is no longer available")

        target = (
            moshaf.next_surah(session.surah)
            if step > 0
            else moshaf.previous_surah(session.surah)
        )
        if target is None:
            edge = "next" if step > 0 else "previous"
            raise ValueError(f"This moshaf has no {edge} surah")

        self._advancing.add(entity_id)
        try:
            url, title, artist = self._metadata_for(reciter, moshaf, target)
            session.surah = target
            session.expected_url = url
            session.title = title
            session.artist = artist
            session.plays_remaining = session.surah_repeat
            session.user_interrupted = False
            session.last_position = None
            session.last_duration = None
            session.max_position = 0.0
            session.pending_play = True
            await self._async_play_url(
                entity_id,
                url,
                title=title,
                artist=artist,
                blocking=False,
            )
            self._notify_listeners()
        finally:
            self._advancing.discard(entity_id)

    async def _async_clear_playlist(self, entity_id: str) -> None:
        """Clear a player playlist when supported.

        VLC's play_media only appends. Without a clear, finished surahs stay
        in the playlist and VLC replays them between our advances.
        """
        try:
            await self.hass.services.async_call(
                MEDIA_PLAYER_DOMAIN,
                "clear_playlist",
                {ATTR_ENTITY_ID: entity_id},
                blocking=True,
            )
        except Exception:  # noqa: BLE001 - Cast/ESPHome have no playlist
            _LOGGER.debug("clear_playlist unsupported on %s", entity_id)

    async def _async_play_url(
        self,
        entity_id: str,
        url: str,
        *,
        title: str = "",
        artist: str = "",
        blocking: bool = False,
    ) -> None:
        """Send play_media using audio/mpeg, matching Media Browser.

        Cast metadata is best-effort. Top-level title/artist keys can make
        Chromecast reject the load (empty PyChromecastError / Unknown error),
        so only Cast metadataType 3 is sent, and a plain retry is used if that fails.
        """
        base: dict[str, Any] = {
            ATTR_ENTITY_ID: entity_id,
            ATTR_MEDIA_CONTENT_ID: url,
            ATTR_MEDIA_CONTENT_TYPE: MIME_TYPE_MP3,
        }
        with_meta = dict(base)
        if title or artist:
            with_meta[ATTR_MEDIA_EXTRA] = {
                "metadata": {
                    "metadataType": 3,
                    "title": title,
                    "artist": artist,
                }
            }

        await self._async_clear_playlist(entity_id)
        try:
            await self.hass.services.async_call(
                MEDIA_PLAYER_DOMAIN,
                SERVICE_PLAY_MEDIA,
                with_meta,
                blocking=blocking,
            )
        except Exception:
            if with_meta is base or ATTR_MEDIA_EXTRA not in with_meta:
                raise
            _LOGGER.debug(
                "play_media with metadata failed on %s; retrying without extra",
                entity_id,
                exc_info=True,
            )
            await self.hass.services.async_call(
                MEDIA_PLAYER_DOMAIN,
                SERVICE_PLAY_MEDIA,
                base,
                blocking=blocking,
            )
