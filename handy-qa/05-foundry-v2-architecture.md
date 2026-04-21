# Foundry V2 Architecture & Migration

> **Workshop coverage:** Module 1 introduces the new Foundry portal and project creation. This document explains the underlying architecture, the differences from hub-based (classic) Azure AI Studio, the resource hierarchy, and migration guidance.

---

## Quick Answer Summary

| Question | Short Answer |
|----------|-------------|
| What changed from Azure AI Studio? | **Foundry V2** replaces hubs with a **Foundry resource (account)** → **Project** hierarchy. Simplified, flatter structure. |
| Do we need to migrate? | Not immediately — classic hubs still work. But new features only ship on the V2 architecture. |
| Is it a different portal? | Same portal ([ai.azure.com](https://ai.azure.com)) — toggle **"New Foundry"** ON in the upper-right corner. |
| What's the resource called in ARM? | `Microsoft.CognitiveServices/accounts` (kind: `AIServices`). Projects are child resources. |
| Can V2 projects connect to the same models? | Yes — model deployments exist at the account level and are shared across projects. |

---

## 1. Architecture Overview

### Resource Hierarchy

```
Azure Subscription
  └── Resource Group
        └── Foundry Resource (Account)
        │     ├── Model Deployments (shared across projects)
        │     ├── Connections (e.g., Azure AI Search, Storage)
        │     ├── Network Configuration
        │     └── Security & RBAC (control plane)
        │
        ├── Project A (child resource)
        │     ├── Agents
        │     ├── Evaluations
        │     ├── Traces
        │     └── Files & Data
        │
        └── Project B (child resource)
              ├── Agents
              └── ...
```

### Classic (Hub-Based) vs. Foundry V2

| Aspect | Classic (Hub + Project) | Foundry V2 (Account + Project) |
|--------|------------------------|-------------------------------|
| **Top-level resource** | Azure AI Hub | Foundry Resource (Account) |
| **ARM resource type** | `Microsoft.MachineLearning/workspaces` (kind: Hub) | `Microsoft.CognitiveServices/accounts` (kind: AIServices) |
| **Project relationship** | Workspace linked to hub | Child resource of the account |
| **Model deployments** | Per workspace | Per account (shared across projects) |
| **Networking** | Hub-level VNet | Account-level VNet (BYO or Managed) |
| **Setup complexity** | Hub + dependent resources (Storage, Key Vault, etc.) | Single resource with optional BYOS |
| **Agent support** | Azure AI Agent Service (connected) | Native agent framework (built-in) |
| **Portal experience** | Azure AI Studio | Microsoft Foundry portal (ai.azure.com) |

📖 **Reference:** [Microsoft Foundry architecture](https://learn.microsoft.com/azure/foundry/concepts/architecture)

### Visual Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                   Microsoft Foundry Portal                    │
│                     (ai.azure.com)                            │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │                Control Plane                           │  │
│  │  Foundry Resource (Account)                            │  │
│  │  ├── Model Catalog & Deployments                       │  │
│  │  ├── Connections (AI Search, Storage, Cosmos DB)       │  │
│  │  ├── Networking (VNet, Private Endpoints)              │  │
│  │  ├── RBAC & Security Policies                          │  │
│  │  └── Guardrails & Content Filters                      │  │
│  └────────────────────────────────────────────────────────┘  │
│           │                              │                    │
│  ┌────────┴────────┐          ┌─────────┴────────┐          │
│  │   Data Plane    │          │   Data Plane     │          │
│  │   Project A     │          │   Project B      │          │
│  │                 │          │                  │          │
│  │  ├── Agents     │          │  ├── Agents      │          │
│  │  ├── Evals      │          │  ├── Evals       │          │
│  │  ├── Traces     │          │  ├── Traces      │          │
│  │  ├── Files      │          │  ├── Files       │          │
│  │  └── Playgrounds│          │  └── Playgrounds │          │
│  └─────────────────┘          └──────────────────┘          │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Control Plane vs. Data Plane

| Aspect | Control Plane | Data Plane |
|--------|--------------|------------|
| **Scope** | Foundry resource (account) | Project |
| **Who manages** | IT Admin / Account Owner | Developer / AI User |
| **Operations** | Create projects, deploy models, configure networking, manage connections, set RBAC | Build agents, run evaluations, upload files, configure traces |
| **Security** | Azure AI Account Owner / Owner | Azure AI User |
| **Endpoint** | `https://<account>.services.ai.azure.com` | `https://<account>.services.ai.azure.com/api/projects/<project>` |

---

## 3. Data Storage Architecture

### Managed Storage (Default)

When you create a Foundry resource with default settings:
- **Project files** stored in Microsoft-managed storage
- **Agent state** (threads, messages, vector stores) stored in Microsoft-managed Cosmos DB
- No external storage account visible in your subscription

### Bring Your Own Storage (BYOS)

For enterprise compliance or data sovereignty:
- **Azure Blob Storage** → project files, evaluation datasets
- **Azure Cosmos DB** → agent state (threads, messages, run history)
- **Azure AI Search** → vector stores for file search tool
- **Azure Key Vault** → customer-managed keys (CMK)

> See [02-bring-your-own-resources.md](02-bring-your-own-resources.md) for detailed BYOS configuration.

### Encryption

| Layer | Default | Optional |
|-------|---------|----------|
| At rest | Microsoft-managed keys (MMK) | Customer-managed keys (CMK) via Key Vault |
| In transit | TLS 1.2+ | Always on |

📖 **Reference:** [Customer-managed keys](https://learn.microsoft.com/azure/ai-services/encryption/cognitive-services-encryption-keys-portal)

---

## 4. Identity & Access Model

### Managed Identities

Each Foundry project has a **system-assigned managed identity** that:
- Accesses model deployments on the parent account
- Connects to storage, AI Search, Cosmos DB
- Requires **Azure AI User** role on the Foundry resource

### User Authentication

| Method | Use Case |
|--------|----------|
| **Entra ID token** | Production — granular RBAC, audit trail |
| **API key** | Quick prototyping — bypasses RBAC |
| **Managed Identity** | App-to-app — passwordless, auto-rotated |

---

## 5. Migration from Hub-Based to Foundry V2

### Why Migrate?

New features are built for V2 first:
- Native agents framework
- Agent Monitoring Dashboard
- Continuous evaluation
- Guardrails with intervention points
- Improved RBAC model
- Simplified resource management

### Migration Options

| Option | Description | Effort |
|--------|------------|--------|
| **New project on V2** | Create fresh Foundry resource + project. Re-deploy models and connections. | Low–Medium |
| **Gradual transition** | Keep classic hub for existing workloads, use V2 for new agent projects. | Low |
| **Full migration** | Move all workloads to V2. Requires re-creating projects and re-deploying models. | Medium–High |

### Migration Steps (New Project on V2)

1. **Create Foundry resource** at [ai.azure.com](https://ai.azure.com) with "New Foundry" toggle ON
2. **Deploy models** at the account level (same models, same regions)
3. **Create project** as a child of the Foundry resource
4. **Configure connections** (AI Search, Storage, etc.)
5. **Recreate agents** in the new project (agent definitions, system prompts, tools)
6. **Set up monitoring** — connect Application Insights
7. **Update application code** — change endpoints to new project endpoint format

> **Note:** There is no automated migration tool yet. Plan for manual recreation of agents and connections.

📖 **Reference:** [Create a Foundry resource](https://learn.microsoft.com/azure/foundry/how-to/create-foundry-resource)

---

## 6. Key Endpoints & SDKs

### Endpoint Format

```
# Account-level (control plane)
https://<account-name>.services.ai.azure.com

# Project-level (data plane)
https://<account-name>.services.ai.azure.com/api/projects/<project-name>
```

### SDK Support

| SDK | Package | Supports V2 |
|-----|---------|:-----------:|
| Python | `azure-ai-projects` | ✔ |
| Python | `azure-ai-agents` | ✔ |
| .NET | `Azure.AI.Projects` | ✔ |
| JavaScript | `@azure/ai-projects` | ✔ |
| REST | Direct API calls | ✔ |

### Environment Variable Pattern

```bash
# Single endpoint — SDK resolves project automatically
PROJECT_ENDPOINT=https://<account>.services.ai.azure.com/api/projects/<project>
```

```python
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

client = AIProjectClient(
    endpoint=os.environ["PROJECT_ENDPOINT"],
    credential=DefaultAzureCredential(),
)
```

---

## 7. Capacity & Limits

| Resource | Limit |
|----------|-------|
| Projects per Foundry resource | 100 |
| Model deployments per account | Varies by model (check quota) |
| Agents per project | 10,000 |
| Threads per project | 10,000 |
| Files per agent vector store | 10,000 |
| Max file size (agent upload) | 512 MB |

📖 **Reference:** [Azure AI services quotas and limits](https://learn.microsoft.com/azure/ai-services/service-quotas-limits)

---

## Talking Points for Q&A

1. **"Why did Microsoft change from hubs?"** → Simplification. Hubs required multiple dependent resources (Storage, Key Vault, etc.). V2 bundles everything into a single Foundry resource with optional BYOS.

2. **"Is our classic Azure AI Studio hub still supported?"** → Yes, classic hubs continue to work. But new features (native agents, monitoring dashboard, guardrails) are V2-first.

3. **"What's the ARM resource type?"** → `Microsoft.CognitiveServices/accounts` with kind `AIServices`. It's the same provider as Azure AI Services — Foundry extends it.

4. **"Can we use Terraform/Bicep?"** → Yes. Use the `Microsoft.CognitiveServices/accounts` resource type. Projects are child resources (`Microsoft.CognitiveServices/accounts/projects`).

5. **"How do model deployments work?"** → Deployed at the account level, shared across all projects. This means you deploy GPT-4o once and all projects can use it.

6. **"What if we have multiple teams?"** → Create separate projects under the same Foundry resource. RBAC scopes to individual projects — Team A can't see Team B's agents.

7. **"Is there a size limit?"** → 100 projects per account, 10K agents per project. For most organisations this is more than sufficient.

---

## Portal Walkthrough (10 min)

1. Open [ai.azure.com](https://ai.azure.com) → ensure **"New Foundry"** toggle is ON
2. Show Foundry resource overview → model deployments (account level)
3. Navigate into a project → show agents, evaluations, traces (project level)
4. Show **Admin** → demonstrate the account vs. project scope
5. Show **Connections** at account level → explain shared connections
6. (Optional) Azure Portal → show the `Microsoft.CognitiveServices/accounts` resource and child project resources
