# Databricks notebook source
# MAGIC %md
# MAGIC # Module 03 -- Domain-Specific Genie Spaces
# MAGIC
# MAGIC Creates **5 Genie Spaces** on the `contoso` catalog: one cross-domain intelligence
# MAGIC space and four specialised domain spaces, each with deep, domain-expert
# MAGIC instructions, example SQLs, and sample questions.
# MAGIC
# MAGIC | Space | Tables | Persona |
# MAGIC |-------|--------|---------|
# MAGIC | Contoso Project Intelligence | All 4: `projects.financials`, `safety.incidents`, `equipment.equipment_telemetry`, `procurement.materials` | Cross-domain Operations Intelligence |
# MAGIC | Projects Agent | `projects.financials` | CFO / Project Controls |
# MAGIC | Safety Agent | `safety.incidents` | HSE Manager |
# MAGIC | Equipment Agent | `equipment.equipment_telemetry` | Fleet Operations Manager |
# MAGIC | Procurement Agent | `procurement.materials` | Procurement Director |
# MAGIC
# MAGIC Parameterised via `customer_name` so it can be rebranded for any customer.

# COMMAND ----------

dbutils.widgets.text("catalog_name", "contoso", "Catalog Name")
dbutils.widgets.text("customer_name", "Contoso", "Customer Display Name")
dbutils.widgets.text("warehouse_name", "Serverless Starter Warehouse", "SQL Warehouse Name")

catalog = dbutils.widgets.get("catalog_name")
customer = dbutils.widgets.get("customer_name")
warehouse_name = dbutils.widgets.get("warehouse_name")

# COMMAND ----------

import requests, json, uuid, time as _time

host = spark.conf.get("spark.databricks.workspaceUrl")
token = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()
user = dbutils.notebook.entry_point.getDbutils().notebook().getContext().userName().get()
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
base_url = f"https://{host}/api/2.0"

# Find warehouse
resp = requests.get(f"{base_url}/sql/warehouses", headers=headers)
resp.raise_for_status()
warehouse_id = None
for wh in resp.json().get("warehouses", []):
    if wh["name"] == warehouse_name:
        warehouse_id = wh["id"]
        break
assert warehouse_id, f"Warehouse '{warehouse_name}' not found"
print(f"[OK] Warehouse: {warehouse_id}")

# COMMAND ----------

C = catalog

def gen_ids(n):
    """Generate n sorted 32-char hex IDs matching the Genie v2 format."""
    ids = []
    for i in range(n):
        hi = int(_time.time() * 1000)
        lo = int.from_bytes(uuid.uuid4().bytes[:8], "big")
        ids.append(f"{hi:016x}{lo:016x}")
        _time.sleep(0.001)
    return sorted(ids)


def create_space(title, description, serialized_space):
    """Create or update a Genie Space via v2 API (idempotent)."""
    # Extract sample_questions from serialized_space config for top-level API field
    top_level_questions = []
    for sq in serialized_space.get("config", {}).get("sample_questions", []):
        q_text = sq.get("question", [""])[0] if isinstance(sq.get("question"), list) else sq.get("question", "")
        if q_text:
            top_level_questions.append({"question": q_text})

    payload = {
        "title": title,
        "description": description,
        "warehouse_id": warehouse_id,
        "parent_path": f"/Workspace/Users/{user}",
        "serialized_space": json.dumps(serialized_space),
        "sample_questions": top_level_questions,
    }
    # Check if space with this title already exists
    existing_id = None
    resp_list = requests.get(f"{base_url}/genie/spaces", headers=headers)
    if resp_list.status_code == 200:
        for s in resp_list.json().get("spaces", resp_list.json().get("genie_spaces", [])):
            if s.get("title") == title:
                existing_id = s.get("space_id") or s.get("id")
                break
    if existing_id:
        resp = requests.patch(
            f"{base_url}/genie/spaces/{existing_id}",
            headers=headers,
            data=json.dumps(payload),
        )
        if resp.status_code in (200, 201):
            print(f"  [OK] Updated: {existing_id}  URL: https://{host}/genie/rooms/{existing_id}")
            return existing_id
        print(f"  [WARN] Update failed ({resp.status_code}), creating new...")
    # Create new
    resp = requests.post(
        f"{base_url}/genie/spaces",
        headers=headers,
        data=json.dumps(payload),
    )
    if resp.status_code in (200, 201):
        sid = resp.json().get("space_id") or resp.json().get("id")
        print(f"  [OK] Created: {sid}  URL: https://{host}/genie/rooms/{sid}")
        return sid
    # Fallback: strip join_specs and sql_snippets
    ss = dict(serialized_space)
    if "instructions" in ss:
        ss["instructions"].pop("join_specs", None)
        ss["instructions"].pop("sql_snippets", None)
    payload["serialized_space"] = json.dumps(ss)
    resp2 = requests.post(f"{base_url}/genie/spaces", headers=headers, data=json.dumps(payload))
    if resp2.status_code in (200, 201):
        sid = resp2.json().get("space_id") or resp2.json().get("id")
        print(f"  [OK] Created (fallback): {sid}  URL: https://{host}/genie/rooms/{sid}")
        return sid
    print(f"  [FAIL] {resp2.status_code}: {resp2.text[:300]}")
    return None

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Contoso Project Intelligence
# MAGIC
# MAGIC Cross-domain operations intelligence covering project finance, safety,
# MAGIC equipment, and procurement. Includes ALL 4 tables with cross-domain joins.

# COMMAND ----------

sq = gen_ids(8)
ti = gen_ids(1)
eq = gen_ids(5)
js = gen_ids(3)
bm = gen_ids(6)

intelligence_space = {
    "version": 2,
    "config": {
        "sample_questions": [
            {"id": sq[0], "question": [f"How many {customer} projects are in red status?"]},
            {"id": sq[1], "question": ["What is the average SPI by division?"]},
            {"id": sq[2], "question": ["Show all equipment with critical or warning status"]},
            {"id": sq[3], "question": ["Which sites have the most safety incidents?"]},
            {"id": sq[4], "question": ["What materials have increasing price trends?"]},
            {"id": sq[5], "question": [f"Compare budget vs actuals for all {customer} divisions"]},
            {"id": sq[6], "question": ["Which divisions have both over-budget projects and rising incident counts?"]},
            {"id": sq[7], "question": ["Show equipment alerts at sites with recent safety incidents"]},
        ]
    },
    "data_sources": {
        "tables": sorted([
            {
                "identifier": f"{C}.projects.financials",
                "description": [f"{customer} project financials with EVM metrics, RAG status, budgets, and schedule tracking across all divisions"],
                "column_configs": sorted([
                    {"column_name": "project_id", "description": ["Unique project identifier, e.g. P-2024-001"]},
                    {"column_name": "project_name", "description": ["Full project name"]},
                    {"column_name": "division", "enable_format_assistance": True, "enable_entity_matching": True, "description": ["Operating division: Division-Alpha, Division-Beta, Division-Gamma, Division-Delta"]},
                    {"column_name": "status", "enable_format_assistance": True, "enable_entity_matching": True, "description": ["RAG status: green, amber, red"]},
                    {"column_name": "spi", "description": ["Schedule Performance Index. EV/PV. Below 1.0 = behind schedule"]},
                    {"column_name": "cpi", "description": ["Cost Performance Index. EV/AC. Below 1.0 = over budget"]},
                    {"column_name": "budget_aud", "description": ["Approved budget in AUD"]},
                    {"column_name": "actual_cost_aud", "description": ["Costs incurred to date in AUD"]},
                    {"column_name": "cost_variance_pct", "description": ["Cost variance percentage: (EV-AC)/EV*100"]},
                    {"column_name": "state", "enable_format_assistance": True, "enable_entity_matching": True, "description": ["Australian state: NSW, QLD, VIC, WA, SA"]},
                    {"column_name": "project_type", "enable_format_assistance": True, "enable_entity_matching": True},
                ], key=lambda x: x["column_name"]),
            },
            {
                "identifier": f"{C}.safety.incidents",
                "description": [f"{customer} workplace health and safety incident records including severity, root cause analysis, and corrective actions"],
                "column_configs": sorted([
                    {"column_name": "incident_id", "description": ["Unique incident reference"]},
                    {"column_name": "incident_date", "description": ["Date the incident occurred"]},
                    {"column_name": "site_name", "enable_format_assistance": True, "enable_entity_matching": True, "description": ["Project site where the incident occurred"]},
                    {"column_name": "division", "enable_format_assistance": True, "enable_entity_matching": True, "description": ["Operating division: Division-Alpha, Division-Beta, Division-Gamma, Division-Delta"]},
                    {"column_name": "severity", "enable_format_assistance": True, "enable_entity_matching": True, "description": ["Minor, Moderate, Serious, Critical"]},
                    {"column_name": "incident_type", "enable_format_assistance": True, "enable_entity_matching": True},
                    {"column_name": "root_cause", "enable_format_assistance": True, "enable_entity_matching": True, "description": ["human_error, equipment_failure, procedural, environmental, design, poor_housekeeping, inadequate_training"]},
                    {"column_name": "status", "enable_format_assistance": True, "enable_entity_matching": True, "description": ["open, investigating, closed"]},
                    {"column_name": "lost_time_days", "description": ["Lost Time Injury days. 0 if no time lost"]},
                    {"column_name": "injuries", "description": ["Number of people injured (0 for near-misses)"]},
                ], key=lambda x: x["column_name"]),
            },
            {
                "identifier": f"{C}.equipment.equipment_telemetry",
                "description": [f"{customer} heavy equipment fleet IoT telemetry data including engine temp, fuel levels, and maintenance scheduling"],
                "column_configs": sorted([
                    {"column_name": "equipment_id", "description": ["Equipment ID, e.g. HT-001 (haul truck), EX-005 (excavator)"]},
                    {"column_name": "equipment_type", "enable_format_assistance": True, "enable_entity_matching": True, "description": ["Type: haul_truck, excavator, drill, loader, dozer, grader, water_cart, crane"]},
                    {"column_name": "division", "enable_format_assistance": True, "enable_entity_matching": True},
                    {"column_name": "site_name", "enable_format_assistance": True, "enable_entity_matching": True, "description": ["Project site where equipment is deployed"]},
                    {"column_name": "status", "enable_format_assistance": True, "enable_entity_matching": True, "description": ["operational, warning, critical, maintenance"]},
                    {"column_name": "engine_temp_celsius", "description": ["Engine temp. Normal 70-95, Warning 95-110, Critical >110"]},
                    {"column_name": "fuel_level_pct", "description": ["Fuel level 0-100%"]},
                    {"column_name": "operating_hours", "description": ["Cumulative engine operating hours"]},
                ], key=lambda x: x["column_name"]),
            },
            {
                "identifier": f"{C}.procurement.materials",
                "description": [f"{customer} material procurement records with supplier pricing, lead times, and market availability"],
                "column_configs": sorted([
                    {"column_name": "category", "enable_format_assistance": True, "enable_entity_matching": True, "description": ["Steel, Concrete, Fuel, Precast, Geosynthetics, Safety, Site Consumables, Electrical, Aggregate, Timber"]},
                    {"column_name": "supplier", "enable_format_assistance": True, "enable_entity_matching": True},
                    {"column_name": "price_trend", "enable_format_assistance": True, "enable_entity_matching": True, "description": ["increasing, stable, decreasing"]},
                    {"column_name": "availability", "enable_format_assistance": True, "enable_entity_matching": True, "description": ["good, moderate, limited, out_of_stock"]},
                    {"column_name": "unit_price_aud", "description": ["Price per unit in AUD"]},
                    {"column_name": "lead_time_days", "description": ["Days from order to delivery"]},
                ], key=lambda x: x["column_name"]),
            },
        ], key=lambda x: x["identifier"]),
    },
    "instructions": {
        "text_instructions": [{
            "id": ti[0],
            "content": [
                f"You are the {customer} Project Intelligence assistant — a cross-domain operations analyst. ",
                f"This Genie Space covers {customer} Group operational data across 4 domains: ",
                "Project Financials (EVM metrics, RAG status, budgets), Safety Incidents (HSE records, severity, root causes), ",
                "Equipment Telemetry (fleet sensor data, maintenance), Procurement Materials (supplier pricing, availability). ",
                "Key terminology: SPI = Schedule Performance Index (EV/PV). 1.0 = on schedule, <1.0 = behind. ",
                "CPI = Cost Performance Index (EV/AC). 1.0 = on budget, <1.0 = over budget. ",
                "EAC = Estimate at Completion = Budget / CPI. RAG = Red/Amber/Green. ",
                "LTI = Lost Time Injury. Near-miss = incident with 0 injuries. ",
                f"Divisions: Division-Alpha, Division-Beta, Division-Gamma, Division-Delta. ",
                "Division is the primary join key across all 4 tables. Site_name links incidents to equipment. ",
                "All monetary values are in AUD. Format with commas and $ prefix. ",
                "When comparing divisions, always include project counts for context. ",
                "Flag red-status projects, critical equipment, and serious incidents prominently. ",
                "Look for cross-domain patterns: divisions with both cost overruns and safety issues need attention."
            ]
        }],
        "example_question_sqls": sorted([
            {"id": eq[0], "question": ["Division performance across finance and safety"],
             "sql": [f"SELECT f.division, COUNT(DISTINCT f.project_id) AS projects, ROUND(AVG(f.cpi), 2) AS avg_cpi, ROUND(AVG(f.spi), 2) AS avg_spi, COUNT(DISTINCT i.incident_id) AS incidents, SUM(i.lost_time_days) AS lti_days\n",
                     f"FROM {C}.projects.financials f\n",
                     f"LEFT JOIN {C}.safety.incidents i ON f.division = i.division\n",
                     "GROUP BY f.division\n", "ORDER BY avg_cpi"]},
            {"id": eq[1], "question": ["Sites with both safety incidents and equipment alerts"],
             "sql": [f"SELECT i.site_name, i.division, COUNT(DISTINCT i.incident_id) AS incidents, COUNT(DISTINCT e.equipment_id) AS equipment_alerts\n",
                     f"FROM {C}.safety.incidents i\n",
                     f"JOIN {C}.equipment.equipment_telemetry e ON i.site_name = e.site_name\n",
                     "WHERE e.status IN ('warning', 'critical')\n",
                     "GROUP BY i.site_name, i.division\n", "ORDER BY incidents DESC"]},
            {"id": eq[2], "question": ["Red-status projects with full details"],
             "sql": [f"SELECT project_name, division, budget_aud, actual_cost_aud, cost_variance_pct, spi, cpi\n",
                     f"FROM {C}.projects.financials\n", "WHERE status = 'red'\n", "ORDER BY cost_variance_pct ASC"]},
            {"id": eq[3], "question": ["Materials with increasing prices and limited availability"],
             "sql": [f"SELECT material_name, category, supplier, unit_price_aud, availability\n",
                     f"FROM {C}.procurement.materials\n", "WHERE price_trend = 'increasing'\n", "ORDER BY unit_price_aud DESC"]},
            {"id": eq[4], "question": ["Equipment status summary by division"],
             "sql": [f"SELECT division, status, COUNT(*) AS units\n",
                     f"FROM {C}.equipment.equipment_telemetry\n", "GROUP BY division, status\n", "ORDER BY division"]},
        ], key=lambda x: x["id"]),
        "join_specs": sorted([
            {"id": js[0],
             "left": {"identifier": f"{C}.projects.financials", "alias": "fin"},
             "right": {"identifier": f"{C}.safety.incidents", "alias": "inc"},
             "sql": ["`fin`.`division` = `inc`.`division`", "--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_MANY--"],
             "comment": ["Cross-domain: project financials to safety incidents"], "instruction": ["Join by division for portfolio-level safety analysis"]},
            {"id": js[1],
             "left": {"identifier": f"{C}.projects.financials", "alias": "fin"},
             "right": {"identifier": f"{C}.equipment.equipment_telemetry", "alias": "equip"},
             "sql": ["`fin`.`division` = `equip`.`division`", "--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_MANY--"],
             "comment": ["Cross-domain: project financials to equipment"], "instruction": ["Join by division for equipment cost context"]},
            {"id": js[2],
             "left": {"identifier": f"{C}.safety.incidents", "alias": "inc"},
             "right": {"identifier": f"{C}.equipment.equipment_telemetry", "alias": "equip"},
             "sql": ["`inc`.`site_name` = `equip`.`site_name`", "--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_MANY--"],
             "comment": ["Cross-domain: incidents to equipment by site"], "instruction": ["Join by site_name for equipment-incident correlation"]},
        ], key=lambda x: x["id"]),
        "sql_snippets": {},
    },
    "benchmarks": sorted([
        {"id": bm[0], "question": [f"How many {customer} projects are in red status?"], "expected_sql": [f"SELECT COUNT(*) FROM {C}.projects.financials WHERE status = 'red'"]},
        {"id": bm[1], "question": ["Which division has the most safety incidents?"], "expected_sql": [f"SELECT division, COUNT(*) AS cnt FROM {C}.safety.incidents GROUP BY division ORDER BY cnt DESC LIMIT 1"]},
        {"id": bm[2], "question": ["How many equipment units have critical status?"], "expected_sql": [f"SELECT COUNT(*) FROM {C}.equipment.equipment_telemetry WHERE status = 'critical'"]},
        {"id": bm[3], "question": ["What is the average CPI across the portfolio?"], "expected_sql": [f"SELECT ROUND(AVG(cpi), 2) FROM {C}.projects.financials"]},
        {"id": bm[4], "question": ["Show materials with increasing price trends"], "expected_sql": [f"SELECT material_name, supplier, unit_price_aud FROM {C}.procurement.materials WHERE price_trend = 'increasing'"]},
        {"id": bm[5], "question": ["Total lost time days across all divisions"], "expected_sql": [f"SELECT SUM(lost_time_days) FROM {C}.safety.incidents"]},
    ], key=lambda x: x["id"]),
}

print(f"Creating {customer} Project Intelligence...")
intelligence_id = create_space(
    f"{customer} Project Intelligence",
    f"Cross-domain operations intelligence covering project finance, safety, equipment, and procurement for {customer} Group",
    intelligence_space,
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Safety Agent

# COMMAND ----------

sq = gen_ids(8)
ti = gen_ids(1)
eq = gen_ids(6)

safety_space = {
    "version": 2,
    "config": {
        "sample_questions": [
            {"id": sq[0], "question": ["How many open safety incidents do we have right now?"]},
            {"id": sq[1], "question": ["What are the most common incident types across all divisions?"]},
            {"id": sq[2], "question": ["Show all critical severity incidents in the last 6 months"]},
            {"id": sq[3], "question": ["Which sites have the highest incident frequency?"]},
            {"id": sq[4], "question": ["What is the total lost time days by division?"]},
            {"id": sq[5], "question": ["Show root cause breakdown for equipment failure incidents"]},
            {"id": sq[6], "question": ["Are there any incidents still under investigation?"]},
            {"id": sq[7], "question": ["Compare safety performance between Division-Alpha and Division-Beta"]},
        ]
    },
    "data_sources": {
        "tables": [
            {
                "identifier": f"{C}.safety.incidents",
                "description": [
                    f"{customer} workplace health and safety (WHS) incident records. "
                    "Each row is a single incident with severity classification, root cause analysis, "
                    "corrective actions taken, injury count, and lost time days. "
                    "Covers all divisions and project sites across Australia."
                ],
                "column_configs": sorted([
                    {"column_name": "incident_id", "description": ["Unique incident reference, e.g. INC-000001"]},
                    {"column_name": "incident_date", "description": ["Date the incident occurred"]},
                    {"column_name": "site_name", "enable_format_assistance": True, "enable_entity_matching": True,
                     "description": ["Project site where the incident occurred, e.g. Sydney Metro West, Bowen Basin"]},
                    {"column_name": "division", "enable_format_assistance": True, "enable_entity_matching": True,
                     "description": ["Operating division: Division-Alpha, Division-Beta, Division-Gamma, Division-Delta"]},
                    {"column_name": "incident_type", "enable_format_assistance": True, "enable_entity_matching": True,
                     "description": ["Type of incident: slip_trip_fall, struck_by, caught_in_between, heat_stress, electrical, vehicle_collision, falling_object, chemical_exposure, manual_handling, noise_exposure, confined_space, dust_inhalation, equipment_failure, near_miss, ergonomic"]},
                    {"column_name": "severity", "enable_format_assistance": True, "enable_entity_matching": True,
                     "description": ["Severity classification: Minor (first aid), Moderate (medical treatment), Serious (lost time), Critical (permanent disability/fatality risk)"]},
                    {"column_name": "description", "description": ["Free-text description of the incident"]},
                    {"column_name": "injuries", "description": ["Number of people injured. 0 for near-misses and property-only damage"]},
                    {"column_name": "lost_time_days", "description": ["Total Lost Time Injury (LTI) days. 0 if the worker returned to duty immediately"]},
                    {"column_name": "root_cause", "enable_format_assistance": True, "enable_entity_matching": True,
                     "description": ["Root cause category: human_error, equipment_failure, procedural, environmental, design, poor_housekeeping, inadequate_training"]},
                    {"column_name": "corrective_action", "description": ["Description of corrective or preventive action taken"]},
                    {"column_name": "status", "enable_format_assistance": True, "enable_entity_matching": True,
                     "description": ["Investigation status: open (new/unresolved), investigating (under review), closed (resolved with corrective action)"]},
                ], key=lambda x: x["column_name"]),
            }
        ]
    },
    "instructions": {
        "text_instructions": [{
            "id": ti[0],
            "content": [
                f"You are the {customer} Safety Agent — an AI assistant for WHS managers and site supervisors. ",
                f"You analyse {customer} Group's incident data to identify safety trends, high-risk sites, and root cause patterns. ",
                "Key terminology: ",
                "- LTI = Lost Time Injury (any incident causing ≥1 day off work). ",
                "- LTIFR = Lost Time Injury Frequency Rate = (LTIs × 1,000,000) / total hours worked. ",
                "- Near-miss = incident with 0 injuries but potential for harm. ",
                "- Severity levels: Minor (first aid only), Moderate (medical treatment), Serious (LTI), Critical (life-threatening). ",
                "- Always highlight Critical and Serious incidents prominently. ",
                "- When showing incident counts, also show total injuries and lost time days for context. ",
                "- For trend analysis, group by month using incident_date. ",
                "- Root cause analysis is critical: always flag 'equipment_failure' and 'inadequate_training' as systemic issues. ",
                f"Divisions: Division-Alpha (infrastructure), Division-Beta (mining services), Division-Gamma (mineral processing), Division-Delta (PPPs)."
            ]
        }],
        "example_question_sqls": sorted([
            {"id": eq[0], "question": ["Show all open incidents with severity"],
             "sql": [f"SELECT incident_id, incident_date, site_name, division, incident_type, severity, injuries, lost_time_days\n",
                     f"FROM {C}.safety.incidents\n", "WHERE status = 'open'\n", "ORDER BY incident_date DESC"]},
            {"id": eq[1], "question": ["Incident count and severity breakdown by division"],
             "sql": [f"SELECT division, severity, COUNT(*) AS count, SUM(injuries) AS total_injuries, SUM(lost_time_days) AS total_lti_days\n",
                     f"FROM {C}.safety.incidents\n", "GROUP BY division, severity\n", "ORDER BY division, CASE severity WHEN 'Critical' THEN 1 WHEN 'Serious' THEN 2 WHEN 'Moderate' THEN 3 ELSE 4 END"]},
            {"id": eq[2], "question": ["Top root causes for all incidents"],
             "sql": [f"SELECT root_cause, COUNT(*) AS incidents, SUM(injuries) AS injuries, ROUND(AVG(lost_time_days), 1) AS avg_lti_days\n",
                     f"FROM {C}.safety.incidents\n", "GROUP BY root_cause\n", "ORDER BY incidents DESC"]},
            {"id": eq[3], "question": ["Sites with the most incidents"],
             "sql": [f"SELECT site_name, division, COUNT(*) AS incidents, SUM(CASE WHEN severity IN ('Critical','Serious') THEN 1 ELSE 0 END) AS critical_serious\n",
                     f"FROM {C}.safety.incidents\n", "GROUP BY site_name, division\n", "ORDER BY incidents DESC\n", "LIMIT 15"]},
            {"id": eq[4], "question": ["Monthly incident trend"],
             "sql": [f"SELECT DATE_TRUNC('month', incident_date) AS month, COUNT(*) AS incidents, SUM(injuries) AS injuries\n",
                     f"FROM {C}.safety.incidents\n", "GROUP BY DATE_TRUNC('month', incident_date)\n", "ORDER BY month"]},
            {"id": eq[5], "question": ["All critical incidents with full details"],
             "sql": [f"SELECT incident_id, incident_date, site_name, division, incident_type, description, injuries, lost_time_days, root_cause, corrective_action\n",
                     f"FROM {C}.safety.incidents\n", "WHERE severity = 'Critical'\n", "ORDER BY incident_date DESC"]},
        ], key=lambda x: x["id"]),
        "sql_snippets": {},
    },
}

print(f"Creating Safety Agent...")
safety_id = create_space(
    f"{customer} Safety Agent",
    f"WHS incident analysis, severity trends, root cause patterns, and site safety performance for {customer} Group",
    safety_space,
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Equipment Agent

# COMMAND ----------

sq = gen_ids(8)
ti = gen_ids(1)
eq = gen_ids(6)

equipment_space = {
    "version": 2,
    "config": {
        "sample_questions": [
            {"id": sq[0], "question": ["Which equipment units have critical status right now?"]},
            {"id": sq[1], "question": ["What is the average engine temperature by equipment type?"]},
            {"id": sq[2], "question": ["Show all equipment with maintenance overdue"]},
            {"id": sq[3], "question": ["How many units does each division operate?"]},
            {"id": sq[4], "question": ["Which sites have the most equipment with warning or critical status?"]},
            {"id": sq[5], "question": ["Show fuel levels below 20% — which units need refuelling?"]},
            {"id": sq[6], "question": ["What is the fleet utilisation breakdown by status?"]},
            {"id": sq[7], "question": ["List all excavators sorted by operating hours"]},
        ]
    },
    "data_sources": {
        "tables": [
            {
                "identifier": f"{C}.equipment.equipment_telemetry",
                "description": [
                    f"{customer} heavy equipment fleet IoT telemetry from on-board sensors. "
                    "Each row is a single sensor reading with engine temperature, fuel level, "
                    "operating hours, and maintenance scheduling. Equipment types include haul trucks, "
                    "excavators, drills, loaders, dozers, graders, water carts, and cranes "
                    "operating across mining and infrastructure sites."
                ],
                "column_configs": sorted([
                    {"column_name": "equipment_id", "description": ["Unique equipment identifier. Prefix indicates type: HT=haul_truck, EX=excavator, DR=drill, LD=loader, DZ=dozer, GR=grader, WC=water_cart, CR=crane"]},
                    {"column_name": "equipment_type", "enable_format_assistance": True, "enable_entity_matching": True,
                     "description": ["Equipment category: haul_truck, excavator, drill, loader, dozer, grader, water_cart, crane"]},
                    {"column_name": "site_name", "enable_format_assistance": True, "enable_entity_matching": True,
                     "description": ["Project site where the equipment is deployed"]},
                    {"column_name": "division", "enable_format_assistance": True, "enable_entity_matching": True,
                     "description": ["Operating division: Division-Alpha, Division-Beta, Division-Gamma, Division-Delta"]},
                    {"column_name": "engine_temp_celsius", "description": ["Engine temperature in Celsius. Normal: 70-95°C. Warning: 95-110°C. Critical: >110°C. Cold: <70°C (idle/shutdown)"]},
                    {"column_name": "fuel_level_pct", "description": ["Fuel tank level as percentage (0-100). Below 20% is low, below 10% is critical"]},
                    {"column_name": "operating_hours", "description": ["Cumulative engine operating hours since commissioning. Used for maintenance scheduling (service intervals every 250/500/1000 hrs)"]},
                    {"column_name": "maintenance_due_date", "description": ["Next scheduled maintenance date. If past today, maintenance is overdue"]},
                    {"column_name": "status", "enable_format_assistance": True, "enable_entity_matching": True,
                     "description": ["Current equipment status: operational (running normally), warning (elevated readings), critical (immediate attention needed), maintenance (planned downtime)"]},
                    {"column_name": "reading_timestamp", "description": ["UTC timestamp of the sensor reading"]},
                ], key=lambda x: x["column_name"]),
            }
        ]
    },
    "instructions": {
        "text_instructions": [{
            "id": ti[0],
            "content": [
                f"You are the {customer} Equipment Agent — an AI assistant for fleet operations managers and maintenance planners. ",
                f"You monitor {customer}'s heavy equipment fleet across mining and infrastructure sites. ",
                "Key thresholds: ",
                "- Engine temperature: Normal 70-95°C, Warning 95-110°C, Critical >110°C. ",
                "- Fuel level: Good >50%, Low 10-20%, Critical <10%. ",
                "- Operating hours: Major service every 1000 hrs, minor service every 250 hrs. ",
                "- Status priority: always surface 'critical' first, then 'warning', then 'maintenance'. ",
                "When asked about fleet health, show a count by status (operational/warning/critical/maintenance). ",
                "When asked about a specific equipment type, show all units of that type with their latest readings. ",
                "Maintenance overdue = maintenance_due_date < current_date(). Flag these prominently. ",
                "Equipment ID prefixes: HT=haul truck, EX=excavator, DR=drill, LD=loader, DZ=dozer, GR=grader, WC=water cart, CR=crane."
            ]
        }],
        "example_question_sqls": sorted([
            {"id": eq[0], "question": ["All critical and warning equipment"],
             "sql": [f"SELECT equipment_id, equipment_type, site_name, division, engine_temp_celsius, fuel_level_pct, status\n",
                     f"FROM {C}.equipment.equipment_telemetry\n", "WHERE status IN ('critical', 'warning')\n", "ORDER BY CASE status WHEN 'critical' THEN 1 ELSE 2 END, engine_temp_celsius DESC"]},
            {"id": eq[1], "question": ["Fleet status breakdown by division"],
             "sql": [f"SELECT division, status, COUNT(*) AS units\n",
                     f"FROM {C}.equipment.equipment_telemetry\n", "GROUP BY division, status\n", "ORDER BY division, CASE status WHEN 'critical' THEN 1 WHEN 'warning' THEN 2 WHEN 'maintenance' THEN 3 ELSE 4 END"]},
            {"id": eq[2], "question": ["Equipment with overdue maintenance"],
             "sql": [f"SELECT equipment_id, equipment_type, site_name, division, maintenance_due_date, operating_hours, status\n",
                     f"FROM {C}.equipment.equipment_telemetry\n", "WHERE maintenance_due_date < current_date()\n", "ORDER BY maintenance_due_date"]},
            {"id": eq[3], "question": ["Average engine temperature and fuel level by type"],
             "sql": [f"SELECT equipment_type, COUNT(*) AS units, ROUND(AVG(engine_temp_celsius), 1) AS avg_temp_c, ROUND(AVG(fuel_level_pct), 1) AS avg_fuel_pct\n",
                     f"FROM {C}.equipment.equipment_telemetry\n", "GROUP BY equipment_type\n", "ORDER BY avg_temp_c DESC"]},
            {"id": eq[4], "question": ["Equipment with low fuel"],
             "sql": [f"SELECT equipment_id, equipment_type, site_name, fuel_level_pct, status\n",
                     f"FROM {C}.equipment.equipment_telemetry\n", "WHERE fuel_level_pct < 20\n", "ORDER BY fuel_level_pct"]},
            {"id": eq[5], "question": ["Highest operating hours — top 20 most used equipment"],
             "sql": [f"SELECT equipment_id, equipment_type, site_name, division, operating_hours, status\n",
                     f"FROM {C}.equipment.equipment_telemetry\n", "ORDER BY operating_hours DESC\n", "LIMIT 20"]},
        ], key=lambda x: x["id"]),
        "sql_snippets": {},
    },
}

print(f"Creating Equipment Agent...")
equip_id = create_space(
    f"{customer} Equipment Agent",
    f"Heavy equipment fleet monitoring, engine diagnostics, maintenance scheduling, and utilisation analysis for {customer} Group",
    equipment_space,
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Procurement Agent

# COMMAND ----------

sq = gen_ids(8)
ti = gen_ids(1)
eq = gen_ids(6)

procurement_space = {
    "version": 2,
    "config": {
        "sample_questions": [
            {"id": sq[0], "question": ["Which materials have increasing price trends?"]},
            {"id": sq[1], "question": ["Show all suppliers for steel products"]},
            {"id": sq[2], "question": ["What materials have limited availability or are out of stock?"]},
            {"id": sq[3], "question": ["Which categories have the longest lead times?"]},
            {"id": sq[4], "question": ["Compare unit prices across suppliers for the same material"]},
            {"id": sq[5], "question": ["What are the most expensive materials we procure?"]},
            {"id": sq[6], "question": ["Show the supplier breakdown by category"]},
            {"id": sq[7], "question": ["Which materials were last ordered more than 90 days ago?"]},
        ]
    },
    "data_sources": {
        "tables": [
            {
                "identifier": f"{C}.procurement.materials",
                "description": [
                    f"{customer} material procurement catalogue with current supplier pricing, "
                    "lead times, availability status, and order history. Covers 10 categories "
                    "including steel, concrete, fuel, precast elements, geosynthetics, safety equipment, "
                    "site consumables, electrical, aggregate, and timber from 30+ suppliers across Australia."
                ],
                "column_configs": sorted([
                    {"column_name": "material_id", "description": ["Unique material identifier, e.g. MAT-001"]},
                    {"column_name": "material_name", "description": ["Descriptive name of the material, e.g. 'Structural Steel Beam 200UB'"]},
                    {"column_name": "category", "enable_format_assistance": True, "enable_entity_matching": True,
                     "description": ["Material category: Steel, Concrete, Fuel, Precast, Geosynthetics, Safety, Site Consumables, Electrical, Aggregate, Timber"]},
                    {"column_name": "supplier", "enable_format_assistance": True, "enable_entity_matching": True,
                     "description": ["Supplier company name, e.g. Supplier-B, Boral, Hanson, Holcim"]},
                    {"column_name": "unit_price_aud", "description": ["Current unit price in AUD. Compare with historical orders for price movement"]},
                    {"column_name": "unit", "description": ["Unit of measure: tonne, m3, litre, each, m2, lineal_m, kg"]},
                    {"column_name": "lead_time_days", "description": ["Expected days from order placement to delivery. >30 days = long lead, >60 days = critical lead"]},
                    {"column_name": "last_order_date", "description": ["Date of the most recent purchase order"]},
                    {"column_name": "last_order_qty", "description": ["Quantity ordered in the most recent purchase"]},
                    {"column_name": "price_trend", "enable_format_assistance": True, "enable_entity_matching": True,
                     "description": ["Recent price direction: increasing (costs rising), stable (no significant change), decreasing (costs falling)"]},
                    {"column_name": "availability", "enable_format_assistance": True, "enable_entity_matching": True,
                     "description": ["Current market availability: good (readily available), moderate (some constraints), limited (supply chain risk), out_of_stock (unavailable)"]},
                ], key=lambda x: x["column_name"]),
            }
        ]
    },
    "instructions": {
        "text_instructions": [{
            "id": ti[0],
            "content": [
                f"You are the {customer} Procurement Agent — an AI assistant for procurement directors and project supply managers. ",
                f"You analyse {customer}'s material procurement data to identify cost risks, supply chain constraints, and supplier performance. ",
                "Key concepts: ",
                "- Price trend 'increasing' = cost risk that may affect project budgets. ",
                "- Availability 'limited' or 'out_of_stock' = supply chain risk requiring alternative sourcing. ",
                "- Lead time >30 days = long lead item. >60 days = critical lead item requiring forward planning. ",
                "- Always show unit price WITH the unit of measure for meaningful comparisons. ",
                "- When comparing suppliers, group by material or category. ",
                "- Flag materials with BOTH increasing price AND limited availability as high-risk. ",
                "- For cost analysis, calculate total spend as unit_price_aud × last_order_qty. ",
                "- Common construction suppliers: Supplier-B (steel), Supplier-A (concrete/aggregate), Supplier-D (concrete), Supplier-F (concrete), Supplier-I (fuel), Supplier-C (cement)."
            ]
        }],
        "example_question_sqls": sorted([
            {"id": eq[0], "question": ["Materials with increasing prices"],
             "sql": [f"SELECT material_name, category, supplier, unit_price_aud, unit, availability\n",
                     f"FROM {C}.procurement.materials\n", "WHERE price_trend = 'increasing'\n", "ORDER BY unit_price_aud DESC"]},
            {"id": eq[1], "question": ["Supply chain risk — limited or out of stock materials"],
             "sql": [f"SELECT material_name, category, supplier, unit_price_aud, lead_time_days, price_trend, availability\n",
                     f"FROM {C}.procurement.materials\n", "WHERE availability IN ('limited', 'out_of_stock')\n", "ORDER BY availability, lead_time_days DESC"]},
            {"id": eq[2], "question": ["Average price and lead time by category"],
             "sql": [f"SELECT category, COUNT(*) AS materials, ROUND(AVG(unit_price_aud), 2) AS avg_price, ROUND(AVG(lead_time_days), 0) AS avg_lead_days\n",
                     f"FROM {C}.procurement.materials\n", "GROUP BY category\n", "ORDER BY avg_price DESC"]},
            {"id": eq[3], "question": ["All steel suppliers with pricing"],
             "sql": [f"SELECT material_name, supplier, unit_price_aud, unit, lead_time_days, price_trend, availability\n",
                     f"FROM {C}.procurement.materials\n", "WHERE category = 'Steel'\n", "ORDER BY unit_price_aud DESC"]},
            {"id": eq[4], "question": ["Long lead time items over 30 days"],
             "sql": [f"SELECT material_name, category, supplier, lead_time_days, availability, price_trend\n",
                     f"FROM {C}.procurement.materials\n", "WHERE lead_time_days > 30\n", "ORDER BY lead_time_days DESC"]},
            {"id": eq[5], "question": ["Highest spend items by last order value"],
             "sql": [f"SELECT material_name, category, supplier, unit_price_aud, unit, last_order_qty, ROUND(unit_price_aud * last_order_qty, 2) AS estimated_spend_aud\n",
                     f"FROM {C}.procurement.materials\n", "ORDER BY estimated_spend_aud DESC\n", "LIMIT 20"]},
        ], key=lambda x: x["id"]),
        "sql_snippets": {},
    },
}

print(f"Creating Procurement Agent...")
proc_id = create_space(
    f"{customer} Procurement Agent",
    f"Material pricing analysis, supplier performance, lead time monitoring, and supply chain risk assessment for {customer} Group",
    procurement_space,
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Projects Agent

# COMMAND ----------

sq = gen_ids(8)
ti = gen_ids(1)
eq = gen_ids(8)

finance_space = {
    "version": 2,
    "config": {
        "sample_questions": [
            {"id": sq[0], "question": ["Which projects are in red status and why?"]},
            {"id": sq[1], "question": ["What is our total portfolio budget vs actual spend?"]},
            {"id": sq[2], "question": ["Compare SPI and CPI across all divisions"]},
            {"id": sq[3], "question": ["Show the top 5 largest projects by budget"]},
            {"id": sq[4], "question": ["Which project managers have the best CPI?"]},
            {"id": sq[5], "question": ["What is the total cost overrun across the portfolio?"]},
            {"id": sq[6], "question": ["Show all projects completing in the next 12 months"]},
            {"id": sq[7], "question": ["Rank divisions by average schedule performance"]},
        ]
    },
    "data_sources": {
        "tables": [
            {
                "identifier": f"{C}.projects.financials",
                "description": [
                    f"{customer} project portfolio financial data with Earned Value Management (EVM) metrics. "
                    "Each row is a project with budget, actual costs, earned value, planned value, "
                    "SPI (schedule performance), CPI (cost performance), RAG status, and project manager. "
                    f"Covers all {customer} divisions: Division-Alpha (infrastructure), Division-Beta (mining), "
                    "Division-Gamma (mineral processing), Division-Delta (PPPs)."
                ],
                "column_configs": sorted([
                    {"column_name": "project_id", "description": ["Unique project code, e.g. P-2024-001"]},
                    {"column_name": "project_name", "description": ["Full project name, e.g. 'Sydney Metro West - Station Fit-Out'"]},
                    {"column_name": "division", "enable_format_assistance": True, "enable_entity_matching": True,
                     "description": ["Operating division: Division-Alpha, Division-Beta, Division-Gamma, Division-Delta"]},
                    {"column_name": "client", "enable_format_assistance": True, "enable_entity_matching": True,
                     "description": ["Client organisation that commissioned the project"]},
                    {"column_name": "project_type", "enable_format_assistance": True, "enable_entity_matching": True,
                     "description": ["Category: Rail Infrastructure, Road Infrastructure, Road/Tunnel, Contract Services, Mineral Processing, Water Infrastructure"]},
                    {"column_name": "state", "enable_format_assistance": True, "enable_entity_matching": True,
                     "description": ["Australian state: NSW, QLD, VIC, WA, SA, NT, TAS, ACT"]},
                    {"column_name": "budget_aud", "description": ["Approved total project budget in AUD. For large projects this is in billions"]},
                    {"column_name": "actual_cost_aud", "description": ["Cumulative actual costs incurred to date in AUD"]},
                    {"column_name": "earned_value_aud", "description": ["Earned Value (EV) — budgeted cost of work actually completed, in AUD"]},
                    {"column_name": "planned_value_aud", "description": ["Planned Value (PV) — budgeted cost of work scheduled to be completed by now, in AUD"]},
                    {"column_name": "cost_variance_pct", "description": ["Cost Variance % = (EV - AC) / EV × 100. Negative = over budget"]},
                    {"column_name": "spi", "description": ["Schedule Performance Index = EV / PV. 1.0 = on schedule, <1.0 = behind, >1.0 = ahead"]},
                    {"column_name": "cpi", "description": ["Cost Performance Index = EV / AC. 1.0 = on budget, <1.0 = over budget, >1.0 = under budget"]},
                    {"column_name": "status", "enable_format_assistance": True, "enable_entity_matching": True,
                     "description": ["RAG status: green (on track), amber (minor concerns), red (at risk / over budget / behind schedule)"]},
                    {"column_name": "start_date", "description": ["Project commencement date"]},
                    {"column_name": "planned_completion", "description": ["Contractual target completion date"]},
                    {"column_name": "reporting_period", "description": ["Financial reporting period end date (typically end of quarter)"]},
                    {"column_name": "project_manager", "description": ["Name of the project manager responsible"]},
                ], key=lambda x: x["column_name"]),
            }
        ]
    },
    "instructions": {
        "text_instructions": [{
            "id": ti[0],
            "content": [
                f"You are the {customer} Projects Agent — an AI assistant for CFOs, project controls managers, and executive leadership. ",
                f"You analyse {customer}'s project portfolio using Earned Value Management (EVM) to assess cost and schedule performance. ",
                "Key EVM formulas and concepts: ",
                "- SPI (Schedule Performance Index) = EV / PV. Below 1.0 = behind schedule. ",
                "- CPI (Cost Performance Index) = EV / AC. Below 1.0 = over budget. ",
                "- CV% (Cost Variance %) = (EV - AC) / EV × 100. Negative = overspend. ",
                "- EAC (Estimate at Completion) = Budget / CPI. Useful for forecasting final cost. ",
                "- RAG: Red = SPI < 0.95 or CPI < 0.95 or CV% < -5%. Amber = minor variance. Green = on track. ",
                "Format monetary values with $ prefix and commas. For billions use $X.XXB format. ",
                "When showing portfolio summaries, always include: total budget, total actuals, overall SPI, overall CPI. ",
                "When comparing divisions, include project count for context (a division with 2 projects vs 20 is not comparable). ",
                "Always flag red-status projects with their cost variance prominently. ",
                f"Divisions: Division-Alpha (major infrastructure — roads, rail, tunnels), Division-Beta (contract mining services), Division-Gamma (mineral processing plants), Division-Delta (PPP concessions)."
            ]
        }],
        "example_question_sqls": sorted([
            {"id": eq[0], "question": ["All red-status projects with financials"],
             "sql": [f"SELECT project_name, division, budget_aud, actual_cost_aud, cost_variance_pct, spi, cpi, project_manager\n",
                     f"FROM {C}.projects.financials\n", "WHERE status = 'red'\n", "ORDER BY cost_variance_pct ASC"]},
            {"id": eq[1], "question": ["Portfolio summary by division"],
             "sql": [f"SELECT division, COUNT(*) AS projects, ROUND(SUM(budget_aud)/1e9, 2) AS budget_b, ROUND(SUM(actual_cost_aud)/1e9, 2) AS actuals_b, ROUND(AVG(spi), 3) AS avg_spi, ROUND(AVG(cpi), 3) AS avg_cpi\n",
                     f"FROM {C}.projects.financials\n", "GROUP BY division\n", "ORDER BY budget_b DESC"]},
            {"id": eq[2], "question": ["Total portfolio budget vs actuals"],
             "sql": [f"SELECT COUNT(*) AS total_projects, ROUND(SUM(budget_aud)/1e9, 2) AS total_budget_b, ROUND(SUM(actual_cost_aud)/1e9, 2) AS total_actuals_b, ROUND(SUM(actual_cost_aud - budget_aud)/1e6, 1) AS variance_m, ROUND(AVG(spi), 3) AS avg_spi, ROUND(AVG(cpi), 3) AS avg_cpi\n",
                     f"FROM {C}.projects.financials"]},
            {"id": eq[3], "question": ["Top 10 largest projects by budget"],
             "sql": [f"SELECT project_name, division, client, budget_aud, actual_cost_aud, status, spi, cpi\n",
                     f"FROM {C}.projects.financials\n", "ORDER BY budget_aud DESC\n", "LIMIT 10"]},
            {"id": eq[4], "question": ["Projects behind schedule (SPI below 1.0)"],
             "sql": [f"SELECT project_name, division, spi, cpi, status, planned_completion\n",
                     f"FROM {C}.projects.financials\n", "WHERE spi < 1.0\n", "ORDER BY spi ASC"]},
            {"id": eq[5], "question": ["Project manager performance"],
             "sql": [f"SELECT project_manager, COUNT(*) AS projects, ROUND(AVG(cpi), 3) AS avg_cpi, ROUND(AVG(spi), 3) AS avg_spi, SUM(CASE WHEN status = 'red' THEN 1 ELSE 0 END) AS red_projects\n",
                     f"FROM {C}.projects.financials\n", "GROUP BY project_manager\n", "ORDER BY avg_cpi DESC"]},
            {"id": eq[6], "question": ["Cost overrun by state"],
             "sql": [f"SELECT state, COUNT(*) AS projects, ROUND(SUM(budget_aud)/1e9, 2) AS budget_b, ROUND(SUM(actual_cost_aud - budget_aud)/1e6, 1) AS overrun_m\n",
                     f"FROM {C}.projects.financials\n", "GROUP BY state\n", "ORDER BY overrun_m DESC"]},
            {"id": eq[7], "question": ["Estimate at Completion for red projects"],
             "sql": [f"SELECT project_name, division, budget_aud, actual_cost_aud, cpi, ROUND(budget_aud / cpi, 0) AS eac_aud, ROUND((budget_aud / cpi) - budget_aud, 0) AS forecast_overrun_aud\n",
                     f"FROM {C}.projects.financials\n", "WHERE status = 'red'\n", "ORDER BY forecast_overrun_aud DESC"]},
        ], key=lambda x: x["id"]),
        "sql_snippets": {},
    },
}

print(f"Creating Projects Agent...")
finance_id = create_space(
    f"{customer} Projects Agent",
    f"EVM-powered project portfolio analysis — budget tracking, SPI/CPI metrics, cost forecasting, and division benchmarking for {customer} Group",
    finance_space,
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

results = {
    "intelligence": intelligence_id,
    "safety": safety_id,
    "equipment": equip_id,
    "procurement": proc_id,
    "projects": finance_id,
}

print("\n" + "=" * 60)
print(f" {customer} Domain Genie Spaces — Summary")
print("=" * 60)
for domain, sid in results.items():
    status = "✅" if sid else "❌"
    url = f"https://{host}/genie/rooms/{sid}" if sid else "FAILED"
    print(f"  {status} {domain:15s} → {url}")
print("=" * 60)

# Store IDs
try:
    for domain, sid in results.items():
        if sid:
            dbutils.jobs.taskValues.set(key=f"genie_{domain}_id", value=sid)
except Exception:
    pass
