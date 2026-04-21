# CIMIC AI Workshop (aiws) — Copilot Agent Instructions

## Project Overview

This is the **CIMIC AI Workshop** project — a reference architecture for connecting Azure Databricks data to Microsoft AI Foundry agents via two paths:

1. **Path A: Genie MCP** — Databricks Genie Spaces exposed as MCP servers, connected directly to Foundry agents. Uses OAuth Identity Passthrough for per-user RLS.
2. **Path B: Fabric Mirroring** — Databricks Unity Catalog mirrored into Microsoft Fabric, queried by Fabric Data Agents. Uses OneLake Security for Fabric-side RLS.

Both paths share the same 4 tables (financials, equipment_telemetry, incidents, materials) across 4 schemas (projects, equipment, safety, procurement) under a Unity Catalog.

## Architecture — 5 Aligned Agents/Spaces

| # | Name | Tables | Purpose |
|---|------|--------|---------|
| 1 | CIMIC Project Intelligence | All 4 | Cross-domain operations |
| 2 | CIMIC Safety & Compliance | incidents | HSE domain |
| 3 | CIMIC Equipment & Fleet | equipment_telemetry | Fleet management |
| 4 | CIMIC Procurement & Supply | materials | Procurement domain |
| 5 | CIMIC Projects & Finance | financials | Project finance |

These 5 are mirrored 1:1 between Databricks Genie Spaces and Fabric Data Agents.

## Repository Structure

```
databricks/
├── cimic_setup/          # Module 03 setup notebooks (DABS-deployed)
│   ├── 01_create_schema.py
│   ├── 02_generate_data.py
│   ├── 03_setup_genie.py          # Creates all-in-one Genie Space
│   ├── 04_configure_rls.py        # RLS + mirror views
│   ├── 05_domain_genie_spaces.py  # Creates 5 domain Genie Spaces
│   └── 06_create_fabric_tables.py
├── src/                  # Main pipeline versions (extended queries)
├── resources/            # DABS job definitions (module03_jobs.yml)
├── docs/                 # Databricks-specific docs
└── databricks.yml        # Bundle config (dev + production targets)

fabric/
├── agents/               # 5 Data Agent instruction files (.md)
├── scripts/              # Fabric deployment (01_deploy_workspace.py, etc.)
├── notebooks/            # SQL scripts for Fabric SQL DB
└── docs/                 # Fabric mirroring + RLS guide

modules/                  # Workshop module guides (01-05)
docs/                     # Cross-cutting docs (production deployment guide)
```

## Key Conventions

### Groups (Demo Only)
- **Group-A** → CPB Contractors division
- **Group-B** → Thiess division
- **Group-C** → Sedgman division
- **Group-Executives** → Full cross-division access
- Do NOT use old names like `CIMIC-Division-CPB` — always use `Group-A/B/C/Executives`

### Catalogs
- **Dev**: `cimic` (workspace: `adb-7405614861019645.5`)
- **Prod**: `cimic_prod` (workspace: `adb-7405609499683390.10`)

### Deployment
- **Databricks**: DABS (`databricks bundle deploy/run`)
  - Dev: `databricks bundle deploy -t dev`
  - Prod: `databricks bundle deploy -t production -p PROD` (requires `-p PROD` profile flag)
- **Fabric**: Python scripts with `az login` auth
  - `python fabric/scripts/01_deploy_workspace.py`

### Service Principals
- **Dev mirroring SP**: `5319dcfd-60d3-4bce-9d26-7e9a6dd81503`
- **Prod mirroring SP**: `8924f20b-eb17-4713-8123-dda701e54eab`
- These are for Fabric mirroring only — Genie uses OAuth Identity Passthrough (per-user)

### RLS Implementation
- **Databricks side**: `{catalog}.security.division_filter` function using `IS_ACCOUNT_GROUP_MEMBER()`
- **Fabric side**: OneLake Security roles (e.g., `RoleCPBFinance`, `RoleCPBEquipment`)
- Row filter expression: `WHERE division = 'CPB Contractors'` (for Group-A)
- ⚠️ Databricks RLS does NOT propagate to Fabric — must configure separately
- ⚠️ Workspace Admins/Members/Contributors bypass OneLake Security — test users must be Viewers

### OAuth for Foundry Genie MCP
- Token URL: `https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token`
- Scope: `2ff814a6-3304-4ab8-85cb-cd0e6f879c1d/.default` (Azure Databricks app ID)
- Do NOT use Databricks OIDC endpoint (`/oidc/v1/token`) — Azure-managed workspaces use Entra ID

### Fabric Mirroring Common Errors
| Error | Cause | Fix |
|-------|-------|-----|
| "Invalid credentials" | Org Account + MFA | Use Service Principal |
| "Unexpected format" | Missing `EXTERNAL USE SCHEMA` grant | Grant on each schema |
| "Invalid connection credentials" (400) | Missing AzureDatabricks API permission | Add `user_impersonation` + admin consent |

## Key Documentation Files
- `modules/03-databricks-integration.md` — One-stop reference (SP setup, OAuth, RLS, mirroring, OneLake Security)
- `fabric/docs/fabric-mirroring-auth-permissions-rls-guide.md` — Deep-dive on SP + mirroring + all 11 OneLake roles
- `docs/production-deployment-guide.md` — Step-by-step prod deployment
- `databricks/docs/genie-space-reference.md` — All 5 Genie Space instructions, SQL queries, sample questions
- `databricks/docs/03-diff-databricks-integration.md` — Implementation vs spec comparison

## Coding Patterns
- Notebooks use `dbutils.widgets` for parameterisation (`catalog_name`, `customer_name`, etc.)
- Genie Spaces are created via `POST /api/2.0/genie/spaces` with `serialized_space` JSON (idempotent: PATCH if exists)
- Fabric items are created via `POST /v1/workspaces/{id}/items` (idempotent: skip if exists)
- Auth for Fabric scripts: `az account get-access-token --resource https://api.fabric.microsoft.com`
- All data generation is deterministic with seeds for reproducibility

## Testing RLS
Best demo query for equipment telemetry (Group-A should see only CPB Contractors):
```
Provide a summary of equipment telemetry metrics by division, including the total fleet count,
operational equipment, equipment under maintenance, equipment with warning status,
and equipment with critical status.
```
