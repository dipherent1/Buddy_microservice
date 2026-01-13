import json
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from app.core.logger import get_logger
from app.mcp.google_calendar_mcp.server import GoogleCalendarService

"""
Initialize logging before importing the server module so any module-level logs
in server.py (e.g., path resolutions) are emitted with the configured handlers.
"""


logger = get_logger(__name__)

logger.info("Starting Google Calendar MCP server...")

logger.info("Imported GoogleCalendarService successfully.")
# Initialize MCP server and Google Calendar service

app = Server("google_calendar_mcp")
gcal = GoogleCalendarService()
logger.info("Initialized GoogleCalendarService successfully., %s", gcal)


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available Google Calendar tools"""
    return [
        Tool(
            name="list-calendars",
            description="List all accessible Google Calendars",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="list-events",
            description="List events from a calendar",
            inputSchema={
                "type": "object",
                "properties": {
                    "calendarId": {
                        "type": "string",
                        "description": "Calendar ID (default: 'primary')",
                        "default": "primary"
                    },
                    "maxResults": {
                        "type": "number",
                        "description": "Maximum number of events to return",
                        "default": 10
                    },
                    "timeMin": {
                        "type": "string",
                        "description": "Start time (ISO 8601 format)"
                    },
                    "timeMax": {
                        "type": "string",
                        "description": "End time (ISO 8601 format)"
                    }
                }
            }
        ),
        Tool(
            name="create-event",
            description="Create a new calendar event",
            inputSchema={
                "type": "object",
                "properties": {
                    "calendarId": {
                        "type": "string",
                        "description": "Calendar ID",
                        "default": "primary"
                    },
                    "summary": {
                        "type": "string",
                        "description": "Event title"
                    },
                    "description": {
                        "type": "string",
                        "description": "Event description"
                    },
                    "startTime": {
                        "type": "string",
                        "description": "Start time (ISO 8601 format)"
                    },
                    "endTime": {
                        "type": "string",
                        "description": "End time (ISO 8601 format)"
                    },
                    "location": {
                        "type": "string",
                        "description": "Event location"
                    },
                    "attendees": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of attendee email addresses"
                    },
                    "timezone": {
                        "type": "string",
                        "description": "Timezone (default: UTC)",
                        "default": "UTC"
                    }
                },
                "required": ["summary", "startTime", "endTime"]
            }
        ),
        Tool(
            name="update-event",
            description="Update an existing calendar event",
            inputSchema={
                "type": "object",
                "properties": {
                    "calendarId": {
                        "type": "string",
                        "description": "Calendar ID",
                        "default": "primary"
                    },
                    "eventId": {
                        "type": "string",
                        "description": "Event ID to update"
                    },
                    "summary": {
                        "type": "string",
                        "description": "New event title"
                    },
                    "description": {
                        "type": "string",
                        "description": "New event description"
                    },
                    "startTime": {
                        "type": "string",
                        "description": "New start time (ISO 8601)"
                    },
                    "endTime": {
                        "type": "string",
                        "description": "New end time (ISO 8601)"
                    },
                    "location": {
                        "type": "string",
                        "description": "New location"
                    },
                    "timezone": {
                        "type": "string",
                        "description": "Timezone",
                        "default": "UTC"
                    }
                },
                "required": ["eventId"]
            }
        ),
        Tool(
            name="delete-event",
            description="Delete a calendar event",
            inputSchema={
                "type": "object",
                "properties": {
                    "calendarId": {
                        "type": "string",
                        "description": "Calendar ID",
                        "default": "primary"
                    },
                    "eventId": {
                        "type": "string",
                        "description": "Event ID to delete"
                    }
                },
                "required": ["eventId"]
            }
        ),
        Tool(
            name="search-events",
            description="Search for calendar events",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "calendarId": {
                        "type": "string",
                        "description": "Calendar ID",
                        "default": "primary"
                    },
                    "maxResults": {
                        "type": "number",
                        "description": "Maximum results",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get-free-busy",
            description="Check free/busy status for calendars",
            inputSchema={
                "type": "object",
                "properties": {
                    "timeMin": {
                        "type": "string",
                        "description": "Start time (ISO 8601)"
                    },
                    "timeMax": {
                        "type": "string",
                        "description": "End time (ISO 8601)"
                    },
                    "calendarIds": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of calendar IDs to check"
                    }
                },
                "required": ["timeMin", "timeMax"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls"""

    # Ensure authentication
    if not gcal.service:
        gcal.authenticate()

    try:
        if name == "list-calendars":
            result = gcal.list_calendars()

        elif name == "list-events":
            result = gcal.list_events(
                calendar_id=arguments.get('calendarId', 'primary'),
                max_results=arguments.get('maxResults', 10),
                time_min=arguments.get('timeMin'),
                time_max=arguments.get('timeMax')
            )

        elif name == "create-event":
            result = gcal.create_event(
                calendar_id=arguments.get('calendarId', 'primary'),
                summary=arguments['summary'],
                description=arguments.get('description', ''),
                start_time=arguments['startTime'],
                end_time=arguments['endTime'],
                location=arguments.get('location', ''),
                attendees=arguments.get('attendees', []),
                timezone=arguments.get('timezone', 'UTC')
            )

        elif name == "update-event":
            result = gcal.update_event(
                calendar_id=arguments.get('calendarId', 'primary'),
                event_id=arguments['eventId'],
                summary=arguments.get('summary'),
                description=arguments.get('description'),
                start_time=arguments.get('startTime'),
                end_time=arguments.get('endTime'),
                location=arguments.get('location'),
                timezone=arguments.get('timezone', 'UTC')
            )

        elif name == "delete-event":
            result = gcal.delete_event(
                calendar_id=arguments.get('calendarId', 'primary'),
                event_id=arguments['eventId']
            )

        elif name == "search-events":
            result = gcal.search_events(
                query=arguments['query'],
                calendar_id=arguments.get('calendarId', 'primary'),
                max_results=arguments.get('maxResults', 10)
            )

        elif name == "get-free-busy":
            result = gcal.get_free_busy(
                time_min=arguments['timeMin'],
                time_max=arguments['timeMax'],
                calendar_ids=arguments.get('calendarIds', ['primary'])
            )

        else:
            raise ValueError(f"Unknown tool: {name}")

        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]

    except Exception as e:
        return [TextContent(
            type="text",
            text=json.dumps({"error": str(e)}, indent=2)
        )]


async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
