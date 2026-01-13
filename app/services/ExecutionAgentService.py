from langchain_google_genai import ChatGoogleGenerativeAI
from app.api.schemas.mcp_schema import ExpanderResponseSchema
from app.core.config import settings
from app.core.logger import get_logger

from app.mcp.client import get_mcp_client
from app.mcp.agent import MCPAgent

logger = get_logger(__name__)

class ExecutionAgentService:
    def __init__(self) -> None:
        api_key = getattr(settings, "GOOGLE_API_KEY", None)
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is not set in the configuration.")
        self.api_key = api_key

        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0,
            max_tokens=None,
            timeout=500,
            max_retries=4,
        )
        

    async def run_agent(self, messageRequest: ExpanderResponseSchema, userprompt: str|None):
        """
        Run the agent using ChatGoogleGenerativeAI.bind_tools().
        """

        client = await get_mcp_client()
        if client is not None:
            llm = self.llm
            agent = MCPAgent(llm=llm, client=client)

            # Construct a detailed prompt from the messageRequest object
            context_prompt = (
                f"Executing a task with the following context:\n"
                f"Response: {messageRequest.response}\n"
                f"Tool Type: {messageRequest.toolType}\n"
            )

            # Combine the context with the user's original prompt
            # This ensures the agent has all the information.
            if userprompt:
                full_prompt = f"{context_prompt}\n\nUser's instruction: {userprompt}"
            else:
                full_prompt = context_prompt

            # Pass the combined and detailed prompt to the agent
            result = await agent.run(full_prompt)
            
            logger.info(result)
            return {"message": result}

        else:
            return {"message": "don't have tools!"}