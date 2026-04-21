# Governance, Security & Responsible AI in Microsoft Foundry V2

> **Workshop coverage:** Module 1 briefly mentions RBAC and Responsible AI. Module 2 covers content safety at a high level in system prompts. This document provides the deep-dive on enterprise governance, RBAC, content safety, guardrails, Defender integration, and compliance.

---

## Quick Answer Summary

| Question | Short Answer |
|----------|-------------|
| What RBAC roles do we need? | **Azure AI User** for developers, **Azure AI Account Owner** for admins, **Azure AI Project Manager** for team leads. |
| How do content filters work? | Default guardrails filter Hate, Violence, Sexual, Self-Harm at Medium severity. Prompt Shields detect jailbreak and document attacks. All configurable. |
| Is there a security baseline? | Yes — [Azure security baseline for Foundry](https://learn.microsoft.com/security/benchmark/azure/baselines/azure-ai-foundry-security-baseline). |
| What about DLP / data leakage? | Combine Foundry guardrails with **Microsoft Purview DLP** policies for sensitive data protection. |
| Can we red-team our agents? | Yes — **AI Red Teaming Agent** scans for safety and security issues before deployment. |

---

## 1. Role-Based Access Control (RBAC)

### Foundry V2 Scope Hierarchy

```
Subscription
  └── Resource Group
        └── Foundry Resource (Account)     ← Control plane: networking, security, model deployments
              └── Foundry Project           ← Data plane: agents, evaluations, files
```

### Built-in Roles

| Role | Create Projects | Create Accounts | Build in Project (Data Plane) | Assign Roles | Reader Access | Manage Models |
|------|:-:|:-:|:-:|:-:|:-:|:-:|
| **Azure AI User** | | | ✔ | | ✔ | |
| **Azure AI Project Manager** | | | ✔ | ✔ (AI User only) | ✔ | |
| **Azure AI Account Owner** | ✔ | ✔ | | ✔ (AI User only) | ✔ | ✔ |
| **Azure AI Owner** | ✔ | ✔ | ✔ | | ✔ | ✔ |
| Azure **Owner** | ✔ | ✔ | | ✔ (any role) | ✔ | ✔ |
| Azure **Contributor** | ✔ | ✔ | | | ✔ | ✔ |
| Azure **Reader** | | | | | ✔ | |

### Enterprise RBAC Pattern

| Persona | Role | Scope | Purpose |
|---------|------|-------|---------|
| IT Admin | Owner | Subscription | Set up resource, assign Account Owners |
| Manager | Azure AI Account Owner | Foundry Resource | Deploy models, manage connections, create projects |
| Team Lead | Azure AI Project Manager | Foundry Resource | Create projects, assign AI User to team members |
| Developer | Azure AI User | Project + Reader on Resource | Build agents, run evaluations |
| Observer | Azure AI User + Azure Monitor Reader | Project + App Insights | View traces and monitoring dashboards |

### Minimum Role Assignments to Get Started
1. Assign **Azure AI User** on the Foundry resource to the **user principal**
2. Assign **Azure AI User** on the Foundry resource to the **project's managed identity**

> If the user who created the project has the Azure Owner role, both assignments are added automatically.

📖 **Reference:** [RBAC for Microsoft Foundry](https://learn.microsoft.com/azure/foundry/concepts/rbac-foundry)

### Authentication

| Method | Recommendation |
|--------|---------------|
| **Microsoft Entra ID** | ✅ Recommended — granular RBAC, managed identities |
| **API Key** | ⚠️ Grants full access, no role restrictions |

📖 **Reference:** [Authentication and Authorization in Foundry](https://learn.microsoft.com/azure/foundry/concepts/authentication-authorization-foundry)

---

## 2. Guardrails & Content Safety

### Default Safety Policies

All Azure OpenAI model deployments (except Whisper) have default guardrails:

| Risk Category | Applied To | Default Severity |
|--------------|-----------|-----------------|
| Hate and Fairness | Prompts + Completions | Medium |
| Violence | Prompts + Completions | Medium |
| Sexual | Prompts + Completions | Medium |
| Self-Harm | Prompts + Completions | Medium |
| Jailbreak (Prompt Injection) | Prompts | Enabled |
| Protected Material — Text | Completions | Enabled |
| Protected Material — Code | Completions | Enabled |

📖 **Reference:** [Default guardrail policies for Azure OpenAI](https://learn.microsoft.com/azure/foundry/openai/concepts/default-safety-policies)

### Guardrails Architecture

Guardrails are collections of **controls**, each defining:
- A **risk** to detect
- **Intervention points** to scan
- A **response action** when risk is detected

#### Four Intervention Points

```
User Input ──→ [ Agent ] ──→ Tool Call ──→ [ Tool ] ──→ Tool Response ──→ [ Agent ] ──→ Output
     ↑                           ↑                            ↑                          ↑
  Scan 1                      Scan 2                       Scan 3                     Scan 4
  (User Input)              (Tool Call)                (Tool Response)              (Output)
                           ⚠️ Preview                   ⚠️ Preview
```

📖 **Reference:** [Guardrails and controls overview](https://learn.microsoft.com/azure/foundry/guardrails/guardrails-overview)

### Prompt Shields

Protects against two types of attacks:

| Type | Attacker | Entry Point | Method |
|------|---------|-------------|--------|
| **User Prompt Attacks** | User | User prompts | Attempts to bypass system instructions or RLHF training |
| **Document Attacks** | Third party | Documents, emails, web pages | Hidden instructions embedded in content |

Prompt Shields are part of the guardrails system. Enable them when configuring guardrail controls.

Example API response:
```json
{
  "prompt_filter_results": [{
    "content_filter_results": {
      "jailbreak": { "filtered": false, "detected": true }
    }
  }]
}
```

📖 **Reference:** [Prompt Shields in Foundry](https://learn.microsoft.com/azure/foundry/openai/concepts/content-filter-prompt-shields)

### Configuring Custom Content Filters

1. Foundry portal → **Guardrails + controls** → **Content filters**
2. **+ Create content filter** → name it, associate with a connection
3. Configure **input filters** (user prompts) and **output filters** (model completions)
4. Adjust severity thresholds per category
5. Enable/disable Prompt Shields, protected material detection

---

## 3. Microsoft Defender for Cloud Integration

### Security Alerts in Foundry

Foundry integrates with **Defender for Foundry Tools** plan:

1. Foundry portal → project → **Risks + alerts** (left navigation)
2. Review active alerts and recommendations
3. Select an alert for details and remediation steps

### What Defender Detects
- Jailbreak attempts and user input attacks
- Misconfigurations (security posture recommendations)
- Unusual model usage patterns
- Threats to AI workloads

📖 **Reference:** [Alerts for AI workloads](https://learn.microsoft.com/azure/defender-for-cloud/alerts-ai-workloads)

---

## 4. Microsoft Purview Integration

### Data Governance for AI

| Capability | Description |
|-----------|-------------|
| **Auditing** | Track all interactions with Foundry resources |
| **SIT Classification** | Sensitive Information Type detection in prompts/responses |
| **DSPM for AI** | Data Security Posture Management — visibility over AI data flows |
| **DLP Policies** | Prevent sensitive data leakage via AI agent interactions |

> **Note:** Purview Data Security Policies require Microsoft Entra ID user-context tokens.

📖 **Reference:** [Manage compliance and security in Foundry](https://learn.microsoft.com/azure/foundry/control-plane/how-to/how-to-manage-compliance-security)

---

## 5. Responsible AI Framework

Microsoft's approach follows **Discover → Protect → Govern**:

### Discover
- Test agents with adversarial prompts before deployment
- Use the **AI Red Teaming Agent** to scan for vulnerabilities
- Run batch evaluations with safety evaluators
- Use [AI Red Teaming Playground Labs](https://github.com/microsoft/AI-Red-Teaming-Playground-Labs)

### Protect
- Apply content filters and guardrails at the model layer
- Enable Prompt Shields for jailbreak/document attack protection
- Configure custom content filters for domain-specific risks
- Use system prompts to define agent boundaries

### Govern
- Set up **continuous monitoring** via Agent Monitoring Dashboard
- Enable **continuous evaluation** for production traffic
- Generate **AI Reports** documenting model cards, filter configs, and evaluation metrics (exportable as PDF or SPDX)
- Use Defender for Cloud for security posture and threat detection

📖 **Reference:** [Responsible AI for Microsoft Foundry](https://learn.microsoft.com/azure/foundry/responsible-use-of-ai-overview)

### AI Reports for Compliance

AI Reports in Foundry help document project details for GRC workflows:
- Model cards and versions
- Content safety filter configurations
- Evaluation metrics
- Exportable as **PDF** or **SPDX** format

📖 **Reference:** [AI Reports blog](https://techcommunity.microsoft.com/blog/aiplatformblog/ai-reports-improve-ai-governance-and-genaiops-with-consistent-documentation/4301914)

---

## 6. Data Access Security Standards

When connecting agents to data, Foundry supports three approved access paths:

| Access Path | Security Model | Best For |
|------------|---------------|----------|
| **Foundry IQ** (Knowledge Bases) | Azure AI Search with sensitivity labels/ACLs | Consistent access enforcement across agents |
| **Fabric Data Agents** | Fabric's fine-grained security | High-value/sensitive organisational data |
| **Direct Connections** (MCP, APIs) | Per-connection auth (OAuth, keys) | Real-time data queries |

📖 **Reference:** [Data security standards for AI — Foundry](https://learn.microsoft.com/azure/cloud-adoption-framework/data/operational-standards-data-product-security-standards-unify-data-platform#microsoft-foundry-security-standard)

---

## Talking Points for Q&A

1. **"What's the minimum we need to set up for security?"** → Assign Azure AI User to developers, use Entra ID auth (not API keys), keep default content filters ON. This gives you baseline security with zero extra config.

2. **"Can we make content filters stricter?"** → Yes. Create a custom content filter with lower severity thresholds. You can also add custom blocklists for domain-specific terms.

3. **"What about prompt injection?"** → Prompt Shields are enabled by default. They detect both direct (user) and indirect (document) injection attacks. You can also scan at tool call and tool response intervention points (preview).

4. **"How do we handle compliance for regulated industries?"** → Use AI Reports for documentation. Integrate with Purview for DLP and data classification. Enable Defender for Cloud for security posture monitoring.

5. **"Can different teams have different levels of access?"** → Yes. RBAC supports scoping at both Foundry resource and project levels. Use the enterprise RBAC pattern: Account Owner for admins, Project Manager for leads, AI User for developers.

6. **"What if someone tries to jailbreak the agent?"** → Three layers of protection: (1) Prompt Shields detect the attempt, (2) content filters block harmful output, (3) Defender for Cloud alerts on the incident.

7. **"Can we audit all agent interactions?"** → Yes. Tracing captures all interactions in Application Insights. Purview provides additional auditing and SIT classification.

---

## Portal Walkthrough (10 min)

1. Foundry portal → **Guardrails + controls** → show default content filters
2. Show how to create a custom content filter with stricter thresholds
3. Show **Prompt Shields** → try a test jailbreak prompt
4. Navigate to **Risks + alerts** → show Defender integration
5. Show **Admin** page → demonstrate role assignment
6. (Optional) Azure Portal → Foundry resource → **Access control (IAM)** → show role assignments
