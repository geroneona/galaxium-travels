# Booking Agent Setup Complete

## Files Modified:

### 1. Created BookingAgent
**File:** `langgraph/src/agents/booking.py`
- Extends `BaseAgentWithMCP`
- Connects to MCP server on port 8003
- Handles flight booking requests

### 2. Updated Agent Configuration
**File:** `langgraph/src/config/agents.py`
- Added "booking" agent with MCP server URL
- Description: "Books interplanetary flights, manages reservations..."

### 3. Registered in Module
**File:** `langgraph/src/agents/__init__.py`
- Added `BookingAgent` import and export

### 4. Added to Main Application
**File:** `langgraph/src/main.py`
- Added `BookingAgent` import
- Added booking agent instantiation in `_build_agent()` function

## Configuration Required:

### `.env` file must have:
```bash
WA_MCP_SERVER_URL=http://localhost:8003/sse
```

## How to Test:

### 1. Make sure MCP server is running (Windows):
```bash
cd booking_system_backend
python mcp_sse_server.py
# Should show: Running on http://127.0.0.1:8003
```

### 2. Restart Agent Backend (WSL):
```bash
cd langgraph/
# Stop with Ctrl+C
make dev
```

### 3. Test in Browser:
Go to http://localhost:5173 and try:
```
Book me a flight from Earth to Mars. My name is John Doe and my email is john.doe@example.com
```

## Expected Behavior:

1. Supervisor receives message
2. Routes to BookingAgent (not MealAgent!)
3. BookingAgent calls MCP tools
4. Returns booking confirmation

## Troubleshooting:

If still routing to MealAgent:
1. Check agent backend logs for "BookingAgent initialized"
2. Verify MCP server is running on port 8003
3. Check `.env` has correct `WA_MCP_SERVER_URL`
4. Ensure you restarted the agent backend after changes