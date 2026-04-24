#!/usr/bin/env python3
"""
Populate Fabric Lakehouse — Contoso AI Workshop

Creates pre-aggregated KPI tables in contoso_lakehouse for the Semantic Model.
Run as a Fabric Spark notebook OR locally to generate the data as Parquet/CSV.

Tables created:
  - ProjectKPIs    (4 rows — division-level project health)
  - SafetyKPIs     (48 rows — monthly safety metrics by division)
  - FleetKPIs      (4 rows — division-level fleet health)

Usage:
  # Option A: Upload to Fabric as notebook and run
  # Option B: Run locally to generate Parquet files
  python fabric/scripts/03_populate_lakehouse.py --output-dir fabric/notebooks/lakehouse_data/
"""

import random, datetime, os, sys, json

random.seed(42)

DIVISIONS = ["Division-Alpha", "Division-Beta", "Division-Gamma", "Division-Delta"]

DIVISION_PROFILES = {
    "Division-Alpha": {
        "project_count": 15, "cpi_mean": 0.95, "spi_mean": 0.92,
        "budget_total": 28.5e9, "fleet_count": 45, "fleet_op_pct": 0.88,
        "incident_base": 35, "maint_cost_base": 2500000,
    },
    "Division-Beta": {
        "project_count": 12, "cpi_mean": 1.02, "spi_mean": 0.98,
        "budget_total": 14.4e9, "fleet_count": 60, "fleet_op_pct": 0.91,
        "incident_base": 28, "maint_cost_base": 3200000,
    },
    "Division-Gamma": {
        "project_count": 10, "cpi_mean": 0.98, "spi_mean": 1.01,
        "budget_total": 4.5e9, "fleet_count": 25, "fleet_op_pct": 0.85,
        "incident_base": 18, "maint_cost_base": 1100000,
    },
    "Division-Delta": {
        "project_count": 5, "cpi_mean": 1.05, "spi_mean": 1.03,
        "budget_total": 15.0e9, "fleet_count": 10, "fleet_op_pct": 0.95,
        "incident_base": 8, "maint_cost_base": 400000,
    },
}


def generate_project_kpis():
    """Division-level project health summary."""
    rows = []
    for div in DIVISIONS:
        p = DIVISION_PROFILES[div]
        actual = p["budget_total"] * (1 / p["cpi_mean"])
        red_count = max(1, int(p["project_count"] * random.uniform(0.10, 0.20)))
        rows.append({
            "division": div,
            "total_budget": round(p["budget_total"], 0),
            "total_actual_cost": round(actual, 0),
            "avg_cpi": p["cpi_mean"],
            "avg_spi": p["spi_mean"],
            "project_count": p["project_count"],
            "red_projects": red_count,
        })
    return rows


def generate_safety_kpis():
    """Monthly safety metrics by division (12 months × 4 divisions)."""
    rows = []
    base_date = datetime.date(2025, 1, 1)
    for month_offset in range(12):
        month = base_date + datetime.timedelta(days=month_offset * 30)
        month_str = month.strftime("%Y-%m-01")
        for div in DIVISIONS:
            p = DIVISION_PROFILES[div]
            seasonal = 1.0 + 0.1 * (month_offset % 3 - 1)
            incidents = max(0, int(p["incident_base"] * seasonal * random.uniform(0.7, 1.3)))
            near_misses = int(incidents * 0.25)
            ltis = max(0, incidents - near_misses - int(incidents * random.uniform(0.3, 0.5)))
            lost_time = round(ltis * random.uniform(1.0, 5.0), 1)
            rows.append({
                "division": div,
                "month": month_str,
                "total_incidents": incidents,
                "near_misses": near_misses,
                "ltis": ltis,
                "lost_time_days": lost_time,
            })
    return rows


def generate_fleet_kpis():
    """Division-level fleet health summary."""
    rows = []
    for div in DIVISIONS:
        p = DIVISION_PROFILES[div]
        operational = int(p["fleet_count"] * p["fleet_op_pct"])
        breakdowns = max(0, int(p["fleet_count"] * random.uniform(0.05, 0.15)))
        rows.append({
            "division": div,
            "total_equipment": p["fleet_count"],
            "operational_count": operational,
            "availability_pct": round(p["fleet_op_pct"] * 100, 1),
            "total_maintenance_cost": round(p["maint_cost_base"] * 12, 0),
            "breakdown_count": breakdowns,
        })
    return rows


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate Lakehouse KPI tables for Contoso semantic model")
    parser.add_argument("--output-dir", default=None,
                        help="Directory to write CSV files (default: fabric/notebooks/lakehouse_data/)")
    parser.add_argument("--format", choices=["csv", "spark"], default="csv",
                        help="Output format: csv (local) or spark (Fabric notebook)")
    parser.add_argument("--config", default=os.path.join(os.path.dirname(__file__), "config.json"),
                        help="Path to config.json from 01_deploy_workspace.py (default: fabric/scripts/config.json)")
    parser.add_argument("--lakehouse-name", default=None,
                        help="Lakehouse name for Spark saveAsTable (env: FABRIC_LAKEHOUSE_NAME, default: contoso_lakehouse)")
    args = parser.parse_args()

    # Resolve lakehouse name: CLI arg > env var > config.json > default
    lakehouse_name = args.lakehouse_name or os.environ.get("FABRIC_LAKEHOUSE_NAME")
    if not lakehouse_name and os.path.exists(args.config):
        try:
            with open(args.config) as f:
                config = json.load(f)
            lakehouse_name = config.get("items", {}).get("lakehouse", {}).get("name")
            print(f"[INFO] Loaded lakehouse name from {args.config}")
        except (json.JSONDecodeError, KeyError):
            pass
    if not lakehouse_name:
        lakehouse_name = "contoso_lakehouse"

    # Resolve output dir
    if not args.output_dir:
        args.output_dir = os.path.join(os.path.dirname(__file__), "..", "notebooks", "lakehouse_data")

    project_kpis = generate_project_kpis()
    safety_kpis = generate_safety_kpis()
    fleet_kpis = generate_fleet_kpis()

    if args.format == "spark":
        # Running inside Fabric Spark notebook
        try:
            from pyspark.sql import SparkSession
            spark = SparkSession.builder.getOrCreate()

            spark.createDataFrame(project_kpis).write.mode("overwrite").format("delta").saveAsTable(f"{lakehouse_name}.ProjectKPIs")
            print(f"[OK] ProjectKPIs → {lakehouse_name}")

            spark.createDataFrame(safety_kpis).write.mode("overwrite").format("delta").saveAsTable(f"{lakehouse_name}.SafetyKPIs")
            print(f"[OK] SafetyKPIs → {lakehouse_name}")

            spark.createDataFrame(fleet_kpis).write.mode("overwrite").format("delta").saveAsTable(f"{lakehouse_name}.FleetKPIs")
            print(f"[OK] FleetKPIs → {lakehouse_name}")

            print(f"\n[OK] All 3 tables written to {lakehouse_name}")
        except ImportError:
            print("[WARN] PySpark not available — falling back to CSV output")
            args.format = "csv"

    if args.format == "csv":
        import csv
        os.makedirs(args.output_dir, exist_ok=True)

        tables = {
            "ProjectKPIs.csv": project_kpis,
            "SafetyKPIs.csv": safety_kpis,
            "FleetKPIs.csv": fleet_kpis,
        }

        for filename, data in tables.items():
            filepath = os.path.join(args.output_dir, filename)
            with open(filepath, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            print(f"[OK] {filename} ({len(data)} rows) → {filepath}")

        print(f"\n[OK] CSV files written to {args.output_dir}")
        print(f"  Upload to Fabric Lakehouse via:")
        print(f"    1. Fabric portal → {lakehouse_name} → Upload files")
        print(f"    2. Or use the Fabric notebook: fabric/notebooks/populate_lakehouse.py")


if __name__ == "__main__":
    main()
