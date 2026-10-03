"""Cancellation and per-browser generation concurrency regressions."""
import json
import subprocess
import sys
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request, urlopen
from unittest.mock import patch

import server


class SlowModelHandler(BaseHTTPRequestHandler):
    request_seen = threading.Event()
    release = threading.Event()

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", "0")))
        type(self).request_seen.set()
        type(self).release.wait(8)
        try:
            body = json.dumps({"choices": [{"message": {"content": "late answer"}}]}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, *_args):
        pass


class SlowSourceHandler(BaseHTTPRequestHandler):
    request_seen = threading.Event()
    release = threading.Event()

    def do_GET(self):
        type(self).request_seen.set()
        type(self).release.wait(8)
        body = b"<html><article>Slow source text that should never finish after cancellation.</article></html>"
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, *_args):
        pass


class GenerationConcurrencyTests(unittest.TestCase):
    def test_cancel_interrupts_model_connect_before_a_request_is_sent(self):
        class BlockingSocket:
            connected = threading.Event()
            released = threading.Event()

            def settimeout(self, _timeout): pass
            def bind(self, _address): pass
            def setsockopt(self, *_args): pass
            def connect(self, _address):
                type(self).connected.set()
                type(self).released.wait(3)
                if getattr(self, 'closed', False):
                    raise OSError('socket closed during connect')
            def shutdown(self, _how): self.close()
            def close(self):
                self.closed = True
                type(self).released.set()

        BlockingSocket.connected.clear()
        BlockingSocket.released.clear()
        cancel = threading.Event()
        result = {}

        def call():
            try:
                server.call_model({"endpoint": "http://fixture/v1", "model": "fixture", "_cancel_event": cancel}, [{"role": "user", "content": "wait"}], 256)
            except Exception as exc:
                result['error'] = exc

        with patch.object(server, 'cancellable_getaddrinfo', return_value=[(server.socket.AF_INET, server.socket.SOCK_STREAM, 0, '', ('127.0.0.1', 1234))]), patch.object(server.socket, 'socket', side_effect=lambda *_args: BlockingSocket()):
            worker = threading.Thread(target=call, daemon=True)
            worker.start()
            self.assertTrue(BlockingSocket.connected.wait(1), 'model socket did not enter connect')
            started = time.monotonic()
            cancel.set()
            server.interrupt_model_requests(cancel)
            worker.join(1.5)
        self.assertFalse(worker.is_alive(), 'cancel left a model connection attempt blocked')
        self.assertIsInstance(result.get('error'), server.GenerationCancelled)
        self.assertLess(time.monotonic() - started, 1.5)

    def test_headless_process_drains_large_stdout_and_stderr(self):
        payload_size = 1024 * 1024
        script = f"import sys;sys.stdout.write('x'*{payload_size});sys.stderr.write('y'*{payload_size})"
        process = subprocess.Popen([sys.executable, '-c', script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
        stdout, stderr = server.communicate_with_timeout(process, 5)
        self.assertEqual(len(stdout), payload_size)
        self.assertEqual(len(stderr), payload_size)

    def assert_cancel_interrupts(self, streamed=False):
        SlowModelHandler.request_seen.clear()
        SlowModelHandler.release.clear()
        upstream = ThreadingHTTPServer(("127.0.0.1", 0), SlowModelHandler)
        upstream.daemon_threads = True
        thread = threading.Thread(target=upstream.serve_forever, daemon=True)
        thread.start()
        cancel = threading.Event()
        result = {}

        def call():
            try:
                config = {
                    "endpoint": f"http://127.0.0.1:{upstream.server_port}/v1",
                    "model": "fixture", "_cancel_event": cancel,
                }
                messages = [{"role": "user", "content": "wait"}]
                if streamed:
                    "".join(event.get("delta", "") for event in server.call_model_stream(config, messages, 256))
                else:
                    server.call_model(config, messages, 256)
            except Exception as exc:  # capture the worker outcome for assertions
                result["error"] = exc

        worker = threading.Thread(target=call, daemon=True)
        worker.start()
        self.assertTrue(SlowModelHandler.request_seen.wait(2), "model request never reached fixture endpoint")
        started = time.monotonic()
        cancel.set()
        server.interrupt_model_requests(cancel)
        worker.join(1.5)
        upstream.shutdown()
        upstream.server_close()
        self.assertFalse(worker.is_alive(), "cancel left the model request blocked")
        self.assertIsInstance(result.get("error"), server.GenerationCancelled)
        self.assertLess(time.monotonic() - started, 1.5)

    def test_cancel_interrupts_an_inflight_model_request(self):
        self.assert_cancel_interrupts()

    def test_cancel_interrupts_an_inflight_streamed_model_request(self):
        self.assert_cancel_interrupts(streamed=True)

    def test_cancel_interrupts_an_inflight_article_source_read(self):
        SlowSourceHandler.request_seen.clear()
        SlowSourceHandler.release.clear()
        upstream = ThreadingHTTPServer(("127.0.0.1", 0), SlowSourceHandler)
        upstream.daemon_threads = True
        api_thread = threading.Thread(target=upstream.serve_forever, daemon=True)
        api_thread.start()
        cancel = threading.Event()
        result = {}

        def read_source():
            try:
                server.run_with_source_cancellation(cancel, server.fetch_bytes,
                    f"http://127.0.0.1:{upstream.server_port}/article", timeout=15)
            except Exception as exc:
                result["error"] = exc

        worker = threading.Thread(target=read_source, daemon=True)
        worker.start()
        self.assertTrue(SlowSourceHandler.request_seen.wait(2), "article request never reached fixture endpoint")
        started = time.monotonic()
        cancel.set()
        server.interrupt_source_requests(cancel)
        worker.join(1.5)
        upstream.shutdown()
        upstream.server_close()
        api_thread.join(1)
        self.assertFalse(worker.is_alive(), "cancellation left a blocked article fetch running")
        self.assertIsInstance(result.get("error"), server.GenerationCancelled)
        self.assertLess(time.monotonic() - started, 1.5)
        with server.SOURCE_CONNECTIONS_LOCK:
            self.assertNotIn(cancel, server.SOURCE_CONNECTIONS)

    def test_cancel_interrupts_a_source_connect_before_request_is_sent(self):
        class BlockingSocket:
            connected = threading.Event()
            released = threading.Event()

            def settimeout(self, _timeout): pass
            def bind(self, _address): pass
            def connect(self, _address):
                type(self).connected.set()
                type(self).released.wait(3)
                if getattr(self, 'closed', False):
                    raise OSError('socket closed during connect')
            def shutdown(self, _how): self.close()
            def close(self):
                self.closed = True
                type(self).released.set()

        BlockingSocket.connected.clear()
        BlockingSocket.released.clear()
        cancel = threading.Event()
        result = {}

        def read_source():
            try:
                server.run_with_source_cancellation(cancel, server.fetch_bytes, 'http://fixture/article', timeout=15)
            except Exception as exc:
                result['error'] = exc

        with patch.object(server, 'cancellable_getaddrinfo', return_value=[(server.socket.AF_INET, server.socket.SOCK_STREAM, 0, '', ('127.0.0.1', 1234))]), patch.object(server.socket, 'socket', side_effect=lambda *_args: BlockingSocket()):
            worker = threading.Thread(target=read_source, daemon=True)
            worker.start()
            self.assertTrue(BlockingSocket.connected.wait(1), 'source socket did not enter connect')
            started = time.monotonic()
            cancel.set()
            server.interrupt_source_requests(cancel)
            worker.join(1.5)
        self.assertFalse(worker.is_alive(), 'cancel left a source connection attempt blocked')
        self.assertIsInstance(result.get('error'), server.GenerationCancelled)
        self.assertLess(time.monotonic() - started, 1.5)

    def test_failed_source_connect_releases_its_registered_socket(self):
        class FailedSocket:
            def settimeout(self, _timeout): pass
            def bind(self, _address): pass
            def connect(self, _address): raise OSError('fixture connect failure')
            def close(self): pass

        cancel = threading.Event()
        with patch.object(server, 'cancellable_getaddrinfo', return_value=[(server.socket.AF_INET, server.socket.SOCK_STREAM, 0, '', ('127.0.0.1', 1234))]), patch.object(server.socket, 'socket', side_effect=lambda *_args: FailedSocket()):
            with self.assertRaises(OSError):
                server.run_with_source_cancellation(cancel, server.fetch_bytes, 'http://fixture/article', timeout=2)
        with server.SOURCE_CONNECTIONS_LOCK:
            self.assertNotIn(cancel, server.SOURCE_CONNECTIONS, 'failed source connection left a registered socket behind')

    def test_cancel_interrupts_stalled_dns_resolution(self):
        started = threading.Event()
        killed = []
        launched = []
        class StalledProcess:
            returncode = None
            def __init__(self, *_args, **_kwargs):
                self.killed = threading.Event()
                launched.append(self)
                killed.append(self.killed)
            def communicate(self, timeout=None):
                if self.returncode is None:
                    started.set()
                    if not self.killed.wait(timeout or 0):
                        raise subprocess.TimeoutExpired('dns', timeout)
                return ('', '')
            def poll(self): return self.returncode
            def kill(self): self.returncode = -9; self.killed.set()

        cancels = [threading.Event() for _ in range(4)]
        results = [{} for _ in cancels]

        def resolve(index):
            try:
                server.cancellable_getaddrinfo(f'stalled-{index}.example', 443, cancels[index], timeout=15)
            except Exception as exc:
                results[index]['error'] = exc

        with patch.object(server.subprocess, 'Popen', StalledProcess):
            workers = [threading.Thread(target=resolve, args=(index,), daemon=True) for index in range(4)]
            for worker in workers: worker.start()
            self.assertTrue(started.wait(1), 'resolver process did not start')
            deadline = time.monotonic() + 1
            while len(launched) < 4 and time.monotonic() < deadline: time.sleep(.01)
            self.assertEqual(len(launched), 4, 'not all resolver processes started')
            begin = time.monotonic()
            for cancel in cancels: cancel.set()
            for worker in workers: worker.join(1.5)
            self.assertTrue(all(not worker.is_alive() for worker in workers), 'cancellation left resolver callers waiting')
            self.assertTrue(all(event.is_set() for event in killed), 'cancellation did not terminate every resolver process')
        self.assertTrue(all(isinstance(result.get('error'), server.GenerationCancelled) for result in results))
        self.assertLess(time.monotonic() - begin, 1.5)
        addresses = server.cancellable_getaddrinfo('localhost', 80, None, timeout=5)
        self.assertTrue(addresses, 'a fresh resolver lookup did not recover after all stalled processes were killed')

    @unittest.skipUnless(server.find_headless_browser(), 'Playwright Chromium is not installed')
    def test_cancel_closes_a_playwright_page_during_navigation(self):
        SlowSourceHandler.request_seen.clear()
        SlowSourceHandler.release.clear()
        upstream = ThreadingHTTPServer(('127.0.0.1', 0), SlowSourceHandler)
        upstream.daemon_threads = True
        api_thread = threading.Thread(target=upstream.serve_forever, daemon=True)
        api_thread.start()
        cancel = threading.Event()
        result = {}

        def read_source():
            try:
                server.run_with_source_cancellation(cancel, server.playwright_article_html, f'http://127.0.0.1:{upstream.server_port}/article', timeout=30)
            except Exception as exc:
                result['error'] = exc

        worker = threading.Thread(target=read_source, daemon=True)
        worker.start()
        try:
            self.assertTrue(SlowSourceHandler.request_seen.wait(15), 'Playwright navigation never reached fixture endpoint')
            started = time.monotonic()
            cancel.set()
            server.interrupt_source_requests(cancel)
            worker.join(3)
            self.assertFalse(worker.is_alive(), 'cancellation left Playwright navigation blocked')
            self.assertIsInstance(result.get('error'), server.GenerationCancelled)
            self.assertLess(time.monotonic() - started, 3)
            with server.SOURCE_BROWSER_PAGES_LOCK:
                self.assertNotIn(cancel, server.SOURCE_BROWSER_PAGES)
        finally:
            SlowSourceHandler.release.set()
            upstream.shutdown()
            upstream.server_close()
            api_thread.join(1)

    def test_same_browser_reuses_its_running_generation(self):
        server.JOBS.clear()
        server.JOB_CANCEL_EVENTS.clear()
        api = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        api.daemon_threads = True
        api_thread = threading.Thread(target=api.serve_forever, daemon=True)
        api_thread.start()
        release = threading.Event()

        def held_job(_job_id, _config):
            release.wait(3)

        def submit(client_id, options=None):
            body = json.dumps({"client_id": client_id, "options": options or {"topic": "local parks"}}).encode()
            request = Request(f"http://127.0.0.1:{api.server_port}/api/generate", data=body, headers={"Content-Type": "application/json"})
            try:
                with urlopen(request, timeout=2) as response:
                    return response.status, json.loads(response.read())
            except Exception as exc:
                if hasattr(exc, "code") and hasattr(exc, "read"):
                    try:
                        return exc.code, json.loads(exc.read())
                    finally:
                        exc.close()
                raise

        try:
            with patch.object(server, "configured_model", return_value={"endpoint": "http://fixture", "model": "fixture"}), patch.object(server, "run_job", side_effect=held_job) as run_job:
                first = submit("consumer-one-123456")
                second = submit("consumer-one-123456")
                conflict = submit("consumer-one-123456", {"topic": "local transit"})
                other = submit("consumer-two-123456")
                self.assertEqual(first[0], 202)
                self.assertEqual(second[0], 202)
                self.assertEqual(first[1]["job_id"], second[1]["job_id"])
                self.assertTrue(second[1]["reused"])
                self.assertEqual(conflict[0], 409)
                self.assertIn("different settings", conflict[1]["error"])
                self.assertNotEqual(first[1]["job_id"], other[1]["job_id"])
                self.assertEqual(run_job.call_count, 2)
        finally:
            release.set()
            api.shutdown()
            api.server_close()
            api_thread.join(1)
            with server.JOBS_LOCK:
                server.JOBS.clear()
                server.JOB_CANCEL_EVENTS.clear()


if __name__ == "__main__":
    unittest.main()
