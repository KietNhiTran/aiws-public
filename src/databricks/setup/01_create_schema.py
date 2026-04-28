# Databricks notebook source
# MAGIC %md
# MAGIC # Module 03 -- Create Schema
# MAGIC
# MAGIC Creates the 4 core tables matching Module 03's exact column schemas.
# MAGIC All names are parameterised via `customer_name` so this can be reused
# MAGIC for a different customer by changing one variable.
# MAGIC
# MAGIC **Storage mix:**
# MAGIC - `projects.financials` -- Managed Delta
# MAGIC - `equipment.equipment_telemetry` -- External Delta on ADLS
# MAGIC - `safety.incidents` -- Managed Delta
# MAGIC - `procurement.materials` -- Iceberg UniForm

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
# MAGIC ## 1. Schemas

# COMMAND ----------

spark.sql(f"USE CATALOG {catalog}")

schemas = {
    "projects": f"{customer} project financials, budgets, milestones, and EVM metrics",
    "equipment": f"{customer} heavy equipment fleet telemetry and maintenance records",
    "safety": f"{customer} workplace health and safety incident records",
    "procurement": f"{customer} material procurement, supplier pricing, and availability",
    "security": f"{customer} row-level security functions and access control",
}

for schema_name, comment in schemas.items():
    spark.sql(f"""
        CREATE SCHEMA IF NOT EXISTS {catalog}.{schema_name}
        COMMENT '{comment}'
    """)
    print(f"[OK] Schema: {catalog}.{schema_name}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Projects -- financials (Managed Delta)

# COMMAND ----------

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {catalog}.projects.financials (
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
COMMENT '{customer} project financials with Earned Value Management (EVM) metrics across all divisions'
TBLPROPERTIES ('quality' = 'gold')
""")
print(f"[OK] {catalog}.projects.financials (Managed Delta)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Equipment -- equipment_telemetry (External Delta on ADLS)

# COMMAND ----------

location_clause = ""
if ext_path:
    location_clause = f"LOCATION '{ext_path}/equipment_telemetry'"
    # Drop existing managed table so it can be recreated as external
    spark.sql(f"DROP TABLE IF EXISTS {catalog}.equipment.equipment_telemetry")

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {catalog}.equipment.equipment_telemetry (
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
COMMENT '{customer} heavy equipment fleet IoT telemetry data'
{location_clause}
TBLPROPERTIES ('quality' = 'gold')
""")
print(f"[OK] {catalog}.equipment.equipment_telemetry {'(External Delta)' if ext_path else '(Managed Delta)'}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Safety -- incidents (Managed Delta)

# COMMAND ----------

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {catalog}.safety.incidents (
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
COMMENT '{customer} workplace health and safety incident records across all divisions and sites'
TBLPROPERTIES ('quality' = 'gold')
""")
print(f"[OK] {catalog}.safety.incidents (Managed Delta)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Procurement -- materials (Iceberg UniForm)

# COMMAND ----------

iceberg_location = ""
if ext_path:
    iceberg_location = f"LOCATION '{ext_path}/materials'"
    # Drop existing table metadata (external files persist but will be overwritten by data gen)
    spark.sql(f"DROP TABLE IF EXISTS {catalog}.procurement.materials")

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {catalog}.procurement.materials (
    material_id STRING COMMENT 'Unique material identifier, e.g. MAT-001',
    material_name STRING COMMENT 'Material description, e.g. Structural Steel (Grade 350)',
    category STRING COMMENT 'Material category: Steel, Concrete, Fuel, Precast, Geosynthetics, Safety, Site Consumables, Electrical, Aggregate, Timber',
    supplier STRING COMMENT 'Primary supplier name',
    unit_price_aud DOUBLE COMMENT 'Price per unit in AUD',
    unit STRING COMMENT 'Unit of measure: tonne, cubic_meter, litre, square_meter, segment, set, unit, each',
    lead_time_days INT COMMENT 'Days from order to delivery',
    last_order_date DATE COMMENT 'Date of most recent order',
    last_order_qty DOUBLE COMMENT 'Quantity of most recent order',
    price_trend STRING COMMENT 'Price direction: increasing, stable, decreasing',
    availability STRING COMMENT 'Supply availability: good, moderate, limited, out_of_stock'
)
COMMENT '{customer} material procurement records with supplier pricing, lead times, and market availability'
{iceberg_location}
TBLPROPERTIES (
    'quality' = 'gold',
    'delta.columnMapping.mode' = 'name',
    'delta.enableIcebergCompatV2' = 'true',
    'delta.universalFormat.enabledFormats' = 'iceberg'
)
""")
print(f"[OK] {catalog}.procurement.materials (Iceberg UniForm)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

for schema_name in ["projects", "equipment", "safety", "procurement"]:
    tables = spark.sql(f"SHOW TABLES IN {catalog}.{schema_name}").collect()
    for t in tables:
        print(f"  {catalog}.{schema_name}.{t.tableName}")

print("\nSchema creation complete.")
