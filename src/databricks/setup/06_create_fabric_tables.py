# Databricks notebook source
# MAGIC %md
# MAGIC # Module 03 -- Fabric Mirror Tables (`_f` suffix)
# MAGIC
# MAGIC Creates duplicate tables **without RLS** for Fabric mirroring.
# MAGIC
# MAGIC Unity Catalog row filters prevent Fabric from mirroring the source tables
# MAGIC (Delta metadata with row filter causes sync failures). These `_f` tables
# MAGIC are identical copies — same schema, same data, same storage type — but
# MAGIC **no row filters, no column masks**. Fabric mirrors these instead.
# MAGIC
# MAGIC | Source Table | Fabric Table | Storage |
# MAGIC |---|---|---|
# MAGIC | `projects.financials` | `projects.financials_f` | Managed Delta |
# MAGIC | `equipment.equipment_telemetry` | `equipment.equipment_telemetry_f` | External Delta |
# MAGIC | `safety.incidents` | `safety.incidents_f` | Managed Delta |
# MAGIC
# MAGIC `procurement.materials` has no RLS — mirror it directly (no `_f` needed).
# MAGIC
# MAGIC **Run after:** `generate_data` (needs data to copy) and `configure_rls` (source tables exist).

# COMMAND ----------

dbutils.widgets.text("catalog_name", "contoso", "Catalog Name")
dbutils.widgets.text("customer_name", "Contoso", "Customer Display Name")
dbutils.widgets.text("external_storage_path", "", "External ADLS Path (optional)")

catalog = dbutils.widgets.get("catalog_name")
customer = dbutils.widgets.get("customer_name")
ext_path = dbutils.widgets.get("external_storage_path").rstrip("/")

print(f"Catalog: {catalog}")
print(f"Customer: {customer}")
print(f"External storage: {ext_path or '(none -- will use managed)'}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. projects.financials_f (Managed Delta)

# COMMAND ----------

spark.sql(f"DROP TABLE IF EXISTS {catalog}.projects.financials_f")

spark.sql(f"""
CREATE TABLE {catalog}.projects.financials_f (
    project_id STRING COMMENT 'Unique project identifier, e.g. P-2024-001',
    project_name STRING COMMENT 'Descriptive project name',
    division STRING COMMENT 'Operating division: Division-Alpha, Division-Beta, Division-Gamma, Division-Delta',
    client STRING COMMENT 'Client organisation commissioning the project',
    project_type STRING COMMENT 'Category: Rail Infrastructure, Road/Tunnel, Contract Services, Mineral Processing, Water Infrastructure, Road Infrastructure',
    state STRING COMMENT 'Australian state: NSW, QLD, VIC, WA, SA',
    budget_aud DOUBLE COMMENT 'Approved budget in AUD',
    actual_cost_aud DOUBLE COMMENT 'Costs incurred to date in AUD',
    earned_value_aud DOUBLE COMMENT 'Value of work completed (EVM)',
    planned_value_aud DOUBLE COMMENT 'Value of work planned to date (EVM)',
    cost_variance_pct DOUBLE COMMENT 'Cost variance as percentage: (EV - AC) / EV * 100',
    spi DOUBLE COMMENT 'Schedule Performance Index: EV / PV. Below 1.0 = behind schedule',
    cpi DOUBLE COMMENT 'Cost Performance Index: EV / AC. Below 1.0 = over budget',
    status STRING COMMENT 'RAG status: green, amber, red',
    start_date DATE COMMENT 'Project start date',
    planned_completion DATE COMMENT 'Planned completion date',
    reporting_period DATE COMMENT 'Reporting period end date for this snapshot',
    project_manager STRING COMMENT 'Name of the project manager'
)
COMMENT '{customer} project financials — Fabric mirror copy (no RLS)'
TBLPROPERTIES ('quality' = 'gold', 'fabric_mirror' = 'true')
""")

spark.sql(f"""
INSERT INTO {catalog}.projects.financials_f
SELECT * FROM {catalog}.projects.financials
""")

count = spark.sql(f"SELECT COUNT(*) AS n FROM {catalog}.projects.financials_f").collect()[0].n
print(f"[OK] {catalog}.projects.financials_f (Managed Delta) — {count} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. equipment.equipment_telemetry_f (External Delta)

# COMMAND ----------

location_clause = ""
if ext_path:
    location_clause = f"LOCATION '{ext_path}/equipment_telemetry_f'"
    spark.sql(f"DROP TABLE IF EXISTS {catalog}.equipment.equipment_telemetry_f")
else:
    spark.sql(f"DROP TABLE IF EXISTS {catalog}.equipment.equipment_telemetry_f")

spark.sql(f"""
CREATE TABLE {catalog}.equipment.equipment_telemetry_f (
    equipment_id STRING COMMENT 'Unique equipment identifier, e.g. HT-001 (haul truck), EX-005 (excavator)',
    equipment_type STRING COMMENT 'Type: haul_truck, excavator, drill, loader, dozer, grader, water_cart',
    site_name STRING COMMENT 'Construction or mining site where equipment is deployed',
    division STRING COMMENT 'Operating division owning this equipment',
    engine_temp_celsius DOUBLE COMMENT 'Engine temperature. Normal: 70-95, Warning: 95-110, Critical: >110',
    fuel_level_pct DOUBLE COMMENT 'Fuel tank level as percentage (0-100)',
    operating_hours INT COMMENT 'Cumulative engine operating hours',
    maintenance_due_date DATE COMMENT 'Next scheduled maintenance date',
    status STRING COMMENT 'Current status: operational, warning, critical, maintenance',
    reading_timestamp TIMESTAMP COMMENT 'Timestamp of this telemetry reading'
)
COMMENT '{customer} equipment telemetry — Fabric mirror copy (no RLS)'
{location_clause}
TBLPROPERTIES ('quality' = 'gold', 'fabric_mirror' = 'true')
""")

spark.sql(f"""
INSERT INTO {catalog}.equipment.equipment_telemetry_f
SELECT * FROM {catalog}.equipment.equipment_telemetry
""")

count = spark.sql(f"SELECT COUNT(*) AS n FROM {catalog}.equipment.equipment_telemetry_f").collect()[0].n
print(f"[OK] {catalog}.equipment.equipment_telemetry_f {'(External Delta)' if ext_path else '(Managed Delta)'} — {count} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. safety.incidents_f (Managed Delta)

# COMMAND ----------

spark.sql(f"DROP TABLE IF EXISTS {catalog}.safety.incidents_f")

spark.sql(f"""
CREATE TABLE {catalog}.safety.incidents_f (
    incident_id STRING COMMENT 'Unique incident identifier, e.g. INC-2025-001',
    incident_date DATE COMMENT 'Date of occurrence',
    site_name STRING COMMENT 'Construction or mining site where incident occurred',
    division STRING COMMENT 'Operating division',
    incident_type STRING COMMENT 'Category: Slip/Trip/Fall, Vehicle Interaction, Equipment Failure, Falling Object, Chemical Exposure, Heat Stress, Noise Exposure, Confined Space, Electrical, Struck By',
    severity STRING COMMENT 'Severity level: Minor, Moderate, Serious, Critical',
    description STRING COMMENT 'Free-text description of the incident',
    injuries INT COMMENT 'Number of people injured (0 for near-misses)',
    lost_time_days DOUBLE COMMENT 'Lost Time Injury (LTI) days. 0 if no time lost',
    root_cause STRING COMMENT 'Root cause category: human_error, equipment_failure, procedural, environmental, design, poor_housekeeping, inadequate_training',
    corrective_action STRING COMMENT 'Corrective action taken to prevent recurrence',
    status STRING COMMENT 'Investigation status: open, investigating, closed'
)
COMMENT '{customer} safety incidents — Fabric mirror copy (no RLS)'
TBLPROPERTIES ('quality' = 'gold', 'fabric_mirror' = 'true')
""")

spark.sql(f"""
INSERT INTO {catalog}.safety.incidents_f
SELECT * FROM {catalog}.safety.incidents
""")

count = spark.sql(f"SELECT COUNT(*) AS n FROM {catalog}.safety.incidents_f").collect()[0].n
print(f"[OK] {catalog}.safety.incidents_f (Managed Delta) — {count} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("Fabric mirror tables created (no RLS):\n")
for tbl in ["projects.financials_f", "equipment.equipment_telemetry_f", "safety.incidents_f"]:
    count = spark.sql(f"SELECT COUNT(*) AS n FROM {catalog}.{tbl}").collect()[0].n
    print(f"  {catalog}.{tbl} — {count} rows")

print(f"\n  {catalog}.procurement.materials — mirror directly (no RLS on source)")
print("\nFabric should mirror these _f tables + procurement.materials.")
