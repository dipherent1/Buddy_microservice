from datetime import datetime 
from typing import Union, Optional, Dict, Any, Literal 
from pydantic import BaseModel, Field, field_validator 

class ExpanderResponseSchema(BaseModel):
    """
    Schema for the response from the Expander Agent.
    Contains response:jsonb that holds the expanded tasks and toolType:str indicating the type of tool to be used.    
    """
    
    response: Dict[str, Any] = Field(
        ...,
        description="Expanded tasks in JSON format"
    )
    toolType: str = Field(
        ...,
        description="Type of tool to be used for the task"
    )

class ChatRequest(BaseModel):
    """
        Schema For Incoming Chat Requests from the Frontend 
        That contains title, contents and type of tool to be used.
    """
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Title for the target resource (e.g., Notion page, Google Doc/Sheet)",
    )
    contents: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Contents or instructions for the resource (text or table-like description)",
    )
    
    type : str = Field(
        ...,
        description="Type of Tool based on the available tools if their is no avialable tools that relates to this use none, e.g., 'notion', 'slack', 'none' etc."
    )
    
    enable_notion: Optional[bool] = Field(
        True,
        description="Toggle MCP integration (true for full agent with tools, false for basic LLM)",
    )
    @field_validator('title', 'contents')
    @classmethod
    def validate_message(cls, v: str) -> str:
        """
            Validate and clean the user title, contents input.
        """
        v = v.strip()
        if not v:
            raise ValueError("Title or contents cannot be empty")
        return v

class ChatResponse(BaseModel):
    """Simple non-streaming response schema for chat endpoint."""
    answer: str = Field(..., description="Final answer produced by the agent/LLM")
    # link: Optional[str] = Field(None, description="Link to the created Notion page, if applicable")
    mode: Literal["mcp_agent", "basic_llm"] = Field(..., description="Execution mode used")
    latency_ms: Optional[int] = Field(None, description="Total processing time in milliseconds")
    
# --- SSE Event Data Models ---- 
class AgentStartData(BaseModel):
    """Data payload for agent start event."""
    status: Literal["started"] = "started"

class ReasoningData(BaseModel):
    """Data payload for agent reasoning/thinking events."""
    thought: str = Field(..., description="Agent's reasoning step or thought process")

class ToolCallData(BaseModel):
    """Data payload for tool call events."""
    tool_name: str = Field(..., description="Name of the tool being called (e.g., 'search')")
    tool_input: Dict[str, Any] = Field(..., description="Input parameters for the tool")

class ToolOutputData(BaseModel):
    """Data payload for tool output events."""
    tool_name: str = Field(..., description="Name of the tool that was called")
    tool_output: str = Field(..., description="Raw output from the tool (JSON string)")

class FinalAnswerData(BaseModel):
    """Data payload for final answer events."""
    answer: str = Field(..., description="Complete answer to user's query")

class ErrorData(BaseModel):
    """Data payload for error events."""
    error: str = Field(..., description="Error message")
    error_type: Optional[str] = Field(None, description="Type/category of error (e.g., 'auth')")

class StreamEndData(BaseModel):
    """Data payload for stream end events."""
    status: Literal["finished"] = "finished"

# ---- SSE Event Wrapper ----
class SSEEvent(BaseModel):
    """Wrapper for Server-Sent Events with proper typing."""
    event: str = Field(..., description="Event type name (e.g., 'reasoning')")
    data: Union[
        AgentStartData,
        ReasoningData,
        ToolCallData,
        ToolOutputData,
        FinalAnswerData,
        ErrorData,
        StreamEndData
    ] = Field(..., description="Event data payload")

    def to_sse_string(self) -> str:
        """Convert to proper SSE format for transmission."""
        return f"event: {self.event}\ndata: {self.data.model_dump_json()}\n\n"

# --- HTTP Response Schemas ---
class HealthCheckResponse(BaseModel):
    """Schema for health check endpoint response."""
    status: Literal["healthy"] = "healthy"
    app_name: str
    version: str = "1.0.0"
    mcp_status: Literal["connected", "disconnected", "error"] = "connected"

class ErrorResponse(BaseModel):
    """Schema for error responses."""
    detail: str = Field(..., description="Error description")
    error_type: Optional[str] = Field(None, description="Type of error")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# --- Exports for easy imports ---
__all__ = [
    "ChatRequest",
    "SSEEvent",
    "AgentStartData",
    "ReasoningData",
    "ToolCallData",
    "ToolOutputData",
    "FinalAnswerData",
    "ErrorData",
    "StreamEndData",
    "HealthCheckResponse",
    "ErrorResponse",
]