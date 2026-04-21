# Fabric Workspace Deployment — CIMIC AI Workshop

Deploy and populate a Microsoft Fabric workspace (`CIMIC-ws-dev`) with all items needed for the Data Agent multi-source demo.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Fabric Workspace: CIMIC-ws-dev                                 │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐ │
│  │  Lakehouse   │  │ SQL Database │  │ Mirrored Databricks   │ │
│  │  cimic_      │  │ cimic_sqldb  │  │ Catalog (cimic)       │ │
│  │  lakehouse   │  │              │  │                       │ │
│  │ ─────────────│  │ ─────────────│  │ projects.financials   │ │
│  │ ProjectKPIs  │  │ division_    │  │ projects.milestones   │ │
│  │ SafetyKPIs   │  │   summary    │  │ equipment.telemetry   │ │
│  │ FleetKPIs    │  │ monthly_kpis │  │ equipment.maintenance │ │
│  │              │  │ mfg_kpis     │  │ safety.incidents      │ │
│  │              │  │ supplier_    │  │ safety.emissions      │ │
│  │              │  │   scorecard  │  │ procurement.materials │ │
│  └──────┬───────┘  └──────┬───────┘  │ workforce.timesheets  │ │
│         │                 │          │ quality.inspections   │ │
│  ┌──────┴───────┐         │          └───────────┬───────────┘ │
│  │ Semantic     │         │                      │             │
│  │ Model        │         │                      │             │
│  │ CIMIC_KPI_   │         │                      │             │
│  │ Model        │         │                      │             │
│  └──────┬───────┘         │                      │             │
│         │                 │                      │             │
│  ┌──────┴─────────────────┴──────────────────────┴───────────┐ │
│  │                    5 Data Agents                           │ │
│  │  • CIMIC Project Intelligence → ALL sources (mirrored+LH+SQL+model) │ │
│  │  • Projects Agent   → mirrored + lakehouse + sqldb         │ │
│  │  • Safety Agent     → mirrored + lakehouse                 │ │
│  │  • Equipment Agent  → mirrored + lakehouse                 │ │
│  │  • Procurement Agent → mirrored + sqldb                    │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

1. **Azure CLI** logged in to the CIMIC tenant:
   ```bash
   az login --tenant <YOUR_TENANT_ID>
   ```

2. **Fabric capacity** provisioned (default: `cimicws`)

3. **Python 3.9+** with `requests`:
   ```bash
   pip install requests
   ```

4. **Mirrored Databricks connection** already configured (see `databricks/docs/fabric-mirroring-auth-permissions-rls-guide.md`)

## Quick Start

```bash
# Step 1: Deploy all workspace items (Lakehouse, SQL DB, Semantic Model, Mirrored DB, 5 Agents)
python fabric/scripts/01_deploy_workspace.py \
  --workspace "my-new-workspace" \
  --capacity "my-capacity" \
  --dbx-host "adb-XXXXXXXXX.X.azuredatabricks.net" \
  --dbx-catalog "my_catalog" \
  --config-out "fabric/scripts/config.json"

# Step 2: Populate SQL Database with CIMIC summary data
python fabric/scripts/02_populate_sql_db.py --config fabric/scripts/config.json

# Step 3: Populate Lakehouse tables (run as Fabric Spark notebook OR locally)
python fabric/scripts/03_populate_lakehouse.py --config fabric/scripts/config.json
```

### Dry Run

Preview what the deploy script would create without making any changes:

```bash
python fabric/scripts/01_deploy_workspace.py \
  --workspace "my-new-workspace" \
  --capacity "my-capacity" \
  --dry-run
```

## Agent Instructions

The `fabric/agents/` directory contains 5 agent instruction files following [MS Learn best practices](https://learn.microsoft.com/en-us/fabric/data-science/concept-agents) for Fabric Data Agents:

- Each file defines the system prompt, grounding context, and example queries for one agent.
- The deploy script (`01_deploy_workspace.py`) reads these automatically when creating agents.
- Override the default directory with `--agents-dir <path>` to use custom instructions.

## Environment Variables

The scripts recognise the following environment variables as an alternative to CLI flags:

| Variable | Purpose | CLI equivalent |
|----------|---------|----------------|
| `FABRIC_WORKSPACE` | Target workspace name | `--workspace` |
| `FABRIC_CAPACITY` | Fabric capacity name | `--capacity` |
| `DBX_HOST` | Databricks workspace host | `--dbx-host` |
| `DBX_CATALOG` | Databricks Unity Catalog name | `--dbx-catalog` |
| `FABRIC_WORKSPACE_ID` | Existing workspace ID (skip creation) | — |
| `FABRIC_SQLDB_ID` | Existing SQL Database ID (skip creation) | — |
| `FABRIC_LAKEHOUSE_NAME` | Override lakehouse name | — |

CLI arguments take precedence over environment variables.

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/01_deploy_workspace.py` | Creates all Fabric items via REST API |
| `scripts/02_populate_sql_db.py` | Populates SQL Database with CIMIC data (division_summary, monthly_kpis, manufacturing_kpis, supplier_scorecard) |
| `scripts/03_populate_lakehouse.py` | Populates Lakehouse with pre-aggregated KPI tables for the semantic model |

## Notebooks (for manual use in Fabric portal)

| Notebook | Purpose |
|----------|---------|
| `notebooks/populate_sql_database.sql` | DDL + INSERT statements for SQL Database — copy-paste into Fabric SQL editor |
| `notebooks/populate_lakehouse.ipynb` | PySpark notebook — upload to Fabric and run against cimic_lakehouse |

## Post-Deployment Manual Steps

After running the scripts:

1. **Mirrored Database** → Open in Fabric portal → Configure connection (use Service Principal — see auth guide) → Start mirroring → Select all schemas
2. **SQL Database** → Open SQL editor → Run `notebooks/populate_sql_database.sql` (or use `02_populate_sql_db.py`)
3. **Each Data Agent** → Add data sources + paste instructions from `config.json`
4. **Semantic Model** → Validate connection to lakehouse in Fabric portal

## Redeployment to a Different Workspace

Use these steps to spin up a fresh copy of the demo in another workspace.

### Prerequisites

1. **Azure CLI** authenticated to your tenant:
   ```bash
   az login --tenant <TENANT_ID>
   ```
2. **Fabric capacity** provisioned and available (e.g. `my-capacity`).
3. **Python 3.9+** with required packages:
   ```bash
   pip install requests
   ```

### Step-by-step

```bash
# 1. Deploy workspace items
python fabric/scripts/01_deploy_workspace.py \
  --workspace "new-demo-workspace" \
  --capacity "my-capacity" \
  --dbx-host "adb-XXXXXXXXX.X.azuredatabricks.net" \
  --dbx-catalog "my_catalog" \
  --config-out "fabric/scripts/config.json"

# 2. Populate SQL Database
python fabric/scripts/02_populate_sql_db.py --config fabric/scripts/config.json

# 3. Populate Lakehouse
python fabric/scripts/03_populate_lakehouse.py --config fabric/scripts/config.json
```

You can also override defaults via environment variables instead of CLI args:

```bash
export FABRIC_WORKSPACE="new-demo-workspace"
export FABRIC_CAPACITY="my-capacity"
export DBX_HOST="adb-XXXXXXXXX.X.azuredatabricks.net"
export DBX_CATALOG="my_catalog"
python fabric/scripts/01_deploy_workspace.py --config-out "fabric/scripts/config.json"
```

### Post-deployment manual steps

After the scripts complete, finish setup in the Fabric portal:

1. **Mirrored Database** → Open → Configure connection (Service Principal — see auth guide) → Start mirroring → Select all schemas.
2. **Each Data Agent** → Add data sources and wire them to the correct lakehouse / SQL DB / mirrored catalog items created in the new workspace.
3. **Semantic Model** → Validate the lakehouse connection in the portal.

## Data Agent Demo Flow

### Single-Source Demo (mirrors Genie Spaces 1:1)
Ask the **Projects Agent**: *"Show me all red-status projects by division"*
→ Queries only `mirrored_catalog:projects.financials`

### Multi-Source Demo (Data Agent value-add)
Ask the **CIMIC Project Intelligence** agent: *"Give me a portfolio health summary with safety metrics and fleet status"*
→ Queries `semantic_model:CIMIC_KPI_Model` + `lakehouse:cimic_lakehouse` + `sql_database:cimic_sqldb`
→ **This is impossible in a single Genie Space** — demonstrates the key Data Agent advantage

See the full comparison below.

## Data Agent vs Genie — Value-Add

| Feature | Databricks Genie | Fabric Data Agent |
|---------|-----------------|-------------------|
| **Data sources** | Unity Catalog tables only | Mirrored catalog + SQL Database + Semantic Model + Lakehouse |
| **Multi-source queries** | ❌ Single workspace | ✅ Cross-source in one agent |
| **Power BI integration** | Manual embed | Native — same semantic model |
| **RLS propagation** | Auto (per-user OAuth) | Must redefine in Fabric (OneLake Security) |
| **No Databricks login needed** | ❌ | ✅ Users only need Fabric access |
| **Cost model** | DBU consumption | Fabric CU (capacity-based) |

## Related Documentation

- [Fabric Mirroring Auth & RLS Guide](docs/fabric-mirroring-auth-permissions-rls-guide.md) — Service Principal setup, OneLake Security, RLS testing
- [Agent Instructions](agents/) — Full agent instructions per domain
- [Databricks Permissions Guide](../databricks/docs/databricks-permissions-guide.md) — Unity Catalog + Genie + Workspace permissions
