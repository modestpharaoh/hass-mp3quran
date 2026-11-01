"""Constants for the MP3 Quran integration."""

from __future__ import annotations

DOMAIN = "mp3quran"

API_BASE = "https://www.mp3quran.net/api/v3"
DEFAULT_UPDATE_INTERVAL_HOURS = 24

# Preferred option key. Older installs may still have CONF_SORT_LANGUAGE.
CONF_DISPLAY_LANGUAGE = "display_language"
CONF_SORT_LANGUAGE = "sort_language"  # legacy alias
CONF_AUTO_ADVANCE = "auto_advance"
CONF_SURAH_REPEAT = "surah_repeat"

LANG_ENGLISH = "english"
LANG_ARABIC = "arabic"
DISPLAY_LANGUAGES = [LANG_ENGLISH, LANG_ARABIC]

# Backward-compatible aliases
SORT_ENGLISH = LANG_ENGLISH
SORT_ARABIC = LANG_ARABIC
SORT_LANGUAGES = DISPLAY_LANGUAGES

DEFAULT_DISPLAY_LANGUAGE = LANG_ENGLISH
DEFAULT_SORT_LANGUAGE = DEFAULT_DISPLAY_LANGUAGE
DEFAULT_AUTO_ADVANCE = True
DEFAULT_SURAH_REPEAT = 1

MIN_SURAH_REPEAT = 1
MAX_SURAH_REPEAT = 20

ATTR_RECITER_ID = "reciter_id"
ATTR_MOSHAF_ID = "moshaf_id"
ATTR_SURAH = "surah"
ATTR_AUTO_ADVANCE = "auto_advance"
ATTR_SURAH_REPEAT = "surah_repeat"
ATTR_ENTITY_ID = "entity_id"

SERVICE_PLAY = "play"
SERVICE_STOP = "stop"

MIME_TYPE_MP3 = "audio/mpeg"

# Media source identifier prefixes
ID_RECITER = "reciter"
ID_MOSHAF = "moshaf"
ID_SURAH = "surah"


def get_display_language(options: dict) -> str:
    """Return the configured display/sort language from options."""
    value = options.get(CONF_DISPLAY_LANGUAGE)
    if value is None:
        value = options.get(CONF_SORT_LANGUAGE, DEFAULT_DISPLAY_LANGUAGE)
    return value if value in DISPLAY_LANGUAGES else DEFAULT_DISPLAY_LANGUAGE
