// Diskoteket – webbsidan. Ingen byggprocess, bara vanlig JavaScript.
"use strict";
const TMDB_IMG = "https://image.tmdb.org/t/p/";
const $ = (s, root = document) => root.querySelector(s);
const $$ = (s, root = document) => [...root.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const pipe = (s) => (s || "").replaceAll(" | ", ", ");
const ymd = (d) => d.toLocaleDateString("sv-SE"); // lokalt datum, ÅÅÅÅ-MM-DD
const today = () => ymd(new Date());
const isWish = (it) => /wish/i.test(it.collection_status || "");
const store = {
  get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* privat läge */ } },
};

const DEFAULT_FILTERS = { sort: "title", format: "", genre: "", watched: "", digital: "", loaned: false };
let state = {
  tab: "all", q: "", field: "title", items: [], facets: null, libs: [],
  lib: store.get("lib", null),               // samlingens id, eller "all"
  view: store.get("view", "grid-m"),          // grid-s, grid-m, grid-l, list, compact
  theme: store.get("theme", "auto"),          // auto, light, dark
  ...DEFAULT_FILTERS, ...store.get("filters", {}),
};
delete state.location; // platsfiltret är borttaget – rensa ev. gammalt sparat värde

async function api(path, opts = {}) {
  if (opts.json !== undefined) {
    opts.body = JSON.stringify(opts.json);
    opts.headers = { "Content-Type": "application/json" };
  }
  const r = await fetch(path, opts);
  const data = await r.json().catch(() => ({}));
  if (r.status === 401 && data.login) location.reload(); // utloggad – sidan visar inloggningen
  if (!r.ok) {
    const err = new Error(data.detail || r.statusText);
    err.status = r.status; err.data = data;
    throw err;
  }
  return data;
}
const patch = (id, json) => api(`/api/items/${id}`, { method: "PATCH", json });
const libParam = () => `lib=${state.lib === "all" ? "all" : state.lib}`;
const libName = (id) => state.libs.find((l) => l.id === id)?.name || "";
const currentLibId = () => (state.lib === "all" ? state.libs[0]?.id : state.lib);

function poster(path, title, cls = "") {
  return path
    ? `<img class="poster ${cls}" loading="lazy" src="/poster${esc(path)}" alt="">`
    : `<div class="poster none ${cls}">${title ? `<span>${esc(title)}</span>` : ""}</div>`;
}
// Omslag från nätet (förslag vid sökning) – döljs tyst om bilden saknas
const netCover = (url, cls = "thumb") => url
  ? `<img class="poster ${cls}" loading="lazy" src="${esc(url)}" alt="" onerror="this.style.visibility='hidden'">`
  : `<div class="poster none ${cls}"></div>`;

const VARIOUS = ["various", "various artists", "va", "blandade artister"];
const artistName = (a) => (a && VARIOUS.includes(a.trim().toLowerCase()) ? "Blandade artister" : a || "");
const isMusic = (it) => it.kind === "music";
const MUSIC_FORMATS = ["CD", "Vinyl", "Kassett", "SACD", "DVD-Audio", "Blu-ray", "Digital"];
const lenText = (min) => (min >= 60 ? `${Math.floor(min / 60)} h ${min % 60} min` : `${min} min`);

// ---------- Formatmärken ----------

const DISC = `<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="7" fill="currentColor" opacity=".9"/><circle cx="8" cy="8" r="2.2" fill="var(--fmt-bg, #000)"/><path d="M8 2.6a5.4 5.4 0 0 1 5.1 3.7" stroke="var(--fmt-bg,#000)" stroke-width="1" fill="none" opacity=".5"/></svg>`;
const PLAY = `<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 2.5v11l9.5-5.5z" fill="currentColor"/></svg>`;
const TAPE = `<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="1" y="3.5" width="14" height="9" rx="1.5" fill="currentColor"/><circle cx="5.2" cy="8" r="1.8" fill="var(--fmt-bg,#000)"/><circle cx="10.8" cy="8" r="1.8" fill="var(--fmt-bg,#000)"/></svg>`;
const VINYL = `<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="7" fill="currentColor"/><circle cx="8" cy="8" r="4.6" fill="none" stroke="var(--fmt-bg,#000)" stroke-width=".6" opacity=".6"/><circle cx="8" cy="8" r="2.4" fill="#e0533c"/><circle cx="8" cy="8" r=".7" fill="var(--fmt-bg,#000)"/></svg>`;

function formatInfo(format) {
  const f = (format || "").toLowerCase();
  const threeD = /3d/.test(f);
  if (/vinyl|\blp\b|"/.test(f)) return { cls: "vinyl", label: "Vinyl", icon: VINYL };
  if (/sacd/.test(f)) return { cls: "cd", label: "SACD", icon: DISC };
  if (/^cd|\bcd\b/.test(f)) return { cls: "cd", label: "CD", icon: DISC };
  if (/kassett|cassette/.test(f)) return { cls: "tape", label: "Kassett", icon: TAPE };
  if (/4k|uhd|ultra/.test(f)) return { cls: "uhd", label: "4K", icon: DISC, threeD };
  if (/blu/.test(f)) return { cls: "bd", label: "Blu-ray", icon: DISC, threeD };
  if (/hd.?dvd/.test(f)) return { cls: "bd", label: "HD DVD", icon: DISC, threeD };
  if (/dvd/.test(f)) return { cls: "dvd", label: "DVD", icon: DISC, threeD };
  if (/digital|stream|itunes|file/.test(f)) return { cls: "dig", label: "Digital", icon: PLAY, threeD };
  if (/vhs/.test(f)) return { cls: "vhs", label: "VHS", icon: TAPE, threeD };
  if (/laser/.test(f)) return { cls: "dvd", label: "LD", icon: DISC, threeD };
  return f ? { cls: "other", label: format.slice(0, 10), icon: DISC, threeD } : null;
}

function fmtBadge(format, extraCls = "") {
  const i = formatInfo(format);
  if (!i) return "";
  return `<span class="fmt fmt-${i.cls} ${extraCls}" title="${esc(format)}">${i.icon}<b>${esc(i.label)}</b>${i.threeD ? `<i>3D</i>` : ""}</span>`;
}

function listItem(it, right = "") {
  return `<div class="list-item" data-id="${it.id ?? ""}">${poster(it.poster_path, "", isMusic(it) ? "thumb square" : "thumb")}
    <div class="grow"><div class="li-title">${esc(it.title)}</div>
    <div class="muted small li-sub">${isMusic(it) ? esc(artistName(it.artist)) + " · " : ""}${it.year || ""} ${fmtBadge(it.format, "sm")} ${esc(it.location || "")}
    ${state.lib === "all" && it.library_id ? `<span class="lib-tag">${esc(libName(it.library_id))}</span>` : ""}</div></div>${right}</div>`;
}
function bindOpen(root = $("#sheet-body")) {
  $$(".list-item[data-id]", root).forEach((el) => el.dataset.id && (el.onclick = () => show(viewItem, +el.dataset.id)));
}

let toastTimer;
function toast(msg, kind = "") {
  const t = $("#toast");
  t.innerHTML = msg;
  t.className = kind;
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (t.hidden = true), 2600);
}

// Pip-ljud vid skanning: högt dubbelpip = finns redan, lågt = ny
let audio;
function beep(kind) {
  try {
    audio = audio || new (window.AudioContext || window.webkitAudioContext)();
    const tones = kind === "owned" ? [[1320, 0], [1320, 0.13]] : kind === "wish" ? [[990, 0], [1320, 0.12]] : [[440, 0]];
    for (const [freq, at] of tones) {
      const o = audio.createOscillator(), g = audio.createGain();
      o.frequency.value = freq; o.connect(g); g.connect(audio.destination);
      g.gain.setValueAtTime(0.15, audio.currentTime + at);
      g.gain.exponentialRampToValueAtTime(0.001, audio.currentTime + at + 0.11);
      o.start(audio.currentTime + at); o.stop(audio.currentTime + at + 0.12);
    }
  } catch { /* inget ljud */ }
  navigator.vibrate?.(kind === "owned" ? [60, 60, 60] : kind === "new" ? 250 : 80);
}

// ---------- Tema och visning ----------

function applyTheme() {
  if (state.theme === "auto") delete document.documentElement.dataset.theme;
  else document.documentElement.dataset.theme = state.theme;
  const dark = state.theme === "dark" || (state.theme === "auto" && matchMedia("(prefers-color-scheme: dark)").matches);
  $('meta[name="theme-color"]').content = dark ? "#0b0d12" : "#f5f3ee";
}
matchMedia("(prefers-color-scheme: dark)").addEventListener?.("change", applyTheme);

const ICON_AUTO = `<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8.5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M12 3.5a8.5 8.5 0 0 1 0 17z" fill="currentColor"/></svg>`;
const ICON_SUN = `<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="4.5" fill="currentColor"/><g stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M4.9 19.1l1.8-1.8M17.3 6.7l1.8-1.8"/></g></svg>`;
const ICON_MOON = `<svg viewBox="0 0 24 24"><path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5z" fill="currentColor"/></svg>`;

function viewDisplay() {
  const opt = (key, val, label, icon) => `<button class="seg ${state[key] === val ? "on" : ""}" data-k="${key}" data-v="${val}">
    <span class="seg-icon">${icon}</span>${label}</button>`;
  const g = (n) => `<span class="mini-g g${n}">${"<i></i>".repeat(n * 2)}</span>`;
  openSheet(`
    <h2>Visning</h2>
    <div class="segs">
      ${opt("view", "grid-s", "Små", g(4))}${opt("view", "grid-m", "Mellan", g(3))}${opt("view", "grid-l", "Stora", g(2))}
      ${opt("view", "list", "Lista", `<span class="mini-l"><i></i><i></i><i></i></span>`)}
      ${opt("view", "compact", "Kompakt", `<span class="mini-c"><i></i><i></i><i></i><i></i></span>`)}
    </div>
    <h3>Tema</h3>
    <div class="segs three">
      ${opt("theme", "auto", "Auto", ICON_AUTO)}${opt("theme", "light", "Ljust", ICON_SUN)}${opt("theme", "dark", "Mörkt", ICON_MOON)}
    </div>
    <p class="muted small">Auto följer inställningen i mobilen eller datorn. Valen sparas på den här enheten.</p>`);
  $$(".seg").forEach((b) => (b.onclick = () => {
    state[b.dataset.k] = b.dataset.v;
    store.set(b.dataset.k, b.dataset.v);
    if (b.dataset.k === "theme") applyTheme(); else render();
    viewDisplay();
  }));
}

// ---------- Samlingar ----------

async function loadLibs() {
  state.libs = await api("/api/libraries");
  if (state.lib !== "all" && !state.libs.some((l) => l.id === state.lib)) state.lib = state.libs[0]?.id;
  store.set("lib", state.lib);
  $("#lib-name").textContent = state.lib === "all" ? "Alla samlingar" : libName(state.lib);
}

async function switchLib(lib) {
  state.lib = lib;
  state.facets = null;
  store.set("lib", lib);
  await loadLibs();
  closeSheet();
  load();
}

async function viewLibPicker() {
  await loadLibs();
  const row = (id, name, sub, on) => `<div class="menu-item ${on ? "on" : ""}" data-lib="${id}"><span class="mi">${on ? "●" : "○"}</span>
    <div class="grow">${esc(name)}<div class="muted small">${sub}</div></div></div>`;
  const total = state.libs.reduce((a, l) => a + l.owned, 0);
  openSheet(`<h2>Samlingar</h2>
    ${state.libs.map((l) => row(l.id, l.name, `${l.owned} titlar${l.wish ? ` · ${l.wish} önskade` : ""}`, state.lib === l.id)).join("")}
    ${state.libs.length > 1 ? row("all", "Alla samlingar", `${total} titlar · sök och bläddra i allt`, state.lib === "all") : ""}
    <button class="btn" id="lib-manage">Hantera samlingar</button>`);
  $$("[data-lib]").forEach((el) => (el.onclick = () => switchLib(el.dataset.lib === "all" ? "all" : +el.dataset.lib)));
  $("#lib-manage").onclick = () => show(viewLibManage);
}

async function viewLibManage() {
  await loadLibs();
  openSheet(`<h2>Hantera samlingar</h2>
    ${state.libs.map((l) => `<div class="list-item"><div class="grow">${esc(l.name)}<div class="muted small">${l.owned} titlar${l.wish ? ` · ${l.wish} önskade` : ""}</div></div>
      <button class="btn small" data-rename="${l.id}">Byt namn</button>
      ${state.libs.length > 1 ? `<button class="btn small danger" data-del="${l.id}">Ta bort</button>` : ""}</div>`).join("")}
    <h3>Ny samling</h3>
    <div class="row"><input id="lib-new" type="text" placeholder="T.ex. Barnens filmer"><button class="btn primary" id="lib-add">Skapa</button></div>
    <p class="muted small">Importera en CLZ-export till en samling via Meny → Importera.</p>`);
  $("#lib-add").onclick = async () => {
    const name = $("#lib-new").value.trim();
    if (!name) return;
    const r = await api("/api/libraries", { method: "POST", json: { name } });
    toast(`Samlingen ”${esc(name)}” skapad`, "ok");
    await switchLib(r.id);
  };
  $$("[data-rename]").forEach((b) => (b.onclick = async () => {
    const lib = state.libs.find((l) => l.id === +b.dataset.rename);
    const name = prompt("Nytt namn:", lib.name);
    if (!name || !name.trim()) return;
    await api(`/api/libraries/${lib.id}`, { method: "PATCH", json: { name } });
    await loadLibs(); refresh();
  }));
  $$("[data-del]").forEach((b) => (b.onclick = () => show(viewLibDelete, +b.dataset.del)));
}

function viewLibDelete(id) {
  const lib = state.libs.find((l) => l.id === id);
  openSheet(`<h2>Ta bort samling</h2>
    <div class="notice bad">Samlingen <b>${esc(lib.name)}</b> och alla dess <b>${lib.owned + lib.wish} titlar</b> tas bort.
    En säkerhetskopia av hela databasen sparas automatiskt precis innan, så det går att ångra.</div>
    <label class="form-label">Skriv <b>${esc(lib.name)}</b> för att bekräfta</label>
    <input id="del-confirm" type="text" autocomplete="off" autocapitalize="off" spellcheck="false">
    <button class="btn danger-fill" id="del-go" disabled>Ta bort för gott</button>
    <button class="btn" id="del-cancel">Avbryt</button>`);
  $("#del-confirm").focus();
  $("#del-confirm").oninput = (e) => ($("#del-go").disabled = e.target.value.trim() !== lib.name);
  $("#del-cancel").onclick = back;
  $("#del-go").onclick = async () => {
    if (!confirm(`Sista chansen: ta bort ”${lib.name}”?`)) return;
    const r = await api(`/api/libraries/${id}`, { method: "DELETE", json: { confirm: $("#del-confirm").value } });
    toast("Borttagen – en säkerhetskopia sparades först", "ok");
    if (state.lib === id) state.lib = r.libraries[0].id;
    await loadLibs();
    stack.pop(); refresh(); load();
  };
}

// ---------- Rutnätet ----------

// Varje flik har egna filter, eftersom musik har andra format och genrer än film
const tabKind = () => ({ all: "video", movie: "movie", tv: "tv", music: "music" }[state.tab] || "");
const musicTab = () => state.tab === "music";

function query() {
  const music = musicTab();
  const p = { q: state.q, field: music && state.field !== "title" ? "all" : state.field,
    sort: !music && state.sort === "artist" ? "title" : state.sort, format: state.format, genre: state.genre,
    watched: music ? "" : state.watched, digital: music ? "" : state.digital };
  p.status = state.tab === "wish" ? "wish" : state.loaned ? "loaned" : "owned";
  if (tabKind()) p.kind = tabKind();
  p.lib = state.lib === "all" ? "all" : state.lib;
  return new URLSearchParams(p);
}

async function load() {
  state.items = await api(`/api/items?${query()}`);
  render();
}

function buildCards() {
  const cards = [], series = {};
  for (const it of state.items) {
    if (it.kind === "tv" && it.series_name && state.tab !== "wish") {
      const key = it.series_name + (state.lib === "all" ? "#" + it.library_id : "");
      if (!series[key]) {
        series[key] = { group: true, name: it.series_name, library_id: it.library_id, seasons: [] };
        cards.push(series[key]);
      }
      series[key].seasons.push(it);
    } else cards.push(it);
  }
  return cards;
}

function render() {
  const cards = buildCards();
  const grid = $("#grid");
  grid.className = state.view + (musicTab() ? " music-grid" : "");
  const list = state.view === "list" || state.view === "compact";
  grid.innerHTML = cards.map((c, i) => (list ? rowHtml(c, i) : cardHtml(c, i))).join("");
  $$("#grid [data-i]").forEach((el) => {
    const c = cards[el.dataset.i];
    el.onclick = () => (c.group ? show(viewSeries, c) : show(viewItem, c.id));
  });
  const n = state.items.length;
  const word = musicTab() ? (n === 1 ? "album" : "album") : n === 1 ? "titel" : "titlar";
  $("#count").textContent = `${n} ${word}${cards.length !== n ? ` · ${cards.length} kort` : ""}`;
  const empty = $("#empty");
  empty.hidden = n > 0;
  empty.textContent = state.tab === "wish"
    ? "Önskelistan är tom. Skanna eller sök en titel och välj ”Önskelista”."
    : activeFilterCount() || state.q ? "Inget matchade. Prova att ändra filtren."
    : musicTab() ? "Ingen musik än. Öppna menyn och importera en export från CLZ Music, eller skanna din första skiva."
    : "Samlingen är tom. Öppna menyn och importera en CLZ-export, eller skanna din första film.";
  renderShelf();
  renderActiveFilters();
}

// "Nyligen tillagt" överst, som en hylla i en streamingtjänst. Bara när man bläddrar fritt.
function renderShelf() {
  const shelf = $("#shelf");
  const browsing = !state.q && !activeFilterCount() && state.tab !== "wish" && state.sort === "title" && state.items.length > 12;
  if (!browsing) { shelf.hidden = true; return; }
  const seen = new Set();
  const recent = [...state.items].filter((i) => i.added_date)
    .sort((a, b) => b.added_date.localeCompare(a.added_date) || b.id - a.id)
    .filter((i) => { const k = i.series_name || i.id; if (seen.has(k)) return false; seen.add(k); return true; })
    .slice(0, 14);
  if (recent.length < 4) { shelf.hidden = true; return; }
  shelf.hidden = false;
  shelf.innerHTML = `<div class="shelf-head"><h2>Nyligen tillagt</h2><span class="muted small">${recent[0].added_date}</span></div>
    <div class="shelf-row">${recent.map((c) => cardHtml(c, "")).join("")}</div>`;
  $$(".shelf-row .card", shelf).forEach((el, i) => (el.onclick = () => show(viewItem, recent[i].id)));
}

function seasonFormats(seasons) {
  const f = [...new Set(seasons.map((s) => formatInfo(s.format)?.label).filter(Boolean))];
  return f.length === 1 ? seasons.find((s) => s.format).format : "";
}

function cardHtml(c, i) {
  if (c.group) {
    const first = c.seasons.find((s) => s.poster_path) || c.seasons[0];
    const n = c.seasons.length;
    return `<div class="card" data-i="${i}"><div class="pw">${poster(first.poster_path, c.name)}
      <span class="badge tr">${n} ${n === 1 ? "säsong" : "säsonger"}</span>
      ${c.seasons.some((s) => s.digital) ? `<span class="badge tl dig">▶</span>` : ""}
      <span class="fmt-wrap">${fmtBadge(seasonFormats(c.seasons))}</span></div>
      <div class="t">${esc(c.name)}</div></div>`;
  }
  const di = i === "" ? "" : `data-i="${i}"`;
  if (isMusic(c)) {
    return `<div class="card music" ${di}><div class="pw">${poster(c.poster_path, c.title, "square")}
      ${c.loaned_to ? `<span class="badge tr warn">Utlånad</span>` : ""}
      <span class="fmt-wrap">${fmtBadge(c.format)}</span></div>
      <div class="t">${esc(c.title)}</div><div class="s">${esc(artistName(c.artist))}${c.year ? ` · ${c.year}` : ""}</div></div>`;
  }
  return `<div class="card" ${di}><div class="pw ${c.watched ? "seen" : ""}">${poster(c.poster_path, c.title)}
    ${c.loaned_to ? `<span class="badge tr warn">Utlånad</span>` : ""}
    ${c.digital ? `<span class="badge tl dig">▶</span>` : ""}
    <span class="fmt-wrap">${fmtBadge(c.format)}</span></div>
    <div class="t">${esc(c.title)}</div><div class="s">${c.year || ""}</div></div>`;
}

function rowHtml(c, i) {
  const compact = state.view === "compact";
  const title = c.group ? c.name : c.title;
  const sub = c.group
    ? `${c.seasons.length} ${c.seasons.length === 1 ? "säsong" : "säsonger"}`
    : [isMusic(c) && artistName(c.artist), c.year, c.location].filter(Boolean).map(esc).join(" · ");
  const fmt = fmtBadge(c.group ? seasonFormats(c.seasons) : c.format, "sm");
  const flags = [c.loaned_to && `<span class="flag warn">Utlånad</span>`, c.watched && `<span class="flag ok">✓</span>`,
    (c.digital || c.seasons?.some((s) => s.digital)) && `<span class="flag dig">▶</span>`].filter(Boolean).join("");
  const lib = state.lib === "all" ? `<span class="lib-tag">${esc(libName(c.library_id))}</span>` : "";
  if (compact) {
    return `<div class="row-c" data-i="${i}"><span class="grow ellip">${isMusic(c) ? `<span class="muted">${esc(artistName(c.artist))} – </span>` : ""}${esc(title)}</span>
      <span class="muted small">${c.group ? sub : c.year || ""}</span>${flags}${fmt}</div>`;
  }
  const p = c.group ? (c.seasons.find((s) => s.poster_path) || c.seasons[0]).poster_path : c.poster_path;
  return `<div class="row-l" data-i="${i}">${poster(p, "", isMusic(c) ? "thumb square" : "thumb")}
    <div class="grow"><div class="li-title">${esc(title)}</div><div class="muted small">${sub} ${lib}</div>
    <div class="row-flags">${fmt}${flags}</div></div></div>`;
}

const filterKeys = () => (musicTab() ? ["format", "genre"] : ["format", "genre", "watched", "digital"]);
function activeFilterCount() {
  return filterKeys().filter((k) => state[k]).length + (state.loaned ? 1 : 0);
}

function renderActiveFilters() {
  const labels = [];
  if (state.format) labels.push(["format", state.format]);
  if (state.genre) labels.push(["genre", state.genre]);
  if (state.watched && !musicTab()) labels.push(["watched", state.watched === "1" ? "Sedda" : "Osedda"]);
  if (state.digital && !musicTab()) labels.push(["digital", state.digital === "yes" ? "Finns digitalt" : "Bara fysiskt"]);
  if (state.loaned) labels.push(["loaned", "Utlånade"]);
  $("#active-filters").innerHTML = labels.map(([k, v]) => `<button class="chip" data-k="${k}">${esc(v)} ✕</button>`).join("");
  $$("#active-filters .chip").forEach((b) => (b.onclick = () => {
    state[b.dataset.k] = b.dataset.k === "loaned" ? false : "";
    saveFilters(); load();
  }));
  const n = activeFilterCount();
  $("#btn-filter").textContent = n ? `Filter (${n})` : "Filter";
  $("#btn-filter").classList.toggle("on", n > 0 || state.sort !== "title");
  $("#q").placeholder = musicTab() ? "Sök album eller artist…" : FIELD_HINT[state.field];
  $("#q-field").hidden = musicTab();
}

function saveFilters() {
  const { sort, format, genre, watched, digital, loaned } = state;
  store.set("filters", { sort, format, genre, watched, digital, loaned });
}

async function facets(fresh = false, kind = musicTab() ? "music" : "video") {
  state.facets = state.facets || {};
  if (!state.facets[kind] || fresh) state.facets[kind] = await api(`/api/facets?${libParam()}&kind=${kind}`);
  return state.facets[kind];
}

// ---------- Bottenarket med bakåtknapp ----------

let stack = [];
function show(view, ...args) {
  stack.push([view, args]);
  return view(...args);
}
function refresh() {
  const top = stack.at(-1);
  if (top) top[0](...top[1]);
}
function back() {
  stopScan();
  stack.pop();
  if (stack.length) refresh(); else closeSheet();
}
function openSheet(html) {
  $("#sheet-body").innerHTML = html;
  $("#sheet").hidden = $("#sheet-bg").hidden = false;
  $("#sheet-back").hidden = stack.length < 2;
  $("#sheet").classList.toggle("has-back", stack.length > 1);
  $("#sheet").scrollTop = 0;
  document.body.classList.add("sheet-open");
}
function closeSheet() {
  stopScan();
  stack = [];
  addedThisRound = 0;
  $("#sheet").hidden = $("#sheet-bg").hidden = true;
  document.body.classList.remove("sheet-open");
}
$("#sheet-close").onclick = closeSheet;
$("#sheet-bg").onclick = closeSheet;
$("#sheet-back").onclick = back;
document.addEventListener("keydown", (e) => e.key === "Escape" && !$("#sheet").hidden && back());

const option = (value, label, cur) => `<option value="${esc(value)}" ${String(cur) === String(value) ? "selected" : ""}>${esc(label)}</option>`;
const libOptions = (cur) => state.libs.map((l) => option(l.id, l.name, cur)).join("");

// ---------- Filter & sortering ----------

async function viewFilter() {
  const f = await facets();
  const music = musicTab();
  const sel = (id, label, opts, cur) => `<label>${label}<select id="${id}">${opts.map(([v, l]) => option(v, l, cur)).join("")}</select></label>`;
  const sorts = music
    ? [["title", "Titel A–Ö"], ["artist", "Artist A–Ö"], ["added", "Senast tillagd"], ["year", "År (nyast först)"],
      ["year_asc", "År (äldst först)"], ["rating", "Mitt betyg"], ["price", "Inköpspris"]]
    : [["title", "Titel A–Ö"], ["added", "Senast tillagd"], ["year", "År (nyast först)"],
      ["year_asc", "År (äldst först)"], ["rating", "Mitt betyg"], ["imdb", "IMDb-betyg"], ["runtime", "Längd (kortast först)"],
      ["price", "Inköpspris"]];
  openSheet(`
    <h2>Filter och sortering</h2>
    <p class="muted small">${music ? "Gäller fliken Musik" : "Gäller filmer och serier"}</p>
    <div class="form">
      ${sel("f-sort", "Sortera", sorts, state.sort)}
      ${sel("f-format", "Format", [["", "Alla format"], ...f.formats.map((x) => [x, x])], state.format)}
      ${sel("f-genre", "Genre", [["", "Alla genrer"], ...f.genres.map((x) => [x, x])], state.genre)}
      ${music ? "" : sel("f-watched", "Sedd", [["", "Alla"], ["0", "Osedda"], ["1", "Sedda"]], state.watched)}
      ${f.digital && !music ? sel("f-digital", "Plex/Jellyfin", [["", "Alla"], ["yes", "Finns digitalt"], ["no", "Bara fysiskt"]], state.digital) : ""}
      <label class="check"><input type="checkbox" id="f-loaned" ${state.loaned ? "checked" : ""}> Visa bara utlånade</label>
    </div>
    <button class="btn primary" id="f-apply">Visa</button>
    <button class="btn" id="f-reset">Nollställ</button>`);
  $("#f-apply").onclick = () => {
    state.sort = $("#f-sort").value; state.format = $("#f-format").value; state.genre = $("#f-genre").value;
    if (!music) { state.watched = $("#f-watched").value; state.digital = $("#f-digital")?.value || ""; }
    state.loaned = $("#f-loaned").checked;
    saveFilters(); closeSheet(); load();
  };
  $("#f-reset").onclick = () => { Object.assign(state, DEFAULT_FILTERS); saveFilters(); closeSheet(); load(); };
}

// ---------- Detaljvy ----------

function viewSeries(group) {
  const seasons = state.items.filter((i) => i.series_name === group.name && (state.lib !== "all" || i.library_id === group.library_id));
  openSheet(`<h2>${esc(group.name)}</h2>` + seasons.map((s) => `
    <div class="list-item" data-id="${s.id}">${poster(s.poster_path, "", "thumb")}
      <div class="grow"><div class="li-title">${s.season ? `Säsong ${s.season}` : esc(s.title)}</div>
      <div class="muted small li-sub">${s.year || ""} ${fmtBadge(s.format, "sm")} ${s.loaned_to ? `· utlånad till ${esc(s.loaned_to)}` : ""}</div></div>
      ${s.watched ? `<span class="ok-text">✓</span>` : ""}</div>`).join(""));
  bindOpen();
}

// Omslagets färg blir detaljvyns tonfärg (fungerar eftersom omslagen kommer från samma server)
function tintFromPoster() {
  const img = $("#sheet .detail > img.poster");
  const hero = $("#sheet .hero");
  if (!img || !hero) return;
  const apply = () => {
    try {
      const c = document.createElement("canvas");
      c.width = c.height = 12;
      const g = c.getContext("2d");
      g.drawImage(img, 0, 0, 12, 12);
      const d = g.getImageData(0, 0, 12, 12).data;
      let r = 0, gg = 0, b = 0, n = 0;
      for (let i = 0; i < d.length; i += 4) {
        const max = Math.max(d[i], d[i + 1], d[i + 2]), min = Math.min(d[i], d[i + 1], d[i + 2]);
        const w = 1 + (max - min) / 40; // mättade färger väger tyngre än grått
        r += d[i] * w; gg += d[i + 1] * w; b += d[i + 2] * w; n += w;
      }
      hero.style.setProperty("--tint", `rgb(${(r / n) | 0}, ${(gg / n) | 0}, ${(b / n) | 0})`);
    } catch { /* bilden gick inte att läsa – behåll standardfärgen */ }
  };
  if (img.complete && img.naturalWidth) apply(); else img.addEventListener("load", apply, { once: true });
}

function heroHtml(it, subtitle) {
  return `<div class="hero">${it.poster_path ? `<div class="hero-bg" style="background-image:url('/poster${esc(it.poster_path)}')"></div>` : ""}
    <h2>${esc(it.title)}</h2>${subtitle ? `<div class="sub">${subtitle}</div>` : ""}
    <div class="detail">${poster(it.poster_path, it.title, isMusic(it) ? "square" : "")}<div class="facts" id="facts"></div></div></div>`;
}

function loanNotice(it) {
  const overdue = it.loaned_to && it.due_date && it.due_date < today();
  return (isWish(it) ? `<div class="notice star">★ På önskelistan</div>` : "") +
    (it.loaned_to ? `<div class="notice ${overdue ? "bad" : "warn"}">Utlånad till <b>${esc(it.loaned_to)}</b>
      ${it.loan_date ? ` sedan ${esc(it.loan_date)}` : ""}${it.due_date ? ` · åter ${esc(it.due_date)}${overdue ? " (försenad!)" : ""}` : ""}</div>` : "");
}

async function viewItem(id) {
  const it = await api(`/api/items/${id}`);
  if (isMusic(it)) return viewAlbum(it);
  const x = it.extra || {};
  const wish = isWish(it);
  const fact = (label, v) => (v ? `<div><b>${label}:</b> ${esc(v)}</div>` : "");
  const sub = [it.year, it.runtime && lenText(it.runtime), it.kind === "tv" ? "Serie" : null, pipe(it.genres)].filter(Boolean).map(esc).join(" · ");
  openSheet(`
    ${heroHtml(it, sub)}
    ${loanNotice(it)}`);
  $("#facts").innerHTML = `
        ${it.format ? `<div class="fmt-line">${fmtBadge(it.format)}</div>` : ""}
        ${fact("År", it.year)}${fact("Utgåva", it.edition)}
        ${fact("Längd", it.runtime && `${it.runtime} min`)}${fact("Genre", pipe(it.genres))}
        ${fact(it.kind === "tv" ? "Regi/skapare" : "Regi", pipe(it.director))}
        ${fact("IMDb", it.imdb_rating)}${fact("Mitt betyg", it.my_rating)}${fact("Plats", it.location)}
        ${fact("Skivor", it.nr_discs)}${fact("Streckkod", it.barcode)}${fact("Undertext", pipe(x["Subtitles"]))}
        ${fact("Inköpt", [it.purchase_price && `${it.purchase_price} kr`, x["Purchase Date"]].filter(Boolean).join(", "))}
        ${state.libs.length > 1 ? fact("Samling", it.library_name) : ""}
        ${it.digital_sources?.length ? `<div><b>Digitalt:</b> ${it.digital_sources.map((s) => s === "plex" ? "Plex" : "Jellyfin").join(", ")} ▶</div>` : ""}
        ${it.collection_name ? `<div><b>Filmserie:</b> <a href="#" id="b-coll">${esc(it.collection_name)}</a></div>` : ""}`;
  $("#sheet-body").insertAdjacentHTML("beforeend", `
    ${it.actors ? `<h3>Skådespelare</h3><div class="plot">${esc(pipe(it.actors))}</div>` : ""}
    ${it.plot ? `<h3>Handling</h3><div class="plot">${esc(it.plot)}</div>` : ""}
    ${it.notes ? `<h3>Anteckningar</h3><div class="plot">${esc(it.notes)}</div>` : ""}
    <div class="actions">
      ${wish ? `<button class="btn primary" id="b-bought">Köpt! Flytta till samlingen</button>` : `
      <button class="btn ${it.watched ? "primary" : ""}" id="b-watched">${it.watched ? "✓ Sedd" : "Markera som sedd"}</button>
      ${it.loaned_to ? `<button class="btn primary" id="b-return">Återlämnad</button>` : `<button class="btn" id="b-loan">Låna ut</button>`}`}
      <button class="btn" id="b-edit">Redigera</button>
      <button class="btn" id="b-refresh">Uppdatera metadata</button>
      <button class="btn" id="b-poster">Byt omslag</button>
      <button class="btn" id="b-own">Eget omslag</button>
      <button class="btn" id="b-rematch">Fel film?</button>
      ${it.imdb_id ? `<a class="btn" href="https://www.imdb.com/title/${esc(it.imdb_id)}/" target="_blank" rel="noopener">IMDb</a>` : ""}
      <button class="btn danger" id="b-del">Ta bort</button>
    </div>
    ${it.locked?.length ? `<p class="muted small">Ändrat av dig (skrivs inte över): ${it.locked.map(fieldName).join(", ")}</p>` : ""}`);
  tintFromPoster();
  const done = async (msg) => { if (msg) toast(msg); refresh(); load(); };
  $("#b-watched") && ($("#b-watched").onclick = async () => { await patch(id, { watched: it.watched ? 0 : 1 }); done(); });
  $("#b-bought") && ($("#b-bought").onclick = async () => {
    await patch(id, { collection_status: "In Collection", added_date: today() }); done("Flyttad till samlingen");
  });
  $("#b-return") && ($("#b-return").onclick = async () => {
    await patch(id, { loaned_to: null, loan_date: null, due_date: null }); done("Markerad som återlämnad");
  });
  $("#b-loan") && ($("#b-loan").onclick = () => show(viewLoan, it));
  $("#b-edit").onclick = () => show(viewEdit, it);
  $("#b-refresh").onclick = () => show(viewRefreshItem, it);
  $("#b-poster").onclick = () => show(viewPosters, it);
  $("#b-own").onclick = () => show(viewOwnCover, it);
  $("#b-rematch").onclick = () => show(viewRematch, it);
  $("#b-coll") && ($("#b-coll").onclick = (e) => { e.preventDefault(); show(viewCollection, it.collection_id); });
  $("#b-del").onclick = async () => {
    if (!confirm(`Ta bort "${it.title}"?`)) return;
    await api(`/api/items/${id}`, { method: "DELETE" });
    back(); load(); toast("Borttagen");
  };
}

// ---------- Musik: album ----------

function tracklistHtml(list, albumArtist = "") {
  if (!list?.length) return "";
  const same = (a) => (a || "").toLowerCase() === (albumArtist || "").toLowerCase(); // artist per spår bara på samlingsskivor
  const discs = new Set(list.map((t) => t.disc || 1));
  let out = "", disc = null;
  for (const t of list) {
    if (discs.size > 1 && t.disc !== disc) { disc = t.disc; out += `${out ? "</ol>" : ""}<div class="disc-head">Skiva ${disc}</div><ol class="tracklist">`; }
    else if (!out) out = `<ol class="tracklist">`;
    out += `<li><span class="n">${esc(t.pos || "")}</span><span class="grow">${esc(t.title)}${t.artist && !same(t.artist) ? `<div class="ta">${esc(t.artist)}</div>` : ""}</span>
      <span class="len">${esc(t.length || "")}</span></li>`;
  }
  return `<h3>Låtlista</h3>${out}</ol>`;
}

function viewAlbum(it) {
  const fact = (label, v) => (v ? `<div><b>${label}:</b> ${esc(v)}</div>` : "");
  const sub = `<b>${esc(artistName(it.artist) || "Okänd artist")}</b>${it.year ? ` · ${it.year}` : ""}`;
  openSheet(`${heroHtml(it, sub)}${loanNotice(it)}`);
  $("#facts").innerHTML = `
    ${it.format ? `<div class="fmt-line">${fmtBadge(it.format)}</div>` : ""}
    ${fact("Skivbolag", it.label)}${fact("Katalognr", it.cat_no)}
    ${fact("Skivor", it.nr_discs > 1 ? it.nr_discs : null)}${fact("Spår", it.tracks)}
    ${fact("Speltid", it.runtime && lenText(it.runtime))}${fact("Genre", pipe(it.genres))}
    ${fact("Mitt betyg", it.my_rating)}${fact("Plats", it.location)}${fact("Streckkod", it.barcode)}
    ${fact("Inköpt", it.purchase_price && `${it.purchase_price} kr`)}
    ${state.libs.length > 1 ? fact("Samling", it.library_name) : ""}`;
  const wish = isWish(it);
  $("#sheet-body").insertAdjacentHTML("beforeend", `
    ${tracklistHtml(it.tracklist, it.artist)}
    ${!it.tracklist?.length && it.enriched === 0 ? `<p class="muted small">Låtlistan hämtas i bakgrunden…</p>` : ""}
    ${it.notes ? `<h3>Anteckningar</h3><div class="plot">${esc(it.notes)}</div>` : ""}
    <div class="actions">
      ${wish ? `<button class="btn primary" id="b-bought">Köpt! Flytta till samlingen</button>`
        : it.loaned_to ? `<button class="btn primary" id="b-return">Återlämnad</button>` : `<button class="btn" id="b-loan">Låna ut</button>`}
      <button class="btn" id="b-edit">Redigera</button>
      <button class="btn" id="b-refresh">Hämta info igen</button>
      <button class="btn" id="b-own">Eget omslag</button>
      <button class="btn" id="b-rematch">Fel album?</button>
      ${it.mbid ? `<a class="btn" href="https://musicbrainz.org/release/${esc(it.mbid)}" target="_blank" rel="noopener">MusicBrainz</a>` : ""}
      ${it.discogs_id ? `<a class="btn" href="https://www.discogs.com/release/${esc(it.discogs_id)}" target="_blank" rel="noopener">Discogs</a>` : ""}
      <button class="btn danger" id="b-del">Ta bort</button>
    </div>
    ${it.locked?.length ? `<p class="muted small">Ändrat av dig (skrivs inte över): ${it.locked.map(fieldName).join(", ")}</p>` : ""}`);
  tintFromPoster();
  const done = (msg) => { if (msg) toast(msg); refresh(); load(); };
  $("#b-bought") && ($("#b-bought").onclick = async () => {
    await patch(it.id, { collection_status: "In Collection", added_date: today() }); done("Flyttad till samlingen");
  });
  $("#b-return") && ($("#b-return").onclick = async () => {
    await patch(it.id, { loaned_to: null, loan_date: null, due_date: null }); done("Markerad som återlämnad");
  });
  $("#b-loan") && ($("#b-loan").onclick = () => show(viewLoan, it));
  $("#b-edit").onclick = () => show(viewAlbumEdit, it);
  $("#b-own").onclick = () => show(viewOwnCover, it);
  $("#b-rematch").onclick = () => show(viewMusicRematch, it);
  $("#b-refresh").onclick = async (e) => {
    e.target.disabled = true; e.target.textContent = "Hämtar…";
    try {
      await api(`/api/items/${it.id}/refresh`, { method: "POST", json: {} });
      done("Info hämtad");
    } catch (err) { toast(esc(err.message), "bad"); e.target.disabled = false; e.target.textContent = "Hämta info igen"; }
  };
  $("#b-del").onclick = async () => {
    if (!confirm(`Ta bort "${it.title}"?`)) return;
    await api(`/api/items/${it.id}`, { method: "DELETE" });
    back(); load(); toast("Borttagen");
  };
}

async function viewAlbumEdit(it) {
  const f = await facets(false, "music");
  const field = (k, label, type = "text", extra = "") =>
    `<label>${label}<input data-f="${k}" type="${type}" value="${esc(it[k] ?? "")}" ${extra}></label>`;
  openSheet(`
    <h2>Redigera album</h2>
    <div class="form">
      ${field("title", "Titel")}
      ${field("artist", "Artist", "text", 'placeholder="Various = samlingsskiva"')}
      <div class="two">${field("year", "År", "number")}${field("format", "Format", "text", 'list="e-formats"')}</div>
      <datalist id="e-formats">${[...new Set([...MUSIC_FORMATS, ...f.formats])].map((x) => `<option value="${esc(x)}">`).join("")}</datalist>
      <div class="two">${field("label", "Skivbolag")}${field("cat_no", "Katalognummer")}</div>
      <div class="two">${field("nr_discs", "Antal skivor", "number")}${field("tracks", "Antal spår", "number")}</div>
      ${field("genres", "Genre (flera med | emellan)")}
      <div class="two">${field("barcode", "Streckkod", "text", 'inputmode="numeric"')}${field("location", "Plats", "text", 'list="e-locs"')}</div>
      <datalist id="e-locs">${f.locations.map((x) => `<option value="${esc(x)}">`).join("")}</datalist>
      <div class="two">${field("my_rating", "Mitt betyg (0–10)", "number", 'step="0.5" min="0" max="10"')}${field("purchase_price", "Inköpspris (kr)", "number", 'step="0.01"')}</div>
      <div class="two">
        <label>Status<select data-f="collection_status">
          ${option("In Collection", "I samlingen", it.collection_status || "In Collection")}
          ${option("On Wish List", "Önskelista", it.collection_status)}
          ${option("Sold", "Såld", it.collection_status)}</select></label>
        ${state.libs.length > 1 ? `<label>Samling<select data-f="library_id">${libOptions(it.library_id)}</select></label>` : ""}
      </div>
      <label>Anteckningar<textarea data-f="notes" rows="3">${esc(it.notes || "")}</textarea></label>
    </div>
    <button class="btn primary" id="e-save">Spara</button>`);
  $("#e-save").onclick = () => saveEdits(it);
}

async function saveEdits(it) {
  const changes = {};
  for (const el of $$("[data-f]", $("#sheet-body"))) {
    const before = String(it[el.dataset.f] ?? "");
    if (el.value !== before) changes[el.dataset.f] = el.value; // skicka bara det som ändrats
  }
  if (Object.keys(changes).length) await patch(it.id, changes);
  state.facets = null;
  toast("Sparat");
  if (changes.library_id) await loadLibs();
  back(); load();
}

function musicCandidate(c, i) {
  return `<div class="list-item" data-i="${i}">${netCover(c.cover, "thumb square")}
    <div class="grow"><div class="li-title">${esc(c.title)}</div>
    <div class="muted small">${esc(artistName(c.artist))}${c.year ? ` · ${c.year}` : ""}${c.format ? ` · ${esc(c.format)}${c.nr_discs > 1 ? ` ×${c.nr_discs}` : ""}` : ""}${c.country ? ` · ${esc(c.country)}` : ""}</div>
    <div class="muted small">${[c.label, c.cat_no].filter(Boolean).map(esc).join(" · ")} <span class="lib-tag">${esc(c.source)}</span></div></div>
    <span class="plus">＋</span></div>`;
}

function viewMusicRematch(it) {
  openSheet(`
    <h2>Välj rätt album</h2>
    <p class="muted">${esc(artistName(it.artist))} – ${esc(it.title)}${it.year ? ` (${it.year})` : ""}</p>
    <div class="form"><div class="two">
      <label>Artist<input id="mr-artist" type="text" value="${esc(VARIOUS.includes((it.artist || "").toLowerCase()) ? "" : it.artist || "")}"></label>
      <label>Album<input id="mr-title" type="text" value="${esc(it.title)}"></label></div></div>
    <button class="btn primary" id="mr-go">Sök</button>
    <div id="results"></div>`);
  const run = async () => {
    $("#results").innerHTML = `<p class="muted">Söker…</p>`;
    try {
      const p = new URLSearchParams({ q: $("#mr-title").value, artist: $("#mr-artist").value });
      const list = await api(`/api/music/search?${p}`);
      $("#results").innerHTML = list.length ? list.map(musicCandidate).join("") : `<p class="muted">Inga träffar.</p>`;
      $$("#results .list-item").forEach((el) => (el.onclick = async () => {
        const c = list[el.dataset.i];
        el.style.opacity = 0.5;
        try {
          await api(`/api/items/${it.id}/rematch`, { method: "POST", json: { source: c.source, id: c.mbid || c.discogs_id } });
          toast("Kopplad till rätt album", "ok");
          back(); load();
        } catch (e) { el.style.opacity = 1; toast(esc(e.message), "bad"); }
      }));
    } catch (e) { $("#results").innerHTML = `<div class="notice bad">${esc(e.message)}</div>`; }
  };
  $("#mr-go").onclick = run;
  $("#mr-title").onkeydown = (e) => e.key === "Enter" && run();
  run();
}

async function viewMusicCode(code) {
  openSheet(`<h2>Streckkod ${esc(code)}</h2><p class="muted">Letar i dina samlingar, MusicBrainz och fler källor…</p>`);
  let r;
  try { r = await api(`/api/music/barcode/${code}?lib=${scanLib()}`); }
  catch (e) { return openSheet(`<h2>Streckkod ${esc(code)}</h2><div class="notice bad">Kunde inte slå upp streckkoden: ${esc(e.message)}</div>`); }
  if (r.existing.length) return showExisting(code, r.existing);
  viewMusicAdd({ barcode: code, candidates: r.candidates, match: r.match, productTitle: r.product_title, tried: r.tried });
}

// Lägg till musik: bästa träff från streckkoden, eller sök på artist/album
async function viewMusicAdd({ query = "", artist = "", barcode = null, candidates = null, productTitle = null, match = null, tried = [] }) {
  const f = await facets(false, "music");
  const last = store.get("lastMusicAdd", { format: "CD", location: "" });
  const keep = store.get("keepAdding", false);
  let head = "";
  if (barcode && match) {
    head = `<div class="best">${netCover(match.cover, "square")}
      <div class="grow"><div class="muted small">Streckkod ${esc(barcode)} · hittad via ${esc(match.source)}</div>
        <h3>${esc(match.title)}</h3>
        <div class="muted">${esc(artistName(match.artist))}${match.year ? ` · ${match.year}` : ""}${match.label ? ` · ${esc(match.label)}` : ""}</div>
        <button class="btn primary" id="b-best">＋ Lägg till</button></div></div>
      ${candidates?.length > 1 ? `<p class="muted small">Flera utgåvor har samma streckkod – välj en annan nedan om det behövs.</p>` : `<p class="muted small">Inte rätt skiva? Sök nedan.</p>`}`;
  } else if (barcode) {
    head = `<div class="notice">Streckkod ${esc(barcode)}${productTitle ? `<br><span class="muted">Hittade: ${esc(productTitle)}</span>`
      : `<br><span class="muted">Okänd streckkod${tried.length ? ` (letade i ${esc(tried.join(", "))})` : ""} – sök på artist och album nedan.</span>`}
      <div><a class="btn small web" href="https://www.discogs.com/search/?q=${encodeURIComponent(barcode)}&type=release" target="_blank" rel="noopener">Sök på Discogs ↗</a></div></div>`;
  }
  openSheet(`
    <h2>${barcode ? (match ? "Hittad!" : "Ny skiva") : "Lägg till musik"}</h2>
    ${addedThisRound ? `<div class="added-count">✓ ${addedThisRound} tillagda ${queue().length && barcode ? `· ${queue().length} kvar i kön` : ""}</div>` : ""}
    ${head}
    <div class="form"><div class="two">
      <label>Artist<input id="ma-artist" type="text" value="${esc(artist)}" placeholder="Valfritt"></label>
      <label>Album<input id="ma-title" type="text" value="${esc(query)}"></label></div></div>
    <button class="btn primary" id="b-ms">Sök</button>
    <div class="row">
      <select id="fmt">${[...new Set([...MUSIC_FORMATS, ...f.formats])].map((x) => option(x, x, match?.format || last.format)).join("")}</select>
      <input id="loc" type="text" list="m-locs" placeholder="Plats" value="${esc(last.location)}">
      <datalist id="m-locs">${f.locations.map((x) => `<option value="${esc(x)}">`).join("")}</datalist>
    </div>
    ${state.libs.length > 1 ? `<select id="add-lib">${libOptions(scanLib())}</select>` : ""}
    <label class="check"><input type="checkbox" id="wish"> ★ Lägg på önskelistan i stället</label>
    <label class="check"><input type="checkbox" id="keep" ${keep ? "checked" : ""}> Fortsätt lägga till fler efter den här</label>
    <div id="results"></div>
    <p class="small"><a href="#" id="b-manual-album">Finns inte? Lägg till skivan för hand ›</a></p>
    ${addedThisRound ? `<button class="btn" id="b-done">Klar</button>` : ""}`);
  $("#keep").onchange = (e) => store.set("keepAdding", e.target.checked);
  $("#b-best") && ($("#b-best").onclick = (e) => addAlbum(match, barcode, e.target.closest(".best")));
  $("#b-done") && ($("#b-done").onclick = () => { addedThisRound = 0; closeSheet(); });
  $("#b-manual-album").onclick = (e) => {
    e.preventDefault();
    show(viewMusicManual, { title: $("#ma-title").value, artist: $("#ma-artist").value, barcode, format: $("#fmt").value });
  };
  const renderList = (list) => {
    $("#results").innerHTML = list.length ? list.map(musicCandidate).join("") : `<p class="muted">Inga träffar. Prova en annan stavning.</p>`;
    $$("#results .list-item").forEach((el) => (el.onclick = () => addAlbum(list[el.dataset.i], barcode, el)));
  };
  $("#b-ms").onclick = async () => {
    if (!$("#ma-title").value.trim()) return $("#ma-title").focus();
    $("#results").innerHTML = `<p class="muted">Söker…</p>`;
    try { renderList(await api(`/api/music/search?${new URLSearchParams({ q: $("#ma-title").value, artist: $("#ma-artist").value })}`)); }
    catch (e) { $("#results").innerHTML = `<div class="notice bad">${esc(e.message)}</div>`; }
  };
  for (const id of ["#ma-title", "#ma-artist"]) $(id).onkeydown = (e) => e.key === "Enter" && $("#b-ms").onclick();
  if (candidates?.length && (!match || candidates.length > 1)) renderList(match ? candidates.slice(1) : candidates);
  else if (query && !match) $("#b-ms").onclick();
  if (!barcode && !query) $("#ma-title").focus();
}

async function addAlbum(c, barcode, el, force = false) {
  const wish = $("#wish").checked, keep = $("#keep").checked;
  const body = { source: c.source, id: c.mbid || c.discogs_id, barcode, format: $("#fmt").value, wish, force,
    location: $("#loc").value.trim() || null, library_id: +($("#add-lib")?.value || scanLib()) };
  store.set("lastMusicAdd", { format: body.format, location: body.location || "" });
  el.style.opacity = 0.5;
  try {
    const item = await api("/api/music", { method: "POST", json: body });
    if (barcode) removeFromQueue(barcode);
    state.facets = null;
    load();
    toast(`${wish ? "★ Önskad" : "✓ Tillagd"}: <b>${esc(item.title)}</b>`, "ok");
    if (!keep) { addedThisRound = 0; stack = []; return show(viewItem, item.id); }
    addedThisRound++;
    if (barcode) return nextAfterAdd(barcode);
    stack[stack.length - 1] = [viewMusicAdd, [{}]];
    viewMusicAdd({});
  } catch (e) {
    el.style.opacity = 1;
    if (e.status === 409) {
      const list = e.data.exists.map((x) => `• ${x.title} (${x.format || "?"}${isWish(x) ? ", önskelista" : ""})`).join("\n");
      if (confirm(`Finns redan i samlingen:\n${list}\n\nLägga till ändå?`)) addAlbum(c, barcode, el, true);
    } else alert(e.message);
  }
}

async function viewMusicManual(pre = {}) {
  const f = await facets(false, "music");
  openSheet(`
    <h2>Lägg till skiva för hand</h2>
    <p class="muted small">För skivor som inte finns i MusicBrainz eller Discogs. Du kan lägga till ett eget omslag efteråt.</p>
    <div class="form">
      <label>Artist<input id="mm-artist" type="text" value="${esc(pre.artist || "")}" placeholder="Various = samlingsskiva"></label>
      <label>Album<input id="mm-title" type="text" value="${esc(pre.title || "")}"></label>
      <div class="two"><label>År<input id="mm-year" type="number"></label>
        <label>Format<select id="mm-format">${[...new Set([...MUSIC_FORMATS, ...f.formats])].map((x) => option(x, x, pre.format || "CD")).join("")}</select></label></div>
      <div class="two"><label>Skivbolag<input id="mm-label" type="text"></label><label>Streckkod<input id="mm-barcode" type="text" inputmode="numeric" value="${esc(pre.barcode || "")}"></label></div>
      <label>Plats<input id="mm-loc" type="text" list="mm-locs"></label>
      <datalist id="mm-locs">${f.locations.map((x) => `<option value="${esc(x)}">`).join("")}</datalist>
      ${state.libs.length > 1 ? `<label>Samling<select id="mm-lib">${libOptions(scanLib())}</select></label>` : ""}
      <label class="check"><input type="checkbox" id="mm-wish"> ★ Lägg på önskelistan</label>
    </div>
    <button class="btn primary" id="mm-save">Lägg till</button>`);
  $("#mm-save").onclick = async () => {
    if (!$("#mm-title").value.trim()) return $("#mm-title").focus();
    const item = await api("/api/music/manual", { method: "POST", json: {
      title: $("#mm-title").value, artist: $("#mm-artist").value, year: $("#mm-year").value, format: $("#mm-format").value,
      label: $("#mm-label").value, barcode: $("#mm-barcode").value || pre.barcode, location: $("#mm-loc").value,
      wish: $("#mm-wish").checked, library_id: +($("#mm-lib")?.value || scanLib()) } });
    if (pre.barcode) removeFromQueue(pre.barcode);
    toast(`✓ Tillagd: <b>${esc(item.title)}</b>`, "ok");
    state.facets = null; load();
    stack = []; show(viewItem, item.id);
  };
}

const FIELD_NAMES = { title: "titel", year: "år", poster_path: "omslag", plot: "handling", series_name: "serienamn",
  season: "säsong", location: "plats", format: "format", edition: "utgåva", notes: "anteckningar", my_rating: "betyg",
  watched: "sedd", barcode: "streckkod", purchase_price: "pris", collection_status: "status", genres: "genre",
  actors: "skådespelare", director: "regi", runtime: "längd", original_title: "originaltitel", loaned_to: "utlåning",
  loan_date: "utlåning", due_date: "utlåning", added_date: "tillagd", artist: "artist", label: "skivbolag",
  cat_no: "katalognummer", tracks: "antal spår", nr_discs: "antal skivor" };
const fieldName = (f) => FIELD_NAMES[f] || f;

function viewRefreshItem(it) {
  openSheet(`
    <h2>Uppdatera metadata</h2>
    <p class="muted">${esc(it.title)}</p>
    <div class="choice" id="r-normal"><b>Uppdatera</b><span>Hämtar handling, skådespelare, regi, genre och omslag på nytt.
      Det du ändrat själv${it.locked?.length ? ` (${[...new Set(it.locked.map(fieldName))].join(", ")})` : ""} behålls.</span></div>
    <div class="choice danger" id="r-reset"><b>Återställ allt från TMDB</b><span>Skriver över även titel, år och omslag med TMDB:s uppgifter.
      Plats, anteckningar, betyg och utlåning påverkas inte.</span></div>
    <div id="r-msg"></div>`);
  const run = async (reset) => {
    if (reset && !confirm("Skriva över titel, år och omslag med uppgifter från TMDB?")) return;
    $("#r-msg").innerHTML = `<p class="muted">Hämtar…</p>`;
    try {
      await api(`/api/items/${it.id}/refresh`, { method: "POST", json: { reset } });
      toast("Metadata uppdaterad", "ok");
      back(); load();
    } catch (e) { $("#r-msg").innerHTML = `<div class="notice bad">${esc(e.message)}</div>`; }
  };
  $("#r-normal").onclick = () => run(false);
  $("#r-reset").onclick = () => run(true);
}

function viewLoan(it) {
  const due = ymd(new Date(Date.now() + 30 * 864e5));
  const names = store.get("loanNames", []);
  openSheet(`
    <h2>Låna ut</h2><p class="muted">${esc(it.title)}</p>
    <div class="form">
      <label>Till vem<input id="l-name" type="text" list="l-names" autocomplete="off"></label>
      <datalist id="l-names">${names.map((n) => `<option value="${esc(n)}">`).join("")}</datalist>
      <label>Ska vara tillbaka<input id="l-due" type="date" value="${due}"></label>
    </div>
    <button class="btn primary" id="l-save">Spara</button>`);
  $("#l-name").focus();
  $("#l-save").onclick = async () => {
    const name = $("#l-name").value.trim();
    if (!name) return;
    store.set("loanNames", [name, ...names.filter((n) => n !== name)].slice(0, 20));
    await patch(it.id, { loaned_to: name, loan_date: today(), due_date: $("#l-due").value || null });
    toast(`Utlånad till ${esc(name)}`);
    back(); load();
  };
}

async function viewEdit(it) {
  const f = await facets(false, "video");
  const field = (k, label, type = "text", extra = "") =>
    `<label>${label}<input id="e-${k}" data-f="${k}" type="${type}" value="${esc(it[k] ?? "")}" ${extra}></label>`;
  openSheet(`
    <h2>Redigera</h2>
    <div class="form">
      ${field("title", "Titel")}
      <div class="two">${field("year", "År", "number")}${it.kind === "tv" ? field("season", "Säsong", "number") : field("edition", "Utgåva")}</div>
      <div class="two">${field("format", "Format", "text", 'list="e-formats"')}${it.kind === "tv" ? field("edition", "Utgåva") : field("barcode", "Streckkod", "text", 'inputmode="numeric"')}</div>
      <datalist id="e-formats">${[...new Set(["DVD", "Blu-ray", "Blu-ray 3D", "4K UHD", "Digital", "VHS", ...f.formats])].map((x) => `<option value="${esc(x)}">`).join("")}</datalist>
      ${field("location", "Plats", "text", 'list="e-locs"')}
      <datalist id="e-locs">${f.locations.map((x) => `<option value="${esc(x)}">`).join("")}</datalist>
      <div class="two">${it.kind === "tv" ? field("barcode", "Streckkod", "text", 'inputmode="numeric"') : ""}${field("my_rating", "Mitt betyg (0–10)", "number", 'step="0.5" min="0" max="10"')}
      ${field("purchase_price", "Inköpspris (kr)", "number", 'step="0.01"')}</div>
      ${it.kind === "tv" ? field("series_name", "Serienamn (grupperar säsonger)") : ""}
      <div class="two">
        <label>Status<select id="e-collection_status" data-f="collection_status">
          ${option("In Collection", "I samlingen", it.collection_status || "In Collection")}
          ${option("On Wish List", "Önskelista", it.collection_status)}
          ${option("Sold", "Såld", it.collection_status)}</select></label>
        ${state.libs.length > 1 ? `<label>Samling<select id="e-library_id" data-f="library_id">${libOptions(it.library_id)}</select></label>` : ""}
      </div>
      <label>Anteckningar<textarea id="e-notes" data-f="notes" rows="3">${esc(it.notes || "")}</textarea></label>
    </div>
    <button class="btn primary" id="e-save">Spara</button>`);
  $("#e-save").onclick = async () => {
    const changes = {};
    for (const el of $$("[data-f]", $("#sheet-body"))) {
      const before = String(it[el.dataset.f] ?? "");
      if (el.value !== before) changes[el.dataset.f] = el.value; // skicka bara det som ändrats
    }
    if (Object.keys(changes).length) await patch(it.id, changes);
    state.facets = null;
    toast("Sparat");
    if (changes.library_id) await loadLibs();
    back(); load();
  };
}

async function viewPosters(it) {
  openSheet(`<h2>Välj omslag</h2><p class="muted">Hämtar…</p>`);
  if (!it.tmdb_id) {
    openSheet(`<h2>Välj omslag</h2><p class="muted">Titeln är inte kopplad till TMDB än. Använd ”Fel film?” först.</p>`);
    return;
  }
  const list = await api(`/api/items/${it.id}/posters`);
  openSheet(`<h2>Välj omslag</h2>
    ${list.length ? `<div class="poster-pick">${list.map((p) => `<img class="poster" loading="lazy" src="${TMDB_IMG}w185${esc(p)}" data-p="${esc(p)}">`).join("")}</div>`
      : `<p class="muted">TMDB har inga andra omslag för den här titeln.</p>`}`);
  $$(".poster-pick img").forEach((img) => (img.onclick = async () => {
    await patch(it.id, { poster_path: img.dataset.p });
    toast("Omslaget bytt");
    back(); load();
  }));
}

// ---------- Egna omslag ----------

function viewOwnCover(it) {
  openSheet(`
    <h2>Eget omslag</h2>
    <p class="muted">${esc(it.title)}</p>
    <div class="cover-prev">${poster(it.poster_path, it.title)}<div id="cov-new"></div></div>
    <div class="cover-btns">
      <label class="btn primary file-btn">📷 Ta foto<input type="file" id="cov-cam" accept="image/*" capture="environment" hidden></label>
      <label class="btn file-btn">🖼 Välj bild<input type="file" id="cov-file" accept="image/*" hidden></label>
    </div>
    <label class="form-label">…eller klistra in en bildadress</label>
    <div class="row"><input id="cov-url" type="url" placeholder="https://…/omslag.jpg">
      <button class="btn" id="cov-url-go">Hämta</button></div>
    <div id="cov-msg"></div>
    <p class="muted small">Bilden sparas i appdata och skrivs aldrig över av ”Uppdatera metadata”. Fotografera rakt framifrån –
      i rutnätet visas omslaget beskuret till omslagsformat.</p>`);
  const send = async (opts, previewUrl) => {
    $("#cov-msg").innerHTML = `<p class="muted">Sparar…</p>`;
    if (previewUrl) $("#cov-new").innerHTML = `<img class="poster" src="${previewUrl}" alt="">`;
    try {
      await api(`/api/items/${it.id}/cover`, { method: "POST", ...opts });
      toast("Eget omslag sparat", "ok");
      back(); load();
    } catch (e) { $("#cov-msg").innerHTML = `<div class="notice bad">${esc(e.message)}</div>`; }
  };
  for (const id of ["cov-cam", "cov-file"]) {
    $("#" + id).onchange = (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const fd = new FormData(); fd.append("file", file);
      send({ body: fd }, URL.createObjectURL(file));
    };
  }
  $("#cov-url-go").onclick = () => $("#cov-url").value.trim() && send({ json: { url: $("#cov-url").value.trim() } });
}

async function viewCoverImport() {
  openSheet(`
    <h2>Importera omslag</h2>
    <p class="muted small">Välj många bilder på en gång, eller en zip-fil. Döp bilderna efter <b>streckkod</b>
      (<code>7319980033032.jpg</code>) eller <b>titel</b>, gärna med år (<code>Evil Dead (1981).jpg</code>),
      så kopplas de till rätt film automatiskt.</p>
    <label class="form-label">Samling</label>
    <select id="ci-lib">${libOptions(currentLibId())}<option value="">Alla samlingar</option></select>
    <label class="check"><input type="checkbox" id="ci-missing" checked> Bara titlar som saknar omslag</label>
    <input type="file" id="ci-files" accept="image/*,.zip" multiple>
    <button class="btn primary" id="ci-go">Importera</button>
    <div id="ci-res"></div>`);
  $("#ci-go").onclick = async () => {
    const files = $("#ci-files").files;
    if (!files.length) return;
    const fd = new FormData();
    for (const f of files) fd.append("files", f);
    fd.append("lib", $("#ci-lib").value);
    fd.append("only_missing", $("#ci-missing").checked ? "1" : "0");
    $("#ci-res").innerHTML = `<p class="muted">Läser in ${files.length} ${files.length === 1 ? "fil" : "filer"}…</p>`;
    try {
      const r = await api("/api/covers/import", { method: "POST", body: fd });
      const sec = (title, list, fmt) => list.length ? `<h3>${title} (${list.length})</h3><div class="small">${list.map(fmt).join("<br>")}</div>` : "";
      $("#ci-res").innerHTML = `<div class="notice ${r.matched.length ? "ok" : ""}">${r.matched.length} omslag kopplade.</div>
        ${sec("Kopplade", r.matched, (m) => `✓ ${esc(m.title)} <span class="muted">← ${esc(m.file)}</span>`)}
        ${sec("Hittade ingen film", r.unmatched, (f) => esc(f))}
        ${sec("Flera möjliga filmer – lägg till året i filnamnet", r.ambiguous, (a) => `${esc(a.file)} <span class="muted">→ ${esc(a.titles.join(", "))}</span>`)}
        ${sec("Hade redan omslag", r.skipped, (m) => `${esc(m.title)} <span class="muted">← ${esc(m.file)}</span>`)}
        ${sec("Fel", r.errors, (m) => `${esc(m.file)}: ${esc(m.error)}`)}`;
      load();
    } catch (e) { $("#ci-res").innerHTML = `<div class="notice bad">${esc(e.message)}</div>`; }
  };
}

function viewRematch(it) {
  openSheet(`
    <h2>Välj rätt titel</h2>
    <p class="muted">${esc(it.title)}${it.year ? ` (${it.year})` : ""} – välj vilken film eller serie det egentligen är.</p>
    <div class="row"><input id="rq" type="text" value="${esc(it.series_name || it.original_title || it.title)}">
      <button class="btn primary" id="b-rq">Sök</button></div>
    <div id="results"></div>`);
  const run = async () => {
    $("#results").innerHTML = `<p class="muted">Söker…</p>`;
    try {
      const list = await api(`/api/search?q=${encodeURIComponent($("#rq").value)}`);
      $("#results").innerHTML = list.length ? list.map((c, i) => candidate(c, i)).join("") : `<p class="muted">Inga träffar.</p>`;
      $$("#results .list-item").forEach((el) => (el.onclick = async () => {
        const c = list[el.dataset.i];
        el.style.opacity = 0.5;
        await api(`/api/items/${it.id}/rematch`, { method: "POST", json: { tmdb_id: c.tmdb_id, type: c.type } });
        toast("Kopplad till rätt titel");
        back(); load();
      }));
    } catch (e) { $("#results").innerHTML = `<div class="notice bad">${esc(e.message)}</div>`; }
  };
  $("#b-rq").onclick = run;
  $("#rq").onkeydown = (e) => e.key === "Enter" && run();
  run();
}

function candidate(c, i) {
  const img = c.poster_path ? `<img class="poster thumb" loading="lazy" src="${TMDB_IMG}w154${esc(c.poster_path)}" alt="">` : `<div class="poster none thumb"></div>`;
  return `<div class="list-item" data-i="${i}">${img}
    <div class="grow"><div class="li-title">${esc(c.title)}</div><div class="muted small">${c.year || ""} · ${c.type === "tv" ? "Serie" : "Film"}
    ${c.original_title && c.original_title !== c.title ? ` · ${esc(c.original_title)}` : ""}</div></div><span class="plus">＋</span></div>`;
}

// ---------- Skanning ----------

let scan = null;        // { stream, timer, controls }
let scanHandler = null; // vad som händer med en kod
let lastCode = { code: "", at: 0 };

function scannerHtml(title, extra = "", manualHint = "…eller skriv streckkoden") {
  return `<h2>${title}</h2>
    <div id="video-wrap"><video id="video" playsinline muted></video></div>
    <div id="scan-msg" class="muted small">Rikta kameran mot streckkoden.</div>
    ${extra}
    <div class="row"><input id="manual" type="text" enterkeyhint="search" autocomplete="off" placeholder="${manualHint}">
      <button class="btn primary" id="b-manual">OK</button></div>
    <div id="manual-msg" class="small" hidden></div>`;
}

// Manuell inmatning: siffror = streckkod, text = titelsökning (om vyn tillåter det).
// Ger alltid ett besked – tidigare hände ingenting vid t.ex. en titel eller för få siffror.
function manualInput(onText) {
  const msg = (text) => { const m = $("#manual-msg"); m.textContent = text; m.hidden = !text; m.className = "small bad-text"; };
  $("#manual").oninput = () => msg("");
  $("#b-manual").onclick = () => {
    const v = $("#manual").value.trim();
    if (!v) return $("#manual").focus();
    const digits = v.replace(/[\s-]/g, "");
    if (/^\d+$/.test(digits)) {
      if (digits.length < 8 || digits.length > 14) return msg(`En streckkod har 8–13 siffror – du skrev ${digits.length}.`);
      $("#manual").value = "";
      return gotCode(digits, true);
    }
    if (onText) { stopScan(); return onText(v); }
    msg("Skriv streckkodens siffror.");
  };
  $("#manual").onkeydown = (e) => e.key === "Enter" && (e.preventDefault(), $("#b-manual").onclick());
}

async function startCamera(onCode, onText = null) {
  scanHandler = onCode;
  manualInput(onText);
  if (!window.isSecureContext || !navigator.mediaDevices) {
    $("#scan-msg").innerHTML = "Kameran kräver <b>HTTPS</b> (eller localhost). Skriv in streckkoden – eller titeln – nedan så länge.";
    $("#video-wrap").hidden = true;
    return;
  }
  try {
    if ("BarcodeDetector" in window && (await BarcodeDetector.getSupportedFormats()).includes("ean_13")) await scanNative();
    else await scanZXing();
  } catch (e) {
    $("#scan-msg").textContent = "Kunde inte starta kameran: " + e.message;
  }
}

function gotCode(code, manual = false) {
  code = String(code).replace(/\D/g, "");
  if (code.length < 8) return;
  const now = Date.now();
  if (!manual && code === lastCode.code && now - lastCode.at < 4000) return; // samma kod igen direkt
  lastCode = { code, at: now };
  scanHandler?.(code);
}

async function scanNative() {
  const detector = new BarcodeDetector({ formats: ["ean_13", "ean_8", "upc_a", "upc_e"] });
  const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
  const video = $("#video");
  video.srcObject = stream;
  await video.play();
  scan = { stream };
  scan.timer = setInterval(async () => {
    const codes = await detector.detect(video).catch(() => []);
    if (codes.length) gotCode(codes[0].rawValue);
  }, 250);
}

function loadZXing() {
  if (window.ZXingBrowser) return Promise.resolve();
  return new Promise((ok, fail) => {
    const s = document.createElement("script");
    s.src = "https://unpkg.com/@zxing/browser@0.1.5/umd/zxing-browser.min.js";
    s.onload = ok; s.onerror = () => fail(new Error("kunde inte ladda skannerbiblioteket"));
    document.head.appendChild(s);
  });
}

async function scanZXing() {
  await loadZXing();
  const reader = new ZXingBrowser.BrowserMultiFormatReader();
  scan = {};
  scan.controls = await reader.decodeFromConstraints(
    { video: { facingMode: "environment" } }, $("#video"),
    (result) => { if (result) gotCode(result.getText()); });
}

function stopScan() {
  if (!scan) return;
  clearInterval(scan.timer);
  scan.stream?.getTracks().forEach((t) => t.stop());
  scan.controls?.stop();
  scan = null;
}

const scanLib = () => currentLibId();
function scanWhere() {
  return state.lib === "all" ? `Skannar mot <b>${esc(libName(scanLib()))}</b> (välj en samling för att byta)` : `Samling: <b>${esc(libName(scanLib()))}</b>`;
}
// Film eller musik? Börjar på det som visas, och går att byta i skanningsrutan.
let scanMode = "video";
const codeView = () => (scanMode === "music" ? viewMusicCode : viewCode);

// Vanlig skanning: en kod i taget, eller serieläge där kameran står kvar
function viewScan() {
  const serial = store.get("serialScan", false);
  openSheet(scannerHtml("Skanna streckkod", `
    <div class="seg-switch" id="scan-mode"><button data-m="video" class="${scanMode === "video" ? "on" : ""}">🎬 Film & serier</button>
      <button data-m="music" class="${scanMode === "music" ? "on" : ""}">🎵 Musik</button></div>
    <p class="muted small">${scanWhere()}</p>
    <label class="check"><input type="checkbox" id="serial" ${serial ? "checked" : ""}> Skanna i serie (kameran står kvar)</label>
    <div id="queue"></div>`, scanMode === "music" ? "Streckkod eller album" : "Streckkod eller titel"));
  $("#serial").onchange = (e) => store.set("serialScan", e.target.checked);
  $$("#scan-mode button").forEach((b) => (b.onclick = () => {
    scanMode = b.dataset.m;
    $$("#scan-mode button").forEach((x) => x.classList.toggle("on", x === b));
    $("#manual").placeholder = scanMode === "music" ? "Streckkod eller album" : "Streckkod eller titel";
    renderQueue();
  }));
  renderQueue();
  startCamera(async (code) => {
    if (!$("#serial")?.checked) {
      stopScan();
      beep("new");
      return show(codeView(), code);
    }
    const r = await api(`/api/barcode/${code}?lib=${scanLib()}&local=1`);
    const mine = r.existing.filter((e) => !isWish(e));
    if (mine.length) {
      beep("owned");
      toast(`✓ Har redan: <b>${esc(mine[0].title)}</b>`, "ok");
    } else if (r.existing.length) {
      beep("wish");
      toast(`★ På önskelistan: <b>${esc(r.existing[0].title)}</b>`, "star");
    } else {
      beep("new");
      const q = queue();
      if (!q.includes(code)) q.unshift(code);
      store.set(queueKey(), q);
      renderQueue();
      toast(`Ny: ${code} – lagd i kön`);
      resolveQueued(code);
    }
  }, (text) => show(scanMode === "music" ? viewMusicAdd : viewAdd, { query: text }));
}

// Kön från serieskanning (en för film, en för musik). Titlarna slås upp i bakgrunden så att du ser vad som ligger där.
const queueKey = () => `scanQueue-${scanMode === "music" ? "music-" : ""}${scanLib()}`;
const queue = () => store.get(queueKey(), []);
const queueInfo = () => store.get("scanInfo", {});
async function resolveQueued(code) {
  try {
    const music = scanMode === "music";
    const r = await api(`/api/${music ? "music/" : ""}barcode/${code}?lib=${scanLib()}`);
    const m = r.match;
    const info = queueInfo();
    info[code] = m ? { title: music ? `${artistName(m.artist)} – ${m.title}` : m.title, year: m.year,
      poster: music ? null : m.poster_path, cover: music ? m.cover : null, src: m.source }
      : { title: r.product_title || null, unknown: !r.product_title };
    store.set("scanInfo", info);
    renderQueue();
  } catch { /* visas som okänd */ }
}
function renderQueue() {
  const el = $("#queue");
  if (!el) return;
  const q = queue(), info = queueInfo();
  el.innerHTML = q.length ? `<h3>Att lägga till (${q.length})</h3>` + q.map((c) => {
    const i = info[c];
    const label = !i ? `<span class="muted">Letar…</span>` : i.title ? `${esc(i.title)}${i.year ? ` (${i.year})` : ""}` : `<span class="muted">Okänd – sök på titel</span>`;
    return `<div class="list-item q" data-code="${c}">${i?.poster ? `<img class="poster thumb" src="${TMDB_IMG}w92${esc(i.poster)}" alt="">` : i?.cover ? netCover(i.cover, "thumb square") : `<div class="poster none thumb"></div>`}
      <div class="grow"><div class="li-title">${label}</div><div class="muted small">${c}</div></div><span class="muted">Lägg till ›</span>
      <button class="icon x" data-rm="${c}" aria-label="Ta bort ur kön">✕</button></div>`;
  }).join("") : "";
  $$("[data-code]", el).forEach((r) => (r.onclick = (e) => {
    if (e.target.closest("[data-rm]")) {
      removeFromQueue(e.target.closest("[data-rm]").dataset.rm);
      renderQueue(); return;
    }
    stopScan(); show(codeView(), r.dataset.code);
  }));
}
const removeFromQueue = (code) => store.set(queueKey(), queue().filter((c) => c !== code));

function showExisting(code, existing) {
  removeFromQueue(code);
  const wish = existing.every(isWish);
  openSheet(`<h2>${wish ? "★ På din önskelista" : "Du har redan den här"}</h2>
    <div class="notice ${wish ? "star" : "ok"}">Streckkod ${esc(code)} · ${esc(libName(scanLib()))}</div>` +
    existing.map((it) => listItem(it)).join("") +
    (wish ? `<button class="btn primary" id="b-buy">Köpt! Flytta till samlingen</button>` : "") +
    `<button class="btn" id="b-again">${queue().length ? "Nästa i kön" : "Skanna nästa"}</button>`);
  bindOpen();
  $("#b-again").onclick = () => nextAfterAdd(code);
  $("#b-buy") && ($("#b-buy").onclick = async () => {
    for (const it of existing) await patch(it.id, { collection_status: "In Collection", added_date: today() });
    toast("Flyttad till samlingen"); load(); nextAfterAdd(code);
  });
}

async function viewCode(code) {
  openSheet(`<h2>Streckkod ${esc(code)}</h2><p class="muted">Letar i dina samlingar, MyMovies och fler källor…</p>`);
  let r;
  try { r = await api(`/api/barcode/${code}?lib=${scanLib()}`); }
  catch (e) { return openSheet(`<h2>Streckkod ${esc(code)}</h2><div class="notice bad">Kunde inte slå upp streckkoden: ${esc(e.message)}</div>`); }
  if (r.existing.length) return showExisting(code, r.existing);
  viewAdd({ query: r.query, barcode: code, candidates: r.candidates, productTitle: r.product_title, match: r.match, tried: r.tried });
}

// Efter en tillagd titel i fortsätt-läget: nästa kod i kön, annars tillbaka till kameran
function nextAfterAdd(code) {
  if (code) removeFromQueue(code);
  const next = queue()[0];
  stack = [];
  if (next) show(codeView(), next); else show(viewScan);
}

let addedThisRound = 0;
const FORMATS = (f) => [...new Set(["DVD", "Blu-ray", "Blu-ray 3D", "4K UHD", "Digital", "VHS", ...f.formats])];

// Lägg till: bästa träff från streckkoden, eller sök på TMDB och välj
async function viewAdd({ query = "", barcode = null, candidates = null, productTitle = null, match = null, tried = [] }) {
  const f = await facets(false, "video");
  const last = store.get("lastAdd", { format: "DVD", location: "" });
  const keep = store.get("keepAdding", false);
  const fmt = match?.format || last.format;
  const webSearch = barcode ? `<a class="btn small web" href="https://www.google.com/search?q=${encodeURIComponent(barcode)}" target="_blank" rel="noopener">Sök streckkoden på nätet ↗</a>` : "";
  let head = "";
  if (barcode && match) {
    head = `<div class="best">
      ${match.poster_path ? `<img class="poster" src="${TMDB_IMG}w185${esc(match.poster_path)}" alt="">` : `<div class="poster none"></div>`}
      <div class="grow"><div class="muted small">Streckkod ${esc(barcode)} · hittad via ${esc(match.source)}</div>
        <h3>${esc(match.title)}</h3>
        <div class="muted">${match.year || ""} · ${match.type === "tv" ? "Serie" : "Film"}${match.original_title && match.original_title !== match.title ? ` · ${esc(match.original_title)}` : ""}</div>
        <button class="btn primary" id="b-best">＋ Lägg till</button></div></div>
      <p class="muted small">Inte rätt film? Sök nedan.</p>`;
  } else if (barcode) {
    head = `<div class="notice">Streckkod ${esc(barcode)}${productTitle ? `<br><span class="muted">Hittade: ${esc(productTitle)}</span>`
      : `<br><span class="muted">Okänd streckkod${tried.length ? ` (letade i ${esc(tried.join(", "))})` : ""} – sök på titeln nedan.</span>`}
      <div>${webSearch}</div></div>`;
  }
  openSheet(`
    <h2>${barcode ? (match ? "Hittad!" : "Ny titel") : "Lägg till"}</h2>
    ${addedThisRound ? `<div class="added-count">✓ ${addedThisRound} tillagda ${queue().length && barcode ? `· ${queue().length} kvar i kön` : ""}</div>` : ""}
    ${head}
    <div class="row"><input id="sq" type="text" value="${esc(query || "")}" placeholder="Titel (gärna med år, t.ex. Alien 1979)">
      <button class="btn primary" id="b-sq">Sök</button></div>
    <div class="row">
      <select id="fmt">${FORMATS(f).map((x) => option(x, x, fmt)).join("")}</select>
      <input id="season" type="number" min="1" placeholder="Säsong (serier)">
    </div>
    <div class="row"><input id="loc" type="text" list="a-locs" placeholder="Plats" value="${esc(last.location)}">
      <datalist id="a-locs">${f.locations.map((x) => `<option value="${esc(x)}">`).join("")}</datalist>
      ${state.libs.length > 1 ? `<select id="add-lib">${libOptions(scanLib())}</select>` : ""}</div>
    <label class="check"><input type="checkbox" id="wish"> ★ Lägg på önskelistan i stället</label>
    <label class="check"><input type="checkbox" id="keep" ${keep ? "checked" : ""}> Fortsätt lägga till fler efter den här</label>
    <div id="results"></div>
    ${!barcode ? `<p class="small"><a href="#" id="b-bulk">Har du många titlar? Klistra in en lista ›</a></p>` : ""}
    ${addedThisRound ? `<button class="btn" id="b-done">Klar</button>` : ""}`);
  $("#keep").onchange = (e) => store.set("keepAdding", e.target.checked);
  $("#b-best") && ($("#b-best").onclick = (e) => addCandidate(match, barcode, e.target.closest(".best")));
  $("#b-bulk") && ($("#b-bulk").onclick = (e) => { e.preventDefault(); show(viewBulkAdd); });
  $("#b-done") && ($("#b-done").onclick = () => { addedThisRound = 0; closeSheet(); });
  const renderList = (list) => {
    $("#results").innerHTML = list.length ? list.map(candidate).join("") : `<p class="muted">Inga träffar. Prova en annan titel.</p>`;
    $$("#results .list-item").forEach((el) => (el.onclick = () => addCandidate(list[el.dataset.i], barcode, el)));
  };
  $("#b-sq").onclick = async () => {
    if (!$("#sq").value.trim()) return $("#sq").focus();
    $("#results").innerHTML = `<p class="muted">Söker…</p>`;
    try { renderList(await api(`/api/search?q=${encodeURIComponent($("#sq").value)}`)); }
    catch (e) { $("#results").innerHTML = `<div class="notice bad">${esc(e.message)}</div>`; }
  };
  $("#sq").onkeydown = (e) => e.key === "Enter" && $("#b-sq").onclick();
  if (candidates?.length && !match) renderList(candidates);
  else if (query && !match) $("#b-sq").onclick();
  if (!barcode && !query) $("#sq").focus();
}

async function addCandidate(c, barcode, el, force = false) {
  const season = parseInt($("#season").value) || null;
  const wish = $("#wish").checked;
  const keep = $("#keep").checked;
  if (c.type === "tv" && !season && !force && !confirm("Ingen säsong angiven. Lägga till hela serien som en post?")) return;
  const body = { tmdb_id: c.tmdb_id, type: c.type, barcode, format: $("#fmt").value, season,
    location: $("#loc").value.trim() || null, wish, force, library_id: +($("#add-lib")?.value || scanLib()) };
  store.set("lastAdd", { format: body.format, location: body.location || "" });
  el.style.opacity = 0.5;
  try {
    const item = await api("/api/items", { method: "POST", json: body });
    if (barcode) removeFromQueue(barcode);
    state.facets = null;
    load();
    toast(`${wish ? "★ Önskad" : "✓ Tillagd"}: <b>${esc(item.title)}</b>`, "ok");
    if (!keep) { addedThisRound = 0; stack = []; return show(viewItem, item.id); }
    addedThisRound++;
    if (barcode) return nextAfterAdd(barcode);
    // Titelsökning: töm sökningen och stanna kvar med samma format, plats och samling
    el.style.opacity = 1;
    $("#results").innerHTML = "";
    $("#sq").value = ""; $("#season").value = "";
    stack[stack.length - 1] = [viewAdd, [{}]];
    viewAdd({});
  } catch (e) {
    el.style.opacity = 1;
    if (e.status === 409) {
      const list = e.data.exists.map((x) => `• ${x.title} (${x.format || "?"}${isWish(x) ? ", önskelista" : ""})`).join("\n");
      if (confirm(`Finns redan i samlingen:\n${list}\n\nLägga till ändå (t.ex. i ett annat format)?`)) addCandidate(c, barcode, el, true);
    } else alert(e.message);
  }
}

// ---------- Lägg till många på en gång: klistra in en lista ----------

function viewBulkAdd() {
  openSheet(`
    <h2>Lägg till flera</h2>
    <p class="muted small">En titel per rad. Skriv gärna året efter titeln för säkrare träff, t.ex. <i>Alien 1979</i>.
      Appen föreslår en träff per rad som du kan byta eller bocka ur innan allt läggs till.</p>
    <textarea id="bulk-text" rows="8" placeholder="Alien 1979&#10;Den enda vägen&#10;Heat (1995)"></textarea>
    <button class="btn primary" id="bulk-find">Hitta träffar</button>
    <div id="bulk-res"></div>`);
  $("#bulk-text").value = store.get("bulkDraft", "");
  $("#bulk-text").oninput = (e) => store.set("bulkDraft", e.target.value);
  $("#bulk-find").onclick = bulkFind;
}

async function bulkFind() {
  const lines = [...new Set($("#bulk-text").value.split("\n").map((l) => l.trim()).filter(Boolean))].slice(0, 100);
  if (!lines.length) return $("#bulk-text").focus();
  const f = await facets(false, "video");
  const last = store.get("lastAdd", { format: "DVD", location: "" });
  const rows = lines.map((line) => ({ line, list: null, pick: 0 }));
  $("#bulk-res").innerHTML = `
    <div class="row">
      <select id="fmt">${FORMATS(f).map((x) => option(x, x, last.format)).join("")}</select>
      <input id="loc" type="text" list="b-locs" placeholder="Plats" value="${esc(last.location)}">
      <datalist id="b-locs">${f.locations.map((x) => `<option value="${esc(x)}">`).join("")}</datalist>
    </div>
    ${state.libs.length > 1 ? `<label class="form-label">Samling</label><select id="add-lib">${libOptions(scanLib())}</select>` : ""}
    <label class="check"><input type="checkbox" id="wish"> ★ Lägg på önskelistan i stället</label>
    <div id="bulk-rows"></div>
    <button class="btn primary big" id="bulk-add" disabled>Söker…</button>`;
  const draw = () => {
    $("#bulk-rows").innerHTML = rows.map((r, i) => {
      if (r.list === null) return `<div class="bulk-row"><div class="poster none thumb"></div><div class="grow"><b>${esc(r.line)}</b><div class="muted small">Söker…</div></div></div>`;
      if (!r.list.length) return `<div class="bulk-row off"><div class="poster none thumb"></div><div class="grow"><b>${esc(r.line)}</b><div class="bad-text small">Ingen träff – prova annan stavning eller lägg till året</div></div></div>`;
      const c = r.list[r.pick];
      return `<div class="bulk-row ${r.skip ? "off" : ""}">
        <input type="checkbox" data-chk="${i}" ${r.skip ? "" : "checked"}>
        ${c.poster_path ? `<img class="poster thumb" src="${TMDB_IMG}w92${esc(c.poster_path)}" alt="">` : `<div class="poster none thumb"></div>`}
        <div class="grow"><div class="muted small">${esc(r.line)}</div>
          <select data-pick="${i}">${r.list.map((x, j) => option(j, `${x.title}${x.year ? ` (${x.year})` : ""} · ${x.type === "tv" ? "serie" : "film"}`, r.pick)).join("")}</select>
          ${r.status ? `<div class="small ${r.status.ok ? "ok-text" : "bad-text"}">${esc(r.status.text)}</div>` : ""}</div></div>`;
    }).join("");
    $$("[data-chk]").forEach((c) => (c.onchange = () => { rows[c.dataset.chk].skip = !c.checked; draw(); }));
    $$("[data-pick]").forEach((s) => (s.onchange = () => { rows[s.dataset.pick].pick = +s.value; draw(); }));
    const n = rows.filter((r) => r.list?.length && !r.skip && !r.status?.ok).length;
    const done = rows.every((r) => r.list !== null);
    $("#bulk-add").disabled = !done || !n;
    $("#bulk-add").textContent = done ? `Lägg till ${n} ${n === 1 ? "titel" : "titlar"}` : "Söker…";
  };
  draw();
  let next = 0;
  const worker = async () => {
    while (next < rows.length) {
      const r = rows[next++];
      try { r.list = (await api(`/api/search?q=${encodeURIComponent(r.line)}`)).slice(0, 6); } catch { r.list = []; }
      draw();
    }
  };
  await Promise.all([worker(), worker(), worker()]);
  $("#bulk-add").onclick = async () => {
    const lib = +($("#add-lib")?.value || scanLib());
    const fmt = $("#fmt").value, loc = $("#loc").value.trim() || null, wish = $("#wish").checked;
    store.set("lastAdd", { format: fmt, location: loc || "" });
    $("#bulk-add").disabled = true;
    let added = 0;
    for (const r of rows) {
      if (!r.list?.length || r.skip || r.status?.ok) continue;
      const c = r.list[r.pick];
      try {
        await api("/api/items", { method: "POST", json: { tmdb_id: c.tmdb_id, type: c.type, format: fmt, location: loc, wish, library_id: lib } });
        r.status = { ok: true, text: "✓ Tillagd" }; added++;
      } catch (e) {
        r.status = { ok: false, text: e.status === 409 ? "Finns redan – hoppades över" : e.message };
        if (e.status === 409) r.skip = true;
      }
      draw();
    }
    store.set("bulkDraft", "");
    state.facets = null; load();
    toast(`✓ ${added} ${added === 1 ? "titel" : "titlar"} tillagda`, "ok");
    $("#bulk-add").textContent = "Klart";
  };
}

// ---------- Inventering ----------

async function viewInventory() {
  const f = await facets(false, "all");
  const inv = store.get("inventory", null);
  openSheet(`
    <h2>Inventering</h2>
    <p class="muted">Skanna allt som står i hyllan. Sedan ser du vad som saknas – utlånat, felplacerat eller borta.</p>
    ${inv ? `<div class="notice">Pågående: <b>${esc(libName(inv.lib))} · ${esc(inv.location || "alla platser")}</b> – ${inv.found.length} skannade
      <br><button class="btn primary" id="i-cont">Fortsätt</button><button class="btn" id="i-res">Visa resultat</button>
      <button class="btn danger" id="i-clear">Avsluta</button></div>` : ""}
    <h3>Ny inventering i ${esc(libName(scanLib()))}</h3>
    <label class="form-label">Plats</label><select id="i-loc">${option("", "Hela samlingen", "")}${f.locations.map((l) => option(l, l, "")).join("")}</select>
    <button class="btn primary" id="i-start">Starta</button>`);
  $("#i-start").onclick = () => {
    if (inv && !confirm("Avsluta pågående inventering och starta en ny?")) return;
    store.set("inventory", { lib: scanLib(), location: $("#i-loc").value, found: [], unknown: [], started: today() });
    show(viewInventoryScan);
  };
  $("#i-cont") && ($("#i-cont").onclick = () => show(viewInventoryScan));
  $("#i-res") && ($("#i-res").onclick = () => show(viewInventoryResult));
  $("#i-clear") && ($("#i-clear").onclick = () => { store.set("inventory", null); refresh(); });
}

const invItems = (inv) => api(`/api/items?status=owned&lib=${inv.lib}&location=${encodeURIComponent(inv.location)}`);

async function viewInventoryScan() {
  const inv = store.get("inventory");
  const total = (await invItems(inv)).length;
  openSheet(scannerHtml(`Inventering: ${esc(inv.location || libName(inv.lib))}`,
    `<div class="notice" id="i-count"></div><button class="btn primary" id="i-done">Klar – visa vad som saknas</button>`));
  const update = () => ($("#i-count").innerHTML = `<b>${inv.found.length}</b> av ${total} hittade${inv.unknown.length ? ` · ${inv.unknown.length} okända` : ""}`);
  update();
  $("#i-done").onclick = () => { stopScan(); show(viewInventoryResult); };
  startCamera(async (code) => {
    const r = await api(`/api/barcode/${code}?lib=${inv.lib}&local=1`);
    const mine = r.existing.filter((e) => !isWish(e));
    if (!mine.length) {
      beep("new");
      if (!inv.unknown.includes(code)) inv.unknown.push(code);
      toast(`Okänd streckkod ${code}`, "bad");
    } else {
      beep("owned");
      let fresh = false;
      for (const m of mine) if (!inv.found.includes(m.id)) { inv.found.push(m.id); fresh = true; }
      const elsewhere = inv.location && mine.every((m) => m.location !== inv.location);
      toast(`${fresh ? "✓" : "Redan skannad:"} <b>${esc(mine[0].title)}</b>${elsewhere ? `<br>⚠ står i ${esc(mine[0].location || "okänd plats")}` : ""}`, elsewhere ? "warn" : "ok");
    }
    store.set("inventory", inv);
    update();
  });
}

async function viewInventoryResult() {
  const inv = store.get("inventory");
  if (!inv) return back();
  const all = await invItems(inv);
  const found = new Set(inv.found);
  const missing = all.filter((i) => !found.has(i.id));
  const loaned = missing.filter((i) => i.loaned_to);
  const gone = missing.filter((i) => !i.loaned_to);
  openSheet(`
    <h2>Resultat: ${esc(inv.location || libName(inv.lib))}</h2>
    <div class="notice">${all.length - missing.length} av ${all.length} hittade · ${gone.length} saknas · ${loaned.length} utlånade</div>
    ${gone.length ? `<h3>Saknas (${gone.length})</h3>${gone.map((i) => listItem(i)).join("")}` : `<p>Allt hittat! 🎉</p>`}
    ${loaned.length ? `<h3>Utlånade (${loaned.length})</h3>${loaned.map((i) => listItem(i, `<span class="muted small">${esc(i.loaned_to)}</span>`)).join("")}` : ""}
    ${inv.unknown.length ? `<h3>Okända streckkoder (${inv.unknown.length})</h3>
      <p class="muted small">Finns inte i samlingen. Tryck för att lägga till.</p>
      ${inv.unknown.map((c) => `<div class="list-item q" data-code="${c}"><div class="grow">${c}</div><span class="muted">Lägg till ›</span></div>`).join("")}` : ""}
    <button class="btn" id="i-more">Skanna fler</button>`);
  bindOpen();
  $$("[data-code]").forEach((r) => (r.onclick = () => show(viewCode, r.dataset.code)));
  $("#i-more").onclick = () => show(viewInventoryScan);
}

// ---------- Utlånat ----------

async function viewLoans() {
  const list = await api(`/api/items?status=loaned&sort=title&${libParam()}`);
  list.sort((a, b) => (a.due_date || "9999").localeCompare(b.due_date || "9999"));
  openSheet(`<h2>Utlånat (${list.length})</h2>` + (list.length ? list.map((i) => {
    const late = i.due_date && i.due_date < today();
    return listItem(i, `<span class="small ${late ? "bad-text" : "muted"} right">${esc(i.loaned_to)}${i.due_date ? `<br>${late ? "försenad " : "åter "}${esc(i.due_date)}` : ""}</span>`);
  }).join("") : `<p class="muted">Inget är utlånat just nu.</p>`));
  bindOpen();
}

// ---------- Statistik ----------

function bars(rows) {
  const max = Math.max(1, ...rows.map((r) => r.n));
  return `<div class="bars">${rows.map((r) => `<div class="bar-row"><span class="bar-label">${esc(r.label)}</span>
    <span class="bar"><span style="width:${(r.n / max) * 100}%"></span></span><span class="bar-n">${r.n}</span></div>`).join("")}</div>`;
}

const kronor = (n) => `${Math.round(n).toLocaleString("sv-SE")} kr`;

async function viewStats(part = musicTab() ? "music" : "video") {
  const s = await api(`/api/stats?${libParam()}`);
  const tile = (n, label, hl = false) => `<div class="tile ${hl ? "hl" : ""}"><b>${n}</b><span>${label}</span></div>`;
  const m = s.music, v = s.value;
  const parts = { video: "Film & serier", music: "Musik", value: "Värde & dubbletter" };
  let body;
  if (part === "music") {
    const hours = Math.round(m.minutes / 60);
    body = m.albums ? `
      <div class="tiles">
        ${tile(m.albums, "album", true)}${tile(m.artists_count, "artister")}${tile(m.discs, "skivor")}
        ${tile(m.tracks.toLocaleString("sv-SE"), "spår")}${tile(hours.toLocaleString("sv-SE"), `timmar musik`)}
        ${tile(m.compilations, "samlingsskivor")}
      </div>
      <h3>Flest album av</h3>${bars(m.artists)}
      <h3>Format</h3>${bars(m.formats)}
      ${m.genres.length ? `<h3>Genrer</h3>${bars(m.genres)}` : ""}
      ${m.decades.length ? `<h3>Årtionde</h3>${bars(m.decades)}` : ""}
      ${m.labels.length ? `<h3>Skivbolag</h3>${bars(m.labels)}` : ""}`
      : `<p class="muted">Ingen musik i samlingen än.</p>`;
  } else if (part === "value") {
    body = `
      <div class="tiles">
        ${tile(kronor(v.total), "inköpspris totalt", true)}${tile(v.priced ? kronor(v.avg) : "–", "i snitt per titel")}
        ${tile(s.all_discs, "skivor totalt")}${tile(`${v.priced} av ${v.items}`, "har inköpspris")}
      </div>
      ${v.priced < v.items ? `<p class="muted small">Värdet räknas bara på titlar där du fyllt i inköpspris (Redigera → Inköpspris, eller från CLZ).</p>` : ""}
      ${v.top.length ? `<h3>Dyraste</h3>${v.top.map((t) => listItem(t, `<span class="muted">${kronor(t.purchase_price)}</span>`)).join("")}` : ""}
      <h3>Dubbletter (${s.duplicates.length})</h3>
      <p class="muted small">Samma film, säsong eller album mer än en gång – t.ex. både DVD och Blu-ray.</p>
      ${s.duplicates.map((d) => `<div class="notice"><b>${esc(d.kind === "music" ? `${artistName(d.artist)} – ${d.title}` : d.title)}</b>
        ${d.items.map((it) => listItem(it)).join("")}</div>`).join("") || `<p>Inga dubbletter. 👌</p>`}`;
  } else {
    const hours = Math.round(s.minutes / 60);
    body = `
      <div class="tiles">
        ${tile(s.movies, "filmer", true)}${tile(s.series, `serier (${s.seasons} säsonger)`)}${tile(s.discs, "skivor")}
        ${tile(hours.toLocaleString("sv-SE"), `timmar (${Math.round(hours / 24)} dygn)`)}
        ${tile(s.titles ? Math.round((s.watched / s.titles) * 100) + " %" : "–", "sedda")}
        ${tile(s.wish, "på önskelistan")}${tile(s.loaned, "utlånade")}
      </div>
      <h3>Format</h3>${bars(s.formats)}
      <h3>Genrer</h3>${bars(s.genres)}
      <h3>Årtionde</h3>${bars(s.decades)}
      ${s.added_per_year.length ? `<h3>Tillagda per år</h3>${bars(s.added_per_year)}` : ""}
      ${s.directors.length ? `<h3>Flest filmer av</h3>${bars(s.directors)}` : ""}
      ${s.locations.length ? `<h3>Platser</h3>${bars(s.locations)}` : ""}`;
  }
  openSheet(`
    <h2>Statistik</h2><p class="muted small">${esc(state.lib === "all" ? "Alla samlingar" : libName(state.lib))}</p>
    <div class="seg-switch stat-tabs">${Object.entries(parts).map(([k, l]) => `<button data-p="${k}" class="${k === part ? "on" : ""}">${l}</button>`).join("")}</div>
    ${body}`);
  $$(".stat-tabs button").forEach((b) => (b.onclick = () => { stack[stack.length - 1] = [viewStats, [b.dataset.p]]; viewStats(b.dataset.p); }));
  bindOpen();
}

// ---------- Slumpa kvällens film ----------

async function viewRandom(pickId = null) {
  const f = await facets(false, "video");
  const r = store.get("randomOpts", { kind: "movie", unwatched: true, max: "", genre: "", format: "" });
  let pick = null;
  if (pickId) pick = await api(`/api/items/${pickId}`).catch(() => null);
  openSheet(`
    <h2>🎲 Vad ska vi se?</h2>
    <div class="form">
      <div class="two">
        <label>Typ<select id="r-kind">${option("movie", "Film", r.kind)}${option("tv", "Serie", r.kind)}${option("", "Vad som helst", r.kind)}</select></label>
        <label>Max längd<select id="r-max">${option("", "Spelar ingen roll", r.max)}${[90, 105, 120, 150].map((m) => option(m, `${m} min`, r.max)).join("")}</select></label>
      </div>
      <div class="two">
        <label>Genre<select id="r-genre">${option("", "Alla", r.genre)}${f.genres.map((g) => option(g, g, r.genre)).join("")}</select></label>
        <label>Format<select id="r-format">${option("", "Alla", r.format)}${f.formats.map((x) => option(x, x, r.format)).join("")}</select></label>
      </div>
      <label class="check"><input type="checkbox" id="r-unwatched" ${r.unwatched ? "checked" : ""}> Bara osedda</label>
    </div>
    <button class="btn primary big" id="r-go">${pick ? "Slumpa igen" : "Slumpa!"}</button>
    <div id="r-result">${pick ? `
      <div class="pick">${poster(pick.poster_path, pick.title)}
        <div><h3>${esc(pick.title)}</h3>
        <div class="muted">${[pick.year, pick.runtime && `${pick.runtime} min`, pick.location].filter(Boolean).map(esc).join(" · ")}</div>
        <div class="fmt-line">${fmtBadge(pick.format)}</div>
        <div class="muted small">${esc(pipe(pick.genres))}</div>
        ${pick.plot ? `<p class="plot small">${esc(pick.plot.length > 280 ? pick.plot.slice(0, 280) + "…" : pick.plot)}</p>` : ""}
        <button class="btn" id="r-open">Visa</button></div></div>` : ""}</div>`);
  $("#r-go").onclick = async () => {
    const o = { kind: $("#r-kind").value, max: $("#r-max").value, genre: $("#r-genre").value,
      format: $("#r-format").value, unwatched: $("#r-unwatched").checked };
    store.set("randomOpts", o);
    const p = new URLSearchParams({ kind: o.kind, unwatched: o.unwatched, genre: o.genre, format: o.format,
      lib: state.lib === "all" ? "all" : state.lib });
    if (o.max) p.set("max_runtime", o.max);
    try {
      const res = await api(`/api/random?${p}`);
      stack[stack.length - 1] = [viewRandom, [res.id]];
      viewRandom(res.id);
    } catch {
      $("#r-result").innerHTML = `<p class="muted">Inget matchade. Prova färre filter.</p>`;
    }
  };
  $("#r-open") && ($("#r-open").onclick = () => show(viewItem, pick.id));
}

// ---------- Filmserier ----------

async function viewCollections() {
  const list = await api(`/api/collections?${libParam()}`);
  openSheet(`<h2>Filmserier</h2>
    <p class="muted small">Filmer som hör ihop enligt TMDB, t.ex. alla Bond-filmer. Tryck för att se vilka delar du saknar.</p>
    ${list.length ? `<div class="mini-grid">${list.map((c) => `<div class="card" data-id="${c.id}"><div class="pw">${poster(c.poster_path, c.name)}
      <span class="badge tr">${c.owned} st</span></div><div class="t">${esc(c.name)}</div></div>`).join("")}</div>`
      : `<p class="muted">Inga filmserier hittade än. De fylls på när omslagen hämtas.</p>`}`);
  $$(".mini-grid .card").forEach((el) => (el.onclick = () => show(viewCollection, +el.dataset.id)));
}

async function viewCollection(id) {
  openSheet(`<h2>Filmserie</h2><p class="muted">Hämtar…</p>`);
  const c = await api(`/api/collections/${id}?${libParam()}`);
  const have = c.parts.filter((p) => p.owned.length).length;
  openSheet(`<h2>${esc(c.name)}</h2>
    <div class="notice">Du har ${have} av ${c.parts.length}</div>
    ${c.parts.map((p, i) => `<div class="list-item part" data-i="${i}">${p.poster_path ? `<img class="poster thumb" loading="lazy" src="/poster${esc(p.poster_path)}" alt="">` : `<div class="poster none thumb"></div>`}
      <div class="grow"><div class="li-title">${esc(p.title)}</div><div class="muted small li-sub">${p.year || ""} ${p.owned.map((o) => fmtBadge(o.format, "sm")).join("")}</div></div>
      ${p.owned.length ? `<span class="ok-text">✓</span>` : p.wished ? `<span class="star-text">★</span>`
        : `<button class="btn small" data-wish="${i}">★ Önska</button>`}</div>`).join("")}`);
  $$(".part").forEach((el) => (el.onclick = async (e) => {
    const p = c.parts[el.dataset.i];
    if (e.target.dataset.wish !== undefined) {
      e.target.disabled = true;
      await api("/api/items", { method: "POST", json: { tmdb_id: p.tmdb_id, type: "movie", wish: true, force: true, format: null, library_id: currentLibId() } });
      toast(`★ ${esc(p.title)} på önskelistan`); load(); refresh();
    } else if (p.owned.length) show(viewItem, p.owned[0].id);
  }));
}

// ---------- Saknar omslag / felmatchningar ----------

async function viewMissing(kind = "video") {
  const music = kind === "music";
  const list = await api(`/api/items?status=all&missing_poster=true&kind=${kind}&${libParam()}`);
  openSheet(`<h2>${music ? "Album utan omslag" : "Saknar omslag"} (${list.length})</h2>
    <p class="muted small">${music ? "Album som inte hittades i MusicBrainz/Discogs. Tryck för att välja rätt album, eller lägg in ett eget omslag."
      : "Titlar som inte kunde matchas automatiskt. Tryck för att välja rätt film."}</p>
    ${list.length ? `<button class="btn" id="m-retry">Försök igen automatiskt</button>` : ""}
    ${list.map((i) => listItem(i, `<span class="muted">Välj ›</span>`)).join("") || `<p>Alla har omslag! 🎉</p>`}`);
  $$(".list-item[data-id]").forEach((el) => (el.onclick = async () =>
    show(music ? viewMusicRematch : viewRematch, await api(`/api/items/${el.dataset.id}`))));
  $("#m-retry") && ($("#m-retry").onclick = async () => {
    await api(`/api/enrich?retry_failed=true${music ? "&kind=music" : ""}`, { method: "POST" });
    toast("Försöker igen i bakgrunden…");
  });
}

// ---------- Bara digitalt ----------

async function viewDigitalOnly() {
  const list = await api(`/api/digital/only?${libParam()}`);
  const src = (s) => s.map((x) => (x === "plex" ? "Plex" : "Jellyfin")).join(" + ");
  openSheet(`<h2>Bara digitalt (${list.length})</h2>
    <p class="muted small">Finns i Plex/Jellyfin men inte på skiva i ${esc(state.lib === "all" ? "någon samling" : libName(state.lib))}.
      Tryck ★ för att lägga den på önskelistan.</p>
    ${list.map((d, i) => `<div class="list-item"><div class="poster none thumb"></div>
      <div class="grow"><div class="li-title">${esc(d.title)}</div>
      <div class="muted small">${d.year || ""} · ${d.kind === "tv" ? "Serie" : "Film"} · ${src(d.sources)}</div></div>
      ${d.wished ? `<span class="star-text">★</span>` : d.tmdb_id ? `<button class="btn small" data-wish="${i}">★ Önska</button>` : ""}</div>`).join("")
      || `<p class="muted">Inget här – allt digitalt finns också på skiva, eller så är Plex/Jellyfin inte synkat än (Meny → Inställningar).</p>`}`);
  $$("[data-wish]").forEach((b) => (b.onclick = async () => {
    const d = list[b.dataset.wish];
    b.disabled = true;
    try {
      await api("/api/items", { method: "POST", json: { tmdb_id: d.tmdb_id, type: d.kind, wish: true, force: true, format: null, library_id: currentLibId() } });
      b.outerHTML = `<span class="star-text">★</span>`;
      toast(`★ ${esc(d.title)} på önskelistan`); load();
    } catch (e) { b.disabled = false; toast(esc(e.message), "bad"); }
  }));
}

// ---------- Export ----------

function viewExport() {
  const lib = state.lib === "all" ? "all" : state.lib;
  openSheet(`<h2>Exportera samlingen</h2>
    <p class="muted">Din data är din. Ladda ner ${esc(state.lib === "all" ? "alla samlingar" : libName(state.lib))} som fil –
      till ett kalkylark, en annan app eller bara för att ha en kopia.</p>
    <a class="choice" href="/api/export?format=csv&lib=${lib}" download><b>📄 CSV (kalkylark)</b><span>Öppnas i Excel, Numbers eller Google Sheets. En rad per titel/album.</span></a>
    <a class="choice" href="/api/export?format=json&lib=${lib}" download><b>🧾 JSON (allt)</b><span>Alla fält, även låtlistor och extra uppgifter från CLZ.</span></a>
    <p class="muted small">Vill du ha hela databasen? Använd Säkerhetskopior – där kan du ladda ner en .db-fil.</p>`);
}

// ---------- Meny ----------

async function viewMenu() {
  const s = await api(`/api/status?${libParam()}`);
  const c = s.counts, e = s.enrich, p = s.posters, m = s.music;
  const entry = (id, icon, label, sub = "") => `<div class="menu-item" id="${id}"><span class="mi">${icon}</span>
    <div class="grow">${label}${sub ? `<div class="muted small">${sub}</div>` : ""}</div><span class="muted">›</span></div>`;
  const group = (label) => `<div class="menu-group">${label}</div>`;
  const prog = (x, text) => `<div class="notice"><progress max="${x.total}" value="${x.done}"></progress><div class="small muted">${text}: ${x.done} av ${x.total}</div></div>`;
  const busy = (e.running ? prog(e, e.mode === "refresh" ? "Uppdaterar metadata" : "Hämtar omslag och filmserier") : "")
    + (m.running ? prog(m, "Hämtar låtlistor och skivomslag") : "")
    + (!e.running && p.running ? prog(p, "Sparar omslag lokalt") : "");
  openSheet(`
    <h2>Meny</h2>
    <div class="notice">${esc(state.lib === "all" ? "Alla samlingar" : libName(state.lib))}: ${c.movies || 0} filmer · ${c.tv || 0} säsonger · ${c.music || 0} album</div>
    ${s.tmdb ? "" : `<div class="notice bad">TMDB-nyckel saknas – omslag och sökning för film fungerar inte. <a href="#" id="m-fix">Fyll i under Inställningar</a>.</div>`}
    ${busy}
    ${group("Lägg till")}
    ${entry("m-add", "🎬", "Film eller serie", "Sök på titel")}
    ${entry("m-add-music", "🎵", "Musik", "Sök på artist och album")}
    ${entry("m-bulk", "☰", "Lägg till flera filmer", "Klistra in en lista med titlar")}
    ${group("Samlingen")}
    ${entry("m-stats", "📊", "Statistik", "Även värde och dubbletter")}
    ${entry("m-coll", "🎞", "Filmserier", "Se vilka delar du saknar")}
    ${entry("m-loans", "🤝", "Utlånat")}
    ${entry("m-inv", "📋", "Inventering", "Skanna hyllan och se vad som saknas")}
    ${s.digital.configured.length ? entry("m-digital", "▶", "Bara digitalt", "Finns i Plex/Jellyfin men inte på skiva") : ""}
    ${entry("m-missing", "🖼", "Saknar omslag", c.no_poster ? `${c.no_poster} filmer/serier` : "")}
    ${c.music ? entry("m-missing-music", "💿", "Album utan omslag", c.music_no_cover ? `${c.music_no_cover} album` : "") : ""}
    ${entry("m-covers", "🗃", "Importera omslag", "Många bilder eller en zip på en gång")}
    ${entry("m-refresh", "⟳", "Uppdatera metadata", "För filmer och serier i hela samlingen")}
    ${entry("m-libs", "🗂", "Samlingar", `${state.libs.length} st – skapa, byt namn, ta bort`)}
    ${group("Data")}
    ${entry("m-import", "⬆", "Importera från CLZ", "CLZ Movies eller CLZ Music (CSV)")}
    ${entry("m-export", "⬇", "Exportera", "CSV eller JSON")}
    ${entry("m-backup", "💾", "Säkerhetskopior", s.backups[0] ? `Senast ${s.backups[0].time.replace("T", " ")} · återställ` : "Ta en kopia eller återställ")}
    ${group("Inställningar")}
    ${entry("m-settings", "⚙", "Inställningar", "TMDB, musik, omslag, Plex/Jellyfin")}
    ${entry("m-auth", "🔒", "Inloggning", s.auth ? "På – lösenord krävs" : "Av – alla i nätverket kommer åt appen")}
    ${entry("m-ha", "🏠", "Home Assistant", "Integration och kort")}
    <p class="muted small center-text">Diskoteket ${esc(s.version)} · data i ${esc(s.config_dir)}<br>
      Vibecodat – byggt av Claude (AI), inte av en proffsutvecklare.</p>`);
  const go = { "m-add": () => show(viewAdd, {}), "m-add-music": () => show(viewMusicAdd, {}), "m-bulk": () => show(viewBulkAdd),
    "m-covers": () => show(viewCoverImport), "m-stats": () => show(viewStats), "m-coll": () => show(viewCollections),
    "m-loans": () => show(viewLoans), "m-inv": () => show(viewInventory), "m-missing": () => show(viewMissing),
    "m-missing-music": () => show(viewMissing, "music"), "m-digital": () => show(viewDigitalOnly),
    "m-refresh": () => show(viewRefreshLib), "m-libs": () => show(viewLibManage), "m-export": () => show(viewExport),
    "m-import": () => show(viewImport), "m-backup": () => show(viewBackups), "m-auth": () => show(viewAuth),
    "m-ha": () => show(viewHA), "m-settings": () => show(viewSettings) };
  for (const [id, fn] of Object.entries(go)) $("#" + id) && ($("#" + id).onclick = fn);
  $("#m-fix") && ($("#m-fix").onclick = (ev) => { ev.preventDefault(); show(viewSettings); });
  if (e.running || p.running || m.running) setTimeout(() => stack.at(-1)?.[0] === viewMenu && !$("#sheet").hidden && refresh(), 1500);
}

function viewRefreshLib() {
  const name = state.lib === "all" ? "alla samlingar" : libName(state.lib);
  openSheet(`
    <h2>Uppdatera metadata</h2>
    <p class="muted">Gäller <b>${esc(name)}</b>. Körs i bakgrunden – du kan fortsätta använda appen.</p>
    <div class="choice" id="r-normal"><b>Uppdatera</b><span>Hämtar handling, skådespelare, regi, genre och omslag på nytt för alla titlar.
      Det du har ändrat själv behålls.</span></div>
    <div class="choice danger" id="r-reset"><b>Återställ allt från TMDB</b><span>Skriver även över titlar, år och omslag du ändrat.
      Plats, anteckningar, betyg och utlåning påverkas inte.</span></div>
    <div id="r-msg"></div>`);
  const run = async (reset) => {
    if (reset && !confirm(`Skriva över titlar, år och omslag för ALLA titlar i ${name}?`)) return;
    try {
      await api("/api/refresh", { method: "POST", json: { lib: state.lib === "all" ? null : state.lib, reset } });
      toast("Uppdatering startad – följ förloppet i menyn", "ok");
      stack = []; show(viewMenu);
    } catch (e) { $("#r-msg").innerHTML = `<div class="notice bad">${esc(e.message)}</div>`; }
  };
  $("#r-normal").onclick = () => run(false);
  $("#r-reset").onclick = () => run(true);
}

function viewImport() {
  openSheet(`
    <h2>Importera från CLZ</h2>
    <p class="muted">Välj CSV-filen som du exporterat från <b>CLZ Movies</b> eller <b>CLZ Music</b> – appen känner själv igen vilken.
      Du kan importera samma fil igen: befintliga poster uppdateras, inget dubbleras och det du ändrat i Diskoteket behålls.
      Musik och film kan ligga i samma samling utan att krocka.</p>
    <label class="form-label">Till samling</label>
    <select id="imp-lib">${libOptions(currentLibId())}<option value="new">+ Ny samling…</option></select>
    <input id="imp-new" type="text" placeholder="Namn på ny samling" hidden>
    <input id="file" type="file" accept=".csv,.txt,text/csv">
    <button class="btn primary" id="b-import">Importera</button>
    <div id="import-msg"></div>`);
  $("#imp-lib").onchange = (e) => ($("#imp-new").hidden = e.target.value !== "new");
  $("#b-import").onclick = async () => {
    const f = $("#file").files[0];
    if (!f) return;
    const fd = new FormData();
    fd.append("file", f);
    if ($("#imp-lib").value === "new") {
      if (!$("#imp-new").value.trim()) return $("#imp-new").focus();
      fd.append("new_library", $("#imp-new").value.trim());
    } else fd.append("library_id", $("#imp-lib").value);
    $("#import-msg").innerHTML = `<p class="muted">Importerar…</p>`;
    try {
      const r = await api("/api/import", { method: "POST", body: fd });
      const music = r.kind === "music";
      $("#import-msg").innerHTML = `<div class="notice ok"><b>${music ? "CLZ Music" : "CLZ Movies"}:</b> ${r.added} nya, ${r.updated} uppdaterade.
        ${music ? "Låtlistor och skivomslag hämtas nu i bakgrunden (några sekunder per skiva) – se menyn." : "Omslagen hämtas nu i bakgrunden – se menyn."}
        ${r.errors.length ? `<br>Fel: ${r.errors.map(esc).join("<br>")}` : ""}</div>`;
      if (music && state.tab !== "music") $('#tabs [data-tab="music"]').click();
      state.lib = r.library_id; store.set("lib", r.library_id); state.facets = null;
      await loadLibs(); load();
    } catch (e) { $("#import-msg").innerHTML = `<div class="notice bad">${esc(e.message)}</div>`; }
  };
}

async function viewBackups() {
  const s = await api("/api/status");
  openSheet(`
    <h2>Säkerhetskopior</h2>
    <p class="muted small">Tas automatiskt var ${s.backup_hours}:e timme och sparas i <code>backup</code> i appdata-mappen.
    Kopior som tas inför borttagning eller återställning sparas tills du själv tar bort dem.</p>
    <button class="btn primary" id="bk-now">Ta en kopia nu</button>
    <label class="btn file-btn">⬆ Återställ från fil…<input type="file" id="bk-file" accept=".db,application/octet-stream" hidden></label>
    <div id="bk-msg"></div>
    <h3>Senaste</h3>
    ${s.backups.map((b) => `<div class="list-item"><div class="grow">${esc(b.time.replace("T", " "))}
      <div class="muted small">${esc(b.name)} · ${(b.size / 1024 / 1024).toFixed(1)} MB</div></div>
      <a class="btn small" href="/api/backups/${encodeURIComponent(b.name)}">Ladda ner</a>
      <button class="btn small" data-restore="${esc(b.name)}">Återställ</button></div>`).join("") || `<p class="muted">Inga kopior än.</p>`}
    <p class="muted small">Vid återställning tar appen först en kopia av nuvarande databas, så det går alltid att ångra.
      Kopior från äldre versioner av Diskoteket uppgraderas automatiskt. Lösenordet för inloggning påverkas inte.</p>`);
  $("#bk-now").onclick = async () => { await api("/api/backup", { method: "POST" }); toast("Kopia sparad"); refresh(); };
  const restore = async (opts, label) => {
    if (!confirm(`Ersätta hela samlingen med ${label}?\n\nNuvarande databas sparas först som en egen säkerhetskopia.`)) return;
    $("#bk-msg").innerHTML = `<p class="muted">Återställer…</p>`;
    try {
      const r = await api("/api/restore", { method: "POST", ...opts });
      state.facets = null;
      await loadLibs(); load();
      $("#bk-msg").innerHTML = `<div class="notice ok">Återställd: ${r.items} titlar. Den gamla databasen sparades som <code>${esc(r.safety_copy)}</code>.</div>`;
      toast("Säkerhetskopian är återställd", "ok");
    } catch (e) { $("#bk-msg").innerHTML = `<div class="notice bad">${esc(e.message)}</div>`; }
  };
  $$("[data-restore]").forEach((b) => (b.onclick = () => restore({ json: { name: b.dataset.restore } }, `kopian från ${b.closest(".list-item").querySelector(".grow").firstChild.textContent.trim()}`)));
  $("#bk-file").onchange = (e) => {
    const f = e.target.files[0];
    if (!f) return;
    const fd = new FormData(); fd.append("file", f);
    restore({ body: fd }, `filen ”${f.name}”`);
    e.target.value = "";
  };
}

async function viewSettings() {
  const [s, st] = await Promise.all([api("/api/settings"), api("/api/status")]);
  const secret = (k, label, ph) => `<label>${label}<input id="s-${k}" type="password" autocomplete="off"
    placeholder="${s[k].set ? `Sparad (${esc(s[k].hint)}) – lämna tomt för att behålla` : esc(ph)}"></label>`;
  const text = (k, label, ph = "", type = "text") => `<label>${label}<input id="s-${k}" type="${type}" value="${esc(s[k])}" placeholder="${esc(ph)}"></label>`;
  openSheet(`
    <h2>Inställningar</h2>
    <div class="form">
      <h3>TMDB (omslag och sökning)</h3>
      ${secret("tmdb_token", "API Read Access Token", "Klistra in din nyckel från themoviedb.org")}
      <label>Språk för handling och titlar<select id="s-tmdb_language">
        ${[["sv-SE", "Svenska"], ["en-US", "Engelska"], ["nb-NO", "Norska"], ["da-DK", "Danska"], ["fi-FI", "Finska"], ["de-DE", "Tyska"]]
          .map(([v, l]) => option(v, l, s.tmdb_language)).join("")}</select></label>
      <button class="btn small" data-test="tmdb">Testa nyckeln</button> <span class="test-msg" id="t-tmdb"></span>

      <h3>Streckkoder</h3>
      <label class="check"><input type="checkbox" id="s-lookup_mymovies" ${s.lookup_mymovies === "1" ? "checked" : ""}> Slå upp i MyMovies (nordiska utgåvor)</label>
      <label class="check"><input type="checkbox" id="s-lookup_upcitemdb" ${s.lookup_upcitemdb === "1" ? "checked" : ""}> Slå upp i UPCitemdb (amerikanska utgåvor, 100/dag)</label>
      ${secret("ean_db_token", "EAN-DB-nyckel (valfri)", "JWT-nyckel från ean-db.com")}
      <p class="muted small">EAN-DB ger 250 gratis uppslag efter registrering. Koder du kopplar till en film kommer appen ihåg.</p>

      <h3>Musik</h3>
      <label class="check"><input type="checkbox" id="s-lookup_musicbrainz" ${s.lookup_musicbrainz === "1" ? "checked" : ""}> Slå upp i MusicBrainz (gratis, ingen nyckel)</label>
      <button class="btn small" data-test="musicbrainz">Testa MusicBrainz</button> <span class="test-msg" id="t-musicbrainz"></span>
      ${secret("discogs_token", "Discogs-nyckel (valfri)", "Personal access token från discogs.com")}
      <button class="btn small" data-test="discogs">Testa Discogs</button> <span class="test-msg" id="t-discogs"></span>
      <p class="muted small">Discogs är bäst på ovanliga utgåvor och vinyl. Nyckel: logga in på discogs.com → Settings → Developers →
        <i>Generate new token</i>. Gratis.</p>

      <h3>Omslag</h3>
      <label class="check"><input type="checkbox" id="s-local_posters" ${s.local_posters === "1" ? "checked" : ""}> Spara omslag lokalt i appdata</label>
      <p class="muted small">${st.posters.files} omslag sparade (${st.posters.mb} MB). Lokala omslag gör att appen fungerar även om TMDB ligger nere.</p>

      <h3>Säkerhetskopior</h3>
      <div class="two">${text("backup_hours", "Var X:e timme (0 = av)", "24", "number")}${text("backup_keep", "Antal att spara", "14", "number")}</div>

      <h3>Plex</h3>
      ${text("plex_url", "Adress", "http://192.168.1.10:32400")}
      ${secret("plex_token", "Plex-token", "X-Plex-Token")}
      <button class="btn small" data-test="plex">Testa Plex</button> <span class="test-msg" id="t-plex"></span>
      <p class="muted small">Token: öppna en film i Plex webb → ⋯ → Hämta info → Visa XML. Den står sist i adressen (X-Plex-Token=…).</p>

      <h3>Jellyfin</h3>
      ${text("jellyfin_url", "Adress", "http://192.168.1.10:8096")}
      ${secret("jellyfin_api_key", "API-nyckel", "Från Jellyfin")}
      <button class="btn small" data-test="jellyfin">Testa Jellyfin</button> <span class="test-msg" id="t-jellyfin"></span>
      <p class="muted small">Nyckel: Jellyfin → Kontrollpanel → API-nycklar → +.</p>
      ${text("digital_sync_hours", "Synka Plex/Jellyfin var X:e timme", "6", "number")}
    </div>
    <button class="btn primary big" id="s-save">Spara inställningar</button>`);
  const collect = () => {
    const out = {};
    for (const el of $$("[id^=s-]", $("#sheet-body"))) {
      if (el.id === "s-save") continue;
      const k = el.id.slice(2);
      if (el.type === "checkbox") out[k] = el.checked ? "1" : "0";
      else if (el.type === "password") out[k] = el.value.trim() || "__keep__";
      else out[k] = el.value.trim();
    }
    return out;
  };
  const save = async () => { await api("/api/settings", { method: "PUT", json: collect() }); };
  $("#s-save").onclick = async () => { await save(); toast("Inställningarna sparade", "ok"); refresh(); };
  $$("[data-test]").forEach((b) => (b.onclick = async () => {
    const what = b.dataset.test, out = $("#t-" + what);
    out.textContent = "Testar…"; out.className = "test-msg";
    await save();
    const r = await api(`/api/settings/test/${what}`, { method: "POST" }).catch((e) => ({ ok: false, message: e.message }));
    out.textContent = (r.ok ? "✓ " : "✗ ") + r.message;
    out.className = "test-msg " + (r.ok ? "ok-text" : "bad-text");
  }));
}

// ---------- Inloggning ----------

async function viewAuth() {
  const a = await api("/api/auth");
  openSheet(`
    <h2>Inloggning</h2>
    ${a.enabled ? `<div class="notice ok">🔒 Inloggning är <b>på</b>. Den som öppnar appen måste skriva lösenordet (en gång per enhet).</div>`
      : `<div class="notice warn">Inloggning är <b>av</b>. Alla som når adressen kan se och ändra samlingen.
        Slå på den om appen nås utanför hemmet, t.ex. via en reverse proxy för kamerans skull.</div>`}
    <div class="form">
      <label>${a.enabled ? "Nytt lösenord" : "Välj ett lösenord"}<input id="au-pw" type="password" autocomplete="new-password" minlength="4"></label>
      <label>Skriv det igen<input id="au-pw2" type="password" autocomplete="new-password"></label>
    </div>
    <button class="btn primary" id="au-save">${a.enabled ? "Byt lösenord" : "Slå på inloggning"}</button>
    ${a.enabled ? `<button class="btn danger" id="au-off">Stäng av inloggning</button><button class="btn" id="au-logout">Logga ut</button>` : ""}
    <div id="au-msg"></div>
    ${a.enabled ? `<h3>API-nyckel för Home Assistant</h3>
      <p class="muted small">Klistra in den när du lägger till Diskoteket-integrationen i Home Assistant. Den ger bara läsrätt till sammanfattningen.</p>
      <div class="notice key">${esc(a.api_key)}</div>
      <button class="btn small" id="au-key">Skapa ny nyckel</button>` : ""}
    <p class="muted small">Glömt lösenordet? Ta bort filen <code>auth.json</code> i appdata-mappen och starta om containern.
      Omslagsbilder visas utan inloggning, så att Home Assistant-kortet kan visa dem.</p>`);
  $("#au-save").onclick = async () => {
    const pw = $("#au-pw").value;
    if (pw.length < 4) return ($("#au-msg").innerHTML = `<div class="notice bad">Minst 4 tecken.</div>`);
    if (pw !== $("#au-pw2").value) return ($("#au-msg").innerHTML = `<div class="notice bad">Lösenorden är inte lika.</div>`);
    await api("/api/auth", { method: "PUT", json: { password: pw } });
    toast(a.enabled ? "Lösenordet är bytt" : "Inloggning påslagen – du är inloggad på den här enheten", "ok");
    refresh();
  };
  $("#au-off") && ($("#au-off").onclick = async () => {
    if (!confirm("Stänga av inloggningen? Då kommer alla i nätverket åt appen utan lösenord.")) return;
    await api("/api/auth", { method: "PUT", json: { disable: true } });
    toast("Inloggning avstängd"); refresh();
  });
  $("#au-logout") && ($("#au-logout").onclick = async () => { await api("/api/logout", { method: "POST" }); location.reload(); });
  $("#au-key") && ($("#au-key").onclick = async () => {
    if (!confirm("Skapa en ny nyckel? Den gamla slutar fungera, så du måste byta den i Home Assistant också.")) return;
    await api("/api/auth/apikey", { method: "POST" }); refresh();
  });
}

async function viewHA() {
  const url = location.origin;
  const a = await api("/api/auth");
  openSheet(`
    <h2>Home Assistant</h2>
    <h3>Integration och kort (rekommenderas)</h3>
    <ol class="small">
      <li>Öppna <b>HACS</b> → ⋮ → <b>Anpassade arkiv</b>. Lägg till <code>https://github.com/claudemicro222-cmd/diskoteket</code>
        som typ <b>Integration</b>.</li>
      <li>Sök på <b>Diskoteket</b> i HACS, installera och starta om Home Assistant.</li>
      <li><b>Inställningar → Enheter och tjänster → Lägg till integration → Diskoteket</b>.
        Adress: <code>${esc(url)}</code>${a.enabled ? ` · API-nyckel: se Meny → Inloggning` : ""}.</li>
      <li>Lägg till kortet <b>Diskoteket</b> på en instrumentpanel. Välj detaljnivå i kortets inställningar:
        kompakt, standard eller detaljerad.</li>
    </ol>
    <p class="muted small">Integrationen ger sensorer för filmer, serier, album, osedda, önskelista, utlånat och försenade lån –
      som du kan använda i egna automationer.</p>
    <h3>Utan integration (REST-sensor)</h3>
    <p class="muted small">Lägg in i <code>configuration.yaml</code> och starta om Home Assistant.</p>
    <pre>rest:
  - resource: ${esc(url)}/api/ha
    scan_interval: 900${a.enabled ? `
    headers:
      Authorization: "Bearer ${esc(a.api_key)}"` : ""}
    sensor:
      - name: "Diskoteket"
        value_template: "{{ value_json.total }}"
        unit_of_measurement: "titlar"
        json_attributes:
          - movies
          - series
          - seasons
          - music
          - unwatched
          - wishlist
          - loaned
          - overdue
          - overdue_list
          - latest
          - collections
      - name: "Diskoteket senast tillagd"
        value_template: "{{ value_json.latest_title }}"
      - name: "Diskoteket försenade lån"
        value_template: "{{ value_json.overdue }}"</pre>`);
}

// ---------- Start ----------

let qTimer;
$("#q").oninput = (e) => { clearTimeout(qTimer); qTimer = setTimeout(() => { state.q = e.target.value.trim(); load(); }, 250); };
// Sökfältet börjar alltid på "Titel" när sidan öppnas
const FIELD_HINT = { title: "Sök titel…", actors: "Sök skådespelare…", director: "Sök regissör…", all: "Sök titel, skådespelare, regissör…" };
$("#q-field").value = "title";
$("#q-field").onchange = (e) => {
  state.field = e.target.value;
  $("#q").placeholder = FIELD_HINT[state.field];
  $("#q").focus();
  if (state.q) load();
};
$("#tabs").onclick = (e) => {
  if (e.target.tagName !== "BUTTON") return;
  $("#tabs .on").classList.remove("on");
  e.target.classList.add("on");
  const wasMusic = musicTab();
  state.tab = e.target.dataset.tab;
  store.set("tab", state.tab);
  if (wasMusic !== musicTab()) { // format och genrer skiljer sig mellan film och musik
    state.format = ""; state.genre = "";
    if (state.sort === "artist" || (musicTab() && ["imdb", "runtime"].includes(state.sort))) state.sort = "title";
    saveFilters();
  }
  load();
};
$("#btn-scan").onclick = () => {
  closeSheet();
  try { audio = audio || new (window.AudioContext || window.webkitAudioContext)(); audio.resume(); } catch { /* inget ljud */ }
  scanMode = musicTab() ? "music" : "video";
  show(viewScan);
};
$("#brand").onclick = (e) => { e.preventDefault(); closeSheet(); window.scrollTo({ top: 0, behavior: "smooth" }); };
const open = (fn) => () => { closeSheet(); show(fn); };
$("#btn-menu").onclick = open(viewMenu);
$("#btn-filter").onclick = open(viewFilter);
$("#btn-random").onclick = open(viewRandom);
$("#btn-view").onclick = open(viewDisplay);
$("#btn-lib").onclick = open(viewLibPicker);

// Kom ihåg fliken mellan besöken (önskelistan börjar alltid om på "Alla")
const savedTab = store.get("tab", "all");
if (savedTab !== "wish" && $(`#tabs [data-tab="${savedTab}"]`)) {
  state.tab = savedTab;
  $("#tabs .on").classList.remove("on");
  $(`#tabs [data-tab="${savedTab}"]`).classList.add("on");
}

applyTheme();
loadLibs().then(load).catch((e) => toast("Kunde inte ladda samlingen: " + esc(e.message), "bad"));
