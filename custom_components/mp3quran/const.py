"""Constants for the MP3 Quran integration."""

from __future__ import annotations

DOMAIN = "mp3quran"

API_BASE = "https://www.mp3quran.net/api/v3"
DEFAULT_UPDATE_INTERVAL_HOURS = 24

CONF_SORT_LANGUAGE = "sort_language"
CONF_AUTO_ADVANCE = "auto_advance"
CONF_SURAH_REPEAT = "surah_repeat"

SORT_ENGLISH = "english"
SORT_ARABIC = "arabic"
SORT_LANGUAGES = [SORT_ENGLISH, SORT_ARABIC]

DEFAULT_SORT_LANGUAGE = SORT_ENGLISH
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
