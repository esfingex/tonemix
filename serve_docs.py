"""
Simple HTTP server to serve documentation
"""
import http.server
import socketserver
import os
from pathlib import Path

PORT = 8000
DIRECTORY = "public_docs"

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

if __name__ == "__main__":
    if not Path(DIRECTORY).exists():
        print(f"Error: {DIRECTORY} not found. Run generate_docs.py first.")
        exit(1)
        
    print(f"🎵 Serving ToneMix Documentation")
    print(f"📂 Directory: {Path(DIRECTORY).absolute()}")
    print(f"🔗 URL: http://localhost:{PORT}")
    print("\nPress Ctrl+C to stop")
    
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
