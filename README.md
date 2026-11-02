# MP3 Quran for Home Assistant

Browse and play Quran recitations from [mp3quran.net](https://mp3quran.net) in Home Assistant — similar to the built-in Radio Browser integration.

Play any of the 114 surahs by many reciters on any media player (VLC, Cast, browser, Music Assistant, etc.).

![MP3 Quran](icon.png)

## Features

- **Media source** — appears in **Media** as **MP3 Quran**
- **Live catalog** — reciters and moshafs loaded from the mp3quran.net API on setup/reload
- **Display language** — show and sort reciter / moshaf / surah names in English or Arabic
- **IDs in Media Browser** — reciter and moshaf titles include their mp3quran.net IDs for easy service calls
- **Surah details** — number, localized name, Makki/Madani, ayah count
- **Incomplete moshafs** — only available surahs are listed
- **Continuous playback** — optional auto-advance via `mp3quran.play` (defaults **off**)
- **Surah repeat** — play each surah N times before advancing
- **Session visibility** — `sensor.mp3quran_active_sessions` plus per-player stop buttons
- **HACS ready** — install as a custom repository

## Install (HACS)

1. Open **HACS → Integrations → ⋮ → Custom repositories**
2. Add `https://github.com/modestpharaoh/hass-mp3quran` as category **Integration**
3. Install **MP3 Quran**
4. Restart Home Assistant
5. Go to **Settings → Devices & services → Add integration → MP3 Quran**

## Usage

### Media Browser

1. Open **Media**
2. Choose **MP3 Quran**
3. Pick a reciter (then a moshaf if the reciter has more than one)
4. Pick a surah and send it to any media player

Examples:

- Reciter: `Maher Al Meaqli [102]`
- Moshaf: `Murattal [102]`
- Surah (English): `001 · Al-Fatihah · Makki · 7 ayahs`
- Surah (Arabic): `001 · الفاتحة · مكية · 7 آية`

### Options

Configure under the integration’s **Configure** menu:

| Option | Description | Default |
|--------|-------------|---------|
| Display language | `english` or `arabic` (names + sort order) | english |
| Default surah repeat | Times to play each surah when using `mp3quran.play` (1–20) | 1 |

Auto-advance is **not** an integration option. Enable it per call on `mp3quran.play` (defaults to off).

### Continuous play service

Media Browser alone plays one URL. For continuous listening, use:

```yaml
action: mp3quran.play
target:
  entity_id: media_player.living_room
data:
  reciter_id: 102
  moshaf_id: 102
  surah: 1
  auto_advance: true
  surah_repeat: 1
```

You can also target a **device** that includes a `media_player` entity; the integration resolves it to media players.

Stop a session **and** the current audio:

```yaml
action: mp3quran.stop
target:
  entity_id: media_player.living_room
```

Or press the matching **Stop MP3 Quran (...)** button entity created when a session starts on that player.

### Session status

- `sensor.mp3quran_active_sessions` — count of active continuous sessions; attributes list each player’s reciter/moshaf/surah.
- Per-player stop buttons remain available after a session ends for that Home Assistant run.

### Metadata

When playing via `mp3quran.play`, the integration sends Cast-style `extra.metadata` (title/artist) and uses `media_content_type: audio/mpeg` (same as Media Browser).

| Player | Metadata display | Notes |
|--------|------------------|-------|
| Chromecast / Cast | Usually works | Title/artist via Cast metadata |
| VLC | **Not supported** | VLC HA integration ignores `extra` and shows the MP3 filename |
| ESPHome speaker | **Not supported** | No metadata path for URL streams |

### Mid-track stop vs auto-advance

- Players that report `media_position` / `media_duration` (e.g. VLC): mid-track stop clears the session and does **not** advance.
- Stopping via Home Assistant (`media_player.media_stop` / turn off / pause) marks the session interrupted even when progress is unavailable.
- Players with **no** progress reporting (many ESPHome speakers): if you stop outside HA (device button / other path) with no stop service call, the integration cannot reliably tell mid-stop from end-of-track, so auto-advance may still continue. Use `mp3quran.stop` or the stop button for a guaranteed stop.

## Example automation

Play Al-Mulk every night after Isha on a Chromecast:

```yaml
alias: Nightly Al-Mulk
triggers:
  - trigger: time
    at: "21:30:00"
actions:
  - action: mp3quran.play
    target:
      entity_id: media_player.bedroom_cast
    data:
      reciter_id: 102
      surah: 67
      auto_advance: false
      surah_repeat: 1
```

## Development

```bash
python -m pip install pytest pytest-asyncio aiohttp voluptuous
pytest tests/ -q
```

## Attribution

Audio streams and catalog data are provided by [mp3quran.net](https://mp3quran.net). This project is not affiliated with mp3quran.net.

## License

MIT
