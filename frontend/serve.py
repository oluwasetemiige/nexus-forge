"""Serve the frontend on http://localhost:8000 with caching disabled,
so edits to the .js/.html files always show up on a normal refresh.

    cd frontend
    python serve.py
"""
import http.server
import socketserver


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


socketserver.TCPServer.allow_reuse_address = True

with socketserver.TCPServer(("127.0.0.1", 8000), NoCacheHandler) as server:
    print("Nexus Forge frontend  ->  http://localhost:8000")
    server.serve_forever()
