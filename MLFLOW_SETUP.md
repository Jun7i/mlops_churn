# MLflow Setup Guide

## What Changed

Your project now uses **local MLflow** instead of Azure ML for model training and tracking:

```
Your Complete Pipeline:
1. CSV → PostgreSQL (raw_data) ✅
2. dbt transforms → analytics.fct_customer_features ✅
3. MLflow trains models (XGBoost, RF, Logistic Regression) 🆕
4. Best model registered in MLflow Model Registry 🆕
5. Batch predictions using registered model 🆕
6. BI dashboards from PostgreSQL predictions table ✅
```

## Architecture

- **MLflow Tracking Server** runs in Docker on port 5000
- **Backend Store**: PostgreSQL (stores metrics, parameters, runs)
- **Artifact Store**: Docker volume (stores models, plots)
- **Model Registry**: Built-in MLflow registry for versioning models

## Setup Steps

### 1. Rebuild Docker Services

```powershell
# Stop existing services
docker-compose down

# Rebuild with new MLflow service
docker-compose build --no-cache

# Start all services
docker-compose up -d
```

Wait ~2 minutes for services to initialize.

### 2. Verify Services Are Running

```powershell
docker-compose ps
```

You should see:
- ✅ `postgres` (port 5433)
- ✅ `airflow-webserver` (port 8080)
- ✅ `airflow-scheduler`
- ✅ `mlflow` (port 5000) 🆕

### 3. Access MLflow UI

Open your browser to: **http://localhost:5000**

You should see the MLflow UI with:
- Experiments list (empty initially)
- Model Registry tab
- No runs yet (will populate after training)

### 4. Test the Complete Pipeline

#### Option A: Run via Airflow (Recommended)

1. Go to http://localhost:8080 (login: `admin`/`admin`)
2. Find `telco_churn_pipeline` DAG
3. Click the **play** button to trigger
4. Watch tasks execute:
   - ✅ `load_csv_to_postgres`
   - ✅ `validate_data_quality`
   - ✅ `run_dbt_models`
   - ✅ `test_dbt_models`
   - 🆕 `train_models_with_mlflow`
   - 🆕 `run_batch_predictions`

#### Option B: Test Training Script Locally

```powershell
# Install dependencies locally (optional)
pip install -r requirements.txt

# Run training script directly
cd src/train
python train.py
```

### 5. View Training Results in MLflow

After training completes, go to http://localhost:5000:

1. Click **"telco_churn_training"** experiment
2. You'll see 4 runs:
   - `xgboost_model`
   - `random_forest_model`
   - `logistic_regression_model`
   - `best_model_<type>` (the winner)

3. Click on any run to see:
   - **Parameters**: model_type, n_features, class_balance
   - **Metrics**: pr_auc, recall_at_top_10_percent, f1_score
   - **Artifacts**: confusion_matrix.png, feature_importance.csv
   - **Model**: The trained model (downloadable)

4. Go to **Models** tab to see:
   - `telco_churn_best_model` (registered model)
   - Latest version ready for serving

### 6. View Predictions in PostgreSQL

```powershell
# Connect to database
docker exec -it telcocustomerchurn-postgres-1 psql -U airflow -d telco_churn
```

```sql
-- View predictions
SELECT * FROM analytics.predictions LIMIT 10;

-- High-risk customers
SELECT COUNT(*) 
FROM analytics.predictions 
WHERE at_risk_flag = 1;

-- Top 10 highest risk customers
SELECT customer_id, churn_probability 
FROM analytics.predictions 
ORDER BY churn_probability DESC 
LIMIT 10;
```

## What Each Model Does

### Training Process
1. **Loads data** from `analytics.fct_customer_features`
2. **Splits data**: 70% train, 10% validation, 20% test
3. **Trains 3 models** with class imbalance handling:
   - **XGBoost**: `scale_pos_weight=3` to handle imbalance
   - **Random Forest**: `class_weight='balanced'`
   - **Logistic Regression**: `class_weight='balanced'`
4. **Evaluates** on validation set using PR-AUC (best for imbalanced data)
5. **Selects best model** based on PR-AUC score
6. **Registers** best model to MLflow Model Registry
7. **Logs everything**: metrics, plots, feature importance

### Key Metrics Tracked
- **PR-AUC** (Precision-Recall AUC): Best metric for imbalanced data
- **Recall @ Top 10%**: Of the 10% we flag as high-risk, how many actually churn?
- **ROC-AUC**: Standard classification metric
- **F1 Score**: Balance of precision and recall
- **Confusion Matrix**: Visual breakdown of predictions

## Airflow Tasks Explained

### Task 1-4: Data Pipeline (Existing)
- Load CSV → PostgreSQL
- Validate data quality
- Run dbt transformations
- Test dbt models

### Task 5: `train_models_with_mlflow` (NEW)
- Reads from `analytics.fct_customer_features`
- Trains XGBoost, Random Forest, Logistic Regression
- Logs all experiments to MLflow
- Registers best model (by PR-AUC)
- Returns best model name and metrics

### Task 6: `run_batch_predictions` (NEW)
- Loads best model from MLflow Model Registry
- Scores all customers in feature table
- Writes predictions to `analytics.predictions`:
  - `customer_id`
  - `churn_probability` (0.0 to 1.0)
  - `at_risk_flag` (1 if probability >= 0.5)
  - `prediction_date`

## Troubleshooting

### MLflow UI not loading?
```powershell
# Check MLflow logs
docker-compose logs -f mlflow

# Should say "Listening at: http://0.0.0.0:5000"
```

### Training task fails?
```powershell
# Check Airflow scheduler logs
docker-compose logs -f airflow-scheduler

# Or view in Airflow UI → Task → Log
```

### Common Issues

**"Import train.train could not be resolved"** (in IDE)
- This is a Pylance warning, ignore it
- The import works inside Docker because `/opt/airflow/src` is on Python path
- Only matters at runtime, not in your IDE

**"No module named mlflow"**
- Rebuild Docker images: `docker-compose build --no-cache`
- Check `requirements.txt` has `mlflow>=2.9.2`

**"Model not found in registry"**
- Training must complete successfully first
- Check MLflow UI → Models tab for `telco_churn_best_model`
- If missing, re-run training task

## Next Steps

### 1. Connect Power BI / Superset to PostgreSQL

**Connection details:**
- Host: `localhost`
- Port: `5433`
- Database: `telco_churn`
- Schema: `analytics`
- Tables: `fct_customer_features`, `predictions`

**Dashboard ideas:**
- Overall churn rate trend
- High-risk customer segments
- Feature importance (from CSV artifact)
- Revenue at risk (customers × ARPU)
- Retention campaign ROI

### 2. Optimize Models (Later)

Update `src/train/model.py` with better hyperparameters:
```python
'xgboost': {
    'max_depth': 8,  # Increased from 6
    'learning_rate': 0.05,  # Decreased for better generalization
    'n_estimators': 200,  # Increased from 100
    'scale_pos_weight': 3,
}
```

### 3. Add Model Monitoring (Advanced)

Track model performance over time:
- Prediction accuracy vs actual churn
- Data drift detection
- Model retraining triggers

## Resources

- **MLflow UI**: http://localhost:5000
- **Airflow UI**: http://localhost:8080
- **PostgreSQL**: `localhost:5433` (pgAdmin)
- **MLflow Docs**: https://mlflow.org/docs/latest/tracking.html
- **Model Registry**: https://mlflow.org/docs/latest/model-registry.html
