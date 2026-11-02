"""Tests for the mp3quran API client and catalog merging."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.mp3quran.api import Catalog, Moshaf, Mp3QuranApi, Reciter
from custom_components.mp3quran.surahs import (
    AYAH_COUNTS,
    build_fallback_surahs,
    merge_suwar_from_api,
)


def test_fallback_surahs_complete() -> None:
    surahs = build_fallback_surahs()
    assert len(surahs) == 114
    assert surahs[1].name_en == "Al-Fatihah"
    assert surahs[1].name_ar == "الفاتحة"
    assert surahs[1].makki is True
    assert surahs[1].ayah_count == 7
    assert surahs[2].makki is False
    assert surahs[2].ayah_count == 286
    assert all(n in AYAH_COUNTS for n in range(1, 115))


def test_merge_suwar_from_api(load_fixture) -> None:
    en = load_fixture("suwar_en.json")["suwar"]
    ar = load_fixture("suwar_ar.json")["suwar"]
    merged = merge_suwar_from_api(en, ar)
    assert len(merged) == 114
    assert "Fatihah" in merged[1].name_en or "fatihah" in merged[1].name_en.lower()
    assert merged[1].name_ar
    assert merged[1].ayah_count == 7
    title = merged[1].display_title("english")
    assert "001" in title
    assert "Makki" in title
    assert "7 ayahs" in title
    assert "الفاتحة" not in title
    ar_title = merged[1].display_title("arabic")
    assert "الفاتحة" in ar_title
    assert "مكية" in ar_title
    assert "آية" in ar_title


def test_moshaf_audio_url_and_next() -> None:
    moshaf = Moshaf(
        id=1,
        name_en="Murattal",
        name_ar="مرتل",
        server="https://cdn.mp3quran.net/audio/test/",
        surah_total=3,
        surah_list=[1, 78, 114],
    )
    assert moshaf.audio_url(1) == "https://cdn.mp3quran.net/audio/test/001.mp3"
    assert moshaf.audio_url(114) == "https://cdn.mp3quran.net/audio/test/114.mp3"
    assert moshaf.next_surah(1) == 78
    assert moshaf.next_surah(78) == 114
    assert moshaf.next_surah(114) is None
    assert moshaf.previous_surah(114) == 78
    assert moshaf.previous_surah(78) == 1
    assert moshaf.previous_surah(1) is None
    assert moshaf.has_surah(78)
    assert not moshaf.has_surah(2)


def test_catalog_sort_and_find(load_fixture) -> None:
    en = load_fixture("reciters_en.json")["reciters"]
    ar = load_fixture("reciters_ar.json")["reciters"]
    ar_names = {int(r["id"]): r["name"] for r in ar}
    ar_moshaf = {
        int(m["id"]): m["name"] for r in ar for m in r.get("moshaf", [])
    }

    reciters: dict[int, Reciter] = {}
    for item in en:
        moshafs = [
            Moshaf(
                id=int(m["id"]),
                name_en=m["name"],
                name_ar=ar_moshaf.get(int(m["id"]), ""),
                server=m["server"],
                surah_total=int(m["surah_total"]),
                surah_list=[int(x) for x in str(m["surah_list"]).split(",") if x],
            )
            for m in item["moshaf"]
        ]
        rid = int(item["id"])
        reciters[rid] = Reciter(
            id=rid,
            name_en=item["name"],
            name_ar=ar_names.get(rid, ""),
            moshafs=moshafs,
        )

    catalog = Catalog(reciters=reciters)
    by_en = catalog.sorted_reciters("english")
    by_ar = catalog.sorted_reciters("arabic")
    assert {r.id for r in by_en} == {1, 102}
    assert by_en[0].browse_title("english").endswith(f"[{by_en[0].id}]")
    assert "[" in by_ar[0].browse_title("arabic")
    maher = catalog.get_reciter(102)
    assert maher is not None
    assert maher.browse_title("english") == f"{maher.name_en} [102]"
    assert maher.moshafs[0].browse_title("english").endswith(
        f"[{maher.moshafs[0].id}]"
    )

    # Incomplete moshaf only has listed surahs
    assert len(maher.moshafs) == 3
    incomplete = next(m for m in maher.moshafs if m.surah_total == 38)
    assert incomplete.has_surah(1)
    assert not incomplete.has_surah(2)
    assert incomplete.next_surah(1) == 78

    url = incomplete.audio_url(1)
    match = catalog.find_by_audio_url(url)
    assert match is not None
    reciter, moshaf, surah = match
    assert reciter.id == 102
    assert moshaf.id == incomplete.id
    assert surah == 1


@pytest.mark.asyncio
async def test_fetch_catalog_merges_languages(load_fixture) -> None:
    session = MagicMock()
    api = Mp3QuranApi(session)
    api.fetch_reciters = AsyncMock(
        side_effect=lambda lang: load_fixture(f"reciters_{'en' if lang == 'en' else 'ar'}.json")[
            "reciters"
        ]
    )
    api.fetch_suwar = AsyncMock(
        side_effect=lambda lang: load_fixture(f"suwar_{'en' if lang == 'en' else 'ar'}.json")[
            "suwar"
        ]
    )

    catalog = await api.fetch_catalog()
    assert len(catalog.reciters) == 2
    assert 1 in catalog.reciters
    assert catalog.reciters[1].name_ar
    assert len(catalog.surahs) == 114
