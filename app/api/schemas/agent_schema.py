
from typing import List, Dict, Any
from pydantic import BaseModel, Field

class AgentMessage(BaseModel):
    tasks: list[str]


class TaskAutomationStatus(BaseModel):
    task: str = Field(description="The task description")
    automatable: bool = Field(description="Whether the task can be automated or not based on the only tools provided")
    reason: str = Field(description="Reason for the decision on automatable or not")


class ExecutorAgentResponseSchema(BaseModel):
    tasks: List[TaskAutomationStatus] = Field(description="List of tasks with their automation status")

# Flexible response schema for expander_agent
class ExpanderAgentResponseSchema(BaseModel):
    response: Dict[str, Any] = Field(description="Flexible response for expander agent, can be any valid JSON object.")