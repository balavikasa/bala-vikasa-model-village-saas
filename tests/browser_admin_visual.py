"""Read-only mobile/desktop render check with local API fixtures; no production backend."""
from __future__ import annotations
import asyncio
from playwright.async_api import async_playwright
from browser_admin_master_data import ROOT, SCRIPT, html

async def main():
    out = ROOT.parent / 'qa_master_data'
    out.mkdir(exist_ok=True)
    async with async_playwright() as play:
        browser = await play.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        for width,height in [(1448,900),(768,960),(390,844)]:
            page = await browser.new_page(viewport={'width':width,'height':height}, device_scale_factor=1)
            markup = html().replace('<body>','<body class="mv-reference">')
            await page.set_content(markup)
            for style in ['app.css','reference-ui.css','admin-master.css']:
                await page.add_style_tag(path=str(ROOT/'app/static/css'/style))
            await page.add_script_tag(content=SCRIPT)
            await page.add_script_tag(path=str(ROOT/'app/static/js/admin.js'))
            await page.wait_for_function("document.querySelector('#admin-resource').options.length > 0")
            await page.select_option('#admin-resource','das')
            await page.click('#admin-add')
            await page.check('#admin-create-login')
            await page.screenshot(path=str(out/f'admin-add-da-{width}.png'),full_page=True)
            # Modal must remain completely within viewport; horizontal scroll is not acceptable.
            box = await page.locator('#admin-dialog').bounding_box()
            assert box and box['x']>=0 and box['x']+box['width']<=width+1,(width,box)
            assert await page.locator('#admin-provision-email').is_visible()
            print(f'PASS responsive dialog at {width}px, bounds={box["width"]:.0f}px')
            await page.close()
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
