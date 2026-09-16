import http.server
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
server = http.server.HTTPServer(("0.0.0.0", 9100), http.server.SimpleHTTPRequestHandler)
print("Serving on port 9100...", flush=True)
server.serve_forever()
