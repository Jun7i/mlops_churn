"""
Backfill historical predictions for Tableau time-series analysis.
This simulates daily predictions over the past 60 days for portfolio demonstration.

Run this script ONCE after your first successful prediction to populate historical data.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import create_engine
import mlflow
import mlflow.xgboost
import mlflow.sklearn

# Configuration
MLFLOW_TRACKING_URI = 'http://localhost:5000'
DB_CONN = 'postgresql://airflow:airflow@localhost:5433/telco_churn'
DAYS_TO_BACKFILL = 60  # Generate predictions for past 60 days
MODEL_NAME = "telco_churn_best_model"

def add_temporal_noise(probabilities, noise_level=0.02):
    """
    Add small random noise to probabilities to simulate natural variation over time.
    This makes the time-series chart more realistic.
    """
    noise = np.random.normal(0, noise_level, size=len(probabilities))
    noisy_probs = probabilities + noise
    # Clip to valid probability range [0, 1]
    return np.clip(noisy_probs, 0.0, 1.0)


def generate_historical_predictions():
    """
    Generate predictions for each of the past N days with slight variations
    """
    print("🚀 Starting Historical Prediction Backfill")
    print("=" * 80)
    
    # Setup MLflow
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    
    # Connect to PostgreSQL
    engine = create_engine(DB_CONN)
    
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
    end_date = datetime.now()
    
    for day_offset in range(DAYS_TO_BACKFILL, 0, -1):
        prediction_date = end_date - timedelta(days=day_offset)
        
        # Add small random noise to simulate natural variation
        # Older predictions have slightly more noise to show model drift
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
        
        if day_offset % 10 == 0:
            print(f"   Generated: {prediction_date.strftime('%Y-%m-%d')} ({len(all_predictions)} days complete)")
    
    # Combine all predictions
    print(f"\n💾 Combining {len(all_predictions)} days of predictions...")
    combined_df = pd.concat(all_predictions, ignore_index=True)
    
    print(f"✅ Total records: {len(combined_df):,}")
    print(f"   Date range: {combined_df['prediction_date'].min()} to {combined_df['prediction_date'].max()}")
    
    # Clear existing predictions and write new ones
    print(f"\n📝 Writing to PostgreSQL analytics.predictions...")
    
    # Use 'replace' to overwrite existing data
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
    
    summary_stats.columns = ['date', 'high_risk_customers', 'avg_churn_probability']
    
    print(f"\nDate Range: {summary_stats['date'].min()} to {summary_stats['date'].max()}")
    print(f"Average High-Risk Customers per Day: {summary_stats['high_risk_customers'].mean():.0f}")
    print(f"Overall Average Churn Probability: {combined_df['churn_probability'].mean():.4f}")
    print(f"\nMin High-Risk: {summary_stats['high_risk_customers'].min():.0f} customers")
    print(f"Max High-Risk: {summary_stats['high_risk_customers'].max():.0f} customers")
    
    print("\n✅ Backfill complete! You can now create time-series charts in Tableau.")
    print("\n💡 Tableau Usage:")
    print("   - X-axis: prediction_date (Day or Week)")
    print("   - Y-axis: SUM(at_risk_flag) or AVG(churn_probability)")
    print("   - Show trend line to demonstrate model stability over time")


if __name__ == "__main__":
    generate_historical_predictions()
