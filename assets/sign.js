/* Cardboard Colin sign maker. Lays text out with opentype.js so the preview,
   print, PDF, SVG, PNG and Word exports are identical. All client-side. */
(() => {
  const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const PAGES = { letter: [612, 792], a4: [595.28, 841.89], tabloid: [792, 1224] }; // points, portrait
  const PAGE_CSS = { letter: "letter", a4: "A4", tabloid: "11in 17in" };
  const LH = 1.12, CAP = 0.7, DESC = 0.22, ASC_EXTRA = 0.18;
  const state = { text: "", weight: "Regular", align: "center", fg: "#1c1a1e", bg: "#ffffff",
                  page: "letter", orient: "landscape", size: 120 };
  const fonts = {};
  const loadFont = (w) => fonts[w] || (fonts[w] = fetch(`fonts/ttf/CardboardColin-${w}.ttf`)
      .then(r => r.arrayBuffer()).then(b => opentype.parse(b)));
  const loadScript = (src) => new Promise((ok, bad) => {
    if (document.querySelector(`script[src="${src}"]`)) return ok();
    const s = document.createElement("script"); s.src = src; s.onload = ok; s.onerror = bad; document.head.appendChild(s);
  });

  // ---------------------------------------------------------------- layout
  function layout(font) {
    const lines = state.text.replace(/\r/g, "").split("\n");
    while (lines.length > 1 && !lines[lines.length - 1].trim()) lines.pop();
    const adv = lines.map(l => font.getAdvanceWidth(l, 1, { kerning: true }));
    const maxAdv = Math.max(0.01, ...adv);
    const n = lines.length;
    const blockEm = (n - 1) * LH + CAP + DESC + ASC_EXTRA;
    let W, H, size, margin;
    if (state.page === "free") {
      size = state.size * 0.75;                         // px -> pt
      margin = size * 0.4;
      W = maxAdv * size + 2 * margin; H = blockEm * size + 2 * margin;
    } else {
      const [pw, ph] = PAGES[state.page];
      [W, H] = state.orient === "landscape" ? [ph, pw] : [pw, ph];
      margin = Math.min(W, H) * 0.07;
      size = Math.min((W - 2 * margin) / maxAdv, (H - 2 * margin) / blockEm);
    }
    const top = (H - blockEm * size) / 2 + ASC_EXTRA * size;
    const paths = lines.map((l, i) => {
      const w = adv[i] * size;
      const x = state.align === "left" ? margin : state.align === "right" ? W - margin - w : (W - w) / 2;
      const y = top + CAP * size + i * LH * size;
      return font.getPath(l, x, y, size, { kerning: true });
    });
    return { W, H, size, paths, lines, margin };
  }

  function svgString(L, { forPrint = false } = {}) {
    const d = L.paths.map(p => p.toPathData(2)).join(" ");
    const dims = forPrint ? `width="${(L.W - 1).toFixed(2)}pt" height="${(L.H - 1).toFixed(2)}pt"` : `width="${L.W}" height="${L.H}"`;
    return `<svg xmlns="http://www.w3.org/2000/svg" ${dims} viewBox="0 0 ${L.W.toFixed(2)} ${L.H.toFixed(2)}">` +
      `<title>${esc(L.lines.join(" "))}</title>` +
      `<rect width="100%" height="100%" fill="${state.bg}"/>` +
      `<path d="${d}" fill="${state.fg}"/></svg>`;
  }
  const esc = (s) => s.replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  // ---------------------------------------------------------------- preview
  const preview = $("#preview");
  let renderToken = 0;
  async function render() {
    const tok = ++renderToken;
    const font = await loadFont(state.weight);
    if (tok !== renderToken) return;
    const L = layout(font);
    preview.innerHTML = svgString(L);
    const svg = preview.firstElementChild;
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", "Sign preview: " + L.lines.join(" "));
    preview.classList.toggle("free", state.page === "free");
    if (state.page === "free") { svg.style.width = (L.W / 0.75) + "px"; }
  }

  // ---------------------------------------------------------------- controls
  const ta = $("#signtext");
  state.text = ta.value;
  ta.addEventListener("input", () => { state.text = ta.value; render(); });
  $$(".maker .presets button").forEach(b => b.addEventListener("click", () => {
    ta.value = b.dataset.text; state.text = ta.value; render();
  }));
  const seg = (btn) => { $$("button", btn.parentElement).forEach(x => x.classList.remove("on")); btn.classList.add("on"); };
  $$("[data-w]").forEach(b => b.addEventListener("click", () => { seg(b); state.weight = b.dataset.w; ta.style.fontWeight = { Light: 300, Regular: 400, Bold: 700 }[state.weight]; render(); }));
  $$("[data-align]").forEach(b => b.addEventListener("click", () => { seg(b); state.align = b.dataset.align; ta.style.textAlign = state.align; render(); }));
  $$("[data-o]").forEach(b => b.addEventListener("click", () => { seg(b); state.orient = b.dataset.o; render(); }));
  const fg = $("#fg"), bg = $("#bg");
  const setColors = (f, g) => { state.fg = f; state.bg = g; fg.value = f; bg.value = g; render(); };
  $$(".swatch").forEach(b => b.addEventListener("click", () => {
    $$(".swatch").forEach(x => x.classList.remove("on")); b.classList.add("on"); setColors(b.dataset.fg, b.dataset.bg);
  }));
  const custom = () => { $$(".swatch").forEach(x => x.classList.remove("on")); state.fg = fg.value; state.bg = bg.value; render(); };
  fg.addEventListener("input", custom); bg.addEventListener("input", custom);
  const page = $("#page"), size = $("#size"), sizeval = $("#sizeval");
  page.addEventListener("change", () => {
    state.page = page.value;
    const free = state.page === "free";
    $("#sizefield").hidden = !free; $("#orient").style.display = free ? "none" : "";
    $("#fitnote").textContent = free ? "The download is just big enough for your text." : "The text grows to fill the page.";
    render();
  });
  size.addEventListener("input", () => { state.size = +size.value; sizeval.textContent = size.value + "px"; render(); });

  // ---------------------------------------------------------------- exports
  const save = (blob, ext) => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = `cardboard-colin-sign.${ext}`;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  };
  const toast = (m) => { const t = $("#toast"); if (!t) return; t.textContent = m; t.classList.add("show"); setTimeout(() => t.classList.remove("show"), 1800); };

  async function pngBlob(L) {
    const scale = state.page === "free" ? 4 : 300 / 72;          // 300 dpi on a page
    const c = document.createElement("canvas");
    c.width = Math.round(L.W * scale); c.height = Math.round(L.H * scale);
    const g = c.getContext("2d");
    g.fillStyle = state.bg; g.fillRect(0, 0, c.width, c.height);
    g.scale(scale, scale); g.fillStyle = state.fg;
    g.fill(new Path2D(L.paths.map(p => p.toPathData(3)).join(" ")));
    return new Promise(ok => c.toBlob(ok, "image/png"));
  }

  function pdfPathOps(path) {
    const ops = []; let cx = 0, cy = 0, sx = 0, sy = 0;
    for (const c of path.commands) {
      if (c.type === "M") { ops.push({ op: "m", c: [c.x, c.y] }); cx = sx = c.x; cy = sy = c.y; }
      else if (c.type === "L") { ops.push({ op: "l", c: [c.x, c.y] }); cx = c.x; cy = c.y; }
      else if (c.type === "C") { ops.push({ op: "c", c: [c.x1, c.y1, c.x2, c.y2, c.x, c.y] }); cx = c.x; cy = c.y; }
      else if (c.type === "Q") {
        const c1x = cx + 2 / 3 * (c.x1 - cx), c1y = cy + 2 / 3 * (c.y1 - cy);
        const c2x = c.x + 2 / 3 * (c.x1 - c.x), c2y = c.y + 2 / 3 * (c.y1 - c.y);
        ops.push({ op: "c", c: [c1x, c1y, c2x, c2y, c.x, c.y] }); cx = c.x; cy = c.y;
      } else if (c.type === "Z") { ops.push({ op: "h", c: [] }); cx = sx; cy = sy; }
    }
    return ops;
  }

  const exporters = {
    async svg(L) { save(new Blob([svgString(L)], { type: "image/svg+xml" }), "svg"); },
    async png(L) { save(await pngBlob(L), "png"); },
    async pdf(L) {
      await loadScript("assets/vendor/jspdf.umd.min.js");
      const { jsPDF } = window.jspdf;
      const doc = new jsPDF({ unit: "pt", format: [L.W, L.H], orientation: L.W > L.H ? "landscape" : "portrait", compress: true });
      doc.setProperties({ title: L.lines.join(" "), creator: "Cardboard Colin sign maker" });
      doc.setFillColor(state.bg); doc.rect(0, 0, L.W, L.H, "F");
      doc.setFillColor(state.fg);
      for (const p of L.paths) { const ops = pdfPathOps(p); if (ops.length) { doc.path(ops); doc.fill(); } }
      save(doc.output("blob"), "pdf");
    },
    async docx(L) {
      await loadScript("assets/vendor/docx.umd.js");
      const D = window.docx;
      const png = await (await pngBlob(L)).arrayBuffer();
      let pageW, pageH, orient, imgW, imgH, margin;
      if (state.page === "free") {                       // free size: fit on a Letter page
        [pageW, pageH] = PAGES.letter; orient = L.W > L.H ? D.PageOrientation.LANDSCAPE : D.PageOrientation.PORTRAIT;
        const [aw, ah] = orient === D.PageOrientation.LANDSCAPE ? [pageH, pageW] : [pageW, pageH];
        margin = 36; const k = Math.min((aw - 2 * margin) / L.W, (ah - 2 * margin) / L.H);
        imgW = L.W * k; imgH = L.H * k;
      } else {
        [pageW, pageH] = PAGES[state.page]; orient = state.orient === "landscape" ? D.PageOrientation.LANDSCAPE : D.PageOrientation.PORTRAIT;
        margin = 0; imgW = L.W; imgH = L.H - 2;            // tiny slack so Word keeps it on one page
      }
      const pt2px = 96 / 72, tw = (pt) => Math.round(pt * 20);
      const children = [new D.Paragraph({ spacing: { before: 0, after: 0 }, alignment: D.AlignmentType.CENTER,
        children: [new D.ImageRun({ data: png, transformation: { width: imgW * pt2px, height: imgH * pt2px },
                   altText: { title: "Sign", description: L.lines.join(" "), name: "sign" } })] })];
      const pageProps = (m) => ({ page: { size: { width: tw(pageW), height: tw(pageH), orientation: orient },
        margin: { top: tw(m), bottom: tw(m), left: tw(m), right: tw(m), header: 0, footer: 0 } } });
      const sections = [{ properties: pageProps(margin), children }];
      if ($("#docxtext").checked) {
        const al = { left: D.AlignmentType.LEFT, center: D.AlignmentType.CENTER, right: D.AlignmentType.RIGHT }[state.align];
        const txt = [new D.Paragraph({ spacing: { after: 240 }, children: [new D.TextRun({
          text: "Editable version: needs the Cardboard Colin font installed (free at https://dadardy.github.io/cardboard-colin/). Delete this line before printing.",
          size: 18, color: "777777", font: "Arial" })] })];
        const halfPts = Math.max(16, Math.round(Math.min(L.size * 0.75, 110) * 2));
        for (const line of L.lines) txt.push(new D.Paragraph({ alignment: al, children: [
          new D.TextRun({ text: line, font: "Cardboard Colin", size: halfPts, color: state.fg.replace("#", ""),
                          bold: state.weight === "Bold" })] }));
        sections.push({ properties: pageProps(54), children: txt });
      }
      const doc = new D.Document({ creator: "Cardboard Colin sign maker", title: L.lines.join(" "),
        background: { color: state.bg.replace("#", "") }, sections });
      save(await D.Packer.toBlob(doc), "docx");
    },
    async print(L) {
      const sheet = $("#print-sheet");
      sheet.innerHTML = svgString(L, { forPrint: true });
      let st = $("#print-page-style");
      if (!st) { st = document.createElement("style"); st.id = "print-page-style"; document.head.appendChild(st); }
      st.textContent = state.page === "free" ? "@page { margin: 0.5in; }"
        : `@page { size: ${PAGE_CSS[state.page]} ${state.orient}; margin: 0; }`;
      document.body.classList.add("printing-sign");
      document.body.classList.toggle("print-free", state.page === "free");
      document.body.classList.toggle("print-page", state.page !== "free");
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
  // expose for testing / power users
  window.cardboardSign = { state, render, layout: async () => layout(await loadFont(state.weight)), exporters };

  if (window.matchMedia("(max-width: 760px)").matches) { state.orient = "landscape"; }
  render();
})();
