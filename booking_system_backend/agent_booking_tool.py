#!/usr/bin/env python3
"""
Agent Booking Tool Demonstration Script

This script demonstrates how an AI agent would use the book_flight_remote MCP tool
to book flights on a remote API server. It showcases the complete booking workflow
including user registration, flight search, booking, and discount retrieval.

The book_flight_remote tool is designed to be used by AI agents in IBM watsonx Orchestrate
or other agent frameworks that support MCP (Model Context Protocol) tools.

Usage:
    python agent_booking_tool.py

Requirements:
    - requests library (pip install requests)
    - Access to the MCP server (mcp_stdio_server.py)
    - Remote API server running (or ngrok tunnel configured)

Author: Bob (AI Software Engineer)
Date: 2026-05-08
"""

import json
import sys
from typing import Dict, Any, Optional

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def print_section_header(title: str) -> None:
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_booking_summary(result: Dict[str, Any]) -> None:
    """
    Print a comprehensive booking summary from the tool result.
    
    Args:
        result: The booking result dictionary from book_flight_remote
    """
    print_section_header("BOOKING SUMMARY")
    
    # User Information
    print("\n📋 USER INFORMATION")
    user = result.get('user', {})
    print(f"  Name:     {user.get('name')}")
    print(f"  Email:    {user.get('email')}")
    print(f"  User ID:  {user.get('user_id')}")
    
    # Flight Details
    print("\n✈️  FLIGHT DETAILS")
    flight = result.get('flight', {})
    print(f"  Flight ID:       {flight.get('flight_id')}")
    print(f"  Route:           {flight.get('origin')} → {flight.get('destination')}")
    print(f"  Departure:       {flight.get('departure_time')}")
    print(f"  Arrival:         {flight.get('arrival_time')}")
    print(f"  Base Price:      ${flight.get('base_price'):,}")
    print(f"  Seats Available: {flight.get('seats_available')}")
    
    # Booking Confirmation
    print("\n✅ BOOKING CONFIRMATION")
    booking = result.get('booking', {})
    print(f"  Booking ID:    {booking.get('booking_id')}")
    print(f"  Status:        {booking.get('status')}")
    print(f"  Booking Time:  {booking.get('booking_time')}")
    print(f"  Infant Count:  {booking.get('infant_count')}")
    
    # Pricing Breakdown
    print("\n💰 PRICING BREAKDOWN")
    pricing = result.get('pricing', {})
    print(f"  Base Price:        ${pricing.get('base_price'):,}")
    print(f"  Infant Count:      {pricing.get('infant_count')}")
    print(f"  Discount Applied:  {'Yes' if pricing.get('discount_applied') else 'No'}")
    
    if pricing.get('discount_applied'):
        discount = result.get('discount', {})
        print(f"\n  💸 INFANT DISCOUNT DETAILS")
        print(f"    Discount ID:                {discount.get('discount_id')}")
        print(f"    Original Price per Infant:  ${discount.get('original_price'):,}")
        print(f"    Discounted Price per Infant: ${discount.get('discounted_price_per_infant'):,}")
        print(f"    Discount Percentage:        {discount.get('discount_percentage')}%")
        print(f"    Total Discount Price:       ${discount.get('total_discount_price'):,}")
        print(f"    Total Savings:              ${pricing.get('savings'):,}")
    
    print(f"\n  🎯 TOTAL COST: ${pricing.get('total_cost'):,}")
    print("\n" + "=" * 80)


def example_1_basic_booking() -> None:
    """
    Example 1: Basic booking without infants
    
    This demonstrates the simplest use case of the book_flight_remote tool.
    """
    print_section_header("EXAMPLE 1: Basic Booking (No Infants)")
    
    print("\n📝 Scenario:")
    print("  An agent needs to book a flight for a user from Earth to Mars")
    print("  without any infant passengers.")
    
    print("\n🤖 Agent Action:")
    print("  The agent would call the book_flight_remote tool with these parameters:")
    
    params = {
        "user_name": "John Doe",
        "user_email": "john.doe@example.com",
        "origin": "Earth",
        "destination": "Mars",
        "infant_count": 0,
        "base_url": "https://brownnose-igloo-ideally.ngrok-free.dev"
    }
    
    print(f"\n  Parameters:")
    for key, value in params.items():
        print(f"    {key}: {value}")
    
    print("\n📤 Expected Tool Call (JSON format):")
    print(json.dumps(params, indent=2))
    
    print("\n📥 Expected Response:")
    print("  The tool will return a comprehensive booking summary including:")
    print("    ✓ User registration/verification")
    print("    ✓ Flight search and selection")
    print("    ✓ Booking confirmation")
    print("    ✓ Total cost (base price only)")


def example_2_booking_with_infants() -> None:
    """
    Example 2: Booking with infant passengers
    
    This demonstrates how the tool handles infant discounts (75% off).
    """
    print_section_header("EXAMPLE 2: Booking with Infants (Discount Applied)")
    
    print("\n📝 Scenario:")
    print("  An agent needs to book a flight for Alice from Earth to Mars")
    print("  with 3 infant passengers. Infants receive a 75% discount.")
    
    print("\n🤖 Agent Action:")
    print("  The agent would call the book_flight_remote tool with these parameters:")
    
    params = {
        "user_name": "Alice",
        "user_email": "alice@email.com",
        "origin": "Earth",
        "destination": "Mars",
        "infant_count": 3,
        "base_url": "https://brownnose-igloo-ideally.ngrok-free.dev"
    }
    
    print(f"\n  Parameters:")
    for key, value in params.items():
        print(f"    {key}: {value}")
    
    print("\n📤 Expected Tool Call (JSON format):")
    print(json.dumps(params, indent=2))
    
    print("\n📥 Expected Response:")
    print("  The tool will return a comprehensive booking summary including:")
    print("    ✓ User registration/verification")
    print("    ✓ Flight search and selection")
    print("    ✓ Booking confirmation with infant count")
    print("    ✓ Discount details (75% off per infant)")
    print("    ✓ Total cost with savings breakdown")
    
    print("\n💡 Pricing Example (assuming $1,000 base price):")
    print("    Base Price per Infant:      $1,000")
    print("    Discounted Price (75% off): $250")
    print("    Total for 3 Infants:        $750")
    print("    Total Savings:              $2,250")


def example_3_different_routes() -> None:
    """
    Example 3: Booking different routes
    
    This demonstrates how the tool can handle various origin/destination combinations.
    """
    print_section_header("EXAMPLE 3: Different Routes")
    
    print("\n📝 Scenario:")
    print("  An agent needs to book flights on different routes for various users.")
    
    routes = [
        {
            "user_name": "Bob Smith",
            "user_email": "bob.smith@example.com",
            "origin": "Mars",
            "destination": "Jupiter",
            "infant_count": 1,
            "description": "Mars to Jupiter with 1 infant"
        },
        {
            "user_name": "Carol White",
            "user_email": "carol.white@example.com",
            "origin": "Earth",
            "destination": "Venus",
            "infant_count": 0,
            "description": "Earth to Venus, no infants"
        },
        {
            "user_name": "David Brown",
            "user_email": "david.brown@example.com",
            "origin": "Jupiter",
            "destination": "Saturn",
            "infant_count": 2,
            "description": "Jupiter to Saturn with 2 infants"
        }
    ]
    
    print("\n🤖 Agent Actions:")
    for i, route in enumerate(routes, 1):
        print(f"\n  Booking {i}: {route['description']}")
        print(f"    User:        {route['user_name']} ({route['user_email']})")
        print(f"    Route:       {route['origin']} → {route['destination']}")
        print(f"    Infants:     {route['infant_count']}")
        print(f"    Tool Call:   book_flight_remote(...)")


def example_4_error_handling() -> None:
    """
    Example 4: Error handling scenarios
    
    This demonstrates how the tool handles various error conditions.
    """
    print_section_header("EXAMPLE 4: Error Handling")
    
    print("\n📝 Scenario:")
    print("  The tool includes comprehensive error handling for various failure modes.")
    
    print("\n⚠️  Common Error Scenarios:")
    
    errors = [
        {
            "scenario": "No flights available",
            "cause": "No flights match the origin/destination criteria",
            "error": "No flights found from Earth to Pluto"
        },
        {
            "scenario": "Connection timeout",
            "cause": "Remote server is not responding",
            "error": "Request timeout: Could not connect to [base_url]"
        },
        {
            "scenario": "User registration failed",
            "cause": "Email already exists with different name",
            "error": "User registration failed: Email already registered"
        },
        {
            "scenario": "Booking failed",
            "cause": "No seats available on the flight",
            "error": "Booking failed: No seats available"
        },
        {
            "scenario": "Invalid parameters",
            "cause": "Missing required parameters",
            "error": "Booking failed: Missing required parameter"
        }
    ]
    
    for i, error in enumerate(errors, 1):
        print(f"\n  {i}. {error['scenario']}")
        print(f"     Cause:  {error['cause']}")
        print(f"     Error:  {error['error']}")
    
    print("\n💡 Best Practices:")
    print("    ✓ Always wrap tool calls in try-except blocks")
    print("    ✓ Check the 'success' field in the response")
    print("    ✓ Provide clear error messages to users")
    print("    ✓ Implement retry logic for transient failures")


def example_5_agent_workflow() -> None:
    """
    Example 5: Complete agent workflow
    
    This demonstrates how an agent would use the tool in a conversational context.
    """
    print_section_header("EXAMPLE 5: Complete Agent Workflow")
    
    print("\n📝 Scenario:")
    print("  A user interacts with an AI agent to book a flight.")
    
    print("\n💬 Conversation Flow:")
    
    conversation = [
        {
            "role": "User",
            "message": "I need to book a flight from Earth to Mars for my family."
        },
        {
            "role": "Agent",
            "message": "I'd be happy to help! Can you provide your name and email?"
        },
        {
            "role": "User",
            "message": "My name is Sarah Johnson and my email is sarah.j@example.com"
        },
        {
            "role": "Agent",
            "message": "Great! How many infants will be traveling with you?"
        },
        {
            "role": "User",
            "message": "I have 2 infants."
        },
        {
            "role": "Agent",
            "message": "Perfect! Let me book that for you. Infants receive a 75% discount.",
            "action": "Calls book_flight_remote tool"
        },
        {
            "role": "Agent",
            "message": "✅ Booking confirmed! Your booking ID is 12345.\n" +
                      "Flight: Earth → Mars\n" +
                      "Departure: 2026-06-15 10:00:00\n" +
                      "Base Price: $1,000\n" +
                      "Infant Discount: $1,500 savings\n" +
                      "Total Cost: $500 for 2 infants"
        }
    ]
    
    for i, turn in enumerate(conversation, 1):
        print(f"\n  {turn['role']}: {turn['message']}")
        if 'action' in turn:
            print(f"           [{turn['action']}]")


def example_6_mcp_integration() -> None:
    """
    Example 6: MCP Integration Details
    
    This explains how the tool integrates with MCP servers and agent frameworks.
    """
    print_section_header("EXAMPLE 6: MCP Integration")
    
    print("\n📝 Overview:")
    print("  The book_flight_remote tool is exposed via the Model Context Protocol (MCP)")
    print("  and can be used by any MCP-compatible agent framework.")
    
    print("\n🔧 Integration Steps:")
    print("  1. Start the MCP server:")
    print("     $ python mcp_stdio_server.py")
    
    print("\n  2. Configure your agent framework to connect to the MCP server")
    print("     (See IBM_AGENT_STUDIO_CONFIG.md for IBM watsonx Orchestrate)")
    
    print("\n  3. The agent can now discover and use the book_flight_remote tool")
    
    print("\n📋 Tool Signature:")
    print("  Name: book_flight_remote")
    print("  Parameters:")
    print("    - user_name: str (required)")
    print("    - user_email: str (required)")
    print("    - origin: str (required)")
    print("    - destination: str (required)")
    print("    - infant_count: int (optional, default: 0)")
    print("    - base_url: str (optional, default: ngrok URL)")
    
    print("\n  Returns: Dict[str, Any]")
    print("    - success: bool")
    print("    - booking_id: int")
    print("    - user: dict (user_id, name, email)")
    print("    - flight: dict (flight details)")
    print("    - booking: dict (booking details)")
    print("    - pricing: dict (cost breakdown)")
    print("    - discount: dict (optional, if infants)")
    
    print("\n🔐 Security Considerations:")
    print("    ✓ Use HTTPS for production (ngrok provides this)")
    print("    ✓ Validate email addresses")
    print("    ✓ Implement rate limiting on the API server")
    print("    ✓ Use authentication tokens for production deployments")


def main() -> None:
    """
    Main function to run all demonstration examples.
    """
    print("\n" + "=" * 80)
    print("  AGENT BOOKING TOOL DEMONSTRATION")
    print("  book_flight_remote MCP Tool Usage Examples")
    print("=" * 80)
    
    print("\n📚 This script demonstrates how AI agents use the book_flight_remote tool")
    print("   to book flights on a remote API server with comprehensive error handling")
    print("   and discount support for infant passengers.")
    
    # Run all examples
    example_1_basic_booking()
    example_2_booking_with_infants()
    example_3_different_routes()
    example_4_error_handling()
    example_5_agent_workflow()
    example_6_mcp_integration()
    
    # Final notes
    print_section_header("ADDITIONAL RESOURCES")
    print("\n📖 Documentation:")
    print("    - MCP_SETUP_INSTRUCTIONS.md: MCP server setup guide")
    print("    - IBM_AGENT_STUDIO_CONFIG.md: IBM watsonx Orchestrate configuration")
    print("    - DISCOUNT_SYSTEM_DOCUMENTATION.md: Discount system details")
    print("    - INFANT_BOOKING_FEATURE.md: Infant booking feature documentation")
    
    print("\n🔗 Related Files:")
    print("    - mcp_stdio_server.py: MCP server with book_flight_remote tool")
    print("    - book_alice_flight.py: Direct API usage example")
    print("    - server.py: FastAPI backend server")
    
    print("\n💡 Tips for Agent Developers:")
    print("    1. Always validate user input before calling the tool")
    print("    2. Handle errors gracefully and provide clear feedback")
    print("    3. Use the comprehensive response to provide detailed confirmations")
    print("    4. Consider implementing retry logic for transient failures")
    print("    5. Test with various scenarios including edge cases")
    
    print("\n" + "=" * 80)
    print("  End of Demonstration")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()

# Made with Bob