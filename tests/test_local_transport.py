"""Local-only transport must hold even when a proxy is configured."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest

from occupational_fitness_rag.llm import OllamaClient
from occupational_fitness_rag.pipeline.config import LLMConfig


@pytest.fixture
def local_endpoint(monkeypatch):
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("NO_PROXY", "")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.respond({"models": [{"name": "llama3:8b", "digest": "test-digest"}]})

        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            self.respond(
                {"embeddings": [[0.1, 0.2]], "model": "test"}
                if self.path == "/api/embed"
                else {"done": True, "message": {"content": '{"commentary":"Local test."}'}}
            )

        def respond(self, payload):
            data = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_chat_ignores_external_proxy(local_endpoint):
    client = OllamaClient(LLMConfig(base_url=local_endpoint))
    assert client.narrative({"test": True}) == "Local test."
    assert client.resolved_digest == "test-digest"


def test_embeddings_ignore_external_proxy(local_endpoint):
    pytest.importorskip("chromadb")
    from occupational_fitness_rag.indexing.local_embedding import LocalOllamaEmbedding

    embedding = LocalOllamaEmbedding(local_endpoint, "test")
    assert list(embedding(["test"])[0]) == pytest.approx([0.1, 0.2])
    restored = LocalOllamaEmbedding.build_from_config(embedding.get_config())
    assert restored.url == local_endpoint
