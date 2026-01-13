import logging
import asyncio
import time
from app.api.schemas.mcp_schema import (
    ChatRequest, ChatResponse,
)
from app.mcp.client import get_mcp_client
from app.mcp.agent import get_or_create_agent
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)

def _build_instruction(request: ChatRequest) -> str:
    """Construct an instruction string for the MCP agent based on request.type."""
    t = (request.type or "").lower()
    title = request.title
    contents = request.contents

    if t in {"notion", "notion-page", "notion_doc"}:
        return (
            f"Task: Create or update a Notion page.\n"
            f"Title: {title}\n"
            f"Contents: {contents}\n\n"
            "Use the available Notion tools to perform this. If a page with the given title exists, update it; otherwise create it. "
            "Return ONLY the newly created or updated Notion page URL/link in your final answer."
        )
    elif t in {"google-docs", "google-doc", "gdoc", "doc"}:
        return (
            f"Task: Create or update a Google Doc.\n"
            f"Title: {title}\n"
            f"Contents: {contents}\n\n"
            "Use the Google Docs tools. If a document with the given title exists, update (append) the contents; "
            "otherwise create a new document with that title and insert the contents. "
            "Return ONLY the Google Doc URL in your final answer."
        )
    elif t in {"google-sheets", "google-sheet", "gsheet", "sheet"}:
        return (
            f"Task: Create or update a Google Sheet.\n"
            f"Title: {title}\n"
            f"Contents: {contents}\n\n"
            "Use the Google Sheets tools. If a spreadsheet with the given title exists, update the first sheet; "
            "otherwise create a new spreadsheet named with the given title. "
            "If contents describe a table, parse it into rows and write starting at A1; if it's plain text, write it to A1. "
            "Return ONLY the spreadsheet URL in your final answer."
        )
    else:
        # Fallback generic instruction; the basic LLM path may handle this
        return (
            f"Title: {title}\n"
            f"Contents: {contents}\n"
        )

async def process_chat_request_non_stream(request: ChatRequest, timeout_seconds: int = 400) -> ChatResponse:
    """
    Non-streaming version that returns a single JSON response after completion.
    Uses a cached MCPAgent to reduce latency on repeated calls.
    """
    start = time.perf_counter()

    # Build an instruction tailored to the requested provider
    usable_request = _build_instruction(request)
    try:
        # Treat enable_notion as a general "enable MCP" flag for all providers
        supported = {"notion", "notion-page", "notion_doc", "google-docs", "google-doc", "gdoc", "doc", "google-sheets", "google-sheet", "gsheet", "sheet"}
        use_mcp = bool(request.enable_notion) and (request.type or "").lower() in supported
        if use_mcp:
            logger.info("🧠 Starting full MCP agent mode (non-stream)...")
            client = await get_mcp_client()
            agent = get_or_create_agent(client)

            async def _run():
                return await agent.run(usable_request)

            # Guard against indefinite hangs
            final_answer = await asyncio.wait_for(_run(), timeout=timeout_seconds)
            print("final_answer:", final_answer)
            latency_ms = int((time.perf_counter() - start) * 1000)
            
            logger.info("✅ Full MCP agent mode completed (non-stream).")
            return ChatResponse(answer=str(final_answer or ""), mode="mcp_agent", latency_ms=latency_ms)
        else:
            logger.info("💬 Using basic LLM mode (non-stream)")
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                temperature=0.7,
            )
            response = await llm.ainvoke(usable_request)
            latency_ms = int((time.perf_counter() - start) * 1000)
            return ChatResponse(answer=str(response.content) if getattr(response, "content", None) else "No response generated.", mode="basic_llm", latency_ms=latency_ms)
    except asyncio.TimeoutError:
        logger.error("⏱️ MCP agent execution timed out")
        return ChatResponse(answer="Timed out while processing the request.", mode="mcp_agent" if request.enable_notion else "basic_llm", latency_ms=int((time.perf_counter() - start) * 1000))
    except Exception as e:
        logger.error(f"Error processing request (non-stream): {e}")
        return ChatResponse(answer=f"Error: {e}", mode="mcp_agent" if request.enable_notion else "basic_llm", latency_ms=int((time.perf_counter() - start) * 1000))
    
    
