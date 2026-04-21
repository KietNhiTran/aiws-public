# CIMIC Group -- AI Workshop Dataset Wiki

## The Story

CIMIC Group is Australia's largest infrastructure and construction conglomerate, operating
across mining services, civil engineering, commercial building, and public infrastructure.
With annual revenues exceeding AUD 14 billion and projects spanning every state, CIMIC faces
a universal challenge: **how do you govern, monitor, and optimise thousands of moving parts
across a portfolio of megaprojects?**

This dataset models a realistic slice of CIMIC's operational world -- seven active construction
sites across New South Wales, Queensland, Victoria, and Western Australia. Each site is running
simultaneously: a motorway upgrade in Sydney, a gold mine expansion in the Pilbara, a hospital
build in Melbourne, a rail tunnel in Brisbane, and more. Every day, hundreds of workers clock on,
dozens of excavators and haul trucks report telemetry, materials flow in from suppliers, safety
officers log incidents, and environmental monitors track dust and noise.

The data tells the story of **one reporting quarter** across these sites. It is designed to
answer questions a CIMIC executive, project director, or AI agent would ask:

- "Which projects are over budget and why?"
- "Is our safety record improving or declining?"
- "Are we paying too much for structural steel?"
- "Which supplier has the worst delivery quality?"
- "Are our excavators being utilised efficiently?"
- "Are we compliant with EPA noise limits at the Sydney site?"

---

## Catalog Structure

All data lives in the Unity Catalog: **`adb_cimic_aiws_dev_ws`**

The catalog is organised into **two distinct data domains**, each serving a different
demonstration purpose:

```
adb_cimic_aiws_dev_ws
|
|-- MANUFACTURING (9 base tables, 7 schemas)
|   |-- projects.financials        (Managed Delta)
|   |-- projects.milestones        (Managed Delta)
|   |-- safety.incidents           (Managed Delta)
|   |-- equipment.equipment_telemetry  (External Delta on ADLS)
|   |-- equipment.maintenance_log      (External Delta on ADLS)
|   |-- workforce.timesheets           (External Delta on ADLS)
|   |-- procurement.materials          (Iceberg UniForm)
|   |-- environmental.emissions        (Iceberg UniForm)
|   |-- quality.inspections            (Iceberg UniForm)
|   |
|   |-- 7 standard views + 3 materialized views
|
|-- SUPPLY CHAIN PIPELINE (Medallion: Bronze > Silver > Gold)
|   |-- supply_chain_bronze.*      (4 raw ingestion tables)
|   |-- supply_chain_silver.*      (4 cleaned tables)
|   |-- supply_chain_gold.*        (2 aggregate tables, 4 views)
|
|-- supply_chain_landing           (UC Volume for raw CSV/JSON files)
```

---

## Storage Format Strategy

The manufacturing tables deliberately use **three different storage formats** to demonstrate
cross-engine interoperability:

| Format | Tables | Why |
|--------|--------|-----|
| **Managed Delta** | financials, milestones, incidents | Core project data. Fully managed by Unity Catalog. Simplest option. |
| **External Delta on ADLS** | equipment_telemetry, maintenance_log, timesheets | Shows data stored outside the catalog metastore, on customer's own ADLS container. Useful for data sharing and bring-your-own-storage. |
| **Iceberg (UniForm)** | materials, emissions, inspections | Delta tables with Iceberg compatibility enabled. Queryable from Spark, Trino, Snowflake, or any Iceberg reader. Demonstrates multi-engine access. |

---

## Domain 1: Manufacturing (Project Operations)

### Entity Relationship Diagram

```
                            +---------------------+
                            |  projects.financials |
                            |---------------------|
                            | project_id (PK)     |
                            | project_name        |
                            | division            |       +------------------------+
                            | client              |       | projects.milestones    |
                            | budget_aud          |------>| milestone_id (PK)      |
                            | actual_cost_aud     |  1:N  | project_id (FK)        |
                            | earned_value_aud    |       | milestone_name         |
                            | spi, cpi            |       | planned_date           |
                            | status              |       | forecast_date          |
                            | project_manager     |       | delay_days             |
                            +--------|------------+       +------------------------+
                                     |
          +----------+----------+----+----+-----------+-----------+
          | 1:N      | 1:N      | 1:N     | 1:N       | 1:N      |
          v          v          v         v           v          v
  +-------------+ +--------+ +--------+ +----------+ +--------+ +----------+
  | safety.     | | equip. | | equip. | | procure. | | enviro.| | quality. |
  | incidents   | | equip_ | | maint_ | | materials| | emiss- | | inspect- |
  |             | | telem. | | log    | |          | | ions   | | ions     |
  | incident_id | | read_id| | wo_id  | | mat_id   | | read_id| | insp_id  |
  | project_id  | | equip_ | | equip_ | | project_ | | proj_  | | project_ |
  | site_name   | | id     | | id     | | id       | | id     | | id       |
  | severity    | | site_  | | cost_  | | supplier | | site_  | | site_    |
  | lost_time_  | | name   | | aud    | | unit_    | | name   | | name     |
  | days        | |        | |        | | price_   | | is_    | | result   |
  +-------------+ +---+----+ +---+----+ | aud      | | exceed.| +----------+
                      |          |       +----------+ +--------+
                      |   1:N    |
                      +----+-----+
                           |
              equipment_id links telemetry
              readings to maintenance
              work orders

  +-------------------+
  | workforce.        |
  | timesheets        |
  |                   |
  | timesheet_id (PK) |
  | employee_id       |
  | project_id (FK)   |
  | site_name         |
  | hours_regular     |
  | hours_overtime    |
  | total_cost_aud    |
  +-------------------+
```

### Key Relationships

| From | To | Join Key | Cardinality | Business Meaning |
|------|----|----------|-------------|------------------|
| `projects.financials` | `projects.milestones` | project_id | 1:N | Each project has 3-6 milestones (design, procurement, earthworks, etc.) |
| `projects.financials` | `safety.incidents` | project_id | 1:N | Safety incidents are logged against the project where they occurred |
| `projects.financials` | `procurement.materials` | project_id | 1:N | Material orders are placed by a specific project |
| `projects.financials` | `workforce.timesheets` | project_id | 1:N | Workers log time against the project they worked on |
| `projects.financials` | `environmental.emissions` | project_id | 1:N | Environmental readings are taken at project sites |
| `projects.financials` | `quality.inspections` | project_id | 1:N | Quality inspections are performed per project |
| `equipment.equipment_telemetry` | `equipment.maintenance_log` | equipment_id | 1:N | Each piece of equipment has telemetry and maintenance history |
| Cross-domain | All tables share `site_name` and `division` | site_name, division | N/A | Enables cross-domain analysis by site or business unit |

### Table Details

#### projects.financials (20 rows)

The **anchor table** for the entire manufacturing domain. Each row represents one active
construction project with full Earned Value Management (EVM) financials.

| Column | Type | Description |
|--------|------|-------------|
| project_id | STRING | Unique ID, e.g. PRJ-001 |
| project_name | STRING | Descriptive name, e.g. "WestConnex M4-M5 Link Tunnels" |
| division | STRING | CIMIC division: CPB Contractors, Thiess, UGL, Sedgman, EIC Activities |
| client | STRING | Client organisation, e.g. "Transport for NSW" |
| project_type | STRING | highway, mining, rail, building, water, renewable_energy |
| state | STRING | Australian state: NSW, QLD, VIC, WA, SA |
| budget_aud | DOUBLE | Approved budget in AUD |
| actual_cost_aud | DOUBLE | Costs incurred to date |
| earned_value_aud | DOUBLE | Value of work completed (EVM) |
| planned_value_aud | DOUBLE | Value of work planned to date (EVM) |
| cost_variance_pct | DOUBLE | (EV - AC) / EV as percentage |
| schedule_variance_pct | DOUBLE | (EV - PV) / PV as percentage |
| spi | DOUBLE | Schedule Performance Index (EV/PV). Below 1.0 = behind schedule |
| cpi | DOUBLE | Cost Performance Index (EV/AC). Below 1.0 = over budget |
| eac_aud | DOUBLE | Estimate at Completion |
| status | STRING | active, on_hold, completed, at_risk |
| pct_complete | DOUBLE | Percentage complete (0-100) |
| project_manager | STRING | Name of the project manager |

**Sample questions this table answers:**
- "What is our total portfolio value across all divisions?"
- "Which projects have a CPI below 0.9 (more than 10% over budget)?"
- "How many projects are on hold in Queensland?"

#### projects.milestones (~100 rows)

Tracks key delivery milestones per project with planned vs actual dates.

| Column | Type | Description |
|--------|------|-------------|
| milestone_id | STRING | e.g. MS-001 |
| project_id | STRING | FK to financials |
| milestone_name | STRING | e.g. "Site mobilisation", "Structural steel erection" |
| planned_date | DATE | Originally planned date |
| forecast_date | DATE | Current forecast date |
| actual_date | DATE | Actual completion date (NULL if not yet complete) |
| milestone_type | STRING | design, procurement, earthworks, structural, commissioning, handover |
| is_critical_path | BOOLEAN | Whether this milestone is on the critical path |
| status | STRING | completed, on_track, at_risk, delayed |
| delay_days | LONG | Days of delay (0 if on track, negative if ahead) |

**Sample questions:**
- "Which critical-path milestones are delayed by more than 30 days?"
- "What percentage of milestones across the portfolio are on track?"

#### safety.incidents (~300 rows)

Every safety incident, near miss, and investigation across all sites.

| Column | Type | Description |
|--------|------|-------------|
| incident_id | STRING | e.g. INC-0001 |
| incident_date | DATE | Date of occurrence |
| shift | STRING | day, night, afternoon |
| site_name | STRING | Construction site |
| severity | STRING | critical, high, medium, low |
| is_near_miss | BOOLEAN | Near miss vs actual incident |
| injuries | LONG | Number of people injured |
| lost_time_days | DOUBLE | Lost Time Injury (LTI) days |
| root_cause | STRING | human_error, equipment_failure, procedural, environmental, design |
| corrective_action | STRING | Action taken to prevent recurrence |
| status | STRING | reported, investigating, closed |

**Sample questions:**
- "What is the LTIFR (Lost Time Injury Frequency Rate) per site?"
- "Which root cause category has the most critical incidents?"

#### equipment.equipment_telemetry (~2,000 rows) -- External Delta

Real-time IoT sensor data from the heavy equipment fleet.

| Column | Type | Description |
|--------|------|-------------|
| equipment_id | STRING | e.g. HT-001 (haul truck), EX-005 (excavator) |
| equipment_type | STRING | haul_truck, excavator, drill, loader, dozer, grader, water_cart |
| manufacturer | STRING | Caterpillar, Komatsu, Liebherr, Hitachi, Volvo |
| engine_temp_celsius | DOUBLE | Normal: 70-95, Warning: 95-110, Critical: >110 |
| hydraulic_pressure_bar | DOUBLE | Normal: 200-350, Warning: >350 or <150 |
| fuel_level_pct | DOUBLE | 0-100% |
| operating_hours | INT | Cumulative engine hours |
| latitude, longitude | DOUBLE | GPS coordinates |
| status | STRING | operational, warning, critical, maintenance |

**Sample questions:**
- "How many pieces of equipment are in critical status right now?"
- "Which haul trucks have the highest fuel consumption?"

#### equipment.maintenance_log (~500 rows) -- External Delta

Maintenance work orders linked to equipment.

| Column | Type | Description |
|--------|------|-------------|
| work_order_id | STRING | e.g. WO-001 |
| equipment_id | STRING | FK to equipment_telemetry |
| maintenance_type | STRING | scheduled, unscheduled, breakdown, inspection |
| downtime_hours | DOUBLE | Hours of equipment downtime |
| cost_aud | DOUBLE | Total cost (parts + labour) |
| parts_cost_aud | DOUBLE | Parts/materials cost |
| labour_cost_aud | DOUBLE | Labour cost |
| priority | STRING | low, medium, high, emergency |

**Sample questions:**
- "What is the average downtime per breakdown event?"
- "Which equipment type has the highest maintenance cost per operating hour?"

#### workforce.timesheets (~5,000 rows) -- External Delta

Daily timesheet entries across all sites.

| Column | Type | Description |
|--------|------|-------------|
| employee_id | STRING | e.g. EMP-001 |
| role | STRING | operator, fitter, electrician, supervisor, labourer, engineer, safety_officer |
| site_name | STRING | Work location |
| hours_regular | DOUBLE | Max 7.6 per shift (Australian standard) |
| hours_overtime | DOUBLE | Overtime hours |
| hourly_rate_aud | DOUBLE | Base hourly rate |
| total_cost_aud | DOUBLE | regular*rate + overtime*rate*1.5 |
| leave_type | STRING | NULL, annual, sick, rdo, public_holiday |
| is_inducted | BOOLEAN | Site induction completed |

**Sample questions:**
- "What is the overtime percentage per site? Is any site over 20%?"
- "How much are we spending on uninducted workers?"

#### procurement.materials (~1,500 rows) -- Iceberg UniForm

Material procurement orders with supplier pricing.

| Column | Type | Description |
|--------|------|-------------|
| material_name | STRING | e.g. "Structural steel beams", "Ready-mix concrete 40MPa" |
| category | STRING | Steel, Concrete, Fuel, Geosynthetics, Precast, Safety, Aggregate, Electrical |
| supplier | STRING | Supplier name |
| unit_price_aud | DOUBLE | Price per unit |
| lead_time_days | INT | Days from order to delivery |
| price_trend | STRING | increasing, stable, decreasing |
| availability | STRING | good, moderate, limited, out_of_stock |

**Sample questions:**
- "Which materials have increasing prices and limited availability?"
- "What is our total steel spend across the portfolio?"

#### environmental.emissions (~2,000 rows) -- Iceberg UniForm

Environmental monitoring data for EPA compliance.

| Column | Type | Description |
|--------|------|-------------|
| monitor_type | STRING | dust_pm10, dust_pm2_5, noise_db, water_ph, water_turbidity, vibration, co2 |
| measurement_value | DOUBLE | Measured value |
| threshold_value | DOUBLE | Regulatory threshold |
| is_exceedance | BOOLEAN | Did this reading exceed the limit? |
| wind_direction | STRING | N, NE, E, SE, S, SW, W, NW |
| action_taken | STRING | NULL, water_cart_deployed, work_stopped, barrier_installed, etc. |

**Sample questions:**
- "Which sites have the highest dust exceedance rate?"
- "Are noise levels consistently above limits during night shifts?"

#### quality.inspections (~1,000 rows) -- Iceberg UniForm

Quality control inspections and ITP (Inspection and Test Plan) records.

| Column | Type | Description |
|--------|------|-------------|
| inspection_type | STRING | hold_point, witness_point, audit, material_test, weld_test, concrete_test |
| result | STRING | pass, fail, conditional, pending |
| defect_category | STRING | NULL, dimensional, material, workmanship, documentation, safety |
| rework_required | BOOLEAN | Whether rework was needed |
| rework_cost_aud | DOUBLE | Cost of rework if applicable |
| inspector | STRING | Inspector name |
| certifications | STRING | ISO 9001, AS/NZS 4801, or specific weld/test certs |

**Sample questions:**
- "What is the first-pass inspection rate per site?"
- "How much are we spending on rework across the portfolio?"

---

## Domain 2: Supply Chain Pipeline (Medallion Architecture)

The supply chain domain demonstrates a **Bronze > Silver > Gold** lakehouse pipeline
processing logistics data for the same CIMIC sites.

### Pipeline Flow

```
  RAW FILES (UC Volume)              BRONZE                  SILVER                  GOLD
  /Volumes/.../raw_data/        (append-only raw)       (cleaned, typed)       (aggregated KPIs)
  +---------------------+      +-----------------+     +----------------+     +------------------+
  | gps_pings.csv       |----->| bronze.         |---->| silver.        |---->| gold.            |
  |                     |      | gps_pings       |     | fleet_positions|     | v_fleet_util.    |
  +---------------------+      +-----------------+     +----------------+     +------------------+
  | delivery_receipts/  |----->| bronze.         |---->| silver.        |---->| gold.            |
  |   *.json            |      | delivery_       |     | deliveries     |     | supplier_        |
  +---------------------+      | receipts        |     +----------------+     | scorecard        |
  | warehouse_stock.csv |----->| bronze.         |---->| silver.        |---->| gold.            |
  |                     |      | warehouse_      |     | inventory_     |     | inventory_       |
  +---------------------+      | stock           |     | snapshots      |     | health           |
  | supplier_invoices/  |----->| bronze.         |---->| silver.        |---->| gold.            |
  |   *.csv             |      | supplier_       |     | invoices       |     | v_invoice_aging  |
  +---------------------+      | invoices        |     +----------------+     +------------------+
                                                                              | gold.            |
                                                                              | site_operations_ |
                                                                              | summary (VIEW)   |
                                                                              +------------------+
```

### Bronze Layer (supply_chain_bronze)

Raw data as-is from source files. Every row gets two metadata columns:
- `_ingested_at`: Timestamp of when the row was ingested
- `_source_file`: Full path to the source file (for lineage)

| Table | Source Format | ~Rows per Batch |
|-------|-------------|-----------------|
| gps_pings | CSV | ~200 |
| delivery_receipts | JSON | ~100 |
| warehouse_stock | CSV | ~80 |
| supplier_invoices | CSV | ~500 |

### Silver Layer (supply_chain_silver)

Cleaned, typed, and enriched data with business rules applied:

| Table | Transformations Applied |
|-------|------------------------|
| fleet_positions | Parse timestamps, add `is_moving` (speed > 2 km/h), add `is_idling` (engine on but not moving), deduplicate by ping_id |
| deliveries | Cast delivery_date to DATE, add `cost_variance_pct` (unit_price vs category avg), add `is_damaged` flag, add `cost_validated` check |
| inventory_snapshots | Parse timestamps, add `stock_status` (critical/low/adequate/surplus), add `days_since_replenishment` |
| invoices | Cast dates, add `gst_validated` (check 10% GST rule), add `is_overdue`, add `days_until_due` |

### Gold Layer (supply_chain_gold)

Business-ready aggregations and scorecards:

| Object | Type | Description |
|--------|------|-------------|
| supplier_scorecard | TABLE | Composite supplier scoring: delivery quality + cost accuracy + payment history. Tiered as Gold/Silver/Bronze/At Risk. |
| inventory_health | TABLE | Latest inventory snapshot with stock status classification |
| v_fleet_utilisation_daily | VIEW | Daily vehicle utilisation: moving %, idling %, fuel trends |
| v_delivery_performance | VIEW | Supplier delivery KPIs by destination site |
| invoice_aging | VIEW | Invoice aging buckets (current, 30-day, 60-day, 90-day+) with payment risk |
| site_operations_summary | VIEW | Cross-domain site dashboard combining fleet, deliveries, inventory, invoices |

---

## Views and Materialized Views

### Standard Views (Manufacturing)

| View | Schema | Purpose |
|------|--------|---------|
| v_project_risk_matrix | projects | Multi-factor risk scoring combining financials, milestones, safety, and procurement data. Produces a 0-100 risk score and RAG rating per project. |
| v_financials_by_division | projects | Division-level financial rollup with average EVM indices and over-budget counts. |
| v_safety_summary | safety | Per-site safety KPIs: incident counts by severity, LTI days, investigation completion rate. |
| v_equipment_status | equipment | Live equipment health combining latest telemetry reading with maintenance history. |
| v_procurement_analytics | procurement | Supplier and material analytics: spend concentration, lead time distribution, price volatility, supply risk. |
| v_workforce_utilisation | workforce | Per-site workforce summary: headcount, overtime percentage, labour cost, uninducted worker shifts. |
| v_compliance_dashboard | environmental | Environmental compliance dashboard: exceedance rates by site and monitor type. |

### Materialized Views (Manufacturing)

Created via SQL Warehouse (serverless) for performance:

| MV | Schema | Refreshes | Purpose |
|----|--------|-----------|---------|
| mv_safety_summary | safety | On demand | Pre-aggregated safety KPIs per site. Avoids scanning incident detail for dashboard queries. |
| mv_financials_summary | projects | On demand | Pre-aggregated financials per division. Powers executive dashboards. |
| mv_procurement_summary | procurement | On demand | Pre-aggregated procurement spend per supplier and category. |

---

## The Customer Scenario

### Imagine you are the CIMIC Chief Operating Officer...

It is Q3 2025. You have 20 active projects worth a combined AUD 8.5 billion. Your board wants
answers to three questions:

**1. "Are we going to deliver on time and on budget?"**

Query `projects.financials` for SPI and CPI across the portfolio. Join with `projects.milestones`
to see which critical-path milestones are delayed. Use `v_project_risk_matrix` to get a single
risk score per project that factors in cost overruns, schedule delays, safety incidents, and
supply chain issues.

**2. "Is anyone getting hurt?"**

Query `safety.incidents` grouped by severity and site. Check the trend -- are incident counts
going up or down month over month? Use `v_safety_summary` for a per-site snapshot. Cross-reference
with `workforce.timesheets` to calculate LTIFR (Lost Time Injury Frequency Rate = LTIs per
million hours worked).

**3. "Where is the money going?"**

Join `procurement.materials` with `projects.financials` to see material spend by project. Check
`workforce.timesheets` for labour cost by site. Look at `equipment.maintenance_log` for
unplanned maintenance spend. Use the supply chain gold layer to score suppliers and identify
which ones are costing you money through damaged deliveries or disputed invoices.

### For the AI Workshop Demo

This dataset is specifically designed to be queried by:

1. **Databricks Genie API** -- A natural language interface where executives ask questions in
   plain English. The Genie Space has all 9 tables pre-configured with join specs, example
   queries, and business measures.

2. **Microsoft Fabric Data Agent** -- A Fabric-native AI agent that queries the same data
   via mirrored Databricks catalog. Demonstrates Microsoft's approach to conversational BI.

Both are managed by **Azure AI Foundry** to compare orchestration patterns, evaluate response
quality, and demonstrate enterprise AI governance.

---

## Data Volume Summary

| Domain | Schema | Tables | Views | MVs | ~Total Rows |
|--------|--------|--------|-------|-----|-------------|
| Manufacturing | projects | 2 | 2 | 1 | ~120 |
| Manufacturing | safety | 1 | 1 | 1 | ~300 |
| Manufacturing | equipment | 2 | 1 | 0 | ~2,500 |
| Manufacturing | workforce | 1 | 1 | 0 | ~5,000 |
| Manufacturing | procurement | 1 | 1 | 1 | ~1,500 |
| Manufacturing | environmental | 1 | 1 | 0 | ~2,000 |
| Manufacturing | quality | 1 | 0 | 0 | ~1,000 |
| Supply Chain | bronze | 4 | 0 | 0 | ~880/batch |
| Supply Chain | silver | 4 | 0 | 0 | ~880/batch |
| Supply Chain | gold | 2 | 4 | 0 | ~varies |
| **Total** | | **19** | **11** | **3** | **~14,000+** |

---

## Site Reference

All data references these CIMIC project sites:

| Site Name | State | Division | Project Type | Example Project |
|-----------|-------|----------|-------------|-----------------|
| Sydney Metro West | NSW | CPB Contractors | rail | Underground rail tunnel and station construction |
| WestConnex M4-M5 | NSW | CPB Contractors | highway | Major motorway tunnel link in Sydney's inner west |
| Cross River Rail | QLD | CPB Contractors | rail | Brisbane underground rail crossing |
| Bowen Basin Mine | QLD | Thiess | mining | Coal mine expansion and processing |
| Pilbara Iron Ore | WA | Thiess | mining | Iron ore mine infrastructure |
| Melbourne Metro | VIC | CPB Contractors | rail | Metro tunnel and station box construction |
| Snowy 2.0 | NSW | CPB Contractors | water | Pumped hydro expansion in the Snowy Mountains |

---

## How to Query

### From Databricks SQL

```sql
-- Portfolio risk overview
SELECT * FROM adb_cimic_aiws_dev_ws.projects.v_project_risk_matrix
ORDER BY risk_score DESC;

-- Safety KPIs per site
SELECT * FROM adb_cimic_aiws_dev_ws.safety.v_safety_summary;

-- Supplier scorecard (gold layer)
SELECT * FROM adb_cimic_aiws_dev_ws.supply_chain_gold.supplier_scorecard
ORDER BY supplier_score DESC;

-- Cross-domain: projects with high cost AND safety risk
SELECT r.project_name, r.risk_score, r.risk_rating,
       r.cost_utilisation_pct, r.critical_incidents
FROM adb_cimic_aiws_dev_ws.projects.v_project_risk_matrix r
WHERE r.risk_rating IN ('High', 'Critical')
ORDER BY r.risk_score DESC;
```

### From Genie API

Ask in natural language:
- "Which projects are over budget?"
- "Show me safety incidents at the Sydney Metro West site"
- "What is the average lead time for structural steel?"
- "Compare overtime costs across all sites"

### From Fabric Data Agent

Same natural language queries, routed through the mirrored Databricks catalog in Fabric.

---

## Genie Spaces (Virtual AI Agents)

The workshop deploys **6 Genie Spaces**, each acting as a purpose-built AI agent for a
specific operational domain. Each space is configured via the Genie API v2 with a
serialized_space payload containing table references, join specifications, example SQL
queries, curated sample questions, and benchmark evaluation sets.

### Architecture

```
                        Genie API v2
                        (serialized_space)
                              |
      +-----------+-----------+-----------+-----------+-----------+
      |           |           |           |           |           |
  +-------+  +-------+  +--------+  +--------+  +--------+  +--------+
  | All-  |  | Safety|  | Equip. |  | Procure|  | Work-  |  | Exec.  |
  | in-One|  | Agent |  | Agent  |  | Agent  |  | force  |  | Agent  |
  |       |  |       |  |        |  |        |  | Agent  |  |        |
  | 9 tbl |  | 4 tbl |  | 3 tbl  |  | 4 tbl  |  | 3 tbl  |  | 3 tbl  |
  | 9 bm  |  | 5 bm  |  | 5 bm   |  | 5 bm   |  | 5 bm   |  | 6 bm   |
  +-------+  +-------+  +--------+  +--------+  +--------+  +--------+
      |           |           |           |           |           |
      +-----------|-----------|-----------|-----------|-----------|-----+
                  |           |           |           |           |
              Unity Catalog: adb_cimic_aiws_dev_ws
              (9 manufacturing tables + views + MVs)
```

### Space Details

#### 1. CIMIC Project Intelligence (All-in-One)

The master space with access to all 9 manufacturing tables. Designed for cross-domain
analysis and executive-level queries that span safety, equipment, procurement, workforce,
and financials.

| Property | Value |
|----------|-------|
| Tables | All 9 manufacturing tables |
| Join Specs | 7 (every FK relationship) |
| Example SQLs | 16 |
| Sample Questions | 12 |
| Benchmarks | 9 |
| Persona | Data analyst or project director |

**Sample questions:**
- "Which projects are over budget and have critical safety incidents?"
- "What is the total portfolio value by division?"
- "Show equipment with engine temperatures above warning threshold"

#### 2. CIMIC Safety and Compliance Agent

Focused on workplace health and safety (WHS), environmental compliance, and quality
inspections. Designed for HSE officers and safety managers.

| Property | Value |
|----------|-------|
| Tables | incidents, emissions, inspections, financials |
| Benchmarks | 5 |
| Persona | Safety manager / HSE officer |

**Sample questions:**
- "What is the LTIFR per site this quarter?"
- "Which sites have dust exceedances above regulatory limits?"
- "Show all critical incidents that are still under investigation"
- "What is the first-pass inspection rate by project?"

#### 3. CIMIC Equipment and Fleet Agent

Manages the heavy equipment fleet -- telemetry monitoring, maintenance scheduling,
utilisation analysis, and breakdown cost tracking.

| Property | Value |
|----------|-------|
| Tables | equipment_telemetry, maintenance_log, financials |
| Benchmarks | 5 |
| Persona | Fleet manager / maintenance planner |

**Sample questions:**
- "Which excavators have logged more than 5000 operating hours?"
- "What is the average downtime per breakdown event by equipment type?"
- "Show me equipment with hydraulic pressure outside normal range"
- "What is the maintenance cost per operating hour for haul trucks?"

#### 4. CIMIC Procurement and Supply Chain Agent

Handles material procurement, supplier performance, inventory management, and cost
analysis across the project portfolio.

| Property | Value |
|----------|-------|
| Tables | materials, supply chain gold tables, financials |
| Benchmarks | 5 |
| Persona | Procurement lead / supply chain manager |

**Sample questions:**
- "Which suppliers have the longest lead times for structural steel?"
- "What materials have increasing prices and limited availability?"
- "Show total procurement spend by project and category"
- "Which suppliers are rated At Risk in the supplier scorecard?"

#### 5. CIMIC Workforce and Labour Agent

Covers workforce planning, timesheet analysis, overtime monitoring, and induction
compliance across all sites.

| Property | Value |
|----------|-------|
| Tables | timesheets, financials, milestones |
| Benchmarks | 5 |
| Persona | HR manager / workforce planner |

**Sample questions:**
- "What is the overtime percentage per site? Flag any over 20%"
- "How many uninducted workers logged shifts last month?"
- "What is the total labour cost per project?"
- "Show average hours by role across all sites"

#### 6. CIMIC Executive Portfolio Agent

Strategic oversight for senior leadership -- portfolio-level financials, risk scoring,
milestone tracking, and cross-domain KPIs.

| Property | Value |
|----------|-------|
| Tables | financials, milestones, v_project_risk_matrix |
| Benchmarks | 6 |
| Persona | COO / project director / board member |

**Sample questions:**
- "Which projects have a CPI below 0.9?"
- "What is the average SPI across the portfolio by division?"
- "Show all critical-path milestones delayed by more than 30 days"
- "Give me a risk summary for the top 5 highest-value projects"

### Genie Space Benchmarks

Each space includes benchmark questions with expected SQL answers. Benchmarks define the
"ground truth" for evaluating how well the Genie LLM translates natural language to SQL.

**How benchmarks work:**
1. Each benchmark has a `question` (natural language) and an `answer` (expected SQL)
2. When you run an evaluation from the Genie Space UI, the system sends each benchmark
   question through the LLM, compares the generated SQL to the expected SQL, and scores
   accuracy
3. Results show which questions the LLM answered correctly, which it got wrong, and where
   there are context gaps (missing table/column descriptions, ambiguous joins, etc.)

**Running benchmark evaluations:**
- Navigate to the Genie Space in the Databricks UI
- Click the "Evaluate" tab
- Click "Run Benchmarks"
- Review results and iterate on instructions/examples as needed

NOTE: Benchmark evaluations can only be triggered from the UI. The evaluation API
endpoints are not publicly available.

---

## Deployment Guide

### Prerequisites

- Databricks CLI v0.200+ installed (`databricks --version`)
- Authentication configured (`~/.databrickscfg` or environment variables)
- Unity Catalog enabled on the target workspace
- An existing all-purpose cluster or Serverless enabled
- An ADLS storage account for external Delta tables (optional)

### Deploying with DABS (Databricks Asset Bundles)

The entire workshop is packaged as a DABS bundle. This is the recommended way to deploy
to any environment.

```
databricks/
  databricks.yml          # Bundle config with variables and targets
  resources/
    jobs.yml              # Job definitions (2 multi-task workflows)
  src/                    # Manufacturing notebooks
  pipeline/               # Medallion pipeline notebooks
```

#### Step 1: Configure Your Target

Edit `databricks.yml` and fill in the target-specific variables:

```yaml
targets:
  dev:
    variables:
      databricks_host: "https://adb-XXXXXXXXX.azuredatabricks.net"
      cluster_id: "your-cluster-id"
      catalog_name: your_catalog
      external_storage_path: "abfss://container@account.dfs.core.windows.net/path"
```

#### Step 2: Validate

```bash
cd databricks
databricks bundle validate -t dev
```

#### Step 3: Deploy

```bash
databricks bundle deploy -t dev
```

This uploads all notebooks and creates two Jobs in the workspace:
- **CIMIC Manufacturing - Initial Setup**: Schema creation, data generation, advanced
  objects, Genie Space creation, and domain agent deployment
- **CIMIC Supply Chain - Medallion Pipeline**: Source simulation, bronze ingestion,
  silver transformation, gold aggregation

#### Step 4: Run

```bash
# Run the manufacturing setup (one-time)
databricks bundle run cimic_data_setup -t dev

# Run the supply chain pipeline
databricks bundle run supply_chain_pipeline -t dev
```

#### Deploying to Production

```bash
# Deploy to production target
databricks bundle deploy -t production

# Run setup
databricks bundle run manufacturing_setup -t production
databricks bundle run supply_chain_pipeline -t production
```

The DABS bundle handles:
- Uploading notebooks to the correct workspace paths
- Creating/updating Jobs with the right cluster and parameters
- Variable substitution per target (catalog, warehouse, cluster, storage paths)

### Multi-Environment Strategy

```
  feature/sg-dbx branch
         |
         v
  +------+------+
  |  DABS       |
  |  bundle     |
  |  deploy     |
  +------+------+
         |
    +----+----+----+
    |         |    |
    v         v    v
  [DEV]    [STG]  [PROD]
  - dev catalog   - prod catalog
  - dev cluster   - prod cluster
  - dev ADLS path - prod ADLS path
  - dev Genie     - prod Genie
    spaces          spaces
```

Each environment gets its own:
- Unity Catalog catalog (isolated data)
- Cluster or Serverless compute
- ADLS external storage path
- Genie Spaces (created fresh per environment)
- Jobs (managed by DABS)

### What Gets Deployed

| Component | Deployment Method | Per-Environment |
|-----------|------------------|-----------------|
| Notebooks | DABS bundle deploy | Uploaded to workspace |
| Jobs | DABS bundle deploy | Created with target variables |
| Tables/Schemas | Job run (01_create_schema) | Created in target catalog |
| Sample Data | Job run (02_generate_data) | Inserted into target tables |
| Views/MVs | Job run (04_advanced_objects) | Created in target catalog |
| Genie Spaces | Job run (03_setup_genie, 05_domain_genie_agents) | Created via API per workspace |
| Materialized Views | SQL Warehouse API (within notebook) | Requires Serverless or Pro warehouse |

### Pipeline Jobs

#### Manufacturing Setup Job

A one-time setup workflow with 5 tasks:

```
  create_schema --> generate_data --> advanced_objects
                                  --> setup_genie --> domain_genie_agents
```

| Task | Notebook | What It Does |
|------|----------|--------------|
| create_schema | 01_create_schema.py | Creates 7 schemas, 9 tables (managed Delta, external Delta, Iceberg) |
| generate_data | 02_generate_data.py | Populates all tables with ~12,450 rows of realistic data |
| advanced_objects | 04_advanced_objects.py | Creates 7 views, attempts 3 MVs, creates 2 metric views |
| setup_genie | 03_setup_genie.py | Creates the all-in-one Genie Space with 9 tables |
| domain_genie_agents | 05_domain_genie_agents.py | Creates 5 domain-specific Genie agents |

#### Supply Chain Pipeline Job

A repeatable medallion pipeline with 4 tasks:

```
  source_simulator --> bronze_ingestion --> silver_transform --> gold_aggregation
```

| Task | Notebook | What It Does |
|------|----------|--------------|
| source_simulator | 00_source_simulator.py | Generates ~880 rows of CSV/JSON into UC Volume |
| bronze_ingestion | 01_bronze_ingestion.py | Ingests raw files into 4 bronze tables |
| silver_transform | 02_silver_transform.py | Cleans and enriches into 4 silver tables |
| gold_aggregation | 03_gold_aggregation.py | Aggregates into 2 gold tables + 4 views |

Scheduled: Daily at 6:00 AM AEST (configurable in jobs.yml).

---

## Technical Notes

### Storage Format Gotchas

**Iceberg UniForm tables** require both TBLPROPERTIES:
```sql
TBLPROPERTIES (
  'delta.enableIcebergCompatV2' = 'true',
  'delta.universalFormat.enabledFormats' = 'iceberg'
)
```

**External Delta tables** on ADLS: Use `INSERT OVERWRITE` for data refresh, never
`DROP TABLE + CREATE`. Dropping destroys the LOCATION and TBLPROPERTIES.

**Materialized Views** cannot be created from general-purpose compute (clusters). They
require a Serverless or Pro SQL Warehouse. The notebooks attempt creation but skip
gracefully on cluster, falling back to regular views.

### Unity Catalog Restrictions

- `input_file_name()` is not supported -- use `_metadata.file_path` instead
- Public DBFS root (`/tmp/`, `dbfs:/`) may be disabled -- use UC Volumes:
  `/Volumes/{catalog}/{schema}/{volume}/`
- Type mismatches on append (e.g., inferred INT vs table LONG) cause merge errors.
  The pipeline uses a `_cast_to_table()` helper to prevent this.

### Genie API v2 Format

- All IDs: 32-char lowercase hex (UUID without hyphens), sorted alphabetically
- `benchmarks` is a top-level key in serialized_space (sibling to `instructions`,
  not nested inside it)
- Benchmark answer format: `{"format": "SQL", "content": ["SELECT ..."]}`
- Rate limits: 5 queries/min via API, 20 queries/min via UI
- Evaluation runs can only be triggered from the UI

### Data Generation

All data uses `dict()` + `pandas.DataFrame` intermediate instead of `Row()` objects.
This prevents Spark schema inference errors (`CANNOT_MERGE_TYPE`,
`DELTA_FAILED_TO_MERGE_FIELDS`) that occur when mixed Python int/float types are
passed to `spark.createDataFrame()`.

---

## Integration with Azure AI Foundry

This Databricks deployment is one half of the CIMIC AI Workshop. The other half is
managed by Microsoft Fabric and Azure AI Foundry:

```
  +--------------------+          +---------------------+
  | Databricks         |          | Microsoft Fabric    |
  | (this deployment)  |          | (Katherine's side)  |
  |                    |          |                     |
  | Unity Catalog      |  mirror  | Mirrored Databricks |
  | 9 mfg tables  -----+--------->  Catalog             |
  | Medallion pipeline |          |                     |
  | 6 Genie Spaces     |          | 6 Data Agents       |
  | Genie API          |          | Data Agent API      |
  +--------+-----------+          +----------+----------+
           |                                 |
           +----------------+----------------+
                            |
                   +--------+--------+
                   | Azure AI Foundry|
                   |                 |
                   | Orchestrates    |
                   | both Genie API  |
                   | and Data Agent  |
                   | Compares pros   |
                   | and cons        |
                   +-----------------+
```

### What Foundry Does

Azure AI Foundry sits above both Databricks Genie and Fabric Data Agent as an
orchestration layer. It can:

1. Route natural language queries to either Genie API or Data Agent
2. Evaluate response quality from each
3. Apply enterprise governance (content filtering, PII detection)
4. Chain multiple agent calls together (e.g., ask Genie for data, then summarise)

### Genie API vs Fabric Data Agent (Summary)

| Capability | Genie API | Fabric Data Agent |
|------------|-----------|-------------------|
| Data Source | Unity Catalog tables | Fabric Lakehouse, SQL, mirrored catalogs |
| Query Language | SQL (generated by LLM) | SQL / DAX |
| Deployment | API-first (serialized_space) | Portal + limited API |
| Benchmarks | Built-in (per space) | Manual evaluation |
| Multi-table Joins | Configurable join specs | Semantic model relationships |
| Custom Instructions | Per-space system prompt | Per-agent instructions |
| Rate Limits | 5 q/min API, 20 q/min UI | Varies by Fabric capacity |
| Best For | Technical teams, API integration | Business users, Power BI integration |

---

## Quick Reference

### File Layout

```
databricks/
  databricks.yml                    # DABS bundle config
  resources/
    jobs.yml                        # Job definitions
  src/
    01_create_schema.py             # Table creation (9 tables, 7 schemas)
    02_generate_data.py             # Data generation (~12,450 rows)
    03_setup_genie.py               # All-in-one Genie Space
    04_advanced_objects.py           # Views, MVs, metric views
    05_domain_genie_agents.py       # 5 domain-specific agents
  pipeline/
    00_source_simulator.py          # Generate raw files
    01_bronze_ingestion.py          # Bronze layer
    02_silver_transform.py          # Silver layer
    03_gold_aggregation.py          # Gold layer
  notebooks/
    demo_genie_api.py               # API demo scenarios
  docs/
    dataset-wiki.md                 # This file
    comparison.md                   # Genie vs Fabric scoring
    genie-api-wiki.md               # API capabilities
    genie-api-guide.md              # API reference
    fabric-data-agent-guide.md      # Fabric setup guide
```

### Key Commands

```bash
# Deploy to dev
cd databricks && databricks bundle deploy -t dev

# Run manufacturing setup
databricks bundle run manufacturing_setup -t dev

# Run supply chain pipeline
databricks bundle run supply_chain_pipeline -t dev

# Check job status
databricks jobs list --output json | jq '.jobs[] | {name, job_id}'

# Query Genie Space via API
curl -X POST "https://{host}/api/2.0/genie/spaces/{space_id}/conversations" \
  -H "Authorization: Bearer {token}" \
  -d '{"content": "Which projects are over budget?"}'
```
