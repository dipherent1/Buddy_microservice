# AI Agent Microservice

This project is an AI Agent Microservice built with FastAPI. It provides a framework for creating and managing AI agents that can interact with various external services like Google Calendar, Gmail, Google Docs, Notion, and Slack.

The application is structured as a FastAPI microservice. The entry point is `app/main.py`, which initializes the FastAPI app, sets up logging, and manages the lifecycle of a "Model-Context-Protocol" (MCP) client. The service exposes endpoints for interacting with different AI agents.

## Key Features

- **AI Agents:** The core of the project is its ability to host different types of AI agents. The `app/services` directory includes an `ExecutionAgentService` and an `ExpanderAgentService`, suggesting different agent capabilities.
- **Model-Context-Protocol (MCP):** A significant part of the project is the MCP, which appears to be a custom protocol for interacting with external tools and services. The `app/mcp` directory contains implementations for various services:
  - Google Calendar
  - Gmail
  - Google Docs & Sheets
  - Notion
  - Slack
- **FastAPI Backend:** The project uses FastAPI to create a robust and modern API. It includes routers for handling agent-related requests (`agent_router.py`) and general AI interactions (`ai_router.py`).
- **Structured AI Logic:** The `app/ai` directory is where all the main agents are. It is well-organized with subdirectories for prompts, input/output schemas, and tools that the AI agents can use.
- **Database Integration:** The project is set up to connect to a database (as seen in `app/infrastructure/db.py` and `app/infrastructure/database`), likely for storing agent state, logs, or other relevant data.

## Available Agents

This microservice contains a suite of specialized AI agents designed to work together to understand and execute user requests.

- **Clarify Agent:** Asks clarifying questions to better understand the user's needs when the initial prompt is ambiguous.
- **Classify Agent:** Categorizes the user's problem into a specific domain (e.g., finance, personal, professional).
- **Domain Agent:** Develops high-level strategies and objectives based on the problem's domain.
- **Task Agent:** Breaks down strategic objectives into smaller, actionable tasks.
- **Automation Agent:** Creates a detailed, step-by-step plan to automate the generated tasks using available tools.
- **Clarify Automation Agent:** Asks for more details if a task is too ambiguous to be automated.
- **Execution Agent:** Executes the automation plan by calling the necessary tools and services.
- **User Memory Agent:** Manages and updates a summary of the user's preferences and past interactions to provide a personalized experience.
- **Venting Agent:** Provides a space for the user to express frustrations, offering empathetic responses without taking action.
- **Problem Space Agent:** An orchestrator agent that uses the Classify, Domain, and Automation agents in a chain to create a comprehensive plan from a single user prompt.
- **Expander Agent:** Enriches a task with external information by performing web searches to gather context and best practices.

## How to Run the Project

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
2.  **Set up Environment Variables:**
    Create a `.env` file based on the `.env.example` and provide the necessary configuration, especially for the database connection and any API keys for the MCP services.
3.  **Run the Application:**
    ```bash
    uvicorn app.main:app --reload
    ```
    The application will be available at `http://127.0.0.1:8000`.

## API Endpoints

The service exposes several endpoints under the `/agent` and `/ai` prefixes. You can explore the available endpoints by accessing the interactive API documentation provided by FastAPI at `http://127.0.0.1:8000/docs`.

## Folder structure

├── app/
│ ├── **init**.py
│ ├── main.py # FastAPI entry point
│ ├── config.py # Environment configs (dotenv / settings)
│ ├── container.py # Dependency injection setup
│ │
│ ├── ai/ # Main directory for AI agent logic
│ │ ├── **init**.py
│ │ ├── ai.py # Core AI agent implementation
│ │ ├── input_schema/ # Pydantic schemas for AI input
│ │ ├── output_schema/ # Pydantic schemas for AI output
│ │ ├── prompt/ # Prompts for different AI agents
│ │ └── tools/ # Tools that AI agents can use
│ │
│ ├── api/
│ │ ├── **init**.py
│ │ ├── routers/
│ │ │ ├── **init**.py
│ │ │ ├── agent_router.py # Endpoints for AI Agent interactions
│ │ │ └── mcp_router.py # Endpoints for MCP server operations
│ │ └── schemas/
│ │ ├── **init**.py
│ │ ├── agent_schema.py # Request/Response models for agents
│ │ └── mcp_schema.py # Request/Response models for MCP
│ │
│ ├── core/
│ │ ├── **init**.py
│ │ ├── exceptions.py # Custom exception classes
│ │ ├── logger.py # Central logging configuration
│ │ ├── utils.py # Shared helper functions
│ │
│ ├── services/
│ │ ├── **init**.py
│ │ ├── agent_service.py # LangChain agent management logic
│ │ ├── mcp_service.py # MCP server interactions
│ │ └── registry.py # For registering & managing multiple agents
│ │
│ ├── domain/
│ │ ├── **init**.py
│ │ ├── agent_model.py # Data models for agent definitions
│ │ ├── mcp_model.py # Data models for MCP context
│ │ └── base_model.py # Shared domain base classes
│ │
│ ├── infrastructure/
│ │ ├── **init**.py
│ │ ├── db.py # If you add a DB (e.g., for logs/state)
│ │ ├── http_client.py # Async external API/MCP HTTP calls
│ │ └── langchain_setup.py # LangChain tool & LLM initialization
│ │
│ └── tests/
│ ├── **init**.py
│ ├── test_agents.py
│ └── test_mcp.py
│

## MCP configuration and telemetry

- MCP servers are launched via `app/mcp/config/mcp_config.json`. The Google Calendar MCP server is configured to run with the project's virtual environment (`.venv/bin/python`) so that required packages are available.
- Prefer module invocation with `-m` and set an explicit `cwd` in your config. Example:

  ```json
  {
    "mcpServers": {
      "google-calendar": {
        "transport": "stdio",
        "command": ".venv/bin/python",
        "args": ["-m", "app.mcp.google_calendar_mcp.app"],
        "cwd": "/ABSOLUTE/PATH/TO/project-x-ai-service",
        "env": {
          "PYTHONUNBUFFERED": "1",
          "GOOGLE_CREDENTIALS_PATH": "/ABSOLUTE/PATH/TO/project-x-ai-service/app/mcp/google_calendar_mcp/credentials.json"
        }
      }
    }
  }
  ```

- To disable anonymized telemetry from the MCP client library, the app now sets `MCP_USE_ANONYMIZED_TELEMETRY=false` by default at process start. You can override this by setting `MCP_USE_ANONYMIZED_TELEMETRY=true` in your environment before starting the app.

## Google Calendar MCP setup

- Place your OAuth client secrets JSON at `app/mcp/google_calendar_mcp/credentials.json`, or set the environment variable `GOOGLE_CREDENTIALS_PATH` to an absolute path to your credentials file.
- The first time a tool call requires authentication, the Google OAuth flow may try to open a browser. For headless environments, consider pre-authorizing and providing a `token.json` alongside the server (or configure an alternative OAuth flow).
  ├── requirements.txt
  ├── .env
  ├── README.md
  └── pyproject.toml (optional if using Poetry)
