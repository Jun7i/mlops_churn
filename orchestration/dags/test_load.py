"""
Test script to verify the load_csv_to_postgres function works
Run this inside the Airflow container to debug issues
"""
import pandas as pd
from airflow.providers.postgres.hooks.postgres import PostgresHook

def test_load():
    print("🔍 Testing CSV load function...")
    
    # Path to the CSV file
    csv_path = '/opt/airflow/data/raw/WA_Fn-UseC_-Telco-Customer-Churn.csv'
    
    # Step 1: Check if file exists
    import os
    if not os.path.exists(csv_path):
        print(f"❌ ERROR: CSV file not found at {csv_path}")
        return
    print(f"✅ CSV file found: {csv_path}")
    
    # Step 2: Read CSV
    try:
        df = pd.read_csv(csv_path)
        print(f"✅ CSV loaded: {len(df)} rows, {len(df.columns)} columns")
        print(f"   Columns: {list(df.columns[:5])}...")
    except Exception as e:
        print(f"❌ ERROR reading CSV: {e}")
        return
    
    # Step 3: Test PostgreSQL connection
    try:
        pg_hook = PostgresHook(postgres_conn_id='postgres_default')
        engine = pg_hook.get_sqlalchemy_engine()
        print(f"✅ PostgreSQL connection successful: {engine.url}")
    except Exception as e:
        print(f"❌ ERROR connecting to PostgreSQL: {e}")
        print(f"   Make sure 'postgres_default' connection is configured!")
        return
    
    # Step 4: Load to PostgreSQL
    try:
        df.to_sql(
            name='telco_churn_raw',
            con=engine,
            schema='raw_data',
            if_exists='replace',
            index=False,
            method='multi',
            chunksize=1000
        )
        print(f"✅ Data loaded successfully to raw_data.telco_churn_raw")
        
        # Verify
        result = engine.execute("SELECT COUNT(*) FROM raw_data.telco_churn_raw")
        count = result.fetchone()[0]
        print(f"✅ Verification: {count} rows in database")
        
    except Exception as e:
        print(f"❌ ERROR loading data: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n🎉 All tests passed!")

if __name__ == '__main__':
    test_load()
