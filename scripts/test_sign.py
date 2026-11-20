"""Headless test of the sign maker: editing, drag-resizing (mouse and touch),
auto-fit / manual size, presets, and every export.
python scripts/test_sign.py <URL> <OUTDIR>"""
import sys, os, json, asyncio
from playwright.async_api import async_playwright

URL, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
results = {}

async def state(pg):
    return await pg.evaluate("({W: cardboardSign.state.W, H: cardboardSign.state.H, scale: cardboardSign.scale})")

async def drag(pg, sel, dx, dy, touch=False):
    box = await pg.locator(sel).bounding_box()
    x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    if not touch:
        await pg.mouse.move(x, y); await pg.mouse.down()
        for i in range(1, 11):
            await pg.mouse.move(x + dx * i / 10, y + dy * i / 10)
        await pg.mouse.up()
    else:   # synthesise touch pointer events (what a finger drag sends)
        await pg.evaluate("""([sel, x, y, dx, dy]) => {
          const h = document.querySelector(sel);
          const ev = (t, cx, cy) => h.dispatchEvent(new PointerEvent(t, {bubbles: true, pointerId: 7, pointerType: 'touch', isPrimary: true, clientX: cx, clientY: cy, buttons: 1}));
          h.setPointerCapture = () => {}; h.hasPointerCapture = () => true;
          ev('pointerdown', x, y);
          for (let i = 1; i <= 10; i++) ev('pointermove', x + dx * i / 10, y + dy * i / 10);
          ev('pointerup', x + dx, y + dy);
        }""", [sel, x, y, dx, dy])
    await pg.wait_for_timeout(400)

async def download(pg, kind, name):
    async with pg.expect_download() as d:
        await pg.click(f'[data-export="{kind}"]')
    dl = await d.value
    path = os.path.join(OUT, name); await dl.save_as(path)
    return os.path.getsize(path)

async def run():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome")
        # ---------------- desktop
        ctx = await b.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
        pg = await ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.goto(URL); await pg.wait_for_function("window.cardboardSign && document.fonts.status==='loaded'")
        await pg.locator("#try").scroll_into_view_if_needed(); await pg.wait_for_timeout(800)
        s0 = await state(pg); fs0 = await pg.evaluate("parseFloat(getComputedStyle(sign).fontSize)")
        # edit the sign directly
        await pg.click("#sign"); await pg.keyboard.press("Control+A"); await pg.keyboard.type("GARAGE SALE\nSaturday 9-2")
        await pg.wait_for_timeout(300)
        txt = await pg.evaluate("cardboardSign.state.text")
        # drag the east edge inward (narrower) and the south-east corner
        await drag(pg, '.h[data-h="e"]', -180, 0)
        s1 = await state(pg); L1 = await pg.evaluate("cardboardSign.layout().then(L => ({size: L.size, lines: L.lines}))")
        await pg.locator("#stage").screenshot(path=f"{OUT}/desktop-after-drag-e.png")
        await drag(pg, '.h[data-h="se"]', -120, 160)
        s2 = await state(pg); L2 = await pg.evaluate("cardboardSign.layout().then(L => ({size: L.size, lines: L.lines}))")
        await pg.locator("#stage").screenshot(path=f"{OUT}/desktop-after-drag-se.png")
        dims = await pg.text_content("#dimsout")
        # manual size: text reflows (wraps) when the sign is narrowed
        await pg.uncheck("#autofit"); await pg.fill("#size", "140"); await pg.dispatch_event("#size", "input")
        await drag(pg, '.h[data-h="w"]', 120, 0)
        L3 = await pg.evaluate("cardboardSign.layout().then(L => ({size: L.size, lines: L.lines}))")
        await pg.locator("#stage").screenshot(path=f"{OUT}/desktop-manual-size.png")
        await pg.check("#autofit")
        # presets snap, rotate, typed dimensions
        await pg.click('[data-preset="banner"]'); sb = await state(pg)
        await pg.click('#rotate'); sr = await state(pg)
        await pg.fill("#win", "18"); await pg.fill("#hin", "12"); await pg.press("#hin", "Enter"); await pg.wait_for_timeout(300)
        st = await state(pg)
        # keyboard resize
        await pg.focus('.h[data-h="se"]'); await pg.keyboard.press("ArrowRight"); sk = await state(pg)
        results["desktop"] = dict(start=s0, start_font_px=fs0, text=txt, after_e=s1, layout_e=L1, after_se=s2, layout_se=L2,
                                  dims_label=dims, manual_after_w=L3, banner=sb, rotated=sr, typed=st, key=sk)
        # exports at the custom 18.25 x 12 in cardboard size
        await pg.click('.swatch[title="Cardboard"]'); await pg.click('[data-w="Bold"]')
        await pg.locator("#try").screenshot(path=f"{OUT}/desktop-try.png")
        sizes = {}
        for k, ext in (("pdf", "pdf"), ("png", "png"), ("svg", "svg"), ("docx", "docx")):
            sizes[k] = await download(pg, k, f"custom.{ext}")
        await pg.select_option("#paper", "letter")
        sizes["pdf_letter"] = await download(pg, "pdf", "custom-on-letter.pdf")
        sizes["docx_letter"] = await download(pg, "docx", "custom-on-letter.docx")
        await pg.click('.swatch[title="Red on white"]')
        await pg.select_option("#paper", "sign"); await pg.click('[data-preset="a4"]'); await pg.click("#rotate")
        await pg.click("#sign"); await pg.keyboard.press("Control+A"); await pg.keyboard.type("WET PAINT!")
        sizes["pdf_a4_red"] = await download(pg, "pdf", "a4-portrait-red.pdf")
        # print: emulate print media and save as PDF to check the @page size
        await pg.click('.swatch[title="Cardboard"]')
        await pg.evaluate("""() => { window.print = () => {}; return cardboardSign.layout().then(L => cardboardSign.exporters.print(L)); }""")
        await pg.emulate_media(media="print")
        await pg.pdf(path=f"{OUT}/print-a4-portrait.pdf", prefer_css_page_size=True, print_background=True)
        await pg.emulate_media(media="screen")
        results["desktop_exports"] = sizes
        results["desktop_errors"] = errs
        await ctx.close()
        # ---------------- mobile (touch)
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True, accept_downloads=True)
        pg = await ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.goto(URL); await pg.wait_for_function("window.cardboardSign && document.fonts.status==='loaded'")
        await pg.locator("#try").scroll_into_view_if_needed(); await pg.wait_for_timeout(800)
        m0 = await state(pg)
        await pg.locator("#try").screenshot(path=f"{OUT}/mobile-try.png")
        await drag(pg, '.h[data-h="s"]', 0, 120, touch=True)
        m1 = await state(pg)
        await drag(pg, '.h[data-h="nw"]', 40, 0, touch=True)
        m2 = await state(pg); Lm = await pg.evaluate("cardboardSign.layout().then(L => ({size: L.size, lines: L.lines}))")
        await pg.locator("#stage").screenshot(path=f"{OUT}/mobile-after-touch-drag.png")
        overflow = await pg.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        msz = await download(pg, "pdf", "mobile.pdf")
        results["mobile"] = dict(start=m0, after_s=m1, after_nw=m2, layout=Lm, horizontal_overflow_px=overflow, pdf_bytes=msz, errors=errs)
        await pg.screenshot(path=f"{OUT}/mobile-full.png", full_page=True)
        await ctx.close(); await b.close()
    json.dump(results, open(f"{OUT}/results.json", "w"), indent=1)
    print(json.dumps(results, indent=1))

asyncio.run(run())
