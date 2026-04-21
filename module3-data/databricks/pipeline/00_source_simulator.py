# Databricks notebook source
# MAGIC %md
# MAGIC # Supply Chain  -  Source Data Simulator
# MAGIC
# MAGIC Simulates external data feeds landing into a **raw zone** as CSV/JSON files.
# MAGIC Each run generates a new batch of data (simulating real-time/scheduled feeds).
# MAGIC
# MAGIC **Data feeds:**
# MAGIC | Feed | Format | ~Rows/batch | Description |
# MAGIC |------|--------|-------------|-------------|
# MAGIC | GPS Pings | CSV | 500 | Fleet vehicle location pings every 5 min |
# MAGIC | Delivery Receipts | JSON | 100 | Material deliveries to construction sites |
# MAGIC | Warehouse Stock | CSV | 200 | Current stock levels across warehouses |
# MAGIC | Supplier Invoices | CSV | 80 | Incoming invoices from suppliers |
# MAGIC
# MAGIC **Landing path:** `{catalog}.supply_chain_raw` volume or DBFS `/tmp/supply_chain_landing/`

# COMMAND ----------

dbutils.widgets.text("catalog_name", "adb_cimic_aiws_dev_ws", "Catalog Name")
dbutils.widgets.text("landing_path", "/Volumes/adb_cimic_aiws_dev_ws/supply_chain_landing/raw_data", "Landing Path")
dbutils.widgets.text("batch_id", "", "Batch ID (leave blank for auto)")

catalog = dbutils.widgets.get("catalog_name")
landing_path = dbutils.widgets.get("landing_path")
batch_id_input = dbutils.widgets.get("batch_id")

# COMMAND ----------

import random, json, datetime, uuid
import pandas as pd

def _to_spark_df(rows):
    """Convert list of dicts to Spark DataFrame via pandas to avoid type inference issues."""
    return spark.createDataFrame(pd.DataFrame(rows))

batch_id = batch_id_input if batch_id_input else datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
print(f"[INFO] Generating batch: {batch_id}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Reference Data

# COMMAND ----------

VEHICLES = [
    {"id": f"VH-{i:03d}", "type": t, "site": s}
    for i, (t, s) in enumerate([
        ("haul_truck", "Sydney Metro West"), ("excavator", "Sydney Metro West"),
        ("crane", "Sydney Metro West"), ("haul_truck", "Inland Rail Narrabri"),
        ("excavator", "Inland Rail Narrabri"), ("loader", "Inland Rail Narrabri"),
        ("haul_truck", "WestConnex M4-M5 Link"), ("crane", "WestConnex M4-M5 Link"),
        ("haul_truck", "Melbourne Metro Tunnel"), ("excavator", "Melbourne Metro Tunnel"),
        ("loader", "Melbourne Metro Tunnel"), ("crane", "Cross River Rail Brisbane"),
        ("haul_truck", "Cross River Rail Brisbane"), ("excavator", "Pacific Hwy Coffs Harbour"),
        ("haul_truck", "Snowy 2.0 Tunnel"), ("loader", "Snowy 2.0 Tunnel"),
        ("crane", "Western Sydney Airport"), ("haul_truck", "Western Sydney Airport"),
        ("excavator", "North East Link Melbourne"), ("haul_truck", "Rozelle Interchange Sydney"),
    ], start=1)
]

WAREHOUSES = [
    {"id": "WH-SYD-01", "name": "Sydney Central Depot", "region": "NSW"},
    {"id": "WH-MEL-01", "name": "Melbourne South Yard", "region": "VIC"},
    {"id": "WH-BNE-01", "name": "Brisbane Northside Hub", "region": "QLD"},
    {"id": "WH-ADL-01", "name": "Adelaide Warehouse", "region": "SA"},
]

MATERIALS = [
    "Concrete Ready-Mix", "Structural Steel Beams", "Rebar 16mm", "Rebar 20mm",
    "Aggregate 20mm", "Sand (washed)", "Cement (bulk)", "Timber Formwork",
    "Precast Panels", "Geotextile Fabric", "PVC Pipe 300mm", "Electrical Cable 4-core",
    "Bolts M20 HDG", "Welding Rod E7018", "Diesel Fuel", "Hydraulic Oil",
]

SUPPLIERS = [
    "Boral Limited", "BlueScope Steel", "Adelaide Brighton Cement",
    "Hanson Construction Materials", "InfraBuild", "Holcim Australia",
    "Downer EDI", "Coates Hire",
]

SITES = [v["site"] for v in VEHICLES]
SITE_COORDS = {
    "Sydney Metro West": (-33.87, 151.08), "Inland Rail Narrabri": (-30.33, 149.78),
    "WestConnex M4-M5 Link": (-33.90, 151.15), "Melbourne Metro Tunnel": (-37.81, 144.96),
    "Pacific Hwy Coffs Harbour": (-30.30, 153.11), "Cross River Rail Brisbane": (-27.47, 153.02),
    "Snowy 2.0 Tunnel": (-36.15, 148.38), "Western Sydney Airport": (-33.88, 150.73),
    "North East Link Melbourne": (-37.74, 145.06), "Rozelle Interchange Sydney": (-33.86, 151.17),
}

# COMMAND ----------

# MAGIC %md
# MAGIC ## Feed 1: GPS Pings (CSV)

# COMMAND ----------

now = datetime.datetime.now()
gps_rows = []
for _ in range(500):
    v = random.choice(VEHICLES)
    base_lat, base_lon = SITE_COORDS.get(v["site"], (-33.87, 151.21))
    gps_rows.append(dict(
        ping_id=uuid.uuid4().hex[:12],
        vehicle_id=v["id"],
        vehicle_type=v["type"],
        site_name=v["site"],
        latitude=round(base_lat + random.uniform(-0.02, 0.02), 6),
        longitude=round(base_lon + random.uniform(-0.02, 0.02), 6),
        speed_kmh=round(random.uniform(0, 60) if random.random() > 0.3 else 0, 1),
        heading_degrees=round(random.uniform(0, 360), 1),
        engine_on=random.choice([True, True, True, False]),
        fuel_level_pct=round(random.uniform(10, 100), 1),
        ping_timestamp=now - datetime.timedelta(minutes=random.randint(0, 60)),
        batch_id=batch_id,
    ))

gps_df = _to_spark_df(gps_rows)
gps_path = f"{landing_path}/{batch_id}/gps_pings"
gps_df.coalesce(1).write.mode("overwrite").option("header", True).csv(gps_path)
print(f"[OK] GPS pings: {gps_df.count()} rows → {gps_path}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Feed 2: Delivery Receipts (JSON)

# COMMAND ----------

delivery_rows = []
for _ in range(100):
    mat = random.choice(MATERIALS)
    qty = random.randint(1, 500)
    unit_price = round(random.uniform(5, 2000), 2)
    delivery_rows.append(dict(
        delivery_id=f"DEL-{uuid.uuid4().hex[:8].upper()}",
        supplier=random.choice(SUPPLIERS),
        material=mat,
        quantity=qty,
        unit=random.choice(["tonnes", "m3", "units", "litres", "metres"]),
        unit_price=unit_price,
        total_cost=round(qty * unit_price, 2),
        destination_site=random.choice(list(set(SITES))),
        warehouse_origin=random.choice(WAREHOUSES)["id"],
        po_number=f"PO-{random.randint(10000, 99999)}",
        delivery_date=(now - datetime.timedelta(days=random.randint(0, 7))).strftime("%Y-%m-%d"),
        received_by=random.choice(["J. Smith", "M. Chen", "A. Patel", "S. Williams", "K. Brown"]),
        condition=random.choices(["good", "good", "good", "damaged", "partial"], weights=[60, 20, 10, 5, 5])[0],
        batch_id=batch_id,
    ))

del_df = _to_spark_df(delivery_rows)
del_path = f"{landing_path}/{batch_id}/delivery_receipts"
del_df.coalesce(1).write.mode("overwrite").json(del_path)
print(f"[OK] Delivery receipts: {del_df.count()} rows → {del_path}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Feed 3: Warehouse Stock Levels (CSV)

# COMMAND ----------

stock_rows = []
for wh in WAREHOUSES:
    for mat in MATERIALS:
        if random.random() > 0.15:  # not every warehouse stocks everything
            on_hand = random.randint(0, 5000)
            reorder_point = random.randint(100, 1000)
            stock_rows.append(dict(
                warehouse_id=wh["id"],
                warehouse_name=wh["name"],
                region=wh["region"],
                material=mat,
                on_hand_qty=on_hand,
                reorder_point=reorder_point,
                unit=random.choice(["tonnes", "m3", "units", "litres", "metres"]),
                below_reorder=on_hand < reorder_point,
                last_replenished=(now - datetime.timedelta(days=random.randint(0, 30))).strftime("%Y-%m-%d"),
                snapshot_timestamp=now.strftime("%Y-%m-%d %H:%M:%S"),
                batch_id=batch_id,
            ))

stock_df = _to_spark_df(stock_rows)
stock_path = f"{landing_path}/{batch_id}/warehouse_stock"
stock_df.coalesce(1).write.mode("overwrite").option("header", True).csv(stock_path)
print(f"[OK] Warehouse stock: {stock_df.count()} rows → {stock_path}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Feed 4: Supplier Invoices (CSV)

# COMMAND ----------

invoice_rows = []
for _ in range(80):
    supplier = random.choice(SUPPLIERS)
    line_items = random.randint(1, 8)
    subtotal = round(random.uniform(500, 150000), 2)
    gst = round(subtotal * 0.1, 2)
    status = random.choices(["pending", "approved", "paid", "disputed"], weights=[30, 35, 25, 10])[0]
    invoice_rows.append(dict(
        invoice_id=f"INV-{uuid.uuid4().hex[:8].upper()}",
        supplier=supplier,
        po_number=f"PO-{random.randint(10000, 99999)}",
        invoice_date=(now - datetime.timedelta(days=random.randint(0, 45))).strftime("%Y-%m-%d"),
        due_date=(now + datetime.timedelta(days=random.randint(14, 60))).strftime("%Y-%m-%d"),
        line_items=line_items,
        subtotal_aud=subtotal,
        gst_aud=gst,
        total_aud=round(subtotal + gst, 2),
        currency="AUD",
        payment_status=status,
        site=random.choice(list(set(SITES))),
        batch_id=batch_id,
    ))

inv_df = _to_spark_df(invoice_rows)
inv_path = f"{landing_path}/{batch_id}/supplier_invoices"
inv_df.coalesce(1).write.mode("overwrite").option("header", True).csv(inv_path)
print(f"[OK] Supplier invoices: {inv_df.count()} rows → {inv_path}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print(f"""
{'='*60}
  [OK] Batch {batch_id}  -  All feeds generated
{'='*60}
  Landing path: {landing_path}/{batch_id}/
  
  Feeds:
    • gps_pings/          ~500 rows  (CSV)
    • delivery_receipts/  ~100 rows  (JSON)
    • warehouse_stock/    ~200 rows  (CSV)
    • supplier_invoices/   ~80 rows  (CSV)
  
  Total: ~880 rows per batch
  
  [NEXT]  Next: Run 01_bronze_ingestion to load into bronze tables
{'='*60}
""")
