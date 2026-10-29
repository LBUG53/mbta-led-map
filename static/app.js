// MBTA LED map simulator: front end.
// The server sends the exact per-output RGB the firmware would send over DDP,
// and the sign bitmap the firmware draws. This file only simulates what
// happens after that: WLED's brightness cap (and optional gamma), then light
// through a hole in the board and the paper; and the sign's LEDs.

const W_MM = 610, H_MM = 610;
const PX_PER_MM = 2;                 // light layer resolution; the print on top is vector
const W = W_MM * PX_PER_MM, H = H_MM * PX_PER_MM;
// How the lights look through the paper: the hole in the wood, how far the bulb sits behind the
// paper, and how much the paper spreads the light, all in mm. Then the room's light and an exposure,
// as if photographed.
const HOLE = 8, DEPTH = 10, SCATTER = 1.2, ROOM = 0.35, EXPOSURE = 4;
const STATE_NAMES = ["off", "stopped", "riding"];

const $ = (id) => document.getElementById(id);
const canvas = $("light");
const ctx = canvas.getContext("2d");
canvas.width = W; canvas.height = H;
const img = ctx.createImageData(W, H);
const buf = new Float32Array(W * H * 3);   // linear light, 0..1 (can exceed 1 before clipping)

let layout = null, frame = null, profile = null, zoom = 1;

// ---------- WLED stage ----------
const GAMMA = new Uint8Array(256).map((_, i) => Math.round(255 * Math.pow(i / 255, 2.8)));

function wledOut(rgb) {
  const bri = Math.round(+$("brightness").value * 255);
  const g = $("gamma").checked;
  return rgb.map((c) => ((g ? GAMMA[c] : c) * (bri + 1)) >> 8);
}

// ---------- Optics ----------
// Paper irradiance from a pixel `depth` mm behind it, seen through a hole of
// radius `a` in the board: cos^4 falloff inside the hole (inverse square,
// incidence angle, and a roughly Lambertian bullet dome), zero outside, then
// blurred by the paper with a Gaussian of `sigma` mm. Returned as a radial
// table (0.1 mm steps) normalised to the un-blurred on-axis value.
function computeProfile(a, depth, sigma) {
  const step = 0.1, rMax = a + 4 * sigma, n = Math.ceil(rMax / step) + 2;
  const h = Math.min(0.25, sigma / 2);
  const pts = [];
  for (let y = -a; y <= a; y += h)
    for (let x = -a; x <= a; x += h) {
      const q2 = x * x + y * y;
      if (q2 <= a * a) { const c = (depth * depth) / (depth * depth + q2); pts.push(x, y, c * c); }
    }
  const norm = (h * h) / (2 * Math.PI * sigma * sigma), cut2 = 16 * sigma * sigma;
  const out = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const r = i * step;
    let s = 0;
    for (let k = 0; k < pts.length; k += 3) {
      const dx = r - pts[k], dy = pts[k + 1], d2 = dx * dx + dy * dy;
      if (d2 < cut2) s += pts[k + 2] * Math.exp(-d2 / (2 * sigma * sigma));
    }
    out[i] = s * norm;
  }
  return { table: out, step, rMax };
}

function updateProfile() {
  profile = computeProfile(HOLE / 2, DEPTH, SCATTER);
}

// ---------- Rendering ----------
const LUT_N = 4096;
const SRGB = new Uint8ClampedArray(LUT_N + 1).map((_, i) => {
  const v = i / LUT_N;
  return Math.round(255 * (v <= 0.0031308 ? 12.92 * v : 1.055 * Math.pow(v, 1 / 2.4) - 0.055));
});

// The module RGB for a light: each output's list is in wiring order.
function ledRGB(i) {
  const l = layout.lights[i];
  return frame.chains[l.output][l.index];
}

function render() {
  if (!layout || !frame || !profile) return;
  buf.fill(ROOM);
  const { table, step, rMax } = profile;
  const R = Math.ceil(rMax * PX_PER_MM);
  layout.lights.forEach((l, i) => {
    const out = wledOut(ledRGB(i));
    if (!out[0] && !out[1] && !out[2]) return;
    const lr = (out[0] / 255) * EXPOSURE, lg = (out[1] / 255) * EXPOSURE, lb = (out[2] / 255) * EXPOSURE;
    const cx = l.x * PX_PER_MM, cy = l.y * PX_PER_MM;
    const x0 = Math.max(0, Math.floor(cx - R)), x1 = Math.min(W - 1, Math.ceil(cx + R));
    const y0 = Math.max(0, Math.floor(cy - R)), y1 = Math.min(H - 1, Math.ceil(cy + R));
    for (let y = y0; y <= y1; y++) {
      const dy = (y + 0.5 - cy) / PX_PER_MM;
      for (let x = x0; x <= x1; x++) {
        const dx = (x + 0.5 - cx) / PX_PER_MM;
        const idx = Math.round(Math.sqrt(dx * dx + dy * dy) / step);
        if (idx >= table.length) continue;
        const p = table[idx], o = (y * W + x) * 3;
        buf[o] += lr * p; buf[o + 1] += lg * p; buf[o + 2] += lb * p;
      }
    }
  });
  const d = img.data;
  for (let i = 0, j = 0; i < buf.length; i += 3, j += 4) {
    d[j] = SRGB[Math.min(LUT_N, (buf[i] * LUT_N) | 0)];
    d[j + 1] = SRGB[Math.min(LUT_N, (buf[i + 1] * LUT_N) | 0)];
    d[j + 2] = SRGB[Math.min(LUT_N, (buf[i + 2] * LUT_N) | 0)];
    d[j + 3] = 255;
  }
  ctx.putImageData(img, 0, 0);
}

// ---------- LED sign ----------
// The 64 x 32 panel at 5 mm pitch is 320 x 160 mm, centred behind the print's
// sign-window-cut rectangle (which the server reads from the print), so the
// outermost pixels sit just inside the window's edge.
let WIN = { x: 249.05, y: 407.8, w: 315.5, h: 156.75 };
const PITCH = 5;
const SIGN_PX_PER_MM = 6;
const SIGN_MS = 50;                  // the board redraws at about 20 frames a second
const signCanvas = $("sign"), sctx = signCanvas.getContext("2d");
let signData = null, signTimer = null;

function placeSign(win) {
  WIN = win;
  signCanvas.width = WIN.w * SIGN_PX_PER_MM; signCanvas.height = WIN.h * SIGN_PX_PER_MM;
  const s = signCanvas.style;
  s.left = (100 * WIN.x) / W_MM + "%"; s.top = (100 * WIN.y) / H_MM + "%";
  s.width = (100 * WIN.w) / W_MM + "%"; s.height = (100 * WIN.h) / H_MM + "%";
}

function signPixelCenter(i, j) {
  const x0 = (WIN.w - 64 * PITCH) / 2 + PITCH / 2, y0 = (WIN.h - 32 * PITCH) / 2 + PITCH / 2;
  return [(x0 + i * PITCH) * SIGN_PX_PER_MM, (y0 + j * PITCH) * SIGN_PX_PER_MM];
}

function drawSign() {
  if (!signData) return;
  const s = SIGN_PX_PER_MM;
  sctx.globalCompositeOperation = "source-over";
  sctx.fillStyle = "#0a0a0b";                       // panel face
  sctx.fillRect(0, 0, signCanvas.width, signCanvas.height);
  sctx.fillStyle = "#1b1b1d";                       // unlit LEDs
  for (let j = 0; j < signData.h; j++)
    for (let i = 0; i < signData.w; i++) {
      const [x, y] = signPixelCenter(i, j);
      sctx.beginPath(); sctx.arc(x, y, 1.1 * s, 0, 2 * Math.PI); sctx.fill();
    }
  sctx.globalCompositeOperation = "lighter";
  // The sign runs very dim (a few percent); show it brighter so it reads on screen.
  const exposure = 2.2 / Math.max(0.05, signData.palette[1][0] / 255);
  const css = signData.palette.map((c) => c.map((v) => SRGB[Math.min(LUT_N, ((Math.pow(v / 255, 2.2) * exposure) * LUT_N) | 0)]));
  for (let j = 0; j < signData.h; j++) {
    const row = signData.rows[j];
    for (let i = 0; i < signData.w; i++) {
      const k = parseInt(row[i], 16);
      if (!k) continue;
      const [r, g, b] = css[k];
      const [x, y] = signPixelCenter(i, j);
      const grad = sctx.createRadialGradient(x, y, 0, x, y, 2.6 * s);
      grad.addColorStop(0, `rgba(${r},${g},${b},1)`);
      grad.addColorStop(0.42, `rgba(${r},${g},${b},0.9)`);
      grad.addColorStop(0.55, `rgba(${r},${g},${b},0.25)`);
      grad.addColorStop(1, `rgba(${r},${g},${b},0)`);
      sctx.fillStyle = grad;
      sctx.fillRect(x - 2.6 * s, y - 2.6 * s, 5.2 * s, 5.2 * s);
    }
  }
}

async function fetchSign() {
  clearTimeout(signTimer);
  const q = new URLSearchParams({ source: source(), night: night() });
  try {
    const j = await (await fetch("/api/sign?" + q)).json();
    if (!j.error) { signData = j; drawSign(); renderSignDebug(); }
  } catch (err) { /* the map status line already reports a dead server */ }
  signTimer = setTimeout(fetchSign, SIGN_MS);
}

function renderSignDebug() {
  if ($("debug").hidden || !signData) return;
  const d = signData.debug;
  const fmt = (times) => times.map(([t]) => t).join(", ") || "none";
  $("signDebug").innerHTML = "<b>Sign</b><br>" +
    d.rows.map((r) => `${esc(r.label)} (stop ${esc(r.stop)}${r.walk ? ", " + r.walk + " min walk" : ""}): ` +
      `${esc(fmt(r.times))} · ${r.count} predictions kept`).join("<br>") +
    `<br>Ticker now: ${esc(d.showing)}<br>Rotation: ${d.rotation.map(esc).join(" | ")}` +
    (d.error ? `<br><span class="warn">${esc(d.error)}</span>` : "") +
    "<br>Requests (time, size):<br>" + d.sources.map((x) => "&nbsp;&nbsp;" + esc(x)).join("<br>");
}

// ---------- Markers & hover ----------
let highlight = -1;
function drawMarkers() {
  const svg = $("markers");
  let ring = "";
  if (highlight >= 0) {
    const l = layout.lights[highlight];
    ring = `<circle cx="${l.x}" cy="${l.y}" r="6.5" fill="none" stroke="#ffb020" stroke-width="1"/>`;
  }
  if (!$("showMarkers").checked || !frame) { svg.innerHTML = ring; return; }
  // Each output's wire, pixel to pixel, then the 8 mm holes with their place in the chain.
  const WIRE = { 1: "#c02a1c", 2: "#b36a00", 3: "#00763a" };
  const chains = {};
  layout.lights.forEach((l) => { (chains[l.output] = chains[l.output] || []).push(l); });
  const wires = Object.entries(chains).map(([o, ls]) =>
    `<polyline points="${ls.sort((a, b) => a.index - b.index).map((l) => l.x + "," + l.y).join(" ")}" fill="none" ` +
    `stroke="${WIRE[o] || "#555"}" stroke-width=".5" stroke-opacity=".75"/>`).join("");
  svg.innerHTML = ring + wires + layout.lights.map((l) =>
    `<circle cx="${l.x}" cy="${l.y}" r="4" fill="none" stroke="#000" stroke-width=".3" stroke-dasharray="1 1"/>` +
    `<text x="${l.x}" y="${l.y + 0.9}" font-size="2.4" text-anchor="middle" font-family="monospace" fill="#000">${l.index}</text>`
  ).join("");
}

$("stage").addEventListener("mousemove", (e) => {
  if (!layout || !frame) return;
  const r = $("stage").getBoundingClientRect();
  const x = ((e.clientX - r.left) / r.width) * W_MM, y = ((e.clientY - r.top) / r.height) * H_MM;
  let best = -1, bd = 7;
  layout.lights.forEach((l, i) => { const d = Math.hypot(l.x - x, l.y - y); if (d < bd) { bd = d; best = i; } });
  if (best < 0) { $("hover").textContent = `x ${x.toFixed(1)} mm, y ${y.toFixed(1)} mm`; return; }
  const l = layout.lights[best], rgb = ledRGB(best);
  $("hover").innerHTML =
    `<b>${l.line} ${esc(l.station)}</b> light ${l.side} (${l.stop_id})\n` +
    `trains heading ${esc(l.toward)}\n` +
    `output ${l.output}, pixel ${l.index}  ·  ${STATE_NAMES[frame.states[best]]}\n` +
    `module ${rgb.join(",")} → WLED ${wledOut(rgb).join(",")}`;
});

// ---------- Data ----------
const REFRESH_MS = 1000;            // the firmware resends to WLED about once a second
const ANIM_MS = 50;                 // 20 frames/s while the remote's find or goal sweep runs
let frameTimer = null, refreshTimer = null, lastDebug = 0;

function source() {
  const v = $("scene").value;
  return v === "live" ? "live" : "sample:" + v;
}
function night() { return $("night").checked ? "1" : "0"; }

function requestFrame() {
  clearTimeout(frameTimer);
  frameTimer = setTimeout(fetchFrame, 60);
}

async function fetchFrame() {
  clearTimeout(refreshTimer);
  const q = new URLSearchParams({ source: source(), night: night() });
  try {
    const res = await fetch("/api/frame?" + q);
    const j = await res.json();
    if (j.error) throw new Error(j.error);
    if (layout && j.layout_id && j.layout_id !== layout.layout_id) {
      location.reload();              // the server now has a different print: start fresh
      return;
    }
    frame = j;
    showStatus();
    if ($("showMarkers").checked) drawMarkers();
    render();
    if (Date.now() - lastDebug > 900) renderDebug();
  } catch (err) {
    $("status").textContent = "Error: " + err.message;
    $("status").className = "err";
  }
  if (frame && frame.animated) refreshTimer = setTimeout(fetchFrame, ANIM_MS);
  else if (source() === "live") refreshTimer = setTimeout(fetchFrame, REFRESH_MS);
}

function showStatus() {
  const st = $("status");
  st.className = "";
  const p = frame.poll;
  if (!p) { st.textContent = "Source: " + frame.source; return; }
  if (p.age === null) { st.textContent = "Live: waiting for the first vehicles request…"; return; }
  const n = new Set(frame.vehicles.flat().concat(frame.unmapped).map((v) => v.id)).size;
  st.textContent = `Live: ${n} vehicles, ${p.age} s old` + (p.error ? ` · ${p.error}` : "") + (p.stale ? " · stale" : "");
  if (p.error || p.stale) st.className = "err";
}

// ---------- Debug view ----------
const hex = (rgb) => "#" + rgb.map((c) => c.toString(16).padStart(2, "0")).join("");
const esc = (t) => String(t).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const SHORT = { STOPPED_AT: "at", INCOMING_AT: "incoming", IN_TRANSIT_TO: "to" };

function vehText(v) {
  const where = v.stop == null ? "(no stop reported)" : `${SHORT[v.status] || esc(v.status)} ${esc(v.stop)}`;
  return `<span class="veh">${esc(v.id)} ${esc(v.route)} dir ${v.direction_id ?? "?"} ${where}</span>`;
}

function renderDebug() {
  if ($("debug").hidden || !frame) return;
  lastDebug = Date.now();
  $("unmapped").innerHTML = frame.unmapped.length
    ? "<b class='warn'>Vehicles lighting nothing:</b><br>" + frame.unmapped.map(vehText).join("<br>")
    : "Every vehicle maps to a light.";
  const onlyLit = $("dbgLit").checked;
  const rows = layout.lights.map((l, i) => ({ l, i }))
    .sort((a, b) => a.l.output - b.l.output || a.l.index - b.l.index)
    .filter(({ i }) => !onlyLit || frame.states[i] > 0);
  $("ledTable").tBodies[0].innerHTML = rows.map(({ l, i }) => {
    const rgb = ledRGB(i), s = frame.states[i];
    return `<tr data-i="${i}"><td>${l.output}</td><td>${l.index}</td><td>${l.line} ${esc(l.station)} ${l.side}</td>` +
      `<td class="st-${s}">${STATE_NAMES[s]}</td><td>${frame.vehicles[i].map(vehText).join("<br>")}</td>` +
      `<td><span class="sw" style="background:${hex(rgb)}"></span>${rgb.join(",")}</td>` +
      `<td>${wledOut(rgb).join(",")}</td></tr>`;
  }).join("");
}

$("ledTable").addEventListener("mouseover", (e) => {
  const tr = e.target.closest("tr[data-i]");
  const i = tr ? +tr.dataset.i : -1;
  if (i !== highlight) { highlight = i; drawMarkers(); }
});
$("ledTable").addEventListener("mouseleave", () => { highlight = -1; drawMarkers(); });
$("showDebug").addEventListener("input", () => {
  $("debug").hidden = !$("showDebug").checked;
  sizeStage();
  renderDebug();
  renderSignDebug();
});
$("dbgLit").addEventListener("input", renderDebug);

// ---------- Controls ----------
const OUTPUTS = { brightness: "o_bri" };
function showValues() { for (const [k, o] of Object.entries(OUTPUTS)) $(o).textContent = $(k).value; }

["scene", "night"].forEach((id) => $(id).addEventListener("input", () => { requestFrame(); fetchSign(); }));
["brightness", "gamma"].forEach((id) => $(id).addEventListener("input", () => { showValues(); render(); renderDebug(); }));
$("showMarkers").addEventListener("input", drawMarkers);
$("outline").addEventListener("input", () => { $("print").src = "/print.svg?outline=" + ($("outline").checked ? 1 : 0); });

function sizeStage() {
  const vp = $("viewport");
  const fitH = Math.min(vp.clientHeight - 48 - 28, ((vp.clientWidth - 48 - 28) * H_MM) / W_MM);
  // "Actual size": browsers treat 96 CSS pixels as one inch.
  const h = zoom === "actual" ? (H_MM * 96) / 25.4 : Math.max(200, fitH) * zoom;
  $("stage").style.height = h + "px";
  $("stage").style.width = (h * W_MM) / H_MM + "px";
}
$("zoom").addEventListener("click", (e) => {
  const z = e.target.dataset.z;
  if (!z) return;
  zoom = z === "actual" ? "actual" : +z;
  [...$("zoom").children].forEach((b) => b.classList.toggle("on", b === e.target));
  sizeStage();
});
window.addEventListener("resize", sizeStage);

(async function init() {
  layout = await (await fetch("/api/layout")).json();
  const m = layout.map || {};
  $("brightness").value = m.brightness ?? 0.3;
  placeSign(layout.sign_window);
  $("outline").checked = !!m.print_outline;
  $("print").src = "/print.svg?outline=" + (m.print_outline ? 1 : 0);
  showValues();
  sizeStage();
  updateProfile();
  requestFrame();
  fetchSign();
})();

// ---------- Modes: the phone remote's commands, sent to the board this page shows ----------
function boardKind() { return source() === "live" ? "live" : "sample"; }

async function remoteCall(path, body) {
  const opts = { headers: { "X-Remote": "1" } };
  if (body) Object.assign(opts, { method: "POST", body: JSON.stringify(body) });
  const res = await fetch("/remote/api/" + path + "?board=" + boardKind(), opts);
  return res.json();
}

function showModeState(s) {
  if (!s || s.error) return;
  [...$("modes").children].forEach((b) => b.classList.toggle("on", b.dataset.mode === s.mode));
  $("costume").checked = !!s.costume;
  $("align").checked = !!s.align;
  $("modeState").textContent = "Board: " + s.mode + (s.timer ? ", timer " + s.timer + " s" : "") +
    (s.message ? ", message " + s.message : "") + ". These go to the board the page is showing (live or sample).";
  showRides(s.rides || []);
}

// ---------- Rides ----------
const rideKey = (name) => name.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 8);
let rideChoices = null;

function fillSelect(id, names) {
  $(id).innerHTML = names.map((n) => `<option>${esc(n)}</option>`).join("");
}

function rideLineChanged() {
  fillSelect("rideFrom", rideChoices.stops[$("rideLine").value]);
  fillSelect("rideTo", rideChoices.stops[$("rideLine").value]);
  $("rideTo").selectedIndex = 1;
}

function showRides(rides) {
  $("rideList").innerHTML = rides.map(([name, line, eta]) =>
    `<div class="rider"><span>${esc(name)} on ${esc(line)}${eta ? ", arriving " + esc(eta) : ", finding the train"}</span>` +
    `<button data-end="${esc(name)}">End</button></div>`).join("");
  $("rideList").querySelectorAll("button").forEach((b) =>
    b.addEventListener("click", () => cmd({ cmd: "ride", text: b.dataset.end + ";DONE" })));
  $("rideSend").textContent = rides.some((r) => r[0] === rideKey($("rideName").value)) ? "Change train" : "Start ride";
}

async function cmd(c) {
  try { showModeState(await remoteCall("cmd", c)); } catch (err) { $("modeState").textContent = "Error: " + err.message; }
  requestFrame();
  fetchSign();
}

[...$("modes").children].forEach((b) => b.addEventListener("click", () => cmd({ cmd: "mode", mode: b.dataset.mode })));
$("costume").addEventListener("input", () => cmd({ cmd: "costume", on: $("costume").checked }));
$("align").addEventListener("input", () => cmd({ cmd: "align", on: $("align").checked }));
$("msgSend").addEventListener("click", () => cmd({ cmd: "message", text: $("msgText").value }));
$("msgClear").addEventListener("click", () => cmd({ cmd: "message", text: "" }));
$("timer60").addEventListener("click", () => cmd({ cmd: "timer", seconds: 60 }));
$("timerStop").addEventListener("click", () => cmd({ cmd: "timer_stop" }));
$("findGo").addEventListener("click", () => cmd({ cmd: "find", i: +$("findWhich").value }));
$("rideLine").addEventListener("change", () => rideChoices && rideLineChanged());
$("rideName").addEventListener("input", async () => showModeState(await remoteCall("state")));
$("rideSend").addEventListener("click", () => {
  const name = rideKey($("rideName").value);
  if (name) cmd({ cmd: "ride", text: [name, $("rideLine").value, $("rideFrom").value, $("rideTo").value].join(";") });
});
$("rideDone").addEventListener("click", () => {
  const name = rideKey($("rideName").value);
  if (name) cmd({ cmd: "ride", text: name + ";DONE" });
});
$("scene").addEventListener("input", async () => showModeState(await remoteCall("state")));

(async function initModes() {
  try {
    const stations = await remoteCall("stations");
    $("findWhich").innerHTML = stations.map(([line, name], i) => `<option value="${i}">${esc(line)} ${esc(name)}</option>`).join("");
    rideChoices = await remoteCall("rides");
    fillSelect("rideLine", rideChoices.lines);
    rideLineChanged();
    showModeState(await remoteCall("state"));
    setInterval(async () => showModeState(await remoteCall("state")), 5000);
  } catch (err) { /* the status line reports a dead server */ }
})();
