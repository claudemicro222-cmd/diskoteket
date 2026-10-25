// Diskoteket-kortet för Home Assistant. Följer med integrationen och laddas automatiskt.
// Detaljnivå väljs i kortets inställningar: kompakt, standard eller detaljerad.

const DK_VERSION = "4.1.1";
const LEVELS = { compact: "Kompakt", standard: "Standard", detailed: "Detaljerad" };
const VARIOUS = ["various", "various artists", "va", "blandade artister"];

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const num = (n) => Number(n || 0).toLocaleString("sv-SE");
const artistName = (a) => (a && VARIOUS.includes(a.trim().toLowerCase()) ? "Blandade artister" : a || "");

const LOGO = `<svg viewBox="0 0 64 64" aria-hidden="true"><defs>
  <radialGradient id="dkd" cx="42%" cy="36%" r="78%"><stop offset="0" stop-color="#fff"/><stop offset=".5" stop-color="#d9dee8"/><stop offset="1" stop-color="#8d96a8"/></radialGradient>
  <radialGradient id="dkl" cx="40%" cy="35%" r="70%"><stop offset="0" stop-color="#ffe08a"/><stop offset=".6" stop-color="#f5b301"/><stop offset="1" stop-color="#c47f00"/></radialGradient></defs>
  <circle cx="32" cy="32" r="29" fill="url(#dkd)"/>
  <path d="M32 32 L32 3 A29 29 0 0 1 57 18 Z" fill="#ff7ab6" opacity=".35"/><path d="M32 32 L7 46 A29 29 0 0 1 6 22 Z" fill="#4de1ff" opacity=".35"/>
  <circle cx="32" cy="32" r="12.5" fill="url(#dkl)"/><path d="M28.5 26 L38 32 L28.5 38 Z" fill="#141720"/></svg>`;

const ICONS = {
  movies: "mdi:movie-open", series: "mdi:television-classic", music: "mdi:album", unwatched: "mdi:eye-off-outline",
  wishlist: "mdi:star-outline", loaned: "mdi:hand-extended-outline", discs: "mdi:disc", value: "mdi:cash-multiple",
};

class DiskoteketCard extends HTMLElement {
  static getConfigElement() { return document.createElement("diskoteket-card-editor"); }

  static getStubConfig(hass) {
    return { entity: findEntity(hass) || "", detail: "standard" };
  }

  setConfig(config) {
    this._config = { detail: "standard", show_music: true, show_covers: true, ...config };
    if (!LEVELS[this._config.detail]) this._config.detail = "standard";
    this._sig = null;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    const id = this._config?.entity || findEntity(hass);
    const st = id && hass.states[id];
    const sig = st ? st.last_updated + this._config.detail : "none";
    if (sig !== this._sig) { this._sig = sig; this._render(); }
  }

  getCardSize() { return { compact: 2, standard: 4, detailed: 8 }[this._config?.detail] || 4; }

  getGridOptions() {
    const rows = { compact: 2, standard: 4, detailed: 8 }[this._config?.detail] || 4;
    return { columns: 12, rows, min_columns: 6, min_rows: 2 };
  }

  _render() {
    if (!this._config) return;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const hass = this._hass;
    const id = this._config.entity || (hass && findEntity(hass));
    const st = hass && id ? hass.states[id] : null;
    const title = this._config.title || "Diskoteket";
    if (!st) {
      this.shadowRoot.innerHTML = `${STYLE}<ha-card><div class="wrap"><div class="head">${LOGO}<div><div class="title">${esc(title)}</div>
        <div class="sub">${hass ? "Hittade ingen Diskoteket-sensor. Lägg till integrationen Diskoteket först." : "Laddar…"}</div></div></div></div></ha-card>`;
      return;
    }
    const a = st.attributes;
    const lvl = this._config.detail;
    const music = this._config.show_music !== false && (a.music || 0) > 0;
    const video = (a.movies || 0) + (a.seasons || 0);
    const total = Number(st.state) || 0;
    const subtitle = [`${num(a.movies)} filmer`, `${num(a.series)} serier`, music ? `${num(a.music)} album` : null].filter(Boolean).join(" · ");

    const pill = (key, n, label) => `<div class="pill"><ha-icon icon="${ICONS[key]}"></ha-icon><b>${num(n)}</b><span>${label}</span></div>`;
    const tile = (key, n, label, cls = "") => `<div class="tile ${cls}"><ha-icon icon="${ICONS[key]}"></ha-icon>
      <div><b>${typeof n === "string" ? n : num(n)}</b><span>${label}</span></div></div>`;
    const overdue = a.overdue ? `<div class="alert"><ha-icon icon="mdi:clock-alert-outline"></ha-icon>
      <span><b>${a.overdue} ${a.overdue === 1 ? "försenat lån" : "försenade lån"}</b>
      ${(a.overdue_list || []).slice(0, lvl === "detailed" ? 5 : 2).map((o) => `<br>${esc(o.title)} – ${esc(o.loaned_to)} (${esc(o.due_date)})`).join("")}</span></div>` : "";

    let body = "";
    if (lvl === "compact") {
      body = `<div class="pills">${pill("movies", a.movies, "filmer")}${pill("series", a.series, "serier")}
        ${music ? pill("music", a.music, "album") : pill("unwatched", a.unwatched, "osedda")}</div>
        ${a.overdue ? `<div class="alert small"><ha-icon icon="mdi:clock-alert-outline"></ha-icon><span>${a.overdue} ${a.overdue === 1 ? "försenat lån" : "försenade lån"}</span></div>` : ""}`;
    } else {
      body = `<div class="tiles">
        ${tile("movies", a.movies, "filmer", "hl")}${tile("series", a.series, `serier · ${num(a.seasons)} säsonger`)}
        ${music ? tile("music", a.music, "album") : tile("discs", a.discs, "skivor")}
        ${tile("unwatched", a.unwatched, "osedda")}${tile("wishlist", a.wishlist, "önskelista")}${tile("loaned", a.loaned, "utlånat")}
        ${lvl === "detailed" ? `${tile("discs", a.discs, "skivor")}${a.value ? tile("value", `${num(Math.round(a.value))} kr`, "inköpsvärde") : ""}` : ""}
      </div>${overdue}`;
      const latest = (a.latest || []).filter((i) => music || i.kind !== "music");
      if (lvl === "standard" && latest[0]) {
        const l = latest[0];
        body += `<div class="latest-line"><ha-icon icon="mdi:new-box"></ha-icon><span>Senast: <b>${esc(l.kind === "music" ? `${artistName(l.artist)} – ${l.title}` : l.title)}</b>
          <span class="muted">${esc(l.added_date || "")}</span></span></div>`;
      }
      if (lvl === "detailed") {
        if (this._config.show_covers !== false && latest.length) {
          body += `<div class="section">Nyligen tillagt</div><div class="shelf">${latest.slice(0, 10).map((l, i) => `
            <div class="cover ${l.kind === "music" ? "sq" : ""}"><div class="img" data-p="${esc(l.poster_path || "")}" data-i="${i}">
              ${l.poster_path ? "" : `<span>${esc(l.title)}</span>`}</div>
              <div class="ct">${esc(l.title)}</div><div class="cs">${esc(l.kind === "music" ? artistName(l.artist) : l.year || "")}</div></div>`).join("")}</div>`;
        }
        const colls = (a.collections || []).filter((c) => c.titles);
        if (colls.length > 1) {
          const max = Math.max(...colls.map((c) => c.titles));
          body += `<div class="section">Samlingar</div>${colls.map((c) => `<div class="bar-row"><span>${esc(c.name)}</span>
            <span class="bar"><i style="width:${(c.titles / max) * 100}%"></i></span><b>${num(c.titles)}</b></div>`).join("")}`;
        }
        if ((a.formats || []).length) {
          body += `<div class="section">Format</div><div class="chips">${a.formats.map((f) => `<span class="chip">${esc(f.label)} <b>${num(f.n)}</b></span>`).join("")}</div>`;
        }
      }
    }

    this.shadowRoot.innerHTML = `${STYLE}<ha-card class="${lvl}"><div class="wrap">
      <div class="head">${LOGO}<div class="grow"><div class="title">${esc(title)}</div><div class="sub">${subtitle}</div></div>
        <div class="big"><b>${num(total)}</b><span>${music ? "titlar & album" : "titlar"}</span></div></div>
      ${body}</div></ha-card>`;
    this.shadowRoot.querySelector(".head").onclick = () => this._more(id);
    if (lvl === "detailed") this._loadCovers(a.diskoteket_entry);
  }

  _more(entityId) {
    const ev = new Event("hass-more-info", { bubbles: true, composed: true });
    ev.detail = { entityId };
    this.dispatchEvent(ev);
  }

  // Omslagen hämtas via Home Assistant (signerade adresser), så de fungerar även utanför hemmet
  async _loadCovers(entry) {
    if (!entry || !this._hass) return;
    this._covers = this._covers || new Map();
    for (const el of this.shadowRoot.querySelectorAll(".img[data-p]")) {
      const p = el.dataset.p.replace(/^\//, "");
      if (!p) continue;
      try {
        if (!this._covers.has(p)) {
          const r = await this._hass.callWS({ type: "auth/sign_path", path: `/api/diskoteket/${entry}/poster/${p}`, expires: 86400 });
          this._covers.set(p, r.path);
        }
        el.style.backgroundImage = `url("${this._covers.get(p)}")`;
      } catch (e) { /* utan omslag går också bra */ }
    }
  }
}

function findEntity(hass) {
  if (!hass) return null;
  return Object.keys(hass.states).find((k) => k.startsWith("sensor.") && hass.states[k].attributes?.diskoteket_entry) || null;
}

const STYLE = `<style>
  :host { display: block; min-width: 0; --dk-accent: #f5b301; --dk-accent2: #ff8a1f; }
  ha-card { overflow: hidden; position: relative; container-type: inline-size; }
  ha-card::before { content: ""; position: absolute; inset: 0; pointer-events: none;
    background: radial-gradient(120% 140px at 0% 0%, color-mix(in srgb, var(--dk-accent) 14%, transparent), transparent); }
  .wrap { position: relative; padding: 16px; }
  .head { display: flex; align-items: center; gap: 12px; cursor: pointer; }
  .head svg { width: 44px; height: 44px; flex: none; filter: drop-shadow(0 3px 8px rgba(0,0,0,.35)); }
  .grow { flex: 1; min-width: 0; }
  .title { font-size: 1.25rem; font-weight: 800; letter-spacing: -.02em;
    background: linear-gradient(100deg, var(--primary-text-color) 30%, var(--dk-accent) 75%, var(--dk-accent2));
    -webkit-background-clip: text; background-clip: text; color: transparent; }
  .sub, .muted { color: var(--secondary-text-color); font-size: .85rem; }
  .big { text-align: right; }
  .big b { display: block; font-size: 1.8rem; line-height: 1; font-weight: 800; letter-spacing: -.03em; }
  .big span { font-size: .72rem; color: var(--secondary-text-color); text-transform: uppercase; letter-spacing: .06em; }
  .compact .big b { font-size: 1.5rem; }
  .pills { display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; }
  .pill { display: flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 999px;
    background: var(--secondary-background-color); font-size: .85rem; }
  .pill ha-icon { --mdc-icon-size: 18px; color: var(--dk-accent); }
  .pill span { color: var(--secondary-text-color); }
  .tiles { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 14px; }
  .tile { display: flex; align-items: center; gap: 10px; padding: 10px; border-radius: 12px; background: var(--secondary-background-color); min-width: 0; }
  .tile ha-icon { --mdc-icon-size: 22px; color: var(--secondary-text-color); flex: none; }
  .tile.hl ha-icon { color: var(--dk-accent); }
  .tile b { display: block; font-size: 1.15rem; line-height: 1.1; white-space: nowrap; }
  .tile span { font-size: .72rem; color: var(--secondary-text-color); display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .alert { display: flex; gap: 10px; align-items: flex-start; margin-top: 12px; padding: 10px 12px; border-radius: 12px;
    background: color-mix(in srgb, var(--error-color, #db4437) 14%, transparent); font-size: .85rem; }
  .alert ha-icon { color: var(--error-color, #db4437); --mdc-icon-size: 20px; }
  .alert.small { padding: 6px 10px; margin-top: 10px; }
  .latest-line { display: flex; gap: 8px; align-items: center; margin-top: 12px; font-size: .88rem; }
  .latest-line ha-icon { --mdc-icon-size: 20px; color: var(--dk-accent); }
  .section { margin: 16px 0 8px; font-size: .72rem; text-transform: uppercase; letter-spacing: .1em; color: var(--secondary-text-color); }
  .shelf { display: flex; gap: 10px; overflow-x: auto; padding-bottom: 6px; scrollbar-width: thin; }
  .cover { flex: 0 0 84px; min-width: 0; }
  .cover.sq { flex-basis: 96px; }
  .img { aspect-ratio: 2/3; border-radius: 8px; background: var(--secondary-background-color) center/cover no-repeat;
    box-shadow: 0 4px 12px rgba(0,0,0,.3); display: flex; align-items: center; justify-content: center; text-align: center;
    font-size: .65rem; color: var(--secondary-text-color); padding: 4px; box-sizing: border-box; }
  .sq .img { aspect-ratio: 1/1; }
  .ct { font-size: .75rem; margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .cs { font-size: .68rem; color: var(--secondary-text-color); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .bar-row { display: grid; grid-template-columns: minmax(70px, 30%) 1fr auto; gap: 8px; align-items: center; font-size: .82rem; margin: 4px 0; }
  .bar { height: 8px; border-radius: 99px; background: var(--secondary-background-color); overflow: hidden; }
  .bar i { display: block; height: 100%; border-radius: 99px; background: linear-gradient(90deg, var(--dk-accent), var(--dk-accent2)); }
  .chips { display: flex; flex-wrap: wrap; gap: 6px; }
  .chip { font-size: .75rem; padding: 3px 9px; border-radius: 99px; background: var(--secondary-background-color); }
  .title { white-space: nowrap; }
  /* Smala kort (t.ex. en kolumn i Home Assistant): mindre siffra, kortare rader, två rutor i bredd */
  @container (max-width: 460px) {
    .wrap { padding: 14px; }
    .head svg { width: 38px; height: 38px; }
    .title { font-size: 1.1rem; }
    .sub { font-size: .78rem; }
    .big b { font-size: 1.45rem; }
    .big span { font-size: .62rem; }
    .tiles { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  }
  @container (max-width: 330px) { .big { display: none; } }
</style>`;

// ---------- Redigeraren (kortets inställningar) ----------

const SCHEMA = [
  { name: "entity", selector: { entity: { filter: { integration: "diskoteket", domain: "sensor" } } } },
  { name: "detail", selector: { select: { mode: "list", options: Object.entries(LEVELS).map(([value, label]) => ({ value, label })) } } },
  { name: "title", selector: { text: {} } },
  { name: "show_music", selector: { boolean: {} } },
  { name: "show_covers", selector: { boolean: {} } },
];
const LABELS = { entity: "Sensor (Diskoteket Titlar)", detail: "Detaljnivå", title: "Rubrik (valfri)",
  show_music: "Visa musik", show_covers: "Visa omslag (detaljerad)" };
const HELPERS = { detail: "Kompakt: bara antal. Standard: siffror, försenade lån och senast tillagd. Detaljerad: även omslag, samlingar och format." };

class DiskoteketCardEditor extends HTMLElement {
  setConfig(config) { this._config = { detail: "standard", show_music: true, show_covers: true, ...config }; this._render(); }
  set hass(hass) { this._hass = hass; this._render(); }

  _render() {
    if (!this._hass || !this._config) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.computeLabel = (s) => LABELS[s.name] || s.name;
      this._form.computeHelper = (s) => HELPERS[s.name];
      this._form.addEventListener("value-changed", (e) => {
        this._config = e.detail.value;
        this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._config }, bubbles: true, composed: true }));
      });
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.schema = SCHEMA;
    this._form.data = this._config;
  }
}

if (!customElements.get("diskoteket-card")) customElements.define("diskoteket-card", DiskoteketCard);
if (!customElements.get("diskoteket-card-editor")) customElements.define("diskoteket-card-editor", DiskoteketCardEditor);
window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "diskoteket-card")) {
  window.customCards.push({ type: "diskoteket-card", name: "Diskoteket", preview: true,
    description: "Din film-, serie- och musiksamling – välj hur detaljerat kortet ska vara.",
    documentationURL: "https://github.com/claudemicro222-cmd/diskoteket" });
}
console.info(`%c DISKOTEKET-KORT %c ${DK_VERSION} `, "background:#f5b301;color:#17120a;font-weight:700", "background:#1c2130;color:#fff");
