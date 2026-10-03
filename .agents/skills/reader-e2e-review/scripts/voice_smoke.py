#!/usr/bin/env python3
"""Exercise browser voice controls with isolated storage and simulated device voices."""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
from reader_smoke import PAPER


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8765')
    parser.add_argument('--output-dir', default='/tmp/daily-signal-voice-review')
    parser.add_argument('--chromium-path')
    args = parser.parse_args()
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(**({'executable_path': args.chromium_path} if args.chromium_path else {}))
        native = browser.new_page()
        native.goto(args.base_url)
        inventory = native.evaluate('speechSynthesis.getVoices().map(v=>({name:v.name,lang:v.lang,local:v.localService}))')
        (output / 'native-voice-inventory.json').write_text(json.dumps(inventory))
        native.close()
        context = browser.new_context(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
        context.add_init_script('''
        window.testVoices=[
          {voiceURI:'local-en',name:'English Local',lang:'en-US',localService:true,default:true},
          {voiceURI:'online-en',name:'English Online',lang:'en-GB',localService:false,default:false},
          {voiceURI:'local-fr',name:'French Local',lang:'fr-FR',localService:true,default:false}];
        window.utterances=[];window.cancelCount=0;
        window.SpeechSynthesisUtterance=class{constructor(text){this.text=text}};
        speechSynthesis.getVoices=()=>window.testVoices;
        speechSynthesis.speak=u=>window.utterances.push(u);
        speechSynthesis.cancel=()=>window.cancelCount++;
        speechSynthesis.resume=()=>{};speechSynthesis.pause=()=>{};
        ''')
        page = context.new_page()
        errors, calls = [], []
        page.on('pageerror', lambda e: errors.append(str(e)))

        def api(route):
            path = urlparse(route.request.url).path
            calls.append(path)
            route.fulfill(json={'job': None, 'model_configured': True} if path in ['/api/current', '/api/config'] else {'error': 'Unexpected API'}, status=200 if path in ['/api/current', '/api/config'] else 400)
        context.route('**/api/**', api)
        page.goto(args.base_url)
        page.wait_for_timeout(300)
        page.evaluate('(paper)=>render(paper,Date.now(),true,"voice-review")', PAPER)
        page.locator('#settings-toggle').click()
        page.evaluate('testVoices[0].localService=false;speechSynthesis.dispatchEvent(new Event("voiceschanged"))')
        assert 'may send' in page.locator('#reading-voice-note').inner_text()
        page.evaluate('testVoices[0].localService=true;speechSynthesis.dispatchEvent(new Event("voiceschanged"))')
        pop = page.locator('#settings-popover').bounding_box()
        assert pop['y'] >= 0 and pop['y'] + pop['height'] <= page.viewport_size['height']
        page.locator('#voice-filter').fill('fr-FR')
        assert page.locator('#reading-voice option').count() == 2
        page.locator('#voice-filter').fill('no-matching-voice')
        assert 'No voices match' in page.locator('#reading-voice-note').inner_text()
        page.locator('#voice-filter').fill('')
        online = json.dumps(['online-en', 'English Online', 'en-GB'], separators=(',', ':'))
        local = json.dumps(['local-en', 'English Local', 'en-US'], separators=(',', ':'))
        page.locator('#reading-voice').select_option(online)
        assert 'may send' in page.locator('#reading-voice-note').inner_text()
        page.locator('#reading-speed').select_option('0.75')
        page.locator('#preview-voice').click()
        assert page.evaluate('utterances.at(-1).voice.name') == 'English Online'
        assert page.evaluate('utterances.at(-1).rate') == .75
        page.locator('#preview-voice').click()
        assert page.evaluate('speechSession===null')
        page.locator('#settings-close').click()
        page.locator('#settings-toggle').click()
        assert page.locator('#reading-voice').input_value() == ''
        assert page.locator('#reading-speed').input_value() == '1'
        page.locator('#reading-voice').select_option(local)
        page.locator('#reading-speed').select_option('1.25')
        page.locator('#settings-form button[type=submit]').click()
        page.reload()
        page.wait_for_timeout(300)
        page.evaluate('(paper)=>render(paper,Date.now(),true,"voice-review")', PAPER)
        page.locator('#settings-toggle').click()
        assert page.locator('#reading-voice').input_value() == local
        assert page.locator('#reading-speed').input_value() == '1.25'
        page.locator('#settings-close').click()
        # Saving unchanged reading preferences must not restart active narration.
        page.locator('#read-paper').click()
        page.evaluate('utterances.at(-1).onstart()')
        count = page.evaluate('utterances.length')
        page.locator('#settings-toggle').click()
        page.locator('#settings-form button[type=submit]').click()
        assert page.evaluate('utterances.length') == count
        page.locator('#settings-toggle').click()
        page.locator('#reading-speed').select_option('1.5')
        page.locator('#settings-form button[type=submit]').click()
        assert page.evaluate('utterances.at(-1).rate') == 1.5
        page.locator('#read-paper').click()
        page.locator('#settings-toggle').click()
        page.locator('#reading-speed').select_option('1.25')
        page.locator('#settings-form button[type=submit]').click()
        # Cross-block selections retain a pause and accurate text-node offsets.
        page.locator('.theme').scroll_into_view_if_needed()
        page.evaluate('''()=>{const r=document.createRange();r.selectNodeContents(document.querySelector('.theme'));getSelection().removeAllRanges();getSelection().addRange(r);document.dispatchEvent(new Event('selectionchange'))}''')
        page.wait_for_timeout(100)
        page.locator('.explain-read').click()
        assert page.evaluate('utterances.at(-1).voice.name') == 'English Local'
        assert page.evaluate('utterances.at(-1).rate') == 1.25
        assert '\n' in page.evaluate('speechSession.chunks.map(c=>c.text).join("")')
        page.evaluate('utterances.at(-1).onstart();utterances.at(-1).onboundary({name:"word",charIndex:0,charLength:5})')
        assert page.evaluate('CSS.highlights.get("speech-word").values().next().value.toString()') == 'Water'
        page.locator('.explain-read').click()
        assert page.evaluate('speechSession===null')

        def read_range(start_selector, start_offset, end_selector, end_offset):
            page.evaluate('''([startSelector,startOffset,endSelector,endOffset])=>{
                const start=document.querySelector(startSelector).firstChild;
                const endElement=document.querySelector(endSelector);
                const end=endElement.lastChild.nodeType===Node.TEXT_NODE?endElement.lastChild:endElement.firstChild;
                const range=document.createRange();range.setStart(start,startOffset);range.setEnd(end,endOffset);
                getSelection().removeAllRanges();getSelection().addRange(range);
                document.dispatchEvent(new Event('selectionchange'));
            }''', [start_selector, start_offset, end_selector, end_offset])
            page.wait_for_timeout(100)
            page.wait_for_function('document.querySelector(".explain-quote")?.textContent===getSelection().toString().trim()')
            page.locator('.explain-read').click()
            return page.evaluate('utterances.at(-1).text')

        # Partial heading-to-paragraph selection keeps the words and a spoken pause.
        theme_heading = page.locator('.theme h3').first.inner_text()
        theme_summary = page.locator('.theme p').first.inner_text()
        selected = read_range('.theme h3', 2, '.theme p', 22)
        assert selected == theme_heading[2:] + '\n' + theme_summary[:22], repr((theme_heading, theme_summary, selected, theme_heading[2:] + '\n' + theme_summary[:22]))
        assert page.locator('#narration-transcript').is_hidden()
        page.evaluate('utterances.at(-1).onstart();utterances.at(-1).onboundary({name:"word",charIndex:0,charLength:4})')
        assert page.evaluate('CSS.highlights.get("speech-word").values().next().value.toString()') == selected[:4]
        page.locator('.explain-read').click()

        # Inline label to paragraph tail neither inserts a false pause nor shifts offsets.
        why = page.locator('.article .why').first
        label = why.locator('strong').inner_text()
        tail = why.evaluate('(p)=>p.lastChild.textContent')
        selected = read_range('.article .why strong', 4, '.article .why', 18)
        assert selected == label[4:] + tail[:18]
        page.evaluate('utterances.at(-1).onstart();utterances.at(-1).onboundary({name:"word",charIndex:0,charLength:7})')
        assert page.evaluate('CSS.highlights.get("speech-word").values().next().value.toString()') == selected[:7]
        page.locator('.explain-read').click()

        # Long selections split into bounded utterances and keep word ranges accurate.
        article_summary = page.locator('.article p:not(.why)').first
        full_text = article_summary.inner_text()
        selected = read_range('.article p:not(.why)', 0, '.article p:not(.why)', len(full_text))
        assert selected == page.evaluate('speechSession.chunks[0].text')
        chunk_texts = page.evaluate('speechSession.chunks.map(chunk=>chunk.text)')
        assert ' '.join(re.sub(r'\s+', ' ', text).strip() for text in chunk_texts) == ' '.join(full_text.split())
        assert page.evaluate('speechSession.chunks.length') >= 2
        assert page.evaluate('Math.max(...speechSession.chunks.map(chunk=>chunk.text.length))') <= 220
        page.evaluate('utterances.at(-1).onstart();utterances.at(-1).onboundary({name:"word",charIndex:0,charLength:6})')
        assert page.evaluate('CSS.highlights.get("speech-word").values().next().value.toString()') == 'Choose'
        previous_count = page.evaluate('utterances.length')
        page.evaluate('utterances.at(-1).onend()')
        assert page.evaluate('utterances.length') == previous_count + 1
        page.evaluate('utterances.at(-1).onstart();utterances.at(-1).onboundary({name:"word",charIndex:0,charLength:5})')
        second_chunk_word = page.evaluate('speechSession.chunks[1].text.slice(0,5)')
        assert page.evaluate('CSS.highlights.get("speech-word").values().next().value.toString()') == second_chunk_word
        remaining_chunks = page.evaluate('speechSession.chunks.length')
        for _ in range(remaining_chunks + 1):
            if page.evaluate('speechSession===null'):
                break
            page.evaluate('utterances.at(-1).onend()')
        assert page.evaluate('speechSession===null')
        assert page.evaluate('CSS.highlights.get("speech-word")===undefined')
        assert page.locator('.explain-read').get_attribute('aria-pressed') == 'false'

        # Article headline-to-summary selections keep both content and spacing.
        headline = page.locator('.article h3').first.inner_text()
        summary = page.locator('.article p:not(.why)').first.inner_text()
        selected = read_range('.article h3', 3, '.article p:not(.why)', 24)
        assert selected == headline[3:] + '\n' + summary[:24]
        page.evaluate('utterances.at(-1).onstart();utterances.at(-1).onboundary({name:"word",charIndex:0,charLength:5})')
        assert page.evaluate('CSS.highlights.get("speech-word").values().next().value.toString()') == selected[:5]
        page.locator('.explain-read').click()

        # Stopping long selected-text playback invalidates late speech events;
        # pressing Read selection again starts from the original selection.
        selected = read_range('.article p:not(.why)', 0, '.article p:not(.why)', len(full_text))
        stale_index = page.evaluate('utterances.length-1')
        page.evaluate('utterances.at(-1).onstart()')
        page.locator('.explain-read').click()
        assert page.evaluate('speechSession===null')
        page.evaluate('(index)=>utterances[index].onend()', stale_index)
        assert page.evaluate('speechSession===null')
        page.locator('.explain-read').click()
        assert page.evaluate('utterances.at(-1).text') == selected
        page.locator('.explain-read').click()
        assert page.evaluate('speechSession===null')

        # Native speech failures stop cleanly and leave the selected passage intact.
        selected = read_range('.theme h3', 0, '.theme h3', len(theme_heading))
        page.evaluate('utterances.at(-1).onerror({error:"voice-unavailable"})')
        assert page.evaluate('speechSession===null')
        assert 'unavailable' in page.locator('#status').inner_text().lower()
        assert page.locator('.theme h3').first.inner_text() == theme_heading
        assert selected == theme_heading

        # The selection popover and its reader control remain reachable on phone.
        if page.locator('#settings-popover').is_visible():
            page.locator('#settings-close').click()
        page.set_viewport_size({'width': 390, 'height': 760})
        page.locator('.theme h3').scroll_into_view_if_needed()
        page.evaluate('getSelection().removeAllRanges()')
        page.wait_for_timeout(100)
        page.evaluate('''()=>{const range=document.createRange();range.selectNodeContents(document.querySelector('.theme h3'));getSelection().removeAllRanges();getSelection().addRange(range);document.dispatchEvent(new Event('selectionchange'))}''')
        page.wait_for_function('document.querySelector(".explain-quote")?.textContent===getSelection().toString().trim()')
        page.locator('#explain-popover').wait_for(state='visible')
        popover = page.locator('#explain-popover').bounding_box()
        assert popover['x'] >= 0 and popover['y'] >= 0
        assert popover['x'] + popover['width'] <= 390
        assert popover['y'] + popover['height'] <= 760
        assert page.locator('.explain-read').is_visible()
        assert page.locator('.explain-read').bounding_box()['height'] >= 44
        page.screenshot(path=str(output / 'selection-popover-390.png'))
        page.locator('.explain-read').click()
        assert page.evaluate('utterances.at(-1).text') == theme_heading
        page.locator('.explain-read').click()

        # Voice disappearance falls back safely; late voices refresh without losing the choice.
        page.locator('#settings-toggle').click()
        page.evaluate('testVoices=[];speechSynthesis.dispatchEvent(new Event("voiceschanged"))')
        assert 'unavailable' in page.locator('#reading-voice-note').inner_text()
        page.locator('#preview-voice').click()
        assert page.evaluate('utterances.at(-1).voice===undefined')
        page.evaluate('utterances.at(-1).onerror({error:"voice-unavailable"})')
        assert 'unavailable' in page.locator('#voice-preview-status').text_content()
        assert page.evaluate('speechSession===null')
        page.evaluate('testVoices=[{voiceURI:"local-en",name:"English Local",lang:"en-US",localService:true,default:true}];speechSynthesis.dispatchEvent(new Event("voiceschanged"))')
        assert page.locator('#reading-voice').input_value() == local
        for width in [1440, 390, 320]:
            page.set_viewport_size({'width': width, 'height': 760})
            page.wait_for_timeout(100)
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.screenshot(path=str(output / f'voice-settings-{width}.png'))
        assert not errors, errors
        assert not any(path not in ['/api/current', '/api/config'] for path in calls), calls
        browser.close()
    print(f'PASS voice filtering, preview/drafts, persistence, selection boundaries, unavailable voices, and mobile settings. Native voices observed: {len(inventory)}; playback simulated.')


if __name__ == '__main__':
    main()
