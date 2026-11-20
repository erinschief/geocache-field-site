"""Synthetic completion, disclosure persistence and sequential scrolling checks.
Run: python tests/test_stage_completion.py (requires Playwright and Chromium).
"""
import functools
import http.server
import os
import threading
from playwright.sync_api import sync_playwright, expect
from test_plan_map import ROOT, QuietServer, fixture


def run(browser, origin, width):
    context = browser.new_context(viewport={'width': width, 'height': 844}, reduced_motion='reduce')
    context.route('**/*', lambda r: r.continue_() if r.request.url.startswith(origin) else r.abort())
    page = context.new_page()
    data = fixture()
    data['ui'].update(tab='field', fieldCache='GCTWO')
    data['caches']['GCTWO']['stages'] = [dict(
        id=f's{i}', title=f'Stage {i}', desc='Stage instructions.\n\n' * 35,
        inputs=[dict(l='Observed value', kind='text')], choices=[])
        for i in range(1, 4)]
    data['prog']['GCTWO']['st'] = {'s2': {'in': {'0': 'Already answered'}, 'done': True}}
    page.goto(origin)
    page.evaluate('(d)=>localStorage.setItem("gfs2", JSON.stringify(d))', data)
    page.reload()
    def checkbox(i):
        return page.locator(f'[data-sdone="GCTWO|s{i}"]')
    def stage(i):
        return checkbox(i).locator('xpath=ancestor::details[1]')
    # Missing answers must not advance or close a stage.
    checkbox(1).evaluate('(el)=>{el.checked=true;el.dispatchEvent(new Event("change",{bubbles:true}));}')
    expect(checkbox(1)).not_to_be_checked()
    expect(stage(1)).to_have_attribute('open', '')
    page.locator('[data-sin="GCTWO|s1|0"]').fill('Answer')
    checkbox(1).check(force=True)
    expect(stage(1)).not_to_have_attribute('open', '', timeout=5000)
    # The sequential stage opens even if it was completed previously.
    expect(stage(2)).to_have_attribute('open', '')
    page.wait_for_function('''()=>{const s=document.querySelector('[data-sdone="GCTWO|s2"]').closest('.stage');return Math.abs(s.getBoundingClientRect().top-document.querySelector('header').getBoundingClientRect().bottom-8)<2}''')
    page.reload()
    expect(stage(1)).not_to_have_attribute('open', '')
    expect(stage(2)).to_have_attribute('open', '')
    # Reopening completion does not navigate away.
    checkbox(2).uncheck(force=True)
    expect(stage(2)).to_have_attribute('open', '')
    checkbox(2).check(force=True)
    expect(stage(2)).not_to_have_attribute('open', '', timeout=5000)
    expect(stage(3)).to_have_attribute('open', '')
    page.locator('[data-sin="GCTWO|s3|0"]').fill('Last answer')
    checkbox(3).check(force=True)
    expect(stage(3)).not_to_have_attribute('open', '', timeout=5000)
    page.reload()
    for i in (1, 2, 3):
        expect(checkbox(i)).to_be_checked()
        expect(stage(i)).not_to_have_attribute('open', '')
    # Station-stage completion uses the same transition after its reordered redraw.
    metro = fixture()
    metro['caches'] = {'GCBJ756': dict(metro['caches']['GCONE'], code='GCBJ756', name='Metro Grand Tour')}
    metro['prog'] = {}
    metro['trips'] = []
    metro['ui'].update(tab='field', fieldCache='GCBJ756')
    page.evaluate('(d)=>localStorage.setItem("gfs2",JSON.stringify(d))', metro)
    page.reload()
    first = page.locator('#metro-station-0')
    first.locator(':scope > summary').click()
    first.locator('[data-metro-bubble] input').check(force=True)
    expect(page.locator('#metro-station-0')).not_to_have_attribute('open', '', timeout=5000)
    expect(page.locator('#metro-station-1')).to_have_attribute('open', '')
    page.reload()
    expect(page.locator('#metro-station-0')).not_to_have_attribute('open', '')
    expect(page.locator('#metro-station-1')).to_have_attribute('open', '')
    context.close()
    print(f'{width}px: completion guard, sequential advance, header offset, reopen and saved disclosures passed')


if __name__ == '__main__':
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietServer, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH', '/usr/bin/chromium'), args=['--no-sandbox'])
            for width in (390, 1280):
                run(browser, f'http://127.0.0.1:{server.server_port}', width)
            browser.close()
    finally:
        server.shutdown()
