#!/usr/bin/env python3
"""
Fabric Workspace Deployment — CIMIC AI Workshop

Creates all Fabric workspace items for the Data Agent multi-source demo:
  - Lakehouse (cimic_lakehouse)
  - SQL Database (cimic_sqldb)
  - Semantic Model (CIMIC_KPI_Model)
  - Mirrored Databricks Catalog
  - 5 Data Agents (CIMIC Project Intelligence, Projects, Safety, Equipment, Procurement)
  - Notebooks (from fabric/notebooks/*.ipynb)

Follows patterns from microsoft/skills-for-fabric (sqldw-authoring, spark-authoring).

Usage:
  az login --tenant <YOUR_TENANT_ID>
  python fabric/scripts/01_deploy_workspace.py
  python fabric/scripts/01_deploy_workspace.py --workspace "CIMIC-ws-dev" --capacity "cimicws"

Prerequisites:
  - az CLI logged in
  - Fabric capacity provisioned
  - pip install requests
"""

import argparse, json, subprocess, sys, time, os, base64, re, warnings
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════
# Defaults — override via CLI args or env vars
# ═══════════════════════════════════════════════════════════════════════
DEFAULTS = {
    "workspace_name": os.environ.get("FABRIC_WORKSPACE", "ws_cimic_aiws_dev"),
    "capacity_name": os.environ.get("FABRIC_CAPACITY", "cimicws"),
    "dbx_host": os.environ.get("DBX_HOST", "adb-7405614861019645.5.azuredatabricks.net"),
    "dbx_catalog": os.environ.get("DBX_CATALOG", "cimic"),
}


# ═══════════════════════════════════════════════════════════════════════
# Agent instruction file parser
# Reads .md files from fabric/agents/ to externalise agent instructions
# ═══════════════════════════════════════════════════════════════════════
# Maps each agent display name to its markdown filename (without .md)
AGENT_FILE_MAP = {
    "CIMIC Project Intelligence": "project-intelligence",
    "Projects Agent": "projects",
    "Safety Agent": "safety",
    "Equipment Agent": "equipment",
    "Procurement Agent": "procurement",
}


def parse_agent_file(path: Path) -> dict:
    """Parse an agent markdown file and extract instructions, data source
    instructions, and example questions.

    Expected format:
        ## Agent Instructions
        <optional preamble>
        ```
        <agent instructions text>
        ```

        ## Data Source Instructions
        ### Source: <label>
        ```
        <data source instructions>
        ```
        (repeats for each source)

        ## Example Questions
        - question 1
        - question 2
    """
    text = path.read_text(encoding="utf-8")

    result = {
        "instructions": None,
        "data_source_instructions": [],
        "example_questions": [],
    }

    # --- Agent Instructions: first code block under ## Agent Instructions ---
    ai_match = re.search(
        r"^## Agent Instructions\b.*?\n```[^\n]*\n(.*?)```",
        text, re.MULTILINE | re.DOTALL,
    )
    if ai_match:
        result["instructions"] = ai_match.group(1).strip()

    # --- Data Source Instructions: each code block under ## Data Source Instructions ---
    ds_section = re.split(r"^## ", text, flags=re.MULTILINE)
    for section in ds_section:
        if section.startswith("Data Source Instructions"):
            for block in re.finditer(r"```[^\n]*\n(.*?)```", section, re.DOTALL):
                result["data_source_instructions"].append(block.group(1).strip())
            break

    # --- Example Questions: bullet items under ## Example Questions ---
    eq_match = re.search(
        r"^## Example Questions\b[^\n]*\n\s*\n?((?:[-*]\s+.+\n?)+)",
        text, re.MULTILINE,
    )
    if eq_match:
        for line in eq_match.group(1).strip().splitlines():
            line = line.strip()
            if line.startswith(("- ", "* ")):
                result["example_questions"].append(line[2:].strip())

    return result


def load_agent_overrides(agents_dir: Path) -> dict:
    """Load all available agent override files. Returns {agent_name: parsed_dict}."""
    overrides = {}
    for agent_name, file_stem in AGENT_FILE_MAP.items():
        md_path = agents_dir / f"{file_stem}.md"
        if md_path.is_file():
            try:
                parsed = parse_agent_file(md_path)
                if parsed["instructions"]:
                    overrides[agent_name] = parsed
                    print(f"   [OK] Loaded instructions: {md_path.name}")
                else:
                    print(f"   [WARN] No instructions found in {md_path.name}, using embedded default")
            except Exception as exc:
                print(f"   [WARN] Failed to parse {md_path.name}: {exc}, using embedded default")
        else:
            print(f"   [WARN] Agent file not found: {md_path}, using embedded default")
    return overrides


# ═══════════════════════════════════════════════════════════════════════
# Agent definitions — 5 agents matching Databricks Genie Spaces
# Mirrors Databricks Genie Spaces 1:1 for direct comparison
# ═══════════════════════════════════════════════════════════════════════
AGENTS = [
    {
        "name": "CIMIC Project Intelligence",
        "description": "Cross-domain operations intelligence covering project finance, safety, equipment, and procurement.",
        "sources": [
            "semantic_model:CIMIC_KPI_Model",
            "lakehouse:cimic_lakehouse",
            "sql_database:cimic_sqldb",
            "mirrored_catalog:projects.financials",
            "mirrored_catalog:safety.incidents",
            "mirrored_catalog:equipment.equipment_telemetry",
            "mirrored_catalog:procurement.materials",
        ],
        "instructions": (
            "You are a cross-domain operations intelligence assistant for CIMIC Group.\n\n"
            "DATA: Semantic model (pre-aggregated KPIs), Lakehouse (ProjectKPIs, SafetyKPIs, FleetKPIs), "
            "SQL database (division_summary, monthly_kpis, manufacturing_kpis, supplier_scorecard), "
            "and 4 mirrored Databricks tables (financials, incidents, equipment_telemetry, materials).\n\n"
            "TERMINOLOGY:\n"
            "- SPI = Schedule Performance Index (1.0 = on schedule)\n"
            "- CPI = Cost Performance Index (1.0 = on budget)\n"
            "- EAC = Estimate At Completion = budget / CPI\n"
            "- RAG = Red/Amber/Green status\n"
            "- LTI = Lost Time Injury\n"
            "- LTIFR = Lost Time Injury Frequency Rate\n\n"
            "RULES:\n"
            "- Lead with the most critical KPIs (red projects, critical equipment, safety)\n"
            "- Use the semantic model for pre-calculated metrics when available\n"
            "- Fall back to lakehouse/SQL for detailed drill-downs\n"
            "- Division is the common join key across domains\n"
            "- All monetary values in AUD with commas\n"
            "- Format for executive audience: concise, actionable, no jargon"
        ),
        "example_questions": [
            "Give me a cross-domain summary of portfolio health, safety, and fleet status",
            "What are the top 5 risks across all projects?",
            "Compare performance across divisions — finance, safety, and fleet",
            "Which divisions need attention this month?",
        ],
    },
    {
        "name": "Projects Agent",
        "description": "Answers questions about project budgets, EVM metrics (SPI/CPI/EAC), cost variance, and schedule performance.",
        "sources": ["mirrored_catalog:projects.financials"],
        "instructions": (
            "You are a project finance analyst for CIMIC Group.\n\n"
            "DATA: projects.financials table (1 table only).\n\n"
            "TERMINOLOGY:\n"
            "- SPI = Schedule Performance Index (1.0 = on schedule)\n"
            "- CPI = Cost Performance Index (1.0 = on budget)\n"
            "- EAC = Estimate At Completion = budget / CPI\n"
            "- RAG = Red/Amber/Green status\n\n"
            "RULES:\n"
            "- All monetary values in AUD with commas\n"
            "- Always include division when comparing\n"
            "- Flag red-status projects prominently\n"
            "- Round percentages to 1 decimal place"
        ),
        "example_questions": [
            "Show me all red-status projects",
            "What is the average CPI by division?",
            "Which projects are over budget?",
            "Total budget vs actual cost across all projects",
        ],
    },
    {
        "name": "Safety Agent",
        "description": "HSE incident analysis, severity trends, root cause patterns, and site safety performance.",
        "sources": [
            "mirrored_catalog:safety.incidents",
        ],
        "instructions": (
            "You are an HSE (Health Safety Environment) analyst for CIMIC Group.\n\n"
            "DATA: safety.incidents (1 table).\n\n"
            "TERMINOLOGY:\n"
            "- LTI = Lost Time Injury (lost_time_days > 0)\n"
            "- Near-miss = incident with 0 injuries but potential for harm\n"
            "- Severity: Critical, Serious, Moderate, Minor\n\n"
            "RULES:\n"
            "- Always separate near-misses from actual incidents in counts\n"
            "- For safety trends, use monthly grouping by default\n"
            "- Flag Critical severity incidents prominently\n"
            "- When showing incident counts, also show total injuries and lost time days"
        ),
        "example_questions": [
            "Show safety incidents trend by month",
            "Which sites have the worst safety record?",
            "What are the top root causes for incidents?",
            "Compare incident rates by division",
        ],
    },
    {
        "name": "Equipment Agent",
        "description": "Equipment health monitoring, temperature alerts, fleet utilisation, and maintenance scheduling.",
        "sources": [
            "mirrored_catalog:equipment.equipment_telemetry",
        ],
        "instructions": (
            "You are a fleet operations analyst for CIMIC Group.\n\n"
            "DATA: equipment.equipment_telemetry (1 table).\n\n"
            "TERMINOLOGY:\n"
            "- Engine temp normal: 70-95°C, warning: 95-110°C, critical: >110°C\n"
            "- Status: operational, warning, critical, maintenance\n"
            "- Fuel level 0-100%\n\n"
            "RULES:\n"
            "- For 'fleet health', show equipment with warning/critical status\n"
            "- Always show equipment_type when listing equipment\n"
            "- Flag critical temperature readings prominently\n"
            "- Show fuel levels below 20% as needing refuelling"
        ),
        "example_questions": [
            "Which equipment is in critical status?",
            "Average engine temperature by equipment type",
            "Show all equipment with overdue maintenance",
            "Fleet utilisation breakdown by division",
        ],
    },
    {
        "name": "Procurement Agent",
        "description": "Material pricing analysis, supplier performance, lead time monitoring, and supply chain risk assessment.",
        "sources": [
            "mirrored_catalog:procurement.materials",
        ],
        "instructions": (
            "You are a procurement analyst for CIMIC Group.\n\n"
            "DATA: procurement.materials (1 table).\n\n"
            "TERMINOLOGY:\n"
            "- Price trend: increasing, stable, decreasing\n"
            "- Availability: good, moderate, limited, out_of_stock\n"
            "- Lead time: days from order to delivery\n\n"
            "RULES:\n"
            "- Flag materials with increasing price AND limited availability as high-risk\n"
            "- For cost analysis, calculate total spend as unit_price_aud × last_order_qty\n"
            "- Lead time > 30 days = long-lead item\n"
            "- Show supplier and category in all material listings"
        ),
        "example_questions": [
            "Which materials have increasing price trends?",
            "Show all suppliers for steel products",
            "What materials have limited availability?",
            "Top 10 materials by estimated spend",
        ],
    },
]


# ═══════════════════════════════════════════════════════════════════════
# Semantic Model definition (TMSL / model.bim)
# ═══════════════════════════════════════════════════════════════════════
def build_semantic_model_tmsl(lakehouse_name):
    """Build a TMSL model.bim for Direct Lake over the CIMIC lakehouse."""
    return {
        "compatibilityLevel": 1604,
        "model": {
            "name": "CIMIC_KPI_Model",
            "culture": "en-AU",
            "tables": [
                {
                    "name": "ProjectKPIs",
                    "columns": [
                        {"name": "division", "dataType": "string", "sourceColumn": "division"},
                        {"name": "total_budget", "dataType": "double", "sourceColumn": "total_budget"},
                        {"name": "total_actual_cost", "dataType": "double", "sourceColumn": "total_actual_cost"},
                        {"name": "avg_cpi", "dataType": "double", "sourceColumn": "avg_cpi"},
                        {"name": "avg_spi", "dataType": "double", "sourceColumn": "avg_spi"},
                        {"name": "project_count", "dataType": "int64", "sourceColumn": "project_count"},
                        {"name": "red_projects", "dataType": "int64", "sourceColumn": "red_projects"},
                    ],
                    "partitions": [{
                        "name": "partition1",
                        "source": {
                            "type": "m",
                            "expression": (
                                f"let Source = Lakehouse.Contents(null),\n"
                                f"    nav = Source{{[workspaceName=\"#workspace#\"]}}[Data],\n"
                                f"    lh = nav{{[lakehouseName=\"{lakehouse_name}\"]}}[Data]\n"
                                f"in lh"
                            )
                        }
                    }],
                },
                {
                    "name": "SafetyKPIs",
                    "columns": [
                        {"name": "division", "dataType": "string", "sourceColumn": "division"},
                        {"name": "month", "dataType": "dateTime", "sourceColumn": "month"},
                        {"name": "total_incidents", "dataType": "int64", "sourceColumn": "total_incidents"},
                        {"name": "near_misses", "dataType": "int64", "sourceColumn": "near_misses"},
                        {"name": "ltis", "dataType": "int64", "sourceColumn": "ltis"},
                        {"name": "lost_time_days", "dataType": "double", "sourceColumn": "lost_time_days"},
                    ],
                    "partitions": [{
                        "name": "partition1",
                        "source": {
                            "type": "m",
                            "expression": (
                                f"let Source = Lakehouse.Contents(null),\n"
                                f"    nav = Source{{[workspaceName=\"#workspace#\"]}}[Data],\n"
                                f"    lh = nav{{[lakehouseName=\"{lakehouse_name}\"]}}[Data]\n"
                                f"in lh"
                            )
                        }
                    }],
                },
                {
                    "name": "FleetKPIs",
                    "columns": [
                        {"name": "division", "dataType": "string", "sourceColumn": "division"},
                        {"name": "total_equipment", "dataType": "int64", "sourceColumn": "total_equipment"},
                        {"name": "operational_count", "dataType": "int64", "sourceColumn": "operational_count"},
                        {"name": "availability_pct", "dataType": "double", "sourceColumn": "availability_pct"},
                        {"name": "total_maintenance_cost", "dataType": "double", "sourceColumn": "total_maintenance_cost"},
                        {"name": "breakdown_count", "dataType": "int64", "sourceColumn": "breakdown_count"},
                    ],
                    "partitions": [{
                        "name": "partition1",
                        "source": {
                            "type": "m",
                            "expression": (
                                f"let Source = Lakehouse.Contents(null),\n"
                                f"    nav = Source{{[workspaceName=\"#workspace#\"]}}[Data],\n"
                                f"    lh = nav{{[lakehouseName=\"{lakehouse_name}\"]}}[Data]\n"
                                f"in lh"
                            )
                        }
                    }],
                },
            ],
            "measures": [
                {
                    "name": "Portfolio Health Score",
                    "table": "ProjectKPIs",
                    "expression": "AVERAGEX(ProjectKPIs, (ProjectKPIs[avg_cpi] + ProjectKPIs[avg_spi]) / 2)"
                },
                {
                    "name": "Fleet Availability %",
                    "table": "FleetKPIs",
                    "expression": "AVERAGE(FleetKPIs[availability_pct])"
                },
                {
                    "name": "Total Incidents MTD",
                    "table": "SafetyKPIs",
                    "expression": "CALCULATE(SUM(SafetyKPIs[total_incidents]), DATESMTD(SafetyKPIs[month]))"
                },
            ],
            "annotations": [
                {"name": "Description", "value": "CIMIC KPI summary model — Direct Lake over cimic_lakehouse for executive dashboard agent"}
            ]
        }
    }


# ═══════════════════════════════════════════════════════════════════════
# NOTE: SQL Database tables are created via populate_sql_database.sql (not init script).
# Fabric SQL DB doesn't support PRIMARY KEY, DEFAULT, or NVARCHAR in CREATE TABLE,
# and tables created with those constraints become permanently read-only.
# To reset: delete cimic_sqldb in portal → re-run this script → paste populate_sql_database.sql


# ═══════════════════════════════════════════════════════════════════════
# API helpers (pattern from microsoft/skills-for-fabric)
# Auth: az account get-access-token --resource https://api.fabric.microsoft.com
# ═══════════════════════════════════════════════════════════════════════
def get_fabric_token():
    """Get Fabric API token via az CLI."""
    result = subprocess.run(
        ["az", "account", "get-access-token", "--resource", "https://api.fabric.microsoft.com",
         "--query", "accessToken", "-o", "tsv"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"[FAIL] az CLI error: {result.stderr.strip()}")
        print("   Run: az login --tenant <YOUR_TENANT_ID>")
        sys.exit(1)
    return result.stdout.strip()


def api(method, path, token, body=None, expect_long=False):
    """Call Fabric REST API with optional long-running operation polling."""
    import requests
    url = f"https://api.fabric.microsoft.com/v1{path}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    resp = getattr(requests, method)(url, headers=headers, json=body)

    if resp.status_code == 202 and expect_long:
        op_url = resp.headers.get("Location") or resp.headers.get("Operation-Location")
        if op_url:
            for _ in range(30):
                time.sleep(5)
                r = requests.get(op_url, headers=headers)
                if r.status_code == 200:
                    st = r.json().get("status", "")
                    if st in ("Succeeded", "Completed"):
                        return r.json()
                    if st == "Failed":
                        print(f"   [FAIL] {r.text[:200]}")
                        return None
        return resp.json() if resp.text else {}

    if resp.status_code not in (200, 201):
        print(f"   [WARN] {method.upper()} {path} → {resp.status_code}: {resp.text[:200]}")
        return None
    return resp.json() if resp.text else {}


def find_or_create_workspace(token, name, capacity_id):
    """Find existing workspace or create a new one."""
    data = api("get", "/workspaces", token)
    if data:
        for ws in data.get("value", []):
            if ws["displayName"].lower() == name.lower():
                print(f"   [OK] Exists: {name} ({ws['id']})")
                return ws["id"]
    result = api("post", "/workspaces", token, {"displayName": name, "capacityId": capacity_id})
    if result:
        print(f"   [OK] Created: {name} ({result['id']})")
        return result["id"]
    return None


def find_capacity(token, name):
    """Find Fabric capacity by name."""
    data = api("get", "/capacities", token)
    if not data:
        return None
    for c in data.get("value", []):
        if c["displayName"].lower() == name.lower():
            print(f"   [OK] {c['displayName']} ({c['sku']}, {c['state']})")
            return c["id"]
    print(f"   [FAIL] Capacity '{name}' not found. Available:")
    for c in data.get("value", []):
        print(f"      - {c['displayName']} ({c['sku']})")
    return None


def find_item(token, ws_id, display_name, item_type):
    """Find an existing Fabric item by name and type in a workspace."""
    data = api("get", f"/workspaces/{ws_id}/items?type={item_type}", token)
    if data:
        for item in data.get("value", []):
            if item["displayName"].lower() == display_name.lower():
                return item["id"]
    return None


def create_item(token, ws_id, display_name, item_type, definition=None, dry_run=False):
    """Create a Fabric item (Lakehouse, SQLDatabase, SemanticModel, DataAgent, etc.).

    Idempotent: if an item with the same name and type already exists, reuse it.
    Returns (item_id, created) where created is True if newly created, False if reused.
    """
    if not dry_run:
        existing_id = find_item(token, ws_id, display_name, item_type)
        if existing_id:
            print(f"   [SKIP] {item_type}: {display_name} already exists ({existing_id})")
            return existing_id, False

    if dry_run:
        print(f"   [DRY-RUN] Would create {item_type}: {display_name}")
        return None, False

    body = {"displayName": display_name, "type": item_type}
    if definition:
        body["definition"] = definition
    result = api("post", f"/workspaces/{ws_id}/items", token, body, expect_long=True)
    if result:
        item_id = result.get("id")
        # Long-running ops may not return the id directly — look it up
        if not item_id:
            item_id = find_item(token, ws_id, display_name, item_type)
        if not item_id:
            item_id = "UNKNOWN"
        print(f"   [OK] {item_type}: {display_name} ({item_id})")
        return item_id, True
    return None, False


# ═══════════════════════════════════════════════════════════════════════
# Main deployment flow
# ═══════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="Deploy Fabric workspace for CIMIC AI Workshop")
    parser.add_argument("--workspace", default=DEFAULTS["workspace_name"],
                        help=f"Workspace name (env: FABRIC_WORKSPACE, default: {DEFAULTS['workspace_name']})")
    parser.add_argument("--capacity", default=DEFAULTS["capacity_name"],
                        help=f"Capacity name (env: FABRIC_CAPACITY, default: {DEFAULTS['capacity_name']})")
    parser.add_argument("--dbx-host", default=DEFAULTS["dbx_host"],
                        help="Databricks workspace URL (env: DBX_HOST)")
    parser.add_argument("--dbx-catalog", default=DEFAULTS["dbx_catalog"],
                        help="Databricks catalog to mirror (env: DBX_CATALOG)")
    parser.add_argument("--config-out", default=os.path.join(os.path.dirname(__file__), "config.json"),
                        help="Path to write config.json (default: fabric/scripts/config.json)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be created without actually creating")
    default_agents_dir = str(Path(__file__).resolve().parent.parent / "agents")
    parser.add_argument("--agents-dir", default=default_agents_dir,
                        help=f"Directory containing agent .md instruction files (default: {default_agents_dir})")
    default_notebooks_dir = str(Path(__file__).resolve().parent.parent / "notebooks")
    parser.add_argument("--notebooks-dir", default=default_notebooks_dir,
                        help=f"Directory containing .ipynb notebook files (default: {default_notebooks_dir})")
    args = parser.parse_args()

    print(f"\n{'='*65}")
    print(f"  Fabric Deployment: {args.workspace}")
    if args.dry_run:
        print(f"  *** DRY RUN — no changes will be made ***")
    print(f"{'='*65}")
    print(f"  Capacity:    {args.capacity}")
    print(f"  DBX Host:    {args.dbx_host}")
    print(f"  DBX Catalog: {args.dbx_catalog}")
    print(f"  Agents dir:  {args.agents_dir}")
    print(f"  Notebooks:   {args.notebooks_dir}")
    print(f"  Config out:  {args.config_out}")
    print(f"{'='*65}\n")

    # Track what was created vs skipped for summary
    summary = {"created": [], "skipped": [], "failed": []}

    if args.dry_run:
        token = None
    else:
        token = get_fabric_token()

    # ── Step 1: Capacity ──────────────────────────────────────────
    print("[1/9] Finding capacity...")
    if args.dry_run:
        print(f"   [DRY-RUN] Would look up capacity '{args.capacity}'")
        cap_id = None
    else:
        cap_id = find_capacity(token, args.capacity)
        if not cap_id:
            sys.exit(1)

    # ── Step 2: Workspace ─────────────────────────────────────────
    print(f"\n[2/9] Workspace '{args.workspace}'...")
    if args.dry_run:
        print(f"   [DRY-RUN] Would find or create workspace '{args.workspace}'")
        ws_id = None
    else:
        ws_id = find_or_create_workspace(token, args.workspace, cap_id)
        if not ws_id:
            sys.exit(1)

    # ── Step 3: Lakehouse ─────────────────────────────────────────
    print(f"\n[3/9] Creating Lakehouse...")
    lh_name = "cimic_lakehouse"
    lh_id, lh_created = create_item(token, ws_id, lh_name, "Lakehouse", dry_run=args.dry_run)
    (summary["created"] if lh_created else summary["skipped"]).append(f"Lakehouse: {lh_name}")

    # ── Step 4: SQL Database ──────────────────────────────────────
    print(f"\n[4/9] Creating SQL Database...")
    sql_name = "cimic_sqldb"
    sql_id, sql_created = create_item(token, ws_id, sql_name, "SQLDatabase", dry_run=args.dry_run)
    (summary["created"] if sql_created else summary["skipped"]).append(f"SQLDatabase: {sql_name}")

    # ── Step 5: Semantic Model ────────────────────────────────────
    print(f"\n[5/9] Creating Semantic Model...")
    tmsl = build_semantic_model_tmsl(lh_name)
    tmsl_b64 = base64.b64encode(json.dumps(tmsl).encode()).decode()
    sm_def = {"parts": [{"path": "model.bim", "payload": tmsl_b64, "payloadType": "InlineBase64"}]}
    sm_id, sm_created = create_item(token, ws_id, "CIMIC_KPI_Model", "SemanticModel", definition=sm_def, dry_run=args.dry_run)
    (summary["created"] if sm_created else summary["skipped"]).append("SemanticModel: CIMIC_KPI_Model")

    # ── Step 6: Mirrored Databricks Catalog ───────────────────────
    print(f"\n[6/9] Mirrored Databricks catalog (best-effort)...")
    mirror_payload = json.dumps({
        "properties": {"source": {"type": "Databricks",
            "typeProperties": {"host": f"https://{args.dbx_host}", "catalog": args.dbx_catalog}}}
    })
    mirror_def = {"parts": [{"path": "mirroredDatabase.json",
                              "payload": base64.b64encode(mirror_payload.encode()).decode(),
                              "payloadType": "InlineBase64"}]}
    mirror_id, mirror_created = create_item(token, ws_id, f"Mirror_{args.dbx_catalog}", "MirroredDatabase", definition=mirror_def, dry_run=args.dry_run)
    if mirror_id or args.dry_run:
        (summary["created"] if mirror_created else summary["skipped"]).append(f"MirroredDatabase: Mirror_{args.dbx_catalog}")
    else:
        summary["failed"].append(f"MirroredDatabase: Mirror_{args.dbx_catalog}")
        print("   [INFO] Create manually: Workspace → New → Mirrored Database → Azure Databricks")
        print("   [INFO] See: databricks/docs/fabric-mirroring-auth-permissions-rls-guide.md")

    # ── Step 7: Data Agents ───────────────────────────────────────
    print(f"\n[7/9] Creating {len(AGENTS)} Data Agents...")

    # Load external instruction files (falls back to embedded defaults)
    agents_dir = Path(args.agents_dir)
    print(f"   Loading agent instructions from: {agents_dir}")
    agent_overrides = load_agent_overrides(agents_dir)

    created_agents = []
    for agent in AGENTS:
        # Apply overrides from external file if available
        override = agent_overrides.get(agent["name"])
        effective_agent = dict(agent)
        if override:
            effective_agent["instructions"] = override["instructions"]
            if override["example_questions"]:
                effective_agent["example_questions"] = override["example_questions"]

        aid, agent_created = create_item(token, ws_id, agent["name"], "DataAgent", dry_run=args.dry_run)
        if aid or args.dry_run:
            created_agents.append({"id": aid, **effective_agent})
            (summary["created"] if agent_created else summary["skipped"]).append(f"DataAgent: {agent['name']}")

    # ── Step 8: Deploy Notebooks ──────────────────────────────────
    notebooks_dir = Path(args.notebooks_dir)
    ipynb_files = sorted(notebooks_dir.glob("*.ipynb")) if notebooks_dir.is_dir() else []
    print(f"\n[8/9] Deploying {len(ipynb_files)} Notebooks from {notebooks_dir}...")

    created_notebooks = []
    for nb_path in ipynb_files:
        nb_name = nb_path.stem
        ipynb_content = nb_path.read_text(encoding="utf-8")
        nb_def = {
            "format": "ipynb",
            "parts": [
                {
                    "path": "notebook-content.py",
                    "payload": base64.b64encode(ipynb_content.encode("utf-8")).decode("utf-8"),
                    "payloadType": "InlineBase64",
                }
            ],
        }
        nb_id, nb_created = create_item(token, ws_id, nb_name, "Notebook", definition=nb_def, dry_run=args.dry_run)
        if nb_id or args.dry_run:
            created_notebooks.append({"name": nb_name, "id": nb_id, "file": nb_path.name})
            (summary["created"] if nb_created else summary["skipped"]).append(f"Notebook: {nb_name}")
        else:
            summary["failed"].append(f"Notebook: {nb_name}")

    # ── Step 9: Save config ───────────────────────────────────────
    print(f"\n[9/9] Saving config...")
    if args.dry_run:
        print(f"   [DRY-RUN] Would write config to {args.config_out}")
    else:
        config = {
            "workspace": {"name": args.workspace, "id": ws_id, "capacity": args.capacity},
            "items": {
                "lakehouse": {"name": lh_name, "id": lh_id},
                "sql_database": {"name": sql_name, "id": sql_id},
                "semantic_model": {"name": "CIMIC_KPI_Model", "id": sm_id},
                "mirrored_database": {"name": f"Mirror_{args.dbx_catalog}", "id": mirror_id},
            },
            "agents": [{
                "name": a["name"],
                "id": a.get("id"),
                "description": a["description"],
                "sources": a["sources"],
                "instructions": a["instructions"],
                "example_questions": a["example_questions"],
            } for a in created_agents],
            "notebooks": [{
                "name": nb["name"],
                "id": nb["id"],
                "file": nb["file"],
            } for nb in created_notebooks],
        }

        config_path = args.config_out
        os.makedirs(os.path.dirname(os.path.abspath(config_path)), exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        print(f"   [OK] Saved to {config_path}")

    # ── Summary ───────────────────────────────────────────────────
    print(f"\n{'='*65}")
    if args.dry_run:
        print(f"  🔍 Dry Run Complete — no changes were made")
    else:
        print(f"  ✅ Fabric Deployment Complete!")
    print(f"{'='*65}")
    print(f"  Workspace:  {args.workspace} ({ws_id or 'dry-run'})")
    if not args.dry_run:
        print(f"  Portal:     https://app.fabric.microsoft.com/groups/{ws_id}")
    print(f"  Lakehouse:  {lh_name} ({lh_id or 'dry-run'})")
    print(f"  SQL DB:     {sql_name} ({sql_id or 'dry-run'})")
    print(f"  Semantic:   CIMIC_KPI_Model ({sm_id or 'dry-run'})")
    print(f"  Mirror:     Mirror_{args.dbx_catalog} ({mirror_id or 'manual/dry-run'})")
    print(f"  Agents:     {len(created_agents)} {'would be created' if args.dry_run else 'created/reused'}")
    print(f"  Notebooks:  {len(created_notebooks)} {'would be deployed' if args.dry_run else 'deployed/reused'}")
    print()

    if summary["created"]:
        print(f"  📦 Created ({len(summary['created'])}):")
        for item in summary["created"]:
            print(f"    + {item}")
    if summary["skipped"]:
        print(f"  ⏭️  Skipped / already exists ({len(summary['skipped'])}):")
        for item in summary["skipped"]:
            print(f"    ~ {item}")
    if summary["failed"]:
        print(f"  ❌ Failed ({len(summary['failed'])}):")
        for item in summary["failed"]:
            print(f"    ! {item}")

    print(f"\n  Agent summary:")
    for a in created_agents:
        srcs = ", ".join(s.split(":")[0] for s in a["sources"])
        print(f"    • {a['name']} → [{srcs}]")

    if created_notebooks:
        print(f"\n  Notebook summary:")
        for nb in created_notebooks:
            print(f"    • {nb['name']} ({nb['file']})")

    print(f"\n  ⚠️  Next steps:")
    print(f"  1. Run: python fabric/scripts/02_populate_sql_db.py")
    print(f"  2. Run: python fabric/scripts/03_populate_lakehouse.py (or upload notebook to Fabric)")
    print(f"  3. Run deployed notebooks in Fabric to populate lakehouse tables")
    print(f"  4. Mirrored DB → Configure connection (see auth guide) → Start mirroring")
    print(f"  5. Each Data Agent → Add data sources + paste instructions from config.json")
    print(f"  6. Semantic Model → Validate lakehouse connection in portal")
    print(f"\n  📄 All agent configs saved to: {args.config_out}")
    print(f"{'='*65}")


if __name__ == "__main__":
    main()
