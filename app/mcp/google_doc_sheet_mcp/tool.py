import asyncio
import json
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from app.mcp.google_doc_sheet_mcp.server import GoogleDocsService
    
# Initialize MCP server and Google Docs/Sheets service
app = Server("google-docs-mcp")
gdocs = GoogleDocsService()


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available Google Docs & Sheets tools"""
    return [
        Tool(
            name="create-document",
            description="Create a new Google Doc",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "The title of the document"
                    },
                    "content": {
                        "type": "string",
                        "description": "Initial content for the document (optional)"
                    }
                },
                "required": ["title"]
            }
        ),
        Tool(
            name="read-document",
            description="Read the content of a Google Doc",
            inputSchema={
                "type": "object",
                "properties": {
                    "documentId": {
                        "type": "string",
                        "description": "The ID of the document to read"
                    }
                },
                "required": ["documentId"]
            }
        ),
        Tool(
            name="update-document",
            description="Update the content of a Google Doc",
            inputSchema={
                "type": "object",
                "properties": {
                    "documentId": {
                        "type": "string",
                        "description": "The ID of the document to update"
                    },
                    "content": {
                        "type": "string",
                        "description": "The new content to add or replace"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["append", "replace"],
                        "description": "Whether to append or replace content",
                        "default": "append"
                    }
                },
                "required": ["documentId", "content"]
            }
        ),
        Tool(
            name="search-documents",
            description="Search for Google Docs by name",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for document names"
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
            name="list-recent-documents",
            description="List recently modified Google Docs",
            inputSchema={
                "type": "object",
                "properties": {
                    "maxResults": {
                        "type": "integer",
                        "description": "Maximum number of documents to return",
                        "default": 20
                    }
                }
            }
        ),
        Tool(
            name="create-sheet",
            description="Create a new Google Sheet (spreadsheet)",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Spreadsheet title"},
                    "sheetName": {"type": "string", "description": "Name of the first sheet", "default": "Sheet1"},
                    "values": {
                        "type": "array",
                        "description": "2D array of initial values to write starting at A1",
                        "items": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    }
                },
                "required": ["title"]
            }
        ),
        Tool(
            name="read-sheet",
            description="Read values from a Google Sheet range (A1)",
            inputSchema={
                "type": "object",
                "properties": {
                    "spreadsheetId": {"type": "string", "description": "Spreadsheet ID"},
                    "range": {"type": "string", "description": "A1 range, e.g., Sheet1!A1:C10"}
                },
                "required": ["spreadsheetId", "range"]
            }
        ),
        Tool(
            name="update-sheet",
            description="Update or append values to a Google Sheet range",
            inputSchema={
                "type": "object",
                "properties": {
                    "spreadsheetId": {"type": "string", "description": "Spreadsheet ID"},
                    "range": {"type": "string", "description": "A1 range or sheet name for append"},
                    "values": {
                        "type": "array",
                        "description": "2D array of values",
                        "items": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "mode": {"type": "string", "enum": ["overwrite", "append"], "default": "overwrite"},
                    "inputMode": {"type": "string", "enum": ["RAW", "USER_ENTERED"], "default": "USER_ENTERED"}
                },
                "required": ["spreadsheetId", "range", "values"]
            }
        ),
        Tool(
            name="search-sheets",
            description="Search Google Sheets by name",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query for spreadsheet names"},
                    "maxResults": {"type": "integer", "description": "Maximum results", "default": 10}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="list-recent-sheets",
            description="List recently modified Google Sheets",
            inputSchema={
                "type": "object",
                "properties": {
                    "maxResults": {"type": "integer", "description": "Maximum number of spreadsheets to return", "default": 20}
                }
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls"""
    
    # Ensure user is authenticated
    if not gdocs.creds:
        gdocs.authenticate()
    
    try:
        if name == "create-document":
            result = gdocs.create_document(
                title=arguments['title'],
                content=arguments.get('content', '')
            )
        elif name == "read-document":
            result = gdocs.read_document(arguments['documentId'])
        elif name == "update-document":
            result = gdocs.update_document(
                document_id=arguments['documentId'],
                content=arguments['content'],
                mode=arguments.get('mode', 'append')
            )
        elif name == "search-documents":
            result = gdocs.search_documents(
                query=arguments['query'],
                max_results=arguments.get('maxResults', 10)
            )
        elif name == "list-recent-documents":
            result = gdocs.list_recent_documents(
                max_results=arguments.get('maxResults', 20)
            )
        elif name == "create-sheet":
            result = gdocs.create_sheet(
                title=arguments['title'],
                sheet_name=arguments.get('sheetName', 'Sheet1'),
                values=arguments.get('values')
            )
        elif name == "read-sheet":
            result = gdocs.read_sheet(
                spreadsheet_id=arguments['spreadsheetId'],
                range_a1=arguments['range']
            )
        elif name == "update-sheet":
            result = gdocs.update_sheet(
                spreadsheet_id=arguments['spreadsheetId'],
                range_a1=arguments['range'],
                values=arguments['values'],
                mode=arguments.get('mode', 'overwrite'),
                input_mode=arguments.get('inputMode', 'USER_ENTERED')
            )
        elif name == "search-sheets":
            result = gdocs.search_sheets(
                query=arguments['query'],
                max_results=arguments.get('maxResults', 10)
            )
        elif name == "list-recent-sheets":
            result = gdocs.list_recent_sheets(
                max_results=arguments.get('maxResults', 20)
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
