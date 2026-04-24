# Connecting Microsoft Foundry agents to enterprise data with Databricks Genie and Fabric

This project demonstrates how to build a Microsoft Foundry agent that queries live enterprise data across Azure Databricks and Microsoft Fabric. The full source code and deployment scripts are available at [github.com/KietNhiTran/aiws-public](https://github.com/KietNhiTran/aiws-public).

## Microsoft Foundry

Microsoft Foundry is the agent platform on Azure. You create agents, attach tools, evaluate them, and deploy to production. The platform provides built-in tools including Bing-grounded web search, a code interpreter (sandboxed Python), file search, and Azure AI Search. You can extend agents with custom function tools, OpenAPI specs, or MCP (Model Context Protocol) connections to external services.

Foundry handles agent versioning, batch evaluation against test datasets, and deployment behind API endpoints. This makes it the management and orchestration layer, not just a chat interface.

> [INSERT SCREENSHOT: Foundry portal showing an agent with multiple tools configured]

## Microsoft Fabric and Data Agents

Microsoft Fabric unifies data warehousing, engineering, and business intelligence in one platform. If your organisation uses Power BI, your semantic models already live in Fabric.

Fabric Data Agents query data sources within a Fabric workspace: lakehouses, SQL databases, Power BI semantic models, and mirrored databases. You configure each agent with natural language instructions describing the data and how to respond. The agent translates user questions into queries against those sources.

Fabric Data Agents can be registered as tools in Foundry. This means your existing Power BI semantic models and lakehouse tables become accessible to a Foundry agent alongside web search, code interpreter, and other tools.

## Architecture

> [INSERT DIAGRAM: Foundry agent at center. Left side: MCP connection to Databricks Genie, pointing to Unity Catalog with RLS. Right side: Fabric Data Agent connection, pointing to lakehouse, SQL DB, mirrored Databricks catalog, and Power BI semantic model]

There are two integration paths. Both require no code on the Foundry side.

**Databricks Genie via MCP** - Databricks exposes managed MCP servers for Genie Spaces. A Genie Space is a curated NL-to-SQL interface over specific Unity Catalog tables, with author-defined instructions and sample queries. You register the MCP endpoint in Foundry, and the agent sends natural language questions to Genie, which generates SQL, executes it on a SQL Warehouse, and returns results. Unity Catalog permissions including row-level security are enforced per user via Entra ID passthrough.

**Fabric mirroring + Data Agents** - Fabric mirrors Unity Catalog metadata (no data movement), giving Fabric read access to Databricks tables. You then configure Fabric Data Agents over the mirrored tables alongside lakehouse data, SQL databases, and semantic models. This path is suited for organisations that want to combine Databricks data with existing Fabric assets, particularly Power BI semantic models that already contain business logic and measures.

## Why Foundry as the orchestration layer

Genie handles structured data queries well. Fabric Data Agents do the same within Fabric. Foundry adds value by composing these with other capabilities in a single agent.

A user asks "show me projects over budget" and the agent calls Genie. The follow-up is "what are the current regulatory requirements for that project type?" and the agent uses web search. Next, "calculate the projected cost at completion using CPI from the data" and the agent runs the formula in code interpreter. One conversation, three different tools, selected automatically.

> [INSERT GIF: Single conversation where the agent uses Genie for data, web search for context, and code interpreter for a calculation]

Foundry also provides the production lifecycle. You evaluate agent accuracy with batch runs, compare versions, and deploy to an API endpoint with authentication and monitoring. This is the layer that moves an agent from prototype to production.

## What the project deploys

The repository contains deployment scripts for the full stack:

**Databricks** (Databricks Asset Bundles):
- Four Unity Catalog tables with synthetic data across projects, equipment, safety, and procurement
- Row-level security with group-based filtering per division
- Five Genie Spaces with domain-specific instructions
- A medallion pipeline (bronze, silver, gold) for supply chain data

**Fabric** (Python scripts):
- Workspace with lakehouse, SQL database, semantic model, and mirrored Databricks catalog
- Five Data Agents with pre-written instructions and data source mappings
- Agent instruction files ready to paste into the Fabric portal

> [INSERT SCREENSHOT: Fabric workspace showing the deployed lakehouse, SQL database, mirrored catalog, and Data Agents]

**Configuration** - All deployment is driven by a single `.env.example` file. You provide your Azure tenant, Databricks workspace URL, Fabric capacity name, and catalog details. The scripts handle the rest.

```
# Clone and configure
git clone https://github.com/KietNhiTran/aiws-public.git
cp .env.example .env.local
# Fill in your values, then deploy:
cd src/databricks && databricks bundle deploy -t dev
cd src/fabric && python scripts/01_deploy_workspace.py
```

> [INSERT GIF: Terminal showing the deployment running]

## Summary

This project connects Microsoft Foundry to enterprise data in Databricks and Fabric using two zero-code integration paths: Genie MCP for direct NL-to-SQL, and Fabric mirroring with Data Agents for combined Fabric and Databricks data access. Foundry provides the agent management layer on top, with web search, code interpreter, evaluation, and production deployment.

Full walkthrough: [modules/03-databricks-integration.md](https://github.com/KietNhiTran/aiws-public/blob/master/modules/03-databricks-integration.md)
