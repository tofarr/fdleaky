import os
import random
import socketserver
from tempfile import NamedTemporaryFile
from threading import Thread
import time
import urllib.request

import pytest
from fdleaky.fd_tracker import FdTracker
from http.server import SimpleHTTPRequestHandler


def test_open():
    temp_file = NamedTemporaryFile(delete=False, delete_on_close=True)
    with FdTracker() as tracker:
        with open(temp_file.name, "w") as writer:
            assert len(tracker.short_term_store) == 1
            fd = next(iter(tracker.short_term_store.values()))
            assert fd.created_at > time.time() - 5
            assert fd.stack is not None
            assert fd.subject is not None
            writer.write("tested")
        assert len(tracker.short_term_store) == 0
    temp_file.close()


def test_temp():
    with FdTracker() as tracker:
        with NamedTemporaryFile(delete=True, delete_on_close=True) as temp_file:
            temp_file.write(b"tested")
            assert len(tracker.short_term_store) == 1
            fd = next(iter(tracker.short_term_store.values()))
            assert fd.created_at > time.time() - 5
            assert fd.stack is not None
            assert fd.subject is not None
        assert len(tracker.short_term_store) == 0


@pytest.mark.skipif(
    os.environ.get("GITHUB_ACTIONS") == "true",
    reason="This integration style test is flaky in github actions",
)
def test_http():
    port = random.randint(30000, 31000)
    httpd = None
    with FdTracker() as tracker:
        try:
            # Create and start a simple server
            def run_server():
                nonlocal httpd
                with socketserver.TCPServer(
                    ("", port), SimpleHTTPRequestHandler
                ) as http_daemon:
                    httpd = http_daemon
                    httpd.serve_forever()

            thread = Thread(target=run_server, daemon=True)
            thread.start()

            while httpd is None:
                time.sleep(0.1)

            # Create a http connection to the server
            connection = urllib.request.urlopen(f"http://localhost:{port}/")
            assert len(tracker.short_term_store) >= 2
            fd = next(iter(tracker.short_term_store.values()))
            assert fd.created_at > time.time() - 5
            assert fd.stack is not None
            assert fd.subject is not None
            content = connection.read()
            assert bool(content)
            connection.close()
        finally:
            if httpd:
                httpd.shutdown()
                thread.join()
            assert len(tracker.short_term_store) == 0
