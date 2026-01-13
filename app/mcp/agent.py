import logging
from mcp_use import MCPAgent, MCPClient
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)

def create_agent(client: MCPClient) -> MCPAgent:
    """
        Factory Function to create a configured MCPAgent instance 
        
        Args:
            Client : The pre-initialized MCPClient singleton 
        Returns:
            A fullly configured MCPAgent ready for execution 
    """
    logger.info("🧠 Creating MCPAgent...")
    try:
        # --- Step 1 : Initialize the LLM (Gemini 2.5 Flash) ---
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.7,
        )
        # --- Step 2 : Create the Agent Instance ---- 
        agent = MCPAgent(
            llm=llm,
            client=client
        )
        logger.info("✅ MCPAgent created successfully.")
        return agent
    except Exception as e:
        logger.error(f"❌ Failed to create MCPAgent: {e}")
        raise RuntimeError(f"MCPAgent creation failed: {e}")

# --- Simple in-process cache for the agent to avoid re-initialization cost ---
_agent_instance: MCPAgent | None = None

def get_or_create_agent(client: MCPClient) -> MCPAgent:
    """
    Return a cached MCPAgent if available, otherwise create and cache a new one.
    This reduces per-request startup overhead (tool discovery, wiring, etc.).
    """
    global _agent_instance
    if _agent_instance is not None:
        return _agent_instance
    _agent_instance = create_agent(client)
    return _agent_instance