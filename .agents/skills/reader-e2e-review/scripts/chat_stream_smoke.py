#!/usr/bin/env python3
"""Exercise real chat forms and backend streaming against a local fake model."""
import argparse
import json
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
import server as app
from reader_smoke import PAPER

FIRST = '**Start small.** Café gardens thrive 🌿.\n\n'
TABLE = '| Plant | Light |\n| --- | --- |\n| Mint | Partial shade |\n| Basil | Sun |\n'
records = {'chat': [], 'cancel': [], 'model': [], 'searches': [], 'reads': []}
model_counts = {}
model_lock = threading.Lock()


class FakeModel(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        mode = body['messages'][-1]['content'].split('\n', 1)[0]
        if 'Decide whether to browse' in body['messages'][0]['content']:
            planning = json.loads(body['messages'][-1]['content'].split('\n', 1)[1])
            question = planning['question']
            needs_search = question != 'Explain the supplied passage'
            records['model'].append(body)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'choices': [{'message': {'content': json.dumps({'search': needs_search, 'query': 'balcony plant options' if needs_search else ''})}, 'finish_reason': 'stop'}]}).encode())
            return
        with model_lock:
            records['model'].append(body)
            count = model_counts.get(mode, 0)
            model_counts[mode] = count + 1
        if mode == 'Context retry' and count == 0:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"error":"maximum context length exceeded"}')
            return
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
        self.send_header('Connection', 'close')
        self.end_headers()

        def send(choice):
            raw = ('data: ' + json.dumps({'choices': [choice]}, ensure_ascii=False) + '\n\n').encode()
            # Split writes inside Unicode as well as event boundaries.
            for offset in range(0, len(raw), 11):
                self.wfile.write(raw[offset:offset + 11])
                self.wfile.flush()

        try:
            time.sleep(0.9)  # Enough time to observe submit scrolling before text.
            send({'index': 0, 'delta': {'reasoning_content': 'PRIVATE TEST REASONING'}})
            send({'index': 0, 'delta': {'content': FIRST}})
            time.sleep(0.35)
            if mode == 'Interrupt response':
                return  # EOF without a completion event.
            chunks = ['\n\nMore detail about sunlight and drainage. ' * 3] * 45 if mode in {'Stop response', 'Long response', 'Read manually'} else [TABLE[:35], TABLE[35:], '\nChoose pots with drainage.']
            for chunk in chunks:
                send({'index': 0, 'delta': {'content': chunk}})
                time.sleep(0.06 if mode in {'Long response', 'Read manually'} else 0.18)
            send({'index': 0, 'delta': {}, 'finish_reason': 'stop'})
            self.wfile.write(b'data: [DONE]\n\n')
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass


def fake_search(query, limit=5):
    records['searches'].append(query)
    return [{'title': 'Balcony gardens', 'url': 'https://publisher.invalid/garden', 'snippet': 'Match plants to the available sunlight.'}]


def fake_article(article):
    records['reads'].append(article['link'])
    article.update(article_url=article['link'], article_text='Mint grows in partial shade. Basil needs sun.', read_status='Full article read')
    return article


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chromium-path')
    parser.add_argument('--output-dir', default='/tmp/daily-signal-chat-stream-review')
    parser.add_argument('--html-revision', help='Serve an older index.html to prove regression detection')
    args = parser.parse_args()
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    os.chdir(ROOT)
    html = subprocess.check_output(['git', 'show', f'{args.html_revision}:index.html']) if args.html_revision else (ROOT / 'index.html').read_bytes()

    class Reader(app.Handler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            if urlparse(self.path).path == '/':
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(html)))
                self.end_headers()
                self.wfile.write(html)
            else:
                super().do_GET()

        def do_POST(self):
            if self.path == '/api/chat':
                records['chat'].append(self.path)
            if self.path == '/api/chat/cancel':
                records['cancel'].append(self.path)
            super().do_POST()

    model = ThreadingHTTPServer(('127.0.0.1', 0), FakeModel)
    reader = ThreadingHTTPServer(('127.0.0.1', 0), Reader)
    model.daemon_threads = reader.daemon_threads = True
    app.MODEL_CONFIG = {'endpoint': f'http://127.0.0.1:{model.server_port}', 'model': 'local-stream-fixture', 'contextLength': 8192, 'outputTokens': 1024}
    app.search_web, app.article_text = fake_search, fake_article
    for service in [model, reader]:
        threading.Thread(target=service.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{reader.server_port}'
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(**({'executable_path': args.chromium_path} if args.chromium_path else {}))
            for width in [1440, 390]:
                context = browser.new_context(viewport={'width': width, 'height': 1000})
                # The only browser networking allowed is this isolated reader.
                context.route('**/*', lambda route: route.continue_() if route.request.url.startswith(base) else route.abort())
                page = context.new_page()
                page.set_default_timeout(10000)
                errors, navigations = [], []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('framenavigated', lambda frame: navigations.append(frame.url) if frame == page.main_frame else None)
                page.goto(base)
                page.wait_for_timeout(100)
                page.evaluate('(paper)=>render(paper,Date.now(),true,"stream-review")', PAPER)
                page.locator('#chat-toggle').click()

                def submit(text, action):
                    page.evaluate("window.__chatDocumentToken='stream-review'")
                    navigation_count, sent_count = len(navigations), len(records['chat'])
                    page.locator('#chat-input').fill(text)
                    if action == 'click':
                        page.locator('#chat-send').click()
                    else:
                        page.locator('#chat-input').press('Enter')
                    page.wait_for_timeout(100)
                    assert not errors, f'Chat submit raised a runtime error: {errors}'
                    assert len(navigations) == navigation_count, 'Chat submit navigated the document'
                    assert page.evaluate("window.__chatDocumentToken==='stream-review'"), 'Chat submit reloaded the document'
                    page.wait_for_function("document.querySelector('#chat-stop').offsetParent!==null")
                    assert len(records['chat']) == sent_count + 1, 'Submit did not send exactly one chat request'
                    page.wait_for_function("(()=>{const box=document.querySelector('#chat-messages');return box.scrollHeight-box.clientHeight-box.scrollTop<3})()")
                    page.wait_for_function("[...document.querySelectorAll('.chat-markdown')].some(node=>node.textContent.includes('Café'))")
                    assert page.locator('#chat-stop').is_visible(), 'No observable partial response before completion'
                    assert 'PRIVATE TEST REASONING' not in page.locator('#chat-messages').inner_text()

                for action in ['click', 'enter']:
                    page.locator('#chat-new').click()
                    history = [{'role': 'user' if i % 2 == 0 else 'assistant', 'content': 'Earlier discussion. ' * 24} for i in range(12)]
                    page.evaluate('(rows)=>{saveChatHistory(rows);renderChatHistory()}', history)
                    submit('Compare options', action)
                    page.wait_for_function("!document.querySelector('#chat-send').disabled")
                    assert page.locator('.chat-markdown table').count() == 1
                    assert page.locator('.chat-markdown').last.inner_text().count('Start small.') == 1
                    assert not errors, errors

                # Follow new text until the question reaches the top, then stop.
                page.locator('#chat-new').click()
                page.evaluate('(rows)=>{saveChatHistory(rows);renderChatHistory()}', history)
                submit('Long response', 'click')
                page.wait_for_function("activeChatRequest && !activeChatRequest.follow && document.querySelector('#chat-send').disabled")
                # Use the active request's exact question, not another older turn.
                question_offset = page.evaluate("(()=>{const pane=document.querySelector('#chat-messages'),index=activeChatRequest.rows.indexOf(activeChatRequest.user),q=pane.querySelector(`[data-chat-index='${index}']`);return q.getBoundingClientRect().top-pane.getBoundingClientRect().top})()")
                assert 15 <= question_offset <= 21, f'Question did not anchor at top: {question_offset}'
                held = page.locator('#chat-messages').evaluate('e=>e.scrollTop')
                page.wait_for_timeout(400)
                assert abs(page.locator('#chat-messages').evaluate('e=>e.scrollTop') - held) < 2, 'Following continued past the question top'
                page.locator('#chat-stop').click()

                page.locator('#chat-new').click()
                page.evaluate('(rows)=>{saveChatHistory(rows);renderChatHistory()}', history)
                submit('Read manually', 'click')
                pane = page.locator('#chat-messages')
                pane.hover()
                page.mouse.wheel(0, -350)
                page.wait_for_timeout(200)
                held = pane.evaluate('e=>e.scrollTop')
                before_text = page.locator('.chat-markdown').last.inner_text()
                page.wait_for_timeout(400)
                assert page.locator('.chat-markdown').last.inner_text() != before_text, 'No further chunks arrived after manual scrolling'
                assert abs(pane.evaluate('e=>e.scrollTop') - held) < 2, 'Streaming interrupted the reader scroll position'
                assert not page.evaluate('activeChatRequest.follow')
                page.locator('#chat-stop').click()

                page.locator('#chat-new').click()
                searches_before, reads_before = len(records['searches']), len(records['reads'])
                submit('Explain the supplied passage', 'enter')
                page.wait_for_function("!document.querySelector('#chat-send').disabled")
                assert len(records['searches']) == searches_before and len(records['reads']) == reads_before, 'Direct-answer question unnecessarily browsed'

                page.locator('#chat-new').click()
                before = len(records['chat'])
                page.locator('#chat-input').fill('Draft')
                page.locator('#chat-input').press('Shift+Enter')
                assert page.locator('#chat-input').input_value().endswith('\n')
                page.locator('#chat-input').evaluate("e=>e.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true,isComposing:true}))")
                page.wait_for_timeout(50)
                assert len(records['chat']) == before, 'Newline or IME composition submitted chat'
                submit('Stop response', 'click')
                page.locator('#chat-stop').click()
                assert not page.locator('#chat-send').is_disabled()
                assert 'Response stopped.' in page.locator('#chat-messages').inner_text()
                assert 'Café' in page.locator('#chat-messages').inner_text()
                page.wait_for_timeout(700)
                assert records['cancel'], 'Stop did not reach the backend cancellation endpoint'
                assert not app.CHAT_REQUESTS, 'Cancelled chat request remained active'
                page.screenshot(path=str(output / f'chat-stop-{width}.png'))

                if width == 1440:
                    for question in ['Interrupt response', 'Context retry']:
                        page.locator('#chat-new').click()
                        submit(question, 'enter')
                        page.wait_for_function("!document.querySelector('#chat-send').disabled")
                        if question == 'Interrupt response':
                            assert 'Response interrupted:' in page.locator('#chat-messages').inner_text()
                            assert 'Café' in page.locator('#chat-messages').inner_text()
                        else:
                            assert model_counts[question] == 2, 'Context overflow did not retry once'
                            assert page.locator('.chat-markdown').last.inner_text().count('Start small.') == 1
                assert not errors, errors
                context.close()
            assert records['searches'] and records['reads'], 'Research path was not exercised'
            browser.close()
        print('PASS: desktop/mobile Send and Enter, no navigation, bottom scrolling, bounded question following, manual-scroll preservation, adaptive browsing, partial Unicode streams, private reasoning, Markdown tables, Stop, interrupted replies, context retry, and local research.')
    finally:
        reader.shutdown()
        model.shutdown()
        reader.server_close()
        model.server_close()


if __name__ == '__main__':
    main()
