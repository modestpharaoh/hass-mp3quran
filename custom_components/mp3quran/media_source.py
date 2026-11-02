"""Media source for browsing and playing mp3quran.net recitations."""

from __future__ import annotations

from homeassistant.components.media_player import BrowseError, MediaClass, MediaType
from homeassistant.components.media_source import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
    Unresolvable,
)
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant

from .api import Catalog, Moshaf, Reciter
from .const import (
    DOMAIN,
    ID_MOSHAF,
    ID_RECITER,
    ID_SURAH,
    MIME_TYPE_MP3,
    get_display_language,
    get_favorite_reciter_ids,
)
from .coordinator import Mp3QuranCoordinator


async def async_get_media_source(hass: HomeAssistant) -> Mp3QuranMediaSource:
    """Set up MP3 Quran media source."""
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        raise BrowseError("MP3 Quran is not configured")
    return Mp3QuranMediaSource(hass, entries[0])


class Mp3QuranMediaSource(MediaSource):
    """Provide Quran recitations as a media source."""

    name = "MP3 Quran"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the media source."""
        super().__init__(DOMAIN)
        self.hass = hass
        self.entry = entry

    @property
    def coordinator(self) -> Mp3QuranCoordinator:
        """Return the catalog coordinator."""
        return self.entry.runtime_data.coordinator

    @property
    def catalog(self) -> Catalog:
        """Return the cached catalog."""
        if self.entry.state is not ConfigEntryState.LOADED or self.coordinator.data is None:
            raise BrowseError("MP3 Quran catalog is not ready")
        return self.coordinator.data

    def _display_language(self) -> str:
        return get_display_language(self.entry.options)

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        """Resolve a surah identifier to a streaming URL."""
        if self.entry.state is not ConfigEntryState.LOADED:
            raise Unresolvable("MP3 Quran is not ready")

        parsed = _parse_identifier(item.identifier)
        if parsed is None or parsed[2] is None:
            raise Unresolvable(f"Invalid media identifier: {item.identifier}")

        reciter_id, moshaf_id, surah = parsed
        catalog = self.catalog
        reciter = catalog.get_reciter(reciter_id)
        if reciter is None:
            raise Unresolvable(f"Unknown reciter: {reciter_id}")

        moshaf = reciter.get_moshaf(moshaf_id) if moshaf_id else reciter.default_moshaf()
        if moshaf is None:
            raise Unresolvable(f"Unknown moshaf for reciter {reciter_id}")
        if not moshaf.has_surah(surah):
            raise Unresolvable(
                f"Surah {surah} is not available for this moshaf"
            )

        return PlayMedia(moshaf.audio_url(surah), MIME_TYPE_MP3)

    async def async_browse_media(
        self,
        item: MediaSourceItem,
    ) -> BrowseMediaSource:
        """Return browsable media for the media browser."""
        if self.entry.state is not ConfigEntryState.LOADED:
            raise BrowseError("MP3 Quran is not ready")

        catalog = self.catalog
        identifier = item.identifier or ""
        language = self._display_language()

        if not identifier:
            return self._browse_root(catalog, language)

        parsed = _parse_identifier(identifier)
        if parsed is None:
            raise BrowseError(f"Unknown media identifier: {identifier}")

        reciter_id, moshaf_id, surah = parsed
        if surah is not None:
            raise BrowseError("Surahs cannot be expanded")

        reciter = catalog.get_reciter(reciter_id)
        if reciter is None:
            raise BrowseError(f"Unknown reciter: {reciter_id}")

        if moshaf_id is None:
            if len(reciter.moshafs) == 1:
                return self._browse_surahs(catalog, reciter, reciter.moshafs[0], language)
            return self._browse_moshafs(reciter, language)

        moshaf = reciter.get_moshaf(moshaf_id)
        if moshaf is None:
            raise BrowseError(f"Unknown moshaf: {moshaf_id}")
        return self._browse_surahs(catalog, reciter, moshaf, language)

    def _browse_root(self, catalog: Catalog, language: str) -> BrowseMediaSource:
        favorites = set(get_favorite_reciter_ids(self.entry.options))
        reciters = sorted(
            catalog.sorted_reciters(language),
            key=lambda reciter: reciter.id not in favorites,
        )
        children = []
        for reciter in reciters:
            title = reciter.browse_title(language)
            if reciter.id in favorites:
                title = f"★ {title}"
            children.append(
                BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=f"{ID_RECITER}/{reciter.id}",
                    media_class=MediaClass.DIRECTORY,
                    media_content_type=MediaType.MUSIC,
                    title=title,
                    can_play=False,
                    can_expand=True,
                    children_media_class=MediaClass.DIRECTORY,
                )
            )
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=None,
            media_class=MediaClass.CHANNEL,
            media_content_type=MediaType.MUSIC,
            title=self.entry.title or "MP3 Quran",
            can_play=False,
            can_expand=True,
            children_media_class=MediaClass.DIRECTORY,
            children=children,
        )

    def _browse_moshafs(self, reciter: Reciter, language: str) -> BrowseMediaSource:
        children = [
            BrowseMediaSource(
                domain=DOMAIN,
                identifier=f"{ID_RECITER}/{reciter.id}/{ID_MOSHAF}/{moshaf.id}",
                media_class=MediaClass.DIRECTORY,
                media_content_type=MediaType.MUSIC,
                title=moshaf.browse_title(language),
                can_play=False,
                can_expand=True,
                children_media_class=MediaClass.TRACK,
            )
            for moshaf in reciter.moshafs
        ]
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=f"{ID_RECITER}/{reciter.id}",
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.MUSIC,
            title=reciter.browse_title(language),
            can_play=False,
            can_expand=True,
            children_media_class=MediaClass.DIRECTORY,
            children=children,
        )

    def _browse_surahs(
        self,
        catalog: Catalog,
        reciter: Reciter,
        moshaf: Moshaf,
        language: str,
    ) -> BrowseMediaSource:
        children: list[BrowseMediaSource] = []
        for surah_num in moshaf.surah_list:
            info = catalog.surahs.get(surah_num)
            title = (
                info.display_title(language) if info else f"{surah_num:03d}"
            )
            children.append(
                BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=(
                        f"{ID_RECITER}/{reciter.id}/{ID_MOSHAF}/{moshaf.id}/"
                        f"{ID_SURAH}/{surah_num}"
                    ),
                    media_class=MediaClass.TRACK,
                    media_content_type=MIME_TYPE_MP3,
                    title=title,
                    can_play=True,
                    can_expand=False,
                )
            )

        identifier = (
            f"{ID_RECITER}/{reciter.id}"
            if len(reciter.moshafs) == 1
            else f"{ID_RECITER}/{reciter.id}/{ID_MOSHAF}/{moshaf.id}"
        )
        title = (
            reciter.browse_title(language)
            if len(reciter.moshafs) == 1
            else f"{reciter.browse_title(language)} · {moshaf.browse_title(language)}"
        )
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=identifier,
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.MUSIC,
            title=title,
            can_play=False,
            can_expand=True,
            children_media_class=MediaClass.TRACK,
            children=children,
        )


def _parse_identifier(
    identifier: str | None,
) -> tuple[int, int | None, int | None] | None:
    """Parse media source identifiers.

    Formats:
      reciter/{id}
      reciter/{id}/moshaf/{id}
      reciter/{id}/moshaf/{id}/surah/{n}
    """
    if not identifier:
        return None
    parts = [part for part in identifier.split("/") if part]
    if len(parts) < 2 or parts[0] != ID_RECITER:
        return None
    try:
        reciter_id = int(parts[1])
    except ValueError:
        return None

    moshaf_id: int | None = None
    surah: int | None = None
    idx = 2
    while idx < len(parts):
        key = parts[idx]
        if idx + 1 >= len(parts):
            return None
        try:
            value = int(parts[idx + 1])
        except ValueError:
            return None
        if key == ID_MOSHAF:
            moshaf_id = value
        elif key == ID_SURAH:
            surah = value
        else:
            return None
        idx += 2
    return reciter_id, moshaf_id, surah
