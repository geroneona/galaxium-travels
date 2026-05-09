#!/usr/bin/env python3
"""
Stub MCP server mimicking the superhighfives weather MCP server.
Runs on port 8020. Open http://localhost:8020 to toggle endpoints up/down.
Run: `python weather-mcp-stub.py`
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

state = {
    "tools/list": True,
    "tools/call": True,
}

TOOLS = [
    {
        "name": "get-current-weather",
        "description": "Get the current weather for a specific city. Returns temperature, conditions, humidity, and wind information.",
        "inputSchema": {
            "type": "object",
            "properties": {"city": {"type": "string", "description": "Name of the city (e.g., 'London', 'New York', 'Tokyo')"}},
            "required": ["city"],
            "additionalProperties": False,
            "$schema": "http://json-schema.org/draft-07/schema#",
        },
    },
    {
        "name": "get-forecast",
        "description": "Get weather forecast for a specific city. Returns daily forecasts with high/low temperatures and conditions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "Name of the city (e.g., 'London', 'New York', 'Tokyo')"},
                "days": {"type": "number", "minimum": 1, "maximum": 7, "description": "Number of days to forecast (1-7)", "default": 3},
            },
            "required": ["city"],
            "additionalProperties": False,
            "$schema": "http://json-schema.org/draft-07/schema#",
        },
    },
]

HTML = """<!DOCTYPE html>
<html>
<head>
  <title>Mock MCP Server</title>
  <style>
    body { font-family: monospace; padding: 2em; max-width: 600px; }
    h2 { margin-bottom: 1.5em; }
    .row { display: flex; align-items: center; gap: 1em; margin: 0.8em 0; font-size: 1.1em; }
    .badge { padding: 0.15em 0.7em; border-radius: 4px; font-weight: bold; }
    .up   { background: #4caf50; color: #fff; }
    .down { background: #e53935; color: #fff; }
    button { cursor: pointer; padding: 0.2em 0.9em; font-family: monospace; }
  </style>
</head>
<body>
  <h2>Mock MCP Server &mdash; :8020</h2>
  <div id="app"></div>
  <script>
    async function load() {
      const s = await (await fetch('/state')).json();
      document.getElementById('app').innerHTML = Object.entries(s).map(([k, v]) => `
        <div class="row">
          <span style="width:120px">${k}</span>
          <span class="badge ${v ? 'up' : 'down'}">${v ? 'UP' : 'DOWN'}</span>
          <button onclick="toggle('${k}')">${v ? 'Set DOWN' : 'Set UP'}</button>
        </div>`).join('');
    }
    async function toggle(key) {
      await fetch('/toggle', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ key }) });
      load();
    }
    load();
  </script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"{self.command} {self.path} -> {args[1]}")

    def _send_json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_sse(self, data):
        body = f"event: message\ndata: {json.dumps(data)}\n\n".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, code):
        self.send_response(code)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Accept")
        self.end_headers()

    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(HTML.encode())
        elif self.path == "/state":
            self._send_json(200, state)
        else:
            self._send_error(404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        if self.path == "/toggle":
            key = json.loads(body).get("key")
            if key in state:
                state[key] = not state[key]
            self._send_json(200, state)
            return

        if self.path == "/mcp":
            req = json.loads(body)
            method = req.get("method")
            req_id = req.get("id")

            if method == "tools/list":
                if not state["tools/list"]:
                    self._send_error(500)
                    return
                self._send_sse({"result": {"tools": TOOLS}, "jsonrpc": "2.0", "id": req_id})

            elif method == "tools/call":
                if not state["tools/call"]:
                    self._send_error(500)
                    return
                params = req.get("params", {})
                tool = params.get("name")
                args = params.get("arguments", {})
                city = args.get("city", "Unknown")
                if tool == "get-current-weather":
                    text = json.dumps({
                        "city": city,
                        "current": {"temperature": "20°C", "conditions": "Sunny", "humidity": "55%", "wind": {"speed": "10 km/h", "direction": "180°"}},
                    })
                elif tool == "get-forecast":
                    days = int(args.get("days", 3))
                    text = json.dumps({
                        "city": city,
                        "forecast": [
                            {"date": f"2026-04-{14 + i:02d}", "temperature": {"max": f"{20 + i}°C", "min": f"{10 + i}°C"}, "conditions": "Sunny"}
                            for i in range(days)
                        ],
                    })
                else:
                    text = f"Unknown tool: {tool}"
                self._send_sse({"result": {"content": [{"type": "text", "text": text}]}, "jsonrpc": "2.0", "id": req_id})

            else:
                self._send_sse({"error": {"code": -32601, "message": f"Method not found: {method}"}, "jsonrpc": "2.0", "id": req_id})
            return

        self._send_error(404)


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8020), Handler)
    print("Mock MCP server at http://localhost:8020")
    print("  UI:         http://localhost:8020/")
    print("  MCP:  POST  http://localhost:8020/mcp")
    server.serve_forever()
