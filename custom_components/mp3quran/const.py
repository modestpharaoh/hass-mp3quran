"""Constants for the MP3 Quran integration."""

from __future__ import annotations

DOMAIN = "mp3quran"

API_BASE = "https://www.mp3quran.net/api/v3"
DEFAULT_UPDATE_INTERVAL_HOURS = 24

# Preferred option key. Older installs may still have CONF_SORT_LANGUAGE.
CONF_DISPLAY_LANGUAGE = "display_language"
CONF_SORT_LANGUAGE = "sort_language"  # legacy alias
CONF_SURAH_REPEAT = "surah_repeat"
CONF_FAVORITE_RECITERS = "favorite_reciters"
# Legacy option key (removed from UI; ignored if still present in storage).
CONF_AUTO_ADVANCE = "auto_advance"

LANG_ENGLISH = "english"
LANG_ARABIC = "arabic"
DISPLAY_LANGUAGES = [LANG_ENGLISH, LANG_ARABIC]

# Backward-compatible aliases
SORT_ENGLISH = LANG_ENGLISH
SORT_ARABIC = LANG_ARABIC
SORT_LANGUAGES = DISPLAY_LANGUAGES

DEFAULT_DISPLAY_LANGUAGE = LANG_ENGLISH
DEFAULT_SORT_LANGUAGE = DEFAULT_DISPLAY_LANGUAGE
DEFAULT_AUTO_ADVANCE = False
DEFAULT_LOOP = False
DEFAULT_SURAH_REPEAT = 1

MIN_SURAH_REPEAT = 1
MAX_SURAH_REPEAT = 20

# Treat track as finished when within this many seconds of duration,
# or when position/duration ratio is at least this value.
END_OF_TRACK_SLACK_SECONDS = 5.0
END_OF_TRACK_RATIO = 0.95

ATTR_RECITER_ID = "reciter_id"
ATTR_MOSHAF_ID = "moshaf_id"
ATTR_SURAH = "surah"
ATTR_AUTO_ADVANCE = "auto_advance"
ATTR_LOOP = "loop"
ATTR_SURAH_REPEAT = "surah_repeat"
ATTR_ENTITY_ID = "entity_id"

SERVICE_PLAY = "play"
SERVICE_STOP = "stop"
SERVICE_NEXT_SURAH = "next_surah"
SERVICE_PREVIOUS_SURAH = "previous_surah"

MIME_TYPE_MP3 = "audio/mpeg"
MEDIA_TYPE_MUSIC = "music"

# Media source identifier prefixes
ID_RECITER = "reciter"
ID_MOSHAF = "moshaf"
ID_SURAH = "surah"

PLATFORMS = ["sensor", "button"]

CARD_URL = "/mp3quran/mp3quran-card.js"


def get_favorite_reciter_ids(options: dict) -> list[int]:
    """Return saved favorite reciter ids."""
    raw = options.get(CONF_FAVORITE_RECITERS) or []
    if isinstance(raw, (str, int)):
        raw = [raw]
    ids: list[int] = []
    for item in raw:
        try:
            number = int(item)
        except (TypeError, ValueError):
            continue
        if number not in ids:
            ids.append(number)
    return ids


def get_display_language(options: dict) -> str:
    """Return the configured display/sort language from options."""
    value = options.get(CONF_DISPLAY_LANGUAGE)
    if value is None:
        value = options.get(CONF_SORT_LANGUAGE, DEFAULT_DISPLAY_LANGUAGE)
    return value if value in DISPLAY_LANGUAGES else DEFAULT_DISPLAY_LANGUAGE
