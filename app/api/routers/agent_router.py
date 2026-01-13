from fastapi import APIRouter
from app.services.ExecutionAgentService import ExecutionAgentService
from app.core.logger import get_logger
from app.api.schemas.agent_schema import AgentMessage
from app.api.schemas.mcp_schema import ExpanderResponseSchema
from langchain_google_genai import ChatGoogleGenerativeAI

from app.services.ExpanderAgentService import run_expander_agent

llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                temperature=0,
                max_tokens=None,
                timeout=300,
            )

router = APIRouter()
agent_service = ExecutionAgentService()
logger = get_logger(__name__)


# @router.post("/run-agent/")
# async def excutable_main_agent(payload: AgentMessage):
#     logger.info("Received tasks for agent")

#     tasks = payload.tasks
#     systemPrompt = """
#     You are a helpful AI assistant. That checks the incoming list of tasks. and deside if they are automatable or not based on the tool you have been provided with. And respond strictly in the given response_schema.
#     """
    
#     message = agent_service.message(incomingData=tasks, systemPrompt=systemPrompt)

#     response = await agent_service.run_agent(message, response_schema=ExecutorAgentResponseSchema.model_json_schema())

#     logger.info(f"Agent response: {response}")
#     return {"response": response}

@router.post("/expander-agent/")
async def expander_agent(payload: AgentMessage):
    logger.info("Received tasks for expander agent")
    try:
        tasks = payload.tasks
        output = []
        for task in tasks:
            logger.info(f"Task: {task}")
            response, userPrompt = await run_expander_agent(str(task))
            # response can be a list or dict
            if isinstance(response, list):
                for item in response:
                    logger.info(f"Expander Agent response list: {item}")
                    if isinstance(item, dict):
                        print("check the type", item.get("toolType"))
                        if item.get("toolType") == "none":
                            output.append(item)
                            continue
                        # Coerce dict into ExpanderResponseSchema for the execution agent
                        try:
                            raw_response = item.get("response")
                            raw_tool = item.get("toolType")
                            if not isinstance(raw_response, dict) or not isinstance(raw_tool, str):
                                raise ValueError("Missing or invalid 'response' (dict) or 'toolType' (str) in item")
                            expander_item = ExpanderResponseSchema(
                                response=raw_response,
                                toolType=raw_tool,
                            )
                        except Exception as e:
                            logger.error(f"Invalid expander item schema: {e}; item: {item}")
                            output.append({"error": "Invalid expander item schema", "details": str(e), "item": item})
                            continue
                        executionAgent = await agent_service.run_agent(messageRequest=expander_item, userprompt=userPrompt)
                        output.append(executionAgent)
                    else:
                        logger.error(f"Unexpected item type inside list: {type(item)}")
                        output.append({"error": "Unexpected item type from expander agent list", "itemType": str(type(item))})
            elif isinstance(response, dict):
                logger.info(f"Expander Agent response dict: {response}")
                print("check the type", response.get("toolType"))
                if response.get("toolType") == "none":
                    output.append(response)
                else:
                    # Coerce dict into ExpanderResponseSchema for the execution agent
                    try:
                        raw_response = response.get("response")
                        raw_tool = response.get("toolType")
                        if not isinstance(raw_response, dict) or not isinstance(raw_tool, str):
                            raise ValueError("Missing or invalid 'response' (dict) or 'toolType' (str) in response")
                        expander_item = ExpanderResponseSchema(
                            response=raw_response,
                            toolType=raw_tool,
                        )
                    except Exception as e:
                        logger.error(f"Invalid expander response schema: {e}; response: {response}")
                        output.append({"error": "Invalid expander response schema", "details": str(e), "item": response})
                        continue
                    executionAgent = await agent_service.run_agent(messageRequest=expander_item, userprompt=userPrompt)
                    output.append(executionAgent)
            else:
                logger.error(f"Unexpected response type from expander agent: {type(response)}")
                output.append({"error": "Unexpected response type from expander agent"})
        return output
    except Exception as e:
        logger.error(f"Error in expander agent: {str(e)}")
        return {"error": str(e)}