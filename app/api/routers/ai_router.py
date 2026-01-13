from fastapi import APIRouter, Body, HTTPException
from typing import List
from app.core.logger import get_logger
from app.ai import input_schema as schema
from app.ai.ai import AI

logger = get_logger(__name__)

router = APIRouter()
@router.post("/invoke")
async def ai(request: schema.AnyAgentRequest = Body(..., discriminator='agent_name')):
    """
    Routes request to the correct agent by `agent_name`, relies on Pydantic's
    discriminated union to validate `context`, invokes the AI agent, and validates
    the AI output against the corresponding response model before returning.
    """
    ai_instance = AI()
    logger.info(f"🤣Received request for agent: {request.agent_name}", extra={"request": request.model_dump()})
    
    agent_name = request.agent_name
    context = request.context
    user_prompt = request.user_prompt
    
    try:
        logger.info(f"Processing request for agent: {agent_name}")
        if agent_name == "clarifying":
            # request is ClarifyingAgentRequest due to discriminator validation
            result = ai_instance.clarify_agent(
                context=context,  # type: ignore[arg-type]
                user_prompt=user_prompt,
            )
            logger.info(f"Clarifying agent result: {result}")
            return result
            # Validate AI output against response model
            

        elif agent_name == "classifying":
            # Extract optional allowed_domains from generic context.data if provided
            
            result = ai_instance.classify_agent(
                context=context,  # type: ignore[arg-type]
            )
            logger.info(f"Classifying agent result: {result}")
            return result

        elif agent_name == "domain":
            result = ai_instance.domain_agent(
                context=context,  # type: ignore[arg-type]
                user_prompt=user_prompt,
            )
            logger.info(f"Domain agent result: {result}")
            return result

        elif agent_name == "tasks":
            result = ai_instance.task_agent(
                context=context,  # type: ignore[arg-type]
                user_prompt=user_prompt,
            )
            logger.info(f"Tasks agent result: {result}")
            return result
        
        elif agent_name == "automation":
            result = ai_instance.automation_agent(
                context=context,  # type: ignore[arg-type]
                user_prompt=user_prompt,
            )
            logger.info(f"Automation agent result: {result}")
            return result
        
        elif agent_name == "clarify_automation":
            result = ai_instance.clarify_automation_agent(
                context=context,  # type: ignore[arg-type]
                user_prompt=user_prompt,
            )
            logger.info(f"Clarify Automation agent result: {result}")
            return result

        elif agent_name == "user_memory":
            result = ai_instance.user_memory_agent(
                context=context,  # type: ignore[arg-type]
                user_prompt=user_prompt,
            )
            logger.info(f"Knowledge Base agent result: {result}")
            return result
        
        elif agent_name == "venting":
            result = ai_instance.venting_agent(
                context=context,  # type: ignore[arg-type]
                user_prompt=user_prompt,
            )
            logger.info(f"Venting agent result: {result}")
            return result
        
        elif agent_name == "execution":
            result = await ai_instance.execution_agent(
                context=context,  # type: ignore[arg-type]
                user_prompt=user_prompt,
            )
            logger.info(f"Execution agent result: {result}")
            return result

        elif agent_name == "problem_space":
            result = ai_instance.problem_space_agent(
                classify_context=context,  # type: ignore[arg-type]
                user_prompt=user_prompt,
            )
            logger.info(f"Problem Space agent result: {result}")
            return result

        elif agent_name == "expander":
            result = ai_instance.expander_agent(
                context=context,  # type: ignore[arg-type]
                user_prompt=user_prompt,
            )
            logger.info(f"Expander agent result: {result}")
            return result

        else:
            raise HTTPException(status_code=400, detail="Invalid agent name.")

    except ValueError as e:
        # Likely JSON parsing issues from AI output
        raise HTTPException(status_code=400, detail=f"AI output parsing error: {str(e)}")
    except Exception as e:
        # Generic safety net
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
