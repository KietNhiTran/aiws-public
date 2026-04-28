# Databricks notebook source
# MAGIC %md
# MAGIC # Supply Chain  -  Bronze Layer (Raw Ingestion)
# MAGIC
# MAGIC Reads raw CSV/JSON from the landing zone and loads into **bronze** tables.
# MAGIC Bronze = raw data, append-only, with ingestion metadata.
# MAGIC
# MAGIC | Bronze Table | Source Feed | Format | Strategy |
# MAGIC |-------------|-------------|--------|----------|
# MAGIC | `bronze.gps_pings` | GPS Pings | CSV | Append with COPY INTO |
# MAGIC | `bronze.delivery_receipts` | Delivery Receipts | JSON | Append with COPY INTO |
# MAGIC | `bronze.warehouse_stock` | Warehouse Stock | CSV | Append with COPY INTO |
# MAGIC | `bronze.supplier_invoices` | Supplier Invoices | CSV | Append with COPY INTO |
# MAGIC
# MAGIC Each row gets `_ingested_at` and `_source_file` metadata columns.

# COMMAND ----------

dbutils.widgets.text("catalog_name", "my_catalog", "Catalog Name")
dbutils.widgets.text("landing_path", "/Volumes/my_catalog/supply_chain_landing/raw_data", "Landing Path")
dbutils.widgets.text("batch_id", "", "Batch ID (blank = latest)")

catalog = dbutils.widgets.get("catalog_name")
landing_path = dbutils.widgets.get("landing_path")
batch_id = dbutils.widgets.get("batch_id")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Bronze Schema

# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.supply_chain_bronze COMMENT 'Raw ingestion layer  -  append only'")
print(f"[OK] Schema: {catalog}.supply_chain_bronze")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Resolve Batch Path

# COMMAND ----------

import os

if batch_id:
    batch_path = f"{landing_path}/{batch_id}"
else:
    # Find latest batch folder
    batches = [f.name for f in dbutils.fs.ls(landing_path) if f.isDir()]
    batches.sort(reverse=True)
    if not batches:
        raise ValueError(f"No batch folders found in {landing_path}")
    batch_id = batches[0].rstrip("/")
    batch_path = f"{landing_path}/{batch_id}"

print(f"[INFO] Processing batch: {batch_id}")
print(f"   Path: {batch_path}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Bronze Table 1: GPS Pings

# COMMAND ----------

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {catalog}.supply_chain_bronze.gps_pings (
    ping_id STRING,
    vehicle_id STRING,
    vehicle_type STRING,
    site_name STRING,
    latitude DOUBLE,
    longitude DOUBLE,
    speed_kmh DOUBLE,
    heading_degrees DOUBLE,
    engine_on BOOLEAN,
    fuel_level_pct DOUBLE,
    ping_timestamp TIMESTAMP,
    batch_id STRING,
    _ingested_at TIMESTAMP,
    _source_file STRING
)
USING DELTA
COMMENT 'Raw GPS telemetry pings from fleet vehicles'
""")

from pyspark.sql.functions import current_timestamp, col, lit

def _cast_to_table(df, table_fqn):
    """Cast DataFrame columns to match existing table schema to avoid type-merge errors."""
    target = spark.table(table_fqn)
    target_fields = {f.name: f.dataType for f in target.schema.fields}
    for c in df.columns:
        if c in target_fields:
            df = df.withColumn(c, col(c).cast(target_fields[c]))
    return df

gps_df = (spark.read
    .option("header", True)
    .option("inferSchema", True)
    .csv(f"{batch_path}/gps_pings")
    .withColumn("_ingested_at", current_timestamp())
    .withColumn("_source_file", col("_metadata.file_path"))
)
gps_df = _cast_to_table(gps_df, f"{catalog}.supply_chain_bronze.gps_pings")

gps_df.write.mode("append").saveAsTable(f"{catalog}.supply_chain_bronze.gps_pings")
print(f"[OK] Bronze GPS pings: {gps_df.count()} rows ingested")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Bronze Table 2: Delivery Receipts

# COMMAND ----------

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {catalog}.supply_chain_bronze.delivery_receipts (
    delivery_id STRING,
    supplier STRING,
    material STRING,
    quantity INT,
    unit STRING,
    unit_price DOUBLE,
    total_cost DOUBLE,
    destination_site STRING,
    warehouse_origin STRING,
    po_number STRING,
    delivery_date STRING,
    received_by STRING,
    `condition` STRING,
    batch_id STRING,
    _ingested_at TIMESTAMP,
    _source_file STRING
)
USING DELTA
COMMENT 'Raw delivery receipt records from suppliers'
""")

from pyspark.sql.functions import current_timestamp, col

del_df = (spark.read
    .option("inferSchema", True)
    .json(f"{batch_path}/delivery_receipts")
    .withColumn("_ingested_at", current_timestamp())
    .withColumn("_source_file", col("_metadata.file_path"))
)
del_df = _cast_to_table(del_df, f"{catalog}.supply_chain_bronze.delivery_receipts")

del_df.write.mode("append").saveAsTable(f"{catalog}.supply_chain_bronze.delivery_receipts")
print(f"[OK] Bronze delivery receipts: {del_df.count()} rows ingested")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Bronze Table 3: Warehouse Stock

# COMMAND ----------

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {catalog}.supply_chain_bronze.warehouse_stock (
    warehouse_id STRING,
    warehouse_name STRING,
    region STRING,
    material STRING,
    on_hand_qty INT,
    reorder_point INT,
    unit STRING,
    below_reorder BOOLEAN,
    last_replenished STRING,
    snapshot_timestamp STRING,
    batch_id STRING,
    _ingested_at TIMESTAMP,
    _source_file STRING
)
USING DELTA
COMMENT 'Raw warehouse stock level snapshots'
""")

stock_df = (spark.read
    .option("header", True)
    .option("inferSchema", True)
    .csv(f"{batch_path}/warehouse_stock")
    .withColumn("_ingested_at", current_timestamp())
    .withColumn("_source_file", col("_metadata.file_path"))
)
stock_df = _cast_to_table(stock_df, f"{catalog}.supply_chain_bronze.warehouse_stock")

stock_df.write.mode("append").saveAsTable(f"{catalog}.supply_chain_bronze.warehouse_stock")
print(f"[OK] Bronze warehouse stock: {stock_df.count()} rows ingested")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Bronze Table 4: Supplier Invoices

# COMMAND ----------

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {catalog}.supply_chain_bronze.supplier_invoices (
    invoice_id STRING,
    supplier STRING,
    po_number STRING,
    invoice_date STRING,
    due_date STRING,
    line_items INT,
    subtotal_aud DOUBLE,
    gst_aud DOUBLE,
    total_aud DOUBLE,
    currency STRING,
    payment_status STRING,
    site STRING,
    batch_id STRING,
    _ingested_at TIMESTAMP,
    _source_file STRING
)
USING DELTA
COMMENT 'Raw supplier invoice records'
""")

inv_df = (spark.read
    .option("header", True)
    .option("inferSchema", True)
    .csv(f"{batch_path}/supplier_invoices")
    .withColumn("_ingested_at", current_timestamp())
    .withColumn("_source_file", col("_metadata.file_path"))
)
inv_df = _cast_to_table(inv_df, f"{catalog}.supply_chain_bronze.supplier_invoices")

inv_df.write.mode("append").saveAsTable(f"{catalog}.supply_chain_bronze.supplier_invoices")
print(f"[OK] Bronze supplier invoices: {inv_df.count()} rows ingested")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Bronze Summary

# COMMAND ----------

tables = ["gps_pings", "delivery_receipts", "warehouse_stock", "supplier_invoices"]
print(f"\n{'='*60}")
print(f"  [OK] Bronze Ingestion Complete  -  Batch {batch_id}")
print(f"{'='*60}")
for t in tables:
    cnt = spark.sql(f"SELECT COUNT(*) FROM {catalog}.supply_chain_bronze.{t}").collect()[0][0]
    print(f"  {t:30s} {cnt:>8,} total rows")
print(f"{'='*60}")
print(f"\n  [NEXT]  Next: Run 02_silver_transform to clean and deduplicate")
