import json
from langchain_google_genai import ChatGoogleGenerativeAI
from app.api.schemas.mcp_schema import ExpanderResponseSchema

from app.core.logger import get_logger
from typing import Tuple


logging = get_logger(__name__)

agent = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    max_tokens=None,
    timeout=300,
    max_retries=2,
)

async def run_expander_agent(task: str) -> Tuple[ExpanderResponseSchema, str]:
    logging.info("Running expander agent with task")
    system_prompt = (
        "You are a helpful AI assistant. Review the incoming tasks and determine if each can be handled by the available tools: [create_notion_page, create_google_doc, create_google_sheet, create_google_calendar, create_gmail, create_slack_message].\n"
        "Tools and expected types: \n"
        
        "- create_notion_page: accepts title, contents, type='notion' to create a Notion page. Contents should describe what the page should include.\n"
        "- create_google_doc: accepts title, contents, type in {'google-docs','google-sheets'} to create a Google Doc or a Google Sheet. For sheets, contents can describe a table to insert.\n"
        "- create_google_calendar: accepts title, contents, type='google-calendar' to create a Google Calendar event. Contents should include event details like date and time.\n"
        "- create_gmail: to, subject, body, type='gmail' to send an email via Gmail.\n"
        "For tasks that can be handled, respond with a JSON array of objects, each strictly following this schema:\n"
        "- create_slack_message: accepts channel, message, type='slack' to send a Slack message.\n"
        f"{ExpanderResponseSchema.model_json_schema()}\n"
        "For tasks that cannot be handled, respond with a JSON object in this format:\n"
        '{ "response": "payload.tasks", "toolType": "none" }\n'
        "Your response must be valid JSON and adhere strictly to the schema. Do not include any explanations or extra text.\n"
        
        "Examples for notion page creation:\n"
        " {'response': {'title': 'Project Plan', 'contents': 'Create a detailed project plan with milestones and tasks.'}, 'toolType': 'notion'}\n"
        "Examples for google-docs creation:\n"
        " {'response': {'title': 'Project Overview', 'contents': 'Create a document outlining the project goals, timeline, and key milestones.'}, 'toolType': 'google-docs'}\n"
        "Examples for google-sheets creation:\n"
        " {'response': {'title': 'Monthly Budget', 'contents': 'Create a sheet with columns: Category, Amount, Date. Add example rows for Rent 1200 and Utilities 200.'}, 'toolType': 'google-sheets'}\n"
        "Examples for google-calendar creation:\n"
        " {'response': {'title': 'Meeting with Team', 'contents': 'Schedule a meeting with the team on Friday at 10 AM.'}, 'toolType': 'google-calendar'}\n"
        "Examples for gmail creation:\n"
        " {'response': {'to': 'recipient@example.com', 'subject': 'Hello', 'body': 'This is a test email.'}, 'toolType': 'gmail'}\n"
        "Examples for slack message creation:\n"
        " {'response': {'channel': '#general', 'message': 'Hello team, please check the latest updates.'}, 'toolType': 'slack'}\n"
        "Examples for unhandled tasks:\n"
        "Example: if their is not tool to handle the task respond with\n"
        '{ "response": "talk to your friends", "toolType": "none" }'
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task}
    ]
    logging.info(f"Expander Agent Message: {messages}")

    response = await agent.ainvoke(messages)
    output = getattr(response, "content")
    logging.info(f"Expander Agent Output no dict: {output}, Task expander: {task}")

    # Remove code block markers if present
    cleaned = output.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[len("```json"):].strip()
    if cleaned.startswith("```"):
        cleaned = cleaned[len("```"):].strip()
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

    # Try to parse as JSON
    try:
        parsed = json.loads(cleaned)
    except Exception as e:
        logging.error(f"Failed to parse LLM output as JSON: {e}, output: {cleaned}")
        raise

    logging.info(f"Expander Agent Output (parsed): {parsed}, Task expander: {task}")
    return parsed, task
