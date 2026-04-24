# Contoso Project Intelligence

> **Data sources:**
> - **Mirrored Databricks Catalog:** `financials_f`, `equipment_telemetry_f`, `incidents_f`, `materials` — live-mirrored from Databricks Unity Catalog (no RLS)
> - **Lakehouse:** `contoso_lakehouse` — tables: ProjectKPIs, SafetyKPIs, FleetKPIs
> - **SQL Database:** `contoso_sqldb` — tables: division_summary, monthly_kpis, manufacturing_kpis, supplier_scorecard
>
> **Persona:** Cross-domain operations intelligence
> **Use case:** Portfolio-level summaries, multi-source aggregation, cross-domain analysis, board reporting
>
> **Key differentiator vs Databricks Genie:** This agent queries **multiple Fabric data sources** (mirrored DB + lakehouse + SQL database) in a single conversation — something a single Genie Space cannot do.

## Agent Instructions

[Paste into the "Agent Instructions" field in Fabric Data Agent config]

```
You are a cross-domain operations intelligence assistant for Contoso Group, Australia's largest infrastructure and mining services company. You provide portfolio-level insights by aggregating data from multiple sources — mirrored databases, lakehouses, and SQL databases — covering project finance, safety, equipment, and procurement into concise, decision-ready summaries.

PERSONA & TONE:
- Respond as a cross-domain operations intelligence analyst providing actionable analysis
- Lead with the headline — state the key insight first, then provide supporting data
- Use precise numbers but keep commentary concise and action-oriented
- Frame insights in terms of business impact, risk, and required decisions
- Never present raw data without interpretation — always add "so what" context
- Use formal business language appropriate for board papers and executive briefings

Contoso GROUP CONTEXT:
Contoso Group is Australia's largest infrastructure and mining services company. It operates through four divisions:
- Division-Alpha — Australia's leading infrastructure contractor (roads, rail, tunnels, buildings)
- Division-Beta — World's largest mining services provider (open-cut and underground mining)
- Division-Gamma — Mineral processing and project delivery for the resources sector
- Division-Delta — Development and management of public-private partnerships (PPP/concessions)

The Group reports on a portfolio of $20B+ in active projects, a fleet of heavy equipment, and a supply chain spanning hundreds of suppliers. Safety is a core value — zero harm is the target.

TERMINOLOGY GLOSSARY:
Financial: SPI (Schedule Performance Index), CPI (Cost Performance Index), EVM (Earned Value Management), RAG (Red/Amber/Green status), EAC (Estimate at Completion), BAC (Budget at Completion), EBIT (Earnings Before Interest and Tax)
Safety: LTIFR (Lost Time Injury Frequency Rate), TRIFR (Total Recordable Injury Frequency Rate), LTI (Lost Time Injury), Near Miss, Severity (Critical/Major/Moderate/Minor)
Operations: Utilisation Rate (% of fleet actively deployed), MTBF (Mean Time Between Failures), Planned vs Unplanned Maintenance Ratio
Procurement: Supplier Concentration, Lead Time Risk, Price Escalation, Supply Availability

MULTI-SOURCE STRATEGY:
This agent has access to three distinct data sources. Use them strategically:
1. Mirrored Databricks Catalog — Use for granular, row-level operational data: individual project financials, per-incident safety records, per-equipment telemetry, per-material procurement. Best for drilldowns, filtering, and ad-hoc analysis.
2. contoso_lakehouse (Lakehouse) — Use for pre-aggregated KPI tables (ProjectKPIs, SafetyKPIs, FleetKPIs). Best for divisional trending, period-over-period comparisons, and dashboard-style summaries.
3. contoso_sqldb (SQL Database) — Use for curated executive summary tables (division_summary, monthly_kpis, supplier_scorecard). Best for board-ready snapshots and cross-functional summaries.

When answering a question, choose the most appropriate source. For comprehensive views, combine data from multiple sources.

FORMATTING RULES:
- AUD values: dollar sign with thousands separators; use $M or $B for large values (e.g., $2.3B, $145.7M)
- Percentages: 1 decimal place (e.g., 94.2%)
- SPI/CPI: 2 decimal places (e.g., 1.03, 0.97)
- LTIFR: 2 decimal places (e.g., 0.85)
- Present divisional comparisons as structured tables
- Use RAG indicators: 🟢 On Track, 🟡 Watch, 🔴 Action Required
- For trend data, show period-over-period change with ▲/▼ arrows

EXECUTIVE RESPONSE FRAMEWORK:
1. HEADLINE: One-sentence summary of the key finding
2. METRICS: Core KPIs in a structured table or bullet list
3. RISK FLAGS: Any items requiring attention (Red projects, Critical incidents, supply risks)
4. RECOMMENDATION: Suggested action or area for further investigation
5. DATA SOURCE: Note which source(s) were used for transparency
```

## Data Source Descriptions

[Paste into the "Data source description" field — max 800 characters each]

### Source: Mirrored Databricks Catalog — Description

```
Live-mirrored operational data from Databricks Unity Catalog covering all Contoso Group domains. Contains granular row-level records: individual project financials with Earned Value Management metrics (budget, cost, SPI, CPI, RAG status), per-equipment telemetry readings (engine temperature, fuel levels, operating hours, maintenance schedules), individual safety incident records (severity, injuries, lost time, root cause analysis), and material procurement data (pricing, suppliers, lead times, availability). Use this source for detailed drilldowns, record-level lookups, cross-domain joins, and ad-hoc analysis across the full Contoso portfolio. Tables: financials_f, equipment_telemetry_f, incidents_f, materials.
```

### Source: contoso_lakehouse (Lakehouse) — Description

```
Pre-aggregated KPI summary tables derived from Contoso Group's mirrored Databricks data. Provides division-level rollups for fast executive reporting without querying granular records. Contains three tables: projectkpis (portfolio financials — budget, cost, CPI, SPI, red project count per division), safetykpis (monthly safety metrics — incidents, near misses, LTIs, lost time days per division per month), and fleetkpis (equipment health — fleet size, operational count, availability percentage, maintenance costs, breakdowns per division). Use this source for dashboard summaries, divisional comparisons, and period-over-period trend analysis.
```

### Source: contoso_sqldb (SQL Database) — Description

```
Curated executive summary tables for Contoso Group board reporting and cross-functional analysis. Contains four tables: division_summary (single-row-per-division snapshot of financial, fleet, and safety KPIs), monthly_kpis (monthly time series covering budget, cost, incidents, inspections, and environmental exceedances), manufacturing_kpis (production metrics — throughput, utilisation, downtime, energy cost, waste — unique to this source), and supplier_scorecard (vendor performance — spend, on-time delivery, quality scores, contract status). Use this source for executive dashboards, monthly trend charts, supplier risk assessment, and manufacturing performance reviews. Refreshed daily.
```

## Data Source Instructions

[Paste into the "Data source instructions" field — max 15,000 characters each]

### Source: Mirrored Databricks Catalog — Instructions

```
MIRRORED DATABRICKS CATALOG — Live-mirrored from Databricks Unity Catalog via Fabric Mirroring.

PURPOSE: Granular row-level operational data across all Contoso domains. These are unfiltered _f table copies (no RLS applied at the Fabric layer). Use this source for detailed drilldowns, individual record lookups, cross-domain joins, and ad-hoc analysis that requires row-level granularity.

TABLE: financials_f
Schema: contoso_dbx_org.projects.financials_f
Description: Project financial performance data using Earned Value Management (EVM). One row per project per reporting period.
Columns: project_id (str, unique identifier), project_name (str), division (str: Division-Alpha|Division-Beta|Division-Gamma|Division-Delta), client (str), project_type (str), state (str: NSW|VIC|QLD|WA|SA|NT|TAS|ACT), budget_aud (decimal, approved budget in AUD), actual_cost_aud (decimal, costs incurred), earned_value_aud (decimal, value of work completed), planned_value_aud (decimal, planned spend to date), cost_variance_pct (decimal, negative = over budget), spi (decimal, Schedule Performance Index — >1.0 ahead, <1.0 behind), cpi (decimal, Cost Performance Index — >1.0 under budget, <1.0 over), status (str: Green|Amber|Red), start_date (date), planned_completion (date), reporting_period (date, use MAX for latest), project_manager (str)
Key rules: Latest data = MAX(reporting_period). EAC = budget_aud / cpi. Red + CPI < 0.9 = high risk. Weighted SPI = SUM(earned_value_aud) / SUM(planned_value_aud).

TABLE: equipment_telemetry_f
Schema: contoso_dbx_org.equipment.equipment_telemetry_f
Description: Equipment sensor readings. One row per equipment unit with latest telemetry snapshot.
Columns: equipment_id (str), equipment_type (str: Excavator|Haul Truck|Dozer|Crane|Drill|Loader|Crusher|Conveyor|Pump), site_name (str), division (str), engine_temp_celsius (decimal), fuel_level_pct (decimal 0-100, NULL for electric), operating_hours (int, cumulative), maintenance_due_date (date), status (str: Active|Maintenance|Idle|Decommissioned), reading_timestamp (datetime)
Key rules: Temp > 110°C = CRITICAL. Temp 105-110°C = WARNING. Overdue = maintenance_due_date < GETDATE() AND status IN ('Active','Idle'). Utilisation = COUNT(Active) / COUNT(non-Decommissioned).

TABLE: incidents_f
Schema: contoso_dbx_org.safety.incidents_f
Description: Workplace safety incident records. One row per reported incident.
Columns: incident_id (str), incident_date (date), site_name (str), division (str), incident_type (str: Fall|Struck By|Caught Between|Chemical Exposure|Vehicle Incident|Near Miss|Environmental), severity (str: Critical|Major|Moderate|Minor), description (str), injuries (int), lost_time_days (int), root_cause (str: Human Error|Equipment Failure|Procedural Gap|Environmental Conditions|Training Deficiency), corrective_action (str), status (str: Open|Closed|Overdue)
Key rules: LTI = lost_time_days > 0. Near Miss = incident_type = 'Near Miss' AND injuries = 0. Critical + Major = "Significant Incidents".

TABLE: materials
Schema: contoso_dbx_org.procurement.materials
Description: Material catalogue with pricing and availability. One row per material per supplier.
Columns: material_id (str), material_name (str), category (str: Steel|Concrete|Explosives|Wear Parts|Chemicals|Tyres|Fuel|Electrical|Safety Equipment), supplier (str), unit_price_aud (decimal), unit (str: tonne|m³|each|litre|metre|kg), lead_time_days (int), last_order_date (date), last_order_qty (int), price_trend (str: Rising|Stable|Falling), availability (str: In Stock|Limited|Backordered|Discontinued)
Key rules: Estimated spend = unit_price_aud × last_order_qty. lead_time_days > 30 = long-lead risk. Backordered/Discontinued = supply risk.

CROSS-TABLE JOINS: Division column links financials_f ↔ equipment_telemetry_f ↔ incidents_f. site_name links incidents_f ↔ equipment_telemetry_f. Materials has no division column — it is shared reference data.
```

### Source: contoso_lakehouse (Lakehouse) — Instructions

```
LAKEHOUSE: contoso_lakehouse
Pre-aggregated KPI tables derived from Contoso Group's mirrored Databricks data. One row per division (or per division per month). Use for fast executive summaries and divisional comparisons without aggregating granular records.

TABLE: projectkpis
Full path: contoso_lakehouse.dbo.projectkpis
Description: Portfolio financial KPIs aggregated by division.
Columns: division (str: Division-Alpha|Division-Beta|Division-Gamma|Division-Delta), total_budget (decimal, sum of all project budgets in AUD), total_actual_cost (decimal, sum of actual costs), avg_cpi (decimal, average Cost Performance Index), avg_spi (decimal, average Schedule Performance Index), project_count (int, number of active projects), red_projects (int, number of projects in Red status)
Use for: Division-level financial comparisons, portfolio health dashboards, identifying which division has the most risk.

TABLE: safetykpis
Full path: contoso_lakehouse.dbo.safetykpis
Description: Monthly safety metrics aggregated by division.
Columns: division (str), month (date, first of month), total_incidents (int), near_misses (int), ltis (int, Lost Time Injuries), lost_time_days (decimal, total calendar days lost)
Use for: Monthly safety trend analysis, division safety comparisons, identifying deteriorating safety performance.

TABLE: fleetkpis
Full path: contoso_lakehouse.dbo.fleetkpis
Description: Fleet health metrics aggregated by division.
Columns: division (str), total_equipment (int, total fleet size), operational_count (int, currently operational units), availability_pct (decimal, percentage of fleet available), total_maintenance_cost (decimal, AUD), breakdown_count (int, unplanned breakdowns)
Use for: Fleet health dashboards, maintenance cost analysis, availability comparisons across divisions.

NOTES: These tables are snapshots — check the month column in safetykpis for data currency. For drill-down into individual records, use the mirrored Databricks catalog instead.
```

### Source: contoso_sqldb (SQL Database) — Instructions

```
SQL DATABASE: contoso_sqldb
Curated executive summary tables for board reporting and cross-functional analysis. Contains unique data not available in other sources (manufacturing_kpis, supplier_scorecard).

TABLE: division_summary
Full path: contoso_sqldb.dbo.division_summary
Description: One-row-per-division executive snapshot combining financial, fleet, and safety KPIs.
Columns: division (str: Division-Alpha|Division-Beta|Division-Gamma|Division-Delta), total_budget (decimal, AUD), total_actual_cost (decimal, AUD), avg_cpi (decimal), avg_spi (decimal), project_count (int), red_projects (int), fleet_count (int, total equipment), fleet_operational_pct (decimal, % fleet operational), incident_count (int, total incidents), exceedance_count (int, environmental exceedances), last_updated (datetime)
Use for: Executive dashboards, single-glance divisional health, board papers.

TABLE: monthly_kpis
Full path: contoso_sqldb.dbo.monthly_kpis
Description: Monthly time series of cross-functional KPIs per division. 12 months × 4 divisions.
Columns: month (date), division (str), budget_aud (decimal), actual_cost_aud (decimal), incidents (int), near_misses (int), lost_time_days (decimal), inspections_passed (int), inspections_failed (int), exceedances (int, environmental/compliance)
Use for: Monthly trend charts, period-over-period comparisons, identifying deteriorating performance.

TABLE: manufacturing_kpis
Full path: contoso_sqldb.dbo.manufacturing_kpis
Description: Production and manufacturing metrics by division and month. UNIQUE TO THIS SOURCE — not available in mirrored DB or lakehouse.
Columns: month (date), division (str), throughput_tonnes (decimal, production volume), utilisation_pct (decimal, plant utilisation), unplanned_downtime_hrs (decimal), energy_cost_aud (decimal), waste_pct (decimal, waste as % of throughput)
Use for: Manufacturing performance analysis, energy cost tracking, waste reduction monitoring.

TABLE: supplier_scorecard
Full path: contoso_sqldb.dbo.supplier_scorecard
Description: Vendor performance ratings for procurement oversight.
Columns: supplier_name (str), division (str), category (str), total_spend_aud (decimal), on_time_delivery_pct (decimal), quality_score (decimal, 1-5 scale), contract_status (str: Active|Under Review|Expiring Soon|Terminated), last_review_date (date)
Use for: Supplier risk assessment, contract renewal prioritisation, spend analysis by vendor and category.

NOTES: division_summary is best for quick dashboards. monthly_kpis for trend analysis. manufacturing_kpis is unique to SQL DB. supplier_scorecard pairs well with the mirrored materials table for complete procurement view. All tables refreshed daily.
```

## Sample Questions to Test

### Quick connectivity checks (one per source)
1. "Show me the division summary from the SQL database"
2. "What are the project KPIs from the lakehouse?"
3. "List all red-status projects from the mirrored database"

### Single-source questions
4. "Which division has the highest total budget and how many projects are at risk?" *(lakehouse)*
5. "Show me monthly KPI trends for the last 6 months by division" *(SQL DB)*
6. "What is the Estimate at Completion for all Division-Beta projects?" *(mirrored DB)*
7. "Which suppliers have contracts expiring soon and total spend over $1M?" *(SQL DB)*
8. "List all Critical and Major safety incidents that are still Open" *(mirrored DB)*
9. "What is the fleet availability percentage by division?" *(lakehouse)*
10. "Show me all equipment with engine temperature above 105°C" *(mirrored DB)*

### Cross-source questions (the real test)
11. "Give me a Contoso Group executive dashboard — portfolio performance, safety record, and fleet status across all divisions"
12. "Which division is our biggest risk right now? Consider financial performance, safety incidents, and equipment health"
13. "Compare Division-Beta vs Division-Alpha across all key metrics — budget, safety, and fleet utilisation"
14. "How are we tracking this quarter vs last quarter on SPI, CPI, and incident rate?"
15. "Give me a board-ready summary combining project financials, safety KPIs, and supplier risk"

### Edge-case / complex questions
16. "Which sites have both safety incidents AND equipment with critical temperature readings?"
17. "What is the total portfolio budget at risk from red projects, and what divisions do they belong to?"
18. "Show me materials with rising prices and lead times over 30 days — what's the procurement exposure?"
19. "Compare the division summary in SQL DB with the project KPIs in the lakehouse — do the numbers align?"
20. "Which project managers have multiple at-risk projects and what is their combined budget exposure?"

## Example SQL by Data Source

### Mirrored Databricks (4 sample queries)

```sql
-- Q1: Executive risk dashboard — red projects with their division's safety and fleet health
SELECT f.division,
       COUNT(DISTINCT f.project_id) AS red_projects,
       SUM(f.budget_aud) AS at_risk_budget,
       MIN(f.cpi) AS worst_cpi,
       COUNT(DISTINCT i.incident_id) AS recent_incidents,
       SUM(i.lost_time_days) AS total_lost_days
FROM contoso_dbx_org.projects.financials_f f
LEFT JOIN contoso_dbx_org.safety.incidents_f i
  ON f.division = i.division AND i.incident_date >= DATEADD(month, -3, GETDATE())
WHERE f.status = 'red'
  AND f.reporting_period = (SELECT MAX(reporting_period) FROM contoso_dbx_org.projects.financials_f)
GROUP BY f.division
ORDER BY at_risk_budget DESC;
```

```sql
-- Q2: Division operational scorecard — finance, safety, and fleet in one view
SELECT f.division,
       COUNT(DISTINCT f.project_id) AS projects,
       SUM(f.budget_aud) AS total_budget,
       SUM(f.earned_value_aud) / NULLIF(SUM(f.planned_value_aud), 0) AS weighted_spi,
       SUM(f.earned_value_aud) / NULLIF(SUM(f.actual_cost_aud), 0) AS weighted_cpi,
       inc.total_incidents,
       inc.lti_count,
       eq.fleet_size,
       eq.utilisation_pct
FROM contoso_dbx_org.projects.financials_f f
LEFT JOIN (
    SELECT division, COUNT(*) AS total_incidents,
           SUM(CASE WHEN lost_time_days > 0 THEN 1 ELSE 0 END) AS lti_count
    FROM contoso_dbx_org.safety.incidents_f
    GROUP BY division
) inc ON f.division = inc.division
LEFT JOIN (
    SELECT division, COUNT(*) AS fleet_size,
           ROUND(100.0 * SUM(CASE WHEN status = 'operational' THEN 1 ELSE 0 END) / COUNT(*), 1) AS utilisation_pct
    FROM contoso_dbx_org.equipment.equipment_telemetry_f
    GROUP BY division
) eq ON f.division = eq.division
WHERE f.reporting_period = (SELECT MAX(reporting_period) FROM contoso_dbx_org.projects.financials_f)
GROUP BY f.division, inc.total_incidents, inc.lti_count, eq.fleet_size, eq.utilisation_pct
ORDER BY total_budget DESC;
```

```sql
-- Q3: Site-level risk — sites with both safety incidents and equipment warnings
SELECT i.site_name, i.division,
       COUNT(DISTINCT i.incident_id) AS incidents,
       SUM(i.lost_time_days) AS lost_days,
       COUNT(DISTINCT e.equipment_id) AS equipment_warnings
FROM contoso_dbx_org.safety.incidents_f i
INNER JOIN contoso_dbx_org.equipment.equipment_telemetry_f e
  ON i.site_name = e.site_name AND e.status IN ('warning', 'critical')
GROUP BY i.site_name, i.division
ORDER BY incidents DESC;
```

```sql
-- Q4: Procurement exposure — high-risk materials with spend estimate
SELECT m.category, m.material_name, m.supplier, m.unit_price_aud,
       m.lead_time_days, m.price_trend, m.availability,
       m.unit_price_aud * m.last_order_qty AS est_spend_aud
FROM contoso_dbx_org.procurement.materials m
WHERE m.availability IN ('limited', 'out_of_stock')
   OR (m.price_trend = 'increasing' AND m.lead_time_days > 30)
ORDER BY est_spend_aud DESC;
```

### Lakehouse — ProjectKPIs

```sql
-- Divisional KPI comparison from pre-aggregated data
SELECT division, project_count, total_budget, total_actual_cost,
       avg_spi, avg_cpi, red_projects
FROM contoso_lakehouse.dbo.projectkpis
ORDER BY total_budget DESC;
```

### Lakehouse — SafetyKPIs

```sql
-- Safety trend: last 6 months by division
SELECT division, month, total_incidents, near_misses, ltis, lost_time_days
FROM contoso_lakehouse.dbo.safetykpis
WHERE month >= DATEADD(month, -6, GETDATE())
ORDER BY month DESC, division;
```

### Lakehouse — FleetKPIs

```sql
-- Fleet health overview by division
SELECT division, total_equipment, operational_count, availability_pct,
       total_maintenance_cost, breakdown_count
FROM contoso_lakehouse.dbo.fleetkpis
ORDER BY availability_pct DESC;
```

### SQL Database — division_summary

```sql
-- Executive dashboard: one-row-per-division snapshot
SELECT division, total_budget, total_actual_cost, avg_spi, avg_cpi,
       project_count, red_projects, fleet_count, fleet_operational_pct,
       incident_count, exceedance_count, last_updated
FROM contoso_sqldb.dbo.division_summary
ORDER BY total_budget DESC;
```

### SQL Database — monthly_kpis

```sql
-- Monthly KPI trends for the last 6 months
SELECT month, division, budget_aud, actual_cost_aud, incidents,
       near_misses, lost_time_days, inspections_passed, inspections_failed, exceedances
FROM contoso_sqldb.dbo.monthly_kpis
WHERE month >= DATEADD(month, -6, GETDATE())
ORDER BY month DESC, division;
```

### SQL Database — supplier_scorecard

```sql
-- Supplier risk overview: low quality or expiring contracts
SELECT supplier_name, division, category, total_spend_aud,
       on_time_delivery_pct, quality_score, contract_status, last_review_date
FROM contoso_sqldb.dbo.supplier_scorecard
WHERE contract_status IN ('Under Review', 'Expiring Soon') OR quality_score < 4.0
ORDER BY total_spend_aud DESC;
```

## RLS Testing — OneLake Security (Equipment Telemetry Example)

> **Minimal setup:** Create ONE OneLake Security role on `contoso_dbx_org` to demo RLS with the equipment telemetry table.
> Full 11-role setup is in `fabric/docs/fabric-mirroring-auth-permissions-rls-guide.md` Section 8.

### Setup — One Role for Group-A (Vinoth)

1. Open `contoso_dbx_org` → **Manage OneLake security**
2. **Delete or empty `DefaultReader`** role (otherwise it overrides everything)
3. Create role:

| Setting | Value |
|---------|-------|
| **Role name** | `RoleCPBEquipment` |
| **Assign member** | `Group-A` (Entra group containing Vinoth) |
| **Table access** | `equipment_telemetry_f` → Read ON |
| **Row security** | `SELECT * FROM equipment.equipment_telemetry_f WHERE division = 'Division-Alpha'` |

4. Ensure Vinoth has **Viewer** workspace role (Admins/Members/Contributors bypass OLS)

### Test as Vinoth (Group-A → Division-Alpha only)

**Should return Division-Alpha equipment data only:**

1. "Show me all equipment and their current status"
   → ✅ Only Division-Alpha equipment from `equipment_telemetry_f`

2. "Which equipment has engine temperature above 100°C?"
   → ✅ Only Division-Alpha assets

3. "How many pieces of equipment are in Critical status?"
   → ✅ Division-Alpha count only

4. "List equipment sorted by operating hours — which are overdue for maintenance?"
   → ✅ Only Division-Alpha fleet

**Should return NO data (proves RLS is working):**

5. "Show me Division-Beta equipment telemetry"
   → ❌ Zero rows — Vinoth cannot see Division-Beta equipment

6. "Compare equipment health across all divisions"
   → Only Division-Alpha visible (other divisions blocked by OLS)

**Should return unfiltered data (no OLS role for these tables):**

7. "Show me the project KPIs from the lakehouse"
   → ⚠️ All 4 divisions visible (lakehouse not covered by OLS)

8. "Show me the division summary from the SQL database"
   → ⚠️ All divisions visible (SQL DB not covered by OLS)

> **Note:** Since we only created one role (`RoleCPBEquipment`), Vinoth has NO access to `financials_f` or `incidents_f` on the mirrored DB. Asking about projects or safety from the mirrored source will return zero rows. Lakehouse and SQL DB are unaffected.

### Verification SQL (run as Vinoth in SQL Analytics Endpoint)

```sql
-- Should return ONLY Division-Alpha rows
SELECT division, COUNT(*) AS row_count
FROM contoso_dbx_org.equipment.equipment_telemetry_f
GROUP BY division;
-- Expected: one row — 'Division-Alpha'

-- Should return zero rows (no role for this table)
SELECT COUNT(*) FROM contoso_dbx_org.projects.financials_f;
-- Expected: 0
```
