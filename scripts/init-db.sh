#!/bin/bash
set -e

# Create telco_churn database
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE telco_churn;
    GRANT ALL PRIVILEGES ON DATABASE telco_churn TO airflow;
EOSQL

# Create schemas in telco_churn database
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "telco_churn" <<-EOSQL
    CREATE SCHEMA IF NOT EXISTS raw_data;
    CREATE SCHEMA IF NOT EXISTS staging;
    CREATE SCHEMA IF NOT EXISTS analytics;
    GRANT ALL PRIVILEGES ON SCHEMA raw_data TO airflow;
    GRANT ALL PRIVILEGES ON SCHEMA staging TO airflow;
    GRANT ALL PRIVILEGES ON SCHEMA analytics TO airflow;
EOSQL

echo "Database telco_churn and schemas created successfully!"
