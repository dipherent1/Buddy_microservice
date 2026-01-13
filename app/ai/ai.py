from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from unittest import result
from app.core.logger import get_logger
from fastapi import FastAPI, Body
from pydantic import BaseModel, Field
import json
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.chat_models import init_chat_model
from langchain_core.globals import set_debug
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_perplexity import ChatPerplexity
from app.ai import output_schema, input_schema, prompt
from dotenv import load_dotenv
from app.services.ExecutionAgentService import ExecutionAgentService
from app.api.schemas.mcp_schema import ChatRequest

load_dotenv()
set_debug(True)

class AI():
    def __init__(self):
        # self.model = init_chat_model("gemini-2.5-flash", model_provider="google_genai", temperature=0.1, top_p = 0.5)
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
        self.perplexity_llm = ChatPerplexity(temperature=0, model="sonar", timeout=1800)
        self.logger = get_logger(__name__)

    def parse_json_like_content(self, input_text):
        """
        Parse a JSON-like string that may contain code block markers or a `json` prefix.
        """
        # If input_text is an AIMessage, get the content string
        if hasattr(input_text, "content"):
            input_text = input_text.content

        # Step 1: Remove code block markers if present
        if input_text.startswith("```"):
            input_text = input_text[3:].strip()

        if input_text.endswith("```"):
            input_text = input_text[:-3].strip()

        # Step 2: Remove the `json` prefix if present
        if input_text.startswith("json"):
            input_text = input_text[4:].strip()

        # Step 3: Parse the JSON content
        try:
            return json.loads(input_text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON content: {e}")



# {user_prompt} (user's problem description)
# {history} (list of conversation turns)
    def clarify_agent(self, context: input_schema.ClarifyingContext, user_prompt: str|None ):
        self.logger.info("Clarify Agent Invoked with context:", extra={"context": context.model_dump()})
        try:
            clarify_prompt = ChatPromptTemplate.from_messages([
                # SystemMessagePromptTemplate.from_template(prompt.ClarifyingAgentPrompt),
                HumanMessagePromptTemplate.from_template(prompt.ClarifyingAgentPrompt)
            ])

            clarifyingAgent = self.llm.with_structured_output(output_schema.ClarifyingAgentOutput)
        
            result_text = (clarify_prompt | clarifyingAgent).invoke({
                "history": context.history,
                "user_prompt": user_prompt
            })

        except Exception as e:
            self.logger.error("Clarify Agent failed", exc_info=e)
            raise
        # print("Clarify Agent Result:", result_text)

        return result_text


# {history} (list of conversation turns)
# {allowed_domains} (list of strings)
    def classify_agent(self, context: input_schema.ClassifyingContext):
        self.logger.info("Classify Agent Invoked with context:", extra={"context": context.model_dump()})
        try:
            classify_prompt = ChatPromptTemplate.from_messages([
                # SystemMessagePromptTemplate.from_template(prompt.ClarifyingAgentPrompt),
                HumanMessagePromptTemplate.from_template(prompt.ClassifyingAgentPrompt)
            ])
        
            classifyingAgent = self.llm.with_structured_output(output_schema.ClassifyingAgentOutput)
        

            result_text = (classify_prompt | classifyingAgent).invoke({
                "history": context.history,
                "allowed_domains": input_schema.AllowedDomains
            })
        except Exception as e:
            self.logger.error("Classify Agent failed", exc_info=e)
            raise

        return result_text

# *   {problem_space} (json object)
# *   {domain_profile} (json object)
# *   {user_memory_summary} (json object)
    def domain_agent(self, context: input_schema.DomainContext, user_prompt: str|None):
        input_prompt = ""
        if context.domain_profile.domain_type == "finance":
            input_prompt = prompt.FinanceDomainAgentPrompt
        elif context.domain_profile.domain_type == "personal":
            input_prompt = prompt.PersonalDomainAgentPrompt
        elif context.domain_profile.domain_type == "professional":
            input_prompt = prompt.ProfessionalDomainAgentPrompt
        
        try:
            domain_prompt = ChatPromptTemplate.from_messages([
                HumanMessagePromptTemplate.from_template(input_prompt),
            ])

            domainAgent = self.llm.with_structured_output(output_schema.DomainAgentOutput)
            result_text = (domain_prompt | domainAgent).invoke({
                "problem_space": json.dumps(context.problem_space.model_dump()),
                "previous_objectives":  [objectives.model_dump() for objectives in context.previous_objectives] if context.previous_objectives else None,
                "user_prompt": user_prompt,
                "domain_profile": json.dumps(context.domain_profile.model_dump()),
                "user_memory_summary": json.dumps(context.user_memory_summary)
            })
        except Exception as e:
            self.logger.error("Domain Agent failed", exc_info=e)
            raise

        return result_text


#  {problem_space} (json object)
# *   {domain_profile} (json object)
# *   {user_memory_summary} (json object)
# *   {strategic_objective} (
    def task_agent(self, context: input_schema.TaskContext, user_prompt: str|None):
        try:
            task_prompt = ChatPromptTemplate.from_messages([
                HumanMessagePromptTemplate.from_template(prompt.TasksAgentPrompt),
            ])

            taskAgent = self.perplexity_llm.with_structured_output(output_schema.TasksAgentOutput)
            
            result_text = (task_prompt | taskAgent).invoke({
                "problem_space": json.dumps(context.problem_space.model_dump()),
                "domain_profile": json.dumps(context.domain_profile.model_dump()),
                "strategic_objective": [strategies.model_dump() for strategies in context.strategies],
                "previous_tasks": [tasks.model_dump() for tasks in context.previous_tasks] if context.previous_tasks else None,
                "user_prompt": user_prompt,
                "user_memory_summary": json.dumps(context.user_memory_summary),
            })
        except Exception as e:
            self.logger.error("Task Agent failed", exc_info=e)
            raise

        return result_text
    
    def automation_agent(self, context: input_schema.TaskContext, user_prompt: str|None):
        self.logger.info("Automation Agent Invoked with context:", extra={"context": context.model_dump()})
        try:
            automation_prompt = ChatPromptTemplate.from_messages([
                HumanMessagePromptTemplate.from_template(prompt.AutomationAgentPrompt)
            ])

            automationAgent = self.llm.with_structured_output(output_schema.TasksAgentOutput)
        
            result_text = (automation_prompt | automationAgent).invoke({
                "available_tools": prompt.AvailableTools,
                "strategies": json.dumps([strategy.model_dump() for strategy in context.strategies]),
                "user_memory": json.dumps(context.user_memory_summary),
                "history": json.dumps(context.history),
                "data": json.dumps(context.data) if context.data else None,
                "user_prompt": user_prompt,


            })

        except Exception as e:
            self.logger.error("Automation Agent failed", exc_info=e)
            raise

        return result_text
    
    def clarify_automation_agent(self, context: input_schema.TaskClarificationContext, user_prompt: str|None):
        self.logger.info("Clarify Automation Agent Invoked with context:", extra={"context": context.model_dump()})
        try:
            clarify_automation_prompt = ChatPromptTemplate.from_messages([
                HumanMessagePromptTemplate.from_template(prompt.ClarifyAutomationAgentPrompt)
            ])

            clarifyAutomationAgent = self.llm.with_structured_output(output_schema.ClarifyAutomationAgentOutput)
        
            result_text = (clarify_automation_prompt | clarifyAutomationAgent).invoke({
                "available_tools": prompt.AvailableTools,
                "task_to_clarify": json.dumps(context.task_to_clarify.model_dump()),
                "user_memory_summary": json.dumps(context.user_memory_summary) if context.user_memory_summary else None,
                "history": json.dumps(context.history),
                "user_prompt": user_prompt
            })

        except Exception as e:
            self.logger.error("Clarify Automation Agent failed", exc_info=e)
            raise

        return result_text
    
    async def execution_agent(self, context: input_schema.ExecutionContext, user_prompt: str|None):
        agent_service = ExecutionAgentService()
        response = await agent_service.run_agent(context, user_prompt)
        return response

    
    def user_memory_agent(self, context: input_schema.UserMemoryContext, user_prompt: str|None):
        self.logger.info("User Memory Agent Invoked with context:", extra={"context": context.model_dump()})
        try:
            kb_prompt = ChatPromptTemplate.from_messages([
                HumanMessagePromptTemplate.from_template(prompt.UserMemoryAgentPrompt)
            ])

            UserMemoryAgent = self.llm.with_structured_output(output_schema.UserMemoryAgentOutput)
        
            result = (kb_prompt | UserMemoryAgent).invoke({
                "user_memory": json.dumps(context.user_memory),
                "user_prompt": user_prompt,
                "history": json.dumps(context.history) if context.history else json.dumps([]),
            })

            # Ensure validated output (in case provider returns dict)
            validated = output_schema.UserMemoryAgentOutput.model_validate(result)

        except Exception as e:
            self.logger.error("User Memory Agent failed", exc_info=e)
            raise

        return validated
    
    def venting_agent(self, context: input_schema.VentingContext, user_prompt: str|None):
        self.logger.info("Venting Agent Invoked with context:", extra={"context": context.model_dump()})
        try:
            venting_prompt = ChatPromptTemplate.from_messages([
                HumanMessagePromptTemplate.from_template(prompt.VentingAgentPrompt)
            ])

            ventingAgent = self.llm.with_structured_output(output_schema.VentingAgentOutput)
        
            result_text = (venting_prompt | ventingAgent).invoke({
                "user_memory": json.dumps(context.user_memory),
                "user_prompt": user_prompt,
                "history": json.dumps(context.history)


            })
    
        except Exception as e:
            self.logger.error("Venting Agent failed", exc_info=e)
            raise

        return result_text
    
    def problem_space_agent(self, classify_context: input_schema.ClassifyingContext, user_prompt: str | None):
        """
        Orchestrates a three-agent chain to process a user request:
        1. Classify Agent: Determines the domain and problem space.
        2. Domain Agent: Generates high-level strategies.
        3. Automation (Tasks) Agent: Creates a detailed execution plan for the first objective.

        Returns a dictionary containing the structured output from each agent.
        """
        self.logger.info("Problem Space Agent invoked for user prompt: %s", user_prompt)

        try:

            # --- PHASE 1: CLASSIFICATION AGENT ---
            # Goal: Understand and categorize the user's core problem.
            raw_classification = self.classify_agent(classify_context)
            classification_output: output_schema.ClassifyingAgentOutput = output_schema.ClassifyingAgentOutput.model_validate(raw_classification)

            # Map classification output to internal ProblemSpaceModel & DomainProfileModel
            problem_space_model = input_schema.ProblemSpaceModel(
                name=classification_output.problem_space.name,
                description=classification_output.problem_space.description,
                root_cause=classification_output.problem_space.root_cause,
            )

            domain_profile_model = input_schema.DomainProfileModel(
                domain_type=classification_output.domain,
                personality=None  # Could be inferred later
            )


            # --- PHASE 2: DOMAIN AGENT ---
            # Goal: Generate high-level strategies based on the classified problem.
            domain_context = input_schema.DomainContext(
                history=classify_context.history,
                data=classify_context.data,
                problem_space=problem_space_model,
                domain_profile=domain_profile_model,
                previous_objectives=None,  # Assuming no prior objectives for this new problem
                user_memory_summary=None,
            )

            raw_domain = self.domain_agent(domain_context, user_prompt=user_prompt)
            domain_output: output_schema.DomainAgentOutput = output_schema.DomainAgentOutput.model_validate(raw_domain)


            # --- PHASE 3: AUTOMATION (TASKS) AGENT ---
            # Goal: Create a concrete execution plan for the most relevant objective.
            # Note: In a real system, you'd ask the user to choose. Here, we default to the first objective of the first strategy.
            
            self.logger.info("Phase 3: Invoking Automation (Tasks) Agent")
            # Convert DomainAgentOutput strategies -> StrategyModel list
            strategies_models = [
                input_schema.StrategyModel(
                    strategy_name=strategy.strategy_name,
                    approach_summary=strategy.approach_summary,
                    key_objectives=[obj.objective_name for obj in strategy.key_objectives],
                )
                for strategy in domain_output.strategies
            ]

            automation_context = input_schema.TaskContext(
                domain_profile=domain_context.domain_profile,
                problem_space=domain_context.problem_space,
                history=classify_context.history,
                data=classify_context.data,
                strategies=strategies_models,
                user_memory_summary=None,
            )
            
            
            raw_tasks = self.automation_agent(automation_context, user_prompt=user_prompt)
            tasks_output: output_schema.TasksAgentOutput = output_schema.TasksAgentOutput.model_validate(raw_tasks)


            # --- FINAL OUTPUT ---
            # Combine all results into a single dictionary.
            final_result = {
                "classification_output": classification_output.model_dump(),
                "domain_output": domain_output.model_dump(),
                "tasks_output": tasks_output.model_dump(),
            }
            
            self.logger.info("Problem Space Agent chain completed successfully.")
            return final_result

        except Exception as e:
            self.logger.error("The agent chain failed.", exc_info=e)
            # Depending on desired behavior, you might want to return an error dictionary
            return {"error": str(e)}

    def expander_agent(self, context: input_schema.ExpanderContext, user_prompt: str | None):
        """Expander Agent

        Enriches a chosen automation task with external context via DuckDuckGo search.
        It leverages the static AvailableTools prompt and returns a structured
        ExpanderAgentOutput.
        """

        self.logger.info("Expander Agent Invoked", extra={"context": context.model_dump(), "user_prompt": user_prompt})
        try:
            # Prepare dynamic search queries based on task name/description and user prompt
            queries = []
            if context.chosen_task.name:
                queries.append(f"best practices {context.chosen_task.name}")
            if context.chosen_task.description:
                queries.append(context.chosen_task.description[:120])
            if user_prompt:
                queries.append(user_prompt[:120])
            # Deduplicate and cap
            seen = set()
            unique_queries = []
            for q in queries:
                qn = q.strip()
                if qn and qn.lower() not in seen:
                    seen.add(qn.lower())
                    unique_queries.append(qn)
            unique_queries = unique_queries[:4]

            search_tool = DuckDuckGoSearchRun()
            search_results = []
            for q in unique_queries:
                try:
                    res = search_tool.run(q)
                except Exception as e:
                    res = f"Search error for '{q}': {e}"
                search_results.append({"query": q, "raw_result": res})

            expander_prompt = ChatPromptTemplate.from_messages([
                HumanMessagePromptTemplate.from_template(prompt.ExpanderAgentPrompt)
            ])

            structured_llm = self.llm.with_structured_output(output_schema.ExpanderAgentOutput)
            result = (expander_prompt | structured_llm).invoke({
                "chosen_task": json.dumps(context.chosen_task.model_dump()),
                "clarification_answers": json.dumps(context.clarification_answers) if context.clarification_answers else json.dumps({}),
                "user_prompt": user_prompt or "",
                "user_memory": json.dumps(context.user_memory) if context.user_memory else json.dumps({}),
                "available_tools": prompt.AvailableTools,
                "search_snippets": json.dumps(search_results),
            })

            validated = output_schema.ExpanderAgentOutput.model_validate(result)
            return validated
        except Exception as e:
            self.logger.error("Expander Agent failed", exc_info=e)
            raise
        

   


