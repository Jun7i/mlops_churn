"""
Telco Customer Churn Pipeline DAG

This DAG orchestrates the entire ML pipeline:
1. Load raw CSV data into PostgreSQL
2. Run dbt transformations (staging → analytics)
3. Trigger Azure ML training pipeline
4. Run batch predictions and write back to PostgreSQL
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta
import pandas as pd
import os
#import kagglehub

# Default arguments for the DAG
default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

# DAG definition
dag = DAG(
    'telco_churn_pipeline',
    default_args=default_args,
    description='End-to-end ML pipeline for customer churn prediction',
    schedule_interval='@daily',  # Run daily at midnight
    start_date=datetime(2025, 11, 1),
    catchup=False,
    tags=['ml', 'churn', 'production'],
)


def load_csv_to_postgres():
    """
    Load raw CSV data into PostgreSQL raw_data schema
    """
    # Path to the CSV file (mounted in Docker)
    csv_path = '/opt/airflow/data/raw/WA_Fn-UseC_-Telco-Customer-Churn.csv'
    
    # Get PostgreSQL connection
    pg_hook = PostgresHook(postgres_conn_id='postgres_default')
    engine = pg_hook.get_sqlalchemy_engine()
    
    # Check if table already has data
    result = engine.execute("SELECT COUNT(*) FROM raw_data.telco_churn_raw")
    existing_count = result.fetchone()[0]
    
    if existing_count > 0:
        print(f"✅ Table already has {existing_count} rows, skipping load")
        return existing_count
    
    # Read CSV
    df = pd.read_csv(csv_path)
    
    # Load to PostgreSQL
    df.to_sql(
        name='telco_churn_raw',
        con=engine,
        schema='raw_data',
        if_exists='append',  # Changed from 'replace' to avoid dropping table with dependent views
        index=False,
        method='multi',
        chunksize=1000
    )
    
    print(f"✅ Loaded {len(df)} rows into raw_data.telco_churn_raw")
    return len(df)


def validate_data_quality():
    """
    Run data quality checks on raw data
    Raises AssertionError if checks fail, which will fail the Airflow task
    """
    pg_hook = PostgresHook(postgres_conn_id='postgres_default')
    
    # Check 1: Row count
    row_count = pg_hook.get_first("SELECT COUNT(*) FROM raw_data.telco_churn_raw")[0]
    assert row_count > 0, f"❌ No data found in raw table! Expected > 0, got {row_count}"
    
    # Check 2: No null customer IDs
    null_check = pg_hook.get_first("""
        SELECT COUNT(*) FROM raw_data.telco_churn_raw 
        WHERE "customerID" IS NULL
    """)[0]
    assert null_check == 0, f"❌ Found {null_check} rows with null customer IDs!"
    
    # Check 3: No duplicate customer IDs
    duplicate_check = pg_hook.get_first("""
        SELECT COUNT(*) - COUNT(DISTINCT "customerID") 
        FROM raw_data.telco_churn_raw
    """)[0]
    assert duplicate_check == 0, f"❌ Found {duplicate_check} duplicate customer IDs!"
    
    print(f"✅ All data quality checks passed! Row count: {row_count}")
    return True


def train_models_with_mlflow():
    """
    Train churn models with MLflow tracking
    Runs the training script that trains XGBoost, RF, and Logistic Regression
    """
    print("🚀 Training models with MLflow...")
    
    import sys
    import os
    sys.path.insert(0, '/opt/airflow/src')
    
    # Set environment variables for Docker network
    os.environ['MLFLOW_TRACKING_URI'] = 'http://mlflow:5000'
    os.environ['DB_CONN'] = 'postgresql://airflow:airflow@postgres:5432/telco_churn'
    
    from train.train import main as train_main
    
    # Run training
    best_model, metrics = train_main()
    
    print(f"✅ Training complete! Best model: {best_model}")
    print(f"   PR-AUC: {metrics['pr_auc']:.4f}")
    print(f"   Recall@Top10%: {metrics['recall_at_top_10_percent']:.4f}")
    
    return best_model


def run_batch_predictions():
    """
    Run batch predictions on all customers using the best MLflow model
    Writes predictions to analytics.predictions table
    """
    print("🔮 Running batch predictions...")
    
    import sys
    sys.path.insert(0, '/opt/airflow/src')
    
    import mlflow
    import mlflow.xgboost
    import mlflow.sklearn
    import pandas as pd
    import numpy as np
    from sqlalchemy import create_engine
    
    # MLflow setup
    mlflow.set_tracking_uri('http://mlflow:5000')
    
    # Get PostgreSQL connection
    pg_hook = PostgresHook(postgres_conn_id='postgres_default')
    engine = pg_hook.get_sqlalchemy_engine()
    
    # Read features
    query = "SELECT * FROM analytics.fct_customer_features"
    df = pd.read_sql(query, engine)
    
    # Separate customer_id and features
    customer_ids = df['customer_id']
    features = df.drop(columns=['customer_id', 'has_churned'])
    
    # Load best model from registry - try xgboost first, then sklearn
    model_name = "telco_churn_best_model"
    model_uri = f"models:/{model_name}/latest"
    
    print(f"📦 Loading model: {model_uri}")
    
    try:
        # Try loading as xgboost (best model is usually xgboost)
        model = mlflow.xgboost.load_model(model_uri)
        print("✅ Loaded as XGBoost model")
    except:
        try:
            # Fallback to sklearn
            model = mlflow.sklearn.load_model(model_uri)
            print("✅ Loaded as sklearn model")
        except:
            # Last resort - pyfunc
            model = mlflow.pyfunc.load_model(model_uri)
            print("✅ Loaded as pyfunc model")
    
    # Make predictions
    print(f"🎯 Scoring {len(df)} customers...")
    
    # Get probability predictions
    if hasattr(model, 'predict_proba'):
        # Standard sklearn/xgboost predict_proba
        predictions_proba = model.predict_proba(features)
        churn_probability = predictions_proba[:, 1]
    elif hasattr(model, 'predict'):
        # Some models return probabilities directly from predict
        predictions = model.predict(features)
        if isinstance(predictions, np.ndarray) and len(predictions.shape) > 1 and predictions.shape[1] == 2:
            churn_probability = predictions[:, 1]
        else:
            # If boolean/class predictions, treat as 0 or 1 probability
            churn_probability = np.array(predictions, dtype=float)
    else:
        raise ValueError("Model does not have predict or predict_proba method")
    
    # Create predictions dataframe
    predictions_df = pd.DataFrame({
        'customer_id': customer_ids,
        'churn_probability': churn_probability,
        'at_risk_flag': (churn_probability >= 0.5).astype(int),
        'prediction_date': pd.Timestamp.now()
    })
    
    # Write to PostgreSQL
    predictions_df.to_sql(
        name='predictions',
        con=engine,
        schema='analytics',
        if_exists='replace',
        index=False
    )
    
    high_risk_count = (predictions_df['at_risk_flag'] == 1).sum()
    print(f"✅ Predictions saved! {high_risk_count:,} high-risk customers identified")
    
    return len(predictions_df)


# Task 1: Load raw CSV data into PostgreSQL
task_load_data = PythonOperator(
    task_id='load_csv_to_postgres',
    python_callable=load_csv_to_postgres,
    dag=dag,
)

# Task 2: Validate data quality
task_validate = PythonOperator(
    task_id='validate_data_quality',
    python_callable=validate_data_quality,
    dag=dag,
)

# Task 3: Run dbt transformations
task_dbt_run = BashOperator(
    task_id='run_dbt_models',
    bash_command='cd /opt/airflow/dbt_project && dbt run --profiles-dir . --target dev',
    dag=dag,
)

# Task 4: Run dbt tests
task_dbt_test = BashOperator(
    task_id='test_dbt_models',
    bash_command='cd /opt/airflow/dbt_project && dbt test --profiles-dir . --target dev',
    dag=dag,
)

# Task 5: Train models with MLflow
task_train_model = PythonOperator(
    task_id='train_models_with_mlflow',
    python_callable=train_models_with_mlflow,
    dag=dag,
)

# Task 6: Run batch predictions
task_predict = PythonOperator(
    task_id='run_batch_predictions',
    python_callable=run_batch_predictions,
    dag=dag,
)

# Define task dependencies (pipeline flow)
task_load_data >> task_validate >> task_dbt_run >> task_dbt_test >> task_train_model >> task_predict

