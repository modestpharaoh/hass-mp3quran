"""Tests for the HACS catalog manifest."""

from __future__ import annotations

import json
from pathlib import Path

MANIFEST_PATH = (
    Path(__file__).parents[1] / "custom_components" / "mp3quran" / "manifest.json"
)
REQUIRED_KEYS = (
    "domain",
    "name",
    "codeowners",
    "documentation",
    "issue_tracker",
    "version",
)


def test_manifest_meets_hacs_catalog() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    for key in REQUIRED_KEYS:
        assert manifest.get(key), key
    assert manifest["domain"] == "mp3quran"
    assert manifest["categories"] == ["media_entertainment.music_radio_services"]
    assert "category" not in manifest

    keys = list(manifest)
    assert keys[:2] == ["domain", "name"]
    assert keys[2:] == sorted(keys[2:])
