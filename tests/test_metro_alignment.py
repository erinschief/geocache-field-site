"""Check all 16 checkbox centers against reviewed station centers in the bitmap.
Run: python tests/test_metro_alignment.py (Playwright, Chromium and Pillow).
"""
import base64
import functools
import http.server
import io
import os
from pathlib import Path
import re
import threading
from PIL import Image
from playwright.sync_api import sync_playwright
from test_plan_map import QuietServer, fixture

ROOT = Path(__file__).resolve().parents[1]
# Independently reviewed native-image coordinates, in METRO_STATIONS listing order.
BITMAP_CENTERS = [(914.61,1109.88),(818.32,955.40),(1157.39,1079.99),
                  (952.37,635.38),(952.42,592.58),(952.35,549.63),
                  (1185.26,721.73),(978.88,867.50),(1019.39,1109.88),
                  (1019.31,1247.40),(1502.38,1037.93),(626.56,1112.86),
                  (876.56,1574.15),(876.62,1607.36),(889.14,1801.61),
                  (114.29,891.28)]


def verify(page):
    image = page.locator('.metro-map-art>img').bounding_box()
    centers = page.locator('.metro-map-pin input').evaluate_all('''inputs=>inputs.map(input=>{
        const r=input.getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2];
    })''')
    assert len(centers) == len(BITMAP_CENTERS)
    for i, ((x, y), (expected_x, expected_y)) in enumerate(zip(centers, BITMAP_CENTERS)):
        native_x = (x-image['x'])/image['width']*1728
        native_y = (y-image['y'])/image['height']*2100
        assert abs(native_x-expected_x)<1 and abs(native_y-expected_y)<1, (i,native_x,native_y)


def run(browser, origin, mobile):
    context=browser.new_context(viewport={'width':390 if mobile else 1280,'height':844},
                                is_mobile=mobile,has_touch=mobile,reduced_motion='reduce')
    page=context.new_page()
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(origin)
    data=fixture()
    cache=dict(data['caches']['GCONE'],code='GCBJ756',name='Metro Grand Tour')
    data['caches']={'GCBJ756':cache}
    data['trips']=[]
    data['prog']={}
    data['ui'].update(tab='field',fieldCache='GCBJ756')
    page.evaluate('(data)=>localStorage.setItem("gfs2",JSON.stringify(data))',data)
    page.reload()
    page.get_by_role('button',name='Metro Grand Tour map · 0/16').click()
    page.locator('.sheet-ready').wait_for()
    page.wait_for_function("document.querySelector('.metro-map-art img')?.complete")
    verify(page)
    page.locator('.metro-viewport').focus()
    for key in ['+','+','ArrowLeft','ArrowUp']:
        page.keyboard.press(key)
    verify(page)
    page.evaluate("METRO_STATIONS.forEach((s,i)=>{const p=PR(METRO_CODE);p.st['metro'+(i+1)]={done:true,in:{}};});metroRefreshStationViews()")
    verify(page)  # Completion-order badges must not shift checkbox centers.
    page.set_viewport_size({'width':430 if mobile else 1024,'height':932})
    page.wait_for_timeout(100)
    verify(page)
    assert not errors,errors
    context.close()


if __name__=='__main__':
    source=(ROOT/'index.html').read_text()
    encoded=re.search("const METRO_MAP = 'data:image/jpeg;base64,([^']+)'",source)[1]
    bitmap=Image.open(io.BytesIO(base64.b64decode(encoded))).convert('RGB')
    assert bitmap.size==(1728,2100)
    for x,y in BITMAP_CENTERS:
        assert min(bitmap.getpixel((round(x),round(y))))>225
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietServer,directory=str(ROOT)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=os.getenv('CHROMIUM_PATH','/usr/bin/chromium'),args=['--no-sandbox'])
            for mobile in [False,True]:
                run(browser,f'http://127.0.0.1:{server.server_port}/',mobile)
                print(('Mobile' if mobile else 'Desktop')+': all 16 checkbox centers aligned at fit, zoom/pan, completion and resize')
            browser.close()
    finally:
        server.shutdown()
