# Port Configuration Summary

## Updated Ports (to avoid conflicts)

### Backend Services

1. **Booking System REST API** (`server.py`)
   - **Old Port:** 8080
   - **New Port:** 8082
   - **Run:** `python server.py`
   - **Access:** http://localhost:8082
   - **Swagger UI:** http://localhost:8082/docs

2. **MCP SSE Server** (`mcp_sse_server.py`)
   - **Old Port:** 8000
   - **New Port:** 8003
   - **Run:** `python mcp_sse_server.py`
   - **Access:** http://localhost:8003/sse
   - **Purpose:** Provides tools to IBM Agentic App Studio

### Frontend

3. **Booking System Frontend**
   - **Old Port:** 5173 (default Vite)
   - **New Port:** 5174
   - **Run:** `npm run dev`
   - **Access:** http://localhost:5174
   - **Backend API:** Configured to connect to port 8082

### Agent Studio (Separate Project)

4. **Agent Studio Backend**
   - **Port:** 8001
   - **Location:** `agents/agentstudio-external-agent-boilerplate/.../langgraph/`
   - **Run:** `make dev`

5. **Agent Studio Frontend**
   - **Port:** 5173
   - **Location:** `agents/agentstudio-external-agent-boilerplate/frontend/`
   - **Run:** `npm run dev`

## Port Conflict Resolution

### Why These Changes?

- **8080 → 8082:** WSL was using port 8080
- **8000 → 8003:** WSL was using port 8000
- **5173 → 5174:** Agent Studio frontend was using 5173

### Running All Services Together

```bash
# Terminal 1 - Booking Backend API
cd booking_system_backend
python server.py
# Running on http://localhost:8082

# Terminal 2 - MCP SSE Server (for Agent Studio)
cd booking_system_backend
python mcp_sse_server.py
# Running on http://localhost:8003

# Terminal 3 - Booking Frontend
cd booking_system_frontend
npm run dev
# Running on http://localhost:5174

# Terminal 4 - Agent Studio Backend (WSL)
cd agents/.../langgraph
make dev
# Running on http://localhost:8001

# Terminal 5 - Agent Studio Frontend (WSL)
cd agents/.../frontend
npm run dev
# Running on http://localhost:5173
```

## Environment Variables

### Booking Frontend
No `.env` needed - defaults to `http://localhost:8082`

Or create `.env`:
```
VITE_API_URL=http://localhost:8082
```

### Agent Studio Frontend
Create `.env`:
```
VITE_BACKEND_URL=http://localhost:8001
```

### Agent Studio Backend
Create `.env` with:
```
PORT=8001
WA_MCP_SERVER_URL=http://localhost:8003/sse
```

## Quick Reference

| Service | Port | Purpose |
|---------|------|---------|
| Booking API | 8082 | REST API for booking system |
| MCP Server | 8003 | Tools for AI agents |
| Booking UI | 5174 | User interface for bookings |
| Agent Backend | 8001 | AI agent orchestration |
| Agent UI | 5173 | Chat interface for agent |

## Troubleshooting

### Check if port is in use:
```bash
# Windows
netstat -ano | findstr :8082
netstat -ano | findstr :8003

# WSL/Linux
sudo lsof -i :8082
sudo lsof -i :8003
```

### Kill process using port:
```bash
# Windows
taskkill /PID <PID> /F

# WSL/Linux
sudo kill -9 <PID>