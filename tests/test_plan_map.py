"""Synthetic browser regressions; no personal saves or network requests required.
Run: python tests/test_plan_map.py (requires playwright and Chromium).
"""
import functools
import http.server
import json
import os
import re
from pathlib import Path
import threading
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    def cache(code, name, kind, lat, lon):
        return dict(code=code, name=name, type=kind, lat=lat, lon=lon,
                    coords=f'{lat}, {lon}' if lat is not None else '',
                    description="A synthetic cache description", questions=[], stages=[],
                    images=[], policy=[], waypoints=[], links=[])
    return dict(v=2, caches={c['code']: c for c in [
        cache('GCONE', 'River walk', 'Virtual', 38.90, -77.02),
        cache('GCTWO', 'Hill puzzle', 'Multi', 38.92, -77.05),
        cache('GCLOOSE', 'Unlisted earth', 'EarthCache', 38.88, -77.07),
        cache('GCDONE', 'Completed cache', 'Traditional', 38.89, -77.04),
        cache('GCOTHER', 'Another list', 'Multi', 38.87, -77.01),
        cache('GCMISSING', 'No location', 'Virtual', None, None)]},
        trips=[dict(id='walk', name='Weekend walk', emoji='🥾', codes=['GCONE', 'GCTWO']),
               dict(id='other', name='Other trip', emoji='🌳', codes=['GCOTHER'])],
        prog={'GCTWO': {'notes': 'Started this one'}, 'GCDONE': {'logged': True}},
        # An existing Field trip must not override the new Plan default.
        ui={'tab': 'plan', 'scope': {'k': 'trip', 'id': 'other'}, 'mapProvider': 'off',
            'lastExport': 9999999999999})


class QuietServer(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def marker(page, code):
    return page.locator(f'#map [data-act="mapmark"][data-code="{code}"]')


def click_marker(page, code, touch):
    node = marker(page, code)
    node.scroll_into_view_if_needed()
    node.tap() if touch else node.click()


def map_codes(page):
    return set(page.locator('#map [data-act="mapmark"]').evaluate_all('(els)=>els.map(e=>e.dataset.code)'))


def state(page):
    return page.evaluate("JSON.parse(localStorage.getItem('gfs2'))")


def select_trip(page, value):
    page.locator('#planscope').select_option(value)


def run_flow(browser, origin, touch):
    context = browser.new_context(viewport={'width': 390 if touch else 1280, 'height': 844},
                                  is_mobile=touch, has_touch=touch, reduced_motion='reduce')
    page = context.new_page()
    page.set_default_timeout(8000)
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    context.route('**/*', lambda route: route.continue_() if route.request.url.startswith(origin) else route.abort())
    page.goto(origin)
    page.evaluate('(data)=>localStorage.setItem("gfs2",JSON.stringify(data))', fixture())
    page.reload()
    expect(page.locator('#planscope')).to_have_value('all')
    assert map_codes(page) == {'GCONE', 'GCTWO', 'GCLOOSE', 'GCOTHER'}
    assert page.locator('#map polyline').count() == 0
    assert page.locator('#map text:not([data-list-icon])').count() == 0
    expect(marker(page, 'GCTWO').locator('[data-progress="half"]')).to_have_count(1)
    expect(marker(page, 'GCOTHER').locator('[data-list-icon]')).to_have_text('🌳')
    expect(marker(page, 'GCTWO').locator('[data-list-icon]')).to_have_text('🥾')
    expect(marker(page, 'GCONE').locator('[data-progress]')).to_have_count(0)
    expect(page.locator('#tilenote')).to_contain_text('1 cache has no coordinates')
    expect(page.locator('.mapgesture')).to_have_count(0)
    fit = page.get_by_role('button', name='Fit all caches', exact=True)
    assert fit.inner_text() == ''
    fit_box, map_box = fit.bounding_box(), page.locator('#map').bounding_box()
    assert fit_box['x'] > map_box['x'] + map_box['width'] / 2
    assert fit_box['y'] > map_box['y'] + map_box['height'] / 2
    assert page.locator('body').evaluate('(el)=>el.scrollWidth<=innerWidth')
    # Auto-fit leaves room for the corner control so it does not cover a cache icon.
    assert page.locator('#map [data-act="mapmark"]').evaluate_all('''(els)=>{
        const b=document.querySelector('.mapfit').getBoundingClientRect();
        return els.every(el=>{const r=el.getBoundingClientRect();
            return r.right<=b.left || r.left>=b.right || r.bottom<=b.top || r.top>=b.bottom;});
    }''')
    click_marker(page, 'GCLOOSE', touch)
    if touch:
        page.evaluate("document.documentElement.dataset.theme='dark'")
        page.screenshot(path='/tmp/geocache-overview-dark.png', full_page=True)
        page.evaluate("document.documentElement.dataset.theme='light'")
    expect(page.locator('#t-plan')).to_have_class('on')
    expect(page.locator('#cap')).to_contain_text('Unlisted earth')
    expect(page.locator('#cap')).to_contain_text('GCLOOSE')
    expect(page.locator('[data-act="mapfirst"]')).to_have_count(0)
    expect(page.locator('#map-list-picker')).to_be_hidden()
    page.get_by_role('button', name='Add to list', exact=True).click()
    expect(page.locator('#map-list-picker')).to_be_visible()
    page.locator('#map-list-picker').select_option('walk')
    assert 'GCLOOSE' in state(page)['trips'][0]['codes']
    expect(page.locator('#planscope')).to_have_value('all')
    expect(marker(page, 'GCLOOSE').locator('[data-list-icon]')).to_have_text('🥾')
    # Single-cache mode persists across rerenders, edits, progress, tabs and reload.
    page.get_by_role('button', name='View cache details', exact=True).click()
    expect(page.locator('#chips')).to_have_text('Single cache view')
    expect(page.locator('article.card')).to_have_count(1)
    expect(page.locator('#card-GCLOOSE .num')).not_to_have_text('1')
    page.get_by_role('button', name='Sync, import and export').click()
    page.locator('#t-field').click()
    expect(page.locator('#card-GCLOOSE')).to_be_visible()
    page.locator('#card-GCLOOSE details.menu summary').click()
    page.get_by_role('button', name='Edit details', exact=True).click()
    page.locator('#ed-name').fill('Unlisted earth edited')
    page.get_by_role('button', name='Save', exact=True).click()
    expect(page.locator('#card-GCLOOSE h2')).to_have_text('Unlisted earth edited')
    page.reload()
    expect(page.locator('#chips')).to_have_text('Single cache view')
    expect(page.locator('#card-GCLOOSE h2')).to_have_text('Unlisted earth edited')
    sent = page.locator('[data-act="field-progress"][data-step="sent"]')
    if sent.count():
        sent.click()
    page.locator('[data-act="field-progress"][data-step="logged"]').click()
    expect(page.locator('#card-GCLOOSE')).to_have_class(re.compile('done'))
    page.reload()
    expect(page.locator('#chips')).to_have_text('Single cache view')
    expect(page.locator('#card-GCLOOSE')).to_have_count(1)
    # List browsing shows exactly that route, including completed members.
    page.locator('#t-plan').click()
    assert 'GCLOOSE' not in map_codes(page)
    select_trip(page, 'trip:walk')
    assert map_codes(page) == {'GCONE', 'GCTWO', 'GCLOOSE'}, (map_codes(page), state(page)['trips'])
    expect(page.locator('h3', has_text='Not in a list')).to_have_count(1)
    expect(page.locator('[data-plan-kind="out"][data-plan-code="GCDONE"]')).to_have_count(1)
    assert page.locator('#map polyline').count() == 1
    click_marker(page, 'GCTWO', touch)
    expect(page.locator('#t-plan')).to_have_class('on')
    expect(page.locator('[data-act="mapfirst"]')).to_be_visible()
    expect(page.locator('[data-act="map-add-list"]')).to_have_count(0)
    page.get_by_role('button', name='View cache details', exact=True).click()
    expect(page.locator('#chips button')).to_have_count(3)
    expect(page.locator('#chips button.ok')).to_have_count(1)
    expect(page.locator('#card-GCTWO .num')).to_have_text('2')
    page.locator('#t-plan').click()
    # Move-to-top still requires confirmation.
    click_marker(page, 'GCTWO', touch)
    page.locator('[data-act="mapfirst"]').click()
    assert state(page)['trips'][0]['codes'][0] == 'GCONE'
    page.locator('[data-act="mapfirst"]').click()
    assert state(page)['trips'][0]['codes'][0] == 'GCTWO'
    # Remove from route requires two taps and keeps the saved cache and progress.
    remove = page.locator('[data-plan-kind="in"][data-plan-code="GCONE"] [data-act="toggleSel"]')
    remove.click()
    assert 'GCONE' in state(page)['trips'][0]['codes']
    expect(remove).to_have_text('Tap again')
    remove.click()
    assert 'GCONE' not in state(page)['trips'][0]['codes']
    assert 'GCONE' in state(page)['caches']
    expect(page.locator('[data-plan-kind="out"][data-plan-code="GCONE"]')).to_have_count(1)
    page.get_by_role('button', name='Undo last action', exact=True).click()
    assert 'GCONE' in state(page)['trips'][0]['codes']
    remove.click()
    remove.click()
    assert 'GCONE' not in state(page)['trips'][0]['codes']
    # Re-add below the map; existing drag reorder still works.
    page.locator('[data-plan-kind="out"][data-plan-code="GCONE"] [data-act="toggleSel"]').click()
    assert state(page)['trips'][0]['codes'][-1] == 'GCONE'
    handle = page.locator('[data-drag="GCONE"]')
    handle.scroll_into_view_if_needed()
    start = handle.bounding_box()
    target = page.locator('[data-plan-kind="in"][data-plan-code="GCTWO"]').bounding_box()
    page.mouse.move(start['x']+10, start['y']+10)
    page.mouse.down()
    page.mouse.move(target['x']+20, target['y']+5, steps=8)
    page.mouse.up()
    assert state(page)['trips'][0]['codes'][0] == 'GCONE'
    # Expired removal confirmation needs a fresh pair of taps.
    remove = page.locator('[data-plan-kind="in"][data-plan-code="GCONE"] [data-act="toggleSel"]')
    remove.click()
    expect(remove).to_have_text('✕', timeout=5000)
    remove.click()
    assert 'GCONE' in state(page)['trips'][0]['codes']
    # The newly armed removal cannot carry into a new scope.
    select_trip(page, 'all')
    select_trip(page, 'trip:walk')
    remove.click()
    assert 'GCONE' in state(page)['trips'][0]['codes']
    # Wheel zoom, drag/pan, fit and keyboard selection must remain in Plan.
    page.locator('#map').scroll_into_view_if_needed()
    before = page.locator('#map').get_attribute('viewBox')
    box = page.locator('#map').bounding_box()
    page.mouse.move(box['x']+box['width']/2, box['y']+box['height']/2)
    page.mouse.wheel(0, -240)
    expect(page.locator('#map')).not_to_have_attribute('viewBox', before)
    page.get_by_role('button', name='Fit all caches', exact=True).click()
    expect(page.locator('#map')).to_have_attribute('viewBox', before)
    box = page.locator('#map').bounding_box()
    x, y = box['x']+box['width']/2, box['y']+box['height']/2
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x+45, y+30, steps=8)
    page.mouse.up()
    expect(page.locator('#map')).not_to_have_attribute('viewBox', before)
    expect(page.locator('#t-plan')).to_have_class('on')
    page.get_by_role('button', name='Fit all caches', exact=True).click()
    if touch:
        client = context.new_cdp_session(page)
        def send(kind, points):
            client.send('Input.dispatchTouchEvent', {'type': kind, 'touchPoints': points})
        def points(distance):
            return [{'x': x-distance, 'y': y, 'id': 1}, {'x': x+distance, 'y': y, 'id': 2}]
        send('touchStart', points(35))
        send('touchMove', points(65))
        send('touchEnd', [])
        expect(page.locator('#map')).not_to_have_attribute('viewBox', before)
        expect(page.locator('#t-plan')).to_have_class('on')
        page.get_by_role('button', name='Fit all caches', exact=True).click()
        expect(page.locator('#map')).to_have_attribute('viewBox', before)
        client.detach()
    marker(page, 'GCTWO').focus()
    page.keyboard.press('Enter')
    expect(page.locator('#cap')).to_contain_text('Hill puzzle')
    expect(page.locator('#t-plan')).to_have_class('on')
    assert not errors, errors
    page.screenshot(path=f'/tmp/geocache-plan-{"mobile" if touch else "desktop"}.png', full_page=True)
    context.close()


def run_edges(browser, origin):
    context = browser.new_context(reduced_motion='reduce')
    page = context.new_page()
    page.goto(origin)
    data = fixture()
    data['trips'] = []
    page.evaluate('(data)=>localStorage.setItem("gfs2",JSON.stringify(data))', data)
    page.reload()
    click_marker(page, 'GCONE', False)
    page.get_by_role('button', name='Add to list', exact=True).click()
    expect(page.locator('#map-no-lists')).to_be_visible()
    assert state(page)['trips'] == []
    # Completed-only and coordinate-less libraries give accurate empty states.
    page.evaluate("Object.keys(DB.caches).forEach(c=>PR(c).logged=true); renderPlan()")
    expect(page.locator('.mapwrap')).to_contain_text('All saved caches are complete')
    page.evaluate("DB.trips=[{id:'empty',name:'Empty',codes:[]}]; UI.planScope={k:'trip',id:'empty'};renderPlan()")
    expect(page.locator('.mapwrap')).to_contain_text('This list has no caches yet')
    page.evaluate("DB.trips[0].codes=['GCMISSING'];renderPlan()")
    expect(page.locator('.mapwrap')).to_contain_text('None of these caches has coordinates')
    expect(page.locator('[data-plan-kind="in"][data-plan-code="GCMISSING"]')).to_have_count(1)
    context.close()


if __name__ == '__main__':
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietServer, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}/'
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=os.getenv('CHROMIUM_PATH', '/usr/bin/chromium'), args=['--no-sandbox'])
            for touch in (False, True):
                run_flow(browser, origin, touch)
                print(f'{"Mobile" if touch else "Desktop"} map and field flow passed')
            run_edges(browser, origin)
            print('Empty, completed-only, no-list and missing-coordinate cases passed')
            browser.close()
    finally:
        server.shutdown()
