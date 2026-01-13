from app.api.schemas.mcp_schema import ChatRequest
from app.core.logger import get_logger
from langchain.tools import tool

from app.services.mcp_service import process_chat_request_non_stream

logger = get_logger(__name__)


# @tool(
#     description="Creates a Notion page with the provided content. Requires a title and content.",
#     parse_docstring=True,
# )
async def create_notion_page(request: ChatRequest) -> dict:
    """
    Create a Notion page with the given request that contains title, contents and type (using the ChatRequest schema).

    Args:
        request (ChatRequest): The request object containing title, contents and type.

    Returns:
        dict: A dictionary with the result of the page creation, including the page url or link or an error message.
    """
    try:
        notionResponse = await process_chat_request_non_stream(request)
        return {"answer": notionResponse.answer}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
# google doc and sheet creation tools can be added similarly in future
# @tool(
#     description="Creates a Google Doc or Google sheet with the provided content. Requires a title and content.",
#     parse_docstring=True,
# )
async def create_google_doc(request: ChatRequest) -> dict:
    """
    GCreate a Google Doc and google sheet with the given request that contains title, contents and type (using the ChatRequest schema).

    Args:
        request (ChatRequest): The request object containing title, contents and type.

    Returns:
        dict: A dictionary with the result of the document creation, including the document url or link or an error message.
    """
    try:
        # Implement Google Doc creation logic here
        googleDocSpread = await process_chat_request_non_stream(request)
        return {"answer": googleDocSpread.answer}
    except Exception as e:
        return {"status": "error", "message": str(e)}

