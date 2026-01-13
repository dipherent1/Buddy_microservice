from token import OP
from pydantic import BaseModel, Field
import json
from typing import Any, Dict, List, Optional, Union, Literal
from regex import T
from sqlalchemy import Enum
from pydantic import BaseModel, Field, field_validator 

AllowedDomains = ["finance", "personal", "professional"]
    

class ProblemSpaceModel(BaseModel):
    name: str
    description: str
    root_cause: str
    status: str = 'active'

class DomainProfileModel(BaseModel):
    domain_type: str
    personality: Optional[str] = None

class TaskModel(BaseModel):
    order: int
    name: str
    description: Optional[str] = None
    status: str = 'pending'
    is_automated: bool = True

class StrategyModel(BaseModel):
    strategy_name: str
    approach_summary: str
    key_objectives: List[str]

# --- Base Models for Context (Simplified) ---
class BaseContext(BaseModel):
    history: Optional[List[Dict[str, str]]] = None
    data: Optional[Dict[str, Any]] = None

class ClarifyingContext(BaseContext):
    pass

class ClassifyingContext(BaseContext):
    pass

class DomainContext(ClarifyingContext):
    problem_space: ProblemSpaceModel
    domain_profile: DomainProfileModel # Use the new structured model
    user_memory_summary: Optional[Dict[str, Any]] = None
    previous_objectives: Optional[List[TaskModel]] = None

class TaskContext(DomainContext):
    strategies: List[StrategyModel]
    previous_tasks: Optional[List[TaskModel]] = None

class AutomationContext(BaseContext):
    strategies: List[StrategyModel]
    user_memory: Dict[str, Any]

class TaskClarificationContext(BaseContext):
    """The specific context needed for the ClarifyAutomationAgent."""
    task_to_clarify: TaskModel 
    user_memory_summary: Optional[Dict[str, Any]] 
    
class ExpanderContext(BaseContext):
    """Context for the Expander Agent.

    Combines a chosen automation task, any answers the user provided to previous
    clarification questions, and optionally user memory. The agent will enrich this
    with external context (web search) and produce expanded execution-relevant
    insights. The raw user prompt is passed separately (top-level request like other agents).
    Available tools are read implicitly from the static prompt export (`prompt.AvailableTools`).
    """
    chosen_task: TaskModel
    clarification_answers: Optional[Dict[str, Any]] = None
    user_memory: Optional[Dict[str, Any]] = None
    


# --- Meta Agents context ---#
class UserMemoryContext(BaseContext):
    """Context for the User Memory Agent.

    Accepts optional conversation history/data via BaseContext and any existing
    user memory store to allow incremental updates/merges.
    """
    user_memory: Dict[str, Any]

class VentingContext(BaseModel):
    user_memory: List[Dict[str, Any]]
    history: List[str]

class ExecutionContext(BaseModel):
    """
        Schema For Incoming Chat Requests from the Frontend 
        That contains title, contents and type of tool to be used.
    """
    title: Optional[str] = None
    contents: Optional[str] = None
    type: Optional[str] = None
    # --- Add Notion Mode ----
    

# --- Request Models (Updated to use new models) ---
class AgentRequest(BaseModel):
    agent_name: str
    user_prompt: Optional[str] = None

class ClarifyingAgentRequest(AgentRequest):
    agent_name: Literal["clarifying"]
    context: ClarifyingContext

class ClassifyingAgentRequest(AgentRequest):
    agent_name: Literal["classifying"]
    context: ClassifyingContext

class DomainAgentRequest(AgentRequest):
    agent_name: Literal["domain"]
    context: DomainContext

class TasksAgentRequest(AgentRequest):
    agent_name: Literal["tasks"]
    context: TaskContext

class AutomationAgentRequest(AgentRequest):
    agent_name: Literal["automation"]
    context: TaskContext

class ClarifyAutomationAgentRequest(AgentRequest):
    """The request model for the ClarifyAutomationAgent."""
    agent_name: Literal["clarify_automation"]
    context: TaskClarificationContext

class ProblemSpaceRequest(AgentRequest):
    agent_name: Literal["problem_space"]
    context: ClassifyingContext


# --- Meta agent context --- #
class UserMemoryAgentRequest(AgentRequest):
    agent_name: Literal["user_memory"]
    context: UserMemoryContext

class VentingAgentRequest(AgentRequest):
    agent_name: Literal["venting"]
    context: VentingContext

class ExecutionAgentRequest(AgentRequest):
    agent_name: Literal["execution"]
    context: Optional[ExecutionContext]
    
class ExpanderAgentRequest(AgentRequest):
    agent_name: Literal["expander"]
    context: ExpanderContext
    
AnyAgentRequest = Union[
    ClarifyingAgentRequest,
    ClassifyingAgentRequest,
    DomainAgentRequest,
    TasksAgentRequest,
    UserMemoryAgentRequest,
    VentingAgentRequest,
    AutomationAgentRequest,
    ExecutionAgentRequest,
    ClarifyAutomationAgentRequest,
    ProblemSpaceRequest,
    ExpanderAgentRequest,
]

