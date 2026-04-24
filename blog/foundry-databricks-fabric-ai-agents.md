# Building an AI agent that actually talks to your data

Most enterprise AI demos hit the same wall. You build a chatbot, connect it to GPT-4o, and it answers general questions well enough. Then someone asks "what's our cost overrun on the Queensland rail project?" and the bot hallucinates a number. Your data lives in Databricks, Fabric, or a dozen other systems, and the agent has no idea any of it exists.

This post walks through how we built a working multi-source AI agent using Microsoft Foundry, Databricks Genie, and Fabric Data Agents. The full source code is open at [github.com/KietNhiTran/aiws-public](https://github.com/KietNhiTran/aiws-public).

## What Foundry actually does

Microsoft Foundry (previously Azure AI Foundry) is an agent management platform. You create agents, give them tools, and deploy them. That part is straightforward. What makes it useful in practice is the tool catalog.

Out of the box, an agent can use web search (Bing-grounded), a code interpreter (runs Python in a sandbox), file search over uploaded documents, and Azure AI Search for RAG over your own indexes. You can also add custom function tools or connect to external services through MCP (Model Context Protocol) or API specs.

The point is that Foundry agents aren't just chat wrappers. They're orchestrators that pick the right tool for each question. Ask about public news, the agent calls web search. Ask it to calculate something, it writes and runs Python. Ask about your project data, it calls Genie or a Fabric Data Agent.

> [INSERT GIF: Foundry agent switching between web search, code interpreter, and Genie tool in a single conversation]

## A quick word on Fabric and Data Agents

Microsoft Fabric is a unified analytics platform that brings together data warehousing, data engineering, data science, and business intelligence into one product. If your org already uses Power BI, Fabric is where those semantic models live.

Fabric Data Agents are a relatively new addition. You point them at data sources within your Fabric workspace (lakehouses, SQL databases, semantic models, mirrored databases) and give them natural language instructions. The agent then answers questions by querying those sources directly. Think of them as Fabric-native copilots that understand your data schema and business context.

The interesting part: you can bring a Fabric Data Agent into Foundry as a tool, alongside other tools your agent already uses. Your Power BI semantic models, lakehouse tables, and SQL databases become queryable through natural language in the same agent that also has web search and code execution.

## The architecture

Here's what the full setup looks like.

> [INSERT DIAGRAM: Architecture showing Foundry agent at center, with MCP connection to Databricks Genie on one side and Fabric Data Agent connection on the other. Databricks side shows Unity Catalog tables with RLS. Fabric side shows lakehouse, SQL DB, mirrored Databricks catalog, and semantic model feeding into 5 Data Agents]

There are two paths from Foundry to your Databricks data. Both are zero-code on the Foundry side.

**Path 1: Genie through MCP.** Databricks exposes managed MCP servers for Genie Spaces. You register the MCP endpoint in Foundry, and your agent can ask natural language questions against any Genie Space. Genie translates the question to SQL, runs it against a SQL Warehouse, and returns the result. All Unity Catalog permissions (including row-level security) are enforced per user through Entra ID passthrough.

**Path 2: Fabric mirroring.** Fabric can mirror your Unity Catalog, which means Fabric gets read access to your Databricks tables without copying data. You then set up Fabric Data Agents over those mirrored tables, add a lakehouse and SQL database for supplementary data, and wire the whole thing into Foundry. This path is better when you want to combine Databricks data with other Fabric sources like Power BI models or curated SQL summaries.

We implemented both. The Genie path took about 15 minutes to configure. The Fabric path took longer because of the workspace setup, but the deployment scripts in our repo automate most of it.

## Why not just use Genie directly?

Genie is excellent for structured data queries. But Foundry adds capabilities that Genie alone doesn't have.

A user might ask a question that starts with data ("show me red-status projects") and then follow up with something that needs web context ("what are the latest safety regulations for tunnel construction in NSW?"). Genie can't answer the second question. A Foundry agent can, because it also has web search.

Or someone asks "calculate the projected cost at completion using the CPI from our data." The agent fetches the CPI through Genie, then uses the code interpreter to run the EAC formula and return the result with a chart. That multi-step reasoning across tools is what Foundry handles.

> [INSERT GIF: Agent answering a data question via Genie, then a follow-up using web search, in one thread]

Foundry also gives you agent versioning, evaluation pipelines, and a deployment model for production. You can run batch evaluations against test datasets, compare agent versions on accuracy, and deploy behind an API endpoint. Genie doesn't cover that lifecycle.

## What we built

The [open-source workshop](https://github.com/KietNhiTran/aiws-public) includes everything needed to reproduce this setup:

**Databricks side** (deployed via Asset Bundles):
- Four Unity Catalog tables with synthetic data (projects, equipment, safety, procurement)
- Row-level security configured with groups, so different users see different divisions
- Five Genie Spaces with curated instructions for each domain
- A medallion pipeline (bronze/silver/gold) for supply chain data

**Fabric side** (deployed via Python scripts):
- A workspace with a lakehouse, SQL database, semantic model, and mirrored Databricks catalog
- Five Data Agents, each with detailed instructions and specific data source assignments
- Agent instruction files you can copy-paste directly into the Fabric portal

**Foundry side:**
- An agent with MCP tools for Genie and connections to Fabric Data Agents
- Web search and code interpreter enabled for multi-source reasoning

Everything is parameterized through environment files. No hardcoded credentials, workspace IDs, or customer names. Clone the repo, fill in your `.env.local`, run the deployment scripts, and you have a working environment.

> [INSERT GIF: Running the deployment, showing Databricks bundle deploy and Fabric workspace creation]

## Where this is heading

The gap between "AI demo" and "AI that works with our data" has been the main blocker for most enterprise teams we've talked to. The tooling has caught up. Genie MCP and Fabric Data Agents both went from preview to usable in the last few months, and Foundry's tool catalog makes it possible to compose them without writing middleware.

If you want to try it, start with the repo. Module 3 has the full walkthrough: [modules/03-databricks-integration.md](https://github.com/KietNhiTran/aiws-public/blob/master/modules/03-databricks-integration.md).
