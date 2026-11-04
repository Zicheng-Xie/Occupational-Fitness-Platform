"""Transport failure injection: preserve native responses and reject partial output."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

import pytest

from tools import run_external_graph_retrieval as graph


@pytest.mark.parametrize("reason,expected", [("stop", 200), ("length", 502)])
def test_strict_proxy_preserves_audit_and_only_delivers_complete_output(tmp_path, monkeypatch, reason, expected):
    native = {"done": True, "done_reason": reason, "message": {"content": "Entity extraction"}}

    class NativeHandler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            raw = json.dumps(native).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    server = ThreadingHTTPServer(("127.0.0.1", 0), NativeHandler)
    native_thread = threading.Thread(target=server.serve_forever, daemon=True)
    native_thread.start()
    # Reserve an ephemeral local port, then let the proxy own it.
    reserve = ThreadingHTTPServer(("127.0.0.1", 0), NativeHandler)
    port = reserve.server_port
    reserve.server_close()
    config = {"endpoint": f"http://127.0.0.1:{server.server_port}",
              "audit_endpoint": f"http://127.0.0.1:{port}", "graph_model": "test-model",
              "embedding_model": "test-embedding", "call_timeout_seconds": 10, "strict_graph_completions": True}
    monkeypatch.setattr(graph, "verify_runtime", lambda config: None)
    try:
        with graph.AuditProxy(config, tmp_path) as proxy:
            proxy.job = tmp_path
            request = Request(config["audit_endpoint"] + "/api/chat",
                              data=json.dumps({"model": "test-model"}).encode(),
                              headers={"Content-Type": "application/json"})
            try:
                response = build_opener(ProxyHandler({})).open(request, timeout=10)
            except HTTPError as exc:
                response = exc
            with response:
                assert response.status == expected
                delivered = json.load(response)
            assert delivered == native if expected == 200 else "error" in delivered
        row = json.loads((tmp_path / "model_calls.jsonl").read_text(encoding="utf-8"))
        assert json.loads(row["raw_response"]) == native
        assert row["http_status"] == 200
        assert row["returned_http_status"] == expected
        assert row["status"] == ("completed" if expected == 200 else "failed")
    finally:
        server.shutdown()
        server.server_close()
        native_thread.join()
