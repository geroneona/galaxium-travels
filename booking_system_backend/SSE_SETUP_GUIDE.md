# SSE MCP Server Setup Guide for IBM Agentic App Studio

## The Confusion Explained

You have **TWO SEPARATE SERVERS**:

### Server 1: Booking API (server.py)
- **Port:** 8080
- **Purpose:** Your booking system backend (flights, bookings, users)
- **URL:** http://localhost:8080 or https://brownnose-igloo-ideally.ngrok-free.dev
- **Swagger UI:** http://localhost:8080/docs
- **Status:** ✅ Already running

### Server 2: MCP Server (mcp_sse_server.py) - NEW!
- **Port:** 8000
- **Purpose:** Provides tools to IBM Agentic App Studio
- **URL:** http://localhost:8000 (needs ngrok)
- **SSE Endpoint:** http://localhost:8000/sse
- **Status:** ❌ Not running yet - YOU NEED TO START THIS

---

## Step-by-Step Setup

### Step 1: Start the MCP SSE Server

Open a **NEW terminal** (keep your booking API running on port 8080):

```bash
cd booking_system_backend
python mcp_sse_server.py
```

You should see:
```
================================================================================
MCP SSE Server for IBM Agentic App Studio
================================================================================
This is a SEPARATE server from your booking API (port 8080)
This MCP server will run on port 8000
...
```

### Step 2: Expose MCP Server with Ngrok

Open **ANOTHER terminal** and run:

```bash
ngrok http 8000
```

You'll get output like:
```
Forwarding  https://xyz123.ngrok-free.dev -> http://localhost:8000
```

**Copy that ngrok URL!**

### Step 3: Configure IBM Agentic App Studio

In IBM Agentic App Studio, use this URL:

```
https://xyz123.ngrok-free.dev/sse
```

**NOT** `https://brownnose-igloo-ideally.ngrok-free.dev/sse` (that's your booking API, not MCP server)

---

## What You'll Have Running

After setup, you'll have **3 things running**:

1. **Booking API** (port 8080) - Your existing server
2. **MCP Server** (port 8000) - New server for tools
3. **Ngrok tunnel** - Exposes MCP server to internet

---

## URLs Summary

| Purpose | URL | What It Does |
|---------|-----|--------------|
| **Booking API** | https://brownnose-igloo-ideally.ngrok-free.dev | Your booking system backend |
| **MCP Server** | https://xyz123.ngrok-free.dev/sse | Provides tools to IBM Agentic App Studio |
| **Swagger UI** | http://localhost:8080/docs | API documentation |

---

## Testing

1. **Test MCP Server locally:**
   ```bash
   curl http://localhost:8000/sse
   ```

2. **Test MCP Server via ngrok:**
   ```bash
   curl https://xyz123.ngrok-free.dev/sse
   ```

3. **Test in IBM Agentic App Studio:**
   - Add MCP Server URL: `https://xyz123.ngrok-free.dev/sse`
   - Your agent should see tools like `book_flight_remote`

---

## Troubleshooting

### "Not Found" Error
- ❌ Wrong: `https://brownnose-igloo-ideally.ngrok-free.dev/sse`
- ✅ Correct: `https://your-new-ngrok-url.ngrok-free.dev/sse`

### Port Already in Use
- Your booking API uses port 8080 ✅
- MCP server uses port 8000 ✅
- These are different ports - no conflict

### Can't Connect
- Make sure MCP server is running: `python mcp_sse_server.py`
- Make sure ngrok is running: `ngrok http 8000`
- Use the ngrok URL, not localhost

---

## Why Two Servers?

- **Booking API** = Where your DATA lives (flights, bookings)
- **MCP Server** = Where your TOOLS live (for AI agents)
- IBM Agentic App Studio connects to MCP Server to get tools
- Tools call Booking API to get/modify data

This separation is normal and recommended!