# Gemini

Follow [AGENTS.md](AGENTS.md). Behavior and services: [README.md](README.md).

Tests run from this repo: `.venv/bin/python -m pytest tests/ -q` after `requirements_test.txt`. Do not use another project's virtualenv.

Do not break: manifest key order; card registration only after Home Assistant is running, with `?v=` matching the manifest; integration display language on the card; favorites first; incomplete moshafs via `surah_list`; loop only after the last surah and previous never wrapping; `update_session` without restarting audio; pause blocking auto-advance until resume; progress hidden without a real position and duration; seek as feature bit 2; selectors following the session and returning to card config; Cast metadata-only `extra` plus a playlist clear before play. Do not open brand images or doc screenshots unless the user asks. Commit only when asked.
