const ROOT_ID = "media-source://mp3quran";
const BRAND_ICON = "/mp3quran_brand/icon.png";
const VOLUME_SET = 4;
const VOLUME_STEP = 1024;

const STRINGS = {
  en: {
    dir: "ltr",
    title: "MP3 Quran",
    player: "Media player",
    reciter: "Reciter",
    moshaf: "Moshaf",
    surah: "Starting surah",
    repeat: "Surah repeat",
    advance: "Advance to next surah",
    play: "Play",
    stop: "Stop",
    pick: "Select",
    loading: "Loading…",
    idle: "No active session",
    error: "Could not load the catalog",
    missing: "Choose a media player, reciter, and surah",
    surahEmpty: "Select a surah",
    reciterEmpty: "Reciter and moshaf",
    playing: "Playing",
    paused: "Paused",
    volumeDown: "Volume down",
    volumeUp: "Volume up",
  },
  ar: {
    dir: "rtl",
    title: "قرآن MP3",
    player: "مشغل الوسائط",
    reciter: "القارئ",
    moshaf: "المصحف",
    surah: "سورة البداية",
    repeat: "تكرار السورة",
    advance: "الانتقال إلى السورة التالية",
    play: "تشغيل",
    stop: "إيقاف",
    pick: "اختر",
    loading: "جارٍ التحميل…",
    idle: "لا توجد جلسة نشطة",
    error: "تعذر تحميل القائمة",
    missing: "اختر مشغل الوسائط والقارئ والسورة",
    surahEmpty: "اختر سورة",
    reciterEmpty: "القارئ والمصحف",
    playing: "يعمل",
    paused: "متوقف مؤقتاً",
    volumeDown: "خفض الصوت",
    volumeUp: "رفع الصوت",
  },
};

function language(hass) {
  const code =
    (hass && hass.locale && hass.locale.language) ||
    (hass && hass.language) ||
    "en";
  return String(code).toLowerCase().startsWith("ar") ? "ar" : "en";
}

function strings(hass) {
  return STRINGS[language(hass)];
}

function idFromContent(contentId, key) {
  if (!contentId) return null;
  const marker = `/${key}/`;
  const index = contentId.lastIndexOf(marker);
  if (index === -1) return null;
  const value = parseInt(contentId.slice(index + marker.length).split("/")[0], 10);
  return Number.isFinite(value) ? value : null;
}

function asOption(child, key) {
  const id = idFromContent(child.media_content_id, key);
  if (id == null) return null;
  return { id, label: child.title || String(id) };
}

function clampRepeat(value) {
  const number = parseInt(value, 10);
  if (!Number.isFinite(number)) return 1;
  return Math.min(20, Math.max(1, number));
}

function errorText(err, fallback) {
  if (!err) return fallback;
  if (typeof err === "string") return err;
  return err.message || fallback;
}

function sessionFor(hass, entityId) {
  if (!hass || !entityId || !hass.states) return null;
  const known = [
    "sensor.mp3quran_active_sessions",
    "sensor.mp3_quran_active_sessions",
  ];
  const states = known
    .map((id) => hass.states[id])
    .filter(Boolean)
    .concat(Object.values(hass.states));
  for (const state of states) {
    if (!state || !state.entity_id || !state.entity_id.startsWith("sensor.")) {
      continue;
    }
    const session = state.attributes && state.attributes[entityId];
    if (session && typeof session === "object" && "surah" in session) {
      return session;
    }
  }
  return null;
}

function mediaPlayers(hass) {
  if (!hass || !hass.states) return [];
  return Object.values(hass.states)
    .filter((state) => state.entity_id && state.entity_id.startsWith("media_player."))
    .map((state) => ({
      id: state.entity_id,
      label: (state.attributes && state.attributes.friendly_name) || state.entity_id,
    }))
    .sort((a, b) => a.label.localeCompare(b.label));
}

async function browse(hass, contentId) {
  return hass.callWS({
    type: "media_source/browse_media",
    media_content_id: contentId,
  });
}

function fillSelect(select, options, selected, placeholder) {
  const value = selected == null || selected === "" ? "" : String(selected);
  const key = `${placeholder}\n${options.map((item) => `${item.id}\t${item.label}`).join("\n")}`;
  if (select.dataset.options !== key) {
    select.dataset.options = key;
    select.replaceChildren();
    if (placeholder) {
      const blank = document.createElement("option");
      blank.value = "";
      blank.textContent = placeholder;
      select.appendChild(blank);
    }
    options.forEach((item) => {
      const option = document.createElement("option");
      option.value = String(item.id);
      option.textContent = item.label;
      select.appendChild(option);
    });
  }
  if (select.value === value) return;
  const exists = Array.from(select.options).some((option) => option.value === value);
  if (exists || value === "") select.value = value;
}

const STYLE = `
  :host { display: block; }
  ha-card { overflow: hidden; }
  .header {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 14px 16px 10px;
  }
  .header img, .header ha-icon {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    flex: 0 0 auto;
  }
  .header .name {
    font-size: 1.12rem;
    font-weight: 650;
    letter-spacing: 0.01em;
    color: var(--primary-text-color);
  }
  .stage {
    margin: 0 16px 4px;
    padding: 18px 16px 16px;
    border-radius: 18px;
    text-align: center;
    color: #f4fbff;
    background:
      radial-gradient(90% 70% at 50% 0%, rgba(79, 195, 232, 0.45), transparent 60%),
      linear-gradient(180deg, #134556 0%, #0c2a34 100%);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.16);
  }
  .art {
    width: 76px;
    height: 76px;
    border-radius: 50%;
    margin: 0 auto 10px;
    display: block;
    background: rgba(255, 255, 255, 0.08);
    box-shadow: 0 10px 22px rgba(0, 0, 0, 0.28);
  }
  .surah-line {
    font-size: 1.12rem;
    font-weight: 650;
    line-height: 1.35;
  }
  .reciter-line {
    margin-top: 4px;
    font-size: 0.92rem;
    line-height: 1.35;
    opacity: 0.88;
  }
  .state-pill {
    display: inline-block;
    margin-top: 8px;
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 0.75rem;
    letter-spacing: 0.04em;
    background: rgba(255, 255, 255, 0.16);
  }
  .state-pill[hidden] { display: none; }
  ha-icon { --mdc-icon-size: 20px; }
  .body { display: flex; flex-direction: column; gap: 12px; padding: 12px 16px 16px; }
  label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--secondary-text-color); }
  label.hidden, .hidden { display: none; }
  select, input[type="number"] {
    width: 100%;
    box-sizing: border-box;
    padding: 8px 10px;
    border-radius: 10px;
    border: 1px solid var(--divider-color, rgba(127, 127, 127, 0.4));
    background: var(--card-background-color, transparent);
    color: var(--primary-text-color);
    font: inherit;
  }
  .volume {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .volume input[type="range"] {
    flex: 1;
    height: 4px;
    padding: 0;
    border: none;
    border-radius: 999px;
    accent-color: #1aa3d6;
    cursor: pointer;
  }
  .pct {
    min-width: 2.6em;
    text-align: end;
    font-size: 0.85rem;
    font-variant-numeric: tabular-nums;
    color: var(--primary-text-color);
  }
  .switch {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    font-size: 14px;
    color: var(--primary-text-color);
  }
  .actions { display: flex; gap: 8px; }
  button {
    flex: 1;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 10px 12px;
    border: none;
    border-radius: 999px;
    font: inherit;
    cursor: pointer;
  }
  button.icon {
    flex: 0 0 36px;
    width: 36px;
    height: 36px;
    padding: 0;
    border-radius: 50%;
    background: var(--secondary-background-color, rgba(127, 127, 127, 0.18));
    color: var(--primary-text-color);
  }
  button.play { background: #1287b8; color: #fff; }
  button.stop {
    background: var(--secondary-background-color, rgba(127, 127, 127, 0.2));
    color: var(--primary-text-color);
  }
  button:disabled { opacity: 0.5; cursor: default; }
  .status { color: var(--secondary-text-color); font-size: 0.9em; }
  .status.error { color: var(--error-color, #db4437); }
  .status[hidden] { display: none; }
`;

function brandImage(className) {
  const image = document.createElement("img");
  image.className = className;
  image.alt = "";
  image.src = BRAND_ICON;
  image.addEventListener("error", () => {
    const icon = document.createElement("ha-icon");
    icon.icon = "mdi:book-open-variant";
    icon.setAttribute("icon", "mdi:book-open-variant");
    image.replaceWith(icon);
  });
  return image;
}

function iconButton(className, iconName) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = className;
  const icon = document.createElement("ha-icon");
  icon.icon = iconName;
  icon.setAttribute("icon", iconName);
  button.append(icon);
  return button;
}

function buildShell(chrome) {
  const card = document.createElement("ha-card");
  const style = document.createElement("style");
  style.textContent = STYLE;
  const body = document.createElement("div");
  body.className = "body";

  let header = null;
  let title = null;
  let surahLine = null;
  let reciterLine = null;
  let statePill = null;
  let volume = null;

  if (chrome) {
    header = document.createElement("div");
    header.className = "header";
    title = document.createElement("div");
    title.className = "name";
    header.append(brandImage("logo"), title);

    const stage = document.createElement("div");
    stage.className = "stage";
    surahLine = document.createElement("div");
    surahLine.className = "surah-line";
    reciterLine = document.createElement("div");
    reciterLine.className = "reciter-line";
    statePill = document.createElement("div");
    statePill.className = "state-pill";
    statePill.hidden = true;
    stage.append(brandImage("art"), surahLine, reciterLine, statePill);

    const row = document.createElement("div");
    row.className = "volume";
    const down = iconButton("icon", "mdi:volume-minus");
    const slider = document.createElement("input");
    slider.type = "range";
    slider.min = "0";
    slider.max = "100";
    slider.step = "1";
    slider.value = "0";
    const pct = document.createElement("span");
    pct.className = "pct";
    pct.textContent = "0%";
    const up = iconButton("icon", "mdi:volume-plus");
    row.append(down, slider, pct, up);
    volume = { row, down, slider, pct, up };

    card.append(header, stage);
  }

  const player = field("select");
  const reciter = field("select");
  const moshaf = field("select");
  const surah = field("select");
  const repeat = field("input");
  repeat.input.type = "number";
  repeat.input.min = "1";
  repeat.input.max = "20";
  repeat.input.step = "1";
  const advance = document.createElement("label");
  advance.className = "switch";
  const advanceText = document.createElement("span");
  const advanceInput = document.createElement("input");
  advanceInput.type = "checkbox";
  advance.append(advanceText, advanceInput);

  const actions = document.createElement("div");
  actions.className = "actions";
  const play = document.createElement("button");
  play.type = "button";
  play.className = "play";
  const playIcon = document.createElement("ha-icon");
  playIcon.icon = "mdi:play";
  playIcon.setAttribute("icon", "mdi:play");
  const playLabel = document.createElement("span");
  play.append(playIcon, playLabel);
  const stop = document.createElement("button");
  stop.type = "button";
  stop.className = "stop";
  const stopIcon = document.createElement("ha-icon");
  stopIcon.icon = "mdi:stop";
  stopIcon.setAttribute("icon", "mdi:stop");
  const stopLabel = document.createElement("span");
  stop.append(stopIcon, stopLabel);
  actions.append(play, stop);

  const status = document.createElement("div");
  status.className = "status";
  status.setAttribute("role", "status");
  status.hidden = true;

  const rows = [player.label];
  if (volume) rows.push(volume.row);
  rows.push(reciter.label, moshaf.label, surah.label, repeat.label, advance, actions, status);
  body.append(...rows);
  card.append(body);
  return {
    card,
    style,
    header,
    title,
    surahLine,
    reciterLine,
    statePill,
    volume,
    player,
    reciter,
    moshaf,
    surah,
    repeat,
    advance,
    advanceText,
    advanceInput,
    actions,
    play,
    playLabel,
    stop,
    stopLabel,
    status,
  };
}

function field(kind) {
  const label = document.createElement("label");
  const text = document.createElement("span");
  const input = document.createElement(kind);
  label.append(text, input);
  return { label, text, input };
}

class Mp3QuranCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
    this._ready = false;
    this._entity = "";
    this._reciterId = null;
    this._moshafId = null;
    this._surah = null;
    this._repeat = 1;
    this._autoAdvance = false;
    this._reciters = [];
    this._moshafs = [];
    this._surahs = [];
    this._showMoshaf = false;
    this._token = 0;
    this._error = "";
    this._loading = false;
    this._playerKey = "";
    this._volumeHold = false;
  }

  static getConfigElement() {
    return document.createElement("mp3quran-card-editor");
  }

  static getStubConfig() {
    return { surah_repeat: 1, auto_advance: false };
  }

  setConfig(config) {
    if (!config || Array.isArray(config)) {
      throw new Error("Invalid configuration");
    }
    const first = !this._ready;
    this._config = config;
    if (first) {
      this._entity = config.entity || "";
      this._reciterId = numberOrNull(config.reciter_id);
      this._moshafId = numberOrNull(config.moshaf_id);
      this._surah = numberOrNull(config.surah);
      this._repeat = clampRepeat(config.surah_repeat == null ? 1 : config.surah_repeat);
      this._autoAdvance = Boolean(config.auto_advance);
    }
    if (this._hass) this._ensure();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._config) this._ensure();
  }

  getCardSize() {
    return 10;
  }

  _ensure() {
    if (!this._ui) {
      this._ui = buildShell(true);
      this.shadowRoot.replaceChildren(this._ui.style, this._ui.card);
      this._bind();
      this._ready = true;
    }
    this._applyStrings();
    this._paintPlayers();
    this._paintSelections();
    this._paintStatus();
    if (this._hass.callWS && !this._reciters.length && !this._loading) {
      this._loadReciters();
    }
  }

  _bind() {
    const ui = this._ui;
    ui.player.input.addEventListener("change", () => {
      this._entity = ui.player.input.value;
      this._error = "";
      this._paintStatus();
    });
    ui.reciter.input.addEventListener("change", () => {
      this._reciterId = numberOrNull(ui.reciter.input.value);
      this._moshafId = null;
      this._surah = null;
      this._error = "";
      this._loadReciter(this._reciterId);
    });
    ui.moshaf.input.addEventListener("change", () => {
      this._moshafId = numberOrNull(ui.moshaf.input.value);
      this._surah = null;
      this._error = "";
      this._loadMoshaf(this._reciterId, this._moshafId);
    });
    ui.surah.input.addEventListener("change", () => {
      this._surah = numberOrNull(ui.surah.input.value);
      this._error = "";
      this._paintStatus();
    });
    ui.repeat.input.addEventListener("change", () => {
      this._repeat = clampRepeat(ui.repeat.input.value);
      ui.repeat.input.value = String(this._repeat);
    });
    ui.advanceInput.addEventListener("change", () => {
      this._autoAdvance = ui.advanceInput.checked;
    });
    ui.play.addEventListener("click", () => this._play());
    ui.stop.addEventListener("click", () => this._stop());
    ui.volume.down.addEventListener("click", () => this._nudgeVolume(-1));
    ui.volume.up.addEventListener("click", () => this._nudgeVolume(1));
    ui.volume.slider.addEventListener("pointerdown", () => {
      this._volumeHold = true;
    });
    ui.volume.slider.addEventListener("pointerup", () => {
      this._volumeHold = false;
    });
    ui.volume.slider.addEventListener("input", () => {
      ui.volume.pct.textContent = `${ui.volume.slider.value}%`;
    });
    ui.volume.slider.addEventListener("change", () => this._setVolume());
  }

  _applyStrings() {
    const text = strings(this._hass);
    const ui = this._ui;
    ui.card.dir = text.dir;
    ui.title.textContent = text.title;
    ui.volume.down.setAttribute("aria-label", text.volumeDown);
    ui.volume.up.setAttribute("aria-label", text.volumeUp);
    ui.player.text.textContent = text.player;
    ui.reciter.text.textContent = text.reciter;
    ui.moshaf.text.textContent = text.moshaf;
    ui.surah.text.textContent = text.surah;
    ui.repeat.text.textContent = text.repeat;
    ui.advanceText.textContent = text.advance;
    ui.playLabel.textContent = text.play;
    ui.stopLabel.textContent = text.stop;
  }

  _paintPlayers() {
    const players = mediaPlayers(this._hass);
    const key = players.map((item) => item.id).join("|");
    if (key === this._playerKey && this._ui.player.input.options.length) return;
    this._playerKey = key;
    fillSelect(this._ui.player.input, players, this._entity, strings(this._hass).pick);
    if (!this._entity && this._ui.player.input.value) {
      this._entity = this._ui.player.input.value;
    }
  }

  _paintSelections() {
    const text = strings(this._hass);
    const ui = this._ui;
    fillSelect(ui.reciter.input, this._reciters, this._reciterId, text.pick);
    fillSelect(ui.moshaf.input, this._moshafs, this._moshafId, text.pick);
    fillSelect(ui.surah.input, this._surahs, this._surah, text.pick);
    ui.moshaf.label.classList.toggle("hidden", !this._showMoshaf);
    if (this.shadowRoot.activeElement !== ui.repeat.input) {
      ui.repeat.input.value = String(this._repeat);
    }
    ui.advanceInput.checked = this._autoAdvance;
    const canPlay = Boolean(this._entity && this._reciterId && this._surah) && !this._loading;
    ui.play.disabled = !canPlay;
    ui.stop.disabled = !this._entity;
  }

  _paintStatus() {
    const text = strings(this._hass);
    const ui = this._ui;
    this._paintNow();
    this._paintVolume();
    ui.status.classList.toggle("error", Boolean(this._error));
    if (this._error) {
      ui.status.hidden = false;
      ui.status.textContent = this._error;
      return;
    }
    if (this._loading) {
      ui.status.hidden = false;
      ui.status.textContent = text.loading;
      return;
    }
    ui.status.hidden = true;
    ui.status.textContent = "";
  }

  _paintNow() {
    const text = strings(this._hass);
    const ui = this._ui;
    const now = this._nowPlaying();
    ui.surahLine.textContent = now.surah || text.surahEmpty;
    ui.reciterLine.textContent = now.reciter || text.reciterEmpty;
    const player = this._hass && this._entity ? this._hass.states[this._entity] : null;
    const state = player && player.state;
    if (state === "playing" || state === "paused") {
      ui.statePill.hidden = false;
      ui.statePill.textContent = state === "playing" ? text.playing : text.paused;
    } else {
      ui.statePill.hidden = true;
      ui.statePill.textContent = "";
    }
  }

  _nowPlaying() {
    const text = strings(this._hass);
    const session = sessionFor(this._hass, this._entity);
    if (session && (session.title || session.artist)) {
      return {
        surah: session.title || text.surahEmpty,
        reciter: session.artist || text.reciterEmpty,
      };
    }
    const surah = this._surahs.find((item) => item.id === this._surah);
    const reciter = this._reciters.find((item) => item.id === this._reciterId);
    const moshaf = this._moshafs.find((item) => item.id === this._moshafId);
    const reciterLabel = [reciter && reciter.label, this._showMoshaf && moshaf && moshaf.label]
      .filter(Boolean)
      .join(" · ");
    return {
      surah: (surah && surah.label) || text.surahEmpty,
      reciter: reciterLabel || text.reciterEmpty,
    };
  }

  _paintVolume() {
    const ui = this._ui;
    const state = this._hass && this._entity ? this._hass.states[this._entity] : null;
    const attrs = (state && state.attributes) || {};
    const features = Number(attrs.supported_features) || 0;
    const level = typeof attrs.volume_level === "number" ? attrs.volume_level : null;
    const canSet = (features & VOLUME_SET) !== 0 || level != null;
    const canStep = (features & VOLUME_STEP) !== 0 || canSet;
    const show = Boolean(this._entity) && (canSet || canStep);
    ui.volume.row.classList.toggle("hidden", !show);
    ui.volume.slider.classList.toggle("hidden", !canSet);
    ui.volume.pct.classList.toggle("hidden", !canSet);
    ui.volume.down.disabled = !show;
    ui.volume.up.disabled = !show;
    if (!show || !canSet || this._volumeHold) return;
    if (this.shadowRoot.activeElement === ui.volume.slider) return;
    const pct = level == null ? 0 : Math.round(Math.min(1, Math.max(0, level)) * 100);
    ui.volume.slider.value = String(pct);
    ui.volume.pct.textContent = `${pct}%`;
  }

  async _setVolume() {
    if (!this._entity) return;
    const level = Math.min(1, Math.max(0, Number(this._ui.volume.slider.value) / 100));
    this._volumeHold = false;
    try {
      await this._hass.callService(
        "media_player",
        "volume_set",
        { volume_level: level },
        { entity_id: this._entity }
      );
    } catch (err) {
      this._error = errorText(err, strings(this._hass).error);
      this._paintStatus();
    }
  }

  async _nudgeVolume(direction) {
    if (!this._entity) return;
    const state = this._hass.states[this._entity];
    const attrs = (state && state.attributes) || {};
    const features = Number(attrs.supported_features) || 0;
    const canSet = (features & VOLUME_SET) !== 0 || typeof attrs.volume_level === "number";
    this._error = "";
    try {
      if (canSet) {
        const current =
          typeof attrs.volume_level === "number"
            ? attrs.volume_level
            : Number(this._ui.volume.slider.value) / 100;
        const next = Math.min(1, Math.max(0, current + direction * 0.05));
        this._ui.volume.slider.value = String(Math.round(next * 100));
        this._ui.volume.pct.textContent = `${Math.round(next * 100)}%`;
        await this._hass.callService(
          "media_player",
          "volume_set",
          { volume_level: next },
          { entity_id: this._entity }
        );
      } else {
        await this._hass.callService(
          "media_player",
          direction > 0 ? "volume_up" : "volume_down",
          {},
          { entity_id: this._entity }
        );
      }
    } catch (err) {
      this._error = errorText(err, strings(this._hass).error);
      this._paintStatus();
    }
  }

  async _loadReciters() {
    const token = ++this._token;
    this._loading = true;
    this._paintStatus();
    try {
      const page = await browse(this._hass, ROOT_ID);
      if (token !== this._token) return;
      this._reciters = (page.children || []).map((child) => asOption(child, "reciter")).filter(Boolean);
      this._paintSelections();
      if (this._reciterId != null) await this._loadReciter(this._reciterId, token);
    } catch (err) {
      if (token !== this._token) return;
      this._error = errorText(err, strings(this._hass).error);
    } finally {
      if (token === this._token) {
        this._loading = false;
        this._paintSelections();
        this._paintStatus();
      }
    }
  }

  async _loadReciter(reciterId, token = ++this._token) {
    if (reciterId == null) {
      this._moshafs = [];
      this._surahs = [];
      this._showMoshaf = false;
      this._paintSelections();
      return;
    }
    this._loading = true;
    this._paintStatus();
    try {
      const page = await browse(this._hass, `${ROOT_ID}/reciter/${reciterId}`);
      if (token !== this._token) return;
      const children = page.children || [];
      const surahs = children.filter((child) => child.can_play);
      if (surahs.length || !children.length) {
        this._showMoshaf = false;
        this._moshafs = [];
        this._moshafId = null;
        this._surahs = surahs.map((child) => asOption(child, "surah")).filter(Boolean);
        this._keepSurah();
      } else {
        this._moshafs = children.map((child) => asOption(child, "moshaf")).filter(Boolean);
        this._showMoshaf = this._moshafs.length > 1;
        if (!this._moshafs.some((item) => item.id === this._moshafId)) {
          this._moshafId = this._showMoshaf ? null : this._moshafs[0] ? this._moshafs[0].id : null;
        }
        this._surahs = [];
        if (this._moshafId != null) await this._loadMoshaf(reciterId, this._moshafId, token);
      }
    } catch (err) {
      if (token !== this._token) return;
      this._error = errorText(err, strings(this._hass).error);
    } finally {
      if (token === this._token) {
        this._loading = false;
        this._paintSelections();
        this._paintStatus();
      }
    }
  }

  async _loadMoshaf(reciterId, moshafId, token = ++this._token) {
    if (reciterId == null || moshafId == null) return;
    this._loading = true;
    this._paintStatus();
    try {
      const page = await browse(
        this._hass,
        `${ROOT_ID}/reciter/${reciterId}/moshaf/${moshafId}`
      );
      if (token !== this._token) return;
      this._surahs = (page.children || [])
        .map((child) => asOption(child, "surah"))
        .filter(Boolean);
      this._keepSurah();
    } catch (err) {
      if (token !== this._token) return;
      this._error = errorText(err, strings(this._hass).error);
    } finally {
      if (token === this._token) {
        this._loading = false;
        this._paintSelections();
        this._paintStatus();
      }
    }
  }

  _keepSurah() {
    if (!this._surahs.length) {
      this._surah = null;
      return;
    }
    if (!this._surahs.some((item) => item.id === this._surah)) {
      this._surah = this._surahs[0].id;
    }
  }

  async _play() {
    const text = strings(this._hass);
    this._repeat = clampRepeat(this._ui.repeat.input.value);
    this._autoAdvance = this._ui.advanceInput.checked;
    if (!this._entity || this._reciterId == null || this._surah == null) {
      this._error = text.missing;
      this._paintStatus();
      return;
    }
    const data = {
      reciter_id: this._reciterId,
      surah: this._surah,
      surah_repeat: this._repeat,
      auto_advance: this._autoAdvance,
    };
    if (this._showMoshaf && this._moshafId != null) {
      data.moshaf_id = this._moshafId;
    }
    this._error = "";
    try {
      await this._hass.callService("mp3quran", "play", data, { entity_id: this._entity });
    } catch (err) {
      this._error = errorText(err, text.error);
    }
    this._paintStatus();
  }

  async _stop() {
    if (!this._entity) return;
    this._error = "";
    try {
      await this._hass.callService("mp3quran", "stop", {}, { entity_id: this._entity });
    } catch (err) {
      this._error = errorText(err, strings(this._hass).error);
    }
    this._paintStatus();
  }
}

class Mp3QuranCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
    this._reciters = [];
    this._moshafs = [];
    this._surahs = [];
    this._showMoshaf = false;
    this._token = 0;
    this._loading = false;
  }

  setConfig(config) {
    this._config = { ...config };
    if (this._hass) this._ensure();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._config) this._ensure();
  }

  _ensure() {
    if (!this._ui) {
      this._ui = buildShell(false);
      this._ui.actions.remove();
      this._ui.status.remove();
      this.shadowRoot.replaceChildren(this._ui.style, this._ui.card);
      this._bind();
    }
    this._applyStrings();
    this._paint();
    if (this._hass.callWS && !this._reciters.length && !this._loading) {
      this._loading = true;
      this._load();
    }
  }

  _applyStrings() {
    const text = strings(this._hass);
    const ui = this._ui;
    ui.card.header = text.title;
    ui.card.dir = text.dir;
    ui.player.text.textContent = text.player;
    ui.reciter.text.textContent = text.reciter;
    ui.moshaf.text.textContent = text.moshaf;
    ui.surah.text.textContent = text.surah;
    ui.repeat.text.textContent = text.repeat;
    ui.advanceText.textContent = text.advance;
    ui.playLabel.textContent = text.play;
    ui.stopLabel.textContent = text.stop;
  }

  _paint() {
    const text = strings(this._hass);
    const ui = this._ui;
    fillSelect(ui.player.input, mediaPlayers(this._hass), this._config.entity || "", text.pick);
    fillSelect(ui.reciter.input, this._reciters, this._config.reciter_id, text.pick);
    fillSelect(ui.moshaf.input, this._moshafs, this._config.moshaf_id, text.pick);
    fillSelect(ui.surah.input, this._surahs, this._config.surah, text.pick);
    ui.moshaf.label.classList.toggle("hidden", !this._showMoshaf);
    if (this.shadowRoot.activeElement !== ui.repeat.input) {
      ui.repeat.input.value = String(
        clampRepeat(this._config.surah_repeat == null ? 1 : this._config.surah_repeat)
      );
    }
    ui.advanceInput.checked = Boolean(this._config.auto_advance);
  }

  _bind() {
    const ui = this._ui;
    ui.player.input.addEventListener("change", () => {
      this._commit({ entity: ui.player.input.value || undefined });
    });
    ui.reciter.input.addEventListener("change", () => {
      const reciterId = numberOrNull(ui.reciter.input.value);
      this._commit({
        reciter_id: reciterId == null ? undefined : reciterId,
        moshaf_id: undefined,
        surah: undefined,
      });
      this._loadReciter(reciterId);
    });
    ui.moshaf.input.addEventListener("change", () => {
      const moshafId = numberOrNull(ui.moshaf.input.value);
      this._commit({
        moshaf_id: moshafId == null ? undefined : moshafId,
        surah: undefined,
      });
      this._loadMoshaf(numberOrNull(this._config.reciter_id), moshafId);
    });
    ui.surah.input.addEventListener("change", () => {
      const surah = numberOrNull(ui.surah.input.value);
      this._commit({ surah: surah == null ? undefined : surah });
    });
    ui.repeat.input.addEventListener("change", () => {
      this._commit({ surah_repeat: clampRepeat(ui.repeat.input.value) });
    });
    ui.advanceInput.addEventListener("change", () => {
      this._commit({ auto_advance: ui.advanceInput.checked });
    });
  }

  _commit(patch) {
    const config = { ...this._config, ...patch };
    Object.keys(config).forEach((key) => {
      if (config[key] === undefined || config[key] === "") delete config[key];
    });
    this._config = config;
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config },
        bubbles: true,
        composed: true,
      })
    );
  }

  async _load() {
    try {
      const page = await browse(this._hass, ROOT_ID);
      this._reciters = (page.children || []).map((child) => asOption(child, "reciter")).filter(Boolean);
      this._paint();
      const reciterId = numberOrNull(this._config.reciter_id);
      if (reciterId != null) await this._loadReciter(reciterId);
    } catch (_err) {
      /* The card shows catalog errors; the editor can stay on manual ids. */
    } finally {
      this._loading = false;
    }
  }

  async _loadReciter(reciterId) {
    if (reciterId == null || !this._hass || !this._hass.callWS) return;
    const token = ++this._token;
    try {
      const page = await browse(this._hass, `${ROOT_ID}/reciter/${reciterId}`);
      if (token !== this._token) return;
      const children = page.children || [];
      const surahs = children.filter((child) => child.can_play);
      if (surahs.length || !children.length) {
        this._showMoshaf = false;
        this._moshafs = [];
        this._surahs = surahs.map((child) => asOption(child, "surah")).filter(Boolean);
      } else {
        this._moshafs = children.map((child) => asOption(child, "moshaf")).filter(Boolean);
        this._showMoshaf = this._moshafs.length > 1;
        const moshafId = numberOrNull(this._config.moshaf_id) || (this._moshafs[0] && this._moshafs[0].id);
        if (moshafId != null) await this._loadMoshaf(reciterId, moshafId, token);
      }
      if (token === this._token) this._paint();
    } catch (_err) {
      /* Ignore browse failures in the editor. */
    }
  }

  async _loadMoshaf(reciterId, moshafId, token = ++this._token) {
    if (reciterId == null || moshafId == null || !this._hass || !this._hass.callWS) return;
    try {
      const page = await browse(
        this._hass,
        `${ROOT_ID}/reciter/${reciterId}/moshaf/${moshafId}`
      );
      if (token !== this._token) return;
      this._surahs = (page.children || []).map((child) => asOption(child, "surah")).filter(Boolean);
      this._paint();
    } catch (_err) {
      /* Ignore browse failures in the editor. */
    }
  }
}

function numberOrNull(value) {
  if (value == null || value === "") return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

if (!customElements.get("mp3quran-card")) {
  customElements.define("mp3quran-card", Mp3QuranCard);
}
if (!customElements.get("mp3quran-card-editor")) {
  customElements.define("mp3quran-card-editor", Mp3QuranCardEditor);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "mp3quran-card")) {
  window.customCards.push({
    type: "mp3quran-card",
    name: "MP3 Quran",
    description: "Play a Quran recitation on a media player",
    preview: true,
  });
}
