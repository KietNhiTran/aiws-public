# Contoso Genie Space Reference

> Complete reference of all 5 Genie Spaces — their instructions, example SQL queries, sample questions, and benchmarks.
> Use this alongside the [production deployment guide](../../docs/production-deployment-guide.md) to verify or customise space content.

> **Note:** Replace `contoso` with your catalog name (e.g. `contoso_prod`) for production.

---

## Overview

| # | Space Name | Tables | Source Script |
|---|-----------|--------|---------------|
| 1 | Contoso Project Intelligence | All 4 core tables | `05_domain_genie_spaces.py` |
| 2 | Safety Agent | `safety.incidents` | `05_domain_genie_spaces.py` |
| 3 | Equipment Agent | `equipment.equipment_telemetry` | `05_domain_genie_spaces.py` |
| 4 | Procurement Agent | `procurement.materials` | `05_domain_genie_spaces.py` |
| 5 | Projects Agent | `projects.financials` | `05_domain_genie_spaces.py` |

**Source scripts:**

- **Primary (Module 03):** `databricks/setup/05_domain_genie_spaces.py` — deployed via the module03 job. Uses `{customer}` / `{C}` placeholders resolved at runtime.
- **Main pipeline:** `databricks/src/05_domain_genie_agents.py` — extended version with additional tables (`maintenance_log`, `environmental.emissions`, `quality.inspections`, `supply_chain_gold.*`) and more complex queries. Content unique to this version is shown in "Extended Queries (Main Pipeline)" subsections.

---

## 1. Contoso Project Intelligence

### Description

Cross-domain operations intelligence covering project finance, safety, equipment, and procurement for Contoso Group.

### Agent Instructions

You are the Contoso Project Intelligence assistant — a cross-domain operations analyst. This Genie Space covers Contoso Group operational data across 4 domains: Project Financials (EVM metrics, RAG status, budgets), Safety Incidents (HSE records, severity, root causes), Equipment Telemetry (fleet sensor data, maintenance), Procurement Materials (supplier pricing, availability).

Key terminology:
- **SPI** = Schedule Performance Index (EV/PV). 1.0 = on schedule, <1.0 = behind.
- **CPI** = Cost Performance Index (EV/AC). 1.0 = on budget, <1.0 = over budget.
- **EAC** = Estimate at Completion = Budget / CPI.
- **RAG** = Red/Amber/Green.
- **LTI** = Lost Time Injury. Near-miss = incident with 0 injuries.

Divisions: Division-Alpha, Division-Beta, Division-Gamma, Division-Delta. Division is the primary join key across all 4 tables. Site_name links incidents to equipment.

All monetary values are in AUD. Format with commas and $ prefix. When comparing divisions, always include project counts for context. Flag red-status projects, critical equipment, and serious incidents prominently. Look for cross-domain patterns: divisions with both cost overruns and safety issues need attention.

### Example SQL Queries

**1. Division performance across finance and safety**

```sql
SELECT f.division, COUNT(DISTINCT f.project_id) AS projects,
  ROUND(AVG(f.cpi), 2) AS avg_cpi, ROUND(AVG(f.spi), 2) AS avg_spi,
  COUNT(DISTINCT i.incident_id) AS incidents, SUM(i.lost_time_days) AS lti_days
FROM contoso.projects.financials f
LEFT JOIN contoso.safety.incidents i ON f.division = i.division
GROUP BY f.division
ORDER BY avg_cpi
```

**2. Sites with both safety incidents and equipment alerts**

```sql
SELECT i.site_name, i.division,
  COUNT(DISTINCT i.incident_id) AS incidents,
  COUNT(DISTINCT e.equipment_id) AS equipment_alerts
FROM contoso.safety.incidents i
JOIN contoso.equipment.equipment_telemetry e ON i.site_name = e.site_name
WHERE e.status IN ('warning', 'critical')
GROUP BY i.site_name, i.division
ORDER BY incidents DESC
```

**3. Red-status projects with full details**

```sql
SELECT project_name, division, budget_aud, actual_cost_aud,
  cost_variance_pct, spi, cpi
FROM contoso.projects.financials
WHERE status = 'red'
ORDER BY cost_variance_pct ASC
```

**4. Materials with increasing prices and limited availability**

```sql
SELECT material_name, category, supplier, unit_price_aud, availability
FROM contoso.procurement.materials
WHERE price_trend = 'increasing'
ORDER BY unit_price_aud DESC
```

**5. Equipment status summary by division**

```sql
SELECT division, status, COUNT(*) AS units
FROM contoso.equipment.equipment_telemetry
GROUP BY division, status
ORDER BY division
```

### Sample Questions

- How many Contoso projects are in red status?
- What is the average SPI by division?
- Show all equipment with critical or warning status
- Which sites have the most safety incidents?
- What materials have increasing price trends?
- Compare budget vs actuals for all Contoso divisions
- Which divisions have both over-budget projects and rising incident counts?
- Show equipment alerts at sites with recent safety incidents

### Benchmarks

| Question | Expected SQL |
|----------|-------------|
| How many Contoso projects are in red status? | `SELECT COUNT(*) FROM contoso.projects.financials WHERE status = 'red'` |
| Which division has the most safety incidents? | `SELECT division, COUNT(*) AS cnt FROM contoso.safety.incidents GROUP BY division ORDER BY cnt DESC LIMIT 1` |
| How many equipment units have critical status? | `SELECT COUNT(*) FROM contoso.equipment.equipment_telemetry WHERE status = 'critical'` |
| What is the average CPI across the portfolio? | `SELECT ROUND(AVG(cpi), 2) FROM contoso.projects.financials` |
| Show materials with increasing price trends | `SELECT material_name, supplier, unit_price_aud FROM contoso.procurement.materials WHERE price_trend = 'increasing'` |
| Total lost time days across all divisions | `SELECT SUM(lost_time_days) FROM contoso.safety.incidents` |

### Extended Queries (Main Pipeline)

The main pipeline version (`src/05_domain_genie_agents.py`) uses a richer description and adds cross-domain queries with subqueries.

**Description:** Cross-domain operations intelligence for Contoso Group. Connects project finance (EVM, SPI/CPI, budget vs actuals), safety incidents, equipment telemetry, and procurement spend. Supports operational decisions by correlating insights across all four domains.

**Additional instructions:** Risk classification: Critical = CPI < 0.85 OR SPI < 0.85. High = CPI < 0.95 OR SPI < 0.95. Medium = within 5% of plan. Low = on or ahead of plan. When asked for an 'operations summary', show: total portfolio value, number of projects by status, average SPI and CPI, total incidents, total procurement spend, and equipment utilisation. Use 'M' suffix for millions (e.g. $45.2M).

**Additional sample questions:**

- Give me an operations health summary
- Which projects are at highest risk?
- What is our overall safety record this quarter?
- Compare incident rates with equipment utilisation by site
- Which projects need immediate attention?

**1. Operations health summary**

```sql
SELECT
  COUNT(*) AS total_projects,
  ROUND(SUM(budget_aud) / 1e6, 1) AS total_budget_m,
  ROUND(SUM(actual_cost_aud) / 1e6, 1) AS total_spent_m,
  ROUND(AVG(spi), 2) AS avg_spi,
  ROUND(AVG(cpi), 2) AS avg_cpi,
  ROUND(AVG(pct_complete), 1) AS avg_completion_pct,
  SUM(CASE WHEN status = 'at_risk' THEN 1 ELSE 0 END) AS at_risk_projects,
  SUM(CASE WHEN cpi < 0.9 THEN 1 ELSE 0 END) AS over_budget_projects
FROM contoso.projects.financials
```

**2. Projects needing immediate attention**

```sql
SELECT project_name, division, status,
  ROUND(budget_aud / 1e6, 1) AS budget_m,
  ROUND(actual_cost_aud / 1e6, 1) AS spent_m,
  ROUND(cost_variance_pct, 1) AS cv_pct,
  spi, cpi, pct_complete, project_manager
FROM contoso.projects.financials
WHERE cpi < 0.9 OR status = 'at_risk' OR spi < 0.9
ORDER BY cpi ASC
```

**3. Division performance comparison**

```sql
SELECT division,
  COUNT(*) AS projects,
  ROUND(SUM(budget_aud) / 1e6, 1) AS total_budget_m,
  ROUND(AVG(spi), 2) AS avg_spi,
  ROUND(AVG(cpi), 2) AS avg_cpi,
  ROUND(AVG(pct_complete), 1) AS avg_completion,
  SUM(CASE WHEN status = 'at_risk' THEN 1 ELSE 0 END) AS at_risk
FROM contoso.projects.financials
GROUP BY division
ORDER BY avg_cpi
```

**4. Budget vs actual cost for all projects**

```sql
SELECT project_name, division,
  ROUND(budget_aud / 1e6, 1) AS budget_m,
  ROUND(actual_cost_aud / 1e6, 1) AS actual_m,
  ROUND((budget_aud - actual_cost_aud) / 1e6, 1) AS variance_m,
  ROUND(cost_variance_pct, 1) AS cv_pct,
  status, pct_complete
FROM contoso.projects.financials
ORDER BY cost_variance_pct ASC
```

**5. Safety record across the portfolio**

```sql
SELECT
  COUNT(*) AS total_incidents,
  SUM(CASE WHEN severity = 'critical' THEN 1 ELSE 0 END) AS critical,
  SUM(CASE WHEN severity = 'high' THEN 1 ELSE 0 END) AS high,
  SUM(CASE WHEN is_near_miss THEN 1 ELSE 0 END) AS near_misses,
  ROUND(SUM(lost_time_days), 1) AS total_lti_days,
  COUNT(CASE WHEN lost_time_days > 0 AND NOT is_near_miss THEN 1 END) AS lti_count
FROM contoso.safety.incidents
```

**6. Top 5 cost overruns**

```sql
SELECT project_name, division,
  ROUND(budget_aud / 1e6, 1) AS budget_m,
  ROUND(actual_cost_aud / 1e6, 1) AS actual_m,
  ROUND((actual_cost_aud - budget_aud) / 1e6, 1) AS overrun_m,
  cpi, spi, project_manager
FROM contoso.projects.financials
WHERE actual_cost_aud > budget_aud
ORDER BY (actual_cost_aud - budget_aud) DESC
LIMIT 5
```

**7. Compare incident rates with equipment utilisation by division**

```sql
SELECT f.division,
  COUNT(DISTINCT f.project_id) AS projects,
  COALESCE(i.incident_count, 0) AS incidents,
  COALESCE(ROUND(e.avg_utilisation, 1), 0) AS avg_equip_util_pct,
  ROUND(AVG(f.cpi), 2) AS avg_cpi
FROM contoso.projects.financials f
LEFT JOIN (SELECT division, COUNT(*) AS incident_count FROM contoso.safety.incidents GROUP BY division) i ON f.division = i.division
LEFT JOIN (SELECT division, AVG(utilisation_pct) AS avg_utilisation FROM contoso.equipment.equipment_telemetry GROUP BY division) e ON f.division = e.division
GROUP BY f.division, i.incident_count, e.avg_utilisation
ORDER BY incidents DESC
```

**8. Procurement spend vs budget by division**

```sql
SELECT f.division,
  ROUND(SUM(f.budget_aud) / 1e6, 1) AS total_budget_m,
  ROUND(COALESCE(p.procurement_cost, 0) / 1e6, 2) AS procurement_m,
  ROUND(100.0 * COALESCE(p.procurement_cost, 0) / NULLIF(SUM(f.budget_aud), 0), 1) AS procurement_pct_of_budget
FROM contoso.projects.financials f
LEFT JOIN (SELECT division, SUM(total_cost_aud) AS procurement_cost FROM contoso.procurement.materials GROUP BY division) p ON f.division = p.division
GROUP BY f.division, p.procurement_cost
ORDER BY procurement_m DESC
```

---

## 2. Safety Agent

### Description

WHS incident analysis, severity trends, root cause patterns, and site safety performance for Contoso Group.

### Agent Instructions

You are the Contoso Safety Agent — an AI assistant for WHS managers and site supervisors. You analyse Contoso Group's incident data to identify safety trends, high-risk sites, and root cause patterns.

Key terminology:
- **LTI** = Lost Time Injury (any incident causing ≥1 day off work).
- **LTIFR** = Lost Time Injury Frequency Rate = (LTIs × 1,000,000) / total hours worked.
- **Near-miss** = incident with 0 injuries but potential for harm.
- **Severity levels:** Minor (first aid only), Moderate (medical treatment), Serious (LTI), Critical (life-threatening).

Always highlight Critical and Serious incidents prominently. When showing incident counts, also show total injuries and lost time days for context. For trend analysis, group by month using incident_date. Root cause analysis is critical: always flag 'equipment_failure' and 'inadequate_training' as systemic issues.

Divisions: Division-Alpha (infrastructure), Division-Beta (mining services), Division-Gamma (mineral processing), Division-Delta (PPPs).

### Example SQL Queries

**1. Show all open incidents with severity**

```sql
SELECT incident_id, incident_date, site_name, division, incident_type,
  severity, injuries, lost_time_days
FROM contoso.safety.incidents
WHERE status = 'open'
ORDER BY incident_date DESC
```

**2. Incident count and severity breakdown by division**

```sql
SELECT division, severity, COUNT(*) AS count,
  SUM(injuries) AS total_injuries, SUM(lost_time_days) AS total_lti_days
FROM contoso.safety.incidents
GROUP BY division, severity
ORDER BY division,
  CASE severity WHEN 'Critical' THEN 1 WHEN 'Serious' THEN 2 WHEN 'Moderate' THEN 3 ELSE 4 END
```

**3. Top root causes for all incidents**

```sql
SELECT root_cause, COUNT(*) AS incidents, SUM(injuries) AS injuries,
  ROUND(AVG(lost_time_days), 1) AS avg_lti_days
FROM contoso.safety.incidents
GROUP BY root_cause
ORDER BY incidents DESC
```

**4. Sites with the most incidents**

```sql
SELECT site_name, division, COUNT(*) AS incidents,
  SUM(CASE WHEN severity IN ('Critical','Serious') THEN 1 ELSE 0 END) AS critical_serious
FROM contoso.safety.incidents
GROUP BY site_name, division
ORDER BY incidents DESC
LIMIT 15
```

**5. Monthly incident trend**

```sql
SELECT DATE_TRUNC('month', incident_date) AS month,
  COUNT(*) AS incidents, SUM(injuries) AS injuries
FROM contoso.safety.incidents
GROUP BY DATE_TRUNC('month', incident_date)
ORDER BY month
```

**6. All critical incidents with full details**

```sql
SELECT incident_id, incident_date, site_name, division, incident_type,
  description, injuries, lost_time_days, root_cause, corrective_action
FROM contoso.safety.incidents
WHERE severity = 'Critical'
ORDER BY incident_date DESC
```

### Sample Questions

- How many open safety incidents do we have right now?
- What are the most common incident types across all divisions?
- Show all critical severity incidents in the last 6 months
- Which sites have the highest incident frequency?
- What is the total lost time days by division?
- Show root cause breakdown for equipment failure incidents
- Are there any incidents still under investigation?
- Compare safety performance between Division-Alpha and Division-Beta

### Benchmarks

| Question | Expected SQL |
|----------|-------------|
| How many open safety incidents are there? | `SELECT COUNT(*) FROM contoso.safety.incidents WHERE status = 'open'` |
| Which division has the most serious incidents? | `SELECT division, COUNT(*) AS cnt FROM contoso.safety.incidents WHERE severity IN ('Serious', 'Critical') GROUP BY division ORDER BY cnt DESC LIMIT 1` |
| What is the total lost time days? | `SELECT SUM(lost_time_days) FROM contoso.safety.incidents` |
| Show critical incidents | `SELECT incident_id, incident_date, site_name, severity FROM contoso.safety.incidents WHERE severity = 'Critical'` |
| Which site has the most incidents? | `SELECT site_name, COUNT(*) AS cnt FROM contoso.safety.incidents GROUP BY site_name ORDER BY cnt DESC LIMIT 1` |
| What are the most common incident types? | `SELECT incident_type, COUNT(*) AS cnt FROM contoso.safety.incidents GROUP BY incident_type ORDER BY cnt DESC LIMIT 1` |

### Extended Queries (Main Pipeline)

The main pipeline version adds **environmental monitoring** (`environmental.emissions`) and **quality inspections** (`quality.inspections`) tables.

**Description:** Virtual HSE officer for Contoso Group. Analyses workplace safety incidents, environmental monitoring (dust, noise, water, vibration), quality inspections and ITP hold points. Supports regulatory reporting, root cause analysis, and compliance dashboards.

**Additional instructions:** Key terminology additions: TRIFR = Total Recordable Injury Frequency Rate. ITP = Inspection and Test Plan. When asked about compliance, show exceedance_count / total_readings as a percentage. When asked about quality, show pass rate (passes / total) and total rework cost. If the user asks about LTIFR, note that hours-worked data is in workforce.timesheets (not in this space) so show LTI count and lost days instead. Regulatory context: Australian WHS Act 2011, EPA licence conditions vary by state. Critical incidents require notification to SafeWork within 24 hours.

**Additional sample questions:**

- How many critical safety incidents occurred this quarter?
- Which sites have the highest lost time injury days?
- Show me all environmental exceedances for dust monitors
- What is the quality inspection pass rate by project?
- Are there any open investigations for critical incidents?
- Compare near-miss reporting rates across divisions
- Which sites exceeded EPA noise limits in the last 3 months?
- Show rework costs from failed quality inspections by site

**1. Show critical safety incidents with investigation status**

```sql
SELECT incident_id, incident_date, site_name, division, incident_type,
  description, injuries, lost_time_days, root_cause, corrective_action, status
FROM contoso.safety.incidents
WHERE severity = 'critical'
ORDER BY incident_date DESC
```

**2. Incident trend by month and severity**

```sql
SELECT DATE_TRUNC('month', incident_date) AS month,
  COUNT(*) AS total,
  SUM(CASE WHEN severity = 'critical' THEN 1 ELSE 0 END) AS critical,
  SUM(CASE WHEN severity = 'high' THEN 1 ELSE 0 END) AS high,
  SUM(CASE WHEN severity = 'medium' THEN 1 ELSE 0 END) AS medium,
  SUM(CASE WHEN severity = 'low' THEN 1 ELSE 0 END) AS low,
  SUM(CASE WHEN is_near_miss THEN 1 ELSE 0 END) AS near_misses,
  ROUND(SUM(lost_time_days), 1) AS total_lti_days
FROM contoso.safety.incidents
GROUP BY DATE_TRUNC('month', incident_date)
ORDER BY month
```

**3. Root causes for high and critical incidents**

```sql
SELECT root_cause, COUNT(*) AS incidents,
  ROUND(SUM(lost_time_days), 1) AS total_lti_days,
  SUM(injuries) AS total_injuries
FROM contoso.safety.incidents
WHERE severity IN ('critical', 'high')
GROUP BY root_cause
ORDER BY incidents DESC
```

**4. Environmental exceedances by site**

```sql
SELECT site_name, monitor_type, unit,
  COUNT(*) AS total_readings,
  SUM(CASE WHEN is_exceedance THEN 1 ELSE 0 END) AS exceedances,
  ROUND(100.0 * SUM(CASE WHEN is_exceedance THEN 1 ELSE 0 END) / COUNT(*), 1) AS exceedance_rate_pct,
  ROUND(MAX(measurement_value), 1) AS max_reading,
  ROUND(AVG(threshold_value), 1) AS threshold
FROM contoso.environmental.emissions
GROUP BY site_name, monitor_type, unit
ORDER BY exceedances DESC
```

**5. Quality inspection pass rate by project**

```sql
SELECT f.project_name, f.division,
  COUNT(*) AS total_inspections,
  SUM(CASE WHEN q.result = 'pass' THEN 1 ELSE 0 END) AS passed,
  SUM(CASE WHEN q.result = 'fail' THEN 1 ELSE 0 END) AS failed,
  ROUND(100.0 * SUM(CASE WHEN q.result = 'pass' THEN 1 ELSE 0 END) / COUNT(*), 1) AS pass_rate_pct,
  ROUND(SUM(COALESCE(q.rework_cost_aud, 0)), 2) AS total_rework_cost
FROM contoso.quality.inspections q
JOIN contoso.projects.financials f ON q.project_id = f.project_id
GROUP BY f.project_name, f.division
ORDER BY pass_rate_pct ASC
```

**6. Safety incidents for a specific site** *(parameterised — replace `:site`)*

```sql
SELECT incident_id, incident_date, shift, incident_type, severity,
  description, injuries, lost_time_days, root_cause, status
FROM contoso.safety.incidents
WHERE site_name = :site  -- default: 'Sydney Metro West'
ORDER BY incident_date DESC
```

**7. Sites needing dust suppression action**

```sql
SELECT site_name,
  COUNT(*) AS dust_readings,
  SUM(CASE WHEN is_exceedance THEN 1 ELSE 0 END) AS exceedances,
  ROUND(MAX(measurement_value), 1) AS max_dust_ug_m3,
  ROUND(AVG(threshold_value), 1) AS threshold_ug_m3,
  MAX(action_taken) AS latest_action
FROM contoso.environmental.emissions
WHERE monitor_type IN ('dust_pm10', 'dust_pm2_5')
GROUP BY site_name
HAVING SUM(CASE WHEN is_exceedance THEN 1 ELSE 0 END) > 0
ORDER BY exceedances DESC
```

**8. Night shift vs day shift incident rate**

```sql
SELECT shift,
  COUNT(*) AS incidents,
  SUM(CASE WHEN severity IN ('critical', 'high') THEN 1 ELSE 0 END) AS serious,
  ROUND(SUM(lost_time_days), 1) AS lti_days,
  SUM(CASE WHEN is_near_miss THEN 1 ELSE 0 END) AS near_misses
FROM contoso.safety.incidents
GROUP BY shift
ORDER BY incidents DESC
```

**9. Failed weld and concrete tests with defect details**

```sql
SELECT q.inspection_id, f.project_name, q.site_name, q.inspection_type,
  q.discipline, q.defect_category, q.severity AS defect_severity,
  q.rework_cost_aud, q.inspector, q.inspection_date
FROM contoso.quality.inspections q
LEFT JOIN contoso.projects.financials f ON q.project_id = f.project_id
WHERE q.result = 'fail' AND q.inspection_type IN ('weld_test', 'concrete_test')
ORDER BY q.inspection_date DESC
```

**10. EPA noise compliance at night**

```sql
SELECT site_name,
  COUNT(*) AS night_noise_readings,
  SUM(CASE WHEN is_exceedance THEN 1 ELSE 0 END) AS exceedances,
  ROUND(AVG(measurement_value), 1) AS avg_noise_db,
  ROUND(MAX(measurement_value), 1) AS max_noise_db,
  ROUND(AVG(threshold_value), 1) AS limit_db
FROM contoso.environmental.emissions
WHERE monitor_type = 'noise_db' AND reading_time >= '18:00'
GROUP BY site_name
ORDER BY exceedances DESC
```

**Extended Benchmarks (Main Pipeline)**

| Question | Expected SQL |
|----------|-------------|
| How many critical incidents are still open? | `SELECT COUNT(*) FROM contoso.safety.incidents WHERE severity = 'critical' AND status != 'closed'` |
| What is the dust exceedance rate at Bowen Basin? | `SELECT ROUND(100.0 * SUM(CASE WHEN is_exceedance THEN 1 ELSE 0 END) / COUNT(*), 1) FROM contoso.environmental.emissions WHERE site_name LIKE '%Bowen%' AND monitor_type LIKE 'dust%'` |
| Show total rework cost | `SELECT ROUND(SUM(rework_cost_aud), 2) FROM contoso.quality.inspections WHERE result = 'fail'` |
| Which site has the most incidents? | `SELECT site_name, COUNT(*) AS cnt FROM contoso.safety.incidents GROUP BY site_name ORDER BY cnt DESC LIMIT 1` |
| How many near-misses were reported? | `SELECT COUNT(*) FROM contoso.safety.incidents WHERE is_near_miss = TRUE` |
| Show water quality exceedances | `SELECT site_name, measurement_value, threshold_value FROM contoso.environmental.emissions WHERE monitor_type LIKE 'water%' AND is_exceedance = TRUE` |

---

## 3. Equipment Agent

### Description

Heavy equipment fleet monitoring, engine diagnostics, maintenance scheduling, and utilisation analysis for Contoso Group.

### Agent Instructions

You are the Contoso Equipment Agent — an AI assistant for fleet operations managers and maintenance planners. You monitor Contoso's heavy equipment fleet across mining and infrastructure sites.

Key thresholds:
- **Engine temperature:** Normal 70–95°C, Warning 95–110°C, Critical >110°C.
- **Fuel level:** Good >50%, Low 10–20%, Critical <10%.
- **Operating hours:** Major service every 1000 hrs, minor service every 250 hrs.
- **Status priority:** always surface 'critical' first, then 'warning', then 'maintenance'.

When asked about fleet health, show a count by status (operational/warning/critical/maintenance). When asked about a specific equipment type, show all units of that type with their latest readings. Maintenance overdue = `maintenance_due_date < current_date()`. Flag these prominently.

Equipment ID prefixes: HT=haul truck, EX=excavator, DR=drill, LD=loader, DZ=dozer, GR=grader, WC=water cart, CR=crane.

### Example SQL Queries

**1. All critical and warning equipment**

```sql
SELECT equipment_id, equipment_type, site_name, division,
  engine_temp_celsius, fuel_level_pct, status
FROM contoso.equipment.equipment_telemetry
WHERE status IN ('critical', 'warning')
ORDER BY CASE status WHEN 'critical' THEN 1 ELSE 2 END, engine_temp_celsius DESC
```

**2. Fleet status breakdown by division**

```sql
SELECT division, status, COUNT(*) AS units
FROM contoso.equipment.equipment_telemetry
GROUP BY division, status
ORDER BY division,
  CASE status WHEN 'critical' THEN 1 WHEN 'warning' THEN 2 WHEN 'maintenance' THEN 3 ELSE 4 END
```

**3. Equipment with overdue maintenance**

```sql
SELECT equipment_id, equipment_type, site_name, division,
  maintenance_due_date, operating_hours, status
FROM contoso.equipment.equipment_telemetry
WHERE maintenance_due_date < current_date()
ORDER BY maintenance_due_date
```

**4. Average engine temperature and fuel level by type**

```sql
SELECT equipment_type, COUNT(*) AS units,
  ROUND(AVG(engine_temp_celsius), 1) AS avg_temp_c,
  ROUND(AVG(fuel_level_pct), 1) AS avg_fuel_pct
FROM contoso.equipment.equipment_telemetry
GROUP BY equipment_type
ORDER BY avg_temp_c DESC
```

**5. Equipment with low fuel**

```sql
SELECT equipment_id, equipment_type, site_name, fuel_level_pct, status
FROM contoso.equipment.equipment_telemetry
WHERE fuel_level_pct < 20
ORDER BY fuel_level_pct
```

**6. Highest operating hours — top 20 most used equipment**

```sql
SELECT equipment_id, equipment_type, site_name, division,
  operating_hours, status
FROM contoso.equipment.equipment_telemetry
ORDER BY operating_hours DESC
LIMIT 20
```

### Sample Questions

- Which equipment units have critical status right now?
- What is the average engine temperature by equipment type?
- Show all equipment with maintenance overdue
- How many units does each division operate?
- Which sites have the most equipment with warning or critical status?
- Show fuel levels below 20% — which units need refuelling?
- What is the fleet utilisation breakdown by status?
- List all excavators sorted by operating hours

### Benchmarks

| Question | Expected SQL |
|----------|-------------|
| How many equipment are in critical status? | `SELECT COUNT(DISTINCT equipment_id) FROM contoso.equipment.equipment_telemetry WHERE status = 'critical'` |
| What is the total breakdown cost? | `SELECT ROUND(SUM(cost_aud), 2) FROM contoso.equipment.maintenance_log WHERE maintenance_type = 'breakdown'` |
| Average downtime per breakdown | `SELECT ROUND(AVG(downtime_hours), 1) FROM contoso.equipment.maintenance_log WHERE maintenance_type = 'breakdown'` |
| Which manufacturer has the most breakdowns? | `SELECT t.manufacturer, COUNT(*) AS cnt FROM contoso.equipment.maintenance_log m JOIN contoso.equipment.equipment_telemetry t ON m.equipment_id = t.equipment_id WHERE m.maintenance_type = 'breakdown' GROUP BY t.manufacturer ORDER BY cnt DESC LIMIT 1` |
| Show equipment due for maintenance this week | `SELECT DISTINCT equipment_id, equipment_type, site_name, maintenance_due_date FROM contoso.equipment.equipment_telemetry WHERE maintenance_due_date BETWEEN CURRENT_DATE() AND DATE_ADD(CURRENT_DATE(), 7)` |

### Extended Queries (Main Pipeline)

The main pipeline version adds the **`equipment.maintenance_log`** table with work orders, parts/labour cost breakdown, and downtime tracking. It also uses `reading_timestamp` for latest-reading logic and adds hydraulic pressure and fuel consumption columns.

**Description:** Virtual fleet manager for Contoso Group. Monitors equipment health via IoT telemetry (engine temp, hydraulics, fuel), analyses maintenance costs and downtime, tracks breakdown frequency by manufacturer, and supports predictive maintenance planning.

**Additional instructions:** Key terminology: MTBF = Mean Time Between Failures. MTTR = Mean Time To Repair = avg downtime_hours for breakdowns. Fleet availability = percentage of equipment in operational status. Hydraulic pressure: Normal 200–350 bar, Warning >350 or <150, Critical >400 or <100. When asked about equipment status, show the LATEST reading per equipment_id (`MAX(reading_timestamp)`). When asked about costs, always break down into `parts_cost_aud` and `labour_cost_aud`.

**Additional sample questions:**

- What is the total maintenance cost by equipment type?
- Show breakdown frequency by manufacturer
- Which haul trucks have the highest fuel consumption?
- What is the average downtime per breakdown event?
- Compare scheduled vs unscheduled maintenance costs
- Which sites have the most equipment in warning status?

**1. Current status of all equipment (latest reading)**

```sql
SELECT t.equipment_id, t.equipment_type, t.manufacturer, t.site_name,
  t.status, t.engine_temp_celsius, t.hydraulic_pressure_bar, t.fuel_level_pct,
  t.operating_hours, t.maintenance_due_date
FROM contoso.equipment.equipment_telemetry t
INNER JOIN (SELECT equipment_id, MAX(reading_timestamp) AS latest
  FROM contoso.equipment.equipment_telemetry GROUP BY equipment_id) lat
  ON t.equipment_id = lat.equipment_id AND t.reading_timestamp = lat.latest
ORDER BY CASE t.status WHEN 'critical' THEN 1 WHEN 'warning' THEN 2 WHEN 'maintenance' THEN 3 ELSE 4 END
```

**2. Total maintenance cost by equipment type (JOINs maintenance_log)**

```sql
SELECT t.equipment_type, t.manufacturer,
  COUNT(DISTINCT m.work_order_id) AS work_orders,
  ROUND(SUM(m.cost_aud), 2) AS total_cost_aud,
  ROUND(SUM(m.parts_cost_aud), 2) AS parts_aud,
  ROUND(SUM(m.labour_cost_aud), 2) AS labour_aud,
  ROUND(SUM(m.downtime_hours), 1) AS total_downtime_hrs
FROM contoso.equipment.maintenance_log m
JOIN contoso.equipment.equipment_telemetry t ON m.equipment_id = t.equipment_id
WHERE m.status = 'completed'
GROUP BY t.equipment_type, t.manufacturer
ORDER BY total_cost_aud DESC
```

**3. Breakdown frequency and cost by manufacturer**

```sql
SELECT t.manufacturer, t.equipment_type,
  COUNT(*) AS breakdowns,
  ROUND(SUM(m.cost_aud), 2) AS breakdown_cost_aud,
  ROUND(AVG(m.downtime_hours), 1) AS avg_downtime_hrs,
  ROUND(SUM(m.downtime_hours), 1) AS total_downtime_hrs
FROM contoso.equipment.maintenance_log m
JOIN contoso.equipment.equipment_telemetry t ON m.equipment_id = t.equipment_id
WHERE m.maintenance_type = 'breakdown'
GROUP BY t.manufacturer, t.equipment_type
ORDER BY breakdowns DESC
```

**4. Overdue maintenance with days overdue**

```sql
SELECT DISTINCT t.equipment_id, t.equipment_type, t.manufacturer, t.site_name,
  t.maintenance_due_date, DATEDIFF(CURRENT_DATE(), t.maintenance_due_date) AS days_overdue
FROM contoso.equipment.equipment_telemetry t
INNER JOIN (SELECT equipment_id, MAX(reading_timestamp) AS latest
  FROM contoso.equipment.equipment_telemetry GROUP BY equipment_id) lat
  ON t.equipment_id = lat.equipment_id AND t.reading_timestamp = lat.latest
WHERE t.maintenance_due_date < CURRENT_DATE()
ORDER BY days_overdue DESC
```

**5. Scheduled vs unscheduled maintenance costs**

```sql
SELECT maintenance_type,
  COUNT(*) AS work_orders,
  ROUND(SUM(cost_aud), 2) AS total_cost_aud,
  ROUND(AVG(cost_aud), 2) AS avg_cost_aud,
  ROUND(SUM(downtime_hours), 1) AS total_downtime_hrs,
  ROUND(AVG(downtime_hours), 1) AS avg_downtime_hrs
FROM contoso.equipment.maintenance_log
WHERE status = 'completed'
GROUP BY maintenance_type
ORDER BY total_cost_aud DESC
```

**6. Top 10 most expensive maintenance work orders**

```sql
SELECT m.work_order_id, t.equipment_id, t.equipment_type, t.manufacturer,
  t.site_name, m.maintenance_type, m.description,
  m.cost_aud, m.parts_cost_aud, m.labour_cost_aud, m.downtime_hours
FROM contoso.equipment.maintenance_log m
JOIN contoso.equipment.equipment_telemetry t ON m.equipment_id = t.equipment_id
WHERE m.status = 'completed'
ORDER BY m.cost_aud DESC
LIMIT 10
```

**7. Fuel consumption by equipment type**

```sql
SELECT equipment_type, manufacturer,
  COUNT(DISTINCT equipment_id) AS fleet_count,
  ROUND(AVG(fuel_consumption_lph), 1) AS avg_fuel_lph,
  ROUND(MAX(fuel_consumption_lph), 1) AS max_fuel_lph,
  ROUND(AVG(fuel_level_pct), 1) AS avg_fuel_level_pct
FROM contoso.equipment.equipment_telemetry
GROUP BY equipment_type, manufacturer
ORDER BY avg_fuel_lph DESC
```

**8. Fleet availability by site**

```sql
SELECT site_name,
  COUNT(DISTINCT equipment_id) AS total_equipment,
  SUM(CASE WHEN status = 'operational' THEN 1 ELSE 0 END) AS operational,
  SUM(CASE WHEN status = 'warning' THEN 1 ELSE 0 END) AS warning,
  SUM(CASE WHEN status = 'critical' THEN 1 ELSE 0 END) AS critical,
  SUM(CASE WHEN status = 'maintenance' THEN 1 ELSE 0 END) AS in_maintenance,
  ROUND(100.0 * SUM(CASE WHEN status = 'operational' THEN 1 ELSE 0 END) / COUNT(DISTINCT equipment_id), 1) AS availability_pct
FROM contoso.equipment.equipment_telemetry t
INNER JOIN (SELECT equipment_id, MAX(reading_timestamp) AS latest
  FROM contoso.equipment.equipment_telemetry GROUP BY equipment_id) lat
  ON t.equipment_id = lat.equipment_id AND t.reading_timestamp = lat.latest
GROUP BY site_name
ORDER BY availability_pct
```

---

## 4. Procurement Agent

### Description

Material pricing analysis, supplier performance, lead time monitoring, and supply chain risk assessment for Contoso Group.

### Agent Instructions

You are the Contoso Procurement Agent — an AI assistant for procurement directors and project supply managers. You analyse Contoso's material procurement data to identify cost risks, supply chain constraints, and supplier performance.

Key concepts:
- **Price trend 'increasing'** = cost risk that may affect project budgets.
- **Availability 'limited' or 'out_of_stock'** = supply chain risk requiring alternative sourcing.
- **Lead time >30 days** = long lead item. **>60 days** = critical lead item requiring forward planning.
- Always show unit price WITH the unit of measure for meaningful comparisons.
- When comparing suppliers, group by material or category.
- Flag materials with BOTH increasing price AND limited availability as high-risk.
- For cost analysis, calculate total spend as `unit_price_aud × last_order_qty`.
- Common construction suppliers: Supplier-B (steel), Supplier-A (concrete/aggregate), Supplier-D (concrete), Supplier-F (concrete), Supplier-I (fuel), Supplier-C (cement).

### Example SQL Queries

**1. Materials with increasing prices**

```sql
SELECT material_name, category, supplier, unit_price_aud, unit, availability
FROM contoso.procurement.materials
WHERE price_trend = 'increasing'
ORDER BY unit_price_aud DESC
```

**2. Supply chain risk — limited or out of stock materials**

```sql
SELECT material_name, category, supplier, unit_price_aud,
  lead_time_days, price_trend, availability
FROM contoso.procurement.materials
WHERE availability IN ('limited', 'out_of_stock')
ORDER BY availability, lead_time_days DESC
```

**3. Average price and lead time by category**

```sql
SELECT category, COUNT(*) AS materials,
  ROUND(AVG(unit_price_aud), 2) AS avg_price,
  ROUND(AVG(lead_time_days), 0) AS avg_lead_days
FROM contoso.procurement.materials
GROUP BY category
ORDER BY avg_price DESC
```

**4. All steel suppliers with pricing**

```sql
SELECT material_name, supplier, unit_price_aud, unit,
  lead_time_days, price_trend, availability
FROM contoso.procurement.materials
WHERE category = 'Steel'
ORDER BY unit_price_aud DESC
```

**5. Long lead time items over 30 days**

```sql
SELECT material_name, category, supplier,
  lead_time_days, availability, price_trend
FROM contoso.procurement.materials
WHERE lead_time_days > 30
ORDER BY lead_time_days DESC
```

**6. Highest spend items by last order value**

```sql
SELECT material_name, category, supplier, unit_price_aud, unit,
  last_order_qty,
  ROUND(unit_price_aud * last_order_qty, 2) AS estimated_spend_aud
FROM contoso.procurement.materials
ORDER BY estimated_spend_aud DESC
LIMIT 20
```

### Sample Questions

- Which materials have increasing price trends?
- Show all suppliers for steel products
- What materials have limited availability or are out of stock?
- Which categories have the longest lead times?
- Compare unit prices across suppliers for the same material
- What are the most expensive materials we procure?
- Show the supplier breakdown by category
- Which materials were last ordered more than 90 days ago?

### Benchmarks

| Question | Expected SQL |
|----------|-------------|
| What is total procurement spend? | `SELECT ROUND(SUM(unit_price_aud), 2) FROM contoso.procurement.materials` |
| How many suppliers are At Risk? | `SELECT COUNT(*) FROM contoso.supply_chain_gold.supplier_scorecard WHERE supplier_tier = 'At Risk'` |
| Show materials with supply risk | `SELECT material_name, supplier, availability, price_trend FROM contoso.procurement.materials WHERE price_trend = 'increasing' AND availability IN ('limited', 'out_of_stock')` |
| Which warehouse has the most critical items? | `SELECT warehouse_name, COUNT(*) AS cnt FROM contoso.supply_chain_gold.inventory_health WHERE stock_status = 'critical' GROUP BY warehouse_name ORDER BY cnt DESC LIMIT 1` |
| Average lead time for concrete | `SELECT ROUND(AVG(lead_time_days), 0) FROM contoso.procurement.materials WHERE category = 'Concrete'` |

### Extended Queries (Main Pipeline)

The main pipeline version adds **`supply_chain_gold.supplier_scorecard`** and **`supply_chain_gold.inventory_health`** tables, plus `total_cost_aud` and `project_id` columns on materials.

**Description:** Virtual procurement lead for Contoso Group. Analyses material spend and pricing trends, evaluates supplier performance via composite scorecards, monitors warehouse inventory levels, tracks supply risk (price + availability), and supports commercial negotiations.

**Additional instructions:** Key terminology additions: Supplier tier = Gold/Silver/Bronze/At Risk based on composite score. When asked about spend, always group by supplier or category and show `total_cost_aud`. When asked about supplier performance, use the `supplier_scorecard` table from the gold layer. When asked about inventory, show `stock_status` and flag items `below_reorder = TRUE`.

**Additional sample questions:**

- Show total procurement spend by supplier
- What is the supplier scorecard ranking?
- Which warehouses have stock below reorder point?
- Show overdue invoices by supplier
- What is the delivery damage rate by supplier?
- Show invoice aging summary

**1. Total procurement spend by supplier and category**

```sql
SELECT supplier, category,
  COUNT(*) AS orders,
  ROUND(SUM(total_cost_aud), 2) AS total_spend_aud,
  ROUND(AVG(unit_price_aud), 2) AS avg_unit_price,
  ROUND(AVG(lead_time_days), 0) AS avg_lead_days
FROM contoso.procurement.materials
GROUP BY supplier, category
ORDER BY total_spend_aud DESC
```

**2. Materials at supply risk**

```sql
SELECT material_name, category, supplier, unit_price_aud, unit,
  lead_time_days, price_trend, availability
FROM contoso.procurement.materials
WHERE price_trend = 'increasing' AND availability IN ('limited', 'out_of_stock')
ORDER BY unit_price_aud DESC
```

**3. Supplier scorecard ranking**

```sql
SELECT supplier, supplier_score, supplier_tier,
  deliveries, delivery_spend_aud,
  delivery_damage_rate_pct, cost_discrepancy_rate_pct,
  invoices, invoiced_aud, invoice_overdue_pct
FROM contoso.supply_chain_gold.supplier_scorecard
ORDER BY supplier_score DESC
```

**4. Warehouses with critical stock levels**

```sql
SELECT warehouse_name, region, material, on_hand_qty, reorder_point,
  stock_status, days_since_replenishment
FROM contoso.supply_chain_gold.inventory_health
WHERE stock_status IN ('critical', 'low')
ORDER BY CASE stock_status WHEN 'critical' THEN 1 ELSE 2 END, days_since_replenishment DESC
```

**5. Compare steel prices across suppliers**

```sql
SELECT supplier, material_name,
  ROUND(AVG(unit_price_aud), 2) AS avg_price_aud,
  ROUND(MIN(unit_price_aud), 2) AS min_price,
  ROUND(MAX(unit_price_aud), 2) AS max_price,
  COUNT(*) AS orders, price_trend
FROM contoso.procurement.materials
WHERE category = 'Steel'
GROUP BY supplier, material_name, price_trend
ORDER BY avg_price_aud
```

**6. Procurement spend by project**

```sql
SELECT f.project_name, f.division,
  COUNT(*) AS orders,
  ROUND(SUM(m.total_cost_aud), 2) AS procurement_spend_aud,
  COUNT(DISTINCT m.supplier) AS unique_suppliers,
  COUNT(DISTINCT m.category) AS material_categories
FROM contoso.procurement.materials m
JOIN contoso.projects.financials f ON m.project_id = f.project_id
WHERE m.project_id IS NOT NULL
GROUP BY f.project_name, f.division
ORDER BY procurement_spend_aud DESC
```

**7. At Risk suppliers with their issues**

```sql
SELECT supplier, supplier_score, supplier_tier,
  delivery_damage_rate_pct, cost_discrepancy_rate_pct,
  disputed_invoices, invoice_overdue_pct
FROM contoso.supply_chain_gold.supplier_scorecard
WHERE supplier_tier = 'At Risk'
ORDER BY supplier_score
```

**8. Inventory by region with reorder urgency**

```sql
SELECT region, warehouse_name,
  SUM(CASE WHEN stock_status = 'critical' THEN 1 ELSE 0 END) AS critical_items,
  SUM(CASE WHEN stock_status = 'low' THEN 1 ELSE 0 END) AS low_items,
  SUM(CASE WHEN stock_status = 'adequate' THEN 1 ELSE 0 END) AS adequate_items,
  SUM(CASE WHEN stock_status = 'surplus' THEN 1 ELSE 0 END) AS surplus_items
FROM contoso.supply_chain_gold.inventory_health
GROUP BY region, warehouse_name
ORDER BY critical_items DESC
```

---

## 5. Projects Agent

### Description

EVM-powered project portfolio analysis — budget tracking, SPI/CPI metrics, cost forecasting, and division benchmarking for Contoso Group.

### Agent Instructions

You are the Contoso Projects Agent — an AI assistant for CFOs, project controls managers, and executive leadership. You analyse Contoso's project portfolio using Earned Value Management (EVM) to assess cost and schedule performance.

Key EVM formulas and concepts:
- **SPI** (Schedule Performance Index) = EV / PV. Below 1.0 = behind schedule.
- **CPI** (Cost Performance Index) = EV / AC. Below 1.0 = over budget.
- **CV%** (Cost Variance %) = (EV − AC) / EV × 100. Negative = overspend.
- **EAC** (Estimate at Completion) = Budget / CPI. Useful for forecasting final cost.
- **RAG:** Red = SPI < 0.95 or CPI < 0.95 or CV% < −5%. Amber = minor variance. Green = on track.

Format monetary values with $ prefix and commas. For billions use $X.XXB format. When showing portfolio summaries, always include: total budget, total actuals, overall SPI, overall CPI. When comparing divisions, include project count for context. Always flag red-status projects with their cost variance prominently.

Divisions: Division-Alpha (major infrastructure — roads, rail, tunnels), Division-Beta (contract mining services), Division-Gamma (mineral processing plants), Division-Delta (PPP concessions).

### Example SQL Queries

**1. All red-status projects with financials**

```sql
SELECT project_name, division, budget_aud, actual_cost_aud,
  cost_variance_pct, spi, cpi, project_manager
FROM contoso.projects.financials
WHERE status = 'red'
ORDER BY cost_variance_pct ASC
```

**2. Portfolio summary by division**

```sql
SELECT division, COUNT(*) AS projects,
  ROUND(SUM(budget_aud)/1e9, 2) AS budget_b,
  ROUND(SUM(actual_cost_aud)/1e9, 2) AS actuals_b,
  ROUND(AVG(spi), 3) AS avg_spi, ROUND(AVG(cpi), 3) AS avg_cpi
FROM contoso.projects.financials
GROUP BY division
ORDER BY budget_b DESC
```

**3. Total portfolio budget vs actuals**

```sql
SELECT COUNT(*) AS total_projects,
  ROUND(SUM(budget_aud)/1e9, 2) AS total_budget_b,
  ROUND(SUM(actual_cost_aud)/1e9, 2) AS total_actuals_b,
  ROUND(SUM(actual_cost_aud - budget_aud)/1e6, 1) AS variance_m,
  ROUND(AVG(spi), 3) AS avg_spi, ROUND(AVG(cpi), 3) AS avg_cpi
FROM contoso.projects.financials
```

**4. Top 10 largest projects by budget**

```sql
SELECT project_name, division, client, budget_aud, actual_cost_aud,
  status, spi, cpi
FROM contoso.projects.financials
ORDER BY budget_aud DESC
LIMIT 10
```

**5. Projects behind schedule (SPI below 1.0)**

```sql
SELECT project_name, division, spi, cpi, status, planned_completion
FROM contoso.projects.financials
WHERE spi < 1.0
ORDER BY spi ASC
```

**6. Project manager performance**

```sql
SELECT project_manager, COUNT(*) AS projects,
  ROUND(AVG(cpi), 3) AS avg_cpi, ROUND(AVG(spi), 3) AS avg_spi,
  SUM(CASE WHEN status = 'red' THEN 1 ELSE 0 END) AS red_projects
FROM contoso.projects.financials
GROUP BY project_manager
ORDER BY avg_cpi DESC
```

**7. Cost overrun by state**

```sql
SELECT state, COUNT(*) AS projects,
  ROUND(SUM(budget_aud)/1e9, 2) AS budget_b,
  ROUND(SUM(actual_cost_aud - budget_aud)/1e6, 1) AS overrun_m
FROM contoso.projects.financials
GROUP BY state
ORDER BY overrun_m DESC
```

**8. Estimate at Completion for red projects**

```sql
SELECT project_name, division, budget_aud, actual_cost_aud, cpi,
  ROUND(budget_aud / cpi, 0) AS eac_aud,
  ROUND((budget_aud / cpi) - budget_aud, 0) AS forecast_overrun_aud
FROM contoso.projects.financials
WHERE status = 'red'
ORDER BY forecast_overrun_aud DESC
```

### Sample Questions

- Which projects are in red status and why?
- What is our total portfolio budget vs actual spend?
- Compare SPI and CPI across all divisions
- Show the top 5 largest projects by budget
- Which project managers have the best CPI?
- What is the total cost overrun across the portfolio?
- Show all projects completing in the next 12 months
- Rank divisions by average schedule performance

### Benchmarks

| Question | Expected SQL |
|----------|-------------|
| How many projects do we have? | `SELECT COUNT(*) FROM contoso.projects.financials` |
| Total portfolio budget | `SELECT ROUND(SUM(budget_aud), 2) FROM contoso.projects.financials` |
| Average CPI across portfolio | `SELECT ROUND(AVG(cpi), 2) FROM contoso.projects.financials` |
| How many projects are at risk? | `SELECT COUNT(*) FROM contoso.projects.financials WHERE status = 'at_risk'` |
| Total safety incidents | `SELECT COUNT(*) FROM contoso.safety.incidents` |
| Which project has the lowest CPI? | `SELECT project_name, cpi FROM contoso.projects.financials ORDER BY cpi ASC LIMIT 1` |

### Extended Queries (Main Pipeline)

The main pipeline version uses `pct_complete` column, `'at_risk'` status values, and `$XM` formatting conventions.

**Description:** Virtual project controls analyst for Contoso Group. Analyses project financials using Earned Value Management (EVM): SPI/CPI performance, budget vs actuals, cost variance, and risk classification. Supports CFOs, project controls managers, and commercial directors.

**Additional instructions:** Risk classification: Critical = CPI < 0.85 OR SPI < 0.85. High = CPI < 0.95 OR SPI < 0.95. Medium = within 5% of plan. Low = on or ahead of plan. When asked about 'red status' or 'problem projects', show projects where `status = 'at_risk' OR cpi < 0.9 OR spi < 0.9`. When asked for EAC, calculate as `budget_aud / cpi`. All monetary values in AUD with commas. Use 'M' suffix for millions (e.g. $45.2M).

**Additional sample questions:**

- Which projects are in red status?
- Show me at-risk projects with their project managers
- Compare completion percentage across divisions
- Which project managers have the most at-risk projects?

**1. Projects in red status (at_risk or low CPI/SPI)**

```sql
SELECT project_name, division, status,
  ROUND(budget_aud / 1e6, 1) AS budget_m,
  ROUND(actual_cost_aud / 1e6, 1) AS spent_m,
  spi, cpi, pct_complete, project_manager
FROM contoso.projects.financials
WHERE status = 'at_risk' OR cpi < 0.9 OR spi < 0.9
ORDER BY cpi ASC
```

**2. SPI and CPI by division**

```sql
SELECT division,
  COUNT(*) AS projects,
  ROUND(AVG(spi), 2) AS avg_spi,
  ROUND(AVG(cpi), 2) AS avg_cpi,
  ROUND(SUM(budget_aud) / 1e6, 1) AS total_budget_m,
  SUM(CASE WHEN status = 'at_risk' THEN 1 ELSE 0 END) AS at_risk
FROM contoso.projects.financials
GROUP BY division
ORDER BY avg_cpi
```

**3. Budget vs actual cost for all projects**

```sql
SELECT project_name, division,
  ROUND(budget_aud / 1e6, 1) AS budget_m,
  ROUND(actual_cost_aud / 1e6, 1) AS actual_m,
  ROUND((budget_aud - actual_cost_aud) / 1e6, 1) AS variance_m,
  ROUND(cost_variance_pct, 1) AS cv_pct,
  status, pct_complete
FROM contoso.projects.financials
ORDER BY cost_variance_pct ASC
```

**4. Top 5 cost overruns with EAC**

```sql
SELECT project_name, division,
  ROUND(budget_aud / 1e6, 1) AS budget_m,
  ROUND(actual_cost_aud / 1e6, 1) AS actual_m,
  ROUND((actual_cost_aud - budget_aud) / 1e6, 1) AS overrun_m,
  ROUND(budget_aud / NULLIF(cpi, 0) / 1e6, 1) AS eac_m,
  cpi, spi, project_manager
FROM contoso.projects.financials
WHERE actual_cost_aud > budget_aud
ORDER BY (actual_cost_aud - budget_aud) DESC
LIMIT 5
```

**5. Completion percentage across divisions**

```sql
SELECT division,
  COUNT(*) AS projects,
  ROUND(AVG(pct_complete), 1) AS avg_completion,
  ROUND(MIN(pct_complete), 1) AS min_completion,
  ROUND(MAX(pct_complete), 1) AS max_completion
FROM contoso.projects.financials
GROUP BY division
ORDER BY avg_completion
```

**6. Project managers with the most at-risk projects**

```sql
SELECT project_manager,
  COUNT(*) AS total_projects,
  SUM(CASE WHEN status = 'at_risk' THEN 1 ELSE 0 END) AS at_risk,
  ROUND(AVG(cpi), 2) AS avg_cpi,
  ROUND(AVG(spi), 2) AS avg_spi
FROM contoso.projects.financials
GROUP BY project_manager
HAVING SUM(CASE WHEN status = 'at_risk' THEN 1 ELSE 0 END) > 0
ORDER BY at_risk DESC
```

---

## Appendix: Genie API Reference

### Conversation APIs (querying data)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/2.0/genie/spaces/{space_id}/start-conversation` | POST | Start new conversation with initial question |
| `/api/2.0/genie/spaces/{space_id}/conversations/{cid}/messages` | POST | Send follow-up question (multi-turn) |
| `/api/2.0/genie/spaces/{space_id}/conversations/{cid}/messages/{mid}` | GET | Poll for message status and generated SQL |
| `/api/2.0/genie/spaces/{space_id}/conversations/{cid}/messages/{mid}/attachments/{aid}/query-result` | GET | Fetch data rows from a query |
| `/api/2.0/genie/spaces/{space_id}/conversations/{cid}/messages/{mid}/feedback` | POST | Submit thumbs up/down feedback |

### Management APIs (CI/CD)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/2.0/genie/spaces` | POST | Create a new Genie Space |
| `/api/2.0/genie/spaces/{space_id}` | GET | Retrieve space configuration |
| `/api/2.0/genie/spaces/{space_id}` | PATCH | Update space configuration |
| `/api/2.0/genie/spaces/{space_id}` | DELETE | Delete a space |

### Foundry Integration (MCP)

```
Foundry Agent → MCP tool_call → Databricks Managed MCP Server
    → POST /genie/spaces/{id}/start-conversation
    → GET  /genie/.../messages/{mid}  (poll)
    → GET  /genie/.../query-result    (fetch data)
    ← MCP tool_result → Agent presents answer
```

- **Auth:** OAuth Identity Passthrough — each user's Entra ID identity
- **Per-user RLS:** Unity Catalog row filters enforced per signed-in user

### API vs UI Limitations

| Feature | API | UI |
|---------|-----|-----|
| NL-to-SQL + follow-ups | ✅ | ✅ |
| Rate limit | 5 QPM | 20 QPM |
| File upload (CSV/Excel) | ❌ | ✅ |
| Autoflow / Think Deeper | ❌ | ✅ |
| Dashboard assembly | ❌ | ✅ |
| Monitoring tab | ❌ | ✅ |
| Space CRUD | ✅ | ✅ |
| Feedback | ✅ | ✅ |

### Best Practices

1. **Start small** — 5-10 tables, focused on one topic
2. **Use gold-layer views** — pre-joined, business-ready
3. **Instruction priority:** SQL expressions > Example SQL > Text instructions
4. **Metadata quality:** column COMMENTs, synonyms, entity_matching, format_assistance
5. **Testing:** benchmarks for accuracy, multiple phrasings, edge cases
