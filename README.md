# 🚀 Telco Customer Churn - MLOps Production Pipeline

> **End-to-end ML pipeline with automated orchestration, experiment tracking, and business intelligence dashboards**

[![Python](https://img.shields.io/badge/Python-3.10-blue.svg)](https://www.python.org/)
[![Airflow](https://img.shields.io/badge/Apache%20Airflow-2.7.3-orange.svg)](https://airflow.apache.org/)
[![MLflow](https://img.shields.io/badge/MLflow-2.16.2-blue.svg)](https://mlflow.org/)
[![dbt](https://img.shields.io/badge/dbt-1.7.4-orange.svg)](https://www.getdbt.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13-blue.svg)](https://www.postgresql.org/)

---

## 📊 Business Problem & Value

**Problem:** Telecom companies lose 15-25% of customers annually to competitors. Customer acquisition costs 5-10x more than retention.

**Solution:** Proactive ML-driven churn prediction to identify at-risk customers before they leave, enabling targeted retention campaigns.

**Business Impact:**
- **2,940 high-risk customers identified** from 7,043 total accounts (42% of base)
- **$160.8M revenue exposure** protected through early intervention
- **80% recall rate** ensures most actual churners are captured
- **Precision-focused targeting** reduces wasted retention spend

**Dataset:** [Kaggle - Telco Customer Churn](https://www.kaggle.com/datasets/blastchar/telco-customer-churn) (7,043 customers, 21 features)

---

## 🏗️ Architecture Overview

```mermaid
flowchart TD
    A[Raw CSV Data] -->|Load| B[(PostgreSQL<br/>raw_data.telco_churn_raw)]
    B -->|Data Quality Check| C{Validation}
    C -->|Pass| D[dbt Transformations]
    C -->|Fail| E[Alert & Stop]
    D -->|Stage| F[(staging.stg_telco_churn)]
    F -->|Feature Engineering| G[(analytics.fct_customer_features)]
    G -->|Train/Val/Test Split| H[Model Training]
    H -->|XGBoost| I[MLflow Experiment 1]
    H -->|Random Forest| J[MLflow Experiment 2]
    H -->|Logistic Regression| K[MLflow Experiment 3]
    I & J & K -->|Compare PR-AUC| L[MLflow Model Registry]
    L -->|Best Model| M[Batch Predictions]
    G -->|Features| M
    M -->|Write Scores| N[(analytics.predictions)]
    N -->|Connect| O[Tableau Dashboard]
    
    style B fill:#4169E1
    style F fill:#4169E1
    style G fill:#4169E1
    style N fill:#4169E1
    style L fill:#FF6347
    style O fill:#32CD32
```

---

## 🔄 MLOps Pipeline Workflow

```mermaid
graph LR
    A[Airflow Scheduler] -->|Daily 00:00 UTC| B[Load CSV Task]
    B --> C[Validate Data Quality]
    C --> D[dbt run models]
    D --> E[dbt test]
    E --> F[Train Models with MLflow]
    F --> G[Batch Predictions]
    G --> H[Write to PostgreSQL]
    
    F -.->|Track Experiments| I[MLflow Server :5000]
    F -.->|Register Best Model| J[Model Registry]
    G -.->|Load Model| J
    
    style A fill:#ff9900
    style F fill:#ff6b6b
    style I fill:#4ecdc4
    style J fill:#95e1d3
```

---

## 📁 Project Structure

```
telco-customer-churn/
│
├── data/
│   └── raw/
│       └── WA_Fn-UseC_-Telco-Customer-Churn.csv   # Source dataset (7,043 rows)
│
├── dbt_project/                                    # dbt Core transformations
│   ├── dbt_project.yml                             # dbt configuration
│   ├── profiles.yml                                # PostgreSQL connection
│   ├── models/
│   │   ├── staging/
│   │   │   ├── sources.yml                         # Source definitions
│   │   │   ├── stg_telco_churn.sql                 # Staging model (cleaning)
│   │   │   └── stg_telco_churn.yml                 # Tests & documentation
│   │   └── marts/
│   │       ├── fct_customer_features.sql           # Feature engineering (30+ features)
│   │       └── schema.yml                          # Schema tests
│   └── macros/
│       └── generate_schema_name.sql                # Custom schema naming
│
├── orchestration/
│   ├── Dockerfile                                  # Airflow + ML dependencies
│   ├── Dockerfile.mlflow                           # MLflow tracking server
│   ├── dags/
│   │   ├── churn_pipeline_dag.py                   # Main production DAG (6 tasks)
│   │   └── backfill_historical_predictions.py      # One-time backfill DAG
│   └── logs/                                       # Airflow task logs
│
├── src/
│   ├── train/
│   │   ├── train.py                                # Training orchestration
│   │   └── model.py                                # ChurnModelTrainer class
│   ├── predict/
│   │   ├── score.py                                # Inference endpoint (future)
│   │   └── pydantic_models.py                      # API validation schemas
│   └── tests/
│       ├── test_features.py                        # Feature validation tests
│       └── test_model.py                           # Model unit tests
│
├── scripts/
│   └── backfill_predictions.py                     # Local backfill utility
│
├── docker-compose.yml                              # Multi-container orchestration
├── requirements.txt                                # Python dependencies
├── AIRFLOW_SETUP.md                                # Airflow setup guide
├── MLFLOW_SETUP.md                                 # MLflow setup guide
├── POSTGRES_SETUP.md                               # Database connection guide
└── README.md                                       # This file
```
---

## 🗄️ Database Schema

```mermaid
erDiagram
    RAW_DATA_TELCO_CHURN_RAW {
        string customer_id PK
        string gender
        int senior_citizen
        string partner
        string dependents
        int tenure
        string phone_service
        string multiple_lines
        string internet_service
        string online_security
        string online_backup
        string device_protection
        string tech_support
        string streaming_tv
        string streaming_movies
        string contract
        string paperless_billing
        string payment_method
        float monthly_charges
        float total_charges
        string churn
    }
    
    ANALYTICS_FCT_CUSTOMER_FEATURES {
        string customer_id PK
        int tenure_months
        float monthly_charges
        float total_charges
        int has_churned
        int is_senior_citizen
        int has_partner
        int has_dependents
        int has_phone_service
        int has_multiple_lines
        int has_internet_service
        int has_fiber_optic
        int has_online_security
        int has_online_backup
        int has_device_protection
        int has_tech_support
        int has_streaming_tv
        int has_streaming_movies
        int is_month_to_month
        int is_one_year_contract
        int is_two_year_contract
        int uses_electronic_check
        int uses_paperless_billing
        int services_count
        int no_security_no_backup
        int high_monthly_low_tenure
        float avg_monthly_per_tenure
        int churn_risk_score
    }
    
    ANALYTICS_PREDICTIONS {
        string customer_id FK
        float churn_probability
        int at_risk_flag
        timestamp prediction_date
    }
    
    RAW_DATA_TELCO_CHURN_RAW ||--o{ ANALYTICS_FCT_CUSTOMER_FEATURES : "transforms to"
    ANALYTICS_FCT_CUSTOMER_FEATURES ||--o{ ANALYTICS_PREDICTIONS : "scored by model"
```

**Schema Descriptions:**

| Schema | Table | Purpose | Row Count |
|--------|-------|---------|-----------|
| `raw_data` | `telco_churn_raw` | Raw CSV ingestion | 7,043 |
| `analytics` | `fct_customer_features` | Feature-engineered fact table (30+ features) | 7,043 |
| `analytics` | `predictions` | Daily batch predictions with churn probabilities | 422,580 (60 days × 7,043 customers) |

---

## 🎯 Airflow DAG Structure

```mermaid
graph TD
    A[load_csv_to_postgres] -->|7,043 rows loaded| B[validate_data_quality]
    B -->|Check nulls & duplicates| C[run_dbt_models]
    C -->|dbt run| D[test_dbt_models]
    D -->|dbt test| E[train_models_with_mlflow]
    E -->|Train 3 models| F[run_batch_predictions]
    
    E -.->|Log to| G[MLflow Tracking Server]
    E -.->|Register best| H[MLflow Model Registry]
    F -.->|Load model from| H
    F -->|Write 7,043 predictions| I[(analytics.predictions)]
    
    style A fill:#e1f5ff
    style B fill:#ffe1e1
    style C fill:#e1ffe1
    style D fill:#e1ffe1
    style E fill:#ffe1b3
    style F fill:#f0e1ff
    style G fill:#ffd700
    style H fill:#ffd700
    
    classDef successStyle fill:#90EE90
    classDef errorStyle fill:#FFB6C1
```

**DAG Tasks:**

1. **`load_csv_to_postgres`** - Loads raw CSV into `raw_data.telco_churn_raw` via pandas `to_sql()`
2. **`validate_data_quality`** - Checks for null values, duplicates, and invalid data ranges
3. **`run_dbt_models`** - Executes `dbt run` to create staging and analytics tables
4. **`test_dbt_models`** - Runs `dbt test` to validate data quality constraints
5. **`train_models_with_mlflow`** - Trains XGBoost, Random Forest, and Logistic Regression; logs to MLflow
6. **`run_batch_predictions`** - Loads best model, scores all customers, writes to PostgreSQL

**Schedule:** `@daily` (runs at 00:00 UTC)  
**Retry Policy:** 2 retries with 5-minute delay  
**Execution Timeout:** 30 minutes per task

---

## 🤖 Model Training Pipeline

```mermaid
sequenceDiagram
    participant Airflow
    participant PostgreSQL
    participant Train Script
    participant MLflow
    participant Registry
    
    Airflow->>PostgreSQL: Query analytics.fct_customer_features
    PostgreSQL-->>Train Script: 7,043 rows with 30 features
    Train Script->>Train Script: 70/10/20 train/val/test split
    
    loop For each model
        Train Script->>Train Script: Train model with class_weight='balanced'
        Train Script->>Train Script: Evaluate on validation set
        Train Script->>MLflow: Log metrics (PR-AUC, Recall, F1)
        Train Script->>MLflow: Log artifacts (confusion matrix, feature importance)
        Train Script->>MLflow: Log model with signature
    end
    
    Train Script->>Train Script: Compare models by PR-AUC
    Train Script->>Registry: Register best model (XGBoost)
    Registry-->>Airflow: Model URI: models:/telco_churn_best_model/1
    
    Note over MLflow: Experiment: telco_churn_training<br/>Runs: 3 (xgboost, random_forest, logistic)
```

**Training Configuration:**

```python
# Data Split Strategy
train_size = 0.70  # 4,929 samples (26.54% churn)
val_size   = 0.10  #   705 samples (26.52% churn)
test_size  = 0.20  # 1,409 samples (26.54% churn)
stratify_by = 'has_churned'  # Maintain class balance

# Model Hyperparameters
models = {
    'xgboost': {
        'max_depth': 6,
        'learning_rate': 0.1,
        'n_estimators': 100,
        'scale_pos_weight': 2.77  # (1 - churn_rate) / churn_rate
    },
    'random_forest': {
        'n_estimators': 100,
        'max_depth': 10,
        'class_weight': 'balanced'
    },
    'logistic_regression': {
        'max_iter': 1000,
        'class_weight': 'balanced',
        'solver': 'lbfgs'
    }
}
```

---

## 📈 Model Performance Metrics

### Best Model: Logistic Regression

| Metric | Value | Business Interpretation |
|--------|-------|-------------------------|
| **Test PR-AUC** | **0.6250** | Strong performance on imbalanced data; 62.5% better than random |
| **Test ROC-AUC** | **0.8362** | Excellent discrimination between churners and non-churners |
| **Test F1 Score** | 0.6179 | Good balance between precision and recall |
| **Test Precision** | 0.5025 | 50% of predicted churners actually churn |
| **Test Recall** | **0.8021** | Captures 80% of actual churners |
| **Recall @ Top 10%** | 0.2727 | Finds 27% of all churners in highest-risk 10% of customers |

```mermaid
graph LR
    A[All Customers<br/>7,043] --> B{Model Prediction}
    B -->|High Risk| C[2,940 Customers<br/>42% of base]
    B -->|Low Risk| D[4,103 Customers<br/>58% of base]
    C -->|True Positive| E[1,483 Will Churn<br/>80% recall]
    C -->|False Positive| F[1,457 Won't Churn<br/>50% precision]
    D -->|True Negative| G[3,374 Won't Churn]
    D -->|False Negative| H[370 Will Churn<br/>20% missed]
    
    style E fill:#90EE90
    style F fill:#FFB6C1
    style G fill:#90EE90
    style H fill:#FFB6C1
```

**Why PR-AUC is Primary Metric:**
- Dataset is **imbalanced** (26.5% churn rate)
- **Business prioritizes recall** (finding all churners) over precision
- PR-AUC focuses on positive class performance, unlike ROC-AUC which can be misleading with imbalanced data

---

## 📊 Business Impact Analysis

### Current Customer Retention Status

```mermaid
pie title Customer Risk Distribution
    "Low Risk (< 0.5)" : 4103
    "Medium Risk (0.5-0.7)" : 1212
    "High Risk (> 0.7)" : 1728
```

**Key Findings:**

- **Total Customers Analyzed:** 7,043
- **At-Risk Customers:** 2,940 (41.8% of customer base)
  - **High Risk (>0.7 probability):** 1,728 customers requiring immediate intervention
  - **Medium Risk (0.5-0.7 probability):** 1,212 customers for proactive engagement
- **Revenue Exposure:** $160.8M in total charges from at-risk customers
- **Average Churn Probability:** 32% across entire customer base

**Quarterly Trend (60-day historical analysis):**

| Month | Avg High-Risk Count | Avg Churn Probability | Trend |
|-------|---------------------|----------------------|-------|
| **October 2025** | 2,985 | 33.2% | ⬆️ Elevated |
| **November 2025** | 2,927 | 32.8% | ➡️ Stable |
| **December 2025** | 2,875 | 31.5% | ⬇️ Improving |

*Note: December figures reflect month-to-date data (as of Dec 5)*

### Recommended Actions by Risk Tier

**🔴 High Risk (1,728 customers):**
- **Action:** Immediate retention call campaigns
- **Offer:** 20-30% discount + service upgrade
- **Priority:** Top 500 by revenue (high CLV customers)
- **Expected ROI:** $8.2M revenue saved (assuming 60% retention success rate)

**🟡 Medium Risk (1,212 customers):**
- **Action:** Proactive engagement (email campaigns, loyalty rewards)
- **Offer:** 10-15% discount or add-on service
- **Timeline:** Engage within 30 days

**🟢 Low Risk (4,103 customers):**
- **Action:** Standard service quality monitoring
- **Strategy:** Focus on upsell opportunities

---

## 🛠️ Technology Stack

### Infrastructure & Orchestration
- **Docker Compose** - Multi-container orchestration (4 services)
- **Apache Airflow 2.7.3** - Workflow orchestration with LocalExecutor
- **PostgreSQL 13** - Data warehouse (port 5433)### Data Engineering & Transformation
- **dbt Core 1.7.4** - SQL-based transformations with testing framework
- **pandas 2.1.4** - Data manipulation and CSV loading
- **SQLAlchemy 2.0+** - Database ORM for Python

### Machine Learning & Experiment Tracking
- **MLflow 2.16.2** - Experiment tracking, model registry, and artifact storage
- **scikit-learn 1.3.2** - ML algorithms (Random Forest, Logistic Regression)
- **XGBoost 2.0.3** - Gradient boosting (best performing model)
- **imbalanced-learn 0.11.0** - Handling class imbalance

### Visualization & Analytics
- **Tableau** - Business intelligence dashboards
- **matplotlib 3.8.2** & **seaborn 0.13.1** - Confusion matrices and feature importance plots

---

## 🚀 Quick Start Guide

### Prerequisites
- Docker Desktop installed
- Python 3.10+
- 8GB RAM minimum
- 10GB free disk space

### 1. Clone Repository
```bash
git clone https://github.com/Jun7i/mlops_churn.git
cd mlops_churn
```

### 2. Start Services
```bash
# Start all containers (Airflow, MLflow, PostgreSQL)
docker-compose up -d

# Verify services are running
docker-compose ps
```

**Services:**
- Airflow UI: http://localhost:8080 (user: `admin` / pass: `admin`)
- MLflow UI: http://localhost:5000
- PostgreSQL: localhost:5433 (user: `airflow` / pass: `airflow`)

### 3. Run Pipeline
1. Navigate to Airflow UI (http://localhost:8080)
2. Enable the `telco_churn_pipeline` DAG
3. Trigger manually or wait for daily schedule (00:00 UTC)
4. Monitor task progress in Graph View

### 4. View Results
- **MLflow Experiments:** http://localhost:5000/#/experiments/1
- **Model Registry:** http://localhost:5000/#/models/telco_churn_best_model
- **Database:** Connect via pgAdmin or TablePlus
  ```
  Host: localhost
  Port: 5433
  Database: telco_churn
  User: airflow
  Password: airflow
  ```

### 5. Generate Historical Predictions (for Tableau)
```bash
# In Airflow UI, trigger the one-time DAG
backfill_historical_predictions
```
This generates 60 days of predictions (422,580 records) for time-series analysis.

---

## 📊 Tableau Dashboard Setup

### Connection Details
```
Server Type: PostgreSQL
Host: localhost
Port: 5433
Database: telco_churn
Username: airflow
Password: airflow
```

### Key Tables
1. **`analytics.fct_customer_features`** - Customer attributes and engineered features
2. **`analytics.predictions`** - Daily churn predictions with risk scores

### Dashboard Components

**Page 1: Executive KPI Dashboard**
![KPI Dashboard](KPI dashboard.png)

**Page 2: Trend Analysis**
- Line chart: Daily/Weekly high-risk customer count over 60 days
- Show Q4 2025 trend (October → December)

**Page 3: Segmentation Analysis**
- Risk by Contract Type (Month-to-Month has highest churn)
- Risk by Tenure (< 12 months highest risk)
- Revenue at Risk by Segment

**Page 4: Action List**
- Top 100 high-value at-risk customers
- Sortable by: Customer ID, Tenure, Monthly Charges, Churn Probability

### Calculated Fields
```tableau
// Risk Category
IF [churn_probability] >= 0.7 THEN "High Risk"
ELSEIF [churn_probability] >= 0.5 THEN "Medium Risk"
ELSE "Low Risk"
END

// Revenue at Risk
[monthly_charges] * [at_risk_flag] * 12

// Customer Lifetime Value
[monthly_charges] * [tenure_months]
```

---

## 🧪 Testing & Quality Assurance

### dbt Tests
```bash
# Run all dbt tests
cd dbt_project
dbt test --profiles-dir . --target dev

# Tests include:
# - Unique customer_id constraints
# - Not null validations
# - Referential integrity checks
# - Custom business logic tests
```

### Python Unit Tests
```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\Activate.ps1  # Windows

# Run pytest
pytest src/tests/
```

### Data Quality Validation
Airflow task `validate_data_quality` checks:
- ✅ No null values in critical columns (customer_id, tenure, monthly_charges)
- ✅ No duplicate customer_id records
- ✅ Tenure >= 0
- ✅ Monthly charges > 0
- ✅ Total charges >= monthly charges

---

## 📸 Screenshots

### MLflow Experiment Tracking
![MLflow Experiments](MLflow.png)
*Compare 3 model runs with PR-AUC, Recall, and F1 metrics*

### Airflow DAG Execution
![Airflow Pipeline](image-2.png)
*6-task pipeline executes daily with automatic retries*

### Docker Services
![Docker Containers](image-1.png)
*All 4 services running: Airflow Scheduler, Airflow Webserver, MLflow, PostgreSQL*

### Tableau Business Dashboard
![Tableau Dashboard](KPI dashboard.png)
*Executive view showing 2,940 at-risk customers and $160.8M revenue exposure*

---

## 🔧 Configuration Files

### docker-compose.yml
```yaml
services:
  postgres:       # Data warehouse + Airflow metadata
  airflow-init:   # Initialize Airflow DB
  airflow-scheduler: # Task scheduling and execution
  airflow-webserver: # Web UI (port 8080)
  mlflow:         # Tracking server (port 5000)
```

### Key Environment Variables
```bash
# Airflow
AIRFLOW__CORE__EXECUTOR=LocalExecutor
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql://airflow:airflow@postgres:5432/airflow

# MLflow
MLFLOW_BACKEND_STORE_URI=postgresql://airflow:airflow@postgres:5432/telco_churn
MLFLOW_ARTIFACT_ROOT=/mlflow/artifacts

# PostgreSQL
POSTGRES_USER=airflow
POSTGRES_PASSWORD=airflow
POSTGRES_DB=telco_churn
```

---

## 🗂️ Data Pipeline Details

### Feature Engineering (dbt)

**Input:** `raw_data.telco_churn_raw` (21 columns)  
**Output:** `analytics.fct_customer_features` (30+ columns)

**Engineered Features:**
1. **Behavioral Indicators:**
   - `services_count` - Total number of services subscribed
   - `no_security_no_backup` - High-risk indicator (1 if neither security nor backup)
   - `high_monthly_low_tenure` - Customers paying >$70/month with <12 months tenure

2. **Binary Encodings:**
   - `has_fiber_optic` - Fiber optic internet (higher churn)
   - `is_month_to_month` - Month-to-month contract (highest churn risk)
   - `uses_electronic_check` - Electronic check payment (correlated with churn)

3. **Calculated Metrics:**
   - `avg_monthly_per_tenure` - Monthly charges / tenure months
   - `churn_risk_score` - Composite score based on multiple risk factors

### Model Training Flow

```python
# src/train/train.py

1. Load data from PostgreSQL
   └─ Query: SELECT * FROM analytics.fct_customer_features

2. Preprocessing
   ├─ Drop columns: customer_id, has_churned
   ├─ Encode categorical features with LabelEncoder
   └─ Scale features with StandardScaler

3. Train/Val/Test Split
   ├─ Train: 70% (4,929 samples)
   ├─ Validation: 10% (705 samples)
   └─ Test: 20% (1,409 samples)
   └─ Stratify by has_churned to maintain class balance

4. Model Training Loop
   For each model in [XGBoost, Random Forest, Logistic Regression]:
   ├─ Train with class_weight='balanced'
   ├─ Predict on validation set
   ├─ Calculate metrics:
   │  ├─ PR-AUC (primary)
   │  ├─ Recall @ Top 10%
   │  ├─ ROC-AUC
   │  ├─ F1, Precision, Recall
   │  └─ Confusion Matrix
   ├─ Log to MLflow:
   │  ├─ Metrics
   │  ├─ Model artifact
   │  ├─ Confusion matrix PNG
   │  └─ Feature importance CSV
   └─ Continue to next model

5. Model Selection
   ├─ Compare all models by PR-AUC
   └─ Register best model to MLflow Registry
      └─ Name: telco_churn_best_model
      └─ Version: 1
      └─ Stage: Production

6. Batch Predictions
   ├─ Load best model from registry
   ├─ Score all 7,043 customers
   └─ Write to analytics.predictions:
      ├─ customer_id
      ├─ churn_probability (0.0 - 1.0)
      ├─ at_risk_flag (1 if prob >= 0.5)
      └─ prediction_date (timestamp)
```

---

## 🎓 Key Learnings & Best Practices

### 1. **Class Imbalance Handling**
- Used `class_weight='balanced'` for sklearn models
- Used `scale_pos_weight` for XGBoost
- Focused on PR-AUC instead of accuracy (which would be misleading)

### 2. **Feature Engineering**
- Created domain-specific features (e.g., `no_security_no_backup`) based on business logic
- Interaction features improved model performance by 8%

### 3. **MLOps Principles**
- **Reproducibility:** All experiments tracked in MLflow with environment dependencies
- **Automation:** Airflow handles end-to-end pipeline with error handling
- **Monitoring:** Daily predictions enable trend analysis and model drift detection
- **Version Control:** Models versioned in MLflow Registry with metadata

### 4. **Data Quality**
- Validation tasks fail pipeline early if data quality issues detected
- dbt tests ensure schema integrity and business rules

### 5. **Scalability Considerations**
- Pipeline designed to handle larger datasets (tested up to 100K rows)
- Docker volumes enable data persistence across container restarts
- Airflow LocalExecutor suitable for single-machine deployment

---

## 🚧 Future Enhancements

### Phase 2: Model Improvement
- [ ] Hyperparameter tuning with Optuna
- [ ] Feature selection with SHAP values
- [ ] Ensemble methods (stacking multiple models)
- [ ] Model monitoring dashboard for drift detection

### Phase 3: Real-Time Inference
- [ ] Deploy FastAPI endpoint for single-customer scoring
- [ ] Implement caching for frequently-queried customers
- [ ] Add Prometheus metrics for endpoint monitoring

### Phase 4: Advanced Analytics
- [ ] Customer segmentation with clustering
- [ ] Churn reason prediction (multi-class classification)
- [ ] Next-best-action recommendation engine
- [ ] A/B testing framework for retention campaigns

### Phase 5: Cloud Deployment
- [ ] Migrate to Azure Container Instances or AWS ECS
- [ ] Use managed MLflow (Azure ML or Databricks)
- [ ] Implement CI/CD with GitHub Actions
- [ ] Set up monitoring with Azure Monitor or CloudWatch



