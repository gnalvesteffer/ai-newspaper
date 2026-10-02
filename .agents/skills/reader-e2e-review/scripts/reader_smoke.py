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
        'read_status': 'Full article read', 'link': 'https://example.com/gardening', 'date': '2026-10-01'}],
    'feed_errors': []}
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
        options = {'headless': True}
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
                state['job'] = {'id': f'review-{len(generated)}', 'status': 'running',
                    'stage': 'Reading sources', 'detail': 'Review generation in progress', 'percent': 20}
                payload = {'job_id': state['job']['id']}
            elif path == '/api/status':
                state['polls'] += 1
                if state['polls'] >= 3:
                    state['job'] = {**state['job'], 'status': 'done', 'result': PAPER,
                        'finished_at': '2026-10-02T12:00:00Z'}
                payload = state['job']
            elif path == '/api/explain':
                payload = {'explanation': ANSWER, 'sources_used': []}
            elif path == '/api/chat':
                chats.append(route.request.post_data_json)
                payload = {'reply': ANSWER, 'web_sources': []}
            else:
                route.fulfill(status=400, json={'error': f'Unexpected review API: {path}'})
                return
            route.fulfill(json=payload)

        context.route('**/api/**', api)
        page.goto(args.base_url, wait_until='domcontentloaded')
        page.wait_for_timeout(500)
        assert not generated, 'Fresh visit started generation without an action'
        assert page.locator('#paper-topic').input_value() == ''
        page.locator('#paper-topic').fill(PAPER['topic'])
        page.locator('#paper-topic').press('Enter')
        page.wait_for_function('document.querySelector("#paper-topic").disabled')
        assert page.locator('#refresh').is_disabled()
        page.reload(wait_until='domcontentloaded')
        page.wait_for_function('document.querySelector(".article")')
        assert len(generated) == 1, 'Reload restarted the job'
        page.wait_for_function('document.querySelectorAll(".saved-edition-open").length === 1')

        # Validation must leave the loaded paper intact.
        page.locator('#paper-topic').fill('   ')
        page.locator('#refresh').click()
        assert page.locator('.article').count() == 1
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
        page.reload(wait_until='domcontentloaded')
        page.wait_for_function('document.querySelector(".article")')
        assert page.evaluate('CSS.highlights.get("saved-explanations").size') == 1
        assert page.locator('.chat-message').count() == 2

        for _ in range(3):
            page.locator('#font-larger').click()
        for width, height in [(320, 740), (390, 844), (768, 1024), (1440, 1000)]:
            page.set_viewport_size({'width': width, 'height': height})
            page.evaluate('window.scrollTo(0,0)')
            for theme in ['light', 'comfort', 'dark']:
                while page.locator('#theme-toggle').inner_text().lower() != theme:
                    page.locator('#theme-toggle').click()
                page.wait_for_timeout(100)
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), f'Overflow at {width}/{theme}'
                assert not page.locator('#generation').is_visible(), 'Hidden generation panel remained visible'
                page.screenshot(path=str(output / f'reader-{width}-{theme}.png'))
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
            page.locator('.saved-edition-open').first.click()
            assert page.locator('#paper-topic').input_value() == PAPER['topic']
            assert page.locator('#theme-toggle').inner_text() == 'DARK'
            assert page.locator('.article').count() == 1
        assert not errors, errors
        browser.close()
        print(f'PASS: generation/reload, validation, settings drafts, explanation ranges, chat tables, archive, and responsive layouts. Screenshots: {output}')


if __name__ == '__main__':
    main()
