/* Cardboard Colin sign maker.
   The sign is an editable, resizable piece of cardboard. Its real size is kept
   in points (1/72 in); the screen shows it to scale. opentype.js does the
   layout (wrapping + fitting) so print, PDF, SVG, PNG and Word all match.
   Everything runs in the browser. */
(() => {
  const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const PAPER = { letter: [612, 792], a4: [595.28, 841.89], tabloid: [792, 1224] };      // pt, portrait
  const PRESETS = { letter: [792, 612], a4: [841.89, 595.28], tabloid: [1224, 792], square: [864, 864], banner: [2592, 864] };
  const NAMES = { letter: "Letter", a4: "A4", tabloid: "Tabloid", square: "Square 12 in", banner: "Banner 36 × 12 in" };
  const MIN = 144, MAX = 3456;                       // 2 in .. 48 in
  const LH = 1.12, CAP = 0.7, DESC = 0.22, ASC_EXTRA = 0.18;
  const TEX_TILE = 512 * 0.75;                       // texture tile width in pt (matches the 512 px CSS tile at 1:1)
  const state = { text: "", weight: "Regular", align: "center", fg: "#1c1a1e", bg: "#c4a06c", tex: true,
                  W: 792, H: 612, auto: true, size: 120, paper: "sign", texExport: true };
  const fonts = {};
  const loadFont = (w) => fonts[w] || (fonts[w] = fetch(`fonts/ttf/CardboardColin-${w}.ttf`)
      .then(r => r.arrayBuffer()).then(b => opentype.parse(b)));
  const loadScript = (src) => new Promise((ok, bad) => {
    if (document.querySelector(`script[src="${src}"]`)) return ok();
    const s = document.createElement("script"); s.src = src; s.onload = ok; s.onerror = bad; document.head.appendChild(s);
  });
  let texImg = null;
  const loadTex = () => texImg || (texImg = new Promise((ok, bad) => { const i = new Image(); i.onload = () => ok(i); i.onerror = bad; i.src = "assets/cardboard.jpg"; }));

  // ---------------------------------------------------------------- layout (pt)
  const marginOf = (W, H) => Math.min(W, H) * 0.07;
  function wrap(font, text, maxEm) {
    const out = [];
    for (const hard of text.replace(/\r/g, "").split("\n")) {
      const words = hard.split(/ +/);
      let line = "";
      for (const w of words) {
        const t = line ? line + " " + w : w;
        if (!line || font.getAdvanceWidth(t, 1, { kerning: true }) <= maxEm) line = t;
        else { out.push(line); line = w; }
      }
      out.push(line);
    }
    while (out.length > 1 && !out[out.length - 1].trim()) out.pop();
    return out;
  }
  const blockEm = (n) => (n - 1) * LH + CAP + DESC + ASC_EXTRA;
  function fits(font, size, W, H, m) {
    const lines = wrap(font, state.text, (W - 2 * m) / size);
    const wide = Math.max(0, ...lines.map(l => font.getAdvanceWidth(l, 1, { kerning: true })));
    return wide * size <= W - 2 * m + 0.01 && blockEm(lines.length) * size <= H - 2 * m + 0.01 ? lines : null;
  }
  function layout(font) {
    const W = state.W, H = state.H, m = marginOf(W, H);
    let size, lines;
    if (state.auto) {                                   // biggest size whose wrapped text fits
      let lo = 4, hi = Math.max(8, H);
      for (let i = 0; i < 26; i++) { const mid = (lo + hi) / 2; if (fits(font, mid, W, H, m)) lo = mid; else hi = mid; }
      size = lo; lines = fits(font, size, W, H, m) || wrap(font, state.text, (W - 2 * m) / size);
    } else {
      size = state.size; lines = wrap(font, state.text, (W - 2 * m) / size);
    }
    const adv = lines.map(l => font.getAdvanceWidth(l, 1, { kerning: true }));
    const top = (H - blockEm(lines.length) * size) / 2 + ASC_EXTRA * size;
    const paths = lines.map((l, i) => {
      const w = adv[i] * size;
      const x = state.align === "left" ? m : state.align === "right" ? W - m - w : (W - w) / 2;
      return font.getPath(l, x, top + CAP * size + i * LH * size, size, { kerning: true });
    });
    return { W, H, size, paths, lines, margin: m };
  }
  // where the sign sits on the output page (paper = "sign" means same size)
  function placement(L) {
    if (state.paper === "sign") return { PW: L.W, PH: L.H, k: 1, ox: 0, oy: 0 };
    let [pw, ph] = PAPER[state.paper];
    if ((L.W > L.H) !== (pw > ph)) [pw, ph] = [ph, pw];          // match orientation
    const k = Math.min(pw / L.W, ph / L.H);
    return { PW: pw, PH: ph, k, ox: (pw - L.W * k) / 2, oy: (ph - L.H * k) / 2 };
  }

  const esc = (s) => s.replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  function svgString(L, { forPrint = false, texture = false } = {}) {
    const P = forPrint ? placement(L) : { PW: L.W, PH: L.H, k: 1, ox: 0, oy: 0 };
    const d = L.paths.map(p => p.toPathData(2)).join(" ");
    const dims = forPrint ? `width="${(P.PW - 1).toFixed(2)}pt" height="${(P.PH - 1).toFixed(2)}pt"` : `width="${L.W.toFixed(1)}pt" height="${L.H.toFixed(1)}pt"`;
    const tex = texture ? `<defs><pattern id="cb" patternUnits="userSpaceOnUse" width="${TEX_TILE}" height="${TEX_TILE * 0.75}">` +
      `<image href="${new URL("assets/cardboard.jpg", location.href)}" width="${TEX_TILE}" height="${TEX_TILE * 0.75}" preserveAspectRatio="none"/></pattern></defs>` : "";
    return `<svg xmlns="http://www.w3.org/2000/svg" ${dims} viewBox="0 0 ${P.PW.toFixed(2)} ${P.PH.toFixed(2)}">` +
      `<title>${esc(L.lines.join(" "))}</title>${tex}` + (forPrint && state.paper !== "sign" ? `<rect width="100%" height="100%" fill="#fff"/>` : "") +
      `<g transform="translate(${P.ox.toFixed(2)} ${P.oy.toFixed(2)}) scale(${P.k.toFixed(5)})">` +
      `<rect width="${L.W.toFixed(2)}" height="${L.H.toFixed(2)}" fill="${state.bg}"/>` +
      (texture ? `<rect width="${L.W.toFixed(2)}" height="${L.H.toFixed(2)}" fill="url(#cb)"/>` : "") +
      `<path d="${d}" fill="${state.fg}"/></g></svg>`;
  }

  // ---------------------------------------------------------------- on-screen sign
  const stage = $("#stage"), board = $("#board"), sign = $("#sign");
  let scale = 1, dragging = null;
  const readText = () => sign.innerText.replace(/\u00a0/g, " ").replace(/\n$/, "");
  state.text = readText();
  function fitScale() {
    const cs = getComputedStyle(stage);
    const availW = stage.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight) - 24;
    const availH = Math.min(window.innerHeight * 0.72, 760);
    return Math.max(0.05, Math.min(availW / state.W, availH / state.H, 1.6));
  }
  let tok = 0;
  async function render() {
    const t = ++tok;
    scale = dragging ? Math.min(dragging.scale, fitScale()) : fitScale();   // zoom out if the sign outgrows the screen
    board.style.width = state.W * scale + "px"; board.style.height = state.H * scale + "px";
    board.classList.toggle("tex", state.tex);
    board.style.backgroundColor = state.bg;
    sign.style.color = state.fg; sign.style.textAlign = state.align;
    sign.style.fontWeight = { Light: 300, Regular: 400, Bold: 700 }[state.weight];
    const m = marginOf(state.W, state.H) * scale;
    sign.style.padding = `${m}px`;
    showDims();
    if (typeof opentype === "undefined") return;
    const font = await loadFont(state.weight);
    if (t !== tok) return;
    const L = layout(font);
    lastLayout = L;
    // the browser wraps the live text itself; give it the same size and width
    sign.style.fontSize = L.size * scale + "px";
    const over = !state.auto && !fits(font, L.size, L.W, L.H, L.margin);
    $("#sizeval").textContent = state.auto ? `auto · ${Math.round(L.size)} pt` : `${Math.round(L.size)} pt${over ? " · too big to fit" : ""}`;
    if (state.auto) $("#size").value = Math.round(Math.min(400, L.size));
  }
  let lastLayout = null;
  const inches = (pt) => pt / 72;
  function presetName() {
    for (const [k, [a, b]] of Object.entries(PRESETS)) {
      if (Math.abs(state.W - a) < 2 && Math.abs(state.H - b) < 2) return NAMES[k] + (a !== b ? " landscape" : "");
      if (Math.abs(state.W - b) < 2 && Math.abs(state.H - a) < 2) return NAMES[k] + " portrait";
    }
    return "Custom";
  }
  function showDims() {
    const wi = inches(state.W), hi = inches(state.H);
    if (document.activeElement !== $("#win")) $("#win").value = wi.toFixed(1);
    if (document.activeElement !== $("#hin")) $("#hin").value = hi.toFixed(1);
    const r = state.W / state.H;
    const txt = `${Math.round(wi * 25.4)} × ${Math.round(hi * 25.4)} mm · ${r >= 1 ? r.toFixed(2) + " : 1" : "1 : " + (1 / r).toFixed(2)} · ${presetName()}`;
    $("#dimsout").textContent = txt;
    $('.h[data-h="se"]').setAttribute("aria-valuetext", `${wi.toFixed(1)} by ${hi.toFixed(1)} inches`);
    $$("[data-preset]").forEach(b => { const [a, c] = PRESETS[b.dataset.preset];
      b.classList.toggle("on", (Math.abs(state.W - a) < 2 && Math.abs(state.H - c) < 2) || (Math.abs(state.W - c) < 2 && Math.abs(state.H - a) < 2)); });
  }
  const clamp = (v) => Math.max(MIN, Math.min(MAX, v));
  function setSize(W, H) { state.W = clamp(W); state.H = clamp(H); render(); }

  // drag handles: pointer events (mouse, pen and touch). The board stays centred,
  // so each edge moves half the change: a handle follows the finger exactly.
  $$(".h", board).forEach(h => {
    h.addEventListener("pointerdown", (e) => {
      e.preventDefault(); h.setPointerCapture(e.pointerId);
      dragging = { dir: h.dataset.h, x: e.clientX, y: e.clientY, W: state.W, H: state.H, scale };
      stage.style.minHeight = stage.offsetHeight + "px";
      document.body.classList.add("resizing");
    });
    h.addEventListener("pointermove", (e) => {
      if (!dragging || !h.hasPointerCapture(e.pointerId)) return;
      const d = dragging.dir, dx = (e.clientX - dragging.x) / dragging.scale, dy = (e.clientY - dragging.y) / dragging.scale;
      let W = dragging.W, H = dragging.H;
      if (d.includes("e")) W += 2 * dx; if (d.includes("w")) W -= 2 * dx;
      if (d.includes("s")) H += 2 * dy; if (d.includes("n")) H -= 2 * dy;
      if (d.length === 2 && e.shiftKey) {            // Shift on a corner keeps the shape
        const k = Math.max(W / dragging.W, H / dragging.H); W = dragging.W * k; H = dragging.H * k;
      }
      setSize(W, H);
    });
    const end = (e) => {
      if (!dragging) return;
      dragging = null; stage.style.minHeight = ""; document.body.classList.remove("resizing");
      render();
    };
    h.addEventListener("pointerup", end); h.addEventListener("pointercancel", end);
    h.addEventListener("keydown", (e) => {      // keyboard: arrows resize by 1/4 inch (Shift: 1 inch)
      const st = e.shiftKey ? 72 : 18, k = { ArrowRight: [st, 0], ArrowLeft: [-st, 0], ArrowDown: [0, st], ArrowUp: [0, -st] }[e.key];
      if (k) { e.preventDefault(); setSize(state.W + k[0], state.H + k[1]); }
    });
  });
  window.addEventListener("resize", () => { if (!dragging) render(); });

  // ---------------------------------------------------------------- controls
  sign.addEventListener("input", () => { state.text = readText(); render(); });
  sign.addEventListener("paste", (e) => {            // plain text only (for browsers without plaintext-only)
    e.preventDefault();
    const t = (e.clipboardData || window.clipboardData).getData("text/plain");
    document.execCommand("insertText", false, t);
  });
  if (sign.contentEditable !== "plaintext-only") sign.contentEditable = "true";
  const setText = (t) => { sign.textContent = t; state.text = t; render(); };
  $$(".signbar .presets button").forEach(b => b.addEventListener("click", () => setText(b.dataset.text)));
  const seg = (btn) => { $$("button", btn.parentElement).forEach(x => x.classList.remove("on")); btn.classList.add("on"); };
  $$("[data-w]").forEach(b => b.addEventListener("click", () => { seg(b); state.weight = b.dataset.w; render(); }));
  $$("[data-align]").forEach(b => b.addEventListener("click", () => { seg(b); state.align = b.dataset.align; render(); }));
  $$("[data-preset]").forEach(b => b.addEventListener("click", () => {
    const [a, c] = PRESETS[b.dataset.preset]; const portrait = state.H > state.W && a !== c;
    portrait ? setSize(c, a) : setSize(a, c);
  }));
  $("#rotate").addEventListener("click", () => setSize(state.H, state.W));
  const dimIn = () => { const w = parseFloat($("#win").value), h = parseFloat($("#hin").value);
    if (w > 0 && h > 0) setSize(w * 72, h * 72); };
  $("#win").addEventListener("change", dimIn); $("#hin").addEventListener("change", dimIn);
  const auto = $("#autofit"), size = $("#size");
  auto.addEventListener("change", () => {
    state.auto = auto.checked; size.disabled = state.auto;
    if (!state.auto && lastLayout) { state.size = Math.round(lastLayout.size); size.value = Math.min(400, state.size); }
    render();
  });
  size.addEventListener("input", () => { state.size = +size.value; render(); });
  const fg = $("#fg"), bg = $("#bg");
  $$(".swatch").forEach(b => b.addEventListener("click", () => {
    $$(".swatch").forEach(x => x.classList.remove("on")); b.classList.add("on");
    state.fg = b.dataset.fg; state.bg = b.dataset.bg; state.tex = !!b.dataset.tex; fg.value = state.fg; bg.value = state.bg; render();
  }));
  fg.addEventListener("input", () => { state.fg = fg.value; render(); });
  bg.addEventListener("input", () => { $$(".swatch").forEach(x => x.classList.remove("on")); state.bg = bg.value; state.tex = false; render(); });
  $("#paper").addEventListener("change", (e) => { state.paper = e.target.value; });
  $("#texexport").addEventListener("change", (e) => { state.texExport = e.target.checked; });
  const useTex = () => state.tex && state.texExport;

  // ---------------------------------------------------------------- exports
  const save = (blob, ext) => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = `cardboard-colin-sign.${ext}`;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  };
  const toast = (m) => { const t = $("#toast"); if (!t) return; t.textContent = m; t.classList.add("show"); setTimeout(() => t.classList.remove("show"), 1800); };

  async function paintBg(g, W, H, scale) {           // g already scaled to pt
    g.fillStyle = state.bg; g.fillRect(0, 0, W, H);
    if (!useTex()) return;
    const img = await loadTex();
    const pat = g.createPattern(img, "repeat");
    pat.setTransform(new DOMMatrix().scale(TEX_TILE / img.width));
    g.fillStyle = pat; g.fillRect(0, 0, W, H);
  }
  async function pngBlob(L, dpi = 300) {
    const scale = Math.min(dpi / 72, Math.sqrt(24e6 / (L.W * L.H)));     // cap at ~24 megapixels
    const c = document.createElement("canvas");
    c.width = Math.round(L.W * scale); c.height = Math.round(L.H * scale);
    const g = c.getContext("2d"); g.scale(scale, scale);
    await paintBg(g, L.W, L.H);
    g.fillStyle = state.fg; g.fill(new Path2D(L.paths.map(p => p.toPathData(3)).join(" ")));
    return new Promise(ok => c.toBlob(ok, "image/png"));
  }
  async function texJpeg(W, H) {                     // page-sized texture for the PDF background
    const k = Math.min(150 / 72, Math.sqrt(8e6 / (W * H)));
    const c = document.createElement("canvas"); c.width = Math.round(W * k); c.height = Math.round(H * k);
    const g = c.getContext("2d"); g.scale(k, k); await paintBg(g, W, H);
    return c.toDataURL("image/jpeg", 0.85);
  }
  function pdfPathOps(path, P) {
    const X = (x) => P.ox + x * P.k, Y = (y) => P.oy + y * P.k;
    const ops = []; let cx = 0, cy = 0, sx = 0, sy = 0;
    for (const c of path.commands) {
      if (c.type === "M") { ops.push({ op: "m", c: [X(c.x), Y(c.y)] }); cx = sx = c.x; cy = sy = c.y; }
      else if (c.type === "L") { ops.push({ op: "l", c: [X(c.x), Y(c.y)] }); cx = c.x; cy = c.y; }
      else if (c.type === "C") { ops.push({ op: "c", c: [X(c.x1), Y(c.y1), X(c.x2), Y(c.y2), X(c.x), Y(c.y)] }); cx = c.x; cy = c.y; }
      else if (c.type === "Q") {
        const c1x = cx + 2 / 3 * (c.x1 - cx), c1y = cy + 2 / 3 * (c.y1 - cy);
        const c2x = c.x + 2 / 3 * (c.x1 - c.x), c2y = c.y + 2 / 3 * (c.y1 - c.y);
        ops.push({ op: "c", c: [X(c1x), Y(c1y), X(c2x), Y(c2y), X(c.x), Y(c.y)] }); cx = c.x; cy = c.y;
      } else if (c.type === "Z") { ops.push({ op: "h", c: [] }); cx = sx; cy = sy; }
    }
    return ops;
  }

  const exporters = {
    async svg(L) { save(new Blob([svgString(L)], { type: "image/svg+xml" }), "svg"); },
    async png(L) { save(await pngBlob(L), "png"); },
    async pdf(L) {
      await loadScript("assets/vendor/jspdf.umd.min.js");
      const { jsPDF } = window.jspdf, P = placement(L);
      const doc = new jsPDF({ unit: "pt", format: [P.PW, P.PH], orientation: P.PW > P.PH ? "landscape" : "portrait", compress: true });
      doc.setProperties({ title: L.lines.join(" "), creator: "Cardboard Colin sign maker" });
      if (useTex()) doc.addImage(await texJpeg(L.W, L.H), "JPEG", P.ox, P.oy, L.W * P.k, L.H * P.k);
      else { doc.setFillColor(state.bg); doc.rect(P.ox, P.oy, L.W * P.k, L.H * P.k, "F"); }
      doc.setFillColor(state.fg);
      for (const p of L.paths) { const ops = pdfPathOps(p, P); if (ops.length) { doc.path(ops); doc.fill(); } }
      save(doc.output("blob"), "pdf");
    },
    async docx(L) {
      await loadScript("assets/vendor/docx.umd.js");
      const D = window.docx;
      let P = placement(L);
      if (P.PW > 1584 || P.PH > 1584) {               // Word pages top out at 22 in: fit on Tabloid
        const keep = state.paper; state.paper = "tabloid"; P = placement(L); state.paper = keep;
      }
      const png = await (await pngBlob(L, 150)).arrayBuffer();   // 150 dpi keeps Word files small
      const orient = P.PW > P.PH ? D.PageOrientation.LANDSCAPE : D.PageOrientation.PORTRAIT;
      const [pageW, pageH] = P.PW > P.PH ? [P.PH, P.PW] : [P.PW, P.PH];   // docx wants portrait numbers + orientation
      const imgW = L.W * P.k, imgH = L.H * P.k - 2;      // tiny slack so Word keeps it on one page
      const pt2px = 96 / 72, tw = (pt) => Math.round(pt * 20);
      const children = [new D.Paragraph({ spacing: { before: 0, after: 0, line: 240 }, alignment: D.AlignmentType.CENTER,
        children: [new D.ImageRun({ data: png, transformation: { width: imgW * pt2px, height: imgH * pt2px },
                   altText: { title: "Sign", description: L.lines.join(" "), name: "sign" } })] })];
      const pageProps = (m) => ({ page: { size: { width: tw(pageW), height: tw(pageH), orientation: orient },
        margin: { top: tw(m.t), bottom: tw(m.b), left: tw(m.l), right: tw(m.r), header: 0, footer: 0 } } });
      const imgMargin = { t: Math.max(0, P.oy - 1), b: 0, l: Math.max(0, P.ox - 1), r: Math.max(0, P.ox - 1) };
      const textMargin = { t: 54, b: 54, l: 54, r: 54 };
      const sections = [{ properties: pageProps(imgMargin), children }];
      if ($("#docxtext").checked) {
        const al = { left: D.AlignmentType.LEFT, center: D.AlignmentType.CENTER, right: D.AlignmentType.RIGHT }[state.align];
        const txt = [new D.Paragraph({ spacing: { after: 240 }, children: [new D.TextRun({
          text: "Editable version: needs the Cardboard Colin font installed (free at https://dadardy.github.io/cardboard-colin/). Delete this line before printing.",
          size: 18, color: "777777", font: "Arial" })] })];
        const k2 = Math.min((P.PW - 108) / L.W, (P.PH - 140) / L.H, 1);   // same layout, shrunk to fit inside 0.75 in margins
        const halfPts = Math.max(16, Math.round(L.size * k2 * 0.92 * 2));
        for (const line of L.lines) txt.push(new D.Paragraph({ alignment: al, children: [
          new D.TextRun({ text: line, font: "Cardboard Colin", size: halfPts, color: state.fg.replace("#", ""),
                          bold: state.weight === "Bold" })] }));
        sections.push({ properties: pageProps(textMargin), children: txt });
      }
      const doc = new D.Document({ creator: "Cardboard Colin sign maker", title: L.lines.join(" "), sections });
      save(await D.Packer.toBlob(doc), "docx");
    },
    async print(L) {
      const P = placement(L);
      const sheet = $("#print-sheet");
      sheet.innerHTML = svgString(L, { forPrint: true, texture: useTex() });
      if (useTex()) await loadTex();
      let st = $("#print-page-style");
      if (!st) { st = document.createElement("style"); st.id = "print-page-style"; document.head.appendChild(st); }
      st.textContent = `@page { size: ${P.PW.toFixed(2)}pt ${P.PH.toFixed(2)}pt; margin: 0; }`;
      document.body.classList.add("printing-sign");
      window.print();
    },
  };
  window.addEventListener("afterprint", () => document.body.classList.remove("printing-sign"));

  $$("[data-export]").forEach(b => b.addEventListener("click", async () => {
    const kind = b.dataset.export, label = b.textContent;
    b.disabled = true; b.textContent = "…";
    try { const L = layout(await loadFont(state.weight)); await exporters[kind](L); if (kind !== "print") toast(`${label} downloaded`); }
    catch (e) { console.error(e); toast(`Sorry, ${label} export failed`); }
    finally { b.disabled = false; b.textContent = label; }
  }));
  // for testing / power users
  window.cardboardSign = { state, render, setSize, layout: async () => layout(await loadFont(state.weight)), exporters, get scale() { return scale; } };

  if (window.matchMedia("(max-width: 760px)").matches) state.W = 792, state.H = 612;
  render();
  if (typeof opentype === "undefined") window.addEventListener("load", render);
})();
