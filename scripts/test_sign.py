import asyncio, sys, os
from playwright.async_api import async_playwright
OUT = sys.argv[2] if len(sys.argv) > 2 else "/workspace/cardboard-colin-screens/sign-tests"; os.makedirs(OUT, exist_ok=True)
URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765/"
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        ctx = await b.new_context(accept_downloads=True, viewport={"width": 1280, "height": 900})
        pg = await ctx.new_page()
        errs = []
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.goto(URL); await pg.wait_for_selector("#preview svg")
        await pg.click('.swatch[title="Cardboard"]'); await pg.click('[data-w="Bold"]')
        await pg.wait_for_timeout(500)
        await pg.locator("#try").screenshot(path=f"{OUT}/section-desktop.png")
        for kind, ext in [("pdf","pdf"),("png","png"),("svg","svg"),("docx","docx")]:
            async with pg.expect_download() as dl:
                await pg.click(f'[data-export="{kind}"]')
            d = await dl.value; path = f"{OUT}/sign.{ext}"; await d.save_as(path)
            print(kind, os.path.getsize(path), d.suggested_filename)
        # free size + red, png & pdf
        await pg.select_option("#page", "free"); await pg.click('.swatch[title="Red on white"]')
        await pg.fill("#signtext", "WET PAINT!"); await pg.wait_for_timeout(400)
        async with pg.expect_download() as dl: await pg.click('[data-export="pdf"]')
        await (await dl.value).save_as(f"{OUT}/sign-free.pdf")
        async with pg.expect_download() as dl: await pg.click('[data-export="docx"]')
        await (await dl.value).save_as(f"{OUT}/sign-free.docx")
        # print: A4 portrait, dark
        await pg.select_option("#page", "a4"); await pg.click('[data-o="portrait"]'); await pg.click('.swatch[title="Dark"]')
        await pg.fill("#signtext", "Back in\n5 minutes"); await pg.wait_for_timeout(400)
        await pg.evaluate("window.print = () => {}")
        await pg.click('[data-export="print"]')
        await pg.emulate_media(media="print")
        await pg.pdf(path=f"{OUT}/print-a4.pdf", prefer_css_page_size=True, print_background=True)
        await pg.emulate_media(media="screen")
        # mobile
        m = await b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, accept_downloads=True)
        mp = await m.new_page(); await mp.goto(URL); await mp.wait_for_selector("#preview svg"); await mp.wait_for_timeout(500)
        await mp.locator("#try").screenshot(path=f"{OUT}/section-mobile.png")
        async with mp.expect_download() as dl: await mp.click('[data-export="png"]')
        await (await dl.value).save_as(f"{OUT}/sign-mobile.png")
        print("errors:", errs)
        await b.close()
asyncio.run(main())
