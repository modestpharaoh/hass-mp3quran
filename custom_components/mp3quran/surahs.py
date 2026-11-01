"""Static surah metadata including ayah counts.

Ayah counts are canonical and not provided by the mp3quran API.
Names and revelation type are refreshed from the API when available.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SurahInfo:
    """Metadata for a single surah."""

    number: int
    name_en: str
    name_ar: str
    ayah_count: int
    makki: bool

    @property
    def revelation(self) -> str:
        """Return Makki or Madani label."""
        return "Makki" if self.makki else "Madani"

    @property
    def revelation_ar(self) -> str:
        """Return Arabic revelation label."""
        return "مكية" if self.makki else "مدنية"

    def localized_name(self, language: str = "english") -> str:
        """Return the surah name in the requested language."""
        if language == "arabic":
            return self.name_ar or self.name_en
        return self.name_en or self.name_ar

    def display_title(self, language: str = "english") -> str:
        """Return localized browse title with revelation type and ayah count."""
        if language == "arabic":
            return (
                f"{self.number:03d} · {self.localized_name('arabic')} · "
                f"{self.revelation_ar} · {self.ayah_count} آية"
            )
        return (
            f"{self.number:03d} · {self.localized_name('english')} · "
            f"{self.revelation} · {self.ayah_count} ayahs"
        )


# Canonical ayah counts for all 114 surahs.
AYAH_COUNTS: dict[int, int] = {
    1: 7,
    2: 286,
    3: 200,
    4: 176,
    5: 120,
    6: 165,
    7: 206,
    8: 75,
    9: 129,
    10: 109,
    11: 123,
    12: 111,
    13: 43,
    14: 52,
    15: 99,
    16: 128,
    17: 111,
    18: 110,
    19: 98,
    20: 135,
    21: 112,
    22: 78,
    23: 118,
    24: 64,
    25: 77,
    26: 227,
    27: 93,
    28: 88,
    29: 69,
    30: 60,
    31: 34,
    32: 30,
    33: 73,
    34: 54,
    35: 45,
    36: 83,
    37: 182,
    38: 88,
    39: 75,
    40: 85,
    41: 54,
    42: 53,
    43: 89,
    44: 59,
    45: 37,
    46: 35,
    47: 38,
    48: 29,
    49: 18,
    50: 45,
    51: 60,
    52: 49,
    53: 62,
    54: 55,
    55: 78,
    56: 96,
    57: 29,
    58: 22,
    59: 24,
    60: 13,
    61: 14,
    62: 11,
    63: 11,
    64: 18,
    65: 12,
    66: 12,
    67: 30,
    68: 52,
    69: 52,
    70: 44,
    71: 28,
    72: 28,
    73: 20,
    74: 56,
    75: 40,
    76: 31,
    77: 50,
    78: 40,
    79: 46,
    80: 42,
    81: 29,
    82: 19,
    83: 36,
    84: 25,
    85: 22,
    86: 17,
    87: 19,
    88: 26,
    89: 30,
    90: 20,
    91: 15,
    92: 21,
    93: 11,
    94: 8,
    95: 8,
    96: 19,
    97: 5,
    98: 8,
    99: 8,
    100: 11,
    101: 11,
    102: 8,
    103: 3,
    104: 9,
    105: 5,
    106: 4,
    107: 7,
    108: 3,
    109: 6,
    110: 3,
    111: 5,
    112: 4,
    113: 5,
    114: 6,
}

# Fallback English / Arabic names and revelation type if API is unavailable.
_FALLBACK: list[tuple[str, str, bool]] = [
    ("Al-Fatihah", "الفاتحة", True),
    ("Al-Baqarah", "البقرة", False),
    ("Aal Imran", "آل عمران", False),
    ("An-Nisa'", "النساء", False),
    ("Al-Ma'idah", "المائدة", False),
    ("Al-An'am", "الأنعام", True),
    ("Al-A'raf", "الأعراف", True),
    ("Al-Anfal", "الأنفال", False),
    ("At-Taubah", "التوبة", False),
    ("Yunus", "يونس", True),
    ("Hood", "هود", True),
    ("Yusuf", "يوسف", True),
    ("Ar-Ra'd", "الرعد", False),
    ("Ibrahim", "إبراهيم", True),
    ("Al-Hijr", "الحجر", True),
    ("An-Nahl", "النحل", True),
    ("Al-Isra", "الإسراء", True),
    ("Al-Kahf", "الكهف", True),
    ("Maryam", "مريم", True),
    ("Ta-Ha", "طه", True),
    ("Al-Anbiya'", "الأنبياء", True),
    ("Al-Hajj", "الحج", False),
    ("Al-Mu'minun", "المؤمنون", True),
    ("An-Nur", "النور", False),
    ("Al-Furqan", "الفرقان", True),
    ("Ash-Shu'ara'", "الشعراء", True),
    ("An-Naml", "النمل", True),
    ("Al-Qasas", "القصص", True),
    ("Al-'Ankabut", "العنكبوت", True),
    ("Ar-Room", "الروم", True),
    ("Luqman", "لقمان", True),
    ("As-Sajdah", "السجدة", True),
    ("Al-Ahzab", "الأحزاب", False),
    ("Saba'", "سبأ", True),
    ("Fatir", "فاطر", True),
    ("Ya-Sin", "يس", True),
    ("As-Saffat", "الصافات", True),
    ("Sad", "ص", True),
    ("Az-Zumar", "الزمر", True),
    ("Ghafir", "غافر", True),
    ("Fussilat", "فصلت", True),
    ("Ash-Shura", "الشورى", True),
    ("Az-Zukhruf", "الزخرف", True),
    ("Ad-Dukhan", "الدخان", True),
    ("Al-Jathiya", "الجاثية", True),
    ("Al-Ahqaf", "الأحقاف", True),
    ("Muhammad", "محمد", False),
    ("Al-Fath", "الفتح", False),
    ("Al-Hujurat", "الحجرات", False),
    ("Qaf", "ق", True),
    ("Az-Zariyat", "الذاريات", True),
    ("At-Tur", "الطور", True),
    ("An-Najm", "النجم", True),
    ("Al-Qamar", "القمر", True),
    ("Ar-Rahman", "الرحمن", False),
    ("Al-Waqi'ah", "الواقعة", True),
    ("Al-Hadid", "الحديد", False),
    ("Al-Mujadilah", "المجادلة", False),
    ("Al-Hashr", "الحشر", False),
    ("Al-Mumtahinah", "الممتحنة", False),
    ("As-Saff", "الصف", False),
    ("Al-Jumu'ah", "الجمعة", False),
    ("Al-Munafiqun", "المنافقون", False),
    ("At-Taghabun", "التغابن", False),
    ("At-Talaq", "الطلاق", False),
    ("At-Tahrim", "التحريم", False),
    ("Al-Mulk", "الملك", True),
    ("Al-Qalam", "القلم", True),
    ("Al-Haqqah", "الحاقة", True),
    ("Al-Ma'arij", "المعارج", True),
    ("Nooh", "نوح", True),
    ("Al-Jinn", "الجن", True),
    ("Al-Muzzammil", "المزمل", True),
    ("Al-Muddaththir", "المدثر", True),
    ("Al-Qiyamah", "القيامة", True),
    ("Al-Insan", "الإنسان", False),
    ("Al-Mursalat", "المرسلات", True),
    ("An-Naba'", "النبأ", True),
    ("An-Nazi'at", "النازعات", True),
    ("Abasa", "عبس", True),
    ("At-Takwir", "التكوير", True),
    ("Al-Infitar", "الانفطار", True),
    ("Al-Mutaffifin", "المطففين", True),
    ("Al-Inshiqaq", "الانشقاق", True),
    ("Al-Buruj", "البروج", True),
    ("At-Tariq", "الطارق", True),
    ("Al-A'la", "الأعلى", True),
    ("Al-Ghashiyah", "الغاشية", True),
    ("Al-Fajr", "الفجر", True),
    ("Al-Balad", "البلد", True),
    ("Ash-Shams", "الشمس", True),
    ("Al-Lail", "الليل", True),
    ("Ad-Duha", "الضحى", True),
    ("Ash-Sharh", "الشرح", True),
    ("At-Tin", "التين", True),
    ("Al-'Alaq", "العلق", True),
    ("Al-Qadr", "القدر", True),
    ("Al-Baiyinah", "البينة", False),
    ("Az-Zalzalah", "الزلزلة", False),
    ("Al-'Adiyat", "العاديات", True),
    ("Al-Qari'ah", "القارعة", True),
    ("At-Takathur", "التكاثر", True),
    ("Al-'Asr", "العصر", True),
    ("Al-Humazah", "الهمزة", True),
    ("Al-Fil", "الفيل", True),
    ("Quraish", "قريش", True),
    ("Al-Ma'un", "الماعون", True),
    ("Al-Kauthar", "الكوثر", True),
    ("Al-Kafirun", "الكافرون", True),
    ("An-Nasr", "النصر", False),
    ("Al-Masad", "المسد", True),
    ("Al-Ikhlas", "الإخلاص", True),
    ("Al-Falaq", "الفلق", True),
    ("An-Nas", "الناس", True),
]


def build_fallback_surahs() -> dict[int, SurahInfo]:
    """Build the bundled surah map used when the API is unavailable."""
    result: dict[int, SurahInfo] = {}
    for idx, (name_en, name_ar, makki) in enumerate(_FALLBACK, start=1):
        result[idx] = SurahInfo(
            number=idx,
            name_en=name_en,
            name_ar=name_ar,
            ayah_count=AYAH_COUNTS[idx],
            makki=makki,
        )
    return result


def merge_suwar_from_api(
    english: list[dict[str, Any]],
    arabic: list[dict[str, Any]],
) -> dict[int, SurahInfo]:
    """Merge EN/AR suwar API payloads with bundled ayah counts."""
    fallback = build_fallback_surahs()
    ar_by_id = {int(item["id"]): item for item in arabic}
    result: dict[int, SurahInfo] = {}

    for item in english:
        number = int(item["id"])
        ar_item = ar_by_id.get(number, {})
        base = fallback[number]
        makki = bool(int(item.get("makkia", 1 if base.makki else 0)))
        result[number] = SurahInfo(
            number=number,
            name_en=str(item.get("name", base.name_en)).strip() or base.name_en,
            name_ar=str(ar_item.get("name", base.name_ar)).strip() or base.name_ar,
            ayah_count=AYAH_COUNTS[number],
            makki=makki,
        )

    # Ensure all 114 exist even if API is partial.
    for number, base in fallback.items():
        result.setdefault(number, base)
    return result
