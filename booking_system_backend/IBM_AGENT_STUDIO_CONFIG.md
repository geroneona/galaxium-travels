# IBM Agent Studio MCP Configuration

## ✅ Correct Configuration

Based on IBM Agent Studio's security requirements, use these exact settings:

### STDIO Transport Configuration

**Name:**
```
galaxium-travels
```

**Command:**
```
python
```

**Arguments:** (Click the + button to add this as a single argument)
```
C:\Users\CHRISTIANGERONEONA\Documents\IBM\AI\agentic_ai_watsonx_orchestrate_2026\practice-bob\galaxium-travels\booking_system_backend\mcp_stdio_server.py
```

**Environment Variables:** (Leave empty)

---

## 📋 Step-by-Step Setup

1. **Open IBM Agent Studio**
   - Go to: https://agentstudio.servicesessentials.ibm.com/create/mcp-servers
   - Click "Add MCP Server"

2. **Select STDIO Tab**

3. **Fill in the form:**
   - **Name:** `galaxium-travels`
   - **Command:** `python` (just the word "python", nothing else)
   - **Arguments:** Click the `+` button and add:
     ```
     C:\Users\CHRISTIANGERONEONA\Documents\IBM\AI\agentic_ai_watsonx_orchestrate_2026\practice-bob\galaxium-travels\booking_system_backend\mcp_stdio_server.py
     ```
   - **Environment Variables:** Leave empty

4. **Click "Add Server"**

---

## 🔍 Why This Works

IBM Agent Studio only allows these commands for security:
- `bash`
- `cmd`
- `docker`
- `node`
- `npx`
- `python` ✅
- `python3`
- `sh`
- `uvx`

By using `python` as the command and the script path as an argument, we comply with their security policy.

---

## ✅ Verification

Your MCP server is working correctly! The terminal shows:
```
Starting MCP server 'Galaxium Booking System' with transport 'stdio'
```

This confirms the server runs successfully when called with `python mcp_stdio_server.py`.

---

## 🎯 Available Tools

Once configured, AI agents can use these 7 tools:

1. **list_flights()** - List all available interplanetary flights
2. **book_flight(user_id, name, flight_id, infant_count)** - Book a flight with optional infants
3. **get_bookings(user_id)** - Retrieve all bookings for a user
4. **cancel_booking(booking_id)** - Cancel an existing booking
5. **register_user(name, email)** - Register a new user account
6. **get_user_id(name, email)** - Get user information by name and email
7. **get_discount_by_booking(booking_id)** - Get discount details for bookings with infants

---

## 🚀 Example Usage

Once connected, you can ask the AI agent:

```
"Book a flight from Earth to Mars for John Doe with 2 infants"
```

The agent will:
1. Call `list_flights()` to find Earth→Mars flights
2. Call `get_user_id("John Doe", "john@email.com")` to get the user ID
3. Call `book_flight(user_id=1, name="John Doe", flight_id=3, infant_count=2)`
4. Call `get_discount_by_booking(booking_id)` to show the infant discount
5. Return the booking confirmation with discount details

---

## 📝 Notes

- The MCP server must be able to access the SQLite database (`booking.db`)
- Make sure all Python dependencies are installed (`pip install -r requirements.txt`)
- The server runs in the background when IBM Agent Studio needs it
- No need to manually start the server - IBM Agent Studio handles that

---

## 🐛 Troubleshooting

**Problem:** "Command not allowed for security reasons"
- **Solution:** Use `python` as the command, not the full path or script name

**Problem:** Import errors when server starts
- **Solution:** Ensure you're in a virtual environment with all dependencies:
  ```bash
  cd booking_system_backend
  python -m venv venv
  venv\Scripts\activate
  pip install -r requirements.txt
  ```

**Problem:** Database not found
- **Solution:** Run `python server.py` once to initialize the database, then stop it

---

## ✨ Success Indicator

When properly configured, IBM Agent Studio will show:
- ✅ Server status: Connected
- ✅ 7 tools available
- ✅ Ready to use in flows