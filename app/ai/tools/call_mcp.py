from openai import chat
from app.services.ExecutionAgentService import ExecutionAgentService
from app.core.logger import get_logger
from langchain.tools import tool
from app.api.schemas.mcp_schema import ChatRequest
logger = get_logger(__name__)

@tool(
    description="Call MCP tools to perform various operations like creating or managing documents and sheets.",
    args_schema=ChatRequest,
)
def call_mcp_tool(llm, prompt: ChatRequest):
    """
    Call MCP tool using the ExecutionAgentService.
    """
    agent_service = ExecutionAgentService()
    response =  agent_service.run_agent(prompt)
    return response
