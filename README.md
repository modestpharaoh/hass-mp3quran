# MP3 Quran for Home Assistant

Browse and play Quran recitations from [mp3quran.net](https://mp3quran.net) in Home Assistant — similar to the built-in Radio Browser integration.

Play any of the 114 surahs by many reciters on any media player (VLC, Cast, browser, Music Assistant, etc.).

![MP3 Quran](icon.png)

## Features

- **Media source** — appears in **Media** as **MP3 Quran**
- **Live catalog** — reciters and moshafs loaded from the mp3quran.net API on setup/reload
- **Bilingual UI** — English and Arabic names for reciters, moshafs, and surahs
- **Sort options** — sort reciters by English or Arabic name
- **Surah details** — number, EN/AR name, Makki/Madani, ayah count
- **Incomplete moshafs** — only available surahs are listed
- **Continuous playback** — optional auto-advance to the next surah
- **Surah repeat** — play each surah N times before advancing
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

Surah titles look like:

`001 · Al-Fatihah · الفاتحة · Makki · 7 ayahs`

### Options

Configure under the integration’s **Configure** menu:

| Option | Description | Default |
|--------|-------------|---------|
| Sort reciters by | `english` or `arabic` | english |
| Auto-play next surah | Advance when the current surah ends | on |
| Repeat each surah | Times to play each surah before advancing (1–20) | 1 |

### Continuous play service

Media Browser alone plays one URL. For reliable auto-advance / repeat on VLC, Cast, and similar players, use the service:

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

Stop tracking a continuous session:

```yaml
action: mp3quran.stop
target:
  entity_id: media_player.living_room
```

When auto-advance is enabled, playing a known mp3quran URL from Media Browser will also attach a session so the next surah can continue on that player.

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
