# Databricks notebook source
# MAGIC %md
# MAGIC # Supply Chain  -  Silver Layer (Cleansed & Conformed)
# MAGIC
# MAGIC Reads bronze tables and applies:
# MAGIC - **Type casting** (string dates → DATE/TIMESTAMP)
# MAGIC - **Deduplication** (by primary key, keep latest)
# MAGIC - **Data quality checks** (null handling, range validation)
# MAGIC - **Standardisation** (consistent naming, enums)
# MAGIC
# MAGIC | Silver Table | Source Bronze | Key Transforms |
# MAGIC |-------------|-------------|----------------|
# MAGIC | `silver.fleet_positions` | `bronze.gps_pings` | Dedup by ping_id, validate coords, cast timestamps |
# MAGIC | `silver.deliveries` | `bronze.delivery_receipts` | Dedup by delivery_id, cast dates, validate costs |
# MAGIC | `silver.inventory_snapshots` | `bronze.warehouse_stock` | Dedup by wh+material+batch, cast dates, flag anomalies |
# MAGIC | `silver.invoices` | `bronze.supplier_invoices` | Dedup by invoice_id, cast dates, validate totals |

# COMMAND ----------

dbutils.widgets.text("catalog_name", "my_catalog", "Catalog Name")
catalog = dbutils.widgets.get("catalog_name")

# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.supply_chain_silver COMMENT 'Cleansed and conformed layer'")
print(f"[OK] Schema: {catalog}.supply_chain_silver")

# COMMAND ----------

from pyspark.sql.functions import (
    col, to_timestamp, to_date, current_timestamp, row_number, when, abs as spark_abs, lit
)
from pyspark.sql.window import Window

# COMMAND ----------

# MAGIC %md
# MAGIC ## Silver Table 1: Fleet Positions

# COMMAND ----------

gps_bronze = spark.table(f"{catalog}.supply_chain_bronze.gps_pings")

# Dedup: keep latest ingestion per ping_id
w = Window.partitionBy("ping_id").orderBy(col("_ingested_at").desc())
gps_clean = (gps_bronze
    .withColumn("_rn", row_number().over(w))
    .filter("_rn = 1").drop("_rn")
    # Validate coordinates (Australia bounding box)
    .filter("latitude BETWEEN -45 AND -10 AND longitude BETWEEN 110 AND 155")
    # Clamp speed to realistic range
    .withColumn("speed_kmh", when(col("speed_kmh") < 0, lit(0.0))
                             .when(col("speed_kmh") > 120, lit(120.0))
                             .otherwise(col("speed_kmh")))
    # Cast timestamp
    .withColumn("ping_timestamp", to_timestamp("ping_timestamp"))
    # Derive movement status
    .withColumn("is_moving", col("speed_kmh") > 1.0)
    .withColumn("is_idling", (col("engine_on") == True) & (col("speed_kmh") <= 1.0))
    # Metadata
    .withColumn("_silver_processed_at", current_timestamp())
    .drop("_ingested_at", "_source_file")
)

(gps_clean.write
    .mode("overwrite")
    .option("overwriteSchema", True)
    .saveAsTable(f"{catalog}.supply_chain_silver.fleet_positions"))
print(f"[OK] Silver fleet_positions: {gps_clean.count()} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Silver Table 2: Deliveries

# COMMAND ----------

del_bronze = spark.table(f"{catalog}.supply_chain_bronze.delivery_receipts")

w = Window.partitionBy("delivery_id").orderBy(col("_ingested_at").desc())
del_clean = (del_bronze
    .withColumn("_rn", row_number().over(w))
    .filter("_rn = 1").drop("_rn")
    # Cast dates
    .withColumn("delivery_date", to_date("delivery_date"))
    # Validate costs: total should equal qty * unit_price (within tolerance)
    .withColumn("expected_total", col("quantity") * col("unit_price"))
    .withColumn("cost_variance_pct",
                when(col("expected_total") > 0,
                     spark_abs(col("total_cost") - col("expected_total")) / col("expected_total") * 100)
                .otherwise(lit(0.0)))
    .withColumn("cost_validated", col("cost_variance_pct") < 1.0)
    # Standardise condition
    .withColumn("condition", when(col("condition").isNull(), lit("unknown")).otherwise(col("condition")))
    # Derive flags
    .withColumn("is_damaged", col("condition").isin("damaged", "partial"))
    .withColumn("_silver_processed_at", current_timestamp())
    .drop("_ingested_at", "_source_file", "expected_total")
)

(del_clean.write
    .mode("overwrite")
    .option("overwriteSchema", True)
    .saveAsTable(f"{catalog}.supply_chain_silver.deliveries"))
print(f"[OK] Silver deliveries: {del_clean.count()} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Silver Table 3: Inventory Snapshots

# COMMAND ----------

stock_bronze = spark.table(f"{catalog}.supply_chain_bronze.warehouse_stock")

w = Window.partitionBy("warehouse_id", "material", "batch_id").orderBy(col("_ingested_at").desc())
stock_clean = (stock_bronze
    .withColumn("_rn", row_number().over(w))
    .filter("_rn = 1").drop("_rn")
    # Cast dates
    .withColumn("last_replenished", to_date("last_replenished"))
    .withColumn("snapshot_timestamp", to_timestamp("snapshot_timestamp"))
    # Validate stock levels
    .withColumn("on_hand_qty", when(col("on_hand_qty") < 0, lit(0)).otherwise(col("on_hand_qty")))
    # Derive stock health
    .withColumn("stock_status",
                when(col("on_hand_qty") == 0, lit("out_of_stock"))
                .when(col("below_reorder") == True, lit("below_reorder"))
                .when(col("on_hand_qty") > col("reorder_point") * 3, lit("overstocked"))
                .otherwise(lit("healthy")))
    .withColumn("days_since_replenishment",
                (to_date(current_timestamp()) - col("last_replenished")).cast("int"))
    .withColumn("_silver_processed_at", current_timestamp())
    .drop("_ingested_at", "_source_file")
)

(stock_clean.write
    .mode("overwrite")
    .option("overwriteSchema", True)
    .saveAsTable(f"{catalog}.supply_chain_silver.inventory_snapshots"))
print(f"[OK] Silver inventory_snapshots: {stock_clean.count()} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Silver Table 4: Invoices

# COMMAND ----------

inv_bronze = spark.table(f"{catalog}.supply_chain_bronze.supplier_invoices")

w = Window.partitionBy("invoice_id").orderBy(col("_ingested_at").desc())
inv_clean = (inv_bronze
    .withColumn("_rn", row_number().over(w))
    .filter("_rn = 1").drop("_rn")
    # Cast dates
    .withColumn("invoice_date", to_date("invoice_date"))
    .withColumn("due_date", to_date("due_date"))
    # Validate GST calculation (should be 10% of subtotal)
    .withColumn("expected_gst", col("subtotal_aud") * 0.1)
    .withColumn("gst_validated", spark_abs(col("gst_aud") - col("expected_gst")) < 1.0)
    # Derive payment flags
    .withColumn("is_overdue",
                (col("payment_status") == "pending") & (col("due_date") < to_date(current_timestamp())))
    .withColumn("days_until_due",
                (col("due_date") - to_date(current_timestamp())).cast("int"))
    .withColumn("_silver_processed_at", current_timestamp())
    .drop("_ingested_at", "_source_file", "expected_gst")
)

(inv_clean.write
    .mode("overwrite")
    .option("overwriteSchema", True)
    .saveAsTable(f"{catalog}.supply_chain_silver.invoices"))
print(f"[OK] Silver invoices: {inv_clean.count()} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Silver Summary

# COMMAND ----------

tables = ["fleet_positions", "deliveries", "inventory_snapshots", "invoices"]
print(f"\n{'='*60}")
print(f"  [OK] Silver Transform Complete")
print(f"{'='*60}")
for t in tables:
    cnt = spark.sql(f"SELECT COUNT(*) FROM {catalog}.supply_chain_silver.{t}").collect()[0][0]
    print(f"  {t:30s} {cnt:>8,} rows")
print(f"{'='*60}")
print(f"\n  [NEXT]  Next: Run 03_gold_aggregation for analytics-ready tables")
