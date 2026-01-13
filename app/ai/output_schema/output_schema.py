"""Output schemas for AI agents based on their prompts.

These Pydantic models mirror the exact JSON shapes each agent is instructed
to return in its prompt templates under `app.prompt`:

- ClarifyingAgentPrompt -> ClarifyingAgentOutput
- ClassifyingAgentPrompt -> ClassifyingAgentOutput (+ nested ProblemSpaceOutput)
- FinanceDomainAgentPrompt -> DomainAgentOutput
- TasksAgentPrompt -> TasksAgentOutput (+ nested TaskItemOutput)

Note: These are output-only shapes to validate/model the AI responses. They are
kept separate from request/context models in `app.schema`.
"""

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


# --- Clarifying Agent ---
class ClarifyingAgentOutput(BaseModel):
	"""Output for the Clarifying agent as specified in ClarifyingAgentPrompt.

	Example shape (when not yet clear):
	{
	  "is_problem_clear": false,
	  "clarifying_question": "...",
	  "suggested_answers": ["...", "...", "...", "...", "Other/None of the above."]
	}

	When clear:
	{
	  "is_problem_clear": true,
	  "clarifying_question": null,
	  "suggested_answers": []
	}
	"""

	is_problem_clear: bool = Field(..., description="Whether the problem is sufficiently understood.")
	clarifying_question: Optional[str] = Field(
		None,
		description="Next best clarifying question to ask, null if the problem is clear.",
	)
	suggested_answers: List[str] = Field(
		default_factory=list,
		description="Suggested answer options for the clarifying question.",
		min_length=0,
	)


# --- Classifying Agent ---
class ProblemSpaceOutput(BaseModel):
	"""Structured problem space as required by ClassifyingAgentPrompt.

	Includes a concise name, a descriptive paragraph, and a single-sentence root cause.
	"""

	name: str = Field(..., description="3-5 word concise title of the problem.")
	description: str = Field(
		..., description="Detailed one-paragraph summary (goal, action, expected vs actual)."
	)
	root_cause: str = Field(
		..., description="Specific one-sentence statement of the core reason for the issue."
	)


class ClassifyingAgentOutput(BaseModel):
	"""Output for the Classifying agent as specified in ClassifyingAgentPrompt."""

	domain: str = Field(
		..., description="The selected domain (must be one of the allowed domains provided to the agent)."
	)
	justification: str = Field(
		..., description="A brief one-sentence justification for the selected domain."
	)
	problem_space: ProblemSpaceOutput = Field(
		..., description="Structured problem definition for downstream specialist agents."
	)


# --- Domain Agent ---
# --- Domain Agent ---
class ObjectiveOutput(BaseModel):
	"""Single high-level objective as produced by the Domain agent."""

	objective_name: str = Field(
		..., description="Concise name of the strategic objective."
	)
	objective_description: str = Field(
		..., description="Detailed description explaining the importance and intended outcome of the objective."
	)
class DomainStrategyOutput(BaseModel):
    """Single strategy option produced by the Domain agent."""

    strategy_name: str = Field(
        ..., description="Compelling strategy name that reflects the goal and user personality."
    )
    approach_summary: str = Field(
        ..., description="Concise 1-2 sentence summary of the strategy's core philosophy."
    )
    key_objectives: List[ObjectiveOutput] = Field(
        ..., min_length=7, max_length=10, description="List of 7-10 high-level strategic objectives."
    )


class DomainAgentOutput(BaseModel):
    """Output for the Domain agent as specified in FinanceDomainAgentPrompt.

    Produces a list of high-level strategies aligned with the user's personality.
    """

    strategies: List[DomainStrategyOutput] = Field(
        ...,
        min_length=1,
        description="Ordered list of strategy options tailored to the user's personality and goal.",
    )	
## --- Domain Agent ---

# --- Tasks Agent ---
class TaskItemOutput(BaseModel):
	"""Single execution task item as required by TasksAgentPrompt."""
	order: int = Field(..., description="Execution order of this task in the overall plan.")
	name: str = Field(..., description="Short task name.")
	description: str = Field(..., description="Concrete, actionable task description.")
	is_automated: bool = Field(
		..., description="Whether this task can be automated by the agent/system."
	)


class TasksAgentOutput(BaseModel):
	"""Output for the Tasks agent as specified in TasksAgentPrompt."""

	overall_status: Literal["completed", "failed"] = Field(
		..., description='Overall outcome of the end-to-end plan ("completed" or "failed").'
	)
	research_summary: str = Field(
		..., description="Summary of research that informed the execution plan."
	)
	task: List[TaskItemOutput] = Field(
		..., description="Granular, step-by-step execution plan items."
	)


class TaskResults (BaseModel):
	result_type: str
	content: Dict[str, Any]

class AutomationAgentOutput(BaseModel):
	need_more_context: bool = False
	clarifying_question: Optional[str]
	automation_result: Optional[str]
	task_result: Optional[TaskResults]

class ClarifyAutomationAgentOutput(BaseModel):
	"""The output of the ClarifyAutomationAgent, providing questions to gather necessary parameters."""
	need_more_context: bool = False
	clarification_summary: str = Field(
		..., description="A one-sentence summary explaining why more information is needed to automate the task."
	)
	clarifying_questions: List[str] = Field(
		..., description="A list of short, direct questions for the user to answer. This list can be empty if no clarification is needed."
	)

class ExecutionAgentOutput(BaseModel):
	task_results: List[TaskResults]


class UserMemoryAgentOutput(BaseModel):
	"""Enhanced output for the User Memory agent.

	The agent now performs extraction & summarization of user-specific facts from
	conversation history and existing memory. It returns:
	- summary: high-level natural language recap
	- extracted_facts: structured key/value or category lists (finance, preferences, schedule, etc.)
	- user_memory_entries: any raw/relevant entries referenced or newly created
	- timestamp: ISO8601 string of when the snapshot was generated
	"""

	summary: Optional[str] = Field(
		None, description="High-level summary of the most salient user facts just extracted."
	)
	extracted_facts: Dict[str, Any] = Field(
		default_factory=dict,
		description="Structured categories of user facts (e.g., finance, preferences, habits, goals)."
	)
	user_memory_entries: List[Dict[str, Any]] = Field(
		default_factory=list,
		description="Raw or normalized memory entries relevant to or created from this pass.",
	)
	timestamp: Optional[str] = Field(
		None, description="UTC ISO timestamp when this memory snapshot was generated."
	)

class VentingAgentOutput(BaseModel):
	"""Therapeutic clarifying agent + problem space detector.

	Produces only clarifying questions (therapeutic tone) and signals readiness
	to construct a structured problem space.
	"""
	is_problem_space: bool = Field(
		False, description="Whether sufficient context exists to form a structured problem space."
	)
	clarifying_questions: List[str] = Field(
		default_factory=list, description="Therapeutic, specific questions to fill missing context."
	)
	problem_space: Optional[ProblemSpaceOutput] = Field(
		None, description="Proposed structured problem space when is_problem_space is true."
	)

# --- Expander Agent ---
class ExecutionContextSuggestion(BaseModel):
    """Suggested key-value pair or structured snippet to add to execution context."""
    key: str = Field(..., description="Name of the context field (snake_case).")
    value: Any = Field(..., description="Value or structured object to attach under this key.")
    rationale: str = Field(..., description="Why this addition is helpful for execution.")

class ExpanderAgentOutput(BaseModel):
    """Output for the Expander agent.

    Takes a chosen automation task + clarification answers + available tools + user prompt
    and performs external research (DuckDuckGo) to enrich the execution context.
    """
    research_summary: str = Field(..., description="Narrative summary (3-6 sentences) of findings relevant to the task.")
    sources: List[str] = Field(default_factory=list, description="Distinct source URLs or titles referenced.")
    risk_flags: List[str] = Field(default_factory=list, description="Potential risks, ambiguities, or missing data points.")
    recommended_tools: List[str] = Field(default_factory=list, description="Subset of available tools most relevant to this task.")
    enriched_context: Dict[str, Any] = Field(default_factory=dict, description="Merged enriched facts (low-level).")
    execution_suggestions: List[ExecutionContextSuggestion] = Field(
        default_factory=list,
        description="Discrete suggestions to augment downstream execution context.")

__all__ = [
	"ClarifyingAgentOutput",
	"ProblemSpaceOutput",
	"ClassifyingAgentOutput",
	"DomainAgentOutput",
	"TaskItemOutput",
	"TasksAgentOutput",
	"UserMemoryAgentOutput",
	"VentingAgentOutput",
	"ExecutionAgentOutput",
	"AutomationAgentOutput",
	"ClarifyAutomationAgentOutput",
	"ExpanderAgentOutput"
]

