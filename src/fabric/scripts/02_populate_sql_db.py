#!/usr/bin/env python3
"""
Populate Fabric SQL Database — Contoso AI Workshop

Generates a SQL script (DDL + INSERT statements) with Contoso summary data.
Data uses same random.seed(42) distributions as databricks/src/02_generate_data.py.

Tables populated:
  - dbo.division_summary     (4 rows — one per division)
  - dbo.monthly_kpis         (48 rows — 12 months × 4 divisions)
  - dbo.manufacturing_kpis   (48 rows — unique to SQL DB, not in mirrored catalog)
  - dbo.supplier_scorecard   (20 rows — unique to SQL DB, shows multi-source value)

Usage:
  az login --tenant <YOUR_TENANT_ID>
  python fabric/scripts/02_populate_sql_db.py
  python fabric/scripts/02_populate_sql_db.py --workspace-id <ws-id> --sqldb-id <db-id>

The generated SQL file can be copy-pasted into the Fabric SQL editor for execution.
If IDs not provided, reads from fabric/scripts/config.json (output of 01_deploy_workspace.py).
"""

import argparse, json, os, random, datetime

random.seed(42)

DIVISIONS = ["Division-Alpha", "Division-Beta", "Division-Gamma", "Division-Delta"]

# Division profiles (consistent with databricks/src/02_generate_data.py distributions)
DIVISION_PROFILES = {
    "Division-Alpha": {
        "project_count": 15, "budget_range": (500e6, 3.5e9), "cpi_mean": 0.95, "spi_mean": 0.92,
        "fleet_count": 45, "fleet_op_pct": 0.88, "incident_base": 35, "exceedance_base": 8,
        "throughput_tonnes": 250000, "utilisation_pct": 0.82, "energy_cost_base": 450000,
    },
    "Division-Beta": {
        "project_count": 12, "budget_range": (200e6, 2.0e9), "cpi_mean": 1.02, "spi_mean": 0.98,
        "fleet_count": 60, "fleet_op_pct": 0.91, "incident_base": 28, "exceedance_base": 12,
        "throughput_tonnes": 800000, "utilisation_pct": 0.87, "energy_cost_base": 680000,
    },
    "Division-Gamma": {
        "project_count": 10, "budget_range": (100e6, 800e6), "cpi_mean": 0.98, "spi_mean": 1.01,
        "fleet_count": 25, "fleet_op_pct": 0.85, "incident_base": 18, "exceedance_base": 15,
        "throughput_tonnes": 400000, "utilisation_pct": 0.79, "energy_cost_base": 320000,
    },
    "Division-Delta": {
        "project_count": 5, "budget_range": (1.0e9, 5.0e9), "cpi_mean": 1.05, "spi_mean": 1.03,
        "fleet_count": 10, "fleet_op_pct": 0.95, "incident_base": 8, "exceedance_base": 3,
        "throughput_tonnes": 50000, "utilisation_pct": 0.92, "energy_cost_base": 120000,
    },
}

SUPPLIERS = [
    ("Boral Construction Materials", "Division-Alpha", "Concrete & Aggregates"),
    ("Holcim Australia", "Division-Alpha", "Cement"),
    ("Liberty Steel", "Division-Alpha", "Structural Steel"),
    ("Coates Hire", "Division-Alpha", "Equipment Rental"),
    ("Orica Mining Services", "Division-Beta", "Explosives & Blasting"),
    ("Sandvik Mining", "Division-Beta", "Mining Equipment"),
    ("Caterpillar Australia", "Division-Beta", "Heavy Equipment"),
    ("Komatsu", "Division-Beta", "Haul Trucks"),
    ("Weir Minerals", "Division-Beta", "Wear Parts"),
    ("FLSmidth", "Division-Gamma", "Processing Equipment"),
    ("Metso Outotec", "Division-Gamma", "Crushers & Screens"),
    ("Nalco Water", "Division-Gamma", "Water Treatment"),
    ("Atlas Copco", "Division-Gamma", "Compressors"),
    ("Siemens Energy", "Division-Gamma", "Electrical Systems"),
    ("Transurban Materials", "Division-Delta", "Toll Systems"),
    ("AECOM Consulting", "Division-Delta", "Engineering Services"),
    ("John Holland Supply", "Division-Alpha", "Subcontracting"),
    ("Downer EDI", "Division-Beta", "Site Services"),
    ("Monadelphous", "Division-Gamma", "Mechanical Services"),
    ("Lendlease Engineering", "Division-Delta", "Joint Venture"),
]


def generate_division_summary():
    """Generate division_summary INSERT statements."""
    rows = []
    for div in DIVISIONS:
        p = DIVISION_PROFILES[div]
        budget = sum(random.uniform(*p["budget_range"]) for _ in range(p["project_count"]))
        actual = budget * (1 / p["cpi_mean"])
        red_count = max(1, int(p["project_count"] * 0.15))
        rows.append(
            f"('{div}', {budget:.0f}, {actual:.0f}, {p['cpi_mean']:.2f}, {p['spi_mean']:.2f}, "
            f"{p['project_count']}, {red_count}, {p['fleet_count']}, {p['fleet_op_pct']:.2f}, "
            f"{p['incident_base'] * 12}, {p['exceedance_base'] * 12})"
        )
    return (
        "INSERT INTO dbo.division_summary "
        "(division, total_budget, total_actual_cost, avg_cpi, avg_spi, "
        "project_count, red_projects, fleet_count, fleet_operational_pct, "
        "incident_count, exceedance_count) VALUES\n" +
        ",\n".join(rows) + ";"
    )


def generate_monthly_kpis():
    """Generate monthly_kpis INSERT statements (12 months × 4 divisions)."""
    rows = []
    base_date = datetime.date(2025, 1, 1)
    for month_offset in range(12):
        year = base_date.year + (base_date.month + month_offset - 1) // 12
        month_num = (base_date.month + month_offset - 1) % 12 + 1
        month_str = f"{year}-{month_num:02d}-01"
        for div in DIVISIONS:
            p = DIVISION_PROFILES[div]
            seasonal = 1.0 + 0.1 * (month_offset % 3 - 1)  # seasonal variation
            budget = sum(random.uniform(*p["budget_range"]) for _ in range(p["project_count"])) / 12 * seasonal
            actual = budget * (1 / p["cpi_mean"]) * random.uniform(0.95, 1.05)
            incidents = max(0, int(p["incident_base"] * seasonal * random.uniform(0.7, 1.3)))
            near_misses = int(incidents * 0.25)
            lost_time = round(incidents * random.uniform(0.5, 2.0), 1)
            inspections_total = random.randint(40, 80)
            passed = int(inspections_total * random.uniform(0.85, 0.98))
            failed = inspections_total - passed
            exceedances = max(0, int(p["exceedance_base"] * random.uniform(0.5, 1.5)))
            rows.append(
                f"('{month_str}', '{div}', {budget:.0f}, {actual:.0f}, "
                f"{incidents}, {near_misses}, {lost_time}, {passed}, {failed}, {exceedances})"
            )
    return (
        "INSERT INTO dbo.monthly_kpis "
        "(month, division, budget_aud, actual_cost_aud, incidents, near_misses, "
        "lost_time_days, inspections_passed, inspections_failed, exceedances) VALUES\n" +
        ",\n".join(rows) + ";"
    )


def generate_manufacturing_kpis():
    """Generate manufacturing_kpis INSERT statements — unique to Fabric SQL DB."""
    rows = []
    base_date = datetime.date(2025, 1, 1)
    for month_offset in range(12):
        year = base_date.year + (base_date.month + month_offset - 1) // 12
        month_num = (base_date.month + month_offset - 1) % 12 + 1
        month_str = f"{year}-{month_num:02d}-01"
        for div in DIVISIONS:
            p = DIVISION_PROFILES[div]
            seasonal = 1.0 + 0.08 * (month_offset % 4 - 2)
            throughput = p["throughput_tonnes"] * seasonal * random.uniform(0.9, 1.1)
            utilisation = min(1.0, p["utilisation_pct"] * random.uniform(0.95, 1.05))
            downtime = random.uniform(5, 40) * (1 - utilisation) * 10
            energy = p["energy_cost_base"] * seasonal * random.uniform(0.9, 1.1)
            waste = random.uniform(0.02, 0.08)
            rows.append(
                f"('{month_str}', '{div}', {throughput:.0f}, {utilisation:.2f}, "
                f"{downtime:.1f}, {energy:.0f}, {waste:.3f})"
            )
    return (
        "INSERT INTO dbo.manufacturing_kpis "
        "(month, division, throughput_tonnes, utilisation_pct, unplanned_downtime_hrs, "
        "energy_cost_aud, waste_pct) VALUES\n" +
        ",\n".join(rows) + ";"
    )


def generate_supplier_scorecard():
    """Generate supplier_scorecard INSERT statements — unique to Fabric SQL DB."""
    rows = []
    for supplier, division, category in SUPPLIERS:
        spend = random.uniform(500000, 50000000)
        otd = random.uniform(0.75, 0.99)
        quality = random.uniform(3.0, 5.0)
        status = random.choice(["Active", "Active", "Active", "Under Review", "Expiring Soon"])
        review_date = datetime.date(2025, random.randint(1, 12), random.randint(1, 28))
        rows.append(
            f"('{supplier}', '{division}', '{category}', {spend:.0f}, {otd:.2f}, "
            f"{quality:.1f}, '{status}', '{review_date.isoformat()}')"
        )
    return (
        "INSERT INTO dbo.supplier_scorecard "
        "(supplier_name, division, category, total_spend_aud, on_time_delivery_pct, "
        "quality_score, contract_status, last_review_date) VALUES\n" +
        ",\n".join(rows) + ";"
    )


def build_full_sql():
    """Build complete SQL script: DDL + INSERT statements."""
    # Read DDL from config or define inline
    ddl = """
-- ============================================================
-- Contoso Fabric SQL Database — Full Population Script
-- Generated by fabric/scripts/02_populate_sql_db.py
-- NOTE: No PRIMARY KEY constraints (not supported in Fabric SQL DB)
-- ============================================================

-- Division-level summary
DROP TABLE IF EXISTS dbo.division_summary;
CREATE TABLE dbo.division_summary (
    division VARCHAR(100) NOT NULL,
    total_budget FLOAT,
    total_actual_cost FLOAT,
    avg_cpi FLOAT,
    avg_spi FLOAT,
    project_count INT,
    red_projects INT,
    fleet_count INT,
    fleet_operational_pct FLOAT,
    incident_count INT,
    exceedance_count INT,
    last_updated DATETIME2(6)
);

-- Monthly KPIs by division
DROP TABLE IF EXISTS dbo.monthly_kpis;
CREATE TABLE dbo.monthly_kpis (
    month DATE NOT NULL,
    division VARCHAR(100) NOT NULL,
    budget_aud FLOAT,
    actual_cost_aud FLOAT,
    incidents INT,
    near_misses INT,
    lost_time_days FLOAT,
    inspections_passed INT,
    inspections_failed INT,
    exceedances INT
);

-- Manufacturing KPIs (UNIQUE TO SQL DB — not in mirrored catalog)
DROP TABLE IF EXISTS dbo.manufacturing_kpis;
CREATE TABLE dbo.manufacturing_kpis (
    month DATE NOT NULL,
    division VARCHAR(100) NOT NULL,
    throughput_tonnes FLOAT,
    utilisation_pct FLOAT,
    unplanned_downtime_hrs FLOAT,
    energy_cost_aud FLOAT,
    waste_pct FLOAT
);

-- Supplier scorecard (UNIQUE TO SQL DB — shows multi-source value)
DROP TABLE IF EXISTS dbo.supplier_scorecard;
CREATE TABLE dbo.supplier_scorecard (
    supplier_name VARCHAR(200) NOT NULL,
    division VARCHAR(100) NOT NULL,
    category VARCHAR(100),
    total_spend_aud FLOAT,
    on_time_delivery_pct FLOAT,
    quality_score FLOAT,
    contract_status VARCHAR(50),
    last_review_date DATE
);

-- ============================================================
-- DATA POPULATION
-- ============================================================

"""
    ddl += generate_division_summary() + "\n\n"
    ddl += generate_monthly_kpis() + "\n\n"
    ddl += generate_manufacturing_kpis() + "\n\n"
    ddl += generate_supplier_scorecard() + "\n"

    return ddl


def main():
    parser = argparse.ArgumentParser(description="Populate Fabric SQL Database with Contoso data")
    parser.add_argument("--workspace-id", help="Fabric workspace ID (env: FABRIC_WORKSPACE_ID)")
    parser.add_argument("--sqldb-id", help="Fabric SQL Database ID (env: FABRIC_SQLDB_ID)")
    parser.add_argument("--config", default=os.path.join(os.path.dirname(__file__), "config.json"),
                        help="Path to config.json from 01_deploy_workspace.py (default: fabric/scripts/config.json)")
    parser.add_argument("--output-sql", default=os.path.join(os.path.dirname(__file__), "..", "notebooks", "populate_sql_database.sql"),
                        help="Also write SQL to file")
    args = parser.parse_args()

    # Resolve IDs: CLI arg > env var > config.json
    if not args.workspace_id:
        args.workspace_id = os.environ.get("FABRIC_WORKSPACE_ID")
    if not args.sqldb_id:
        args.sqldb_id = os.environ.get("FABRIC_SQLDB_ID")

    # Try to load IDs from config.json if still not provided
    if (not args.workspace_id or not args.sqldb_id) and os.path.exists(args.config):
        with open(args.config) as f:
            config = json.load(f)
        if not args.workspace_id:
            args.workspace_id = config["workspace"]["id"]
        if not args.sqldb_id:
            args.sqldb_id = config["items"]["sql_database"]["id"]
        print(f"[INFO] Loaded IDs from {args.config}")

    # Generate SQL
    full_sql = build_full_sql()

    # Write SQL file for manual use
    if args.output_sql:
        os.makedirs(os.path.dirname(args.output_sql), exist_ok=True)
        with open(args.output_sql, "w") as f:
            f.write(full_sql)
        print(f"[OK] SQL written to {args.output_sql}")

    # Provide instructions for manual execution
    if args.workspace_id and args.sqldb_id:
        print(f"\n[INFO] To populate the Fabric SQL Database:")
        print(f"  Workspace: {args.workspace_id}")
        print(f"  SQL DB:    {args.sqldb_id}")
        print(f"  1. Open Fabric portal → SQL Database 'contoso_sqldb'")
        print(f"  2. Click 'New Query'")
        print(f"  3. Paste contents of: {args.output_sql}")
        print(f"  4. Click 'Run'")
    else:
        print(f"\n[INFO] No workspace/sqldb IDs — SQL file written only")
        print(f"  Run 01_deploy_workspace.py first, or provide --workspace-id and --sqldb-id")

    print(f"\n[OK] Done. Tables: division_summary, monthly_kpis, manufacturing_kpis, supplier_scorecard")
    print(f"  Total rows: 4 + 48 + 48 + 20 = 120 rows")


if __name__ == "__main__":
    main()
