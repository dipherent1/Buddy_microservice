import asyncio
from langchain_google_genai import ChatGoogleGenerativeAI
from mcp_use import MCPAgent, MCPClient

config = {
    "mcpServers": {
        "google-calendar": {
            "command": "python",
            "args": ["app.py"],
        }
    }
}


async def main():
    print("🚀 Starting Google Calendar MCP Client...")
    print("Note: If this is your first time, a browser window will open for authentication.\n")

    # Create client and agent
    client = MCPClient.from_dict(config)
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.7,
    )
    agent = MCPAgent(llm=llm, client=client)

    try:
        # Example 1: Ask the agent to list upcoming events
        print("📅 Listing your next 5 events in the coming week...")
        result = await agent.run(
            "List my next 5 Google Calendar events happening within the next 7 days. Today is 11/03/2025."
        )
        print(f"Result: {result}\n")
        
        # Example 2: Ask the agent to create a new event
        print("🆕 Creating a new event on your Google Calendar...")
        result = await agent.run(
            "Create a new event on my Google Calendar titled 'Team Meeting' on 11/05/2025 from 10:00 AM to 11:00 AM with a description 'Monthly sync-up meeting with the team.'"
        )
        print(f"Result: {result}\n")
    finally:
        await client.close_all_sessions()
        print("✅ Done!")


if __name__ == "__main__":
    asyncio.run(main())