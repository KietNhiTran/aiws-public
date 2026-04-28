# Databricks Permissions Guide: Genie, Data & User Access

> **Scope:** Complete reference for Databricks permissions — covering workspace access, Unity Catalog data permissions, Genie Space ACLs, and how they all layer together. Written for the Contoso workshop context.

---

## Table of Contents

1. [The Three Permission Layers](#1-the-three-permission-layers)
2. [Layer 1: Workspace Permissions](#2-layer-1-workspace-permissions)
3. [Layer 2: Unity Catalog (Data Permissions)](#3-layer-2-unity-catalog-data-permissions)
4. [Layer 3: Genie Space Permissions](#4-layer-3-genie-space-permissions)
5. [How the Layers Stack Together](#5-how-the-layers-stack-together)
6. [Permission Matrix: What Each User Type Needs](#6-permission-matrix-what-each-user-type-needs)
7. [Row-Level Security & Column Masks](#7-row-level-security--column-masks)
8. [Fabric Mirroring: Different Permission Model](#8-fabric-mirroring-different-permission-model)
9. [SCIM: How Identities Get Into Databricks](#9-scim-how-identities-get-into-databricks)
10. [Practical Setup: Contoso Workshop](#10-practical-setup-contoso-workshop)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. The Three Permission Layers

Databricks has **three independent layers** of permissions. A user needs the right permissions at **each layer** to successfully interact with data through Genie or direct SQL.

```
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 1: WORKSPACE PERMISSIONS                                     │
│  "Can this user access the Databricks workspace at all?"            │
│  ┌────────────┐ ┌────────────┐ ┌──────────────┐ ┌──────────────┐  │
│  │  Admin      │ │  User      │ │  Viewer      │ │  No access   │  │
│  └────────────┘ └────────────┘ └──────────────┘ └──────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│  Layer 2: UNITY CATALOG (DATA PERMISSIONS)                          │
│  "Which catalogs, schemas, and tables can this user read/write?"    │
│  ┌───────────┐ ┌────────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │USE CATALOG│ │ USE SCHEMA │ │  SELECT  │ │ EXTERNAL USE     │   │
│  │           │ │            │ │          │ │ SCHEMA           │   │
│  └───────────┘ └────────────┘ └──────────┘ └──────────────────┘   │
│  + Row Filters (RLS) + Column Masks                                 │
├─────────────────────────────────────────────────────────────────────┤
│  Layer 3: GENIE SPACE PERMISSIONS                                   │
│  "Can this user ask questions in this specific Genie Space?"        │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌──────────────────┐   │
│  │ CAN VIEW  │ │ CAN QUERY │ │ CAN EDIT  │ │ CAN MANAGE       │   │
│  └───────────┘ └───────────┘ └───────────┘ └──────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

**All three layers must be satisfied.** Having `CAN QUERY` on a Genie Space but no `SELECT` on the underlying tables = empty results. Having `SELECT` on tables but no workspace access = can't even log in.

---

## 2. Layer 1: Workspace Permissions

Workspace permissions control **who can access the Databricks workspace** and what they can do with workspace objects (notebooks, jobs, clusters, SQL warehouses, dashboards).

### Workspace Roles

| Role | What It Allows | Typical User |
|------|---------------|-------------|
| **Admin** | Full control — manage users, clusters, settings, all objects | Platform team, Databricks admins |
| **User** | Create and run notebooks, jobs, clusters; access SQL warehouses; use Genie | Data engineers, analysts, workshop participants |
| **Viewer** (Consumer) | Read-only access to dashboards, Genie spaces (with CAN VIEW/QUERY); cannot create anything | Business users who only consume reports/Genie |
| **No access** | Cannot enter the workspace | Users not assigned to this workspace |

### How to Assign

- **Account Console** → Workspaces → [your workspace] → Permissions → Add user/group → select role
- Or via SCIM auto-provisioning (users synced from Entra ID get workspace access automatically if configured)

### SQL Warehouse Permissions

Within a workspace, SQL Warehouses have their own permissions:

| Permission | What It Allows |
|-----------|---------------|
| **CAN USE** | Execute queries on this warehouse |
| **CAN MONITOR** | View warehouse status and query history |
| **CAN MANAGE** | Start/stop, resize, configure the warehouse |
| **IS OWNER** | Full control + delete |

> **For Genie:** Users need **CAN USE** on the SQL Warehouse attached to the Genie Space. Without it, Genie can generate SQL but can't execute it.

---

## 3. Layer 2: Unity Catalog (Data Permissions)

Unity Catalog is Databricks' **data governance layer**. It controls access to data objects: catalogs, schemas, tables, views, functions, volumes, and external locations.

### Hierarchy

```
Metastore (account-level, one per region)
  └── Catalog (e.g., contoso)
        └── Schema (e.g., contoso.projects)
              ├── Table (e.g., contoso.projects.financials)
              ├── View
              ├── Function (e.g., contoso.security.division_filter)
              └── Volume
```

### Permission Reference

#### Catalog-Level

| Permission | What It Allows | SQL Example |
|-----------|---------------|-------------|
| **USE CATALOG** | Navigate into the catalog; see its schemas | `GRANT USE CATALOG ON CATALOG contoso TO 'user@company.com'` |
| **CREATE SCHEMA** | Create new schemas in the catalog | `GRANT CREATE SCHEMA ON CATALOG contoso TO 'data_engineers'` |
| **ALL PRIVILEGES** | Everything on the catalog | `GRANT ALL PRIVILEGES ON CATALOG contoso TO 'admin_group'` |

#### Schema-Level

| Permission | What It Allows | SQL Example |
|-----------|---------------|-------------|
| **USE SCHEMA** | Navigate into the schema; see its tables | `GRANT USE SCHEMA ON SCHEMA contoso.projects TO 'user@company.com'` |
| **SELECT** | Read data from all tables in the schema | `GRANT SELECT ON SCHEMA contoso.projects TO 'analyst_group'` |
| **MODIFY** | INSERT, UPDATE, DELETE on tables | `GRANT MODIFY ON SCHEMA contoso.projects TO 'data_engineers'` |
| **CREATE TABLE** | Create new tables in the schema | `GRANT CREATE TABLE ON SCHEMA contoso.projects TO 'data_engineers'` |
| **CREATE FUNCTION** | Create UDFs in the schema | `GRANT CREATE FUNCTION ON SCHEMA contoso.security TO 'admin_group'` |
| **EXTERNAL USE SCHEMA** | Read Delta files directly from storage (ADLS) — **required for Fabric mirroring** | `GRANT EXTERNAL USE SCHEMA ON SCHEMA contoso.projects TO 'sp-client-id'` |
| **ALL PRIVILEGES** | Everything on the schema | `GRANT ALL PRIVILEGES ON SCHEMA contoso.projects TO 'admin_group'` |

#### Table-Level

| Permission | What It Allows | SQL Example |
|-----------|---------------|-------------|
| **SELECT** | Read data from this specific table | `GRANT SELECT ON TABLE contoso.projects.financials TO 'user@company.com'` |
| **MODIFY** | INSERT, UPDATE, DELETE on this table | `GRANT MODIFY ON TABLE contoso.projects.financials TO 'data_engineers'` |
| **ALTER** | Change table structure (add columns, set properties) | Not needed for read-only access |
| **DROP** | Delete the table | Admin only |

### The Minimum for a Read-Only User

To query `contoso.projects.financials`, a user needs exactly:

```sql
GRANT USE CATALOG ON CATALOG contoso TO `user@company.com`;
GRANT USE SCHEMA ON SCHEMA contoso.projects TO `user@company.com`;
GRANT SELECT ON TABLE contoso.projects.financials TO `user@company.com`;
```

Or grant at schema level for all tables in the schema:

```sql
GRANT USE CATALOG ON CATALOG contoso TO `user@company.com`;
GRANT USE SCHEMA ON SCHEMA contoso.projects TO `user@company.com`;
GRANT SELECT ON SCHEMA contoso.projects TO `user@company.com`;
```

Or at catalog level for everything:

```sql
GRANT USE CATALOG ON CATALOG contoso TO `user@company.com`;
GRANT USE SCHEMA ON CATALOG contoso TO `user@company.com`;
GRANT SELECT ON CATALOG contoso TO `user@company.com`;
```

### What `EXTERNAL USE SCHEMA` Is (and When You Need It)

| Permission | Normal SQL Query Path | Fabric Mirroring Path |
|-----------|----------------------|----------------------|
| `SELECT` | ✅ Needed — query runs through SQL Warehouse | ✅ Also needed |
| `EXTERNAL USE SCHEMA` | ❌ Not needed | ✅ **Required** — Fabric reads Delta files directly from ADLS, bypassing the SQL Warehouse |

**Rule of thumb:** If the consumer reads through a SQL Warehouse or Genie → `SELECT` is enough. If the consumer reads the underlying files directly (Fabric mirroring, external tools) → also need `EXTERNAL USE SCHEMA`.

---

## 4. Layer 3: Genie Space Permissions

Genie Spaces have their own ACL (Access Control List) that determines **who can interact with a specific Genie Space**.

### Genie Space Permission Levels

| Permission | View Space | Ask Questions | Edit Instructions/Tables | Manage Sharing |
|-----------|:----------:|:-------------:|:------------------------:|:--------------:|
| **CAN VIEW** | ✅ | ❌ | ❌ | ❌ |
| **CAN QUERY** (CAN RUN) | ✅ | ✅ | ❌ | ❌ |
| **CAN EDIT** | ✅ | ✅ | ✅ | ❌ |
| **CAN MANAGE** | ✅ | ✅ | ✅ | ✅ |

### What Each Level Means

**CAN VIEW** — Can see the Genie Space exists and view its configuration, but cannot submit questions. Useful for auditors or stakeholders who need to review what's been set up.

**CAN QUERY** (also called CAN RUN) — Can **ask questions** in the Genie Space. Genie generates SQL and executes it against the SQL Warehouse. This is the level for **business users** who want to interact with data through natural language. They cannot change the Space's instructions, tables, or sample queries.

**CAN EDIT** — Can modify the Genie Space: change instructions, add/remove tables, update sample queries, adjust terminology. Cannot change who has access. This is for **data stewards** or **analysts** who curate the Space.

**CAN MANAGE** — Full control: edit + manage sharing + delete. This is for the **Space owner** or **admin**.

### How to Assign Genie Permissions

1. Open the Genie Space
2. Click the **"Share"** button (top-right)
3. Search for users or groups
4. Select the permission level from the dropdown
5. Click **"Add"**

> **Important:** Genie permissions control access to the *Space*. Even if a user has `CAN QUERY`, they still need `SELECT` on the underlying Unity Catalog tables — otherwise Genie generates SQL but the execution returns "Permission denied."

---

## 5. How the Layers Stack Together

### Example: Alice wants to ask a question in the Contoso Genie Space

```
Alice tries to ask: "Show me red-status CPB projects"
    │
    ▼ Layer 1: Does Alice have workspace access?
    ├── NO  → "You don't have access to this workspace" ❌
    └── YES → continue
          │
          ▼ Layer 3: Does Alice have CAN QUERY on this Genie Space?
          ├── NO  → Alice can't see or interact with the Space ❌
          ├── CAN VIEW only → Alice can see the Space but can't ask questions ❌
          └── CAN QUERY → continue
                │
                ▼ Genie generates SQL:
                │  SELECT * FROM contoso.projects.financials WHERE status = 'red'
                │
                ▼ Layer 2: Does Alice have SELECT on contoso.projects.financials?
                ├── NO  → "Permission denied" error ❌
                └── YES → SQL executes
                      │
                      ▼ Layer 2 (RLS): Row filter applied
                      │  Alice is in Group-A → only CPB rows returned
                      │
                      ▼ Results returned to Alice ✅
                      Only red-status CPB projects shown
```

### The Checklist: What a Genie End User Needs

| # | Layer | Permission | How to Grant |
|---|-------|-----------|-------------|
| 1 | Workspace | **User** or **Viewer** role | Account Console → Workspaces → Permissions |
| 2 | SQL Warehouse | **CAN USE** on the warehouse attached to Genie | SQL Warehouses → [warehouse] → Permissions |
| 3 | Unity Catalog | **USE CATALOG** on `contoso` | SQL: `GRANT USE CATALOG ON CATALOG contoso TO ...` |
| 4 | Unity Catalog | **USE SCHEMA** on relevant schemas | SQL: `GRANT USE SCHEMA ON SCHEMA contoso.projects TO ...` |
| 5 | Unity Catalog | **SELECT** on relevant tables/schemas | SQL: `GRANT SELECT ON SCHEMA contoso.projects TO ...` |
| 6 | Genie Space | **CAN QUERY** on the Genie Space | Genie Space → Share → add user with CAN QUERY |
| 7 | (Optional) RLS | User in the right Entra group | Entra ID group membership (synced via SCIM) |

> **Shortcut for workshops:** Grant items 3–5 at the catalog level to a group, and add all participants to that group.

---

## 6. Permission Matrix: What Each User Type Needs

### For the Contoso Workshop

| User Type | Workspace Role | SQL Warehouse | Unity Catalog | Genie Space | Entra Group |
|-----------|:-----:|:-----:|:-----:|:-----:|:-----:|
| **Workshop presenter** | Admin | CAN MANAGE | ALL PRIVILEGES on `contoso` | CAN MANAGE | Group-Executives |
| **CPB analyst** | User | CAN USE | USE CATALOG + USE SCHEMA + SELECT on `contoso` | CAN QUERY | Group-A |
| **Division-Beta analyst** | User | CAN USE | USE CATALOG + USE SCHEMA + SELECT on `contoso` | CAN QUERY | Group-B |
| **Executive** | User | CAN USE | USE CATALOG + USE SCHEMA + SELECT on `contoso` | CAN QUERY | Group-Executives |
| **Genie Space curator** | User | CAN USE | USE CATALOG + USE SCHEMA + SELECT on `contoso` | CAN EDIT | (any division) |
| **Fabric mirror SP** | (Service principal) | Not needed | USE CATALOG + USE SCHEMA + SELECT + **EXTERNAL USE SCHEMA** | Not needed | N/A |
| **Foundry agent (via MCP)** | N/A (uses OAuth passthrough) | End user's permission | End user's permission | End user's permission | End user's group |

### Key Observations

- **Genie via MCP uses the end user's identity** — the Foundry agent passes through the signed-in user's Entra ID token. So Alice's query runs with Alice's permissions. No service account.
- **Fabric mirror uses a Service Principal** — a single identity with broad read access. RLS must be reimplemented in Fabric (see [section 8](#8-fabric-mirroring-different-permission-model)).
- **The SP doesn't need Genie permissions** — it reads Delta files directly, not through Genie.

---

## 7. Row-Level Security & Column Masks

### Row Filters (RLS)

Unity Catalog row filters are **enforced at the data layer** — they apply to ALL query paths: direct SQL, notebooks, Genie, MCP, dashboards.

```sql
-- The filter function (already created in Module 3)
CREATE OR REPLACE FUNCTION contoso.security.division_filter(division_value STRING)
RETURNS BOOLEAN
RETURN
  IS_ACCOUNT_GROUP_MEMBER('Group-Executives')
  OR (division_value = 'Division-Alpha' AND IS_ACCOUNT_GROUP_MEMBER('Group-A'))
  OR (division_value = 'Division-Beta'           AND IS_ACCOUNT_GROUP_MEMBER('Group-B'))
  OR (division_value = 'Division-Gamma'          AND IS_ACCOUNT_GROUP_MEMBER('Group-C'));

-- Applied to a table
ALTER TABLE contoso.projects.financials
  SET ROW FILTER contoso.security.division_filter ON (division);
```

### Column Masks

Column masks partially hide sensitive values for unauthorised users:

```sql
-- Executives see exact budget; others see rounded to nearest million
CREATE OR REPLACE FUNCTION contoso.security.mask_budget(budget_value DOUBLE)
RETURNS DOUBLE
RETURN
  CASE
    WHEN IS_ACCOUNT_GROUP_MEMBER('Group-Executives') THEN budget_value
    ELSE ROUND(budget_value / 1000000, 0) * 1000000
  END;

ALTER TABLE contoso.projects.financials
  ALTER COLUMN budget_aud SET MASK contoso.security.mask_budget;
```

### RLS + Genie: How It Works End-to-End

| Step | What Happens |
|------|-------------|
| 1. User asks Genie a question | "Show me all projects" |
| 2. Genie generates SQL | `SELECT * FROM contoso.projects.financials` |
| 3. SQL Warehouse executes query | Unity Catalog applies row filter automatically |
| 4. Row filter checks user identity | `IS_ACCOUNT_GROUP_MEMBER('Group-A')` → TRUE for Alice |
| 5. Only matching rows returned | Alice sees 5 CPB projects, not all 10 |
| 6. Column mask applied | If Alice isn't an executive, budget shows as rounded |
| 7. Result sent back through MCP to Foundry agent | Agent presents filtered results |

**No Genie-side or Foundry-side configuration needed for RLS.** It's entirely a Unity Catalog concern.

---

## 8. Fabric Mirroring: Different Permission Model

When data is mirrored to Fabric, the permission model **completely changes**:

### What Carries Over vs What Doesn't

| Databricks Permission | Carries Over to Fabric? | Why |
|----------------------|:-:|---|
| Unity Catalog grants (USE CATALOG, SELECT, etc.) | ❌ No | Fabric has its own permission model |
| Row filters (RLS) | ❌ No | Fabric reads Delta files directly, bypassing the SQL engine where filters execute |
| Column masks | ❌ No | Same reason — bypassed |
| Entra ID group membership | ✅ Yes | Groups exist in Entra ID, accessible from both platforms |

### Where to Redefine Security in Fabric

| Databricks Equivalent | Fabric Equivalent | Where to Configure |
|----------------------|------------------|-------------------|
| Workspace role (User/Admin) | Workspace role (Viewer/Contributor/Member/Admin) | Fabric workspace settings |
| Unity Catalog SELECT | Item-level sharing | Fabric workspace → share specific items |
| Row filters (`IS_ACCOUNT_GROUP_MEMBER()`) | Fabric RLS (`IS_MEMBER()`) | SQL Analytics Endpoint → security policies |
| Column masks | Fabric column-level security | SQL Analytics Endpoint → security policies |
| Genie Space ACL | Data Agent table selection | Fabric Data Agent config |

> **Full Fabric RLS setup guide:** See `databricks/docs/fabric-mirroring-auth-permissions-rls-guide.md` section 8 (Part D).

---

## 9. SCIM: How Identities Get Into Databricks

### What SCIM Does

SCIM (System for Cross-domain Identity Management) **auto-syncs users and groups** from Microsoft Entra ID to the Databricks Account Console.

```
Entra ID                          Databricks Account Console
────────                          ──────────────────────────
Users:                     ──►    Users (auto-provisioned)
  alice@contoso.com      SCIM      alice@contoso.com
  bob@contoso.com                   bob@contoso.com

Groups:                    ──►    Account Groups (auto-provisioned)
  Group-A                 SCIM      Group-A
  Group-B                            Group-B
```

### What SCIM Is Needed For

| Scenario | Needs SCIM? | Why |
|----------|:-:|---|
| Users logging into Databricks workspace | ✅ Recommended | Users must exist in Databricks; SCIM automates this |
| Groups for Unity Catalog row filters | ✅ Yes | `IS_ACCOUNT_GROUP_MEMBER()` checks Databricks groups — SCIM syncs Entra groups so they're available |
| Genie Space sharing with groups | ✅ Yes | You share a Genie Space with a group — that group must exist in Databricks |
| Service Principal for Fabric mirror | ❌ No | SPs are manually added at Account Console, not via SCIM |
| Fabric RLS with `IS_MEMBER()` | ❌ No | Fabric checks Entra groups directly — no Databricks involved |
| Unity Catalog GRANT statements | ❌ No | Grants are manual SQL — SCIM just makes the users/groups available to grant to |

### How to Set Up SCIM

1. **Azure Portal** → **Microsoft Entra ID** → **Enterprise applications**
2. Click **"+ New application"** → search **"Azure Databricks SCIM Provisioning Connector"**
3. Or find your existing Databricks enterprise app
4. Go to **"Provisioning"** tab → **"Get started"**
5. Set Provisioning Mode to **"Automatic"**
6. Enter:
   - **Tenant URL:** `https://accounts.azuredatabricks.net/api/2.0/accounts/<account-id>/scim/v2`
   - **Secret Token:** Generate a PAT from Databricks Account Console → Settings → User provisioning → Generate token
7. Click **"Test Connection"** → should succeed
8. Under **"Mappings"**, ensure both Users and Groups are enabled
9. Click **"Start provisioning"**

> **Note:** SCIM provisioning typically runs every 40 minutes. You can click "Provision on demand" for immediate sync of specific users.

---

## 10. Practical Setup: Contoso Workshop

### Quick Setup Script for Workshop Participants

Run this in a Databricks SQL Editor as a workspace admin to grant a group read access to all Contoso data:

```sql
-- Create a group for workshop participants (if not using SCIM)
-- (Skip if the group already exists via SCIM)

-- Grant catalog-level read access to the workshop group
GRANT USE CATALOG ON CATALOG contoso TO `Contoso-Workshop-Participants`;
GRANT USE SCHEMA ON CATALOG contoso TO `Contoso-Workshop-Participants`;
GRANT SELECT ON CATALOG contoso TO `Contoso-Workshop-Participants`;
```

Then share the Genie Space:
1. Open the Genie Space → **Share** → add `Contoso-Workshop-Participants` with **CAN QUERY**
2. Verify the SQL Warehouse has `CAN USE` for the same group

### Per-Division RLS (Already Set Up in Module 3)

If row filters are applied (section 3.3.5 in Module 3), division-level isolation is automatic:
- Alice (CPB group) queries through Genie → sees only CPB data
- Bob (Division-Beta group) queries through Genie → sees only Division-Beta data
- Carol (Executives group) queries through Genie → sees all data

### For Fabric Mirroring (Service Principal)

Additional grants needed beyond normal user access:

```sql
-- The SP needs EXTERNAL USE SCHEMA (not needed for regular users)
GRANT EXTERNAL USE SCHEMA ON SCHEMA contoso.projects TO `REPLACE_WITH_SERVICE_PRINCIPAL_ID`;
GRANT EXTERNAL USE SCHEMA ON SCHEMA contoso.equipment TO `REPLACE_WITH_SERVICE_PRINCIPAL_ID`;
GRANT EXTERNAL USE SCHEMA ON SCHEMA contoso.safety TO `REPLACE_WITH_SERVICE_PRINCIPAL_ID`;
GRANT EXTERNAL USE SCHEMA ON SCHEMA contoso.procurement TO `REPLACE_WITH_SERVICE_PRINCIPAL_ID`;
```

---

## 11. Troubleshooting

| Symptom | Layer | Cause | Fix |
|---------|-------|-------|-----|
| "You don't have access to this workspace" | Workspace | User not assigned to workspace | Account Console → Workspaces → add user |
| Can see Genie Space but can't ask questions | Genie | Only has CAN VIEW, needs CAN QUERY | Genie Space → Share → change to CAN QUERY |
| Genie says "Permission denied" on query | Unity Catalog | Missing SELECT on the table | `GRANT SELECT ON SCHEMA contoso.projects TO ...` |
| Genie says "Cannot resolve catalog" | Unity Catalog | Missing USE CATALOG | `GRANT USE CATALOG ON CATALOG contoso TO ...` |
| Genie runs but returns 0 rows | RLS | User not in any division group (row filter blocks all) | Add user to appropriate Entra group; verify SCIM sync |
| "SQL warehouse not found" or timeout | SQL Warehouse | Warehouse stopped or user lacks CAN USE | Start warehouse; grant CAN USE permission |
| Fabric mirror: "unexpected format" | Unity Catalog | Missing EXTERNAL USE SCHEMA | `GRANT EXTERNAL USE SCHEMA ON SCHEMA ... TO ...` |
| Fabric mirror: "Invalid credentials" | Auth | Org account blocked by MFA | Use Service Principal instead |
| Fabric Data Agent shows all divisions | Fabric RLS | RLS not configured in Fabric | See `fabric-mirroring-auth-permissions-rls-guide.md` Part D |
| SCIM groups not appearing in Databricks | SCIM | Provisioning not started or group out of scope | Check Entra ID → Enterprise apps → Provisioning → start/scope |

---

## 12. RLS & Data Governance — Demo Script

> Walks through a live demo showing how RLS, column masking, and table-level access control are enforced through Genie Spaces.

### Prerequisites

- Entra ID groups synced to Databricks via SCIM
- Row filters applied (`apply_row_filter=yes`)
- Column mask applied (`apply_column_mask=yes`)
- Table-level grants applied (`apply_grants=yes`)
- Genie Space created
- OAuth Identity Passthrough configured in Foundry

### Act 1: Same Question, Different Data

**Ask:** "Show me all projects and their RAG status"

| User | Group | Sees |
|------|-------|------|
| Alice | CPB Division | CPB projects only, budget rounded |
| Bob | Division-Beta Division | Division-Beta projects only, budget rounded |
| Carol | Executives | ALL projects, exact budget values |

> **Talking point:** Same agent, same Genie Space — Unity Catalog enforces security automatically via Entra ID group membership.

### Act 2: Cross-Domain Query

**Ask:** "How many safety incidents does my division have this month?"

- Alice → CPB incidents only
- Carol → All divisions with breakdown

### Act 3: Column Masking

**Ask:** "What's the exact budget for the WestConnex project?"

- Alice (division user) → Rounded ($1,200,000,000)
- Carol (executive) → Exact ($1,203,456,789)

### Governance Flow

```
User signs in (Entra ID) → Foundry Agent → Genie MCP → SQL Warehouse → Unity Catalog
    ├── Table RBAC: Does user have SELECT?
    ├── Row Filter: division_filter() → IS_MEMBER() check
    ├── Column Mask: mask_budget() → executives see exact, others see rounded
    └── Only authorized, filtered, masked data returned
```

### Fabric Comparison

| Security Layer | Genie (Databricks) | Data Agent (Fabric) |
|---------------|--------------------|--------------------|
| Row Filters | UC `division_filter` | OneLake Security roles |
| Column Masks | UC `mask_budget` | Not yet supported on mirrored data |
| Table RBAC | UC GRANT/REVOKE | OneLake Security object-level |
| Identity | OAuth passthrough | Fabric workspace identity |
| Groups | Same Entra ID groups | Same Entra ID groups |
