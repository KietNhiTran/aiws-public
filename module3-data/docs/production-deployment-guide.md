# CIMIC AI Workshop — Production Deployment Guide

> **Audience**: Workshop admin deploying to the **prod** Databricks + Fabric environment.
> **Time**: ~45–60 min (excluding data sync wait times).

---

## Prerequisites

| Requirement | Details |
|-------------|---------|
| **Azure CLI** | `az login --tenant <TENANT_ID>` — logged in with Owner/Contributor on `cimic-aiws-prod-rg` |
| **Databricks CLI** | `databricks auth login --host https://adb-7405609499683390.10.azuredatabricks.net` |
| **Python 3.9+** | With `requests` installed (`pip install requests`) |
| **Fabric capacity** | An active F-SKU capacity (e.g. `cimicws`) |
| **Entra ID groups** | `Group-A`, `Group-B`, `Group-C`, `Group-Executives` synced to Databricks via SCIM |
| **Git branch** | `feature/sg-dbx` checked out and up to date |

---

## Part 1 — Databricks (Prod Workspace)

### 1.1 Verify prod target config

```bash
cd databricks/
cat databricks.yml   # Check targets.production section
```

Prod target settings:
- **Host**: `https://adb-7405609499683390.10.azuredatabricks.net`
- **Catalog**: `cimic_prod`
- **Cluster**: `0420-031307-t5q63cm0`
- **Customer**: `CIMIC`

### 1.2 Deploy the bundle

```bash
databricks bundle deploy --target production
```

This uploads all notebooks and creates/updates the jobs. Verify:

```bash
databricks bundle summary --target production
```

You should see 4 jobs deployed:

| Job | Purpose |
|-----|---------|
| `manufacturing_setup` | Full setup: create schemas → generate data → configure RLS |
| `module03_data_setup` | Module 03: create schemas → generate data → RLS → Fabric tables |
| `module03_genie_spaces` | Create all 5 Genie Spaces |
| `supply_chain_pipeline` | Medallion pipeline: bronze → silver → gold |

### 1.3 Run data setup (create catalog + generate data + RLS)

Run the **module03_data_setup** job — it creates the catalog, schemas, tables, data, RLS, and mirror views:

```bash
# Get the JOB_ID from the summary above, then:
databricks jobs run-now <MODULE03_DATA_SETUP_JOB_ID>

# Or from the Databricks UI:
# Jobs → [prod] Module 03 - CIMIC Data Setup → Run now
```

**Tasks executed in order:**

| # | Task | What it does |
|---|------|-------------|
| 1 | `create_schema` | Creates `cimic_prod` catalog with 4 schemas + tables |
| 2 | `generate_data` | Populates all 4 tables with sample data |
| 3 | `configure_rls` | Creates `security.division_filter()`, mirror views, applies row filters |
| 4 | `create_fabric_tables` | Creates `_f` suffix tables for Fabric mirroring compatibility |

### 1.4 Create / verify Entra groups in Databricks

```bash
# Check if groups already exist
databricks groups list | grep Group-

# If missing, create them:
databricks groups create --group-name "Group-A"
databricks groups create --group-name "Group-B"
databricks groups create --group-name "Group-C"
databricks groups create --group-name "Group-Executives"
```

Add users to groups:
```bash
# Find user ID
databricks users list --filter 'displayName co "Vinoth"'

# Add to group (replace IDs)
databricks groups patch <GROUP_ID> --json '{
  "Operations": [{"op": "add", "value": {"members": [{"value": "<USER_ID>"}]}}]
}'
```

**Group → Division mapping:**

| Group | Division | Access |
|-------|----------|--------|
| `Group-A` | CPB Contractors | Own division data only |
| `Group-B` | Thiess | Own division data only |
| `Group-C` | Sedgman | Own division data only |
| `Group-Executives` | ALL | All divisions |

### 1.5 Verify RLS is working

```sql
-- Check the function exists and uses correct group names:
DESCRIBE FUNCTION EXTENDED cimic_prod.security.division_filter;

-- Should show: IS_MEMBER('Group-Executives') OR IS_MEMBER('admins')
--   OR (division_value = 'CPB Contractors' AND IS_MEMBER('Group-A'))
--   OR (division_value = 'Thiess' AND IS_MEMBER('Group-B'))
--   OR (division_value = 'Sedgman' AND IS_MEMBER('Group-C'))

-- Check row filters are applied:
DESCRIBE EXTENDED cimic_prod.projects.financials;
-- Look for: row_filter → cimic_prod.security.division_filter

-- Test as a Group-A member:
SELECT DISTINCT division FROM cimic_prod.projects.financials;
-- Should return ONLY: 'CPB Contractors'
```

> ⚠️ **Workspace admins bypass row filters.** Remove demo users from the `admins` group for RLS to work.

### 1.6 Create Genie Spaces

```bash
databricks jobs run-now <MODULE03_GENIE_SPACES_JOB_ID>
```

This creates 5 Genie Spaces:

| Space | Tables | Persona |
|-------|--------|---------|
| **CIMIC Project Intelligence** | All 4 tables | Cross-domain analyst |
| **Safety Agent** | `safety.incidents` | HSE manager |
| **Equipment Agent** | `equipment.equipment_telemetry` | Fleet ops manager |
| **Procurement Agent** | `procurement.materials` | Procurement director |
| **Projects Agent** | `projects.financials` | Project controls analyst |

> **Tip:** For the full list of instructions, example queries, and sample questions for each space, see [`databricks/docs/genie-space-reference.md`](../databricks/docs/genie-space-reference.md).

### 1.7 (Optional) Run the supply chain pipeline

```bash
databricks jobs run-now <SUPPLY_CHAIN_JOB_ID>
```

Creates medallion architecture: source → bronze → silver → gold.

---

## Part 2 — Fabric (Prod Workspace)

### 2.1 Deploy Fabric workspace

```bash
cd ..  # back to repo root

python fabric/scripts/01_deploy_workspace.py \
  --workspace "ws_cimic_aiws_prod" \
  --capacity "cimicws" \
  --dbx-host "adb-7405609499683390.10.azuredatabricks.net" \
  --dbx-catalog "cimic_prod" \
  --config-out "fabric/scripts/config-prod.json"
```

This creates:

| Item | Name |
|------|------|
| Lakehouse | `cimic_lakehouse` |
| SQL Database | `cimic_sqldb` |
| Semantic Model | `CIMIC_KPI_Model` (may need manual config) |
| Mirrored Database | `Mirror_cimic_prod` (likely needs manual setup — see §2.4) |
| **5 Data Agents** | CIMIC Project Intelligence, Projects, Safety, Equipment, Procurement |
| **2 Notebooks** | `populate_lakehouse`, `populate_sql_database` |

### 2.2 Populate SQL Database

```bash
python fabric/scripts/02_populate_sql_db.py
```

Creates tables: `division_summary`, `monthly_kpis`, `manufacturing_kpis`, `supplier_scorecard`.

### 2.3 Populate Lakehouse

```bash
python fabric/scripts/03_populate_lakehouse.py
```

Or run the `populate_lakehouse` notebook in the Fabric portal.

Creates tables: `ProjectKPIs`, `SafetyKPIs`, `FleetKPIs`.

### 2.4 Configure Mirrored Databricks Catalog (Manual)

> The mirrored catalog typically requires manual portal setup.

1. **Fabric Portal** → workspace → **+ New** → **Mirrored Database** → **Azure Databricks**
2. **Connection**: `adb-7405609499683390.10.azuredatabricks.net`
3. **Auth**: Org Account (recommended) or Service Principal
4. **Catalog**: `cimic_prod`
5. **Tables**: Select all 4:
   - `projects.financials`
   - `safety.incidents`
   - `equipment.equipment_telemetry`
   - `procurement.materials`
6. **Start mirroring** → Wait for initial sync (5–15 min)

> ⚠️ Tables with row filters may fail to mirror ("Resilience check failed"). If so, mirror the `v_*_mirror` views instead, or start mirroring BEFORE running `configure_rls`.

Full auth guide: `fabric/docs/fabric-mirroring-auth-permissions-rls-guide.md`

### 2.5 Configure Data Agent sources (Portal)

For each agent, open it in the Fabric portal and add data sources:

| Agent | Data Sources to Connect |
|-------|------------------------|
| **CIMIC Project Intelligence** | Mirrored DB (all 4 tables) + Lakehouse + SQL DB + Semantic Model |
| **Projects Agent** | Mirrored DB (`financials`) + Lakehouse (`ProjectKPIs`) + SQL DB (`monthly_kpis`) |
| **Safety Agent** | Mirrored DB (`incidents`) + Lakehouse (`SafetyKPIs`) |
| **Equipment Agent** | Mirrored DB (`equipment_telemetry`) + Lakehouse (`FleetKPIs`) |
| **Procurement Agent** | Mirrored DB (`materials`) + SQL DB (`supplier_scorecard`) |

### 2.6 Paste agent + data source instructions

Instructions are saved in `fabric/scripts/config-prod.json` (generated in §2.1) and also in the `fabric/agents/*.md` files.

For each agent:
1. Open agent → **Settings** → **Agent Instructions** → paste from config JSON `instructions` field
2. For each data source → **Data Source Instructions** → paste from the corresponding section in the `.md` file
3. **Example Questions** → add from `example_questions` in config JSON

---

## Part 3 — OneLake Security RLS (Fabric Side)

> Databricks UC row filters do **NOT** propagate to Fabric. You must configure OneLake Security separately on the Lakehouse.

### 3.1 Create Lakehouse roles

**Lakehouse** → **Manage OneLake Security** → **+ New Role**

#### Division roles (9 roles — one per division × table)

| Role Name | Table | Row Security SQL |
|-----------|-------|-----------------|
| `RoleCPBFinance` | `financials` | `SELECT * FROM financials WHERE division = 'CPB Contractors'` |
| `RoleCPBSafety` | `incidents` | `SELECT * FROM incidents WHERE division = 'CPB Contractors'` |
| `RoleCPBEquipment` | `equipment_telemetry` | `SELECT * FROM equipment_telemetry WHERE division = 'CPB Contractors'` |
| `RoleThiessFinance` | `financials` | `SELECT * FROM financials WHERE division = 'Thiess'` |
| `RoleThiessSafety` | `incidents` | `SELECT * FROM incidents WHERE division = 'Thiess'` |
| `RoleThiessEquipment` | `equipment_telemetry` | `SELECT * FROM equipment_telemetry WHERE division = 'Thiess'` |
| `RoleSedgmanFinance` | `financials` | `SELECT * FROM financials WHERE division = 'Sedgman'` |
| `RoleSedgmanSafety` | `incidents` | `SELECT * FROM incidents WHERE division = 'Sedgman'` |
| `RoleSedgmanEquipment` | `equipment_telemetry` | `SELECT * FROM equipment_telemetry WHERE division = 'Sedgman'` |

#### Cross-division roles (2 roles)

| Role Name | Tables | Row Security SQL |
|-----------|--------|-----------------|
| `RoleExecutivesAll` | `financials`, `incidents`, `equipment_telemetry` | *(no row filter — sees all rows)* |
| `RoleProcurementAll` | `materials` | *(no row filter — sees all rows)* |

### 3.2 Assign Entra groups to roles

| Group | Assign to Roles |
|-------|----------------|
| `Group-A` | `RoleCPBFinance`, `RoleCPBSafety`, `RoleCPBEquipment`, `RoleProcurementAll` |
| `Group-B` | `RoleThiessFinance`, `RoleThiessSafety`, `RoleThiessEquipment`, `RoleProcurementAll` |
| `Group-C` | `RoleSedgmanFinance`, `RoleSedgmanSafety`, `RoleSedgmanEquipment`, `RoleProcurementAll` |
| `Group-Executives` | `RoleExecutivesAll`, `RoleProcurementAll` |

### 3.3 Important notes

- **Workspace Admins/Members/Contributors bypass OneLake Security** — only **Viewers** are restricted by RLS
- Demo users who should see filtered data must be assigned the workspace **Viewer** role
- SQL syntax: `SELECT * FROM <table> WHERE <predicate>` (max 1000 chars)
- Supported operators: `=`, `<>`, `>`, `<`, `IN`, `AND`, `OR`, `NOT`

---

## Part 4 — Verification Checklist

### Databricks ✓

- [ ] `databricks bundle summary --target production` → 4 jobs listed
- [ ] `cimic_prod` catalog exists with schemas: `projects`, `safety`, `equipment`, `procurement`, `security`
- [ ] Tables populated: `SELECT COUNT(*) FROM cimic_prod.projects.financials` returns data
- [ ] `cimic_prod.security.division_filter` uses `Group-A/B/C/Executives`
- [ ] Row filters applied: `DESCRIBE EXTENDED cimic_prod.projects.financials` shows `row_filter`
- [ ] Mirror views exist: `v_financials_mirror`, `v_incidents_mirror`
- [ ] 5 Genie Spaces created and accessible
- [ ] RLS test: non-admin Group-A user sees only CPB Contractors data
- [ ] Groups exist with correct members

### Fabric ✓

- [ ] Workspace `ws_cimic_aiws_prod` exists with all items
- [ ] Lakehouse has tables: `ProjectKPIs`, `SafetyKPIs`, `FleetKPIs`
- [ ] SQL DB has tables: `division_summary`, `monthly_kpis`, `manufacturing_kpis`, `supplier_scorecard`
- [ ] Mirrored DB syncing all 4 Databricks tables
- [ ] 5 Data Agents with correct names, sources connected, instructions pasted
- [ ] OneLake Security: 11 roles created
- [ ] OneLake Security: Groups assigned to roles
- [ ] Test: Viewer in Group-A sees only CPB data through Data Agent

---

## Quick Reference — Full Command Sequence

```bash
# ── Databricks ──────────────────────────────────────
cd databricks/

# 1. Deploy bundle
databricks bundle deploy --target production
databricks bundle summary --target production       # note the job IDs

# 2. Create catalog + data + RLS
databricks jobs run-now <MODULE03_DATA_SETUP_JOB_ID>

# 3. Create Genie Spaces
databricks jobs run-now <MODULE03_GENIE_SPACES_JOB_ID>

# ── Fabric ──────────────────────────────────────────
cd ..

# 4. Deploy workspace + agents
python fabric/scripts/01_deploy_workspace.py \
  --workspace "ws_cimic_aiws_prod" \
  --dbx-host "adb-7405609499683390.10.azuredatabricks.net" \
  --dbx-catalog "cimic_prod" \
  --config-out "fabric/scripts/config-prod.json"

# 5. Populate data
python fabric/scripts/02_populate_sql_db.py
python fabric/scripts/03_populate_lakehouse.py

# ── Manual steps (Fabric portal) ───────────────────
# 6. Configure mirrored Databricks catalog (§2.4)
# 7. Add data sources to each agent (§2.5)
# 8. Paste agent + data source instructions (§2.6)
# 9. Create OneLake Security roles (§3.1)
# 10. Assign groups to roles (§3.2)
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| User sees all data despite RLS | User is in `admins` group — remove them; admins bypass row filters |
| Mirroring fails "Resilience check" | Table has row filters. Mirror `v_*_mirror` views or mirror before applying filters |
| `division_filter` wrong group names | Recreate function with `Group-A/B/C/Executives` (see `04_configure_rls.py`) |
| Genie can't query tables | Grant `USE CATALOG`, `USE SCHEMA`, `SELECT` to groups |
| Fabric agent shows no data | Connect data sources in portal; verify mirroring is active |
| OneLake RLS not filtering | User must be workspace **Viewer** — Admins/Members/Contributors bypass |
| `bundle deploy` auth error | Run `databricks auth login --host https://adb-7405609499683390.10.azuredatabricks.net` |
| Semantic Model creation fails | Create manually in portal: New → Semantic Model → connect to Lakehouse |
