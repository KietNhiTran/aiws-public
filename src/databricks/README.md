# Databricks – AI Workshop (DABS)

End-to-end Databricks Asset Bundles (DABS) project that demonstrates a supply-chain analytics pipeline with Unity Catalog, Row-Level Security, and Genie Spaces.

## Directory structure

```
databricks/
├── databricks.yml            # DABS bundle config (variables, targets)
├── .env.example              # Environment variable template
├── resources/
│   └── module03_jobs.yml     # Workflow / job definitions
├── setup/                    # One-time workspace setup notebooks
│   ├── 01_create_schema.py   # Create Unity Catalog schemas
│   ├── 02_generate_data.py   # Generate synthetic supply-chain data
│   ├── 04_configure_rls.py   # Configure row-level security
│   ├── 05_domain_genie_spaces.py  # Create Genie Spaces per domain
│   └── 06_create_fabric_tables.py # Create external tables for Fabric
├── pipeline/                 # Medallion-architecture pipeline notebooks
│   ├── 00_source_simulator.py    # Simulate raw source files
│   ├── 01_bronze_ingestion.py    # Bronze layer (raw → Delta)
│   ├── 02_silver_transform.py    # Silver layer (cleanse & enrich)
│   └── 03_gold_aggregation.py    # Gold layer (business aggregates)
├── notebooks/
│   └── demo_genie_api.py    # Genie Space API demo notebook
└── docs/
    ├── databricks-permissions-guide.md  # Permissions & access setup
    ├── dataset-wiki.md                  # Dataset schema reference
    └── genie-space-reference.md         # Genie Space configuration guide
```

## Quick start

1. Install the [Databricks CLI](https://docs.databricks.com/dev-tools/cli/index.html) and authenticate.
2. Copy `.env.example` to `.env` and fill in your workspace values.
3. Update `databricks.yml` targets with your workspace URL, cluster ID, and catalog name.
4. Deploy with DABS:
   ```bash
   databricks bundle deploy --target dev
   ```
5. Run the setup notebooks (01 → 06) to initialise schemas, data, RLS, and Genie Spaces.
6. Run the pipeline notebooks (00 → 03) to execute the medallion pipeline.

## Targets

| Target | Description |
|--------|-------------|
| `dev` | Development workspace (default) |
| `staging` | Staging workspace |
| `production` | Production workspace |

Replace all `REPLACE_WITH_*` placeholders in `databricks.yml` with your environment-specific values before deploying.
