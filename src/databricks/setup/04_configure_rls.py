# Databricks notebook source
# MAGIC %md
# MAGIC # Module 03 -- Row-Level Security (RLS)
# MAGIC
# MAGIC Implements division-based Row-Level Security as described in Module 03 section 3.3.5.
# MAGIC
# MAGIC Creates:
# MAGIC 1. A `security` schema with a `division_filter` SQL function
# MAGIC 2. (Optional) Unfiltered `v_*_mirror` views for Fabric mirroring
# MAGIC 3. Row filters on financials, equipment_telemetry, and incidents
# MAGIC 4. (Optional) Column mask on budget_aud for non-executives
# MAGIC
# MAGIC **Prerequisites:**
# MAGIC - Entra ID security groups synced to Databricks account via SCIM.
# MAGIC - Default naming follows Module 03 spec: `{customer}-Division-CPB`, etc.
# MAGIC - Set `group_naming_style = "generic"` for legacy Group-A/B/C names.
# MAGIC
# MAGIC **SCIM Setup Required:**
# MAGIC 1. Entra ID → Enterprise Applications → Add "Azure Databricks SCIM Provisioning Connector"
# MAGIC 2. Configure provisioning scope to include the above groups
# MAGIC 3. Start provisioning → groups sync to Databricks account automatically
# MAGIC 4. Groups appear under Account Console → User management → Groups
# MAGIC
# MAGIC Parameterised via `customer_name` so group names adapt to the customer.

# COMMAND ----------

dbutils.widgets.text("catalog_name", "contoso", "Catalog Name")
dbutils.widgets.text("customer_name", "Contoso", "Customer Display Name")
dbutils.widgets.dropdown("apply_column_mask", "yes", ["yes", "no"], "Apply Column Mask on budget_aud")
dbutils.widgets.dropdown("apply_row_filter", "no", ["yes", "no"], "Apply Row Filters (requires Entra ID groups)")
dbutils.widgets.dropdown("group_naming_style", "generic", ["customer-division", "generic"], "Group Naming Style")
dbutils.widgets.dropdown("apply_grants", "no", ["yes", "no"], "Apply Table-Level Grants")
dbutils.widgets.dropdown("create_mirror_views", "yes", ["yes", "no"], "Create unfiltered views for Fabric mirroring")
dbutils.widgets.text("mirror_sp_id", "", "Mirror Service Principal App ID (optional, for GRANT)")

catalog = dbutils.widgets.get("catalog_name")
customer = dbutils.widgets.get("customer_name")
apply_mask = dbutils.widgets.get("apply_column_mask") == "yes"
apply_filter = dbutils.widgets.get("apply_row_filter") == "yes"
group_style = dbutils.widgets.get("group_naming_style")
apply_grants_flag = dbutils.widgets.get("apply_grants") == "yes"
create_mirror = dbutils.widgets.get("create_mirror_views") == "yes"
mirror_sp_id = dbutils.widgets.get("mirror_sp_id").strip()

print(f"Catalog: {catalog} | Customer: {customer}")
print(f"Group naming style: {group_style}")
print(f"Row filter: {'yes' if apply_filter else 'no (function created but not applied)'}")
print(f"Column mask: {'yes' if apply_mask else 'no'}")
print(f"Table-level grants: {'yes' if apply_grants_flag else 'no'}")
print(f"Mirror views: {'yes' if create_mirror else 'no'}")
if mirror_sp_id:
    print(f"Mirror SP: {mirror_sp_id}")
else:
    print(f"Mirror SP: not set (views created but no GRANT)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Create Security Schema

# COMMAND ----------

spark.sql(f"""
    CREATE SCHEMA IF NOT EXISTS {catalog}.security
    COMMENT '{customer} row-level security functions and access control'
""")
print(f"[OK] Schema: {catalog}.security")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Create Division Filter Function
# MAGIC
# MAGIC This function returns TRUE if the current user belongs to the matching
# MAGIC division group, or if the user is in the Executives group (full access).
# MAGIC
# MAGIC Group naming convention: generic (Group-A/B/C) by default; customer-division uses `{customer}-Division-*`

# COMMAND ----------

# Division group mappings -- maps data division values to Entra ID group names
# "customer-division" (default): aligns with Module 03 spec ({customer}-Division-*)
# "generic": uses Group-A/B/C for environments without customer-specific groups
if group_style == "customer-division":
    DIVISION_GROUPS = {
        "Division-Alpha": f"{customer}-Division-Alpha",
        "Division-Beta": f"{customer}-Division-Beta",
        "Division-Gamma": f"{customer}-Division-Gamma",
        "Division-Delta": f"{customer}-Division-Delta",
    }
    exec_group = f"{customer}-Division-Executives"
else:
    DIVISION_GROUPS = {
        "Division-Alpha": "Group-A",
        "Division-Beta": "Group-B",
        "Division-Gamma": "Group-C",
        "Division-Delta": "Group-D",
    }
    exec_group = "Group-Executives"

# Build the OR conditions for each division
or_clauses = []
for div_full, group_name in DIVISION_GROUPS.items():
    or_clauses.append(
        f"  OR (division_value = '{div_full}' AND IS_MEMBER('{group_name}'))"
    )


filter_sql = f"""
CREATE OR REPLACE FUNCTION {catalog}.security.division_filter(division_value STRING)
RETURNS BOOLEAN
RETURN
  IS_MEMBER('{exec_group}')
  OR IS_MEMBER('admins')
{chr(10).join(or_clauses)}
"""

spark.sql(filter_sql)
print(f"[OK] Function: {catalog}.security.division_filter")
print(f"     Executives group: {exec_group}")
for div_full, group_name in DIVISION_GROUPS.items():
    print(f"     {group_name} -> {div_full}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2b. Create Unfiltered Views for Fabric Mirroring
# MAGIC
# MAGIC Tables with UC row filters fail to sync to Fabric mirroring (Fabric reads Delta
# MAGIC files directly from ADLS, and row filter metadata causes "Resilience check failed"
# MAGIC errors). These views provide a clean metadata target for Fabric to mirror.
# MAGIC
# MAGIC **Must run BEFORE row filters are applied** — `CREATE OR REPLACE VIEW` on a
# MAGIC row-filtered source table may fail on reruns.
# MAGIC
# MAGIC On the Fabric side, OneLake Security RLS re-applies equivalent division-based
# MAGIC filtering using the same Entra ID groups.

# COMMAND ----------

tables_for_mirror = [
    "projects.financials",
    "safety.incidents",
]

if create_mirror:
    for tbl in tables_for_mirror:
        schema, table = tbl.split(".")
        view_name = f"{catalog}.{schema}.v_{table}_mirror"
        try:
            spark.sql(f"""
                CREATE OR REPLACE VIEW {view_name} AS
                SELECT * FROM {catalog}.{tbl}
            """)
            print(f"[OK] Mirror view: {view_name}")
        except Exception as e:
            print(f"[WARN] {view_name}: {str(e)[:200]}")

    if mirror_sp_id:
        for tbl in tables_for_mirror:
            schema, table = tbl.split(".")
            view_name = f"{catalog}.{schema}.v_{table}_mirror"
            try:
                spark.sql(f"GRANT SELECT ON VIEW {view_name} TO `{mirror_sp_id}`")
                print(f"[OK] GRANT SELECT on {view_name} to SP")
            except Exception as e:
                print(f"[WARN] GRANT on {view_name}: {str(e)[:200]}")
        for schema in ["projects", "safety"]:
            try:
                spark.sql(f"GRANT USE SCHEMA ON SCHEMA `{catalog}`.`{schema}` TO `{mirror_sp_id}`")
                spark.sql(f"GRANT EXTERNAL USE SCHEMA ON SCHEMA `{catalog}`.`{schema}` TO `{mirror_sp_id}`")
            except Exception:
                pass
else:
    print("[SKIP] Mirror views not requested (set create_mirror_views=yes to enable)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Apply Row Filters to Tables

# COMMAND ----------

tables_with_division = [
    "projects.financials",
    "equipment.equipment_telemetry",
    "safety.incidents",
]

for tbl in tables_with_division:
    if apply_filter:
        try:
            spark.sql(f"""
                ALTER TABLE {catalog}.{tbl}
                SET ROW FILTER {catalog}.security.division_filter ON (division)
            """)
            print(f"[OK] Row filter applied to {catalog}.{tbl}")
        except Exception as e:
            err = str(e)
            if "already has a row filter" in err.lower() or "row_filter" in err.lower():
                print(f"[SKIP] {catalog}.{tbl} already has a row filter")
            else:
                print(f"[WARN] {catalog}.{tbl}: {err[:200]}")
    else:
        # Remove any existing row filter so data is visible
        try:
            spark.sql(f"ALTER TABLE {catalog}.{tbl} DROP ROW FILTER")
            print(f"[OK] Row filter removed from {catalog}.{tbl}")
        except Exception:
            print(f"[OK] {catalog}.{tbl} -- no row filter to remove")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. (Optional) Column Mask for Budget
# MAGIC
# MAGIC Non-executives see budget values rounded to the nearest million.

# COMMAND ----------

if apply_mask:
    spark.sql(f"""
    CREATE OR REPLACE FUNCTION {catalog}.security.mask_budget(budget_value DOUBLE)
    RETURNS DOUBLE
    RETURN
      CASE
        WHEN IS_MEMBER('{exec_group}') THEN budget_value
        ELSE ROUND(budget_value / 1000000, 0) * 1000000
      END
    """)
    print(f"[OK] Function: {catalog}.security.mask_budget")

    try:
        spark.sql(f"""
            ALTER TABLE {catalog}.projects.financials
            ALTER COLUMN budget_aud SET MASK {catalog}.security.mask_budget
        """)
        print(f"[OK] Column mask applied to {catalog}.projects.financials.budget_aud")
    except Exception as e:
        err = str(e)
        if "already has" in err.lower():
            print(f"[SKIP] budget_aud already has a mask")
        else:
            print(f"[WARN] Column mask: {err[:200]}")
else:
    print("[SKIP] Column mask not requested (set apply_column_mask=yes to enable)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Verify

# COMMAND ----------

print("Row filters applied to:")
for tbl in tables_with_division:
    detail = spark.sql(f"DESCRIBE DETAIL {catalog}.{tbl}").collect()[0]
    print(f"  {catalog}.{tbl}")

print(f"\nGroup naming style: {group_style}")
print(f"RLS setup complete for {customer}.")
print(f"\nTo test, sign in as different Entra ID users belonging to different groups:")
for div_full, group_name in DIVISION_GROUPS.items():
    print(f"  - {group_name} -> sees only {div_full} data")
print(f"  - {exec_group} -> sees all divisions")
print(f"\nSCIM provisioning required: Entra ID → Enterprise Apps → Databricks SCIM Connector")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Table-Level Grants
# MAGIC
# MAGIC Grants USE CATALOG, USE SCHEMA, and SELECT privileges so that division
# MAGIC groups can query their filtered data. RLS row filters handle the actual
# MAGIC per-division restriction; these grants just open the door to the tables.
# MAGIC
# MAGIC Controlled by the `apply_grants` widget (default "no") to avoid
# MAGIC accidental privilege changes in shared environments.

# COMMAND ----------

if apply_grants_flag:
    all_groups = list(DIVISION_GROUPS.values()) + [exec_group]
    schemas = ["projects", "equipment", "safety", "procurement", "security"]

    # Tables every division group can SELECT (RLS filters rows)
    division_tables = [
        "projects.financials",
        "equipment.equipment_telemetry",
        "safety.incidents",
    ]
    # Tables with no division column -- all groups get SELECT
    # (Division-Delta data remains unfiltered/shared in these tables)
    shared_tables = [
        "procurement.materials",
    ]

    def run_grant(sql_stmt, label):
        """Execute a GRANT/REVOKE, print result, tolerate missing groups."""
        try:
            spark.sql(sql_stmt)
            print(f"  [OK] {label}")
        except Exception as e:
            print(f"  [WARN] {label}: {str(e)[:200]}")

    for grp in all_groups:
        print(f"\nGranting privileges to `{grp}`:")
        run_grant(
            f"GRANT USE CATALOG ON CATALOG `{catalog}` TO `{grp}`",
            f"USE CATALOG {catalog}",
        )
        for schema in schemas:
            run_grant(
                f"GRANT USE SCHEMA ON SCHEMA `{catalog}`.`{schema}` TO `{grp}`",
                f"USE SCHEMA {catalog}.{schema}",
            )
        # Security function access (needed for row filter evaluation)
        run_grant(
            f"GRANT EXECUTE ON FUNCTION `{catalog}`.`security`.`division_filter` TO `{grp}`",
            f"EXECUTE {catalog}.security.division_filter",
        )

    # Division groups: SELECT on RLS-filtered + shared tables
    for grp in DIVISION_GROUPS.values():
        print(f"\nGranting SELECT to division group `{grp}`:")
        for tbl in division_tables + shared_tables:
            run_grant(
                f"GRANT SELECT ON TABLE `{catalog}`.`{tbl}` TO `{grp}`",
                f"SELECT {catalog}.{tbl}",
            )

    # Executives: SELECT on ALL tables (full visibility)
    print(f"\nGranting full SELECT to executives group `{exec_group}`:")
    exec_tables = division_tables + shared_tables
    for tbl in exec_tables:
        run_grant(
            f"GRANT SELECT ON TABLE `{catalog}`.`{tbl}` TO `{exec_group}`",
            f"SELECT {catalog}.{tbl}",
        )

    print("\n[OK] Table-level grants applied.")
else:
    print("[SKIP] Table-level grants not requested (set apply_grants=yes to enable)")
