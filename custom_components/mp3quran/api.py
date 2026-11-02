"""Async client for the mp3quran.net v3 API."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import API_BASE
from .surahs import SurahInfo, build_fallback_surahs, merge_suwar_from_api

_LOGGER = logging.getLogger(__name__)
_TIMEOUT = ClientTimeout(total=30)


class Mp3QuranApiError(Exception):
    """Raised when the mp3quran API request fails."""


@dataclass(slots=True)
class Moshaf:
    """A moshaf (riwayah / recording style) for a reciter."""

    id: int
    name_en: str
    name_ar: str
    server: str
    surah_total: int
    surah_list: list[int]

    def audio_url(self, surah: int) -> str:
        """Build the direct MP3 URL for a surah."""
        base = self.server if self.server.endswith("/") else f"{self.server}/"
        return f"{base}{surah:03d}.mp3"

    def has_surah(self, surah: int) -> bool:
        """Return True if this moshaf includes the given surah."""
        return surah in self.surah_list

    def next_surah(self, surah: int) -> int | None:
        """Return the next available surah after the given one, or None."""
        for candidate in self.surah_list:
            if candidate > surah:
                return candidate
        return None

    def previous_surah(self, surah: int) -> int | None:
        """Return the previous available surah before the given one, or None."""
        previous = None
        for candidate in self.surah_list:
            if candidate >= surah:
                break
            previous = candidate
        return previous

    def localized_name(self, language: str = "english") -> str:
        """Return the moshaf name in the requested language."""
        if language == "arabic":
            return self.name_ar or self.name_en
        return self.name_en or self.name_ar

    def browse_title(self, language: str = "english") -> str:
        """Return media-browser title including the mp3quran moshaf id."""
        return f"{self.localized_name(language)} [{self.id}]"

    @property
    def display_name(self) -> str:
        """Default English browse title with id."""
        return self.browse_title("english")


@dataclass(slots=True)
class Reciter:
    """A Quran reciter with one or more moshafs."""

    id: int
    name_en: str
    name_ar: str
    letter: str = ""
    moshafs: list[Moshaf] = field(default_factory=list)

    def localized_name(self, language: str = "english") -> str:
        """Return the reciter name in the requested language."""
        if language == "arabic":
            return self.name_ar or self.name_en
        return self.name_en or self.name_ar

    def browse_title(self, language: str = "english") -> str:
        """Return media-browser title including the mp3quran reciter id."""
        return f"{self.localized_name(language)} [{self.id}]"

    @property
    def display_name(self) -> str:
        """Default English browse title with id."""
        return self.browse_title("english")

    def get_moshaf(self, moshaf_id: int) -> Moshaf | None:
        """Return a moshaf by id."""
        for moshaf in self.moshafs:
            if moshaf.id == moshaf_id:
                return moshaf
        return None

    def default_moshaf(self) -> Moshaf | None:
        """Return the first moshaf, if any."""
        return self.moshafs[0] if self.moshafs else None


@dataclass(slots=True)
class Catalog:
    """Cached catalog of reciters and surahs."""

    reciters: dict[int, Reciter] = field(default_factory=dict)
    surahs: dict[int, SurahInfo] = field(default_factory=build_fallback_surahs)

    def sorted_reciters(self, language: str = "english") -> list[Reciter]:
        """Return reciters sorted by English or Arabic name."""
        key = (
            (lambda r: (r.name_ar or r.name_en).casefold())
            if language == "arabic"
            else (lambda r: (r.name_en or r.name_ar).casefold())
        )
        return sorted(self.reciters.values(), key=key)

    def get_reciter(self, reciter_id: int) -> Reciter | None:
        """Return a reciter by id."""
        return self.reciters.get(reciter_id)

    def find_by_audio_url(self, url: str) -> tuple[Reciter, Moshaf, int] | None:
        """Match an audio URL back to reciter/moshaf/surah if possible."""
        if not url or "mp3quran" not in url:
            return None
        # Expect .../NNN.mp3
        filename = url.rstrip("/").rsplit("/", 1)[-1]
        if not filename.lower().endswith(".mp3"):
            return None
        stem = filename[:-4]
        if not stem.isdigit():
            return None
        surah = int(stem)
        server_prefix = url[: url.rfind("/") + 1]
        for reciter in self.reciters.values():
            for moshaf in reciter.moshafs:
                moshaf_server = (
                    moshaf.server if moshaf.server.endswith("/") else f"{moshaf.server}/"
                )
                if moshaf_server == server_prefix and moshaf.has_surah(surah):
                    return reciter, moshaf, surah
        return None


class Mp3QuranApi:
    """Thin async wrapper around mp3quran.net API v3."""

    def __init__(self, session: ClientSession) -> None:
        """Initialize with an aiohttp session."""
        self._session = session

    async def _get_json(self, path: str, **params: Any) -> dict[str, Any]:
        """GET a JSON endpoint."""
        url = f"{API_BASE}/{path.lstrip('/')}"
        try:
            async with self._session.get(url, params=params, timeout=_TIMEOUT) as resp:
                resp.raise_for_status()
                data = await resp.json(content_type=None)
        except (ClientError, TimeoutError, ValueError) as err:
            raise Mp3QuranApiError(f"Failed to fetch {url}: {err}") from err
        if not isinstance(data, dict):
            raise Mp3QuranApiError(f"Unexpected response from {url}")
        return data

    async def fetch_reciters(self, language: str) -> list[dict[str, Any]]:
        """Fetch all reciters for a language."""
        data = await self._get_json("reciters", language=language)
        return list(data.get("reciters", []))

    async def fetch_suwar(self, language: str) -> list[dict[str, Any]]:
        """Fetch all surah metadata for a language."""
        data = await self._get_json("suwar", language=language)
        return list(data.get("suwar", []))

    async def fetch_catalog(self) -> Catalog:
        """Fetch and merge bilingual catalog data."""
        en_reciters, ar_reciters, en_suwar, ar_suwar = await _gather_catalog(self)

        ar_names = {int(item["id"]): str(item.get("name", "")).strip() for item in ar_reciters}
        ar_moshaf_names: dict[int, str] = {}
        for item in ar_reciters:
            for moshaf in item.get("moshaf", []):
                ar_moshaf_names[int(moshaf["id"])] = str(moshaf.get("name", "")).strip()

        reciters: dict[int, Reciter] = {}
        for item in en_reciters:
            reciter_id = int(item["id"])
            moshafs: list[Moshaf] = []
            for raw in item.get("moshaf", []):
                surah_list = _parse_surah_list(raw.get("surah_list", ""))
                moshaf_id = int(raw["id"])
                server = str(raw.get("server", "")).strip()
                if not server:
                    continue
                moshafs.append(
                    Moshaf(
                        id=moshaf_id,
                        name_en=str(raw.get("name", "")).strip(),
                        name_ar=ar_moshaf_names.get(moshaf_id, ""),
                        server=server,
                        surah_total=int(raw.get("surah_total", len(surah_list)) or 0),
                        surah_list=surah_list,
                    )
                )
            if not moshafs:
                continue
            reciters[reciter_id] = Reciter(
                id=reciter_id,
                name_en=str(item.get("name", "")).strip(),
                name_ar=ar_names.get(reciter_id, ""),
                letter=str(item.get("letter", "")).strip(),
                moshafs=moshafs,
            )

        surahs = merge_suwar_from_api(en_suwar, ar_suwar)
        _LOGGER.debug(
            "Loaded %s reciters and %s surahs from mp3quran API",
            len(reciters),
            len(surahs),
        )
        return Catalog(reciters=reciters, surahs=surahs)


async def _gather_catalog(
    api: Mp3QuranApi,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    """Fetch EN/AR reciters and suwar concurrently."""
    import asyncio

    en_reciters, ar_reciters, en_suwar, ar_suwar = await asyncio.gather(
        api.fetch_reciters("en"),
        api.fetch_reciters("ar"),
        api.fetch_suwar("en"),
        api.fetch_suwar("ar"),
    )
    return en_reciters, ar_reciters, en_suwar, ar_suwar


def _parse_surah_list(value: str | list[int] | None) -> list[int]:
    """Parse a comma-separated surah list into sorted unique ints."""
    if value is None:
        return []
    if isinstance(value, list):
        numbers = [int(v) for v in value]
    else:
        numbers = [int(part) for part in str(value).split(",") if part.strip().isdigit()]
    return sorted(set(numbers))
