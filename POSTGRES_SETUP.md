# PostgreSQL Connection Guide

## Your Setup

You now have **TWO separate PostgreSQL instances**:

1. **Your existing PostgreSQL** (port 5432) - contains `ecomm` database
2. **Docker PostgreSQL** (port 5433) - contains `airflow` and `telco_churn` databases

## Connect to Docker PostgreSQL in pgAdmin

1. Right-click **Servers** → **Register** → **Server**
2. **General tab:**
   - Name: `Telco Churn Docker`
3. **Connection tab:**
   - Host: `localhost`
   - Port: `5433`
   - Database: `telco_churn`
   - Username: `airflow`
   - Password: `airflow`
4. Click **Save**

You should now see two databases:
- `airflow` (Airflow metadata)
- `telco_churn` (Your churn data with schemas: raw_data, staging, analytics)

## Your New Workflow (Without Snowflake)
```
# top grade students than 50 in each subject
select name from students group by name having avg(score) > 50
# top one student in each subject
select name, max(score) from students group by name order by max(score) desc limit 1
```
```
1. Raw CSV Data (data/raw/WA_Fn-UseC_-Telco-Customer-Churn.csv)
   ↓
2. Airflow DAG loads CSV → PostgreSQL (raw_data schema)
   ↓
3. Airflow triggers dbt run
   ↓
4. dbt transforms data:
   - raw_data.telco_churn → staging.stg_telco_churn
   - staging.stg_telco_churn → analytics.fct_customer_features
   ↓
5. Airflow triggers Azure ML training
   ↓
6. Azure ML reads from PostgreSQL analytics.fct_customer_features
   ↓
7. Model training + MLflow tracking
   ↓
8. Predictions written back to PostgreSQL analytics.predictions
   ↓
9. BI tool (Power BI/Superset) connects to PostgreSQL for dashboards
```

## Quick Commands

**Access PostgreSQL via Docker:**
```powershell
docker exec -it telcocustomerchurn-postgres-1 psql -U airflow -d telco_churn
```

**List schemas:**
```sql
\dn
```

**List tables in a schema:**
```sql
\dt analytics.*
```

**Query data:**
```sql
SELECT * FROM analytics.fct_customer_features LIMIT 10;
```

**Exit:**
```sql
\q
```

## Connection String for Python/dbt

```
postgresql://airflow:airflow@localhost:5433/telco_churn
```

## Docker Management Commands

**Stop all services:**
```powershell
docker-compose down
```

**Start all services:**
```powershell
docker-compose up -d
```

**Restart services:**
```powershell
docker-compose restart
```

**View running services:**
```powershell
docker-compose ps
```

**View logs:**
```powershell
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f airflow-webserver
docker-compose logs -f airflow-scheduler
docker-compose logs -f postgres
```

**Stop services and remove all data (WARNING: deletes database!):**
```powershell
docker-compose down -v
```
