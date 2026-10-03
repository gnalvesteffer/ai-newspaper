#!/usr/bin/env python3
"""Exercise browser voice controls with isolated storage and simulated device voices."""
import argparse
import json
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
