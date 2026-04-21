# Databricks notebook source
# MAGIC %md
# MAGIC # Supply Chain  -  Gold Layer (Analytics-Ready)
# MAGIC
# MAGIC Creates analytics-ready **gold tables, views, and materialized views** from silver.
# MAGIC
# MAGIC | Gold Object | Type | Description |
# MAGIC |-------------|------|-------------|
# MAGIC | `gold.fleet_utilisation_daily` | **Materialized View** | Daily fleet metrics per vehicle |
# MAGIC | `gold.delivery_performance` | **Materialized View** | Supplier delivery KPIs |
# MAGIC | `gold.inventory_health` | **Table** | Latest stock health per warehouse/material |
# MAGIC | `gold.invoice_aging` | **View** | Invoice aging buckets (always current) |
# MAGIC | `gold.site_operations_summary` | **View** | Cross-domain site-level dashboard |
# MAGIC | `gold.supplier_scorecard` | **Table** | Supplier performance scoring |

# COMMAND ----------

dbutils.widgets.text("catalog_name", "adb_cimic_aiws_dev_ws", "Catalog Name")
catalog = dbutils.widgets.get("catalog_name")

# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.supply_chain_gold COMMENT 'Analytics-ready aggregations and KPIs'")
print(f"[OK] Schema: {catalog}.supply_chain_gold")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold 1: Fleet Utilisation (Materialized View)
# MAGIC
# MAGIC Materialized views auto-refresh and are incrementally maintained by Databricks.

# COMMAND ----------

try:
    spark.sql(f"DROP MATERIALIZED VIEW IF EXISTS {catalog}.supply_chain_gold.fleet_utilisation_daily")
    spark.sql(f"""
    CREATE MATERIALIZED VIEW {catalog}.supply_chain_gold.fleet_utilisation_daily
    COMMENT 'Daily fleet utilisation metrics per vehicle and site  -  auto-refreshed from silver. Supports fleet management dashboards.'
    AS
    SELECT
        DATE(ping_timestamp) AS report_date,
        vehicle_id,
        vehicle_type,
        site_name,
        COUNT(*) AS total_pings,
        SUM(CASE WHEN is_moving THEN 1 ELSE 0 END) AS moving_pings,
        SUM(CASE WHEN is_idling THEN 1 ELSE 0 END) AS idling_pings,
        SUM(CASE WHEN NOT engine_on THEN 1 ELSE 0 END) AS off_pings,
        ROUND(AVG(speed_kmh), 1) AS avg_speed_kmh,
        ROUND(MAX(speed_kmh), 1) AS max_speed_kmh,
        ROUND(AVG(fuel_level_pct), 1) AS avg_fuel_pct,
        ROUND(MIN(fuel_level_pct), 1) AS min_fuel_pct,
        ROUND(SUM(CASE WHEN is_moving THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS utilisation_pct,
        ROUND(SUM(CASE WHEN is_idling THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS idle_pct
    FROM {catalog}.supply_chain_silver.fleet_positions
    GROUP BY DATE(ping_timestamp), vehicle_id, vehicle_type, site_name
    """)
    print("[OK] Materialized View: fleet_utilisation_daily")
except Exception as e:
    err_msg = str(e)
    if "MATERIALIZED_VIEW_OPERATION_NOT_ALLOWED" in err_msg:
        print("[SKIP] fleet_utilisation_daily  -  requires SQL Warehouse (Serverless or Pro)")
    else:
        print(f"[ERROR] fleet_utilisation_daily: {err_msg[:200]}")

# Always create a regular view equivalent
spark.sql(f"""
CREATE OR REPLACE VIEW {catalog}.supply_chain_gold.v_fleet_utilisation_daily
COMMENT 'Daily fleet utilisation metrics per vehicle and site  -  live query from silver layer. Use this view on any compute; use the materialized view (mv) for cached performance.'
AS
SELECT
    DATE(ping_timestamp) AS report_date,
    vehicle_id,
    vehicle_type,
    site_name,
    COUNT(*) AS total_pings,
    SUM(CASE WHEN is_moving THEN 1 ELSE 0 END) AS moving_pings,
    SUM(CASE WHEN is_idling THEN 1 ELSE 0 END) AS idling_pings,
    SUM(CASE WHEN NOT engine_on THEN 1 ELSE 0 END) AS off_pings,
    ROUND(AVG(speed_kmh), 1) AS avg_speed_kmh,
    ROUND(MAX(speed_kmh), 1) AS max_speed_kmh,
    ROUND(AVG(fuel_level_pct), 1) AS avg_fuel_pct,
    ROUND(MIN(fuel_level_pct), 1) AS min_fuel_pct,
    ROUND(SUM(CASE WHEN is_moving THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS utilisation_pct,
    ROUND(SUM(CASE WHEN is_idling THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS idle_pct
FROM {catalog}.supply_chain_silver.fleet_positions
GROUP BY DATE(ping_timestamp), vehicle_id, vehicle_type, site_name
""")
print("[OK] View: v_fleet_utilisation_daily")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold 2: Delivery Performance (Materialized View)

# COMMAND ----------

try:
    spark.sql(f"DROP MATERIALIZED VIEW IF EXISTS {catalog}.supply_chain_gold.delivery_performance")
    spark.sql(f"""
    CREATE MATERIALIZED VIEW {catalog}.supply_chain_gold.delivery_performance
    COMMENT 'Supplier delivery performance KPIs by destination site  -  auto-refreshed from silver. Damage rates, cost discrepancies, and material diversity.'
    AS
    SELECT
        supplier,
        destination_site,
        COUNT(*) AS total_deliveries,
        SUM(total_cost) AS total_spend_aud,
        ROUND(AVG(total_cost), 2) AS avg_delivery_cost_aud,
        SUM(CASE WHEN is_damaged THEN 1 ELSE 0 END) AS damaged_deliveries,
        ROUND(SUM(CASE WHEN is_damaged THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS damage_rate_pct,
        SUM(CASE WHEN NOT cost_validated THEN 1 ELSE 0 END) AS cost_discrepancies,
        COUNT(DISTINCT material) AS unique_materials,
        COUNT(DISTINCT po_number) AS unique_pos
    FROM {catalog}.supply_chain_silver.deliveries
    GROUP BY supplier, destination_site
    """)
    print("[OK] Materialized View: delivery_performance")
except Exception as e:
    err_msg = str(e)
    if "MATERIALIZED_VIEW_OPERATION_NOT_ALLOWED" in err_msg:
        print("[SKIP] delivery_performance  -  requires SQL Warehouse (Serverless or Pro)")
    else:
        print(f"[ERROR] delivery_performance: {err_msg[:200]}")

# Always create a regular view equivalent
spark.sql(f"""
CREATE OR REPLACE VIEW {catalog}.supply_chain_gold.v_delivery_performance
COMMENT 'Supplier delivery performance KPIs by destination site  -  live query from silver. Damage rates, cost discrepancies, and material diversity.'
AS
SELECT
    supplier,
    destination_site,
    COUNT(*) AS total_deliveries,
    SUM(total_cost) AS total_spend_aud,
    ROUND(AVG(total_cost), 2) AS avg_delivery_cost_aud,
    SUM(CASE WHEN is_damaged THEN 1 ELSE 0 END) AS damaged_deliveries,
    ROUND(SUM(CASE WHEN is_damaged THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS damage_rate_pct,
    SUM(CASE WHEN NOT cost_validated THEN 1 ELSE 0 END) AS cost_discrepancies,
    COUNT(DISTINCT material) AS unique_materials,
    COUNT(DISTINCT po_number) AS unique_pos
FROM {catalog}.supply_chain_silver.deliveries
GROUP BY supplier, destination_site
""")
print("[OK] View: v_delivery_performance")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold 3: Inventory Health (Table  -  snapshot)

# COMMAND ----------

from pyspark.sql.functions import col, current_timestamp, row_number
from pyspark.sql.window import Window

inv = spark.table(f"{catalog}.supply_chain_silver.inventory_snapshots")

# Latest snapshot per warehouse + material
w = Window.partitionBy("warehouse_id", "material").orderBy(col("snapshot_timestamp").desc())
latest_inv = (inv
    .withColumn("_rn", row_number().over(w))
    .filter("_rn = 1").drop("_rn")
    .withColumn("_gold_processed_at", current_timestamp())
)

(latest_inv.write
    .mode("overwrite")
    .option("overwriteSchema", True)
    .saveAsTable(f"{catalog}.supply_chain_gold.inventory_health"))
print(f"[OK] Table: inventory_health ({latest_inv.count()} rows)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold 4: Invoice Aging (View  -  always live)
# MAGIC
# MAGIC Regular views are always current  -  no refresh needed.

# COMMAND ----------

spark.sql(f"DROP VIEW IF EXISTS {catalog}.supply_chain_gold.invoice_aging")

spark.sql(f"""
CREATE VIEW {catalog}.supply_chain_gold.invoice_aging
COMMENT 'Live invoice aging analysis with payment risk buckets'
AS
SELECT
    invoice_id,
    supplier,
    site,
    invoice_date,
    due_date,
    total_aud,
    payment_status,
    days_until_due,
    is_overdue,
    CASE
        WHEN payment_status IN ('paid', 'approved') THEN 'settled'
        WHEN days_until_due > 30 THEN 'not_yet_due'
        WHEN days_until_due BETWEEN 15 AND 30 THEN 'due_soon'
        WHEN days_until_due BETWEEN 0 AND 14 THEN 'due_imminent'
        WHEN days_until_due BETWEEN -30 AND -1 THEN 'overdue_30'
        WHEN days_until_due BETWEEN -60 AND -31 THEN 'overdue_60'
        ELSE 'overdue_90_plus'
    END AS aging_bucket,
    CASE
        WHEN payment_status = 'disputed' THEN 'high'
        WHEN is_overdue AND days_until_due < -30 THEN 'high'
        WHEN is_overdue THEN 'medium'
        WHEN days_until_due < 7 THEN 'medium'
        ELSE 'low'
    END AS payment_risk
FROM {catalog}.supply_chain_silver.invoices
""")
print("[OK] View: invoice_aging")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold 5: Site Operations Summary (View  -  cross-domain)

# COMMAND ----------

spark.sql(f"DROP VIEW IF EXISTS {catalog}.supply_chain_gold.site_operations_summary")

spark.sql(f"""
CREATE VIEW {catalog}.supply_chain_gold.site_operations_summary
COMMENT 'Cross-domain site-level operations dashboard  -  combines fleet, deliveries, invoices'
AS
WITH fleet AS (
    SELECT
        site_name AS site,
        COUNT(DISTINCT vehicle_id) AS active_vehicles,
        ROUND(AVG(CASE WHEN is_moving THEN 1.0 ELSE 0.0 END) * 100, 1) AS fleet_utilisation_pct,
        ROUND(AVG(fuel_level_pct), 1) AS avg_fuel_level
    FROM {catalog}.supply_chain_silver.fleet_positions
    GROUP BY site_name
),
deliveries AS (
    SELECT
        destination_site AS site,
        COUNT(*) AS total_deliveries,
        SUM(total_cost) AS delivery_spend_aud,
        SUM(CASE WHEN is_damaged THEN 1 ELSE 0 END) AS damaged_count,
        COUNT(DISTINCT supplier) AS active_suppliers
    FROM {catalog}.supply_chain_silver.deliveries
    GROUP BY destination_site
),
invoices AS (
    SELECT
        site,
        SUM(total_aud) AS total_invoiced_aud,
        SUM(CASE WHEN is_overdue THEN total_aud ELSE 0 END) AS overdue_amount_aud,
        COUNT(CASE WHEN payment_status = 'disputed' THEN 1 END) AS disputed_invoices
    FROM {catalog}.supply_chain_silver.invoices
    GROUP BY site
)
SELECT
    COALESCE(f.site, d.site, i.site) AS site_name,
    f.active_vehicles,
    f.fleet_utilisation_pct,
    f.avg_fuel_level,
    d.total_deliveries,
    d.delivery_spend_aud,
    d.damaged_count,
    d.active_suppliers,
    i.total_invoiced_aud,
    i.overdue_amount_aud,
    i.disputed_invoices
FROM fleet f
FULL OUTER JOIN deliveries d ON f.site = d.site
FULL OUTER JOIN invoices i ON COALESCE(f.site, d.site) = i.site
""")
print("[OK] View: site_operations_summary")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold 6: Supplier Scorecard (Table  -  composite scoring)

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE TABLE {catalog}.supply_chain_gold.supplier_scorecard
COMMENT 'Composite supplier scoring combining delivery quality, cost, and payment metrics'
AS
WITH del_stats AS (
    SELECT
        supplier,
        COUNT(*) AS deliveries,
        SUM(total_cost) AS total_spend,
        ROUND(SUM(CASE WHEN is_damaged THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS damage_rate,
        ROUND(SUM(CASE WHEN NOT cost_validated THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS discrepancy_rate,
        COUNT(DISTINCT destination_site) AS sites_served
    FROM {catalog}.supply_chain_silver.deliveries
    GROUP BY supplier
),
inv_stats AS (
    SELECT
        supplier,
        COUNT(*) AS invoices,
        SUM(total_aud) AS invoiced_total,
        SUM(CASE WHEN payment_status = 'disputed' THEN 1 ELSE 0 END) AS disputes,
        ROUND(AVG(CASE WHEN is_overdue THEN 1.0 ELSE 0.0 END) * 100, 1) AS overdue_pct
    FROM {catalog}.supply_chain_silver.invoices
    GROUP BY supplier
)
SELECT
    COALESCE(d.supplier, i.supplier) AS supplier,
    d.deliveries,
    d.total_spend AS delivery_spend_aud,
    d.damage_rate AS delivery_damage_rate_pct,
    d.discrepancy_rate AS cost_discrepancy_rate_pct,
    d.sites_served,
    i.invoices,
    i.invoiced_total AS invoiced_aud,
    i.disputes AS disputed_invoices,
    i.overdue_pct AS invoice_overdue_pct,
    -- Composite score: 100 = perfect, penalise for damage/disputes/overdue
    ROUND(100
        - COALESCE(d.damage_rate, 0) * 2          -- -2 pts per % damaged
        - COALESCE(d.discrepancy_rate, 0) * 1.5    -- -1.5 pts per % discrepancy
        - COALESCE(i.overdue_pct, 0) * 1           -- -1 pt per % overdue
        - COALESCE(i.disputes, 0) * 5              -- -5 pts per dispute
    , 1) AS supplier_score,
    CASE
        WHEN (100 - COALESCE(d.damage_rate, 0)*2 - COALESCE(d.discrepancy_rate, 0)*1.5
              - COALESCE(i.overdue_pct, 0)*1 - COALESCE(i.disputes, 0)*5) >= 90 THEN 'A - Preferred'
        WHEN (100 - COALESCE(d.damage_rate, 0)*2 - COALESCE(d.discrepancy_rate, 0)*1.5
              - COALESCE(i.overdue_pct, 0)*1 - COALESCE(i.disputes, 0)*5) >= 75 THEN 'B - Approved'
        WHEN (100 - COALESCE(d.damage_rate, 0)*2 - COALESCE(d.discrepancy_rate, 0)*1.5
              - COALESCE(i.overdue_pct, 0)*1 - COALESCE(i.disputes, 0)*5) >= 50 THEN 'C - Conditional'
        ELSE 'D - Review Required'
    END AS supplier_tier,
    current_timestamp() AS scored_at
FROM del_stats d
FULL OUTER JOIN inv_stats i ON d.supplier = i.supplier
""")

cnt = spark.sql(f"SELECT COUNT(*) FROM {catalog}.supply_chain_gold.supplier_scorecard").collect()[0][0]
print(f"[OK] Table: supplier_scorecard ({cnt} rows)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold Summary

# COMMAND ----------

print(f"""
{'='*60}
  [OK] Gold Layer Complete
{'='*60}
  
  Materialized Views (auto-refreshed):
    • fleet_utilisation_daily     -  daily vehicle metrics
    • delivery_performance        -  supplier delivery KPIs
  
  Tables (snapshot):
    • inventory_health            -  latest stock per warehouse
    • supplier_scorecard          -  composite supplier scoring
  
  Views (always live):
    • invoice_aging               -  payment risk buckets
    • site_operations_summary     -  cross-domain site dashboard
  
  [NEXT]  All gold objects ready for Genie Space / Data Agent / BI
{'='*60}
""")
