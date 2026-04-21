# Module 3: Integrate Azure Databricks as Data Source

**Duration:** 90 minutes  
**Objective:** Connect your Foundry agent to Azure Databricks using the two most meaningful integration approaches — **MCP-based Genie** (zero-code, direct) and **Fabric mirroring** (enterprise data layer).

---

## 3.1 Integration Options Overview

There are **two recommended patterns** for connecting Microsoft Foundry agents to Databricks data. Both are low-code and align with the Foundry Portal experience from Module 2.

### Comparison Matrix

| # | Pattern | Complexity | Code Required | Data Freshness | Auth Model | Best For |
|---|---------|-----------|---------------|----------------|------------|----------|
| 1 | **Databricks Genie via MCP** | Very Low | None | Real-time | OAuth per-user (Entra ID) | Ad-hoc analytics, NL-to-SQL |
| 2 | **Fabric Mirroring + Data Agent** | Low–Medium | None (portal) | Near-real-time (seconds–minutes) | Fabric workspace permissions | Enterprise reporting, Power BI, cross-platform analytics |

### Why These Two?

Other approaches (Custom Function Tools, Azure AI Search indexing, File Export) required **middleware code**, **Azure Function deployments**, or **batch export pipelines**. The landscape has changed:

- **Databricks now provides managed MCP servers** — Genie is exposed as a ready-to-use MCP endpoint that plugs directly into Foundry's tool catalog. No wrapper code needed.
- **Microsoft Fabric now mirrors Unity Catalog natively** — metadata-only sync (no data movement), giving Fabric full read access to Databricks tables. Fabric Data Agents can then query this mirrored data and connect to Foundry.

Both approaches are **zero-code** from the Foundry side and represent the current best practice as of April 2026.

---

## 3.2 Option 1: Databricks Genie via MCP (Recommended Primary)

**Pattern:** Foundry Agent → MCP Tool (built-in) → Databricks Managed MCP Server → Genie Space → Unity Catalog data

> **Status:** Public Preview (both Databricks and Foundry sides)

### How It Works

```
User: "What's the average cost overrun for road projects?"
    │
    ▼
Foundry Agent (recognises Genie MCP tool is relevant)
    │
    ▼ (MCP protocol — automatic)
Databricks Managed MCP Server
    │  https://<workspace>/api/2.0/mcp/genie/<space_id>
    ▼
Genie (NL → SQL → execute against SQL Warehouse → result)
    │
    ▼ (result returned via MCP)
Foundry Agent (presents answer to user)
```

### What is Genie?

Databricks **Genie** is a compound AI system that translates natural language questions into SQL queries against Unity Catalog tables. It uses:

- Table/column metadata and descriptions from Unity Catalog
- Author-curated instructions and terminology (a "knowledge store")
- Sample SQL queries for common patterns
- A **Pro or Serverless SQL Warehouse** to execute generated queries

All generated queries are **read-only**. Unity Catalog permissions (including row filters and column masks) are always enforced.

### What is MCP?

The **Model Context Protocol (MCP)** is an open standard that defines how applications provide tools and data to LLMs. Databricks exposes several **managed MCP servers** out of the box:

| Server | Endpoint | Purpose |
|--------|----------|---------|
| **Genie** | `https://<workspace>/api/2.0/mcp/genie/<space_id>` | NL-to-SQL on structured data |
| **Vector Search** | `https://<workspace>/api/2.0/mcp/vector-search/<catalog>/<schema>/<index>` | Similarity search on documents |
| **SQL** | `https://<workspace>/api/2.0/mcp/sql` | AI-generated SQL (read/write) |
| **Unity Catalog Functions** | `https://<workspace>/api/2.0/mcp/functions/<catalog>/<schema>/<function>` | Run predefined SQL functions |

For this module, we use the **Genie MCP server**.

### Prerequisites

1. **Databricks workspace** with Unity Catalog enabled
2. **Managed MCP Servers** preview feature enabled in the workspace
   - Click your **username** (top-right) → **Previews** → toggle **"Managed MCP Servers"** On
3. A **Genie Space** configured with tables and instructions
4. **Pro or Serverless SQL Warehouse** attached to the Genie Space
5. **Microsoft Foundry project** (from Module 1)

> **Don't have a Databricks workspace yet?** Follow the provisioning steps below (3.2.P) before proceeding.

### 3.2.P Provision Azure Databricks & Enable Prerequisites

If your Azure subscription already has a Databricks workspace with Unity Catalog, skip to **Step 3.2.0**.

#### P1 — Create an Azure Databricks Workspace

1. Open the [Azure Portal](https://portal.azure.com)
2. Click **+ Create a resource** → search for **"Azure Databricks"**
3. Click **Create** and fill in:

   | Field | Value |
   |-------|-------|
   | Subscription | Your Azure subscription |
   | Resource Group | `rg-cimic-ai-workshop` (create new or use existing) |
   | Workspace Name | `dbw-cimic-workshop` |
   | Region | **Australia East** (same region as your Foundry resource from Module 1) |
   | Pricing Tier | **Premium** (required for Unity Catalog and Genie) |

   > **Important:** Unity Catalog and Genie require the **Premium** pricing tier. The Standard tier does not support these features.

4. Click **Review + Create** → **Create**
5. Wait for deployment to complete (~3–5 minutes), then click **Go to resource**
6. Click **Launch Workspace** to open the Databricks UI

#### P2 — Verify Unity Catalog Is Enabled

Azure Databricks workspaces created after November 2023 have **Unity Catalog enabled by default** (automatic workspace assignment to an account-level metastore).

Use **one** of the following methods to confirm:

- **Method A — SQL query (easiest):** Run `SELECT CURRENT_METASTORE();` in a SQL editor or notebook. If it returns a metastore ID (e.g. `a]b1c2d3-...`), Unity Catalog is enabled.
- **Method B — Catalog Explorer:** Click the **Catalog** icon (![Data icon](https://learn.microsoft.com/azure/databricks/_static/images/product-icons/dataicon.svg)) in the left sidebar. If you can browse catalogs and schemas, Unity Catalog is active.
- **Method C — Account Console:** Log into the [Account Console](https://accounts.azuredatabricks.net) → click **Workspaces** → check the **Metastore** column for your workspace.

If no metastore is assigned:
   - Go to the [Databricks Account Console](https://accounts.azuredatabricks.net)
   - Navigate to **Catalog** → **Metastores**
   - If no metastore exists in your region, click **Create metastore**:

     | Field | Value |
     |-------|-------|
     | Name | `metastore-australiaeast` |
     | Region | Australia East |
     | ADLS Gen2 path | `abfss://<container>@<storage-account>.dfs.core.windows.net/` |

   - After creating, click **Assign to workspace** → select `dbw-cimic-workshop`

> **Tip:** If you are a new Databricks customer, Azure auto-creates a metastore and assigns it to your workspace on first launch. Verify by running `SELECT current_metastore()` in a notebook.

#### P3 — Create a SQL Warehouse

Genie requires a **Pro** or **Serverless SQL Warehouse** to execute queries.

1. In the Databricks workspace, go to **SQL Warehouses** (left sidebar)
2. Click **Create SQL warehouse**
3. Configure:

   | Field | Value |
   |-------|-------|
   | Name | `cimic-ai-agent-warehouse` |
   | Cluster size | **2X-Small** (sufficient for workshop) |
   | Type | **Serverless** (recommended — auto-starts, no idle cost) or **Pro** |
   | Auto stop | **10 minutes** (saves cost during workshop pauses) |

4. Click **Create**
5. Wait for the warehouse to show **Running** status (Serverless starts in ~10 seconds; Pro may take 2–3 minutes)

#### P4 — Enable Managed MCP Servers Preview

1. In the Databricks workspace, click your **username** in the top-right bar
2. Select **"Previews"** directly from the dropdown menu
3. Find **"Managed MCP Servers"** and toggle it **On**

> **Note:** This is a workspace-level preview feature (Public Preview). You must be a **workspace admin** to enable it. If you don't see the toggle, ask your Databricks workspace admin to enable it. After enabling, you can view your MCP servers at **Agents → MCP Servers** in the left sidebar.

After completing these steps, your Databricks environment is ready. Continue below.

---

### Step-by-Step Setup

#### 3.2.0 Prepare Sample Data in Databricks

Before creating the Genie Space, load the CIMIC demo datasets that Genie will query. Run these SQL statements in a Databricks notebook:

```sql
-- Create catalog and schema
CREATE CATALOG IF NOT EXISTS cimic;
CREATE SCHEMA IF NOT EXISTS cimic.projects;
CREATE SCHEMA IF NOT EXISTS cimic.equipment;
CREATE SCHEMA IF NOT EXISTS cimic.safety;
CREATE SCHEMA IF NOT EXISTS cimic.procurement;
```

**Project Financials** — budget, cost variance, EVM metrics for all CIMIC divisions:

```sql
CREATE OR REPLACE TABLE cimic.projects.financials (
    project_id STRING,
    project_name STRING,
    division STRING,
    client STRING,
    project_type STRING,
    state STRING,
    budget_aud DOUBLE,
    actual_cost_aud DOUBLE,
    earned_value_aud DOUBLE,
    planned_value_aud DOUBLE,
    cost_variance_pct DOUBLE,
    spi DOUBLE,
    cpi DOUBLE,
    status STRING,
    start_date DATE,
    planned_completion DATE,
    reporting_period DATE,
    project_manager STRING
);

INSERT INTO cimic.projects.financials VALUES
('P-2024-001', 'Sydney Metro West - Station Fit-Out', 'CPB Contractors', 'Sydney Metro Authority', 'Rail Infrastructure', 'NSW', 850000000, 792000000, 810000000, 800000000, 2.1, 1.01, 1.02, 'green', '2023-01-15', '2026-06-30', '2025-03-31', 'Sarah Johnson'),
('P-2024-002', 'Inland Rail - Narrabri to North Star', 'CPB Contractors', 'ARTC', 'Rail Infrastructure', 'NSW', 1200000000, 1150000000, 1080000000, 1100000000, -6.5, 0.98, 0.94, 'amber', '2022-06-01', '2026-12-31', '2025-03-31', 'Michael Chen'),
('P-2024-003', 'WestConnex M4-M5 Link Tunnels', 'CPB Contractors', 'Transport for NSW', 'Road/Tunnel', 'NSW', 3200000000, 3450000000, 3100000000, 3150000000, -11.3, 0.98, 0.90, 'red', '2021-03-01', '2025-12-31', '2025-03-31', 'David Park'),
('P-2024-004', 'Bowen Basin Resource Expansion', 'Thiess', 'BHP Mitsubishi Alliance', 'Contract Services', 'QLD', 650000000, 610000000, 620000000, 615000000, 1.6, 1.01, 1.02, 'green', '2023-07-01', '2027-06-30', '2025-03-31', 'Lisa Wang'),
('P-2024-005', 'Mount Pleasant Operations', 'Thiess', 'MACH Energy', 'Contract Services', 'NSW', 420000000, 445000000, 400000000, 410000000, -11.3, 0.98, 0.90, 'red', '2022-01-01', '2026-12-31', '2025-03-31', 'James Morrison'),
('P-2024-006', 'Olympic Dam Processing Plant Upgrade', 'Sedgman', 'BHP', 'Mineral Processing', 'SA', 280000000, 265000000, 270000000, 268000000, 1.9, 1.01, 1.02, 'green', '2023-09-01', '2025-09-30', '2025-03-31', 'Emma Nguyen'),
('P-2024-007', 'Melbourne Metro Tunnel', 'CPB Contractors', 'Rail Projects Victoria', 'Rail Infrastructure', 'VIC', 2800000000, 2650000000, 2700000000, 2720000000, -1.8, 0.99, 1.02, 'green', '2020-06-01', '2025-12-31', '2025-03-31', 'Robert Taylor'),
('P-2024-008', 'Carmichael Rail Network', 'Thiess', 'Adani', 'Rail Infrastructure', 'QLD', 550000000, 580000000, 520000000, 540000000, -11.5, 0.96, 0.90, 'red', '2023-03-01', '2026-03-31', '2025-03-31', 'Amanda Liu'),
('P-2024-009', 'Perth Desalination Plant Expansion', 'Sedgman', 'Water Corporation WA', 'Water Infrastructure', 'WA', 180000000, 172000000, 175000000, 174000000, 1.7, 1.01, 1.02, 'green', '2024-01-01', '2026-06-30', '2025-03-31', 'Tom Richards'),
('P-2024-010', 'Pacific Highway Upgrade - Coffs Harbour', 'CPB Contractors', 'Transport for NSW', 'Road Infrastructure', 'NSW', 950000000, 920000000, 900000000, 910000000, -2.2, 0.99, 0.98, 'green', '2022-09-01', '2026-03-31', '2025-03-31', 'Karen White');
```

**Equipment Telemetry** — heavy equipment fleet IoT sensor data:

```sql
CREATE OR REPLACE TABLE cimic.equipment.equipment_telemetry (
    equipment_id STRING,
    equipment_type STRING,
    site_name STRING,
    division STRING,
    engine_temp_celsius DOUBLE,
    fuel_level_pct DOUBLE,
    operating_hours INT,
    maintenance_due_date DATE,
    status STRING,
    reading_timestamp TIMESTAMP
);

INSERT INTO cimic.equipment.equipment_telemetry VALUES
('HT-001', 'haul_truck', 'Bowen Basin', 'Thiess', 92.5, 78.0, 12450, '2025-05-15', 'operational', '2025-04-14 08:00:00'),
('HT-002', 'haul_truck', 'Bowen Basin', 'Thiess', 110.3, 45.0, 15800, '2025-04-20', 'warning', '2025-04-14 08:00:00'),
('HT-003', 'haul_truck', 'Mount Pleasant', 'Thiess', 88.0, 92.0, 8900, '2025-06-01', 'operational', '2025-04-14 08:00:00'),
('EX-001', 'excavator', 'Bowen Basin', 'Thiess', 85.0, 65.0, 9800, '2025-05-20', 'operational', '2025-04-14 08:00:00'),
('EX-002', 'excavator', 'Mount Pleasant', 'Thiess', 115.8, 30.0, 18200, '2025-04-16', 'critical', '2025-04-14 08:00:00'),
('DR-001', 'drill', 'Bowen Basin', 'Thiess', 78.0, 88.0, 6500, '2025-07-01', 'operational', '2025-04-14 08:00:00'),
('DR-002', 'drill', 'Carmichael', 'Thiess', 95.0, 55.0, 11200, '2025-04-25', 'operational', '2025-04-14 08:00:00'),
('LD-001', 'loader', 'Olympic Dam', 'Sedgman', 82.0, 70.0, 7800, '2025-06-15', 'operational', '2025-04-14 08:00:00'),
('DZ-001', 'dozer', 'Bowen Basin', 'Thiess', 90.0, 60.0, 13500, '2025-05-01', 'operational', '2025-04-14 08:00:00'),
('HT-004', 'haul_truck', 'Carmichael', 'Thiess', 98.0, 35.0, 14200, '2025-04-18', 'warning', '2025-04-14 08:00:00');
```

> **Verify:** Run `SELECT COUNT(*) FROM cimic.projects.financials` (expect 10) and `SELECT COUNT(*) FROM cimic.equipment.equipment_telemetry` (expect 10).

**Safety Incidents** — HSE incident records across all divisions:

```sql
CREATE OR REPLACE TABLE cimic.safety.incidents (
    incident_id STRING,
    incident_date DATE,
    site_name STRING,
    division STRING,
    incident_type STRING,
    severity STRING,
    description STRING,
    injuries INT,
    lost_time_days DOUBLE,
    root_cause STRING,
    corrective_action STRING,
    status STRING
);

INSERT INTO cimic.safety.incidents VALUES
('INC-2025-001', '2025-01-15', 'Sydney Metro West', 'CPB Contractors', 'Slip/Trip/Fall', 'Minor', 'Worker tripped on unsecured cable in tunnel section B', 1, 0, 'Poor housekeeping', 'Cable management audit implemented', 'closed'),
('INC-2025-002', '2025-02-03', 'Bowen Basin', 'Thiess', 'Vehicle Interaction', 'Serious', 'Near-miss between haul truck HT-002 and light vehicle at intersection 4', 0, 0, 'Inadequate traffic management', 'Intersection redesigned with barrier separation', 'closed'),
('INC-2025-003', '2025-02-20', 'Mount Pleasant', 'Thiess', 'Equipment Failure', 'Moderate', 'Excavator EX-002 hydraulic line failure during digging operation', 0, 3.0, 'Deferred maintenance', 'Maintenance schedule reviewed and accelerated', 'closed'),
('INC-2025-004', '2025-03-08', 'Melbourne Metro Tunnel', 'CPB Contractors', 'Falling Object', 'Minor', 'Small concrete fragment fell from formwork during pour', 0, 0, 'Formwork inspection missed', 'Pre-pour checklist updated with mandatory sign-off', 'closed'),
('INC-2025-005', '2025-03-22', 'Olympic Dam', 'Sedgman', 'Chemical Exposure', 'Moderate', 'Worker exposed to processing chemical due to PPE glove tear', 1, 2.0, 'PPE degradation not detected', 'PPE inspection frequency increased to start of each shift', 'open'),
('INC-2025-006', '2025-04-01', 'Bowen Basin', 'Thiess', 'Heat Stress', 'Minor', 'Two workers reported heat stress symptoms during afternoon shift', 2, 0.5, 'Inadequate hydration breaks', 'Mandatory hydration breaks every 45 minutes when temp > 35C', 'open'),
('INC-2025-007', '2025-04-10', 'WestConnex Tunnel', 'CPB Contractors', 'Noise Exposure', 'Minor', 'Noise level exceeded 85dB in section C without adequate signage', 0, 0, 'Missing signage after equipment change', 'Noise monitoring automated with real-time alerts', 'open');
```

**Procurement Materials** — supplier pricing, lead times, availability:

```sql
CREATE OR REPLACE TABLE cimic.procurement.materials (
    material_id STRING,
    material_name STRING,
    category STRING,
    supplier STRING,
    unit_price_aud DOUBLE,
    unit STRING,
    lead_time_days INT,
    last_order_date DATE,
    last_order_qty DOUBLE,
    price_trend STRING,
    availability STRING
);

INSERT INTO cimic.procurement.materials VALUES
('MAT-001', 'Structural Steel (Grade 350)', 'Steel', 'BlueScope Steel', 2850.00, 'tonne', 21, '2025-03-15', 500, 'increasing', 'good'),
('MAT-002', 'Ready-Mix Concrete (40 MPa)', 'Concrete', 'Hanson Australia', 285.00, 'cubic_meter', 3, '2025-04-10', 2000, 'stable', 'good'),
('MAT-003', 'Diesel Fuel (Industrial Grade)', 'Fuel', 'Shell Australia', 1.85, 'litre', 1, '2025-04-12', 500000, 'increasing', 'good'),
('MAT-004', 'Reinforcement Bar (N12)', 'Steel', 'InfraBuild', 1650.00, 'tonne', 14, '2025-03-28', 800, 'stable', 'moderate'),
('MAT-005', 'Shotcrete Mix', 'Concrete', 'Sika Australia', 320.00, 'cubic_meter', 5, '2025-04-05', 1500, 'stable', 'good'),
('MAT-006', 'Explosives (ANFO)', 'Site Consumables', 'Orica', 950.00, 'tonne', 7, '2025-04-08', 200, 'stable', 'good'),
('MAT-007', 'Tunnel Liner Segments', 'Precast', 'CPB Precast Facility', 4500.00, 'segment', 28, '2025-03-01', 120, 'stable', 'limited'),
('MAT-008', 'Geotextile Membrane', 'Geosynthetics', 'Geofabrics Australasia', 12.50, 'square_meter', 10, '2025-03-20', 50000, 'decreasing', 'good'),
('MAT-009', 'Caterpillar GET (Ground Engaging Tools)', 'Site Consumables', 'WesTrac', 18500.00, 'set', 14, '2025-04-01', 25, 'increasing', 'moderate'),
('MAT-010', 'PPE - Hard Hats (AS/NZS 1801)', 'Safety', 'Blackwoods', 45.00, 'unit', 5, '2025-04-05', 500, 'stable', 'good');
```

> **Verify all tables:**
> - `SELECT COUNT(*) FROM cimic.projects.financials` → expect 10
> - `SELECT COUNT(*) FROM cimic.equipment.equipment_telemetry` → expect 10
> - `SELECT COUNT(*) FROM cimic.safety.incidents` → expect 7
> - `SELECT COUNT(*) FROM cimic.procurement.materials` → expect 10

#### 3.2.1 Create a Genie Space in Databricks

1. In your Databricks workspace, go to **Genie** (left sidebar)
2. Click **+ New Genie Space**
3. Configure:

   | Field | Value |
   |-------|-------|
   | Name | `CIMIC Project Intelligence` |
   | SQL Warehouse | `cimic-ai-agent-warehouse` (Pro or Serverless) |
   | Tables | `cimic.projects.financials`, `cimic.equipment.equipment_telemetry`, `cimic.safety.incidents`, `cimic.procurement.materials` |

4. Add **General Instructions** to define CIMIC-specific terminology:

   ```
   - LTIFR means Lost Time Injury Frequency Rate
   - SPI means Schedule Performance Index (1.0 = on schedule, <1.0 = behind)
   - CPI means Cost Performance Index (1.0 = on budget, <1.0 = over budget)
   - CV% means Cost Variance Percentage
   - Divisions are: CPB Contractors, Thiess, Sedgman, Pacific Partnerships
   - All monetary values are in AUD unless specified otherwise
   - "Red status" means the project is at risk or over budget
   ```

5. Add **Example SQL Queries** to the knowledge store for common patterns:

   ```sql
   -- Question: Show me all red-status projects
   SELECT project_name, division, budget_aud, actual_cost_aud, cost_variance_pct
   FROM cimic.projects.financials
   WHERE status = 'red'
   ORDER BY cost_variance_pct DESC;

   -- Question: What is the average SPI by division?
   SELECT division, ROUND(AVG(spi), 2) as avg_spi, COUNT(*) as project_count
   FROM cimic.projects.financials
   GROUP BY division
   ORDER BY avg_spi;

   -- Question: Which equipment has a warning or critical status?
   SELECT equipment_id, equipment_type, site_name, engine_temp_celsius, status
   FROM cimic.equipment.equipment_telemetry
   WHERE status IN ('warning', 'critical')
   ORDER BY status, engine_temp_celsius DESC;

   -- Question: What is the average engine temperature by equipment type?
   SELECT equipment_type, ROUND(AVG(engine_temp_celsius), 1) as avg_temp, COUNT(*) as count
   FROM cimic.equipment.equipment_telemetry
   GROUP BY equipment_type
   ORDER BY avg_temp DESC;

   -- Question: Show me all open safety incidents
   SELECT incident_id, incident_date, site_name, division, incident_type, severity, description
   FROM cimic.safety.incidents
   WHERE status = 'open'
   ORDER BY incident_date DESC;

   -- Question: Which division has the most safety incidents?
   SELECT division, COUNT(*) as incident_count
   FROM cimic.safety.incidents
   GROUP BY division
   ORDER BY incident_count DESC;

   -- Question: What materials have increasing price trends?
   SELECT material_name, category, supplier, unit_price_aud, unit, price_trend
   FROM cimic.procurement.materials
   WHERE price_trend = 'increasing'
   ORDER BY unit_price_aud DESC;

   -- Question: Show me steel suppliers and pricing
   SELECT material_name, supplier, unit_price_aud, unit, lead_time_days, availability
   FROM cimic.procurement.materials
   WHERE category = 'Steel'
   ORDER BY unit_price_aud DESC;
   ```

6. Note the **Genie Space ID** from the URL (e.g., `01ef...abcd`)

7. Verify the MCP endpoint is available:
   - Go to **Agents** → **MCP Servers** tab in your Databricks workspace
   - You should see the Genie Space listed with its endpoint URL

#### 3.2.2 Configure OAuth Identity Passthrough for Databricks

OAuth Identity Passthrough ensures that every query the Foundry agent sends to Databricks runs **as the signed-in user** — not a shared service account. This is what makes Row-Level Security (step 3.2.5) work end-to-end.

> **Reference docs:**
> - Databricks side: [Use Azure Databricks Genie in Microsoft Foundry](https://learn.microsoft.com/en-us/azure/databricks/integrations/microsoft-foundry)
> - Foundry side: [MCP server authentication](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/mcp-authentication)

##### Managed vs Custom OAuth

Foundry supports two OAuth options for MCP connections: **Managed** and **Custom**.

- **Managed:** Microsoft handles the OAuth trust automatically — no app registration needed. You simply select "Managed" in the dropdown and Foundry's first-party Entra ID app handles tokens.
- **Custom:** You create your own Entra ID app registration and provide the Client ID, Client Secret, and OAuth URLs.

> **Important — Catalog entry availability:** The "Azure Databricks Genie" catalog entry in Foundry's **Build > Tools** is in **Public Preview** and is rolling out progressively. As of April 2026, it may **not appear** in all regions or tenants (including Australia East). If you cannot find "Azure Databricks Genie" in the tool catalog, or if the "Managed" OAuth option does not appear, use the **Custom OAuth** approach below. It connects to the exact same Databricks MCP endpoint and is functionally identical.

This guide uses the **Custom OAuth** approach — it works reliably regardless of whether the catalog entry has rolled out to your region.

```
Foundry Agent
    │
    ▼ (MCP call — user redirected to sign in)
Microsoft Entra ID (your registered app)
    │ (issues delegated token for the signed-in user,
    │  scoped to Azure Databricks resource)
    ▼
Azure Databricks (validates Entra ID token)
    │ (identifies user as alice@cimic.com.au)
    ▼
Unity Catalog (enforces Alice's permissions + row filters)
```

##### Step 1 — Verify Entra ID User Sync to Databricks

For OAuth Identity Passthrough to work, the users who access the Foundry agent must also exist in the Databricks workspace. Azure Databricks auto-syncs Entra ID identities when using Azure-managed workspaces, but verify this is working:

1. In the Databricks workspace, go to **Workspace admin** → **Users**
2. Confirm that your workshop users appear (e.g., `alice@cimic.com.au`, `bob@cimic.com.au`)
3. If users are missing:
   - **Automatic:** Users are added automatically on first access if "Auto add users" is enabled (default for Azure-managed workspaces). Each user can simply visit the workspace URL once.
   - **SCIM provisioning (recommended for production):** Configure in [Entra ID](https://entra.microsoft.com) → **Enterprise applications** → find your Databricks workspace → **Provisioning** → Enable automatic provisioning. This syncs users and groups continuously.
   - **Manual:** In Databricks workspace → **Users** → **Add user** → enter the Entra ID email

> **Key point:** The Entra ID email in Databricks must exactly match the email the user signs in with in Foundry. Since both use the same Entra ID tenant, this happens automatically.

##### Step 2 — Register an Entra ID App for Databricks OAuth

Create an app registration in Microsoft Entra ID that Foundry will use to request tokens scoped to Azure Databricks on behalf of each user.

1. Open the [Azure Portal](https://portal.azure.com) → **Microsoft Entra ID** → **App registrations**
2. Click **+ New registration**
3. Fill in:

   | Field | Value |
   |-------|-------|
   | Name | `Foundry-Databricks-Genie` (or any descriptive name) |
   | Supported account types | **Accounts in this organizational directory only** (single tenant) |
   | Redirect URI | Leave blank for now (Foundry provides this after connection) |

4. Click **Register**
5. On the overview page, copy and save:
   - **Application (client) ID**
   - **Directory (tenant) ID**

6. Go to **Certificates & secrets** → **Client secrets** → **+ New client secret**
   - Description: `foundry-mcp-secret`
   - Expiry: 6 or 12 months
   - Click **Add**
   - **Copy the secret Value immediately** — it is only shown once

7. Go to **API permissions** → **+ Add a permission**
   - Select **APIs my organization uses**
   - Search for **`AzureDatabricks`** (or paste the resource ID: `2ff814a6-3304-4ab8-85cb-cd0e6f879c1d`)
   - Select **AzureDatabricks**
   - Choose **Delegated permissions** → check **`user_impersonation`**
   - Click **Add permissions**
   - (Recommended) Click **Grant admin consent for [your tenant]** if you have admin rights

> **Why this works:** Azure Databricks natively uses Entra ID as its identity provider. The resource ID `2ff814a6-3304-4ab8-85cb-cd0e6f879c1d` is the Azure Databricks service principal in Entra ID. When Foundry requests a token with this scope, Entra ID issues a delegated token that Databricks accepts — no Databricks-side app configuration needed.

##### Step 3 — Connect Genie to the Foundry Agent via Custom MCP

1. Open [Microsoft Foundry Portal](https://ai.azure.com) → select your project
2. Go to **Build > Tools** → click **+ Add Tool** → select **Custom** → **MCP**
3. Fill in the connection details:

   | Field | Value |
   |-------|-------|
   | Name | `cimic-genie-data` |
   | Remote MCP Server endpoint | `https://adb-<workspace-id>.azuredatabricks.net/api/2.0/mcp/genie/<genie_space_id>` |
   | Authentication | **OAuth Identity Passthrough** |

   > **Tip:** Find your workspace hostname from the Databricks workspace URL. Find your Genie Space ID from the Genie space URL: `https://<instance>/genie/rooms/<space-id>` — the `<space-id>` is what you need.

4. Select **Custom** for OAuth provider, then fill in:

   | OAuth Field | Value |
   |-------------|-------|
   | Client ID | Your Application (client) ID from Step 2 |
   | Client Secret | Your secret Value from Step 2 |
   | Auth URL | `https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/authorize` |
   | Token URL | `https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/token` |
   | Refresh URL | `https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/token` |
   | Scopes | `2ff814a6-3304-4ab8-85cb-cd0e6f879c1d/.default` |

   > **Scope note:** The `/.default` scope means "request all permissions granted to this app." Since you added `user_impersonation` in Step 2, it is included automatically. You do not need to specify `user_impersonation` explicitly here.

5. Click **Connect**

##### Step 4 — Add the Redirect URI Back to Your Entra ID App

After connecting, Foundry provides a **redirect URL**.

1. Copy the redirect URL from Foundry
2. Go back to **Azure Portal** → **Entra ID** → **App registrations** → `Foundry-Databricks-Genie`
3. Go to **Authentication** → **+ Add a platform** → **Web**
4. Paste the redirect URL from Foundry
5. Click **Configure**

> **If you see the "Azure Databricks Genie" catalog entry:** In some regions/tenants, the catalog entry is available in Foundry's tool catalog. If you find it when searching in **Build > Tools**, you can use it with the **Managed** OAuth option instead — it handles the Entra ID app automatically. The Custom approach documented here is functionally identical and works everywhere.

> **Why not PAT or Service Principal?** A Personal Access Token (PAT) or Service Principal authenticates as a **single identity** — all agent users would share the same Databricks permissions, completely bypassing Row-Level Security. OAuth Identity Passthrough ensures each user's query runs under **their own Entra ID identity**, so Unity Catalog row filters and column masks are enforced per user.
>
> | Auth Method | Identity Used | RLS Enforced? | Use Case |
> |-------------|--------------|---------------|----------|
> | **OAuth Identity Passthrough (Custom)** | Signed-in user's Entra ID | **Yes** — per user | Production with RLS ✅ |
> | OAuth Identity Passthrough (Managed) | Signed-in user's Entra ID | **Yes** — per user | Production (if catalog entry available) ✅ |
> | PAT (Personal Access Token) | Token owner (single user) | Only for that one user | Quick personal testing only |
> | Service Principal | App identity (no human user) | No — sees all data | Backend batch jobs (not agent) |

#### 3.2.3 Authorize the Connection (Per-User Consent)

Each user must grant consent the **first time** they use the agent with the Genie tool. This is a standard Entra ID delegated consent flow — similar to approving a Microsoft 365 app.

##### First-Time Consent Walkthrough

1. In Foundry, go to your connected tool → click **Use in an agent** (or open your agent and ensure the Genie MCP tool is attached)
2. Send a test message that triggers a Genie query:

   ```
   What tables do you have access to?
   ```

3. The agent attempts to call the Genie MCP tool — a **consent banner** appears in the response:

   > "This agent needs to connect to Azure Databricks on your behalf. [Open consent]"

4. Click **"Open consent"** — a new browser window opens showing the **Microsoft Entra ID consent page**
5. Sign in with your Entra ID credentials (e.g., `alice@cimic.com.au`)
6. Review the permissions requested (you'll see `user_impersonation` for Azure Databricks) and click **Approve**
7. The browser shows a confirmation dialog — close it and return to Foundry
8. Re-send the query — the agent now calls Genie using your token

##### What Happens Behind the Scenes

```
User sends query in Foundry
    │
    ▼
Foundry Agent determines Genie tool is needed
    │
    ▼ (no valid token for this user yet)
Foundry returns oauth_consent_request → user clicks "Open consent"
    │
    ▼
Browser → Microsoft Entra ID login.microsoftonline.com
    │        (OAuth 2.0 authorization code flow)
    │        Scope: 2ff814a6-.../.default (includes user_impersonation)
    │        App: Foundry-Databricks-Genie (your Entra ID app)
    ▼
User signs in (or SSO) and clicks "Approve"
    │
    ▼
Entra ID issues authorization code → redirects to Foundry via your app's redirect URI
    │
    ▼
Foundry exchanges code for access token + refresh token
    │  (access token is scoped to Azure Databricks for this user)
    ▼
Foundry calls Databricks MCP endpoint with Alice's token
    │
    ▼
Databricks validates Entra ID token → identifies user as Alice
    │
    ▼
Genie → SQL Warehouse → Unity Catalog
    │  (Unity Catalog enforces Alice's row filters + column masks)
    ▼
Results returned → only data Alice is authorised to see
```

##### Token Lifecycle

| Token | Lifetime | Managed By | User Action |
|-------|----------|-----------|-------------|
| **Access token** | ~1 hour | Foundry auto-refreshes silently | None — transparent to user |
| **Refresh token** | Up to 90 days (Entra ID default) | Foundry stores encrypted per-user | Re-consent only if token expires or is revoked |

- **Automatic refresh:** Foundry uses the refresh token to obtain new access tokens silently — the user won't see the consent prompt again during normal use
- **Revocation:** A user can revoke their consent in [My Account](https://myaccount.microsoft.com) → **Permissions** → find the Foundry/Databricks application → **Revoke**
- **Admin revocation:** A tenant admin can revoke consent for all users via Entra ID → **Enterprise applications** → find the Foundry application → **Permissions** → revoke

##### Troubleshooting Consent Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| Consent page doesn't appear | Pop-up blocker | Allow pop-ups from `ai.azure.com` |
| "Need admin approval" on consent page | Entra ID tenant requires admin consent for new apps | Tenant admin grants consent via **Enterprise applications** → **Admin consent** |
| User signs in but gets "Access denied" | User not added to the Databricks workspace | Add the user to the workspace (see Step 1 above) |
| Consent prompt reappears frequently | Refresh token revoked or Conditional Access policy | Check Entra ID sign-in logs; verify no CA policy blocks token refresh |
| "AADSTS65001" error code | Consent not granted or revoked | User re-consents; admin may need to pre-approve |
| Agent returns empty results after consent | User has no permissions on the tables in Unity Catalog | Grant `SELECT` on `cimic.*` tables (or relevant schemas) to the user/group |

#### 3.2.4 Test the Integration

Try these CIMIC-specific queries in the agent chat:

```
Show me all red-status projects in the CPB Contractors division.
```

```
What's the average cost overrun percentage across all Thiess projects?
```

```
Which projects have an SPI below 0.9? Sort by worst performing first.
```

```
Are there any equipment units with critical or warning status?
```

```
Show me all open safety incidents across CIMIC.
```

```
Which materials have increasing price trends? Show supplier and pricing.
```

*Expected: The agent invokes the Genie MCP tool, Genie generates SQL, executes it against the SQL Warehouse, and returns results. The agent then formats the answer for the user.*

#### 3.2.5 Configure Row-Level Security (RLS) in Unity Catalog

A key CIMIC requirement is **division-level data isolation** — a CPB Contractors user should only see CPB projects, while a Thiess user sees only Thiess data. Unity Catalog **row filters** enforce this automatically, and because the Genie MCP connection uses OAuth Identity Passthrough, the same filters apply when querying through the Foundry agent.

##### Step A — Create Entra ID Security Groups

Create groups in Microsoft Entra ID that map to CIMIC divisions. These groups will be referenced in Unity Catalog row filters.

1. Open [Microsoft Entra admin centre](https://entra.microsoft.com) → **Groups** → **All groups**
2. Click **+ New group** and create the following:

   | Group Name | Type | Description |
   |------------|------|-------------|
   | `Group-A` | Security | CPB Contractors division users |
   | `Group-B` | Security | Thiess division users |
   | `Group-C` | Security | Sedgman division users |
   | `Group-Executives` | Security | C-suite / cross-division access |

3. Add workshop participants to the appropriate groups:
   - Add `alice@cimic.com.au` to `Group-A`
   - Add `bob@cimic.com.au` to `Group-B`
   - Add `carol@cimic.com.au` to `Group-Executives`

> **Workshop shortcut:** If you only have one or two test accounts, add one to `Group-A` and another to `Group-B` to demonstrate the difference.

##### Step B — Sync Entra ID Groups to Databricks

Unity Catalog needs to recognise these Entra ID groups.

1. Go to the [Databricks Account Console](https://accounts.azuredatabricks.net) → **User management** → **Groups**
2. Verify your Entra ID groups are synced via SCIM or manual assignment:
   - If **SCIM provisioning** is configured (recommended for production), groups sync automatically
   - If not, click **Add group** → search for each `Group-*` group and add it
3. Assign each group to your workspace: **Workspaces** → `dbw-cimic-workshop` → **Permissions** → add each group with **User** workspace access

##### Step C — Create a Row Filter Function

Row filters in Unity Catalog use a **SQL function** that returns `TRUE` for rows the current user is allowed to see. Run this in a Databricks SQL notebook:

```sql
-- Create a schema for security functions
CREATE SCHEMA IF NOT EXISTS cimic.security;

-- Row filter function: returns TRUE if the user belongs to the matching
-- division group, OR if the user is in the Executives group (full access)
CREATE OR REPLACE FUNCTION cimic.security.division_filter(division_value STRING)
RETURNS BOOLEAN
RETURN
  -- Executives see all divisions
  IS_ACCOUNT_GROUP_MEMBER('Group-Executives')
  -- Division users see only their own data
  OR (division_value = 'CPB Contractors' AND IS_ACCOUNT_GROUP_MEMBER('Group-A'))
  OR (division_value = 'Thiess'           AND IS_ACCOUNT_GROUP_MEMBER('Group-B'))
  OR (division_value = 'Sedgman'          AND IS_ACCOUNT_GROUP_MEMBER('Group-C'));
```

> **How it works:** `IS_ACCOUNT_GROUP_MEMBER()` checks the Entra ID identity of the current user (passed through via OAuth) against account-level groups. No user mapping table is needed.

##### Step D — Apply Row Filters to CIMIC Tables

Attach the filter function to each table's `division` column:

```sql
-- Project financials: filter by division
ALTER TABLE cimic.projects.financials
  SET ROW FILTER cimic.security.division_filter ON (division);

-- Equipment telemetry: filter by division
ALTER TABLE cimic.equipment.equipment_telemetry
  SET ROW FILTER cimic.security.division_filter ON (division);

-- Safety incidents: filter by division
ALTER TABLE cimic.safety.incidents
  SET ROW FILTER cimic.security.division_filter ON (division);

-- Procurement materials: no division column, so no row filter needed
-- (all users can see all materials — this is shared reference data)
```

> **Important:** Row filters are enforced at the **Unity Catalog level** — they apply to all query paths including Genie, direct SQL, notebooks, and MCP. There is no way to bypass them without catalog admin privileges.

##### Step E — Verify RLS in Databricks (Before Testing in Foundry)

Run these verification queries as different users to confirm the filters work:

1. **As a CPB user** (`alice@cimic.com.au` — member of `Group-A`):

   ```sql
   SELECT project_name, division, status FROM cimic.projects.financials;
   ```

   *Expected:* Only rows where `division = 'CPB Contractors'` are returned (5 projects).

2. **As a Thiess user** (`bob@cimic.com.au` — member of `Group-B`):

   ```sql
   SELECT project_name, division, status FROM cimic.projects.financials;
   ```

   *Expected:* Only rows where `division = 'Thiess'` are returned (3 projects).

3. **As an Executive** (`carol@cimic.com.au` — member of `Group-Executives`):

   ```sql
   SELECT project_name, division, status FROM cimic.projects.financials;
   ```

   *Expected:* All 10 projects returned (Executives see everything).

> **Tip:** To quickly test as different users in the workshop, open Databricks in separate browser profiles (e.g., Chrome normal + incognito + Edge) and sign in with different Entra ID accounts.

##### Step E2 — Test RLS on Equipment Telemetry (Recommended Demo Query)

Equipment telemetry is the best table for demonstrating RLS because the results are visually distinct per division. Use this query as the primary RLS test:

**As a Group-A user** (e.g., member of `Group-A` = CPB Contractors):

```
Provide a summary of equipment telemetry metrics by division, including the total fleet count,
operational equipment, equipment under maintenance, equipment with warning status,
and equipment with critical status.
```

*Expected SQL generated by Genie:*
```sql
SELECT
  division,
  COUNT(*) AS total_fleet,
  SUM(CASE WHEN status = 'operational' THEN 1 ELSE 0 END) AS operational,
  SUM(CASE WHEN status = 'maintenance' THEN 1 ELSE 0 END) AS under_maintenance,
  SUM(CASE WHEN status = 'warning' THEN 1 ELSE 0 END) AS warning_status,
  SUM(CASE WHEN status = 'critical' THEN 1 ELSE 0 END) AS critical_status
FROM cimic.equipment.equipment_telemetry
GROUP BY division;
```

*Expected result for Group-A user:*

| division | total_fleet | operational | under_maintenance | warning_status | critical_status |
|----------|-------------|-------------|-------------------|----------------|-----------------|
| CPB Contractors | ~1,250 | ~1,000 | ~63 | ~125 | ~63 |

**Only one row** — CPB Contractors. The user cannot see Thiess or Sedgman data.

*Expected result for Group-Executives user:*

| division | total_fleet | operational | under_maintenance | warning_status | critical_status |
|----------|-------------|-------------|-------------------|----------------|-----------------|
| CPB Contractors | ~1,250 | ~1,000 | ~63 | ~125 | ~63 |
| Thiess | ~1,250 | ~1,000 | ~63 | ~125 | ~63 |
| Sedgman | ~1,250 | ~1,000 | ~63 | ~125 | ~63 |
| Pacific Partnerships | ~1,250 | ~1,000 | ~63 | ~125 | ~63 |

**All four divisions** visible. This is the clearest demo of RLS — same question, different results based on group membership.

> **Key point:** The Genie Space, agent instructions, and MCP tool are identical for all users. The division-level isolation is enforced entirely by the Unity Catalog `division_filter` row filter function.

##### Step F — Test RLS Through the Foundry Agent

Now test that the same row filters are enforced when querying via the Foundry agent's Genie MCP tool.

1. **Sign in to Foundry as the CPB user** (`alice@cimic.com.au`)
2. Open the agent and ask:

   ```
   Show me all projects and their status.
   ```

   *Expected:* The agent returns only CPB Contractors projects:

   | Project | Division | Status |
   |---------|----------|--------|
   | Sydney Metro West - Station Fit-Out | CPB Contractors | green |
   | Inland Rail - Narrabri to North Star | CPB Contractors | amber |
   | WestConnex M4-M5 Link Tunnels | CPB Contractors | red |
   | Melbourne Metro Tunnel | CPB Contractors | green |
   | Pacific Highway Upgrade - Coffs Harbour | CPB Contractors | green |

3. **Sign in to Foundry as the Thiess user** (`bob@cimic.com.au`)
4. Ask the same question:

   ```
   Show me all projects and their status.
   ```

   *Expected:* The agent returns only Thiess projects:

   | Project | Division | Status |
   |---------|----------|--------|
   | Bowen Basin Resource Expansion | Thiess | green |
   | Mount Pleasant Operations | Thiess | red |
   | Carmichael Rail Network | Thiess | red |

5. **Sign in as the Executive** (`carol@cimic.com.au`) and verify all 10 projects are returned.

> **Key takeaway:** No configuration was needed on the Foundry side — the agent, system prompt, and Genie tool are identical for all users. Division-level isolation is enforced entirely by Unity Catalog row filters + OAuth Identity Passthrough. The Foundry agent inherits the user's Databricks permissions automatically.

##### (Optional) Column Masks for Sensitive Fields

For fields that should be partially hidden (e.g., exact budget figures for non-executives), Unity Catalog also supports **column masks**:

```sql
-- Create a masking function: non-executives see rounded figures only
CREATE OR REPLACE FUNCTION cimic.security.mask_budget(budget_value DOUBLE)
RETURNS DOUBLE
RETURN
  CASE
    WHEN IS_ACCOUNT_GROUP_MEMBER('Group-Executives') THEN budget_value
    ELSE ROUND(budget_value / 1000000, 0) * 1000000  -- Round to nearest million
  END;

-- Apply to the budget column
ALTER TABLE cimic.projects.financials
  ALTER COLUMN budget_aud SET MASK cimic.security.mask_budget;
```

With this mask:
- **Executives** see exact values (e.g., `850,000,000`)
- **Division users** see values rounded to the nearest million

> **Tip:** Column masks are most useful for finer-grained values (e.g., individual salaries, margin percentages). For the workshop demo, row filters alone provide a clear and visual demonstration of RLS.

### How OAuth Identity Passthrough Works

This is the critical security advantage of the MCP approach:

```
User (Entra ID: alice@cimic.com.au)
    │
    ▼ (signs into Foundry with Entra ID)
Foundry Agent
    │
    ▼ (MCP call — passes Alice's identity token)
Databricks Managed MCP Server
    │
    ▼ (authenticates as Alice via Entra ID)
Genie → SQL Warehouse → Unity Catalog
    │
    ▼ (Unity Catalog checks Alice's permissions)
Only returns data Alice is authorised to see
```

- A CPB project manager sees **only CPB data** (enforced by the row filter configured in step 3.2.5)
- A Thiess division head sees **only Thiess data**
- An Executive group member sees **all divisions**
- No shared service account or PAT token — each user's permissions are enforced individually
- **No Foundry-side configuration needed for RLS** — it is enforced entirely in Unity Catalog. The Foundry agent, system prompt, and Genie tool connection are identical for all users.

### Rate Limits & Production Considerations

| Limit | Value | Scope | Can Increase? |
|-------|-------|-------|---------------|
| Genie API (free tier) | 5 queries/min | Workspace | Contact Databricks account team |
| MCP server (managed) | 50 queries/sec | Workspace | Yes (support request) |
| Genie tables per space | Up to 30 | Genie Space | No |
| MCP tool call timeout | 100 seconds | Foundry Agent Service | No |

> **Note:** The 5 q/min Genie rate limit is the same regardless of whether you use MCP or direct API calls — it's enforced at the Genie service layer. For production with many concurrent users, contact your Databricks account team about a paid tier.

### Pros & Cons

| Pros | Cons |
|------|------|
| **Zero code** — entire setup via portal | Public Preview (not GA yet) |
| OAuth Identity Passthrough — per-user Unity Catalog permissions | 5 q/min rate limit on Genie free tier |
| No middleware (no Azure Function) | No conversation history passed to Genie (invoked as a tool) |
| Handles ad-hoc questions (NL-to-SQL) | Double-LLM latency (Foundry LLM + Genie AI) |
| Same Foundry Portal experience as Module 2 | Requires "Managed MCP Servers" preview enabled |
| Databricks hosts the MCP server — no infra to manage | Up to 30 tables per Genie space |

---

## 3.3 Option 2: Fabric Mirroring + Data Agent

**Pattern:** Databricks Unity Catalog → Fabric Mirroring (metadata, no data movement) → Fabric Data Agent → Foundry / Power BI Copilot

> **Status:** Generally Available (Fabric mirroring); Preview (Fabric Data Agents)

### How It Works

```
Azure Databricks (Unity Catalog)
    │
    ▼ (Mirroring — metadata sync, no data copy)
Microsoft Fabric (Mirrored Catalog)
    │
    ├──▶ SQL Analytics Endpoint (T-SQL queries)
    ├──▶ Power BI (Direct Lake mode — reports & dashboards)
    └──▶ Fabric Data Agent (NL-to-SQL, publishable API)
              │
              ▼ (Published URL / Copilot in Power BI)
         End Users / Foundry Integration
```

**Key insight:** Fabric mirroring creates **shortcuts** to Databricks data — metadata only. The underlying data stays in Databricks (Delta Lake on ADLS). No ETL, no data duplication, no storage cost in Fabric.

### When to Use This Over Genie MCP

| Scenario | Genie MCP (Option 1) | Fabric Mirroring (Option 2) |
|----------|---------------------|-----------------------------|
| Quick ad-hoc questions from agent | ✅ Best | Possible but heavier setup |
| Power BI dashboards on Databricks data | ❌ | ✅ Best (Direct Lake mode) |
| T-SQL queries on Databricks tables | ❌ | ✅ (SQL Analytics Endpoint) |
| Enterprise BI + governance layer | ❌ | ✅ (Fabric workspace security) |
| Cross-source analytics (Databricks + other) | ❌ | ✅ (Fabric unifies sources) |
| Copilot in Power BI over Databricks data | ❌ | ✅ Native |

**Bottom line:** Use **Genie MCP** for direct agent-to-Databricks querying. Use **Fabric mirroring** when you need an enterprise analytics layer (Power BI, T-SQL, cross-source) on top of the same Databricks data.

### Prerequisites

1. **Microsoft Fabric capacity** — F2 or higher (or Power BI Premium P1+)
2. **Azure Databricks workspace** with Unity Catalog enabled
3. **Databricks Service Principal** or Entra ID authentication
4. **Fabric workspace** with contributor access
5. Fabric admin: **Data Agent tenant settings** enabled
6. Fabric admin: **Cross-geo processing for AI** enabled (if applicable)

### Step-by-Step Setup

#### 3.4.0 Configure Service Principal for Fabric Mirroring

Fabric mirroring runs as a background service that periodically refreshes its connection to Databricks. An **Org Account** (personal login) will fail with `"Invalid credentials"` because MFA prompts can't be completed silently. A **Service Principal** is required.

> **Full troubleshooting guide:** See [`fabric/docs/fabric-mirroring-auth-permissions-rls-guide.md`](../fabric/docs/fabric-mirroring-auth-permissions-rls-guide.md) for detailed steps, screenshots, and error resolution.

##### Quick Checklist

| # | Step | Where | Notes |
|---|------|-------|-------|
| 1 | **Create App Registration** | Entra ID → App registrations → + New registration | Record: Client ID, Tenant ID |
| 2 | **Create Client Secret** | App reg → Certificates & secrets → + New client secret | ⚠️ Copy the Value immediately — it disappears |
| 3 | **Add API Permission** | App reg → API permissions → + Add → **"APIs my organization uses"** → search **"AzureDatabricks"** → Delegated → `user_impersonation` | ⚠️ Must use "APIs my organization uses" tab, NOT "Microsoft APIs" |
| 4 | **Grant Admin Consent** | Same page → "Grant admin consent for [tenant]" | Requires Global Admin or Cloud App Admin |
| 5 | **Add SP to Account Console** | [Databricks Account Console](https://accounts.azuredatabricks.net) → User management → Service principals → + Add | Enter the Application (Client) ID |
| 6 | **Assign SP to Workspace** | Account Console → Workspaces → select workspace → Permissions → add SP with **CAN USE** | |
| 7 | **Enable External Data Access** | Databricks workspace → Catalog → ⚙️ gear → Metastore → Details → toggle ON | Only metastore admins can do this |
| 8 | **Grant UC Permissions** | Databricks SQL Editor (see SQL below) | Both standard + EXTERNAL USE SCHEMA |

##### Unity Catalog Grants

Run in the Databricks SQL Editor, replacing `{sp_client_id}` and `{catalog}` with your values:

```sql
-- Standard catalog access
GRANT USE CATALOG ON CATALOG {catalog} TO `{sp_client_id}`;
GRANT USE SCHEMA ON CATALOG {catalog} TO `{sp_client_id}`;
GRANT SELECT ON CATALOG {catalog} TO `{sp_client_id}`;

-- ⚠️ CRITICAL — without this, mirroring returns "unexpected format" error
GRANT EXTERNAL USE SCHEMA ON SCHEMA {catalog}.projects TO `{sp_client_id}`;
GRANT EXTERNAL USE SCHEMA ON SCHEMA {catalog}.equipment TO `{sp_client_id}`;
GRANT EXTERNAL USE SCHEMA ON SCHEMA {catalog}.safety TO `{sp_client_id}`;
GRANT EXTERNAL USE SCHEMA ON SCHEMA {catalog}.procurement TO `{sp_client_id}`;
```

##### Current Workshop Values

| Environment | SP Client ID | Catalog |
|-------------|-------------|---------|
| Dev | `5319dcfd-60d3-4bce-9d26-7e9a6dd81503` | `cimic` |
| Prod | `8924f20b-eb17-4713-8123-dda701e54eab` | `cimic_prod` |

##### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `"Invalid credentials"` | Using Org Account (MFA blocks background refresh) | Switch to Service Principal authentication |
| `"Invalid connection credentials"` (HTTP 400) | Missing AzureDatabricks API permission or admin consent | Step 3 + 4 above |
| `"Unable to process response from Databricks. The API returned data in an unexpected format"` | Missing `EXTERNAL USE SCHEMA` grant | Step 8 — grant `EXTERNAL USE SCHEMA` on each schema |
| `"AzureDatabricks"` not found in API permissions | Wrong tab — looking at "Microsoft APIs" | Switch to **"APIs my organization uses"** tab |

> **⚠️ Important: Mirroring SP ≠ Genie OAuth.** The Service Principal configured here is for Fabric mirroring (background data sync). The Genie MCP connection (section 3.3.2) uses OAuth Identity Passthrough — each user authenticates as themselves. These are separate auth flows for separate purposes.

##### Fabric Tenant Prerequisites

Before mirroring will work, a Fabric admin must enable these tenant settings:

1. **Fabric admin portal** → **Tenant settings** → search for "service principal"
2. Enable: **"Service principals can use Fabric APIs"**
3. Enable: **"Service principals can access read-only admin APIs"** (if needed for monitoring)
4. Enable: **"Users can create Fabric items"** (for the workspace where mirroring will land)
5. If the Databricks workspace is in a different region than Fabric: **"Allow Azure AI services from other regions"** (under AI workloads)

#### 3.4.1 Mirror Databricks Unity Catalog into Fabric

1. Open [Microsoft Fabric](https://app.fabric.microsoft.com)
2. Navigate to your workspace
3. Click **+ New item** → search for **"Mirrored Azure Databricks Catalog"**
4. Configure the connection:

   | Field | Value |
   |-------|-------|
   | Databricks workspace URL | `https://adb-<workspace-id>.azuredatabricks.net` |
   | Authentication | **Service Principal** (configured in step 3.4.0) |
   | Tenant ID | Your Entra tenant ID |
   | Client ID | SP Application (Client) ID from step 3.4.0 |
   | Client Secret | SP secret value from step 3.4.0 |
   | Catalog | `cimic` (or `cimic_prod` for production) |

5. Select schemas and tables to mirror:

   | Schema | Tables |
   |--------|--------|
   | `cimic.projects` | `financials`, `milestones`, `resources` |
   | `cimic.equipment` | `equipment_telemetry`, `production_output` |

6. Enable **"Automatically sync future catalog changes"** (on by default)
7. Click **Create**

After creation, Fabric provisions:
- A **Mirrored Azure Databricks item** (metadata shortcuts to your tables)
- A **SQL Analytics Endpoint** (T-SQL interface over the mirrored data)

> **Important:** No data is copied. Fabric reads directly from the Delta Lake files in your Databricks-managed storage via shortcuts. Changes in Databricks propagate to Fabric within seconds to minutes.

#### 3.3.2 Verify Mirrored Data

1. In Fabric, open the **SQL Analytics Endpoint** created by mirroring
2. Run a test T-SQL query:

   ```sql
   SELECT TOP 10
       project_name,
       division,
       status,
       budget_aud,
       actual_cost_aud
   FROM cimic.projects.financials
   ORDER BY budget_aud DESC;
   ```

3. Confirm the data matches your Databricks source

> **⚠️ RLS does NOT propagate from Databricks to Fabric.** Unity Catalog row filters (section 3.3.5) are enforced when querying through Databricks (Genie, SQL Warehouse, notebooks). Fabric mirroring bypasses these filters because the SP reads data at the storage level. To enforce division-level isolation in Fabric, you must configure **OneLake Security roles** separately. See [`fabric/docs/fabric-mirroring-auth-permissions-rls-guide.md`](../fabric/docs/fabric-mirroring-auth-permissions-rls-guide.md) Section 8 for all 11 role definitions.

#### 3.4.2b Configure OneLake Security RLS (CPB Contractors Demo)

For the workshop demo, we create one set of OneLake Security roles for **Group-A (CPB Contractors)** to demonstrate Fabric-side RLS on mirrored data.

##### Prerequisites

1. **Workspace Identity** must be created:
   - Fabric workspace → **Settings** → **Workspace identity** → Create
   - In Azure portal, assign **Storage Blob Data Reader** on the Databricks-managed ADLS storage account to this Workspace Identity

2. **OneLake Security** must be enabled (irreversible):
   - Open the **Mirrored Databricks Catalog** item in Fabric
   - Click **"Manage OneLake security"** in the ribbon → accept the prompt
   - A `DefaultReader` role is auto-created for existing viewers

> **⚠️ Workspace Admins, Members, and Contributors bypass OneLake Security.** Only users with the **Viewer** workspace role are restricted by RLS. Ensure demo test users (e.g., Vinoth) have the **Viewer** role.

##### Create the CPB Contractors Roles

Navigate to: **Mirrored DB** → **Manage OneLake security** → **New role**

Create these 3 roles (one per table with a `division` column):

**Role 1: `RoleCPBFinance`**

| Setting | Value |
|---------|-------|
| Role name | `RoleCPBFinance` |
| Assign Entra group | `Group-A` |
| Table access | `financials_f` |

Row security expression:
```sql
SELECT * FROM projects.financials_f WHERE division = 'CPB Contractors'
```

**Role 2: `RoleCPBSafety`**

| Setting | Value |
|---------|-------|
| Role name | `RoleCPBSafety` |
| Assign Entra group | `Group-A` |
| Table access | `incidents_f` |

Row security expression:
```sql
SELECT * FROM safety.incidents_f WHERE division = 'CPB Contractors'
```

**Role 3: `RoleCPBEquipment`**

| Setting | Value |
|---------|-------|
| Role name | `RoleCPBEquipment` |
| Assign Entra group | `Group-A` |
| Table access | `equipment_telemetry_f` |

Row security expression:
```sql
SELECT * FROM equipment.equipment_telemetry_f WHERE division = 'CPB Contractors'
```

> **Why 3 roles?** OneLake Security roles are scoped to **one table per role**. Each role applies one row security expression. Since the `division` column exists on 3 tables (financials, incidents, equipment_telemetry), you need 3 roles for CPB Contractors. Procurement (materials) has no `division` column — all users see all materials.

> **Syntax:** OneLake RLS rules use a full `SELECT` statement: `SELECT * FROM {schema}.{table} WHERE {predicate}`. Supported operators: `=`, `<>`, `>`, `<`, `IN`, `AND`, `OR`, `NOT`.

##### Verify OneLake RLS

Sign in as a **Group-A Viewer** user (e.g., Vinoth) and query the mirrored data via the SQL Analytics Endpoint:

```sql
-- Should return ONLY CPB Contractors rows
SELECT division, COUNT(*) as row_count
FROM equipment.equipment_telemetry_f
GROUP BY division;
-- Expected: one row — 'CPB Contractors'
```

If you see all 4 divisions, check:
1. Is the user a **Viewer** (not Admin/Member/Contributor)?
2. Are the OneLake Security roles assigned to `Group-A`?
3. Is the user actually in the `Group-A` Entra group?

#### 3.4.3 Create a Fabric Data Agent

A Fabric Data Agent provides a natural language interface over your mirrored data — similar to Genie but within the Fabric ecosystem.

1. In your Fabric workspace, click **+ New item** → search for **"Data agent"**
2. Name it: `CIMIC Project Intelligence Agent`
3. **Select data source** → choose the mirrored lakehouse (or SQL Analytics Endpoint)
4. Select the tables to make available to the AI:
   - `cimic.projects.financials`
   - `cimic.equipment.equipment_telemetry`
   - `cimic.safety.incidents`
   - `cimic.procurement.materials`

5. **Add instructions** (similar to Genie):

   ```
   This data source contains CIMIC Group operational data mirrored from Azure Databricks.

   Key tables:
   - financials: Project budget, actuals, cost variance, SPI for all divisions
   - equipment_telemetry: Equipment fleet sensor data (engine temp, fuel, hours)
   - safety_incidents: HSE incident records with severity and site

   Terminology:
   - LTIFR = Lost Time Injury Frequency Rate
   - SPI = Schedule Performance Index (1.0 = on schedule)
   - CPI = Cost Performance Index (1.0 = on budget)
   - Divisions: CPB Contractors, Thiess, Sedgman, Pacific Partnerships
   - All costs in AUD
   ```

6. **Add example queries** to improve accuracy:

   | Question | SQL |
   |----------|-----|
   | Show red-status projects | `SELECT project_name, division, cost_variance_pct FROM cimic.projects.financials WHERE status = 'red'` |
   | Average SPI by division | `SELECT division, AVG(spi) as avg_spi FROM cimic.projects.financials GROUP BY division` |

7. **Test** the agent in the built-in chat panel
8. Click **Publish** to generate a published URL

#### 3.3.4 Use the Fabric Data Agent

Once published, the Fabric Data Agent can be consumed in multiple ways:

**In Copilot in Power BI:**
1. Open Power BI → click the **Copilot** button (left nav)
2. Click **"Add items for better results"** → **Data agents**
3. Select `CIMIC Project Intelligence Agent`
4. Ask questions directly in Copilot

**In Power BI Reports (Direct Lake):**
1. Create a new Power BI report connected to the mirrored data
2. Use **Direct Lake mode** — queries go directly to the Delta Lake files
3. No data import, no scheduled refresh — always current

**Programmatically (Fabric Notebook or external app):**
```python
# Call the published Data Agent API from any Python app
import requests
import time

PUBLISHED_URL = "https://<your-fabric-data-agent-published-url>"
QUESTION = "Show me the top 5 projects by cost overrun"

# Create thread and send question
# (See Fabric Data Agent API documentation for full implementation)
```

### Architecture: Combined View

When you combine both options, the architecture looks like this:

```
                Azure Databricks
                Unity Catalog (cimic.*)
                    │           │
        ┌───────────┘           └───────────┐
        │                                   │
   Genie MCP Server                    Fabric Mirroring
   (managed, /api/2.0/mcp/)           (metadata shortcuts)
        │                                   │
        ▼                                   ▼
   Foundry Agent                    Microsoft Fabric
   (MCP tool — ad-hoc queries)      ┌───────┴───────┐
                                    │               │
                              SQL Analytics    Fabric Data Agent
                              Endpoint         (NL-to-SQL)
                                    │               │
                              Power BI         Copilot in
                              (Direct Lake)    Power BI
```

### Pros & Cons

| Pros | Cons |
|------|------|
| No data duplication — metadata-only mirroring | Requires Microsoft Fabric capacity (F2+) |
| Power BI Direct Lake mode — always current | Fabric Data Agent is Preview |
| T-SQL access to Databricks tables | Additional Fabric cost on top of Databricks |
| Fabric Data Agent provides NL-to-SQL | More moving parts than Genie MCP |
| Copilot in Power BI integration | Propagation delay (seconds–minutes) |
| Enterprise governance via Fabric workspace | Materialized views and streaming tables not supported |

---

## 3.4 Recommendation for CIMIC

For the workshop, we recommend using **both approaches** for different purposes:

| Use Case | Integration Pattern | Rationale |
|----------|-------------------|-----------|
| Agent ad-hoc queries (real-time) | **Genie via MCP** (Option 1) | Zero code, per-user auth, direct from Foundry agent |
| Executive dashboards & BI | **Fabric Mirroring** (Option 2) | Power BI Direct Lake, always current, no ETL |
| Cross-source analytics | **Fabric Mirroring** (Option 2) | Fabric unifies Databricks + other sources |
| Self-service data exploration | **Fabric Data Agent** (Option 2) | Copilot in Power BI for business users |
| Static policies & governance docs | **File Search** (Module 4) | Built-in Foundry tool, no Databricks needed |

In Module 5, we'll implement the **Genie MCP** approach as the primary Databricks integration for the end-to-end demo agent.

---

## 3.5 Security Considerations for CIMIC

| Concern | Genie MCP Mitigation | Fabric Mirroring Mitigation |
|---------|---------------------|-----------------------------|
| Data exfiltration via agent | Genie generates read-only SQL — no arbitrary writes | Fabric workspace permissions + RLS |
| Authentication | **OAuth Identity Passthrough** (Custom Entra ID app per user) | Entra ID / Service Principal |
| Cross-division data access | Unity Catalog row filters & column masks enforced per user | Fabric workspace-level + UC-level permissions |
| Credential management | No PAT tokens — OAuth managed by platform | No PAT tokens — Entra ID connection |
| Network security | Private Endpoints (Databricks + Foundry) in production | Private Endpoints (Fabric + Databricks) |
| Audit trail | Foundry agent logs + Databricks query history | Fabric audit logs + Databricks query history |

---

## 3.6 Additional Databricks MCP Servers (Beyond Genie)

If your CIMIC use case goes beyond Genie, Databricks provides additional managed MCP servers you can add to your Foundry agent using the same portal flow:

| MCP Server | Use Case | Endpoint Pattern |
|------------|----------|-----------------|
| **Vector Search** | Search project documents, safety reports by similarity | `/api/2.0/mcp/vector-search/{catalog}/{schema}/{index}` |
| **Unity Catalog Functions** | Run predefined SQL functions (e.g., calculate EVM metrics) | `/api/2.0/mcp/functions/{catalog}/{schema}/{function}` |
| **SQL** | AI-generated SQL for data pipelines (read and write) | `/api/2.0/mcp/sql` |

These can be combined — for example, a single Foundry agent could have:
- Genie MCP (for NL-to-SQL on structured data)
- Vector Search MCP (for document similarity search)
- UC Functions MCP (for custom business logic)

---

## Checkpoint ✓

- [ ] Understand both Databricks-to-Foundry integration patterns (Genie MCP and Fabric Mirroring)
- [ ] Genie Space created in Databricks with CIMIC tables and instructions
- [ ] Genie MCP tool added to Foundry agent via Custom MCP with Entra ID app registration (Option 1)
- [ ] OAuth Identity Passthrough (Custom) authorised and tested with per-user consent
- [ ] Row-level security configured in Unity Catalog with division-based row filters (step 3.2.5)
- [ ] RLS verified end-to-end: different Entra ID users see only their division's data through the agent
- [ ] (If Fabric available) Unity Catalog mirrored into Fabric, Fabric Data Agent created (Option 2)
- [ ] Security implications understood for CIMIC production deployment

---

**Next:** [Module 4: Azure Foundry Toolkit Deep Dive](04-foundry-toolkit.md)
