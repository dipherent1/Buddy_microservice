## Folder structure

````

├── app/
│
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI entry point
│   ├── config.py                   # Environment configs (dotenv / settings)
│   ├── container.py                # Dependency injection setup
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── agent_router.py     # Endpoints for AI Agent interactions
│   │   │   └── mcp_router.py       # Endpoints for MCP server operations
│   │   └── schemas/
│   │       ├── __init__.py
│   │       ├── agent_schema.py     # Request/Response models for agents
│   │       └── mcp_schema.py       # Request/Response models for MCP
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── exceptions.py           # Custom exception classes
│   │   ├── logger.py               # Central logging configuration
│   │   ├── utils.py                # Shared helper functions
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── agent_service.py        # LangChain agent management logic
│   │   ├── mcp_service.py          # MCP server interactions
│   │   └── registry.py             # For registering & managing multiple agents
│   │
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── agent_model.py          # Data models for agent definitions
│   │   ├── mcp_model.py            # Data models for MCP context
│   │   └── base_model.py           # Shared domain base classes
│   │
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── db.py                   # If you add a DB (e.g., for logs/state)
│   │   ├── http_client.py          # Async external API/MCP HTTP calls
│   │   └── langchain_setup.py      # LangChain tool & LLM initialization
│   │
│   └── tests/
│       ├── __init__.py
│       ├── test_agents.py
│       └── test_mcp.py
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
└── pyproject.toml  (optional if using Poetry)

````
