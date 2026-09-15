import http.server
import os

os.chdir("/home/isp/payment project/walletDemo/download")
server = http.server.HTTPServer(("0.0.0.0", 9100), http.server.SimpleHTTPRequestHandler)
print("Serving on port 9100...", flush=True)
server.serve_forever()
