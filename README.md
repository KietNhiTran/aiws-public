# Microsoft Foundry Workshop — AI Agents for Infrastructure Operations

## Building Intelligent AI Agents for Infrastructure Operations

**Duration:** Full-day workshop (5.5–7 hours)  
**Level:** Intermediate  
**Approach:** Low-code via Microsoft Foundry Agent Service

---

## Workshop Overview

This workshop demonstrates how to build AI agents using **Microsoft Foundry** that leverage **Azure Databricks** as a data source — enabling intelligent decision support for project cost forecasting, equipment maintenance scheduling, safety incident analysis, and supply chain optimization.

The sample scenario uses a fictional construction & infrastructure company (**Contoso Construction Group**) operating across construction (Contoso Build), mining services (Contoso Mining), engineering (Contoso Engineering), and partnerships (Contoso Partnerships).

### Demo Scenario: **Infrastructure Project Intelligence Agent**

A project manager needs an AI agent that can:
- Query project financial data stored in Databricks (budget, schedule variance, RAG status)
- Analyse equipment telemetry for predictive maintenance across the equipment fleet
- Retrieve safety incident reports, generate trend charts, and compare against Zero Harm policy
- Generate procurement recommendations by combining internal pricing with live market data via Bing

---

## Workshop Modules

| Module | Title | Duration | Description |
|--------|-------|----------|-------------|
| 1 | [Microsoft Foundry Overview & Setup](modules/01-foundry-setup.md) | 80 min | Foundry overview, why agents for infrastructure, AI agent concepts, enterprise governance, provision resource & project, deploy models |
| 2 | [Build Your First Agent (Low-Code)](modules/02-build-agent-low-code.md) | 90 min | Create a Prompt agent via Foundry Agent Service portal |
| 3 | [Integrate Azure Databricks as Data Source](modules/03-databricks-integration.md) | 90 min | Connect agents to Databricks via MCP-based Genie + Fabric mirroring |
| 4 | [Azure Foundry Toolkit Deep Dive](modules/04-foundry-toolkit.md) | 60 min | Bing Grounding (hands-on), Azure AI Search & Custom Functions (concept walkthrough) |
| 5 | [End-to-End Demo: Project Intelligence Agent](modules/05-e2e-demo.md) | 30–45 min | Wire all tools together, run test scenarios, evaluate the agent |

---

## Prerequisites

- Azure subscription with an active account
- Access to a role that allows creating a Foundry resource (e.g., **Azure AI Owner** on the subscription or resource group)
- Azure Databricks workspace with sample data loaded
- Modern web browser (Edge/Chrome)
- Basic understanding of REST APIs and JSON

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    Microsoft Foundry                             │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Foundry Resource → Project: project-intelligence          │  │
│  │                                                            │  │
│  │  ┌────────────┐  ┌──────────────┐  ┌───────────────────┐  │  │
│  │  │  Prompt     │  │ File Search  │  │ Code Interpreter  │  │  │
│  │  │  Agent      │  │ (policies,   │  │ (EVM, charts)     │  │  │
│  │  │  (GPT-4o)   │  │  governance) │  │                   │  │  │
│  │  └─────┬──────┘  └──────────────┘  └───────────────────┘  │  │
│  └────────┼──────────────────────────────────────────────────┘  │
│           │                                                     │
│  ┌────────▼────────────────────────────────────────────────┐    │
│  │                    Tool Connections                      │    │
│  └────┬──────────────────┬─────────────────────┬──────────┘    │
└───────┼──────────────────┼─────────────────────┼───────────────┘
        │                  │                     │
  ┌─────▼─────┐    ┌──────▼──────┐       ┌──────▼──────┐
  │  Azure    │    │  Microsoft  │       │    Bing     │
  │Databricks │    │   Fabric    │       │  Grounding  │
  │(Genie MCP)│    │ (Mirroring) │       │ (web data)  │
  │ 4 tables  │    │             │       │             │
  └───────────┘    └─────────────┘       └─────────────┘
```

---

## Sample Data Context

The workshop uses simulated datasets representing a construction company's operations across multiple systems:

| Dataset | Description | System | Table |
|---------|-------------|--------|-------|
| Project Financials | Cost tracking, budget vs. actuals, schedule variance | Azure Databricks | `workshop.projects.financials` |
| Equipment Telemetry | Equipment fleet sensor data — engine temp, fuel, hours | Azure Databricks | `workshop.equipment.equipment_telemetry` |
| Safety Incidents | HSE incident reports, near-misses, risk categories | Azure Databricks | `workshop.safety.incidents` |
| Material Procurement | Supplier pricing, lead times, price trends | Azure Databricks | `workshop.procurement.materials` |

---

## Getting Started

Begin with **[Module 1: Microsoft Foundry Setup](modules/01-foundry-setup.md)**.
