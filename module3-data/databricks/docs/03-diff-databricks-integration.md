# Module 03 -- Databricks Integration: Implementation Diff

This document compares our implementation against the specification in
`modules/03-databricks-integration.md` and explains all deviations.

## Overview

| Aspect | Module 03 Spec | Our Implementation | Notes |
|--------|---------------|-------------------|-------|
| Catalog | `cimic` | `cimic` ✅ | Exact match |
| Tables | 4 (financials, equipment_telemetry, incidents, materials) | 4 ✅ | Exact column schemas match |
| Data volume | 37 inline rows | 6,348 rows (48+5000+1000+300) | Much richer for Genie |
| Storage | Not specified | Managed Delta (all tables) | External ADLS configurable via `external_storage_path` |
| Genie Space | Via MCP Server | Via Genie API v2 (serialized_space) | MCP requires workspace preview toggle |
| Genie Spaces count | 1 (all-in-one) | 5 (1 all-in-one + 4 domain) | Domain spaces for focused agents |
| RLS | division_filter function + IS_ACCOUNT_GROUP_MEMBER | ✅ Implemented (off by default) | Requires Entra ID groups |
| RLS Group Naming | `{customer}-Division-*` | `{customer}-Division-*` (default) or `Group-*` (generic) ✅ | Aligned with spec |
| Table RBAC | Not specified | Automated GRANT/REVOKE via `apply_grants` widget | Extends spec |
| Column Masking | Optional mask_budget | ✅ Implemented via `apply_column_mask` widget | Extends spec |
| OAuth | Identity Passthrough (per-user) | PAT for automation, OAuth for manual | Workshop-specific |
| Deployment | Not specified | DABS (`databricks bundle`) — 2 jobs | Fully parameterised |
| Fabric Data Agents | Not specified (portal-only) | 5 agents (1 cross-domain + 4 single-source) | Scripted deployment |
| Fabric Deployment | Manual (portal) | 3 Python scripts + config.json | Idempotent, dry-run capable |

## DABS Pipeline Structure

The spec doesn't define deployment pipelines. Our implementation uses two separate DABS jobs
in `resources/module03_jobs.yml`:

| Job | Purpose | Tasks | Key Parameters |
|-----|---------|-------|----------------|
| `module03_data_setup` | Schema + data + RLS | 3: `create_schema` → `generate_data` + `configure_rls` | `catalog_name`, `customer_name`, `apply_row_filter` |
| `module03_genie_spaces` | Genie Space creation | 2: `setup_genie` → `domain_genie_spaces` | `catalog_name`, `customer_name`, `warehouse_name` |

**Why two jobs?** Data setup and Genie creation have different lifecycles. You can re-run
data generation without touching Genie Spaces, and vice versa. The jobs share the same
DABS variables but run independently.

**Task dependency graph:**
```
module03_data_setup:
  create_schema ──► generate_data
                └──► configure_rls

module03_genie_spaces:
  setup_genie (all-in-one) ──► domain_genie_spaces (4 domain spaces)
```

## Section-by-Section Comparison

### 3.3.0 -- Data Setup

**Spec**: Inline SQL with 37 rows across 4 tables.

**Ours**: Python notebooks generating 6,348 rows with realistic CIMIC data:
- `financials`: 48 projects with full EVM (SPI, CPI, cost variance), RAG status, 4 divisions
- `equipment_telemetry`: 5,000 IoT readings with status distribution (80% operational, 10% warning, 5% critical, 5% maintenance)
- `incidents`: 1,000 safety records with severity weighting (45% minor, 30% moderate, 18% serious, 7% critical)
- `materials`: 300 procurement records across 10 categories with 30+ suppliers

**Why the deviation**: 37 rows is too thin for Genie SQL generation. The AI needs statistical
patterns to produce meaningful answers. 1000+ rows per table is the minimum recommended.

### 3.3.1 -- Genie Space

**Spec**: Create via MCP Server endpoint `/api/2.0/mcp/genie/<space_id>` with workspace toggle
"Managed MCP Servers" enabled.

**Ours**: Created via Genie API v2 POST `/api/2.0/genie/spaces` with `serialized_space` proto.
Includes:
- 4 data sources with column configs and entity matching
- 8 example question SQLs
- 3 join specs (division-based cross-domain joins)
- 10 curated sample questions
- Text instructions with CIMIC domain knowledge

**MCP Server integration**: The MCP endpoint requires the "Managed MCP Servers" workspace
preview feature. Once enabled, any Genie Space (including ours) can be accessed via:
```
https://{workspace}/api/2.0/mcp/genie/{space_id}
```
This is configured in Foundry (Module 03 section 3.3.1) as a tool connection.

### 3.3.2 -- OAuth Identity Passthrough

**Spec**: Configure per-user OAuth so each Foundry user's Entra ID identity flows through
to Databricks, enabling RLS per user.

**Ours**: Automation uses PAT (stored in `.env`). OAuth is a Foundry-side configuration.
Our RLS functions are ready to work with OAuth once configured.

**Manual OAuth fallback config** is now documented in the main module file:
`modules/03-databricks-integration.md` → section 3.3.2 → "Fallback: Manual OAuth Configuration"

Key values:
- Token URL: `https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token`
- Scope: `2ff814a6-3304-4ab8-85cb-cd0e6f879c1d/.default`
- ⚠️ Do NOT use the Databricks OIDC endpoint (`/oidc/v1/token`) — it doesn't work for Azure-managed workspaces

### 3.3.5 -- Row-Level Security

**Spec**: `division_filter` function using `IS_ACCOUNT_GROUP_MEMBER()` with groups:
- `{customer}-Division-CPB`
- `{customer}-Division-Thiess`
- `{customer}-Division-Sedgman`
- `{customer}-Division-Executives`

**Ours**: ✅ Exact match. Function created in `{catalog}.security.division_filter`.
Row filters configured for `financials`, `equipment_telemetry`, and `incidents`.

**Default state**: Row filters are **off** by default (`apply_row_filter=no`) because
the Entra ID groups don't exist yet. Set `apply_row_filter=yes` in the DABS job after
creating the groups.

**Updates:**
- Group naming now aligned with spec (default: `{customer}-Division-*`)
- Table-level grants automated via `apply_grants` widget — run with `apply_grants=yes` to apply GRANT/REVOKE on schemas
- Column mask automated via `apply_column_mask` widget — run with `apply_column_mask=yes` to apply `mask_budget` on `financials.budget_aud`
- See [rls-demo-guide.md](rls-demo-guide.md) for a full demo walkthrough of RLS, column masking, and table-level RBAC

### Column Schemas

All columns match Module 03's exact specification:

| Table | Module 03 Columns | Our Columns | Match |
|-------|------------------|-------------|-------|
| financials | project_id, project_name, division, client, project_type, state, budget_aud, actual_cost_aud, earned_value_aud, planned_value_aud, cost_variance_pct, spi, cpi, status, start_date, planned_completion, reporting_period, project_manager | ✅ Exact | ✅ |
| equipment_telemetry | equipment_id, equipment_type, site_name, division, engine_temp_celsius, fuel_level_pct, operating_hours, maintenance_due_date, status, reading_timestamp | ✅ Exact | ✅ |
| incidents | incident_id, incident_date, site_name, division, incident_type, severity, description, injuries, lost_time_days, root_cause, corrective_action, status | ✅ Exact | ✅ |
| materials | material_id, material_name, category, supplier, unit_price_aud, unit, lead_time_days, last_order_date, last_order_qty, price_trend, availability | ✅ Exact | ✅ |

## Additional Features (Not in Module 03)

1. **Parameterised notebooks**: Change `customer_name` to rebrand for any customer
2. **DABS deployment**: Two-job structure (see above)
3. **Multi-environment**: dev/staging/production targets in `databricks.yml`
4. **5 Genie Spaces**: 1 all-in-one + 4 domain-specific (Safety, Equipment, Procurement, Projects)

## Fabric Data Agents

The spec describes Fabric Data Agents only in the context of the portal UI (Module 03 section
3.4). Our implementation scripts the creation of 6 Data Agents via the Fabric REST API.

### Agent Inventory

| # | Agent | Data Source(s) | Mirrors Genie Space? | Persona |
|---|-------|---------------|---------------------|---------|
| 1 | Project Intelligence | All 4 mirrored tables | ✅ All-in-one Genie Space | Cross-domain operations manager |
| 2 | Safety & Compliance | Mirrored `safety.incidents` | ✅ Safety Genie Space | HSE officer |
| 3 | Equipment & Fleet | Mirrored `equipment.equipment_telemetry` | ✅ Equipment Genie Space | Fleet manager |
| 4 | Procurement | Mirrored `procurement.materials` | ✅ Procurement Genie Space | Procurement lead |
| 5 | Projects | Mirrored `projects.financials` | ✅ Projects Genie Space | Project controller |

### Genie Space ↔ Data Agent Mapping

The 5 agents are **1:1 mirrors** of the Databricks Genie Spaces. Same data,
same domain focus, different query engine. This enables **side-by-side comparison** of
Databricks Genie vs Fabric Data Agents for the same questions.

### Use Cases for Fabric Data Agents

| Use Case | How It Works |
|----------|-------------|
| **Mirrored data source** | Domain agents query the same Databricks data via Fabric's mirrored catalog SQL endpoint |
| **Side-by-side comparison** | Same questions asked to both Genie Space (via MCP) and Data Agent — compare NL-to-SQL quality |
| **Enterprise reporting** | Data Agents feed into Power BI dashboards and Fabric notebooks |

### Agent Instruction Files

All 5 agents have instruction files in `fabric/agents/`:

```
fabric/agents/
├── project-intelligence.md    # Cross-domain (all 4 tables)
├── projects.md                # Project finance domain
├── safety.md                  # HSE domain
├── equipment.md               # Fleet domain
├── procurement.md             # Procurement domain
└── README.md                  # Setup guide
```

Each file contains three sections for the Fabric Data Agent config UI:
1. **Agent Instructions** — persona, terminology, formatting rules
2. **Data Source Instructions** — schema-specific column descriptions, joins, thresholds
3. **Example Questions** — 5–8 questions demonstrating expected query patterns

The deploy script (`fabric/scripts/01_deploy_workspace.py`) reads these files and provisions
agents via the Fabric REST API.

## Redeployability

Both Databricks and Fabric sides are designed for full teardown-and-rebuild.

### Databricks

| Mechanism | Detail |
|-----------|--------|
| **DABS targets** | `databricks.yml` defines dev/staging/production targets with per-environment variables |
| **Parameterised notebooks** | All notebooks accept `catalog_name`, `customer_name`, etc. via `base_parameters` |
| **env.example** | Template file maps to DABS variables — copy to `env.dev`, fill in values |
| **Idempotent** | Schema/table creation uses `CREATE IF NOT EXISTS`; Genie Spaces are recreated |

```bash
# Full redeploy (Databricks)
databricks bundle validate -t dev
databricks bundle deploy -t dev
databricks bundle run module03_data_setup -t dev
databricks bundle run module03_genie_spaces -t dev
```

### Fabric

| Mechanism | Detail |
|-----------|--------|
| **CLI args** | All 3 scripts accept `--workspace`, `--capacity`, `--dbx-host`, `--dbx-catalog` |
| **config.json** | `01_deploy_workspace.py` writes item IDs; subsequent scripts read them |
| **Idempotent creation** | Scripts check for existing items before creating (skip-if-exists) |
| **Dry-run mode** | `01_deploy_workspace.py --dry-run` prints what would be created without making API calls |

```bash
# Full redeploy (Fabric)
az login --tenant <tenant_id>
python fabric/scripts/01_deploy_workspace.py --workspace "CIMIC-ws-dev" --capacity "cimicws"
python fabric/scripts/02_populate_sql_db.py
python fabric/scripts/03_populate_lakehouse.py
```

### End-to-End Redeploy

For a complete environment rebuild (both platforms):

```bash
# 1. Databricks — data + Genie Spaces
databricks bundle deploy -t dev
databricks bundle run module03_data_setup -t dev
databricks bundle run module03_genie_spaces -t dev

# 2. Fabric — workspace + agents + data population
#    (run after Databricks so mirrored catalog has data)
python fabric/scripts/01_deploy_workspace.py --workspace "CIMIC-ws-dev" --capacity "cimicws"
python fabric/scripts/02_populate_sql_db.py
python fabric/scripts/03_populate_lakehouse.py
```

## Data Governance Summary

### Enforcement by Platform

| Security Layer | Genie (Databricks) | Data Agent (Fabric) | Status |
|---------------|--------------------|--------------------|--------|
| Row Filters | Unity Catalog `division_filter` | OneLake Security roles or T-SQL policies | ✅ Databricks / 🔮 Fabric (future) |
| Column Masks | UC `mask_budget` function | Not yet supported on mirrored data | ✅ Databricks / ❌ Fabric |
| Table RBAC | UC GRANT/REVOKE | OneLake Security object-level | ✅ Databricks / 🔮 Fabric (future) |
| Identity | OAuth passthrough (per-user) | Fabric workspace identity (per-user) | ✅ Both |
| Groups | Entra ID → SCIM sync | Entra ID (native) | ✅ Both |

**Fabric-side RLS is future work.** OneLake Security is in preview and not yet enforced on
mirrored Databricks data. Until then, Databricks-side governance (via Genie + Unity Catalog)
is the primary enforcement mechanism.

Both platforms share the same Entra ID groups — the governance *policy* is defined once, but
each platform enforces it using its native security model.

👉 See [rls-demo-guide.md](rls-demo-guide.md) for a step-by-step demo script covering RLS,
column masking, and table-level RBAC through Genie Spaces.

## Known Gaps

1. **MCP Server toggle**: Requires workspace admin to enable "Managed MCP Servers" preview
2. **Entra ID groups**: Must be created manually and synced to Databricks via SCIM
3. **OAuth Identity Passthrough**: Foundry-side configuration (see Module 03 section 3.3.2)
4. **Benchmarks**: Created in Genie Space but evaluation runs are UI-only (no API endpoint)
5. **Fabric mirroring setup**: Mirrored DB creation is scripted but the initial Databricks ↔ Fabric connection must be configured manually in the Fabric portal
6. **Data Agent API**: Fabric Data Agent creation via REST API is in preview — some fields may change
7. **Agent instruction sync**: If Genie Space instructions are updated, the corresponding Fabric agent instructions must be updated manually (no automated sync)
