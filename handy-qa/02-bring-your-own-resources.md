# Bring Your Own Resources (BYOR) in Microsoft Foundry V2

> **Workshop coverage:** The workshop uses the default "Basic" agent setup with Microsoft-managed resources. This document covers enterprise scenarios where organisations bring their own Azure resources.

---

## Quick Answer Summary

| Question | Short Answer |
|----------|-------------|
| Can we use our own Storage account? | Yes — BYOS (Bring Your Own Storage) supported for agents, evaluations, datasets, Speech, and Language. |
| Can we use our own Cosmos DB? | Yes — for agent conversation/thread storage in the Standard agent setup. |
| Can we use our own AI Search? | Yes — for agent vector stores in the Standard agent setup. |
| Can we use our own Key Vault? | Yes — one Key Vault per Foundry resource for managing connection secrets. |
| Can we use customer-managed keys (CMK)? | Yes — via your own Key Vault with FIPS 140-2 compliant 256-bit AES encryption. |
| Can we reuse existing Azure OpenAI deployments? | Yes — reuse model deployments and quota from existing Foundry Tools or Azure OpenAI resources. |

---

## Basic vs Standard Agent Setup

| Aspect | Basic (Default) | Standard (BYOR) |
|--------|----------------|-----------------|
| **Storage** | Microsoft-managed, logically separated | Your Azure Storage account |
| **Cosmos DB** | Microsoft-managed multitenant | Your Cosmos DB for NoSQL account |
| **AI Search** | Microsoft-managed | Your Azure AI Search resource |
| **Key Vault** | Microsoft-managed Key Vault | Your Azure Key Vault |
| **Network isolation** | Limited | Full — required for VNet injection |
| **CMK encryption** | Not available | Supported |
| **Data residency** | Microsoft-controlled | Customer-controlled |
| **Best for** | Prototyping, workshops | Production, regulated environments |

📖 **Reference:** [Use your own resources with Foundry Agent Service](https://learn.microsoft.com/azure/foundry/agents/how-to/use-your-own-resources)

---

## Bring Your Own Storage (BYOS)

### What Gets Stored
- Agent files (uploaded documents for File Search)
- Evaluation datasets and results
- Content Understanding outputs
- Speech and Language service data

### Prerequisites
Your Azure Storage account must have:
- `allowSharedKeyAccess` set to `true`
- `minimumTlsVersion` set to `TLS1_2`
- `allowBlobPublicAccess` set to `false`
- `allowCrossTenantReplication` set to `false`
- Contributor or Owner permissions on both Foundry resource and Storage account

### Two Connection Approaches

| Approach | Description | Use When |
|----------|-------------|----------|
| **Connections** | Shared data pointer — recommended baseline | Most features |
| **Capability Hosts** | Override/bind a specific feature to one connection | Agent standard setup, fine-grained control |

### Portal Steps
1. Sign in to [Foundry](https://ai.azure.com) → ensure **New Foundry** toggle is ON
2. Select **Build** → **Tools** → **Connect a tool**
3. In the catalog, find **Azure Blob Storage** → **Create**
4. Configure the connection to your storage account

📖 **Reference:** [Connect to your own storage](https://learn.microsoft.com/azure/foundry/how-to/bring-your-own-azure-storage-foundry)

---

## Bring Your Own Key Vault

### Why
- Full control over API key-based connection secrets
- Compliance requirements for secret management
- Customer-managed encryption keys

### Limitations
- **One Key Vault per Foundry resource** (limit)
- Foundry does **not** support secret migration — remove and recreate connections if switching
- Deleting the underlying Key Vault breaks the Foundry resource
- Required RBAC on Key Vault: `Key Vault Secrets Officer` (minimum), `Key Vault Contributor`, or `Key Vault Administrator`

### CMK (Customer-Managed Keys) Prerequisites
- Key Vault deployed in the **same region** as Foundry resource
- **Soft delete** and **purge protection** enabled
- Managed identities have `Key Vault Crypto User` role (Azure RBAC)
- Only RSA and RSA-HSM keys of size 2048 supported

📖 **Reference:** [Set up Azure Key Vault connection in Foundry](https://learn.microsoft.com/azure/foundry/how-to/set-up-key-vault-connection)

---

## Bring Your Own Cosmos DB

### Requirements
- Azure Cosmos DB for NoSQL account
- Total throughput limit of at least **3000 RU/s** (provisioned or serverless)
- Three containers provisioned, each requiring 1000 RU/s
- Must be in the **same region** as Foundry resource

### What Gets Stored
- Agent threads (conversations)
- Messages
- Run history

---

## Bring Your Own AI Search

### Requirements
- Azure AI Search resource
- Same region as Foundry resource
- Used for agent vector stores (File Search tool backend)

---

## Infrastructure as Code (Bicep)

The Azure Verified Module (AVM) for Foundry supports BYOR natively:

```bicep
module aiFoundry 'br/public:avm/ptn/ai-ml/ai-foundry:<version>' = {
  params: {
    baseName: '<basename>'
    aiFoundryConfiguration: {
      createCapabilityHosts: true
    }
    aiModelDeployments: [
      {
        model: { format: 'OpenAI', name: 'gpt-4o', version: '2024-11-20' }
        name: 'gpt-4o'
        sku: { capacity: 1, name: 'Standard' }
      }
    ]
    // Bring your own resources
    storageAccountConfiguration: {
      existingResourceId: '<your-storage-resource-id>'
    }
    cosmosDbConfiguration: {
      existingResourceId: '<your-cosmosdb-resource-id>'
    }
    aiSearchConfiguration: {
      existingResourceId: '<your-search-resource-id>'
    }
    keyVaultConfiguration: {
      existingResourceId: '<your-keyvault-resource-id>'
    }
    includeAssociatedResources: true
  }
}
```

📖 **Reference:** [AVM Bicep module — Bring Your Own Resources example](https://learn.microsoft.com/github/AvmGitHubCom/raw.githubusercontent.com/Azure/bicep-registry-modules/refs/heads/main/avm/ptn/ai-ml/ai-foundry/README.md#usage-examples)

---

## Required Resource Providers

Register these providers before deploying with BYOR:

```bash
az provider register --namespace 'Microsoft.KeyVault'
az provider register --namespace 'Microsoft.CognitiveServices'
az provider register --namespace 'Microsoft.Storage'
az provider register --namespace 'Microsoft.MachineLearningServices'
az provider register --namespace 'Microsoft.Search'
az provider register --namespace 'Microsoft.App'
az provider register --namespace 'Microsoft.ContainerService'
```

---

## Q&A

1. **"We already have Storage / Cosmos DB / Key Vault — do we have to create new ones?"** → No. Foundry V2 supports BYOR for all key dependencies. You can point Foundry to your existing resources.

2. **"Is BYOR required?"** → Only if you need network isolation (VNet injection), customer-managed keys, or full data ownership. The Basic setup works fine for prototyping.

3. **"Can we migrate from Basic to Standard later?"** → There is no direct upgrade path. You'd create a new Foundry project with Standard setup. Agents and data assets don't auto-migrate.

4. **"What about data sovereignty?"** → BYOR gives you full control over where data is stored. All resources must be in the same region as the Foundry resource.

5. **"What permissions does the person creating the Foundry resource need?"** → `Azure AI Account Owner` at subscription scope + `Role Based Access Administrator` for assigning roles to BYOR resources (or `Owner` at subscription level).

---

