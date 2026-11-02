# Changelog

## 1.4.4

- The dashboard card is added to Settings, Dashboards, Resources when Home Assistant finishes starting, as `/mp3quran/mp3quran-card.js`.

## 1.4.1

Changes since 1.1.0.

### Dashboard card

- Lovelace card `custom:mp3quran-card` is included with the integration and appears in the card picker after a restart.
- Choose the media player, reciter, moshaf, starting surah, surah repeat, and whether to advance to the next surah.
- The title shows the MP3 Quran icon.
- The current surah is shown above the reciter and moshaf, and both sit above the media player selector.
- Volume slider, volume down, and volume up control the selected media player.

### Favorite reciters

- New option to mark reciters as favorites.
- Favorites stay at the top of the MP3 Quran media source and their titles start with a star.
- Names follow the configured display language in English and Arabic.

### Playback

- Auto-advance defaults to off and is set on each `mp3quran.play` call.
- `mp3quran.play` and `mp3quran.stop` accept a media player entity, or a device or area that includes one.
- `mp3quran.stop` clears the continuous session and stops the current audio.
- Stopping in the middle of a surah does not advance to the next one.
- When auto-advance is on, the next surah starts after a natural end, including on players that do not report playback progress.
- Chromecast playback sends the surah, reciter, and moshaf as the track title and artist.
- The VLC playlist is cleared before each surah so earlier surahs are not played again.

### Sessions

- `sensor.mp3quran_active_sessions` reports how many continuous sessions are running, with the surah and reciter for each player.
- The sensor icon is an open book.
- A stop button is created for each media player that has had a session and remains available for that Home Assistant run.

## 1.1.0

- Media source for mp3quran.net reciters, moshafs, and surahs.
- English and Arabic names, with mp3quran IDs shown beside reciters and moshafs.
- `mp3quran.play` and `mp3quran.stop` services.
- Official mp3quran.net icon.
