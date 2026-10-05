#!/usr/bin/env python3
"""UI regression review: isolated storage and mocked APIs; no real model calls."""
import argparse
import json
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

PAPER = {
    'topic': 'Urban gardening for small balconies',
    'overview': 'Balcony gardens thrive with careful water and shade planning.',
    'themes': [{'title': 'Water and shade', 'summary': 'Containers need regular watering and shelter from intense midday sun.', 'article_ids': ['garden-1']}],
    'articles': [{'id': 'garden-1', 'headline': 'Container gardens make small spaces productive',
        'publisher': 'Community Garden Review', 'section': 'Practical gardening',
        'summary': 'Choose containers with drainage and plants suited to the available sunlight. ' * 5,
        'why_it_matters': 'Small spaces can support useful, accessible gardens.',
        'source_text': 'Plants in containers need drainage, regular watering, and suitable sunlight.',
        'read_note': 'Retrieved publisher text with a reading limitation.', 'read_status': 'Full article read', 'link': 'https://example.com/gardening', 'date': '2026-10-01'},
        {'id': 'garden-2', 'headline': 'A balcony herb garden can thrive in partial shade', 'publisher': 'City Horticulture', 'section': 'Plant choices', 'summary': 'Basil, parsley, and mint tolerate limited direct sunlight when watered consistently.', 'why_it_matters': 'The right plant choices make a shaded balcony useful.', 'read_kind': 'article', 'link': 'https://example.com/herbs', 'date': '2026-09-30'},
        {'id': 'garden-3', 'headline': 'Planters need safe drainage for apartment gardens', 'publisher': 'Home Growers', 'section': 'Watering', 'summary': 'Drainage trays protect neighbors and building surfaces from runoff.', 'why_it_matters': 'Simple precautions help keep community gardening welcome.', 'read_kind': 'excerpt', 'link': 'https://example.com/drainage', 'date': '2026-09-29'}],
    'research_coverage': {'requested': 4, 'screened': 23, 'attempted': 9, 'stop_reason': 'no_new_queries'},
    'feed_errors': []}
# Prepared narration must match news passages, excluding retrieval diagnostics.
_passages = ['The Daily Signal', PAPER['overview']]
for _theme in PAPER['themes']:
    _passages.extend([_theme['title'], _theme['summary']])
for _article in PAPER['articles']:
    _passages.extend([_article['headline'], _article['summary'].strip(), 'Why it matters: ' + _article['why_it_matters']])
_sections = [{'id': str(index), 'text': text} for index, text in enumerate(_passages)]
PAPER['narration'] = {'version': 1, 'sections': _sections,
    'signature': json.dumps(_sections, ensure_ascii=False, separators=(',', ':'))}
ANSWER = '**Start small.** Match plants to the sunlight available.\n\n| Step | Reason |\n| --- | --- |\n| Check drainage | Avoid waterlogging |\n| Measure sunlight | Choose suitable plants |'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8765')
    parser.add_argument('--output-dir', default='/tmp/daily-signal-reader-review')
    parser.add_argument('--chromium-path')
    args = parser.parse_args()
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        options = {'headless': True, 'args': ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage', '--no-proxy-server']}
        if args.chromium_path:
            options['executable_path'] = args.chromium_path
        browser = p.chromium.launch(**options)
        context = browser.new_context(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
        page = context.new_page()
        page.set_default_timeout(10000)
        errors, generated, chats, navigations, state = [], [], [], [], {'job': None, 'polls': 0}
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('framenavigated', lambda frame: navigations.append(frame.url) if frame == page.main_frame else None)

        def api(route):
            path = urlparse(route.request.url).path
            if path == '/api/current':
                payload = {'job': state['job']}
            elif path == '/api/config':
                payload = {'model_configured': True}
            elif path == '/api/generate':
                request = route.request.post_data_json
                generated.append(request)
                state['polls'] = 0
                state['hold'] = len(generated) > 1
                state['job'] = {'id': f'review-{len(generated)}', 'status': 'running',
                    'stage': 'Reading sources', 'detail': 'Review generation in progress', 'percent': 20}
                payload = {'job_id': state['job']['id']}
            elif path == '/api/status':
                state['polls'] += 1
                if state['polls'] >= 3 and not state['hold']:
                    state['job'] = {**state['job'], 'status': 'done', 'result': PAPER,
                        'finished_at': '2026-10-02T12:00:00Z'}
                payload = state['job']
            elif path == '/api/cancel':
                state['job'] = {**state['job'], 'status': 'cancelled', 'detail': 'Cancelled by the review fixture'}
                payload = {'status': 'cancelled'}
            elif path == '/api/explain':
                payload = {'explanation': ANSWER, 'sources_used': []}
            elif path == '/api/chat':
                chats.append(route.request.post_data_json)
                payload = {'reply': ANSWER, 'web_sources': []}
            else:
                route.fulfill(status=400, json={'error': f'Unexpected review API: {path}'})
                return
            route.fulfill(json=payload)

        context.add_init_script('window.reviewSpoken=[];window.speechSynthesis.speak=u=>window.reviewSpoken.push(u);window.speechSynthesis.cancel=()=>{};window.reviewPause=0;window.reviewResume=0;window.speechSynthesis.pause=()=>reviewPause++;window.speechSynthesis.resume=()=>reviewResume++;')
        context.route('**/api/**', api)
        page.goto(args.base_url, wait_until='commit')
        page.wait_for_timeout(500)
        assert not generated, 'Fresh visit started generation without an action'
        assert page.locator('#paper-topic').input_value() == ''
        page.locator('#settings-toggle').click()
        page.locator('#llm-story-count').fill('4')
        page.locator('#llm-search-days').fill('14')
        page.locator('#settings-form button[type=submit]').click()
        page.locator('#paper-topic').fill(PAPER['topic'])
        page.locator('#paper-topic').press('Enter')
        page.wait_for_function('document.querySelector("#paper-topic").disabled')
        assert page.locator('#refresh').is_disabled()
        page.reload(wait_until='commit')
        page.wait_for_function('document.querySelector(".article")')
        assert len(generated) == 1, 'Reload restarted the job'
        assert generated[0]['options'] == {'articleCount': 4, 'searchDays': 14, 'topic': PAPER['topic']}, generated[0]
        page.wait_for_function('document.querySelectorAll(".saved-edition-open").length === 1')
        assert page.locator('.article').count() == 3
        assert page.locator('#briefing-meta').inner_text().lower().startswith('3 / 4 articles')
        assert '3 of 4 requested stories included' in page.locator('#coverage-note').inner_text().lower(), repr(page.locator('#coverage-note').inner_text().lower())
        assert page.locator('#paper-options').inner_text().lower() == 'paper options · up to 4 stories · past 14 days'

        # Let generation completion finish its archive/poll bookkeeping.
        page.wait_for_timeout(1200)
        # Generated and archived narration starts without another model request.
        page.locator('#read-paper').click()
        assert page.evaluate('window.reviewSpoken.length') == 1
        assert page.locator('#read-paper').get_attribute('aria-pressed') == 'true'
        page.evaluate('window.reviewSpoken[0].onstart()')
        assert page.locator('#transcript-previous').is_disabled()
        page.locator('#transcript-pause').click()
        assert page.locator('#transcript-pause').inner_text() == 'Resume'
        assert page.evaluate('window.reviewPause') == 1
        page.locator('#transcript-pause').click()
        assert page.evaluate('window.reviewResume') == 2
        page.locator('#transcript-next').click()
        page.evaluate('window.reviewSpoken.at(-1).onstart()')
        assert page.locator('#transcript-previous').is_enabled()
        page.locator('#transcript-previous').click()
        page.evaluate('window.reviewSpoken.at(-1).onstart()')
        assert page.locator('#transcript-previous').is_disabled()
        page.evaluate('window.staleUtterance=window.reviewSpoken.at(-1)')
        page.evaluate('window.reviewSpoken.at(-1).onboundary({name:"word",charIndex:4,charLength:5})')
        page.locator('#transcript-speed').select_option('1.5')
        assert page.evaluate('window.reviewSpoken.at(-1).rate') == 1.5
        assert page.evaluate('window.reviewSpoken.at(-1).text') == 'Daily Signal'
        count = page.evaluate('window.reviewSpoken.length')
        page.evaluate('window.staleUtterance.onend();window.staleUtterance.onerror({error:"interrupted"})')
        assert page.evaluate('window.reviewSpoken.length') == count
        assert page.locator('#read-paper').get_attribute('aria-pressed') == 'true'
        page.evaluate('window.reviewSpoken.at(-1).onstart()')

        assert page.locator('#transcript-follow').get_attribute('aria-pressed') == 'true'
        page.mouse.wheel(0, 100)
        page.wait_for_function('document.querySelector("#transcript-follow").getAttribute("aria-pressed") === "false"')
        assert page.locator('#transcript-follow').get_attribute('aria-pressed') == 'false'
        page.locator('#transcript-follow').click()
        assert page.locator('#transcript-follow').get_attribute('aria-pressed') == 'true'
        page.keyboard.press('PageDown')
        assert page.locator('#transcript-follow').get_attribute('aria-pressed') == 'false'
        page.locator('#transcript-follow').click()
        page.set_viewport_size({'width': 1440, 'height': 640})
        page.evaluate('window.scrollTo(0,0)')
        page.evaluate('''()=>{while(speechSession.chunks[speechSession.index-1].segment.element!==document.querySelectorAll('.article h3')[2])window.reviewSpoken.at(-1).onend();window.reviewSpoken.at(-1).onstart()}''')
        page.wait_for_timeout(100)
        assert page.evaluate('scrollY') > 0, 'Narrated article did not scroll into view'
        article_y = page.locator('.article h3').nth(2).bounding_box()['y']
        assert 0 <= article_y < page.locator('#narration-transcript').bounding_box()['y'], 'Narrated heading is obscured by the transcript'
        page.set_viewport_size({'width': 1440, 'height': 1000})
        page.mouse.wheel(0, -100)
        page.wait_for_function('document.querySelector("#transcript-follow").getAttribute("aria-pressed") === "false"')
        page.wait_for_timeout(100)
        paused_y = page.evaluate('scrollY')
        page.evaluate('window.reviewSpoken.at(-1).onend();window.reviewSpoken.at(-1).onstart()')
        page.wait_for_timeout(100)
        assert abs(page.evaluate('scrollY') - paused_y) < 2, 'Narration interrupted manual scrolling'
        page.locator('#transcript-follow').click()
        assert page.locator('#transcript-follow').get_attribute('aria-pressed') == 'true'
        # Speed changed while paused takes effect on explicit resumption.
        page.locator('#transcript-pause').click()
        paused_count = page.evaluate('window.reviewSpoken.length')
        page.locator('#transcript-speed').select_option('2')
        assert page.evaluate('window.reviewSpoken.length') == paused_count
        page.locator('#transcript-pause').click()
        assert page.evaluate('window.reviewSpoken.at(-1).rate') == 2
        page.locator('#transcript-speed').select_option('1.5')
        page.locator('#transcript-pause').click()
        # Stop while paused, then restart via the main button after reload.
        page.locator('#read-paper').click()
        page.reload(wait_until='commit')
        page.wait_for_function('document.querySelector(".article")')
        page.wait_for_timeout(1200)
        page.locator('#read-paper').click()
        assert page.evaluate('window.reviewSpoken.length') == 1
        assert page.evaluate('window.reviewSpoken[0].rate') == 1.5
        page.locator('#read-paper').click()

        # Validation must leave the loaded paper intact.
        page.locator('#paper-topic').fill('   ')
        page.locator('#refresh').click()
        assert page.locator('.article').count() == 3
        assert len(generated) == 1
        page.locator('#paper-topic').fill(PAPER['topic'])

        # Closing a settings draft must discard it and restore keyboard focus.
        page.locator('#settings-toggle').click()
        original = page.locator('#llm-search-days').input_value()
        page.locator('#llm-search-days').fill('50')
        page.keyboard.press('Escape')
        assert not page.locator('#settings-popover').is_visible()
        assert page.locator('#settings-toggle').evaluate('e=>e===document.activeElement')
        page.locator('#settings-toggle').click()
        assert page.locator('#llm-search-days').input_value() == original
        page.locator('#settings-close').click()

        # A selection crossing a heading and paragraph becomes a persistent range.
        page.locator('.theme').scroll_into_view_if_needed()
        page.evaluate('''()=>{const card=document.querySelector('.theme'),r=document.createRange();
            r.selectNodeContents(card);getSelection().removeAllRanges();getSelection().addRange(r);
            document.dispatchEvent(new Event('selectionchange'));}''')
        page.locator('.explain-action').click()
        page.wait_for_function('!document.querySelector(".explain-action").disabled')
        assert page.locator('.explain-answer table').count() == 1
        assert page.evaluate('CSS.highlights.get("saved-explanations").size') == 1
        assert page.locator('#saved-explanations-list').is_visible()
        page.locator('#saved-explanations-summary').click()
        saved_explanation = page.locator('.saved-explanation-open').first
        saved_explanation.focus()
        page.keyboard.press('Enter')
        assert page.locator('#explain-popover').is_visible()
        assert page.locator('.explain-close').evaluate('e=>e===document.activeElement')
        page.keyboard.press('Escape')
        assert saved_explanation.evaluate('e=>e===document.activeElement')
        page.keyboard.press('Enter')
        assert page.evaluate('getSelection().isCollapsed')
        assert page.locator('.chat-message').count() == 0
        page.locator('.explain-chat').click()
        assert page.locator('#chat-context').is_visible()
        navigation_count = len(navigations)
        page.evaluate("window.__chatDocumentToken='reader-smoke'")
        page.locator('#chat-input').fill('How should I start?')
        page.locator('#chat-input').press('Enter')
        page.wait_for_function('!document.querySelector("#chat-send").disabled')
        assert len(chats) == 1, 'Enter did not send exactly one chat API request'
        assert len(navigations) == navigation_count, 'Chat submission navigated the document'
        assert page.evaluate("window.__chatDocumentToken==='reader-smoke'"), 'Chat submission reloaded the page'
        assert page.locator('.chat-markdown table').count() == 1
        page.locator('#chat-close').click()
        page.reload(wait_until='commit')
        page.wait_for_function('document.querySelector(".article")')
        assert page.evaluate('CSS.highlights.get("saved-explanations").size') == 1
        assert page.locator('.chat-message').count() == 2

        # Archive indication, edition-scoped explanations/chat, and browser-wide preferences.
        page.evaluate('''async paper=>{const second={id:'edition-two',savedAt:Date.parse('2026-10-01T09:00:00Z'),topic:'Native plants in city parks',page:{...paper,topic:'Native plants in city parks',overview:'Native flowers support pollinators in neighborhood parks.',themes:[{title:'Pollinator plants',summary:'Regional flowers provide food for bees.',article_ids:['native-1']}],articles:[{id:'native-1',headline:'Prairie flowers support urban pollinators',publisher:'Field Notes',section:'Parks',summary:'Native flowers support city bees and butterflies.',link:'https://example.com/native',date:'2026-10-01'}]},ui:{scrollY:0},explanations:[],chat:[]};await editionTransaction('readwrite',store=>store.put(second));await refreshSavedEditionList()}''', PAPER)
        page.locator('#editions-toggle').click()
        assert page.locator('.saved-edition-current').inner_text().lower() == 'currently reading'
        browser_theme = page.locator('#theme-toggle').inner_text()
        page.locator('.saved-edition-open').filter(has_text='Native flowers support pollinators').click()
        assert page.locator('#paper-topic').input_value() == 'Native plants in city parks'
        assert page.locator('#saved-explanations-list').is_hidden()
        assert page.locator('.chat-message').count() == 0
        assert page.locator('#theme-toggle').inner_text() == browser_theme
        page.locator('#editions-toggle').click()
        page.locator('.saved-edition-open').filter(has_text='Balcony gardens thrive').click()
        assert page.locator('#saved-explanations-list').is_visible()
        assert page.locator('.chat-message').count() == 2

        # Keep a second generation pending while the reader switches to an archived paper.
        page.locator('#paper-topic').fill('New topic while another paper is ready')
        page.locator('#refresh').click()
        page.wait_for_function('document.querySelector("#cancel-generation") && !document.querySelector("#cancel-generation").hidden')
        page.locator('#editions-toggle').click()
        page.locator('.saved-edition-open').filter(has_text='Balcony gardens thrive').click()
        assert page.locator('#paper-topic').input_value() == PAPER['topic']
        page.wait_for_timeout(1100)
        assert page.locator('.article').count() == 3, 'Generation progress replaced the selected archive paper'
        page.locator('#editions-toggle').click()
        page.locator('.generation-edition .saved-edition-open').click()
        page.locator('#cancel-generation').click()
        page.wait_for_function('document.querySelector("#status").textContent.toLowerCase().includes("cancel")')
        assert 'cancel' in page.locator('#status').inner_text().lower(), (page.locator('#status').inner_text(), state['job'], page.evaluate('JSON.stringify(activeGeneration)'))
        assert state['job']['status'] == 'cancelled'

        # IndexedDB archive is the recovery source if the smaller localStorage cache is unavailable.
        state['job'] = None
        page.evaluate('localStorage.removeItem(EDITION_KEY)')
        page.reload(wait_until='commit')
        page.wait_for_function('document.querySelectorAll(".article").length === 3')
        assert page.locator('#paper-topic').input_value() == PAPER['topic']

        for _ in range(3):
            page.locator('#font-larger').click()
        for width, height in [(320, 740), (390, 844), (768, 1024), (1440, 1000)]:
            page.set_viewport_size({'width': width, 'height': height})
            page.evaluate('window.scrollTo(0,0)')
            if width <= 520:
                topic = page.locator('#paper-topic')
                topic.fill('a' * 298)
                topic.press('Control+Home')
                topic.press('X')
                topic.press('Control+End')
                topic.press('Y')
                assert topic.input_value().startswith('X') and topic.input_value().endswith('Y'), 'Long topic field cannot reach and edit both ends on mobile'
                assert topic.evaluate('e=>e.scrollWidth<=e.clientWidth && Math.round(e.getBoundingClientRect().height)===72 && e.scrollHeight>e.clientHeight')
                topic.fill(PAPER['topic'])
                summary = page.locator('#more-actions .more-actions-toggle')
                assert summary.is_visible()
                assert summary.bounding_box()['height'] >= 44
                if width == 320:
                    summary.focus()
                    page.keyboard.press('Enter')
                    assert page.locator('#more-actions').evaluate('e=>e.open')
                    menu_rect = page.locator('#more-actions > div').bounding_box()
                    assert menu_rect and menu_rect['x'] >= 0 and menu_rect['y'] >= 0 and menu_rect['x'] + menu_rect['width'] <= width and menu_rect['y'] + menu_rect['height'] <= height, f'More menu escaped the phone viewport: {menu_rect}'
                    page.keyboard.press('Tab')
                    assert page.locator('#save-screenshot').evaluate('e=>e===document.activeElement'), 'Keyboard could not reach a More menu action'
                    page.keyboard.press('Escape')
                    assert not page.locator('#more-actions').evaluate('e=>e.open')
                    assert summary.evaluate('e=>e===document.activeElement'), 'Escape did not return focus to More'
                else:
                    summary.click()
                    assert page.locator('#more-actions[open] #save-screenshot').is_visible()
                    page.locator('#more-actions .more-actions-toggle').click()
            for theme in ['light', 'comfort', 'dark']:
                while page.locator('#theme-toggle').inner_text().lower() != theme:
                    if width <= 520 and not page.locator('#more-actions').evaluate('e=>e.open'):
                        page.locator('#more-actions .more-actions-toggle').click()
                    page.locator('#theme-toggle').click()
                page.wait_for_timeout(100)
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), f'Overflow at {width}/{theme}: '+page.evaluate('JSON.stringify({sw:document.documentElement.scrollWidth,iw:innerWidth,bw:document.body.scrollWidth,overflow:[...document.querySelectorAll("body *")].map(e=>({tag:e.tagName,id:e.id,cls:e.className,right:e.getBoundingClientRect().right,width:e.getBoundingClientRect().width})).filter(x=>x.right>innerWidth+1).slice(0,15)})')
                assert not page.locator('#generation').is_visible(), 'Hidden generation panel remained visible'
                if width <= 520 and page.locator('#more-actions').evaluate('e=>e.open'):
                    page.locator('#more-actions .more-actions-toggle').click()
                page.screenshot(path=str(output / f'reader-{width}-{theme}.png'))
                if width == 390 and theme == 'light':
                    page.screenshot(path=str(output / 'reader-390-light-full.png'), full_page=True)
            page.locator('#chat-toggle').click()
            if width <= 520:
                assert page.evaluate('document.querySelector(".page").inert')
                assert page.locator('#chat-panel').get_attribute('aria-modal') == 'true'
                page.locator('#chat-close').focus()
                page.keyboard.press('Shift+Tab')
                assert page.locator('#chat-panel').evaluate('e=>e.contains(document.activeElement)')
                page.screenshot(path=str(output / f'chat-{width}.png'))
            page.keyboard.press('Escape')
            assert not page.evaluate('document.querySelector(".page").inert')
            page.locator('#editions-toggle').click()
            page.screenshot(path=str(output / f'archive-{width}.png'))
            page.locator('.saved-edition-open').filter(has_text='Balcony gardens thrive').click()
            assert page.locator('#paper-topic').input_value() == PAPER['topic']
            assert page.evaluate('document.documentElement.dataset.theme') == 'dark'
            assert page.locator('.article').count() == 3

        # Exercise explanation controls in a touch-enabled phone viewport. A text range is
        # seeded in the article fixture because OS-level selection handles vary by browser.
        mobile_context = browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True, reduced_motion='reduce')
        mobile_context.add_init_script('window.reviewSpoken=[];window.speechSynthesis.speak=u=>window.reviewSpoken.push(u);window.speechSynthesis.cancel=()=>{};')
        mobile_context.route('**/api/**', api)
        mobile = mobile_context.new_page()
        mobile.set_default_timeout(10000)
        mobile.on('pageerror', lambda error: errors.append(str(error)))
        mobile.goto(args.base_url, wait_until='commit')
        mobile.wait_for_timeout(250)
        mobile.wait_for_function('typeof render === "function"')
        mobile_explanations = [{'quote': 'Container gardens make small spaces productive',
            'context': 'Choose containers with drainage and plants suited to the available sunlight.',
            'origin': {'type': 'article', 'id': 'garden-1'},
            'explanation': 'The saved passage recommends compact containers and choosing plants suited to the available sunlight.', 'sources': []},
            {'quote': 'A balcony herb garden can thrive in partial shade',
            'context': 'Basil, parsley, and mint tolerate limited direct sunlight when watered consistently.',
            'origin': {'type': 'article', 'id': 'garden-2'},
            'explanation': 'The saved note says basil, parsley, and mint can grow with limited direct sun.', 'sources': []}]
        mobile.evaluate('''({paper,explanations})=>render(paper,Date.parse('2026-10-02T12:00:00Z'),true,'mobile-review',explanations,null)''', {'paper': PAPER, 'explanations': mobile_explanations})
        topic = mobile.locator('#paper-topic')
        topic.fill('Balcony gardens need room for herbs and compact vegetables. ' * 5)
        before_page_scroll = mobile.evaluate('scrollY')
        topic_box = topic.bounding_box()
        assert topic_box and topic.evaluate('e=>e.scrollHeight>e.clientHeight')
        cdp = mobile_context.new_cdp_session(mobile)
        touch_x, touch_y = topic_box['x'] + topic_box['width'] / 2, topic_box['y'] + topic_box['height'] - 6
        cdp.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': touch_x, 'y': touch_y, 'id': 1}]})
        cdp.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': touch_x, 'y': topic_box['y'] + 8, 'id': 1}]})
        cdp.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': touch_x, 'y': topic_box['y'] + 2, 'id': 1}]})
        cdp.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
        mobile.wait_for_timeout(100)
        assert topic.evaluate('e=>e.scrollTop>0'), 'Touch swipe did not scroll the long topic inside its field'
        assert mobile.evaluate('scrollY') == before_page_scroll, 'Touch swipe scrolled the page instead of the topic field'
        topic.fill('x' + topic.input_value()[:298])
        assert topic.input_value().startswith('x'), 'Topic text could not be edited after touch scrolling'
        topic.fill(PAPER['topic'])
        mobile.evaluate('''()=>{const article=document.querySelector('.article'),heading=article.querySelector('h3'),summary=article.querySelector('p'),range=document.createRange();article.scrollIntoView({block:'center'});range.setStart(heading.firstChild,0);range.setEnd(summary.firstChild,Math.min(54,summary.firstChild.length));getSelection().removeAllRanges();getSelection().addRange(range);document.dispatchEvent(new Event('selectionchange'))}''')
        popover = mobile.locator('#explain-popover')
        mobile.wait_for_function('document.querySelector("#explain-popover")?.hidden === false')
        assert popover.is_visible(), 'Mobile selection did not open the explanation popover'
        rect = popover.bounding_box()
        assert rect and rect['x'] >= 0 and rect['y'] >= 0 and rect['x'] + rect['width'] <= 390 and rect['y'] + rect['height'] <= 844, f'Mobile explanation escaped the viewport: {rect}'
        assert int(popover.evaluate('e=>getComputedStyle(e).zIndex')) > int(mobile.locator('#chat-toggle').evaluate('e=>getComputedStyle(e).zIndex'))
        for selector in ['#chat-toggle', '#editions-toggle']:
            control = mobile.locator(selector).bounding_box()
            visible = mobile.locator(selector).evaluate('e=>getComputedStyle(e).visibility !== "hidden"')
            assert not visible, f'Mobile sidebar control {selector} obscures the active passage'
            overlaps = visible and control and rect and rect['x'] < control['x'] + control['width'] and rect['x'] + rect['width'] > control['x'] and rect['y'] < control['y'] + control['height'] and rect['y'] + rect['height'] > control['y']
            assert not overlaps, f'Mobile explanation overlaps fixed control {selector}: {rect} / {control}'
        mobile.screenshot(path=str(output / 'mobile-explanation.png'))
        mobile.locator('.explain-action').click()
        mobile.wait_for_function('document.querySelector(".explain-answer table")')
        mobile.locator('.explain-read').click()
        assert mobile.locator('.explain-read').get_attribute('aria-pressed') == 'true'
        assert mobile.evaluate('window.reviewSpoken.length') == 1
        mobile.locator('#read-paper').click()
        assert mobile.evaluate('speechSession === null')
        mobile.evaluate('''()=>{const article=document.querySelector('.article'),heading=article.querySelector('h3'),summary=article.querySelector('p'),range=document.createRange();range.setStart(heading.firstChild,0);range.setEnd(summary.firstChild,Math.min(54,summary.firstChild.length));getSelection().removeAllRanges();getSelection().addRange(range);document.dispatchEvent(new Event('selectionchange'))}''')
        mobile.wait_for_function('document.querySelector("#explain-popover")?.hidden === false')
        mobile.locator('.explain-chat').click()
        assert mobile.locator('#chat-panel').get_attribute('aria-hidden') == 'false'
        assert mobile.locator('#chat-context-text').inner_text().startswith('Container gardens make small spaces productive')
        assert mobile.locator('#chat-panel').bounding_box()['x'] == 0
        mobile.locator('#chat-close').click()
        cached_heading = mobile.locator('.article[data-article-id="garden-1"] h3')
        cached_heading.scroll_into_view_if_needed()
        cached_heading.tap()
        mobile.wait_for_function('document.querySelector("#explain-popover")?.hidden === false')
        assert 'saved passage recommends compact containers' in mobile.locator('.explain-answer').inner_text()
        before_explanation_scroll = mobile.evaluate('scrollY')
        for _ in range(4):
            touch_point = mobile.evaluate('''()=>{const pop=document.querySelector('#explain-popover').getBoundingClientRect();for(const element of document.querySelectorAll('.article p,.article .meta,.article h3,.theme p')){const r=element.getBoundingClientRect(),x=Math.max(r.left+4,Math.min(r.right-4,innerWidth/2)),y=Math.max(r.top+4,Math.min(r.bottom-4,innerHeight-32));if(r.width>8&&r.height>8&&y>80&&y<innerHeight-16&&!(x>=pop.left&&x<=pop.right&&y>=pop.top&&y<=pop.bottom))return{x,y}}return{x:innerWidth-5,y:innerHeight-35}}''')
            cdp.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': touch_point['x'], 'y': touch_point['y'], 'id': 2}]})
            cdp.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': touch_point['x'], 'y': max(40, touch_point['y'] - 280), 'id': 2}]})
            cdp.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': touch_point['x'], 'y': max(30, touch_point['y'] - 560), 'id': 2}]})
            cdp.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
            mobile.wait_for_timeout(100)
            if mobile.evaluate('''()=>{const range=savedRanges.find(x=>x.item.quote==='Container gardens make small spaces productive')?.range;const rect=range?.getBoundingClientRect();return !rect||rect.bottom<0||rect.top>innerHeight}'''):
                break
        assert mobile.evaluate('scrollY') > before_explanation_scroll, 'Touch scrolling did not move the page'
        assert mobile.evaluate('''()=>{const range=savedRanges.find(x=>x.item.quote==='Container gardens make small spaces productive')?.range;const rect=range?.getBoundingClientRect();return !rect||rect.bottom<0||rect.top>innerHeight}'''), 'Touch scrolling did not move the saved passage out of view'
        assert mobile.locator('#explain-popover').is_visible(), 'Scrolling a cached mobile explanation out of view closed its popover'
        assert mobile.evaluate('document.body.classList.contains("explanation-open")')
        mobile.screenshot(path=str(output / 'mobile-cached-explanation-scrolled.png'))
        mobile.locator('.explain-close').click()
        assert mobile.locator('#explain-popover').is_hidden(), 'The explanation close control did not dismiss the popover'
        second_cached_heading = mobile.locator('.article[data-article-id="garden-2"] h3')
        second_cached_heading.scroll_into_view_if_needed()
        second_cached_heading.tap()
        assert mobile.locator('.explain-quote').inner_text() == 'A balcony herb garden can thrive in partial shade'
        assert 'limited direct sun' in mobile.locator('.explain-answer').inner_text(), 'Opening another saved passage retained stale explanation content'
        mobile.evaluate('window.scrollTo({top:0,behavior:"instant"})')
        mobile.locator('.masthead h1').tap()
        assert mobile.locator('#explain-popover').is_hidden(), 'Tapping outside the paper left the cached explanation open'
        second_cached_heading.scroll_into_view_if_needed()
        second_cached_heading.tap()
        unexplained_passage = mobile.locator('.theme p').first
        unexplained_passage.scroll_into_view_if_needed()
        mobile.evaluate('element=>window.scrollBy({top:element.getBoundingClientRect().top-innerHeight*.68,behavior:"instant"})', unexplained_passage.element_handle())
        unexplained_passage.tap()
        assert mobile.locator('#explain-popover').is_hidden(), 'Tapping an unexplained story left the cached explanation open'
        assert not mobile.locator('#editions-toggle').evaluate('e=>getComputedStyle(e).visibility === "hidden"')
        mobile_context.close()
        assert not errors, errors
        browser.close()
        print(f'PASS: generation/reload, validation, settings drafts, explanation ranges and touch scrolling, chat tables, archive, responsive layouts, and touch-enabled explanation/read/chat controls. Screenshots: {output}')


if __name__ == '__main__':
    main()
