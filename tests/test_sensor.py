"""Tests for the MP3 Quran session sensor."""

from types import SimpleNamespace

from custom_components.mp3quran.sensor import Mp3QuranActiveSessionsSensor


def test_sensor_exposes_display_language() -> None:
    entry = SimpleNamespace(entry_id="abc", options={"display_language": "arabic"})
    sessions = SimpleNamespace(sessions={})
    sensor = Mp3QuranActiveSessionsSensor(entry, sessions)

    assert sensor.native_value == 0
    assert sensor.extra_state_attributes["display_language"] == "arabic"
