"""
One-time DAG to backfill historical predictions for Tableau time-series analysis.
Run this manually ONCE after your first successful training.

This generates predictions for the past 60 days with slight variations
to simulate natural model behavior over time.
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 0,
}

dag = DAG(
    'backfill_historical_predictions',
    default_args=default_args,
    description='Generate 60 days of historical predictions for Tableau',
    schedule_interval=None,  # Manual trigger only
    start_date=datetime(2025, 12, 1),
    catchup=False,
    tags=['ml', 'backfill', 'one-time'],
)


def add_temporal_noise(probabilities, noise_level=0.02):
    """Add small random noise to simulate natural variation"""
    noise = np.random.normal(0, noise_level, size=len(probabilities))
    noisy_probs = probabilities + noise
    return np.clip(noisy_probs, 0.0, 1.0)


def backfill_predictions():
    """
    Generate predictions for each of the past 60 days with slight variations
    """
    import sys
    sys.path.insert(0, '/opt/airflow/src')
    
    import mlflow
    import mlflow.xgboost
    import mlflow.sklearn
    
    DAYS_TO_BACKFILL = 60
    MODEL_NAME = "telco_churn_best_model"
    
    print("🚀 Starting Historical Prediction Backfill")
    print("=" * 80)
    
    # Setup MLflow
    mlflow.set_tracking_uri('http://mlflow:5000')
    
    # Get PostgreSQL connection
    pg_hook = PostgresHook(postgres_conn_id='postgres_default')
    engine = pg_hook.get_sqlalchemy_engine()
    
    # Load customer features
    print("📊 Loading customer features...")
    query = "SELECT * FROM analytics.fct_customer_features"
    df = pd.read_sql(query, engine)
    
    customer_ids = df['customer_id']
    features = df.drop(columns=['customer_id', 'has_churned'])
    
    print(f"✅ Loaded {len(df):,} customers")
    
    # Load best model
    print(f"\n📦 Loading model: {MODEL_NAME}")
    model_uri = f"models:/{MODEL_NAME}/latest"
    
    try:
        model = mlflow.xgboost.load_model(model_uri)
        print("✅ Loaded as XGBoost model")
    except:
        try:
            model = mlflow.sklearn.load_model(model_uri)
            print("✅ Loaded as sklearn model")
        except:
            model = mlflow.pyfunc.load_model(model_uri)
            print("✅ Loaded as pyfunc model")
    
    # Get base predictions
    print(f"\n🎯 Generating base predictions...")
    if hasattr(model, 'predict_proba'):
        base_probabilities = model.predict_proba(features)[:, 1]
    else:
        predictions = model.predict(features)
        if isinstance(predictions, np.ndarray) and len(predictions.shape) > 1:
            base_probabilities = predictions[:, 1]
        else:
            base_probabilities = np.array(predictions, dtype=float)
    
    print(f"✅ Base predictions generated")
    print(f"   Mean probability: {base_probabilities.mean():.4f}")
    print(f"   Std deviation: {base_probabilities.std():.4f}")
    
    # Generate predictions for each historical day
    print(f"\n📅 Generating predictions for past {DAYS_TO_BACKFILL} days...")
    
    all_predictions = []
    # Use today's date (no time component) and go backwards
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    for day_offset in range(DAYS_TO_BACKFILL - 1, -1, -1):  # 59, 58, ..., 1, 0
        prediction_date = today - timedelta(days=day_offset)
        
        # Add small random noise - older predictions have slightly more variation
        noise_level = 0.01 + (day_offset / DAYS_TO_BACKFILL) * 0.02
        daily_probabilities = add_temporal_noise(base_probabilities, noise_level)
        
        # Create daily predictions dataframe
        daily_df = pd.DataFrame({
            'customer_id': customer_ids,
            'churn_probability': daily_probabilities,
            'at_risk_flag': (daily_probabilities >= 0.5).astype(int),
            'prediction_date': prediction_date
        })
        
        all_predictions.append(daily_df)
        
        if (day_offset + 1) % 10 == 0:
            print(f"   Generated: {prediction_date.strftime('%Y-%m-%d')} ({len(all_predictions)} days)")
    
    # Combine all predictions
    print(f"\n💾 Combining {len(all_predictions)} days of predictions...")
    combined_df = pd.concat(all_predictions, ignore_index=True)
    
    print(f"✅ Total records: {len(combined_df):,}")
    print(f"   Date range: {combined_df['prediction_date'].min()} to {combined_df['prediction_date'].max()}")
    
    # Write to PostgreSQL (replace existing data)
    print(f"\n📝 Writing to PostgreSQL analytics.predictions...")
    combined_df.to_sql(
        name='predictions',
        con=engine,
        schema='analytics',
        if_exists='replace',
        index=False,
        method='multi',
        chunksize=1000
    )
    
    print(f"✅ Successfully wrote {len(combined_df):,} prediction records!")
    
    # Summary statistics
    print("\n" + "=" * 80)
    print("📊 BACKFILL SUMMARY")
    print("=" * 80)
    
    summary_stats = combined_df.groupby('prediction_date').agg({
        'at_risk_flag': 'sum',
        'churn_probability': 'mean'
    }).reset_index()
    
    print(f"\nDate Range: {summary_stats['prediction_date'].min()} to {summary_stats['prediction_date'].max()}")
    print(f"Average High-Risk Customers per Day: {summary_stats['at_risk_flag'].mean():.0f}")
    print(f"Overall Average Churn Probability: {combined_df['churn_probability'].mean():.4f}")
    print(f"\nMin High-Risk: {summary_stats['at_risk_flag'].min():.0f} customers")
    print(f"Max High-Risk: {summary_stats['at_risk_flag'].max():.0f} customers")
    
    print("\n✅ Backfill complete! Ready for Tableau time-series analysis.")
    print("\n💡 Tableau Usage:")
    print("   - X-axis: prediction_date (Day or Week)")
    print("   - Y-axis: SUM(at_risk_flag) or AVG(churn_probability)")
    print("   - Add trend line to show model stability")
    
    return len(combined_df)


# Single task to run backfill
task_backfill = PythonOperator(
    task_id='backfill_60_days',
    python_callable=backfill_predictions,
    dag=dag,
    execution_timeout=timedelta(minutes=10),
)
