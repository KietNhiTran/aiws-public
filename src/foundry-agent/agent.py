"""
CIMIC Project Advisor — Foundry Agent Service (SDK)

This is the code-based equivalent of the low-code Prompt Agent built in Module 2.
Instead of using the Foundry portal, it creates the same agent programmatically
using the Foundry Python SDK (azure-ai-projects).

The script:
  1. Uploads knowledge-base documents and creates a vector store (File Search)
  2. Creates a Prompt Agent with File Search + Code Interpreter tools
  3. Runs a sample conversation to verify the agent works
  4. Cleans up resources (optional — comment out to keep the agent)

Commented-out examples show how to add more tools:
  - MCP (e.g. Databricks, GitHub)
  - Web Search (Bing grounding)
  - Azure AI Search (existing search index)
  - Azure Functions (serverless actions)
  - Microsoft Fabric Data Agent
  - SharePoint (preview)
  - OpenAPI (custom REST APIs)

SDK Reference:
  https://learn.microsoft.com/python/api/overview/azure/ai-projects-readme
Tool Catalog:
  https://learn.microsoft.com/azure/foundry/agents/concepts/tool-catalog
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=False)

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    PromptAgentDefinition,
    FileSearchTool,
    CodeInterpreterTool,
    # ── Uncomment the imports below as you enable each tool ──────────
    # MCPTool,                        # MCP servers (e.g. Databricks, GitHub)
    # WebSearchTool,                  # Bing-powered web search
    # AzureAISearchTool,              # Existing Azure AI Search index
    #   AzureAISearchToolResource,
    #   AISearchIndexResource,
    #   AzureAISearchQueryType,
    # MicrosoftFabricPreviewTool,     # Microsoft Fabric data agent
    #   FabricDataAgentToolParameters,
    #   ToolProjectConnection,
    # SharepointPreviewTool,          # SharePoint document grounding
    #   SharepointGroundingToolParameters,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROJECT_ENDPOINT = os.environ["PROJECT_ENDPOINT"]
MODEL_DEPLOYMENT_NAME = os.environ.get("MODEL_DEPLOYMENT_NAME", "gpt-4o")

# Path to sample knowledge-base documents (same docs used in Module 2)
ASSETS_DIR = Path(__file__).parent / "../../sample-data"

# ---------------------------------------------------------------------------
# System instructions — mirrors the portal-configured prompt from Module 2
# ---------------------------------------------------------------------------
SYSTEM_INSTRUCTIONS = """\
You are the CIMIC Project Intelligence Advisor, an AI assistant built for CIMIC Group
project managers and operations teams.

## Your Role
- Provide data-driven insights on infrastructure project performance
- Analyze financial data including budget vs. actuals, cost variance, and schedule performance
- Report on equipment fleet status, maintenance schedules, and utilization rates
- Summarize safety incident trends and HSE compliance metrics
- Advise on procurement timing and supplier performance

## Your Knowledge Domain
- CIMIC Group's current operating companies are ONLY the following:
  • CPB Contractors (construction)
  • Thiess (contract services)
  • Sedgman (mineral processing)
  • Pacific Partnerships (public-private partnerships)
- Do NOT mention former subsidiaries (e.g., UGL) unless the user specifically asks
  about historical company structure
- Projects span road/rail infrastructure, tunnelling, building construction, and resource operations
- Financial metrics follow Australian construction industry standards (AS/NZS)

## Data Source Policy
- For specific project data (budgets, costs, schedules, KPIs, incident counts, equipment
  status), ONLY use information provided by your connected tools (File Search, Code
  Interpreter, or API integrations)
- Always cite your source explicitly, for example:
  "According to [document name]..." or "Source: [file name], [section]"
- If you use general knowledge (e.g., industry standards, company structure), clearly
  label it: "Based on general domain knowledge: ..."
- Do NOT use your training knowledge to answer questions about specific project financials,
  timelines, or operational metrics — even if you believe you know the answer
- If no connected tool or document provides the requested data, respond:
  "I don't currently have access to that data. To answer this, I would need
  [specific data source, e.g., a connection to the project financials database]."

## Response Guidelines
- Always cite the data source and time period when presenting numbers
- Present financial figures in AUD unless otherwise specified
- Use tables for comparative data
- Flag any metrics outside normal thresholds (e.g., cost variance > 10%, SPI < 0.9)
- When uncertain, state assumptions clearly and recommend verification
- Never fabricate or infer project-specific data from training knowledge — only report
  what your connected tools and documents provide

## Safety First
- Always prioritize safety-related queries
- Escalate any critical safety concerns with a clear recommendation to contact the HSE team
"""


# ═══════════════════════════════════════════════════════════════════════════
# ADDITIONAL TOOLS — uncomment and configure the ones you need
# ═══════════════════════════════════════════════════════════════════════════
# Each function returns a tool instance you can add to the agent's tools list.
# See: https://learn.microsoft.com/azure/foundry/agents/concepts/tool-catalog


# ── 1. MCP Tool (Model Context Protocol) ─────────────────────────────────
# Connect to any MCP-compatible server. Great for Databricks, GitHub, etc.
# Docs: https://learn.microsoft.com/azure/foundry/agents/how-to/tools/model-context-protocol
#
# def create_databricks_mcp_tool():
#     """Connect to Databricks Unity Catalog via MCP.
#
#     Prerequisites:
#       - Create an MCP connection in your Foundry project (portal → Connected resources)
#       - The connection stores the Databricks host URL and auth credentials
#     """
#     return MCPTool(
#         server_label="databricks",
#         server_url="https://<your-databricks-host>/api/mcp",
#         require_approval="never",  # "always" for human-in-the-loop
#         project_connection_id="<your-databricks-mcp-connection-name>",
#     )


# ── 2. Web Search (Bing grounding) ───────────────────────────────────────
# Real-time public web search with inline citations. No extra resources needed.
# Docs: https://learn.microsoft.com/azure/foundry/agents/how-to/tools/web-search
#
# def create_web_search_tool():
#     """Enable the agent to search the public web for real-time information."""
#     return WebSearchTool()


# ── 3. Azure AI Search ───────────────────────────────────────────────────
# Ground the agent on an existing Azure AI Search index (your own data).
# Docs: https://learn.microsoft.com/azure/foundry/agents/how-to/tools/ai-search
#
# def create_ai_search_tool(project):
#     """Connect to an Azure AI Search index for enterprise RAG.
#
#     Prerequisites:
#       - An Azure AI Search resource with a populated index
#       - A connection to it in your Foundry project
#     """
#     connection = project.connections.get("<your-search-connection-name>")
#     return AzureAISearchTool(
#         azure_ai_search=AzureAISearchToolResource(
#             indexes=[
#                 AISearchIndexResource(
#                     project_connection_id=connection.id,
#                     index_name="<your-index-name>",
#                     query_type=AzureAISearchQueryType.SIMPLE,
#                 ),
#             ]
#         )
#     )


# ── 4. Microsoft Fabric Data Agent (preview) ─────────────────────────────
# Query structured data in Microsoft Fabric via a data agent.
# Docs: https://learn.microsoft.com/azure/foundry/agents/how-to/tools/fabric
#
# def create_fabric_tool(project):
#     """Connect to a Microsoft Fabric data agent for structured data queries.
#
#     Prerequisites:
#       - A Fabric data agent published in your Fabric workspace
#       - A connection to Fabric in your Foundry project
#     """
#     connection = project.connections.get("<your-fabric-connection-name>")
#     return MicrosoftFabricPreviewTool(
#         fabric_dataagent_preview=FabricDataAgentToolParameters(
#             project_connections=[
#                 ToolProjectConnection(project_connection_id=connection.id)
#             ]
#         )
#     )


# ── 5. SharePoint (preview) ──────────────────────────────────────────────
# Ground the agent on documents stored in SharePoint Online.
# Docs: https://learn.microsoft.com/azure/foundry/agents/how-to/tools/sharepoint
#
# def create_sharepoint_tool(project):
#     """Connect to SharePoint for document grounding.
#
#     Prerequisites:
#       - A SharePoint connection in your Foundry project
#       - Azure AD app registration with SharePoint permissions
#     """
#     connection = project.connections.get("<your-sharepoint-connection-name>")
#     return SharepointPreviewTool(
#         sharepoint_grounding=SharepointGroundingToolParameters(
#             project_connections=[
#                 ToolProjectConnection(project_connection_id=connection.id)
#             ]
#         )
#     )


# ═══════════════════════════════════════════════════════════════════════════
# MORE TOOLS (not shown above — see links for SDK examples)
# ═══════════════════════════════════════════════════════════════════════════
#
# Azure Functions     — Trigger serverless functions from the agent
#   https://learn.microsoft.com/azure/foundry/agents/how-to/tools/azure-functions
#
# Function Calling    — Define custom functions; your app executes them
#   https://learn.microsoft.com/azure/foundry/agents/how-to/tools/function-calling
#
# OpenAPI             — Call any REST API described by an OpenAPI spec
#   https://learn.microsoft.com/azure/foundry/agents/how-to/tools/openapi
#
# Image Generation    — Generate images as part of conversations (preview)
#   https://learn.microsoft.com/azure/foundry/agents/how-to/tools/image-generation
#
# Browser Automation  — Perform browser tasks via natural language (preview)
#   https://learn.microsoft.com/azure/foundry/agents/how-to/tools/browser-automation
#
# Computer Use        — Interact with computer UIs (preview)
#   https://learn.microsoft.com/azure/foundry/agents/how-to/tools/computer-use
#
# Full tool catalog:
#   https://learn.microsoft.com/azure/foundry/agents/concepts/tool-catalog


def main() -> None:
    """Create the CIMIC Project Advisor agent via Foundry Agent Service SDK."""

    # ----- Clients --------------------------------------------------------
    project = AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=DefaultAzureCredential(),
    )
    openai = project.get_openai_client()

    # ----- 1. Upload documents & create a vector store (File Search) ------
    print("Creating vector store and uploading knowledge-base documents...")
    vector_store = openai.vector_stores.create(name="CIMICKnowledgeBase")

    doc_files = [
        ASSETS_DIR / "cimic-safety-policy-2025.md",
        ASSETS_DIR / "project-governance-framework.md",
    ]
    for doc_path in doc_files:
        with doc_path.open("rb") as fh:
            openai.vector_stores.files.upload_and_poll(
                vector_store_id=vector_store.id,
                file=fh,
            )
        print(f"  Uploaded: {doc_path.name}")

    # ----- 2. Create the Prompt Agent ------------------------------------
    #
    # Build the tools list — add or remove tools here as needed.
    # Each tool is independent; combine as many as you like.
    #
    tools = [
        # ── Active tools ──────────────────────────────────────────────
        FileSearchTool(vector_store_ids=[vector_store.id]),
        CodeInterpreterTool(),

        # ── Uncomment to enable additional tools ──────────────────────
        # create_databricks_mcp_tool(),      # Databricks via MCP
        # create_web_search_tool(),          # Bing web search
        # create_ai_search_tool(project),    # Azure AI Search index
        # create_fabric_tool(project),       # Microsoft Fabric
        # create_sharepoint_tool(project),   # SharePoint documents
    ]

    print("\nCreating agent: cimic-project-advisor ...")
    agent = project.agents.create_version(
        agent_name="cimic-project-advisor-4",
        definition=PromptAgentDefinition(
            model=MODEL_DEPLOYMENT_NAME,
            instructions=SYSTEM_INSTRUCTIONS,
            tools=tools,
        ),
        description="CIMIC Project Intelligence Advisor with File Search and Code Interpreter.",
    )
    print(f"  Agent created — name: {agent.name}, version: {agent.version}")

    # ----- 3. Test the agent with a sample conversation -------------------
    print("\n--- Test Conversation ---")
    conversation = openai.conversations.create()

    # Turn 1 — File Search question
    response = openai.responses.create(
        conversation=conversation.id,
        input="What is CIMIC's LTIFR target for 2025?",
        extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
    )
    print(f"User: What is CIMIC's LTIFR target for 2025?")
    print(f"Agent: {response.output_text}\n")

    # Turn 2 — Code Interpreter question (follow-up in same conversation)
    response = openai.responses.create(
        conversation=conversation.id,
        input=(
            "If a CIMIC project has a budget of AUD 450M, actual costs of AUD 412M, "
            "and planned value of AUD 420M, calculate the Cost Variance, "
            "Schedule Variance, CPI, and SPI. Show the formulas."
        ),
        extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
    )
    print(f"User: Calculate EVM metrics for budget=450M, AC=412M, PV=420M")
    print(f"Agent: {response.output_text}\n")

    # Turn 3 — Governance question
    response = openai.responses.create(
        conversation=conversation.id,
        input="What cost variance threshold triggers a red flag on CIMIC projects?",
        extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
    )
    print(f"User: What cost variance threshold triggers a red flag?")
    print(f"Agent: {response.output_text}\n")

    # # ----- 4. Clean up (comment out to keep the agent) --------------------
    # print("Cleaning up resources...")
    # openai.conversations.delete(conversation_id=conversation.id)
    # project.agents.delete_version(agent_name=agent.name, agent_version=agent.version)
    # openai.vector_stores.delete(vector_store.id)
    # print("Done — agent, conversation, and vector store deleted.")


if __name__ == "__main__":
    main()
