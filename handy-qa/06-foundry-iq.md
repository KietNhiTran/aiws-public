# Foundry IQ — Knowledge Integration for Agents

> **Workshop coverage:** Module 2 covers building agents with tools. This document explains **Foundry IQ** — the managed knowledge layer that gives agents permission-aware access to enterprise data across multiple sources.

---

## Quick Answer Summary

| Question | Short Answer |
|----------|-------------|
| What is Foundry IQ? | A managed knowledge layer that connects agents to enterprise data via multi-source **knowledge bases** powered by **agentic retrieval**. |
| Is it the same as RAG? | It goes beyond traditional RAG. Agentic retrieval decomposes queries, runs parallel searches, reranks semantically, and iterates — achieving ~36% higher response quality than single-shot RAG. |
| Is Azure AI Search required? | **Yes.** Foundry IQ is built on Azure AI Search's agentic retrieval capabilities. |
| Is Foundry Agent Service required? | **No.** You can use knowledge bases from Foundry Agent Service, Microsoft Agent Framework, or any app via the knowledge base APIs. |
| What data sources are supported? | Azure Blob Storage, SharePoint, OneLake, public web data, and more. |
| Does it respect permissions? | Yes — ACLs are synced, Microsoft Purview sensitivity labels are honored, and queries run under the caller's Entra identity. |
| How is it billed? | Free tier available for Azure AI Search + free token allocation. After that, token-based billing via Azure AI Search + LLM charges from Azure OpenAI if using query planning. |
| Is it GA? | **No — currently in public preview** (as of early 2026). |

---

## 1. What Is Foundry IQ?

Agents need context from scattered enterprise content to answer questions accurately. **Foundry IQ** lets you create a configurable, multi-source **knowledge base** that provides agents with **permission-aware responses** grounded in your organisation's data, complete with citations.

### Core Concept

```
┌─────────────────────────────────────────────────────┐
│                  FOUNDRY IQ                          │
│                                                     │
│  ┌─────────────┐   ┌────────────────────────────┐  │
│  │ Knowledge   │──▶│  Agentic Retrieval Engine   │  │
│  │ Base        │   │  (Azure AI Search)          │  │
│  │             │   │  ┌──────────────────────┐   │  │
│  │  ┌────────┐ │   │  │ Query decomposition  │   │  │
│  │  │Source 1│ │   │  │ Parallel search      │   │  │
│  │  │(Blob)  │ │   │  │ Semantic reranking   │   │  │
│  │  ├────────┤ │   │  │ Iterative retrieval  │   │  │
│  │  │Source 2│ │   │  └──────────────────────┘   │  │
│  │  │(SPO)   │ │   │            │                │  │
│  │  ├────────┤ │   │   Optional LLM (Azure       │  │
│  │  │Source 3│ │   │   OpenAI) for query          │  │
│  │  │(Web)   │ │   │   planning & reasoning       │  │
│  │  └────────┘ │   └────────────┬───────────────┘  │
│  └─────────────┘                │                   │
│                    ┌────────────▼───────────────┐   │
│                    │  Citations + extractive     │   │
│                    │  data returned to agent     │   │
│                    └────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

📖 **Reference:** [What is Foundry IQ?](https://learn.microsoft.com/azure/foundry/agents/concepts/what-is-foundry-iq)

---

## 2. Key Capabilities

| Capability | Detail |
|-----------|--------|
| **Multi-source knowledge base** | One knowledge base connects to multiple knowledge sources; multiple agents can share the same base. |
| **Automated indexing** | Document chunking, vector embedding generation, and metadata extraction happen automatically. Schedule recurring indexer runs for incremental refresh. |
| **Hybrid search** | Keyword, vector, or hybrid queries across indexed and remote knowledge sources. |
| **Agentic retrieval** | LLM-powered query planning → subquery decomposition → parallel search → semantic reranking → unified response. |
| **Citations** | Returns extractive data with source citations so agents can trace answers to original documents. |
| **Permission enforcement** | Syncs ACLs, honours Purview sensitivity labels, runs queries under the caller's Entra identity. |

---

## 3. Components

| Component | Description |
|-----------|-------------|
| **Knowledge Base** | Top-level resource that orchestrates agentic retrieval. Defines which knowledge sources to query, the retrieval reasoning effort (minimal / low / medium), and other parameters. |
| **Knowledge Sources** | Connections to indexed content (Blob, SharePoint, OneLake) or remote content (web). A knowledge base references one or more sources. |
| **Agentic Retrieval** | Multi-query pipeline that decomposes complex questions into subqueries, executes them in parallel, semantically reranks, and returns unified responses. Optional LLM adds query planning. |

---

## 4. Retrieval Reasoning Effort Levels

The **retrieval reasoning effort** controls how much LLM-driven planning is used during retrieval:

| Level | Sources | Subqueries | LLM Processing | Answer Synthesis Budget |
|-------|---------|------------|-----------------|------------------------|
| **Minimal** | Up to 10 | None | No LLM, no query planning | N/A |
| **Low** | Up to 3 | Up to 3 | Query planning | 5,000 tokens |
| **Medium** | Up to 5 | Up to 5 | Query planning + iterative search | 10,000 tokens |

> **Tip for agents:** For most Foundry IQ scenarios, use **extractive data** (not answer synthesis). Extractive data returns raw content that agents can reason over. Reserve answer synthesis for standalone apps where retrieval output goes directly to users.

---

## 5. How Foundry IQ Differs from Traditional RAG

| Aspect | Traditional RAG | Foundry IQ |
|--------|----------------|------------|
| Source handling | One agent → one source | One knowledge base → many sources → many agents |
| Query strategy | Single-shot query | Multi-step: decompose → parallel search → rerank → iterate |
| Permission model | App-level or custom | Native ACL sync + Entra identity passthrough + Purview labels |
| Indexing | Manual pipeline setup | Automated chunking, embedding, metadata extraction |
| Benchmarks | Baseline | ~36% higher response quality ([source](https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/foundry-iq-boost-response-relevance-by-36-with-agentic-retrieval/4470720)) |

---

## 6. Relationship to Fabric IQ and Work IQ

Microsoft provides **three IQ workloads** that give agents access to different aspects of your organisation:

| IQ Workload | Layer | What It Covers |
|-------------|-------|---------------|
| **Fabric IQ** | Semantic intelligence for Microsoft Fabric | Business data — ontologies, semantic models, graphs in OneLake & Power BI |
| **Work IQ** | Contextual intelligence for Microsoft 365 | Collaboration signals — documents, meetings, chats, workflows |
| **Foundry IQ** | Managed knowledge for enterprise data | Structured & unstructured data across Azure, SharePoint, OneLake, and the web |

Each is standalone, but they can be used together for comprehensive organisational context.

---

## 7. Getting Started — Two Paths

### Portal (Quick Start)

1. Sign in to [Microsoft Foundry](https://ai.azure.com) → ensure **New Foundry** toggle is ON.
2. Create or select a project.
3. Go to **Build** → **Knowledge** tab:
   - Connect to or create a search service.
   - Create a knowledge base + add knowledge sources.
   - Configure retrieval behaviour.
4. Go to **Agents** tab:
   - Create or select an agent.
   - Connect it to your knowledge base.
   - Test in the playground.

### Programmatic

1. Create knowledge sources (Azure AI Search APIs).
2. Create a knowledge base referencing those sources.
3. Connect an agent to the knowledge base.
4. Test and refine.

📖 **Tutorial:** [Build an end-to-end agentic retrieval solution](https://learn.microsoft.com/azure/search/agentic-retrieval-how-to-create-pipeline)

---

## 8. Connecting Foundry IQ to Foundry Agent Service

**Prerequisites:**
- Azure AI Search service with a knowledge base + knowledge sources.
- Microsoft Foundry project with an LLM deployment (e.g., `gpt-4.1-mini`).
- Role-based access (recommended): **Azure AI User** on the parent resource, **Azure AI Project Manager** for MCP connections.
- Python SDK `azure-ai-projects >= 2.0.0` or REST API version `2025-11-01-preview`.

**Integration uses the MCP tool:** Knowledge bases expose the `knowledge_base_retrieve` MCP tool. The agent calls this tool to orchestrate query planning, decomposition, and retrieval.

📖 **How-to:** [Connect a Foundry IQ knowledge base to Foundry Agent Service](https://learn.microsoft.com/azure/foundry/agents/how-to/foundry-iq-connect)

---

## 9. Pricing & Availability

| Item | Detail |
|------|--------|
| **Free tier** | Azure AI Search free tier + free token allocation for agentic retrieval. Foundry Agent Service doesn't charge for agent instances. |
| **Paid usage** | Agentic retrieval billed by token consumption in Azure AI Search. LLM usage for query planning / answer synthesis incurs separate Azure OpenAI charges. |
| **Regional availability** | Subject to Azure AI Search and Azure OpenAI regional availability. |

---

## 10. Talking Points for Q&A

- **"Why not just use Azure AI Search directly?"** — You can. Agentic retrieval is the engine behind Foundry IQ. Foundry IQ adds the portal experience, native agent integration, and multi-source orchestration on top.
- **"Does this replace our existing RAG pipelines?"** — It can simplify them. Automated chunking, embedding, ACL sync, and multi-query retrieval replace much of the custom pipeline code teams typically build.
- **"Can we test for free?"** — Yes. Use the Azure AI Search free tier + the free agentic retrieval token allocation to build a proof of concept at zero cost.
- **"What about data security?"** — Queries run under the caller's Entra identity; ACLs are synced from source systems; Purview sensitivity labels are honoured. No data leaves your tenant boundary.
- **"How does it compare to Azure OpenAI On Your Data?"** — Foundry IQ supports multiple sources per knowledge base, iterative multi-query retrieval, and native agent integration — a significant step up from the single-source On Your Data approach.

---

## Further Reading

- [What is Foundry IQ? (Microsoft Learn)](https://learn.microsoft.com/azure/foundry/agents/concepts/what-is-foundry-iq)
- [Foundry IQ FAQ](https://learn.microsoft.com/azure/foundry/agents/concepts/foundry-iq-faq)
- [Connect Foundry IQ to Foundry Agent Service](https://learn.microsoft.com/azure/foundry/agents/how-to/foundry-iq-connect)
- [Agentic retrieval overview](https://learn.microsoft.com/azure/search/agentic-retrieval-overview)
- [Tutorial: End-to-end agentic retrieval](https://learn.microsoft.com/azure/search/agentic-retrieval-how-to-create-pipeline)
- [Intro video](https://www.youtube.com/watch?v=slDdNIQCJBQ) | [Deep dive video](https://www.youtube.com/watch?v=uDVkcZwB0EU) | [Portal demo](https://www.youtube.com/watch?v=bHL1jbWjJUc)
