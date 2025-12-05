# Airflow Setup Guide

## What Changed in Your DAG

Your new **PostgreSQL-based workflow** (no Snowflake, no Blob Storage, no Airbyte):

```
Task 1: Load CSV → PostgreSQL (raw_data schema)
   ↓
Task 2: Validate data quality
   ↓
Task 3: Run dbt transformations (staging → analytics)
   ↓
Task 4: Test dbt models
   ↓
Task 5: Trigger Azure ML training (TODO)
   ↓
Task 6: Run batch predictions (TODO)
```

## Setup Steps

### 1. Rebuild Docker Images (includes dbt now)

```powershell
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

Wait ~2 minutes for services to start.

### 2. Configure PostgreSQL Connection in Airflow

**Option A: Via Airflow UI (Recommended)**

1. Go to http://localhost:8080
2. Login: `admin` / `admin`
3. Click **Admin** → **Connections**
4. Find `postgres_default` connection, click the **edit** icon
5. Update these fields:
   - **Host:** `postgres` (the Docker service name, not localhost!)
   - **Schema:** `telco_churn`
   - **Login:** `airflow`
   - **Password:** `airflow`
   - **Port:** `5432` (internal Docker port, not 5433!)
6. Click **Test** → Should say "Connection successfully tested"
7. Click **Save**

**Option B: Via Docker Command (Fastest)**

```powershell
# Delete any existing connection first
docker exec telcocustomerchurn-airflow-scheduler-1 airflow connections delete postgres_default

# Add the correct connection
docker exec telcocustomerchurn-airflow-scheduler-1 airflow connections add postgres_default --conn-type postgres --conn-host postgres --conn-schema telco_churn --conn-login airflow --conn-password airflow --conn-port 5432
```

**Common Mistake:** Make sure database name is `telco_churn` (single underscore), NOT `telco__churn` (double underscore)!

### 3. Test Your DAG

1. Go to http://localhost:8080
2. Find `telco_churn_pipeline` in the DAG list
3. Click the **play** button to trigger manually
4. Watch tasks turn green one by one!

**Important:** The first two tasks will work immediately:
- ✅ `load_csv_to_postgres` - Loads your CSV
- ✅ `validate_data_quality` - Checks data
- ⚠️ `run_dbt_models` - Will work after you configure dbt models
- ⚠️ `test_dbt_models` - Will work after dbt models exist
- ⚠️ `trigger_azure_ml_training` - Placeholder (implement later)
- ⚠️ `run_batch_predictions` - Placeholder (implement later)

## Next Steps

### 1. Configure dbt Models (Next Priority)

Your dbt models need to be updated to read from PostgreSQL:

**File: `dbt_project/models/staging/stg_telco_churn.sql`**
```sql
-- Read from raw_data schema
SELECT * FROM {{ source('raw_data', 'telco_churn_raw') }}
```

### 2. Set up dbt sources

**File: `dbt_project/models/staging/sources.yml`**
```yaml
version: 2

sources:
  - name: raw_data
    database: telco_churn
    schema: raw_data
    tables:
      - name: telco_churn_raw
```

### 3. Test dbt Locally (Optional)

```powershell
# Install dbt locally (in your venv)
pip install dbt-core dbt-postgres

# Test connection
cd dbt_project
dbt debug --profiles-dir .

# Run models
dbt run --profiles-dir . --target dev
```

## Troubleshooting

**DAG not showing up?**
- Wait 30-60 seconds for Airflow to scan DAGs
- Check logs: `docker-compose logs -f airflow-scheduler`

**Connection failed?**
- Make sure Host is `postgres` (not `localhost`)
- Make sure Port is `5432` (internal Docker network)

**Task failed?**
- Click on the task → **Log** to see details
- Most common: CSV file not found or connection misconfigured
