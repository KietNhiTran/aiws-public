# Databricks notebook source
# MAGIC %md
# MAGIC # Module 03 -- Generate Data
# MAGIC
# MAGIC Populates the 4 Module 03 tables with realistic data (1000+ rows per table).
# MAGIC Uses dict() + pandas intermediate to avoid Spark type-inference errors.
# MAGIC
# MAGIC All names parameterised via `customer_name`.

# COMMAND ----------

dbutils.widgets.text("catalog_name", "cimic", "Catalog Name")
dbutils.widgets.text("customer_name", "CIMIC", "Customer Display Name")
dbutils.widgets.text("num_projects", "120", "Number of projects")
dbutils.widgets.text("num_telemetry_rows", "5000", "Telemetry rows")
dbutils.widgets.text("num_incident_rows", "1500", "Incident rows")
dbutils.widgets.text("num_material_rows", "1200", "Material rows")

catalog = dbutils.widgets.get("catalog_name")
customer = dbutils.widgets.get("customer_name")
NUM_PROJECTS = int(dbutils.widgets.get("num_projects"))
NUM_TELEMETRY = int(dbutils.widgets.get("num_telemetry_rows"))
NUM_INCIDENTS = int(dbutils.widgets.get("num_incident_rows"))
NUM_MATERIALS = int(dbutils.widgets.get("num_material_rows"))

print(f"Catalog: {catalog} | Customer: {customer}")
print(f"Projects: {NUM_PROJECTS}, Telemetry: {NUM_TELEMETRY}, Incidents: {NUM_INCIDENTS}, Materials: {NUM_MATERIALS}")

# COMMAND ----------

import random, datetime, hashlib
import pandas as pd

random.seed(42)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Reference Data

# COMMAND ----------

# Divisions and their typical project types
DIVISIONS = {
    "CPB Contractors": {
        "types": ["Rail Infrastructure", "Road/Tunnel", "Road Infrastructure", "Building"],
        "sites": ["Sydney Metro West", "WestConnex Tunnel", "Melbourne Metro Tunnel",
                   "Inland Rail Narrabri", "Pacific Highway Coffs Harbour", "Cross River Rail Brisbane"],
        "states": ["NSW", "VIC", "QLD"],
        "clients": ["Transport for NSW", "Rail Projects Victoria", "ARTC",
                     "Sydney Metro Authority", "Cross River Rail Delivery Authority"],
    },
    "Thiess": {
        "types": ["Contract Services", "Mining Services"],
        "sites": ["Bowen Basin", "Mount Pleasant", "Carmichael Mine",
                   "Pilbara Iron Ore", "Olympic Dam Underground", "Hunter Valley Operations"],
        "states": ["QLD", "NSW", "WA", "SA"],
        "clients": ["BHP Mitsubishi Alliance", "MACH Energy", "Adani",
                     "Rio Tinto", "Glencore", "BHP"],
    },
    "Sedgman": {
        "types": ["Mineral Processing", "Water Infrastructure"],
        "sites": ["Olympic Dam Processing", "Perth Desalination", "Gladstone LNG",
                   "Mount Isa Processing", "Snowy 2.0 Hydro"],
        "states": ["SA", "WA", "QLD", "NSW"],
        "clients": ["BHP", "Water Corporation WA", "Santos",
                     "Glencore", "Snowy Hydro"],
    },
    "Pacific Partnerships": {
        "types": ["PPP Infrastructure", "Social Infrastructure"],
        "sites": ["Melbourne Convention Centre", "Sydney Light Rail",
                   "Gold Coast Hospital", "Brisbane Airport Link"],
        "states": ["VIC", "NSW", "QLD"],
        "clients": ["Victorian Government", "Transport for NSW",
                     "Queensland Health", "Brisbane Airport Corporation"],
    },
}

EQUIPMENT_TYPES = ["haul_truck", "excavator", "drill", "loader", "dozer", "grader", "water_cart", "crane"]
EQUIPMENT_PREFIXES = {"haul_truck": "HT", "excavator": "EX", "drill": "DR", "loader": "LD",
                       "dozer": "DZ", "grader": "GR", "water_cart": "WC", "crane": "CR"}

INCIDENT_TYPES = ["Slip/Trip/Fall", "Vehicle Interaction", "Equipment Failure", "Falling Object",
                   "Chemical Exposure", "Heat Stress", "Noise Exposure", "Confined Space",
                   "Electrical", "Struck By", "Manual Handling", "Working at Height"]
SEVERITIES = ["Minor", "Moderate", "Serious", "Critical"]
SEVERITY_WEIGHTS = [0.45, 0.30, 0.18, 0.07]
ROOT_CAUSES = ["human_error", "equipment_failure", "procedural", "environmental",
                "design", "poor_housekeeping", "inadequate_training"]

MATERIAL_CATEGORIES = {
    "Steel": [("Structural Steel (Grade 350)", 2600, 3100, "tonne"),
              ("Reinforcement Bar (N12)", 1500, 1800, "tonne"),
              ("Steel Piling (UC sections)", 3200, 3800, "tonne"),
              ("Stainless Steel (316L)", 5500, 6500, "tonne")],
    "Concrete": [("Ready-Mix Concrete (40 MPa)", 260, 310, "cubic_meter"),
                  ("Shotcrete Mix", 290, 340, "cubic_meter"),
                  ("Precast Concrete Panels", 180, 250, "square_meter"),
                  ("Concrete Admixture (superplasticiser)", 8, 14, "litre")],
    "Fuel": [("Diesel Fuel (Industrial Grade)", 1.60, 2.10, "litre"),
              ("LPG (bulk delivery)", 0.90, 1.30, "litre")],
    "Precast": [("Tunnel Liner Segments", 4000, 5000, "segment"),
                 ("Precast Drainage Pits", 1200, 1600, "unit")],
    "Geosynthetics": [("Geotextile Membrane", 10, 16, "square_meter"),
                       ("HDPE Liner (2mm)", 22, 30, "square_meter")],
    "Site Consumables": [("Explosives (ANFO)", 850, 1050, "tonne"),
                          ("Caterpillar GET (Ground Engaging Tools)", 16000, 20000, "set"),
                          ("Drill Bits (tricone)", 8000, 12000, "unit")],
    "Safety": [("PPE - Hard Hats (AS/NZS 1801)", 35, 55, "unit"),
                ("PPE - Safety Boots (AS/NZS 2210.3)", 120, 180, "pair"),
                ("First Aid Kit (industrial)", 200, 350, "unit")],
    "Electrical": [("HV Cable (11kV XLPE)", 45, 65, "metre"),
                    ("Switchgear Panel", 25000, 40000, "unit")],
    "Aggregate": [("Crushed Rock (20mm)", 35, 50, "tonne"),
                   ("Road Base (DGB20)", 28, 42, "tonne")],
    "Timber": [("Formwork Plywood (17mm)", 55, 75, "sheet"),
                ("Hardwood Sleepers (rail)", 85, 120, "unit")],
}

SUPPLIERS = {
    "Steel": ["BlueScope Steel", "InfraBuild", "OneSteel", "Liberty Steel"],
    "Concrete": ["Hanson Australia", "Boral", "Holcim", "Sika Australia"],
    "Fuel": ["Shell Australia", "BP Australia", "Viva Energy", "Ampol"],
    "Precast": ["CPB Precast Facility", "Rocla", "Humes"],
    "Geosynthetics": ["Geofabrics Australasia", "GeoTech Solutions", "Maccaferri"],
    "Site Consumables": ["Orica", "WesTrac", "Sandvik", "Epiroc"],
    "Safety": ["Blackwoods", "Total Tools", "RSEA Safety"],
    "Electrical": ["Prysmian Group", "NHP Electrical", "Schneider Electric"],
    "Aggregate": ["Boral Quarries", "Hanson Quarries", "Holcim Aggregates"],
    "Timber": ["Hyne Timber", "Carter Holt Harvey", "Dindas Australia"],
}

MANAGERS = ["Sarah Johnson", "Michael Chen", "David Park", "Lisa Wang", "James Morrison",
            "Emma Nguyen", "Robert Taylor", "Amanda Liu", "Tom Richards", "Karen White",
            "Daniel Kim", "Priya Sharma", "Chris O'Brien", "Megan Foster", "Andrew Lee",
            "Rachel Adams", "Nathan Wright", "Sophie Clarke", "Marcus Bell", "Hannah Scott"]

# All sites flattened
ALL_SITES = []
SITE_TO_DIVISION = {}
for div, info in DIVISIONS.items():
    for site in info["sites"]:
        ALL_SITES.append(site)
        SITE_TO_DIVISION[site] = div

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Generate Projects (financials)

# COMMAND ----------

from pyspark.sql.types import StructType, StructField, StringType, DoubleType, IntegerType, DateType, TimestampType

# Explicit schemas to avoid pandas int64 / Spark INT merge failures
_SCHEMAS = {
    "financials": StructType([
        StructField("project_id", StringType()), StructField("project_name", StringType()),
        StructField("division", StringType()), StructField("client", StringType()),
        StructField("project_type", StringType()), StructField("state", StringType()),
        StructField("budget_aud", DoubleType()), StructField("actual_cost_aud", DoubleType()),
        StructField("earned_value_aud", DoubleType()), StructField("planned_value_aud", DoubleType()),
        StructField("cost_variance_pct", DoubleType()), StructField("spi", DoubleType()),
        StructField("cpi", DoubleType()), StructField("status", StringType()),
        StructField("start_date", DateType()), StructField("planned_completion", DateType()),
        StructField("reporting_period", DateType()), StructField("project_manager", StringType()),
    ]),
    "equipment_telemetry": StructType([
        StructField("equipment_id", StringType()), StructField("equipment_type", StringType()),
        StructField("site_name", StringType()), StructField("division", StringType()),
        StructField("engine_temp_celsius", DoubleType()), StructField("fuel_level_pct", DoubleType()),
        StructField("operating_hours", IntegerType()), StructField("maintenance_due_date", DateType()),
        StructField("status", StringType()), StructField("reading_timestamp", TimestampType()),
    ]),
    "incidents": StructType([
        StructField("incident_id", StringType()), StructField("incident_date", DateType()),
        StructField("site_name", StringType()), StructField("division", StringType()),
        StructField("incident_type", StringType()), StructField("severity", StringType()),
        StructField("description", StringType()), StructField("injuries", IntegerType()),
        StructField("lost_time_days", DoubleType()), StructField("root_cause", StringType()),
        StructField("corrective_action", StringType()), StructField("status", StringType()),
    ]),
    "materials": StructType([
        StructField("material_id", StringType()), StructField("material_name", StringType()),
        StructField("category", StringType()), StructField("supplier", StringType()),
        StructField("unit_price_aud", DoubleType()), StructField("unit", StringType()),
        StructField("lead_time_days", IntegerType()), StructField("last_order_date", DateType()),
        StructField("last_order_qty", DoubleType()), StructField("price_trend", StringType()),
        StructField("availability", StringType()),
    ]),
}

def _to_spark(rows, table_name=None):
    """Convert list of dicts to Spark DataFrame with explicit schema to avoid type merge errors."""
    pdf = pd.DataFrame(rows)
    schema = _SCHEMAS.get(table_name)
    if schema:
        return spark.createDataFrame(pdf, schema=schema)
    return spark.createDataFrame(pdf)

projects = []
pid = 1
for div_name, div_info in DIVISIONS.items():
    n_div = max(5, NUM_PROJECTS * len(div_info["sites"]) // len(ALL_SITES))
    for i in range(n_div):
        site = random.choice(div_info["sites"])
        ptype = random.choice(div_info["types"])
        client = random.choice(div_info["clients"])
        state = random.choice(div_info["states"])
        budget = round(random.uniform(50_000_000, 3_500_000_000), -6)
        manager = random.choice(MANAGERS)
        start = datetime.date(random.randint(2020, 2024), random.randint(1, 12), random.randint(1, 28))
        duration_months = random.randint(18, 72)
        completion = start + datetime.timedelta(days=duration_months * 30)
        proj_id = f"P-2024-{pid:03d}"
        proj_name = f"{site} - {ptype} Phase {random.randint(1,4)}"

        # Generate monthly EVM snapshots (12 months of reporting periods)
        reporting_months = []
        for m_offset in range(12):
            rp = datetime.date(2024, 1, 1) + datetime.timedelta(days=m_offset * 30)
            if rp.month > 12:
                rp = rp.replace(year=2025, month=rp.month - 12)
            # Progress fraction for this reporting period
            progress = min(1.0, (m_offset + 1) / 12.0)

            # Realistic EVM: most projects on track, some degrade over time
            roll = random.random()
            if roll < 0.12:
                spi = round(random.uniform(0.78, 0.95), 2)
                cpi = round(random.uniform(0.78, 0.92), 2)
                status = "red"
            elif roll < 0.32:
                spi = round(random.uniform(0.93, 1.03), 2)
                cpi = round(random.uniform(0.91, 1.01), 2)
                status = "amber"
            else:
                spi = round(random.uniform(0.97, 1.10), 2)
                cpi = round(random.uniform(0.97, 1.12), 2)
                status = "green"

            pv = round(budget * progress * random.uniform(0.85, 1.0), -3)
            ev = round(pv * spi, -3)
            ac = round(ev / cpi, -3) if cpi > 0 else round(ev * 1.1, -3)
            cv_pct = round((ev - ac) / ev * 100, 1) if ev > 0 else 0.0

            reporting_months.append(rp)

            projects.append(dict(
                project_id=proj_id,
                project_name=proj_name,
                division=div_name,
                client=client,
                project_type=ptype,
                state=state,
                budget_aud=float(budget),
                actual_cost_aud=float(ac),
                earned_value_aud=float(ev),
                planned_value_aud=float(pv),
                cost_variance_pct=float(cv_pct),
                spi=float(spi),
                cpi=float(cpi),
                status=status,
                start_date=start,
                planned_completion=completion,
                reporting_period=rp,
                project_manager=manager,
            ))
        pid += 1

df_projects = _to_spark(projects, "financials")
df_projects.write.mode("overwrite").saveAsTable(f"{catalog}.projects.financials")
print(f"[OK] {catalog}.projects.financials: {df_projects.count()} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Generate Equipment Telemetry

# COMMAND ----------

# Build equipment fleet
fleet = []
eq_id = 1
for etype in EQUIPMENT_TYPES:
    prefix = EQUIPMENT_PREFIXES[etype]
    count = random.randint(5, 15)
    for i in range(count):
        fleet.append((f"{prefix}-{eq_id:03d}", etype, random.choice(ALL_SITES)))
        eq_id += 1

telemetry = []
base_ts = datetime.datetime(2025, 4, 1, 6, 0, 0)
for _ in range(NUM_TELEMETRY):
    eq_id_str, etype, site = random.choice(fleet)
    division = SITE_TO_DIVISION[site]
    hours = random.randint(500, 20000)

    # Status distribution
    roll = random.random()
    if roll < 0.05:
        status = "critical"
        temp = round(random.uniform(110, 130), 1)
        fuel = round(random.uniform(5, 25), 1)
    elif roll < 0.15:
        status = "warning"
        temp = round(random.uniform(95, 115), 1)
        fuel = round(random.uniform(15, 45), 1)
    elif roll < 0.20:
        status = "maintenance"
        temp = round(random.uniform(20, 40), 1)
        fuel = round(random.uniform(30, 80), 1)
    else:
        status = "operational"
        temp = round(random.uniform(70, 95), 1)
        fuel = round(random.uniform(30, 100), 1)

    ts = base_ts + datetime.timedelta(
        days=random.randint(0, 13),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )
    maint_due = (ts + datetime.timedelta(days=random.randint(1, 90))).date()

    telemetry.append(dict(
        equipment_id=eq_id_str,
        equipment_type=etype,
        site_name=site,
        division=division,
        engine_temp_celsius=float(temp),
        fuel_level_pct=float(fuel),
        operating_hours=int(hours),
        maintenance_due_date=maint_due,
        status=status,
        reading_timestamp=ts,
    ))

df_telemetry = _to_spark(telemetry, "equipment_telemetry")

# Use INSERT OVERWRITE if external table
try:
    tbl_type = spark.sql(f"DESCRIBE DETAIL {catalog}.equipment.equipment_telemetry").collect()[0].type
except Exception:
    tbl_type = "MANAGED"

if tbl_type == "EXTERNAL":
    df_telemetry.createOrReplaceTempView("_tmp_telemetry")
    spark.sql(f"INSERT OVERWRITE {catalog}.equipment.equipment_telemetry SELECT * FROM _tmp_telemetry")
else:
    df_telemetry.write.mode("overwrite").saveAsTable(f"{catalog}.equipment.equipment_telemetry")

print(f"[OK] {catalog}.equipment.equipment_telemetry: {df_telemetry.count()} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Generate Safety Incidents

# COMMAND ----------

incidents = []
for i in range(NUM_INCIDENTS):
    site = random.choice(ALL_SITES)
    division = SITE_TO_DIVISION[site]
    severity = random.choices(SEVERITIES, weights=SEVERITY_WEIGHTS, k=1)[0]
    itype = random.choice(INCIDENT_TYPES)
    idate = datetime.date(2025, 1, 1) + datetime.timedelta(days=random.randint(0, 100))

    if severity == "Critical":
        injuries = random.randint(1, 3)
        ltd = round(random.uniform(5, 30), 1)
    elif severity == "Serious":
        injuries = random.randint(0, 2)
        ltd = round(random.uniform(1, 10), 1)
    elif severity == "Moderate":
        injuries = random.randint(0, 1)
        ltd = round(random.uniform(0, 5), 1)
    else:
        injuries = 0
        ltd = 0.0

    root = random.choice(ROOT_CAUSES)
    # Corrective actions keyed to root cause
    actions = {
        "human_error": "Retraining and toolbox talk delivered",
        "equipment_failure": "Equipment inspection schedule accelerated",
        "procedural": "SWMS updated and re-briefed",
        "environmental": "Environmental controls reviewed and upgraded",
        "design": "Design review initiated with engineering team",
        "poor_housekeeping": "Housekeeping audit implemented for area",
        "inadequate_training": "Mandatory competency assessment added",
    }

    status_roll = random.random()
    if idate < datetime.date(2025, 3, 1):
        inv_status = "closed" if status_roll < 0.85 else "investigating"
    else:
        inv_status = random.choice(["open", "investigating", "closed"])

    incidents.append(dict(
        incident_id=f"INC-2025-{i+1:04d}",
        incident_date=idate,
        site_name=site,
        division=division,
        incident_type=itype,
        severity=severity,
        description=f"{itype} incident at {site}: {severity.lower()} severity event during {random.choice(['day', 'night', 'afternoon'])} shift",
        injuries=int(injuries),
        lost_time_days=float(ltd),
        root_cause=root,
        corrective_action=actions[root],
        status=inv_status,
    ))

df_incidents = _to_spark(incidents, "incidents")
df_incidents.write.mode("overwrite").saveAsTable(f"{catalog}.safety.incidents")
print(f"[OK] {catalog}.safety.incidents: {df_incidents.count()} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Generate Procurement Materials

# COMMAND ----------

materials = []
mid = 1
for _ in range(NUM_MATERIALS):
    category = random.choice(list(MATERIAL_CATEGORIES.keys()))
    mat_name, price_lo, price_hi, unit = random.choice(MATERIAL_CATEGORIES[category])
    supplier = random.choice(SUPPLIERS[category])
    price = round(random.uniform(price_lo, price_hi), 2)
    lead_time = random.randint(1, 35)
    last_order = datetime.date(2025, random.randint(1, 4), random.randint(1, 28))

    # Qty varies by unit type
    qty_map = {"tonne": (50, 2000), "cubic_meter": (100, 5000), "litre": (1000, 500000),
               "square_meter": (500, 100000), "segment": (20, 300), "set": (5, 50),
               "unit": (10, 1000), "each": (10, 500), "pair": (50, 500),
               "sheet": (100, 2000), "metre": (500, 10000)}
    lo, hi = qty_map.get(unit, (10, 500))
    qty = float(random.randint(lo, hi))

    trend_roll = random.random()
    if trend_roll < 0.25:
        trend = "increasing"
    elif trend_roll < 0.85:
        trend = "stable"
    else:
        trend = "decreasing"

    avail_roll = random.random()
    if avail_roll < 0.60:
        avail = "good"
    elif avail_roll < 0.85:
        avail = "moderate"
    elif avail_roll < 0.97:
        avail = "limited"
    else:
        avail = "out_of_stock"

    materials.append(dict(
        material_id=f"MAT-{mid:04d}",
        material_name=mat_name,
        category=category,
        supplier=supplier,
        unit_price_aud=float(price),
        unit=unit,
        lead_time_days=int(lead_time),
        last_order_date=last_order,
        last_order_qty=float(qty),
        price_trend=trend,
        availability=avail,
    ))
    mid += 1

df_materials = _to_spark(materials, "materials")

# Use INSERT OVERWRITE for Iceberg tables
try:
    props = spark.sql(f"SHOW TBLPROPERTIES {catalog}.procurement.materials").collect()
    is_iceberg = any("iceberg" in str(r).lower() for r in props)
except Exception:
    is_iceberg = False

if is_iceberg:
    df_materials.createOrReplaceTempView("_tmp_materials")
    spark.sql(f"INSERT OVERWRITE {catalog}.procurement.materials SELECT * FROM _tmp_materials")
else:
    df_materials.write.mode("overwrite").saveAsTable(f"{catalog}.procurement.materials")

print(f"[OK] {catalog}.procurement.materials: {df_materials.count()} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

for tbl in ["projects.financials", "equipment.equipment_telemetry",
            "safety.incidents", "procurement.materials"]:
    count = spark.sql(f"SELECT COUNT(*) AS cnt FROM {catalog}.{tbl}").collect()[0].cnt
    print(f"  {catalog}.{tbl}: {count} rows")

print(f"\nData generation complete for {customer}.")
