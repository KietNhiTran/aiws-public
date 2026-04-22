# Project Advisor — Foundry Agent Service (SDK)

This is the **code-based equivalent** of the low-code Prompt Agent built in [Module 2](../../modules/02-build-your-first-agent.md). Instead of using the Foundry portal, it creates the same agent programmatically using the **Foundry Python SDK** (`azure-ai-projects`).

The script demonstrates the full lifecycle:
1. Upload knowledge-base documents and create a **vector store** (File Search)
2. Create a **Prompt Agent** with File Search + Code Interpreter tools
3. Run a sample multi-turn conversation to verify the agent
4. Clean up resources

## Prerequisites

- Python 3.10+
- An Azure AI Foundry project with a `gpt-4o` (or equivalent) model deployed
- Azure CLI logged in (`az login`) for `DefaultAzureCredential`
- **Azure AI Owner** role on your Foundry resource
- **Storage Blob Data Contributor** role on your project's storage account

## Quick Start

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env
# Edit .env and fill in your PROJECT_ENDPOINT

# 4. Run the agent
python agent.py
```

## What the Script Does

```
agent.py
  ├─ Creates an AIProjectClient (Foundry SDK)
  ├─ Uploads sample-data/*.md → vector store (File Search)
  ├─ Calls project.agents.create_version() with:
  │     PromptAgentDefinition(
  │       model, instructions, tools=[FileSearchTool, CodeInterpreterTool]
  │     )
  ├─ Runs 3 test prompts via openai.responses.create()
  └─ Cleans up (deletes agent, conversation, vector store)
```

## Project Structure

```
src/foundry-agent/
├── agent.py              # Full lifecycle: create agent, test, clean up
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variable template
└── README.md             # This file

../../sample-data/        # Knowledge-base documents uploaded to File Search
├── safety-policy-2025.md
└── project-governance-framework.md
```

## Key SDK Patterns

### Create a Prompt Agent with tools

```python
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, FileSearchTool, CodeInterpreterTool

project = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=DefaultAzureCredential())
openai = project.get_openai_client()

agent = project.agents.create_version(
    agent_name="project-advisor",
    definition=PromptAgentDefinition(
        model="gpt-4o",
        instructions="...",
        tools=[
            FileSearchTool(vector_store_ids=[vector_store.id]),
            CodeInterpreterTool(),
        ],
    ),
)
```

### Chat with the agent

```python
conversation = openai.conversations.create()

response = openai.responses.create(
    conversation=conversation.id,
    input="What is the company's LTIFR target?",
    extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
)
print(response.output_text)
```

### Clean up

```python
project.agents.delete_version(agent_name=agent.name, agent_version=agent.version)
openai.vector_stores.delete(vector_store.id)
```

## Keeping the Agent

To keep the agent running in your Foundry project after creation, comment out the cleanup section at the bottom of `agent.py`. The agent will then be visible in the **Agents** tab of the Foundry portal and accessible via SDK/API.

## Further Reading

| Resource | Link |
|----------|------|
| Foundry Agent Service overview | https://learn.microsoft.com/azure/foundry/agents/overview |
| File Search tool | https://learn.microsoft.com/azure/foundry/agents/how-to/tools/file-search |
| Code Interpreter tool | https://learn.microsoft.com/azure/foundry/agents/how-to/tools/code-interpreter |
| azure-ai-projects SDK reference | https://learn.microsoft.com/python/api/overview/azure/ai-projects-readme |
