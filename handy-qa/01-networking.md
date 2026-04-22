# Networking & Network Isolation in Microsoft Foundry V2

> **Workshop coverage:** The workshop uses default public networking for simplicity. This document covers enterprise-grade network isolation for production deployments.

---

## Quick Answer Summary

| Question | Short Answer |
|----------|-------------|
| Can we run Foundry agents inside our VNet? | Yes — via **VNet injection** (BYO VNet) or **Managed Virtual Network** (preview). |
| Does Foundry support private endpoints? | Yes — both inbound (to the Foundry resource) and outbound (from agents to dependent services). |
| Can we block all public internet access? | Yes — set Public Network Access to **Disabled** and use private endpoints. |
| What about the Databricks MCP connection? | Databricks supports private endpoints from the managed VNet. Private link to Databricks is available. |

---

## Three Areas of Network Isolation

Microsoft Foundry considers network isolation in three areas:

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│   1. INBOUND ACCESS                                                │
│      User/App → Foundry Resource                                   │
│      (Private Endpoint + PNA flag)                                 │
│                                                                     │
│   2. OUTBOUND ACCESS (PaaS)                                        │
│      Foundry Resource → Storage, Key Vault, AI Search, Cosmos DB   │
│      (Private Link to dependent services)                          │
│                                                                     │
│   3. OUTBOUND ACCESS (Agent Client)                                │
│      Agent runtime → Data sources, APIs, internet                  │
│      (VNet Injection OR Managed Virtual Network)                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

📖 **Reference:** [Plan for network isolation in Foundry](https://learn.microsoft.com/azure/foundry/how-to/configure-private-link)

---

## Option A: Custom Virtual Network (BYO VNet) — GA

Use your own VNet and subnet for full control over network topology.

### Requirements
- Public Network Access set to **Disabled**
- Private endpoint created to the Foundry resource
- **Bring Your Own Resources** (Storage, AI Search, Cosmos DB) — required for VNet injection
- Subnet delegated to `Microsoft.App/environments` with size `/27` or larger
- Private endpoints created separately to Storage, AI Search, and Cosmos DB

### Setup Steps (Portal)
1. Create Foundry resource → **Storage** tab → Select **your own** Storage, AI Search, Cosmos DB
2. **Networking** tab → Set Public Access to **Disabled**
3. Add **Private Endpoint** (same region as VNet)
4. Set **Virtual Network Injection** → select your VNet and delegated subnet
5. Create private endpoints to dependent services (Storage, Search, Cosmos DB) in their respective resource pages

### Architecture Diagram
```
┌──────────────┐     Private Endpoint     ┌─────────────────────┐
│  User / App  │ ──────────────────────── │  Foundry Resource   │
│  (On-Prem /  │     (Inbound)           │                     │
│   VPN/ER)    │                          │  ┌───────────────┐  │
└──────────────┘                          │  │ Agent Client   │  │
                                          │  │ (VNet Injected)│  │
                                          │  └───────┬───────┘  │
                                          └──────────┼──────────┘
                                                     │ Private Endpoints
                              ┌───────────────┬──────┴──────┬────────────┐
                              ▼               ▼             ▼            ▼
                         ┌─────────┐   ┌──────────┐  ┌──────────┐ ┌──────────┐
                         │ Storage │   │ Cosmos DB│  │ AI Search│ │Databricks│
                         └─────────┘   └──────────┘  └──────────┘ └──────────┘
```

📖 **Reference:** [Configure network isolation for Foundry — Outbound](https://learn.microsoft.com/azure/foundry/how-to/configure-private-link#set-up-walkthrough-for-outbound-network-isolation)

---

## Option B: Managed Virtual Network — Preview

Microsoft provisions and manages a VNet for you. Simpler setup, no subnet delegation required.

### Isolation Modes

| Mode | Description | Use When |
|------|-------------|----------|
| **Allow Internet Outbound** | All outbound traffic allowed; inbound via private endpoints | Broad connectivity acceptable |
| **Allow Only Approved Outbound** | Outbound restricted to approved destinations via service tags, private endpoints, and FQDN rules | Minimize data exfiltration risk |
| **Disabled** | No managed network (use BYO VNet or public) | Full control via custom VNet |

### Key Facts
- Deployed via **Bicep template** only (not portal UI)
- Managed private endpoints created to dependent services (Storage auto-created; Cosmos DB and AI Search require CLI)
- FQDN outbound rules support ports 80 and 443 only (via managed Azure Firewall — additional cost)
- **Cannot downgrade** isolation mode once set (e.g., can't go from `AllowOnlyApprovedOutbound` → `AllowInternetOutbound`)

### Supported Regions (as of April 2026)
East US, East US2, Japan East, France Central, UAE North, Brazil South, Spain Central, Germany West Central, Italy North, South Central US, West Central US, **Australia East**, Sweden Central, Canada East, South Africa North, West Europe, West US, West US 3, South India, UK South

### Managed Private Endpoint Targets
Azure Application Gateway, API Management, AI Search, Container Registry, Cosmos DB, Data Factory, Databricks, Event Hubs, Key Vault, Machine Learning, Redis, SQL Server, Storage, Application Insights (via Private Link scope), and Microsoft Foundry itself.

📖 **Reference:** [Configure managed virtual network for Foundry](https://learn.microsoft.com/azure/foundry/how-to/managed-virtual-network)

---

## Agent Tool Support Behind VNet

| Tool | VNet Support | Notes |
|------|-------------|-------|
| File Search | ✅ | Uses private endpoint to Storage |
| Code Interpreter | ✅ | Runs within managed compute |
| Bing Grounding | ⚠️ | Requires FQDN rule or internet outbound |
| Azure AI Search | ✅ | Private endpoint to Search resource |
| MCP Tools (e.g., Databricks) | ✅ | Private endpoint to Databricks workspace |
| Custom Function (OpenAPI) | ✅ | Must be reachable via private endpoint or FQDN rule |

📖 **Reference:** [Agent tools with network isolation](https://learn.microsoft.com/azure/foundry/how-to/configure-private-link#set-up-walkthrough-for-outbound-network-isolation)

---

## DNS Configuration

When using private endpoints, configure DNS resolution:
- **Azure Private DNS Zones** for each service (e.g., `privatelink.cognitiveservices.azure.com`)
- For on-premises access via VPN/ExpressRoute, configure DNS forwarders
- Verify with: `nslookup <your-foundry-endpoint>` → should resolve to private IP
- Test connectivity: `Test-NetConnection <private-endpoint-ip> -Port 443`

---

## Q&A

1. **"We can't use public endpoints in production."** → Foundry V2 supports full private networking via BYO VNet (GA) or Managed VNet (preview). Both options disable public access entirely.

2. **"What's the simplest path to network isolation?"** → Managed VNet is simpler but preview. BYO VNet is GA and gives full control. Both options are supported in most Azure regions.

3. **"Can we connect to on-premises resources?"** → Yes, via Application Gateway with private endpoints. Both L4 and L7 traffic supported (GA).

4. **"What about the Databricks connection?"** → Databricks is a supported private endpoint target from both managed and custom VNets. The MCP connection will work over private networking.


