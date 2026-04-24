# Fabric Mirroring: Authentication, Permissions & RLS Guide

> **Scope:** End-to-end guide for mirroring a Databricks Unity Catalog into Microsoft Fabric using a Service Principal — covering App Registration, SCIM, Databricks permissions, Fabric connection, and Row-Level Security propagation.
>
> **Context:** Contoso workshop — mirroring the `contoso` catalog from workspace `REPLACE_WITH_DATABRICKS_HOST` into Fabric.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Authentication: Org Account vs Service Principal](#2-authentication-org-account-vs-service-principal)
3. [Part A: Azure Portal — Create the App Registration](#3-part-a-azure-portal--create-the-app-registration)
4. [Part B: Databricks — Add the SP & Grant Permissions](#4-part-b-databricks--add-the-sp--grant-permissions)
5. [Where Does SCIM Come In?](#5-where-does-scim-come-in)
6. [Part C: Fabric — Create the Mirrored Catalog](#6-part-c-fabric--create-the-mirrored-catalog)
7. [RLS: Does It Propagate? (No — Here's What To Do)](#7-rls-does-it-propagate)
8. [Part D: Fabric — Secure the Mirrored Data](#8-part-d-fabric--secure-the-mirrored-data)
9. [Part E: Fabric Data Agent — Permissions & RLS Behaviour](#9-part-e-fabric-data-agent--permissions--rls-behaviour)
10. [Quick Reference](#10-quick-reference)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Azure Portal (Entra ID)                                                │
│  ┌──────────────────────────┐                                           │
│  │  App Registration        │──── Client ID + Secret ──────────┐        │
│  │  (Service Principal)     │                                  │        │
│  │                          │                                  │        │
│  │  API Permission:         │                                  │        │
│  │  AzureDatabricks ────────│──── OAuth token grant ──┐        │        │
│  │  user_impersonation      │                         │        │        │
│  │  + Admin Consent ✅      │                         │        │        │
│  └──────────┬───────────────┘                         │        │        │
│             │                                         │        │        │
│   Entra ID Groups                                     │        │        │
│   ┌─────────────────────┐                             │        │        │
│   │ Group-A             │──── SCIM sync ──┐           │        │        │
│   │ Group-B             │                 │           │        │        │
│   │ Group-C             │                 │           │        │        │
│   │ Group-Executives    │                 │           │        │        │
│   └─────────────────────┘                 │           │        │        │
└───────────────────────────────────────────┼───────────┼────────┼────────┘
                                            │           │        │
                    ┌───────────────────────┼───────────┼────────┼────────┐
                    │  Azure Databricks     │           │        │        │
                    │                       ▼           ▼        ▼        │
                    │  Account Console:  Groups synced  Token  SP added   │
                    │       │                           works    │        │
                    │       ▼                                    ▼        │
                    │  Unity Catalog:   Row Filters        GRANT SELECT  │
                    │  (contoso catalog)  use groups          + EXTERNAL   │
                    │       │            for RLS             USE SCHEMA  │
                    │       │                                    │        │
                    │       ▼                                    │        │
                    │  Delta Lake files (ADLS Gen2)              │        │
                    └───────────────────────┬────────────────────┘        │
                                            │                             
                                            │ direct file read            
                                            │ (metadata shortcuts)        
                    ┌───────────────────────▼─────────────────────────────┐
                    │  Microsoft Fabric                                    │
                    │                                                      │
                    │  ⚙️ Manage Connections (pre-create — recommended)   │
                    │       │                                              │
                    │       ▼                                              │
                    │  Mirrored Catalog ──► SQL Analytics Endpoint         │
                    │       │                    │                          │
                    │       │              Fabric RLS Policies              │
                    │       │              (must redefine here!)            │
                    │       │                    │                          │
                    │       ▼                    ▼                          │
                    │  Fabric Data Agent    Power BI (Direct Lake)         │
                    │  (NL-to-SQL)          (dashboards)                   │
                    │       │                                              │
                    │  End users query ──► RLS enforced per Entra group    │
                    └──────────────────────────────────────────────────────┘
```

**Key points visible in the diagram:**
- The **Service Principal** is used to establish the mirror connection (not a user account)
- **Entra ID groups** are synced to Databricks via SCIM (for Databricks RLS) — and the **same groups** are referenced in Fabric RLS
- **Databricks RLS does NOT flow through** to Fabric — you must redefine it

---

## 2. Authentication: Org Account vs Service Principal

When Fabric creates a mirrored catalog, it needs credentials to connect to Databricks. Two options exist:

### Organisational Account (Entra ID User Login)

| Aspect | Detail |
|--------|--------|
| **What it is** | Your personal login (e.g. `sajit@contoso.com`) |
| **How it authenticates** | OAuth interactive flow — Fabric gets a token as *you* |
| **Works for mirroring?** | ❌ Unreliable — MFA / Conditional Access blocks the non-interactive token refresh that mirroring needs for continuous sync |
| **Common error** | `"Invalid credentials"` — caused by MFA challenge that can't be completed silently |
| **When to use** | Quick dev/test only, on tenants with no MFA/Conditional Access |
| **Production risk** | Breaks on: password change, MFA re-prompt, user leaves org, CA policy update |

### Service Principal (App Registration) ✅ Recommended

| Aspect | Detail |
|--------|--------|
| **What it is** | An Entra ID App Registration — a non-human identity with client ID + secret |
| **How it authenticates** | Client credentials flow — no human interaction, no MFA |
| **Works for mirroring?** | ✅ Yes — persistent, automated, no interactive prompts |
| **When to use** | Always for production; recommended for any environment |
| **Key requirement** | Must be added to Databricks Account Console + granted Unity Catalog permissions |
| **Maintenance** | Rotate client secret before expiry (set a calendar reminder) |

### Why the "Invalid Credentials" Error Happens with Org Account

```
Org Account flow (breaks):
  Fabric → "I need a new token" → Entra ID → "Complete MFA" → 💥 No browser to complete MFA

Service Principal flow (works):
  Fabric → "I need a new token" → Entra ID → "Here's a token" (no MFA for SPs) → ✅
```

Fabric mirroring runs as a **background service** — it periodically refreshes its connection to Databricks to sync metadata changes. With an Org Account, the OAuth refresh token eventually expires or hits a Conditional Access policy that requires MFA. Since there's no browser session to complete MFA, the connection fails silently with "Invalid credentials."

---

## 3. Part A: Azure Portal — Create the App Registration

> **Where:** [https://portal.azure.com](https://portal.azure.com) → Microsoft Entra ID

### Step A1 — Register a New Application

1. Sign in to the **Azure Portal**
2. Search for **"Microsoft Entra ID"** → click it
3. Left sidebar → **"App registrations"** → **"+ New registration"**

   | Field | Value |
   |-------|-------|
   | **Name** | `fabric-databricks-mirror-contoso-dev` |
   | **Supported account types** | Accounts in this organizational directory only (Single tenant) |
   | **Redirect URI** | Leave blank |

4. Click **"Register"**

### Step A2 — Copy the IDs

From the app's **Overview** page, copy and save:

| Value | Where | Your Value |
|-------|-------|------------|
| **Application (client) ID** | Overview page | `REPLACE_WITH_RESOURCE_ID` |
| **Directory (tenant) ID** | Overview page | `REPLACE_WITH_RESOURCE_ID` |
| **Object ID** | Overview page | `REPLACE_WITH_RESOURCE_ID` |

### Step A3 — Create a Client Secret

1. Left sidebar → **"Certificates & secrets"** → **"Client secrets"** tab
2. Click **"+ New client secret"**

   | Field | Value |
   |-------|-------|
   | Description | `fabric-mirror-secret` |
   | Expires | 12 months (set a calendar reminder to rotate!) |

3. Click **"Add"**
4. **⚠️ Copy the "Value" column immediately** — it disappears after you leave this page

> **You now have 3 values needed for Fabric:** Client ID, Tenant ID, Client Secret

### Step A4 — Add Azure Databricks API Permission

> **⚠️ This step is critical.** Without it, the SP cannot obtain an OAuth token for the Databricks resource, and Fabric will return **"Invalid connection credentials"** (HTTP 400).

1. Still in the App Registration, left sidebar → **"API permissions"**
2. Click **"+ Add a permission"**
3. Select the **"APIs my organization uses"** tab
4. Search for **"AzureDatabricks"** (Application ID: `REPLACE_WITH_RESOURCE_ID`)
5. Select it → choose **"Delegated permissions"**
6. Check **`user_impersonation`** → click **"Add permissions"**
7. Back on the API permissions page, click **"Grant admin consent for [your tenant]"** → confirm **"Yes"**

After granting, the Status column should show a **green checkmark** with "Granted for [tenant]".

> **Why is this needed?** When Fabric connects to Databricks using the SP, it requests an OAuth token from Entra ID for the Azure Databricks resource. Without this API permission + admin consent, Entra ID refuses to issue the token, causing the 400 error *before* the request ever reaches Databricks.

| If you see... | It means... |
|---------------|-------------|
| "AzureDatabricks" not found in search | Switch to **"APIs my organization uses"** tab (not "Microsoft APIs") |
| "Insufficient privileges to complete the operation" when granting consent | You need **Global Administrator** or **Cloud Application Administrator** role to grant admin consent. Ask your Entra admin. |
| Status shows "Not granted" (orange ⚠️) | Admin consent hasn't been granted yet — the SP won't work until a tenant admin clicks "Grant admin consent" |

---

## 4. Part B: Databricks — Add the SP & Grant Permissions

> **Where:** Databricks Account Console + Workspace SQL Editor

### Why the Workspace "Add SP" Button Is Greyed Out

Your Databricks deployment uses **account-level identity management** (the modern default for enterprise). This means:
- Service principals must be registered at the **Account Console** first
- The workspace-level "Add service principal" is intentionally greyed out to prevent conflicts
- After adding at account level, you assign the SP to specific workspaces

### Step B1 — Add SP at the Account Console

1. Go to: [https://accounts.azuredatabricks.net](https://accounts.azuredatabricks.net)
   - Sign in with an **Account Admin** identity
2. Left sidebar → **"User management"** → **"Service principals"** tab
3. Click **"+ Add service principal"**
4. Select **"Microsoft Entra ID managed"**

   | Field | Value |
   |-------|-------|
   | **Name** | `fabric-databricks-mirror-contoso-dev` |
   | **Microsoft Entra application ID** | `REPLACE_WITH_RESOURCE_ID` |

5. Click **"Add"**

### Step B2 — Assign SP to the Workspace

Still in the **Account Console**:

1. Left sidebar → **"Workspaces"**
2. Click on your workspace (`adb-7405614861019645`)
3. **"Permissions"** tab → **"Add permissions"**
4. Search for `fabric-databricks-mirror-contoso-dev`
5. Set role: **"User"**
6. Click **"Save"**

### Step B3 — Enable External Data Access on the Metastore

> **⚠️ Without this, Fabric mirroring fails with:** *"Unable to process response from Databricks. The API returned data in an unexpected format"*

Fabric reads Delta Lake files directly from ADLS storage — not through the SQL Warehouse. Databricks must explicitly allow this via the **UI** (there is no SQL command for this).

1. In the Databricks workspace, click **"Catalog"** in the left sidebar
2. Click the **gear icon** (⚙️) at the top
3. Click **"Metastore"** → select the **"Details"** tab
4. Find **"External data access"** and toggle it **ON**
5. Click **Save**

> **Not a metastore admin?** Only metastore admins can toggle this. Check who the admin is in the Databricks Account Console → **Data** → **Metastore** → **Admins**. Ask them to enable it.
>
> **How to verify:** After enabling, you can confirm in a SQL Editor:
> ```sql
> DESCRIBE METASTORE;
> -- Look for 'external_data_access_enabled = true' in the output
> ```

### Step B4 — Grant Unity Catalog Permissions

In the Databricks workspace → **SQL Editor**, run these statements one at a time:

```sql
-- Standard catalog access
GRANT USE CATALOG ON CATALOG contoso TO `REPLACE_WITH_RESOURCE_ID`;
GRANT USE SCHEMA ON CATALOG contoso TO `REPLACE_WITH_RESOURCE_ID`;
GRANT SELECT ON CATALOG contoso TO `REPLACE_WITH_RESOURCE_ID`;
```

```sql
-- ⚠️ CRITICAL FOR FABRIC MIRRORING — most people miss this!
-- EXTERNAL USE SCHEMA allows Fabric to read Delta files directly from ADLS
GRANT EXTERNAL USE SCHEMA ON SCHEMA contoso.projects TO `REPLACE_WITH_RESOURCE_ID`;
GRANT EXTERNAL USE SCHEMA ON SCHEMA contoso.equipment TO `REPLACE_WITH_RESOURCE_ID`;
GRANT EXTERNAL USE SCHEMA ON SCHEMA contoso.safety TO `REPLACE_WITH_RESOURCE_ID`;
GRANT EXTERNAL USE SCHEMA ON SCHEMA contoso.procurement TO `REPLACE_WITH_RESOURCE_ID`;
```

#### Why Two Types of Permissions?

| Permission | What It Allows | Needed For |
|-----------|---------------|------------|
| `USE CATALOG` | Navigate the catalog | Both Genie MCP + Fabric mirroring |
| `USE SCHEMA` | Navigate schemas | Both |
| `SELECT` | Query tables **through a SQL Warehouse** | Genie MCP queries, direct SQL |
| `EXTERNAL USE SCHEMA` | Read Delta files **directly from storage** (ADLS) | **Fabric mirroring only** — this is the one that causes "unexpected format" errors when missing |

**Verify grants:**
```sql
SHOW GRANTS ON CATALOG contoso;
SHOW GRANTS ON SCHEMA contoso.projects;
-- Should show: USE CATALOG, USE SCHEMA, SELECT, EXTERNAL USE SCHEMA
```

---

## 5. Where Does SCIM Come In?

SCIM (System for Cross-domain Identity Management) syncs **users and groups** from Entra ID to Databricks. Here's how it relates to this setup:

### What SCIM Does

```
Microsoft Entra ID                    Databricks Account Console
─────────────────                     ──────────────────────────
Users:                        ──►     Users (auto-synced)
  alice@contoso.com          SCIM      alice@contoso.com
  bob@contoso.com                      bob@contoso.com

Groups:                       ──►     Groups (auto-synced)
  Group-A                     SCIM      Group-A
  Group-B                               Group-B
  Group-C                               Group-C
```

### What SCIM Does NOT Do

| Thing | Handled by SCIM? | How to do it instead |
|-------|:-:|---|
| Sync users & groups to Databricks | ✅ Yes | Automatic via SCIM provisioning app |
| Add **service principals** to Databricks | ❌ No | Manual — Account Console (Step B1) |
| Grant Unity Catalog permissions | ❌ No | Manual — SQL `GRANT` statements (Step B4) |
| Set up Fabric mirroring connection | ❌ No | Manual — Fabric portal (Part C) |
| Create Fabric RLS policies | ❌ No | Manual — Fabric SQL (Part D) |

### Why SCIM Matters for This Setup

SCIM is **not involved** in the Service Principal or Fabric mirroring connection at all. But it **is involved** in making RLS work:

1. **Databricks RLS** (Genie MCP path): Unity Catalog row filters use `IS_ACCOUNT_GROUP_MEMBER('Group-A')`. For this to work, the Entra group `Group-A` must exist in Databricks → that's what SCIM syncs.

2. **Fabric RLS** (mirroring path): Fabric's `IS_MEMBER('Group-A')` checks group membership directly against Entra ID — no SCIM needed on the Fabric side. Fabric is an Entra-native service.

### SCIM Summary for This Setup

| Component | Uses SCIM? | Why |
|-----------|:-:|---|
| Service Principal → Databricks | ❌ | SPs are added manually at Account Console |
| Fabric → Databricks connection | ❌ | Uses SP client credentials, not SCIM |
| Databricks RLS (row filters) | ✅ | Groups must be synced for `IS_ACCOUNT_GROUP_MEMBER()` |
| Fabric RLS (security policies) | ❌ | `IS_MEMBER()` checks Entra ID directly |
| End users accessing Fabric Data Agent | ❌ | Users sign in with Entra ID natively |

---

## 6. Part C: Fabric — Create the Mirrored Catalog

> **Where:** [https://app.fabric.microsoft.com](https://app.fabric.microsoft.com)

### Step C0 — Enable Service Principals in Fabric Tenant Settings

> **⚠️ Without this step, ALL SP-based operations in Fabric will fail with `PowerBINotAuthorizedException`.**

This is a **one-time tenant admin setting**. If you're not a Fabric/Power BI admin, ask your admin to do this.

1. Go to [https://app.fabric.microsoft.com](https://app.fabric.microsoft.com) → **⚙️ Settings** (gear icon) → **Admin portal**
2. Left sidebar → **"Tenant settings"**
3. Enable **all three** of these settings (under "Developer settings"):

   | Setting | Purpose |
   |---------|---------|
   | **"Service principals can create workspaces, connections, and deployment pipelines"** | Allows SP to create the Databricks connection |
   | **"Service principals can call Fabric public APIs"** | Allows SP to call Fabric REST APIs (mirroring, catalog operations) |
   | **"Allow service principals to create and use profiles"** | Allows SP to create and use profiles for Fabric items |

4. For each setting, choose scope:
   - **"The entire organization"** — allows all SPs (simpler for dev/workshop)
   - **"Specific security groups"** — add a security group that contains your SP (more secure for production)
5. Click **"Apply"** on each

| If you see... | It means... |
|---------------|-------------|
| "Admin portal" not visible in Settings | You're not a Fabric Admin. Ask your tenant admin (Power BI Service Administrator or Fabric Administrator Entra role). |
| Setting is enabled but still getting the error | The SP may not be in the allowed security group. Either switch to "The entire organization" or add the SP to the specified group. |
| Setting was just changed | Changes can take **up to 15 minutes** to propagate. Wait and retry. |

### Step C1 — Create the Databricks Workspace Connection

There are **two ways** to create the connection. The **recommended approach** (Option A) is to pre-create it centrally — this avoids credential validation issues that sometimes occur with inline creation.

#### Option A: Pre-Create via Manage Connections (Recommended) ✅

This approach creates the connection **before** setting up the mirrored catalog. It's more reliable and the connection can be reused across multiple Fabric items.

1. In Fabric, click **⚙️ Settings** (gear icon, top-right) → **"Manage connections and gateways"**
2. Click **"+ New"** → **"Cloud"**
3. Fill in the connection details:

   | Field | Value |
   |-------|-------|
   | **Connection name** | `databricks-contoso-dev` (or any descriptive name) |
   | **Connection type** | **Azure Databricks** |
   | **Databricks workspace URL** | `https://REPLACE_WITH_DATABRICKS_HOST` |
   | **Authentication kind** | **Service Principal** |
   | **Tenant ID** | `REPLACE_WITH_RESOURCE_ID` |
   | **Service Principal client ID** | `REPLACE_WITH_RESOURCE_ID` |
   | **Service Principal key** | *(paste the secret **Value** from Step A3)* |

4. Click **"Create"** — you should see a ✅ success confirmation

> **💡 Why this works better:** The Manage Connections page validates credentials independently of the mirrored catalog setup. If credentials are wrong, you get a clear error here. The inline flow sometimes has issues with connection state when credentials fail and are re-entered.

5. Now create the mirrored catalog:
   - Go to your workspace → **"+ New item"** → **"Mirrored Azure Databricks Catalog"**
   - In the connection dropdown, select the connection you just created (`databricks-contoso-dev`)
   - It should connect immediately without re-entering credentials

#### Option B: Inline Connection (During Mirrored Catalog Setup)

This creates the connection on-the-fly while setting up the mirrored catalog. Quicker for one-off setups but can be less reliable.

1. Open Fabric → navigate to your workspace
2. Click **"+ New item"** → search **"Mirrored Azure Databricks Catalog"**
3. Configure the **Databricks workspace connection**:

   | Field | Value |
   |-------|-------|
   | **Databricks workspace URL** | `https://REPLACE_WITH_DATABRICKS_HOST` |
   | **Authentication kind** | **Service Principal** |
   | **Tenant ID** | `REPLACE_WITH_RESOURCE_ID` |
   | **Client ID** | `REPLACE_WITH_RESOURCE_ID` |
   | **Client Secret** | *(paste the secret value from Step A3)* |

4. Click **"Connect"**

> **⚠️ If you get "Invalid connection credentials" or "Unable to update connection credentials" with inline creation**, try Option A instead. The inline flow sometimes fails to validate credentials properly, especially after a previous failed attempt in the same session. Pre-creating the connection via Manage Connections resolves this.

> **⚠️ "Failed to refresh OAuth token. Please try logging in again or ensure that OAuth is supported for this resource"**
>
> This error means the SP can't authenticate to the Databricks workspace. Common causes:
>
> | Cause | Fix |
> |-------|-----|
> | **Missing AzureDatabricks API permission (Step A4)** | **Most likely cause.** Go to Azure Portal → App Registration → API permissions → Add `AzureDatabricks` → `user_impersonation` → Grant admin consent |
> | SP not added to workspace (Step B2) | Go to Account Console → Workspaces → add SP with "User" role |
> | Wrong client secret (copied Secret ID instead of Value) | Go to Azure Portal → App Registration → Certificates & secrets → create a new secret and copy the **Value** column |
> | Client secret expired | Create a new secret in Azure Portal |
> | Tenant ID mismatch | Verify the tenant ID matches your Azure AD tenant (not a guest tenant) |
> | Using a Databricks-generated OAuth secret instead of Azure AD secret | Use the secret from **Azure Portal → App Registration → Certificates & secrets**, NOT from Databricks Account Console → "Generate OAuth secret" |
> | SP created in different tenant than the Databricks workspace | Ensure the App Registration is in the same Entra tenant as the Databricks workspace |

### Step C2 — Configure ADLS Storage Access (If Behind Firewall)

> **⚠️ This step is required if your Databricks storage account has a firewall enabled** (common in enterprise). Even with a valid Databricks connection, Fabric reads the actual Delta files from ADLS — if it can't reach the storage, you'll get errors like *"Unable to process response"* even though the workspace connection succeeded.

**Check if you need this:** If your ADLS storage account (where Databricks stores the Delta Lake files) has firewall rules enabled (not set to "Allow access from all networks"), you need this step.

1. In the Fabric mirroring setup wizard, click the **"Network Security"** tab
2. Create a **new ADLS connection**:

   | Field | Value |
   |-------|-------|
   | **URL** | The ADLS path where your catalog data is stored, e.g. `https://sacontosoaiwsauedev.dfs.core.windows.net/manufacturing/aiws-dev` (be specific — folder level, not just storage account) |
   | **Authentication** | **Workspace Identity** (recommended) or Service Principal |

3. **In the Azure Portal** — grant ADLS access to whichever identity you used:

   **Option A: Workspace Identity (recommended)**
   - In Fabric workspace → Settings → create a Workspace Identity (if not already done)
   - In Azure Portal → ADLS storage account → **Access Control (IAM)** → **+ Add role assignment**
   - Assign **Storage Blob Data Reader** to the Fabric Workspace Identity
   - If you specified a specific folder (recommended): also grant **Read (R) + Execute (E)** ACLs on the target folder AND **Execute (E)** on each parent folder up to the root

   **Option B: Service Principal**
   - In Azure Portal → ADLS storage account → **Access Control (IAM)** → **+ Add role assignment**
   - Assign **Storage Blob Data Reader** to the SP (`REPLACE_WITH_RESOURCE_ID`)
   - Same ACL requirements as above if folder-scoped

4. **Enable Trusted Workspace Access** on the storage account:
   - Azure Portal → Storage account → **Networking** → **Firewalls and virtual networks**
   - Under "Exceptions", enable: **"Allow Azure services on the trusted services list to access this storage account"**
   - For more granular control, configure [Trusted Workspace Access](https://learn.microsoft.com/en-us/fabric/security/security-trusted-workspace-access)

> **Why two connections?** The Databricks workspace connection lets Fabric discover catalogs/schemas/tables (metadata). The ADLS connection lets Fabric actually **read the Delta files** (data). If the storage is behind a firewall, only the second connection can punch through.
>
> **No firewall?** If your ADLS storage is set to "Allow access from all networks," you can skip this step — Fabric will access the Delta files directly using the SP credentials from the workspace connection.

### Step C3 — Select Catalog and Tables

1. Catalog: **`contoso`**
2. Select tables:

   | ☑️ | Schema.Table |
   |---|---|
   | ✅ | `contoso.projects.financials` |
   | ✅ | `contoso.equipment.equipment_telemetry` |
   | ✅ | `contoso.safety.incidents` |
   | ✅ | `contoso.procurement.materials` |

> **⚠️ Source tables with RLS/CLM — Known to cause sync failures:** If your Databricks tables have **row filters or column masks** applied (from Module 3 section 3.3.5), those tables **will fail to sync** with errors like:
>
> ```
> Resilience check failed: table change state is Unknown
> Error code: InternalServerError
> Table sync status: Failure
> ```
>
> **Which Contoso tables currently have row filters?**
> - `contoso.projects.financials` — ⚠️ has `division_filter` row filter → **will fail to sync**
> - `contoso.safety.incidents` — ⚠️ has `division_filter` row filter → **will fail to sync**
> - `contoso.equipment.equipment_telemetry` — ✅ no row filter → should mirror fine
> - `contoso.procurement.materials` — ✅ no row filter → should mirror fine
>
> **Fix — Option A: Remove row filters for mirroring (then re-apply later)**
>
> Run in Databricks SQL:
> ```sql
> ALTER TABLE contoso.projects.financials DROP ROW FILTER;
> ALTER TABLE contoso.safety.incidents DROP ROW FILTER;
> ```
>
> After mirroring is established and syncing, you can optionally re-apply the filters for the Genie MCP path:
> ```sql
> ALTER TABLE contoso.projects.financials SET ROW FILTER contoso.security.division_filter ON (division);
> ALTER TABLE contoso.safety.incidents SET ROW FILTER contoso.security.division_filter ON (division);
> ```
> ⚠️ Note: Re-applying row filters after mirroring is established may cause the sync to fail again on next resilience check. Test in your environment.
>
> **Fix — Option B: Create unfiltered views for mirroring (recommended for workshop)** ✅
>
> **This is now automated** in `contoso_setup/04_configure_rls.py` (Section 2b). When `create_mirror_views=yes`, the notebook creates these views before applying row filters:
> ```sql
> CREATE OR REPLACE VIEW contoso.projects.financials_f AS
>   SELECT * FROM contoso.projects.financials;
>
> CREATE OR REPLACE VIEW contoso.safety.incidents_f AS
>   SELECT * FROM contoso.safety.incidents;
> ```
> If `mirror_sp_id` is set, it also grants `SELECT` + `EXTERNAL USE SCHEMA` to the SP.
>
> To run manually or set the SP ID:
> ```
> databricks bundle run manufacturing_setup -t dev
> # or with SP grants:
> # Set mirror_sp_id widget to your SP Application ID (e.g. REPLACE_WITH_RESOURCE_ID)
> ```
> Then in the Fabric mirroring setup, select these tables:
> - `contoso.projects.financials_f` (view, no row filter)
> - `contoso.safety.incidents_f` (view, no row filter)
> - `contoso.equipment.equipment_telemetry` (base table, no row filter)
> - `contoso.procurement.materials` (base table, no row filter)
>
> The Genie MCP path still uses the base tables with row filters intact.
>
> **Why this happens:** Fabric reads Delta files directly from ADLS storage. Row filters are SQL-engine constructs — they don't exist at the storage layer. When Fabric tries to read the change feed from a table with row filters, the storage-level operation conflicts with the filter metadata, causing the "Resilience check failed" error.

3. Leave **"Automatically sync future catalog changes"** enabled
4. Click **"Create"**

### Step C4 — Verify

1. Wait for initial sync (30 seconds – few minutes)
2. Open the **SQL Analytics Endpoint** (auto-created alongside the mirror)
3. Run:

```sql
SELECT TOP 10 project_name, division, status, budget_aud
FROM contoso.projects.financials
ORDER BY budget_aud DESC;
```

✅ If you see data → mirroring works.

---

## 7. RLS: Does It Propagate?

### Short Answer: No

Databricks Unity Catalog row filters (the `IS_ACCOUNT_GROUP_MEMBER()` checks from Module 3 section 3.3.5) **do NOT automatically carry over** to Fabric.

### Why Not?

| Reason | Explanation |
|--------|-------------|
| **Single identity** | The mirror authenticates as the Service Principal — one identity, not per-user. The SP isn't in any division group, so row filters either show everything or nothing. |
| **Bypasses SQL engine** | Fabric reads Delta files directly from ADLS via shortcuts. Databricks row filters only execute when queries go through a SQL Warehouse. Fabric skips that entirely. |
| **Different platforms** | Fabric and Databricks have separate security models. Unity Catalog policies are Databricks-native; they don't extend outside Databricks. |

### What This Means in Practice

```
                                  Databricks                  Fabric
                                  ──────────                  ──────

Alice (CPB) queries               Row filter applied          NO filter applied
via Genie MCP:                    → sees only CPB data ✅     (n/a — not using Fabric)

Alice (CPB) queries               (n/a — not using            No filter by default
via Fabric Data Agent:             Databricks SQL engine)     → sees ALL divisions ❌
                                                              (unless Fabric RLS is set up)
```

### The Security Model Comparison

| Layer | Genie MCP Path | Fabric Mirroring Path |
|-------|---------------|----------------------|
| **Connection identity** | End user (OAuth passthrough) | Service Principal (single identity) |
| **RLS defined in** | Databricks Unity Catalog | Must define in Fabric SQL Analytics |
| **Function used** | `IS_ACCOUNT_GROUP_MEMBER()` | `IS_MEMBER()` |
| **Groups referenced** | Same Entra groups | Same Entra groups |
| **Auto-enforced?** | ✅ Yes — per-user auth means UC filters just work | ❌ No — must set up Fabric RLS manually |
| **Maintenance** | Single source of truth | Two places to maintain (Databricks + Fabric) |

---

## 8. Part D: Fabric — Secure the Mirrored Data

> There are **two approaches** to securing mirrored data in Fabric. Choose one based on your consumption pattern.

### Option 1: OneLake Security with RLS (Recommended — Fabric-Native) ✅

OneLake Security (GA 2026) provides **row-level security** directly on mirrored databases. This is the recommended approach — it enforces security across **all** Fabric engines (SQL, Spark, Power BI, Data Agent).

#### How It Maps to Databricks RLS

The Databricks side uses Unity Catalog row filters with `IS_ACCOUNT_GROUP_MEMBER()`. OneLake Security uses the **same Entra ID groups** with equivalent row-level filtering:

| OneLake Role | Entra Group | RLS Expression | Databricks Equivalent |
|-------------|-------------|------------|----------------------|
| `RoleCPB*` (Finance/Safety/Equipment) | `Group-A` | `SELECT * FROM {table} WHERE division = 'Division-Alpha'` | `IS_ACCOUNT_GROUP_MEMBER('Group-A')` |
| `RoleDivision-Beta*` (Finance/Safety/Equipment) | `Group-B` | `SELECT * FROM {table} WHERE division = 'Division-Beta'` | `IS_ACCOUNT_GROUP_MEMBER('Group-B')` |
| `RoleDivision-Gamma*` (Finance/Safety/Equipment) | `Group-C` | `SELECT * FROM {table} WHERE division = 'Division-Gamma'` | `IS_ACCOUNT_GROUP_MEMBER('Group-C')` |
| `RoleExecutivesAll` | `Group-Executives` | *(no filter — sees all rows)* | `IS_ACCOUNT_GROUP_MEMBER('Group-Executives')` |
| `RoleProcurementAll` | All groups | *(no filter — shared data)* | *(no RLS on procurement)* |

Applied to these mirrored tables (use `v_*_mirror` views if base tables have UC row filters):
- `contoso.projects.financials_f` (or `financials` if no UC row filter)
- `contoso.equipment.equipment_telemetry`
- `contoso.safety.incidents_f` (or `incidents` if no UC row filter)
- `contoso.procurement.materials` (shared reference data — all roles can read)

#### Step D1a — Sync Entra Groups in Databricks (If Not Already Done)

Ensure the Entra groups (`Group-A`, `Group-B`, `Group-C`, `Group-Executives`) are synced to Databricks via SCIM (Section 5) and have Unity Catalog privileges. This is needed so the same groups can be mapped in both systems.

#### Step D1b — Enable OneLake Security

1. In the Fabric workspace, open the **Mirrored Databricks Catalog** item
2. Click **"Manage OneLake security"** in the ribbon
3. Accept the prompt — **⚠️ this is irreversible once enabled**
4. A `DefaultReader` role is auto-created for existing viewers to prevent lockout

#### Step D1c — Create Division Roles with RLS

Below are the **exact role definitions** to create in the OneLake Security UI. Each role specifies which Entra group it maps to, which tables it can read, and the row security expression applied to each table.

> **Navigation:** Fabric workspace → Lakehouse / Mirrored DB → Manage OneLake security (preview) → **New role**
>
> **Syntax:** OneLake RLS rules use a full SQL `SELECT` statement:
> `SELECT * FROM {schema}.{table} WHERE {predicate}`
> Supported operators: `=`, `<>`, `>`, `<`, `IN`, `AND`, `OR`, `NOT`. Max 1000 chars.

---

##### Role 1: `RoleCPBFinance`

| Setting | Value |
|---------|-------|
| **Role name** | `RoleCPBFinance` |
| **Assign Entra group** | `Group-A` |

**Table-level access:** `financials_f`

**Row security expression:**
```sql
SELECT * FROM projects.financials_f WHERE division = 'Division-Alpha'
```

---

##### Role 2: `RoleCPBSafety`

| Setting | Value |
|---------|-------|
| **Role name** | `RoleCPBSafety` |
| **Assign Entra group** | `Group-A` |

**Table-level access:** `incidents_f`

**Row security expression:**
```sql
SELECT * FROM safety.incidents_f WHERE division = 'Division-Alpha'
```

---

##### Role 3: `RoleCPBEquipment`

| Setting | Value |
|---------|-------|
| **Role name** | `RoleCPBEquipment` |
| **Assign Entra group** | `Group-A` |

**Table-level access:** `equipment_telemetry_f`

**Row security expression:**
```sql
SELECT * FROM equipment.equipment_telemetry_f WHERE division = 'Division-Alpha'
```

---

##### Role 4: `RoleDivision-BetaFinance`

| Setting | Value |
|---------|-------|
| **Role name** | `RoleDivision-BetaFinance` |
| **Assign Entra group** | `Group-B` |

**Table-level access:** `financials_f`

**Row security expression:**
```sql
SELECT * FROM projects.financials_f WHERE division = 'Division-Beta'
```

---

##### Role 5: `RoleDivision-BetaSafety`

| Setting | Value |
|---------|-------|
| **Role name** | `RoleDivision-BetaSafety` |
| **Assign Entra group** | `Group-B` |

**Table-level access:** `incidents_f`

**Row security expression:**
```sql
SELECT * FROM safety.incidents_f WHERE division = 'Division-Beta'
```

---

##### Role 6: `RoleDivision-BetaEquipment`

| Setting | Value |
|---------|-------|
| **Role name** | `RoleDivision-BetaEquipment` |
| **Assign Entra group** | `Group-B` |

**Table-level access:** `equipment_telemetry_f`

**Row security expression:**
```sql
SELECT * FROM equipment.equipment_telemetry_f WHERE division = 'Division-Beta'
```

---

##### Role 7: `RoleDivision-GammaFinance`

| Setting | Value |
|---------|-------|
| **Role name** | `RoleDivision-GammaFinance` |
| **Assign Entra group** | `Group-C` |

**Table-level access:** `financials_f`

**Row security expression:**
```sql
SELECT * FROM projects.financials_f WHERE division = 'Division-Gamma'
```

---

##### Role 8: `RoleDivision-GammaSafety`

| Setting | Value |
|---------|-------|
| **Role name** | `RoleDivision-GammaSafety` |
| **Assign Entra group** | `Group-C` |

**Table-level access:** `incidents_f`

**Row security expression:**
```sql
SELECT * FROM safety.incidents_f WHERE division = 'Division-Gamma'
```

---

##### Role 9: `RoleDivision-GammaEquipment`

| Setting | Value |
|---------|-------|
| **Role name** | `RoleDivision-GammaEquipment` |
| **Assign Entra group** | `Group-C` |

**Table-level access:** `equipment_telemetry_f`

**Row security expression:**
```sql
SELECT * FROM equipment.equipment_telemetry_f WHERE division = 'Division-Gamma'
```

---

##### Role 10: `RoleExecutivesAll`

| Setting | Value |
|---------|-------|
| **Role name** | `RoleExecutivesAll` |
| **Assign Entra group** | `Group-Executives` |

**Table-level access:** All tables:
- `financials_f`
- `incidents_f`
- `equipment_telemetry`
- `materials`

**Row security expression:** *(none — do not add any row security rule. Executives see all rows.)*

---

##### Role 11: `RoleProcurementAll`

| Setting | Value |
|---------|-------|
| **Role name** | `RoleProcurementAll` |
| **Assign Entra group** | `Group-A`, `Group-B`, `Group-C`, `Group-Executives` |

**Table-level access:** `materials`

**Row security expression:** *(none — procurement is shared reference data, no `division` column)*

---

#### Quick Reference — All Roles Summary

| # | Role Name | Entra Group | Table | Row Security Expression |
|---|-----------|-------------|-------|------------------------|
| 1 | `RoleCPBFinance` | `Group-A` | `financials_f` | `SELECT * FROM projects.financials_f WHERE division = 'Division-Alpha'` |
| 2 | `RoleCPBSafety` | `Group-A` | `incidents_f` | `SELECT * FROM safety.incidents_f WHERE division = 'Division-Alpha'` |
| 3 | `RoleCPBEquipment` | `Group-A` | `equipment_telemetry_f` | `SELECT * FROM equipment.equipment_telemetry_f WHERE division = 'Division-Alpha'` |
| 4 | `RoleDivision-BetaFinance` | `Group-B` | `financials_f` | `SELECT * FROM projects.financials_f WHERE division = 'Division-Beta'` |
| 5 | `RoleDivision-BetaSafety` | `Group-B` | `incidents_f` | `SELECT * FROM safety.incidents_f WHERE division = 'Division-Beta'` |
| 6 | `RoleDivision-BetaEquipment` | `Group-B` | `equipment_telemetry_f` | `SELECT * FROM equipment.equipment_telemetry_f WHERE division = 'Division-Beta'` |
| 7 | `RoleDivision-GammaFinance` | `Group-C` | `financials_f` | `SELECT * FROM projects.financials_f WHERE division = 'Division-Gamma'` |
| 8 | `RoleDivision-GammaSafety` | `Group-C` | `incidents_f` | `SELECT * FROM safety.incidents_f WHERE division = 'Division-Gamma'` |
| 9 | `RoleDivision-GammaEquipment` | `Group-C` | `equipment_telemetry_f` | `SELECT * FROM equipment.equipment_telemetry_f WHERE division = 'Division-Gamma'` |
| 10 | `RoleExecutivesAll` | `Group-Executives` | All tables | *(none)* |
| 11 | `RoleProcurementAll` | All groups | `materials` | *(none)* |

> **Why per-table roles?** OneLake Security roles are scoped to specific tables. A single role can only apply one row security expression per table. Since each division needs the same filter on 3 different tables, you create 3 roles per division (one per table). This matches how the OneLake Security UI works: each role → one table → one row filter.

> **Why no `v_*_mirror` for equipment/procurement?** These tables don't have UC row filters applied in Databricks, so they mirror directly without needing wrapper views.

#### Step D1d — How to Create Each Role (UI Walkthrough)

For each role above, follow these steps in the Fabric portal:

1. **Manage OneLake security** → Click **"New role"**
2. **Role name** → Enter the exact name from the table above (e.g. `RoleCPBSafety`)
3. **Members** → Click **"Add members"** → Search for the Entra group (e.g. `Group-A`) → Select it
4. **Table access** → Under "Manage table level access", find the table (e.g. `incidents_f`) → Toggle **Read** access ON
5. **Row security** → Click **"Row and column security (Preview)"** on that table
6. **Add rule** → Paste the full SQL expression, e.g.:
   ```sql
   SELECT * FROM safety.incidents_f WHERE division = 'Division-Alpha'
   ```
7. Click **Save**

For `RoleExecutivesAll`:
- Grant Read access to **all tables**
- Do **NOT** add any row security expression (executives see everything)

For `RoleProcurementAll`:
- Grant Read access to `materials` only
- Do **NOT** add row security (procurement data has no division column)

#### Step D1e — Verify

Sign in as different users (must have **Viewer** workspace role):

| Test User | Group | Expected Result |
|-----------|-------|----------------|
| Alice | `Group-A` | Sees only Division-Alpha rows in financials, incidents, equipment. Sees all procurement. |
| Bob | `Group-B` | Sees only Division-Beta rows in financials, incidents, equipment. Sees all procurement. |
| Carol | `Group-C` | Sees only Division-Gamma rows in financials, incidents, equipment. Sees all procurement. |
| Dave | `Group-Executives` | Sees **all rows** in all tables. |

> **⚠️ Important:** Workspace Admins, Members, and Contributors **bypass** OneLake Security. Only users with the **Viewer** role are restricted by RLS. For the workshop demo, ensure test users have the Viewer role on the workspace.

### Option 2: T-SQL RLS on SQL Analytics Endpoint (Fallback)

If OneLake Security RLS doesn't meet your needs (e.g., you need complex filter logic beyond simple equality checks), use T-SQL security policies on the SQL Analytics Endpoint. This approach works when all consumption goes through the SQL endpoint (Data Agent, Power BI via DirectQuery).

> **Where:** Fabric portal → SQL Analytics Endpoint

The good news: you use the **same Entra ID groups** (`Group-A`, `Group-B`, `Group-C`, `Group-Executives`) — just referenced with a different function.

### Step D1 — Create the Security Predicate Function

In the **SQL Analytics Endpoint** → **"New SQL query"**:

```sql
-- Create a schema for security objects
CREATE SCHEMA IF NOT EXISTS security;
GO

-- Predicate function: checks if current user belongs to the division's Entra group
CREATE FUNCTION security.fn_division_filter(@division NVARCHAR(100))
RETURNS TABLE
WITH SCHEMABINDING
AS
RETURN
    SELECT 1 AS result
    WHERE
        -- User is in the specific division group
        (@division = 'Division-Alpha' AND IS_MEMBER('Group-A') = 1)
        OR (@division = 'Division-Beta' AND IS_MEMBER('Group-B') = 1)
        OR (@division = 'Division-Gamma' AND IS_MEMBER('Group-C') = 1)
        -- OR user is in the executives group (full access)
        OR IS_MEMBER('Group-Executives') = 1
        -- OR user is a Fabric workspace admin
        OR IS_MEMBER('db_owner') = 1;
GO
```

> **How this maps to Databricks:** In Databricks you used `IS_ACCOUNT_GROUP_MEMBER('Group-A')`. In Fabric you use `IS_MEMBER('Group-A')`. Same groups, different function name.

### Step D2 — Apply Security Policies to Each Table

```sql
-- Financials
CREATE SECURITY POLICY security.financials_rls
ADD FILTER PREDICATE security.fn_division_filter(division)
ON contoso.projects.financials
WITH (STATE = ON);
GO

-- Equipment Telemetry
CREATE SECURITY POLICY security.telemetry_rls
ADD FILTER PREDICATE security.fn_division_filter(division)
ON contoso.equipment.equipment_telemetry
WITH (STATE = ON);
GO

-- Safety Incidents
CREATE SECURITY POLICY security.incidents_rls
ADD FILTER PREDICATE security.fn_division_filter(division)
ON contoso.safety.incidents
WITH (STATE = ON);
GO

-- Procurement Materials
CREATE SECURITY POLICY security.materials_rls
ADD FILTER PREDICATE security.fn_division_filter(division)
ON contoso.procurement.materials
WITH (STATE = ON);
GO
```

> **Important:** The column name `division` must match exactly what's in each table. If a table uses a different column (e.g. `business_unit`), adjust the `ON` clause accordingly.

### Step D3 — Verify RLS

```sql
-- Check your own group membership
SELECT
    IS_MEMBER('Group-A') AS is_group_a,
    IS_MEMBER('Group-B') AS is_group_b,
    IS_MEMBER('Group-Executives') AS is_exec;

-- Count rows per division (should only show your division)
SELECT division, COUNT(*) AS row_count
FROM contoso.projects.financials
GROUP BY division;
```

If you're in `Group-Executives`, you'll see all rows. Ask a colleague in `Group-A` to run the same query — they should only see Division-Alpha rows.

---

## 9. Part E: Fabric Data Agent — Permissions & RLS Behaviour

### How the Data Agent Enforces Security

The Fabric Data Agent queries through the **SQL Analytics Endpoint**. Because you applied RLS policies on that endpoint (Part D), security is automatically enforced:

```
End User (Alice, Group-A)
    │
    ▼ signs in with Entra ID
Fabric Data Agent
    │
    ▼ generates SQL query
SQL Analytics Endpoint
    │
    ▼ RLS policy checks IS_MEMBER('Group-A')
    │   → Alice is a member → filter applied
    │
    ▼ returns only Division-Alpha rows
Data Agent formats response
    │
    ▼
Alice sees only Division-Alpha data ✅
```

### What You DON'T Need to Redo

| Thing | Need to redo in Fabric? | Why |
|-------|:-:|---|
| Entra ID group creation | ❌ No | Same groups used in both Databricks and Fabric |
| User group assignments | ❌ No | Users are in the same Entra groups regardless of platform |
| Table schema / data | ❌ No | Mirrored automatically — no data duplication |
| Table descriptions for Data Agent | ✅ Yes | Data Agent needs its own instructions (like Genie Space) |

### What You DO Need to Set Up in Fabric

| Thing | Where | Equivalent in Databricks |
|-------|-------|--------------------------|
| RLS security policies | SQL Analytics Endpoint (Part D) | Unity Catalog row filters |
| Data Agent instructions | Data Agent config | Genie Space instructions |
| Data Agent table selection | Data Agent config | Genie Space table selection |
| Workspace role assignments | Fabric workspace settings | Databricks workspace permissions |

### Data Agent Table Selection (Additional Access Control)

When creating the Data Agent, you choose which tables it can query. This is a **coarse-grained** control layer on top of RLS:

- **Table selection** = which tables exist in the agent's world
- **RLS** = which rows within those tables a user can see

Example: You could create two Data Agents:
1. `Contoso Finance Agent` — only has access to `financials` table
2. `Contoso Safety Agent` — only has access to `incidents` table

Both still enforce per-division RLS within their tables.

---

## 10. Quick Reference

### Three Values You Need Throughout

| Value | Source | Used In |
|-------|--------|---------|
| Application (client) ID: `REPLACE_WITH_RESOURCE_ID` | Azure App Registration | Databricks Account Console + Fabric connection |
| Directory (tenant) ID: `REPLACE_WITH_RESOURCE_ID` | Azure App Registration | Fabric connection |
| Client secret value | Azure App Registration → Certificates & secrets | Fabric connection |

### Permission Chain Summary

```
Azure Portal                  Databricks                         Fabric
────────────                  ──────────                         ──────
App Registration ──────►  Account Console: Add SP  ──────►  Connection: SP auth
  ├─ Client Secret                                               (via Manage Connections
  └─ API Permission:          Workspace: Assign "User"            or inline)
     AzureDatabricks          Unity Catalog:
     user_impersonation         ├─ USE CATALOG
     + Admin Consent            ├─ USE SCHEMA
                                ├─ SELECT
                                └─ EXTERNAL USE SCHEMA ◄── required for mirroring!

Entra ID Groups  ──SCIM──►  Account Groups (for DB RLS)
                 ──direct──►  Fabric IS_MEMBER() (for Fabric RLS)
```

### RLS Comparison Cheat Sheet

| | Databricks (Genie MCP) | Fabric (Mirroring) |
|---|---|---|
| **Define RLS** | `CREATE FUNCTION` + `ALTER TABLE ... SET ROW FILTER` | `CREATE FUNCTION` + `CREATE SECURITY POLICY` |
| **Check group** | `IS_ACCOUNT_GROUP_MEMBER('group')` | `IS_MEMBER('group')` |
| **Identity source** | OAuth passthrough (per-user) | Entra ID session (per-user) |
| **Groups** | Same Entra groups | Same Entra groups |
| **Auto-propagates?** | ✅ (per-user auth) | ❌ (must define separately) |

---

## 11. Troubleshooting

| Error / Symptom | Cause | Fix |
|----------------|-------|-----|
| **"Invalid credentials"** with Org Account | MFA / Conditional Access blocks non-interactive token refresh | Use Service Principal instead (this guide) |
| **`PowerBINotAuthorizedException`** | SP not allowed to use Fabric APIs at the tenant level | **Enable "Service principals can use Fabric APIs"** in Admin portal → Tenant settings → Developer settings (Step C0). May take up to 15 min to propagate. |
| **"Invalid credentials"** with Service Principal | Wrong client ID, tenant ID, expired secret, or **missing AzureDatabricks API permission** | Re-check all 3 values; recreate secret if needed; **verify Step A4 (API permission + admin consent)** — this is the most common cause |
| **"Unable to update connection credentials. Invalid connection credentials"** with SP | Inline connection creation failed to validate, or stale connection state | **Try creating the connection via Settings → Manage Connections and Gateways first** (Step C1 Option A), then select it when creating the mirrored catalog. This avoids the inline validation issues. Also verify Step A4 (API permission). |
| **"Failed to refresh OAuth token. Please try logging in again or ensure that OAuth is supported for this resource"** | SP not added to Databricks workspace, or wrong secret used | **Most common fix:** Ensure SP is added at Account Console (Step B1) AND assigned to the workspace (Step B2). Also verify you're using the Azure AD App Registration secret (NOT a Databricks-generated OAuth secret). See Step C1 troubleshooting table for full list. |
| **"Unable to process response from Databricks. API returned data in an unexpected format"** | One or more of: (1) External data access not enabled on metastore, (2) Missing `EXTERNAL USE SCHEMA`, (3) ADLS firewall blocking Fabric, (4) Source tables have RLS/CLM policies | Check in order: Step B3 (metastore toggle), Step B4 (EXTERNAL USE SCHEMA grants), Step C2 (ADLS storage connection if firewalled), Step C3 (source RLS warning) |
| **"Add service principal" greyed out** in Databricks workspace | Account-level identity management is enabled | Add SP at Account Console first (Step B1), then assign to workspace (Step B2) |
| **SP not found** in Databricks Account Console search | App Registration not yet synced to Databricks | Wait a few minutes, or paste the Application (client) ID directly |
| **Mirrored catalog shows "Error" status** | SP lacks permissions, workspace URL wrong, or ADLS inaccessible | Verify grants (Step B4), workspace URL, and ADLS access (Step C2) |
| **Some tables mirrored but others show error** | Those tables have RLS/CLM applied in Databricks | **Most likely cause for Contoso workshop.** The `financials`, `equipment_telemetry`, and `incidents` tables have row filters from Module 3. Drop the filters or create unfiltered views — see Step C3 warning box for SQL commands. |
| **"Resilience check failed: table change state is Unknown"** | Row filters or column masks on source table prevent storage-level change tracking | Same fix as above — drop row filters or mirror views instead of base tables (Step C3) |
| **Connection works but no tables visible** | SP doesn't have USE CATALOG or USE SCHEMA | Run the GRANT statements in Step B4 |
| **Data Agent returns ALL data** (no RLS) | Fabric security not configured | Set up OneLake Security (Option 1) or T-SQL RLS (Option 2) in Part D |
| **Data Agent returns NO data** | User not in any Entra group matching the security rules | Check group membership in Azure Portal → Entra ID → Groups; check `IS_MEMBER()` results |
| **Power BI shows all data despite Fabric RLS** | Direct Lake mode may need to fall back to DirectQuery for RLS | Verify the report uses DirectQuery mode, or configure OneLake Security instead of T-SQL RLS |
| **ADLS: "403 Forbidden" or "AuthorizationPermissionMismatch"** | Missing Storage Blob Data Reader role, or missing folder ACLs | Grant RBAC role AND folder-level ACLs (Read + Execute on target folder, Execute on parent folders) — see Step C2 |
| **Genie MCP: OAuth fails / wrong token endpoint** | Foundry MCP connector pointing at Databricks OIDC endpoint instead of Entra ID | Use `https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token` as the Token URL — **NOT** `https://adb-xxx.azuredatabricks.net/oidc/v1/token`. The Databricks OIDC endpoint is for Databricks-native OAuth (custom apps), not Azure-managed workspaces. Scope: `REPLACE_WITH_RESOURCE_ID/.default`. See diff guide section 3.3.2 for full config. |

---

## 12. RLS Testing Guide — Sample Questions

Use these questions to verify that row-level security works correctly for a test user (e.g., **Vinoth** in `Group-A` → should only see **Division-Alpha** data).

> **Pre-requisites:**
> - Vinoth is a member of `Group-A` in Entra ID
> - For Genie: Group-A is synced to Databricks via SCIM, grants applied (USE_CATALOG, SELECT, EXECUTE)
> - For Data Agent: OneLake Security roles created (Section 8), Vinoth has **Viewer** workspace role (Admins/Members/Contributors bypass OLS!)

### Genie Space — RLS Test Questions (as Vinoth / Group-A)

Ask these in the Databricks Genie Space. Vinoth should only see Division-Alpha rows.

**Positive tests (should return data):**

1. **"Show me all projects"**
   → ✅ Should return ONLY Division-Alpha projects (not Division-Beta, Division-Gamma, or Division-Delta)

2. **"What is the total budget across all my projects?"**
   → ✅ Should show Division-Alpha total only

3. **"List all safety incidents with severity Critical or Major"**
   → ✅ Should show only Division-Alpha incidents

4. **"Which equipment has engine temperature above 100°C?"**
   → ✅ Should show only Division-Alpha equipment

5. **"Show me all projects in Red status with their CPI and SPI"**
   → ✅ Should show only Division-Alpha red projects

**Negative tests (should NOT show other divisions):**

6. **"Show me Division-Beta projects"**
   → ❌ Should return zero rows (Vinoth can't see Division-Beta data)

7. **"Compare all divisions side by side"**
   → ✅ Should only show Division-Alpha (filter prevents seeing other divisions)

8. **"What is the total budget for Division-Gamma?"**
   → ❌ Should return zero or "no data found"

**Cross-domain test:**

9. **"Show me materials with rising prices"**
   → ✅ Should return data (procurement.materials has no RLS — shared reference data)

10. **"Give me a risk summary — red projects, critical incidents, and overdue equipment"**
    → ✅ Should show only Division-Alpha data across all three domains

### Fabric Data Agent — RLS Test Questions (as Vinoth / Group-A)

Ask these in the Fabric Data Agent. If OneLake Security roles are set up correctly, Vinoth should only see Division-Alpha rows from the mirrored DB.

**Positive tests (mirrored DB — should be filtered):**

1. **"Show me all projects from the mirrored database"**
   → ✅ Should return ONLY Division-Alpha projects from `financials_f`

2. **"How many safety incidents are there by severity?"**
   → ✅ Should show only Division-Alpha incidents from `incidents_f`

3. **"What equipment needs maintenance?"**
   → ✅ Should show only Division-Alpha equipment from `equipment_telemetry_f`

4. **"What is the total budget and actual cost for my projects?"**
   → ✅ Should show Division-Alpha totals only

5. **"Show me all Critical incidents that are still Open"**
   → ✅ Should show only Division-Alpha critical incidents

**Negative tests (should NOT show other divisions):**

6. **"Show me Division-Beta project budgets"**
   → ❌ Should return zero rows from mirrored DB

7. **"Compare divisions on safety incidents"**
   → ✅ Should only show Division-Alpha (OLS prevents other divisions)

**Lakehouse & SQL DB tests (NOT covered by OLS — no filtering):**

8. **"Show me the project KPIs from the lakehouse"**
   → ⚠️ Returns ALL divisions (lakehouse has no RLS — this is expected for the demo)

9. **"Show me the division summary from the SQL database"**
   → ⚠️ Returns ALL divisions (SQL DB has no OLS — expected)

10. **"Give me the monthly KPI trends"**
    → ⚠️ Returns all divisions from SQL DB (no OLS)

> **Note:** Lakehouse and SQL DB tables are separate Fabric items and are NOT covered by the mirrored DB's OneLake Security. For the demo, this is acceptable — the mirrored DB is the primary RLS showcase. If needed, T-SQL RLS (Option 2, Section 8) can secure the SQL Analytics Endpoint for these items separately.

### Executive User Tests (as yourself / Group-Executives)

Run the same questions above — you should see **all divisions** in every response.

| Question | Vinoth (Group-A) | You (Group-Executives) |
|----------|-------------------|----------------------|
| "Show me all projects" | Division-Alpha only | All 4 divisions |
| "Total budget" | CPB total | Full portfolio total |
| "Safety incidents" | CPB only | All divisions |
| "Division-Beta projects" | Zero rows | Division-Beta projects shown |
| "Division comparison" | CPB only | Full comparison table |

### Quick Verification SQL (Run in SQL Analytics Endpoint)

Sign in as Vinoth and run:

```sql
-- Check group membership
SELECT
    IS_MEMBER('Group-A') AS is_group_a,
    IS_MEMBER('Group-B') AS is_group_b,
    IS_MEMBER('Group-C') AS is_group_c,
    IS_MEMBER('Group-Executives') AS is_exec;
-- Expected for Vinoth: 1, 0, 0, 0

-- Count rows per division (should only show Division-Alpha)
SELECT division, COUNT(*) AS row_count
FROM projects.financials_f
GROUP BY division;
-- Expected: only one row — 'Division-Alpha'

-- Verify other tables
SELECT division, COUNT(*) AS row_count FROM safety.incidents_f GROUP BY division;
SELECT division, COUNT(*) AS row_count FROM equipment.equipment_telemetry_f GROUP BY division;
-- Expected: only Division-Alpha rows
```
