import asyncio
import json
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from app.mcp.gmail_mcp.server import GmailService
    
app = Server("gmail-mcp")
gmail = GmailService()


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available Gmail tools"""
    return [
        Tool(
            name="send-email",
            description="Send an email via Gmail",
            inputSchema={
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "Recipient email address"
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject"
                    },
                    "body": {
                        "type": "string",
                        "description": "Email body content"
                    },
                    "cc": {
                        "type": "string",
                        "description": "CC email address (optional)"
                    },
                    "bcc": {
                        "type": "string",
                        "description": "BCC email address (optional)"
                    },
                    "html": {
                        "type": "boolean",
                        "description": "Whether the body is HTML",
                        "default": False
                    }
                },
                "required": ["to", "subject", "body"]
            }
        ),
        Tool(
            name="list-messages",
            description="List messages from Gmail inbox",
            inputSchema={
                "type": "object",
                "properties": {
                    "maxResults": {
                        "type": "integer",
                        "description": "Maximum number of messages to return",
                        "default": 10
                    },
                    "query": {
                        "type": "string",
                        "description": "Gmail search query (optional)"
                    },
                    "labelIds": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by label IDs (optional)"
                    }
                }
            }
        ),
        Tool(
            name="get-message",
            description="Get a specific email message by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "messageId": {
                        "type": "string",
                        "description": "The ID of the message to retrieve"
                    },
                    "format": {
                        "type": "string",
                        "enum": ["minimal", "full", "raw", "metadata"],
                        "description": "Message format",
                        "default": "full"
                    }
                },
                "required": ["messageId"]
            }
        ),
        Tool(
            name="search-messages",
            description="Search for messages using Gmail query syntax",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Gmail search query (e.g., 'from:example@gmail.com', 'is:unread', 'subject:meeting')"
                    },
                    "maxResults": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="delete-message",
            description="Delete a message (move to trash)",
            inputSchema={
                "type": "object",
                "properties": {
                    "messageId": {
                        "type": "string",
                        "description": "The ID of the message to delete"
                    }
                },
                "required": ["messageId"]
            }
        ),
        Tool(
            name="modify-labels",
            description="Add or remove labels from a message",
            inputSchema={
                "type": "object",
                "properties": {
                    "messageId": {
                        "type": "string",
                        "description": "The ID of the message"
                    },
                    "addLabels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Label IDs to add"
                    },
                    "removeLabels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Label IDs to remove"
                    }
                },
                "required": ["messageId"]
            }
        ),
        Tool(
            name="list-labels",
            description="List all Gmail labels",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="create-draft",
            description="Create a draft email",
            inputSchema={
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "Recipient email address"
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject"
                    },
                    "body": {
                        "type": "string",
                        "description": "Email body content"
                    },
                    "cc": {
                        "type": "string",
                        "description": "CC email address (optional)"
                    },
                    "bcc": {
                        "type": "string",
                        "description": "BCC email address (optional)"
                    },
                    "html": {
                        "type": "boolean",
                        "description": "Whether the body is HTML",
                        "default": False
                    }
                },
                "required": ["to", "subject", "body"]
            }
        ),
        Tool(
            name="reply-to-message",
            description="Reply to an existing message",
            inputSchema={
                "type": "object",
                "properties": {
                    "messageId": {
                        "type": "string",
                        "description": "The ID of the message to reply to"
                    },
                    "body": {
                        "type": "string",
                        "description": "Reply body content"
                    },
                    "html": {
                        "type": "boolean",
                        "description": "Whether the body is HTML",
                        "default": False
                    }
                },
                "required": ["messageId", "body"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls"""
    
    # Ensure user is authenticated
    if not gmail.creds:
        gmail.authenticate()
    
    try:
        if name == "send-email":
            result = gmail.send_email(
                to=arguments['to'],
                subject=arguments['subject'],
                body=arguments['body'],
                cc=arguments.get('cc'),
                bcc=arguments.get('bcc'),
                html=arguments.get('html', False)
            )
        elif name == "list-messages":
            result = gmail.list_messages(
                max_results=arguments.get('maxResults', 10),
                query=arguments.get('query'),
                label_ids=arguments.get('labelIds')
            )
        elif name == "get-message":
            result = gmail.get_message(
                message_id=arguments['messageId'],
                format=arguments.get('format', 'full')
            )
        elif name == "search-messages":
            result = gmail.search_messages(
                query=arguments['query'],
                max_results=arguments.get('maxResults', 10)
            )
        elif name == "delete-message":
            result = gmail.delete_message(
                message_id=arguments['messageId']
            )
        elif name == "modify-labels":
            result = gmail.modify_labels(
                message_id=arguments['messageId'],
                add_labels=arguments.get('addLabels'),
                remove_labels=arguments.get('removeLabels')
            )
        elif name == "list-labels":
            result = gmail.list_labels()
        elif name == "create-draft":
            result = gmail.create_draft(
                to=arguments['to'],
                subject=arguments['subject'],
                body=arguments['body'],
                cc=arguments.get('cc'),
                bcc=arguments.get('bcc'),
                html=arguments.get('html', False)
            )
        elif name == "reply-to-message":
            result = gmail.reply_to_message(
                message_id=arguments['messageId'],
                body=arguments['body'],
                html=arguments.get('html', False)
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
    asyncio.run(main())