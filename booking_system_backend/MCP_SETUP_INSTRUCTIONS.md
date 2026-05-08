# MCP Server Setup for IBM Agent Studio

This guide explains how to connect your Galaxium Booking System to IBM Agent Studio using the Model Context Protocol (MCP).

## Two MCP Server Options

### Option 1: Stdio MCP Server (Recommended for IBM Agent Studio)

The stdio server runs as a standalone process and communicates via standard input/output.

#### Setup Steps:

1. **Ensure your backend is set up:**
   ```bash
   cd booking_system_backend
   pip install -r requirements.txt
   ```

2. **Test the stdio server locally:**
   ```bash
   python mcp_stdio_server.py
   ```
   Press Ctrl+C to stop.

3. **Configure in IBM Agent Studio:**
   - Go to: https://agentstudio.servicesessentials.ibm.com/create/mcp-servers
   - Click "Add Gateway"
   - Fill in the form:
     - **Name:** Galaxium Booking System
     - **Description:** Interplanetary flight booking system with 7 MCP tools
     - **Transport Type:** `Stdio`
     - **Command:** 
       ```
       python C:\Users\CHRISTIANGERONEONA\Documents\IBM\AI\agentic_ai_watsonx_orchestrate_2026\practice-bob\galaxium-travels\booking_system_backend\mcp_stdio_server.py
       ```
       (Adjust the path to match your actual file location)
     - **Visibility:** Team
     - **Authentication:** None

4. **Click "Add Gateway"**

---

### Option 2: HTTP MCP Server (Alternative)

The HTTP server is integrated into your FastAPI application.

#### Setup Steps:

1. **Start your FastAPI server:**
   ```bash
   cd booking_system_backend
   python server.py
   ```

2. **Expose it publicly with ngrok:**
   ```bash
   # In another terminal
   cd C:\Users\CHRISTIANGERONEONA\Downloads
   ngrok.exe http 8080
   ```

3. **Copy the ngrok URL** (e.g., `https://abc123.ngrok-free.app`)

4. **Configure in IBM Agent Studio:**
   - **Name:** Galaxium Booking System
   - **Description:** Interplanetary flight booking system
   - **URL:** `https://your-ngrok-url.ngrok-free.app/mcp`
   - **Transport Type:** `HTTP`
   - **Authentication:** None

---

## Available MCP Tools

Once connected, AI agents can use these 7 tools:

1. **list_flights()** - List all available flights
2. **book_flight(user_id, name, flight_id, infant_count)** - Book a flight with optional infants
3. **get_bookings(user_id)** - Get all bookings for a user
4. **cancel_booking(booking_id)** - Cancel a booking
5. **register_user(name, email)** - Register a new user
6. **get_user_id(name, email)** - Get user information
7. **get_discount_by_booking(booking_id)** - Get discount details for a booking

---

## Example Agent Interactions

### Example 1: Book a Flight
```
User: "Book a flight from Earth to Mars for John Doe"

Agent:
1. Calls list_flights() → finds available flights
2. Calls get_user_id("John Doe", "john@email.com") → gets user_id
3. Calls book_flight(user_id=1, name="John Doe", flight_id=3, infant_count=0)
4. Returns: "Flight booked! Booking ID: 42"
```

### Example 2: Book with Infants
```
User: "Book flight #5 for Jane Smith with 2 infants"

Agent:
1. Calls get_user_id("Jane Smith", "jane@email.com")
2. Calls book_flight(user_id=2, name="Jane Smith", flight_id=5, infant_count=2)
3. Calls get_discount_by_booking(booking_id=43) → shows infant discount
4. Returns: "Booked with 2 infants. Discount applied: $X"
```

### Example 3: View Bookings
```
User: "Show me all bookings for user ID 1"

Agent:
1. Calls get_bookings(user_id=1)
2. Returns: List of all bookings with details
```

---

## Troubleshooting

### Stdio Server Issues

**Problem:** Command not found
- **Solution:** Use the full absolute path to `mcp_stdio_server.py`

**Problem:** Import errors
- **Solution:** Ensure you're in the correct directory and all dependencies are installed:
  ```bash
  cd booking_system_backend
  pip install -r requirements.txt
  ```

### HTTP Server Issues

**Problem:** 502 Bad Gateway
- **Solution:** 
  1. Ensure FastAPI server is running (`python server.py`)
  2. Ensure ngrok is running (`ngrok.exe http 8080`)
  3. Use the correct ngrok URL (changes each restart)

**Problem:** /mcp/sse returns 404
- **Solution:** Use `/mcp` endpoint instead, not `/mcp/sse`

---

## Notes

- **Stdio is recommended** for IBM Agent Studio as it's more reliable
- **HTTP requires ngrok** to expose your local server publicly
- **Keep servers running** while agents are using them
- **Database is SQLite** - located at `booking.db` in the backend directory

---

## Support

For issues or questions, refer to:
- FastMCP documentation: https://github.com/jlowin/fastmcp
- IBM Agent Studio docs: https://agentstudio.servicesessentials.ibm.com/docs