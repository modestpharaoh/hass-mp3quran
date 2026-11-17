# AGENTS.md

Codex reads this file. Claude reads [CLAUDE.md](CLAUDE.md), Gemini reads [GEMINI.md](GEMINI.md), and Cursor reads [.cursor/rules/mp3quran.mdc](.cursor/rules/mp3quran.mdc). Those files point here.

Home Assistant custom integration. Domain `mp3quran`. It plays Quran recitations from mp3quran.net on any media player. Read [README.md](README.md) before changing playback, services, or the dashboard card.

## Commands

Run tests from this repository, with its own virtualenv:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements_test.txt
.venv/bin/python -m pytest tests/ -q
```

Do not use another project's virtualenv. Home Assistant itself is stubbed in `tests/conftest.py`.

## Invariants

- Manifest keys are `domain`, `name`, then alphabetical. `after_dependencies` is `lovelace`. `dependencies` includes `http` and `media_source`. Hassfest fails if that order changes.
- The card resource is `/mp3quran/mp3quran-card.js?v={manifest version}`. Register it only after `CoreState.running` or `homeassistant_started`. Do not use `hass.is_running`. `tests/test_frontend.py` reads the version from `manifest.json` instead of hardcoding it.
- Bump `manifest.json` only when a user-facing change ships. Keep every released changelog section, including 1.4.5.
- Display language is the integration option `english` or `arabic`, exposed as `display_language` on `sensor.mp3quran_active_sessions`. The card uses that, with Arabic right-to-left. It falls back to the Home Assistant locale only when the sensor is missing. The surah field label is "Surah" / "السورة".
- Favorite reciters sort first and keep the star. A reciter with one moshaf hides the moshaf control. Incomplete moshafs walk `surah_list`; they do not use surah number plus or minus one.
- `mp3quran.play` starts playback. Auto-advance and loop default off and are per call, not integration options. Loop wraps to `surah_list[0]` only after the last available surah, even when auto-advance is off. A middle surah still stops when auto-advance is off. Previous never wraps.
- `mp3quran.update_session` changes auto-advance, loop, or repeat on the active session and does not restart audio. A new repeat count sets both `surah_repeat` and `plays_remaining`.
- Pause and resume call the media player. `media_pause` sets `user_interrupted` and blocks auto-advance. `media_play` clears that flag before the stop-service filter. Stop calls `mp3quran.stop`.
- With an active session, previous and next call `mp3quran.previous_surah` and `mp3quran.next_surah`. Without one, the card starts the neighbor with `mp3quran.play`. Next wraps only when loop is on.
- The card shows the progress bar only when `media_position` and `media_duration` are both real and duration is greater than 0. Do not coerce null with `Number()`. Seek uses feature bit 2. Bit 4 is volume, not seek. Many ESPHome speakers hide the bar.
- While a session is running, the reciter, moshaf, and surah selectors follow it and the settings show its loop, auto-advance, and repeat. When it ends, the selectors return to the card config. Do not write the followed values back into Lovelace. Changing a selector does not retarget audio.
- `play_media` uses `audio/mpeg` and only Cast `extra.metadata` (`metadataType` 3, title, artist). Retry once without `extra`. Clear the playlist before every play. The first play is blocking; advances and skips are not.
- A missing position is a natural end unless the user interrupted. A real mid-track position does not advance. `pending_play` ignores extra idle until the player is playing again.
- Commit only when the user asks. Do not commit `.venv/`, archives, or secrets.

## Leave these files alone unless asked

Brand images and the dashboard screenshot are tracked. Do not open them to answer a code question:

- `custom_components/mp3quran/**/*.png`
- `docs/*.png`
- `.venv/`
