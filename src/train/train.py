"""
Model training script with MLflow tracking

This script:
1. Loads data from PostgreSQL (analytics.fct_customer_features)
2. Splits data into train/validation/test sets
3. Trains multiple models (XGBoost, Random Forest, Logistic Regression)
4. Logs experiments to MLflow
5. Registers the best model to MLflow Model Registry
"""

import os
import mlflow
import mlflow.sklearn
import mlflow.xgboost
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    precision_recall_curve, auc, recall_score, precision_score,
    f1_score, roc_auc_score, confusion_matrix, classification_report
)
import matplotlib.pyplot as plt
import seaborn as sns

# Import works differently locally vs in Docker
try:
    from train.model import ChurnModelTrainer  # For Docker/Airflow
except ModuleNotFoundError:
    from model import ChurnModelTrainer  # For local testing


# MLflow tracking URI (points to Docker MLflow server)
MLFLOW_TRACKING_URI = os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5000')

# PostgreSQL connection (use different ports for local vs Docker)
DB_CONN = os.getenv('DB_CONN', "postgresql://airflow:airflow@localhost:5433/telco_churn")


def load_data_from_postgres():
    """
    Load feature table from PostgreSQL
    """
    engine = create_engine(DB_CONN)
    
    query = """
    SELECT * FROM analytics.fct_customer_features
    """
    
    df = pd.read_sql(query, engine)
    print(f"✅ Loaded {len(df)} rows from analytics.fct_customer_features")
    
    return df


def prepare_data(df, test_size=0.2, val_size=0.1):
    """
    Prepare train/validation/test splits
    
    Args:
        df: Feature dataframe
        test_size: Proportion for test set
        val_size: Proportion for validation set (from remaining data)
    
    Returns:
        X_train, X_val, X_test, y_train, y_val, y_test
    """
    # Separate features and target
    target_col = 'has_churned'  # Target column from dbt model
    id_cols = ['customer_id']  # Don't use as features
    
    X = df.drop(columns=[target_col] + id_cols)
    y = df[target_col]
    
    # First split: train+val vs test
    X_temp, X_test, y_temp, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y
    )
    
    # Second split: train vs val
    val_ratio = val_size / (1 - test_size)
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp, test_size=val_ratio, random_state=42, stratify=y_temp
    )
    
    print(f"\n📊 Data Split:")
    print(f"  Training:   {len(X_train):,} samples ({y_train.mean():.2%} churn)")
    print(f"  Validation: {len(X_val):,} samples ({y_val.mean():.2%} churn)")
    print(f"  Test:       {len(X_test):,} samples ({y_test.mean():.2%} churn)")
    
    return X_train, X_val, X_test, y_train, y_val, y_test


def calculate_metrics(y_true, y_pred, y_pred_proba):
    """
    Calculate comprehensive evaluation metrics
    """
    # Precision-Recall AUC (best for imbalanced data)
    precision, recall, _ = precision_recall_curve(y_true, y_pred_proba)
    pr_auc = auc(recall, precision)
    
    # Standard metrics
    roc_auc = roc_auc_score(y_true, y_pred_proba)
    f1 = f1_score(y_true, y_pred)
    precision_score_val = precision_score(y_true, y_pred)
    recall_score_val = recall_score(y_true, y_pred)
    
    # Business metric: Recall @ Top 10%
    # (Of customers we predict as high-risk, how many actually churn?)
    top_10_threshold = np.percentile(y_pred_proba, 90)
    top_10_predictions = (y_pred_proba >= top_10_threshold).astype(int)
    recall_at_10 = recall_score(y_true, top_10_predictions)
    
    return {
        'pr_auc': pr_auc,
        'roc_auc': roc_auc,
        'f1_score': f1,
        'precision': precision_score_val,
        'recall': recall_score_val,
        'recall_at_top_10_percent': recall_at_10
    }


def plot_confusion_matrix(y_true, y_pred, model_name):
    """
    Create confusion matrix plot
    """
    cm = confusion_matrix(y_true, y_pred)
    
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
    plt.title(f'Confusion Matrix - {model_name}')
    plt.ylabel('Actual')
    plt.xlabel('Predicted')
    plt.tight_layout()
    
    # Save to temporary file
    plot_path = f'/tmp/confusion_matrix_{model_name}.png'
    plt.savefig(plot_path)
    plt.close()
    
    return plot_path


def train_model(model_type, X_train, X_val, y_train, y_val, feature_names):
    """
    Train a single model and log to MLflow
    
    Returns:
        dict with metrics
    """
    with mlflow.start_run(run_name=f"{model_type}_model"):
        # Log parameters
        mlflow.log_param("model_type", model_type)
        mlflow.log_param("n_train_samples", len(X_train))
        mlflow.log_param("n_features", X_train.shape[1])
        mlflow.log_param("class_balance_train", y_train.mean())
        
        # Train model
        print(f"\n🚀 Training {model_type}...")
        trainer = ChurnModelTrainer(model_type=model_type)
        trainer.fit(X_train, y_train)
        
        # Validation predictions
        y_val_pred = trainer.predict(X_val)
        y_val_proba = trainer.predict_proba(X_val)[:, 1]
        
        # Calculate metrics
        metrics = calculate_metrics(y_val, y_val_pred, y_val_proba)
        
        # Log metrics
        for metric_name, metric_value in metrics.items():
            mlflow.log_metric(metric_name, metric_value)
        
        print(f"  ✅ PR-AUC: {metrics['pr_auc']:.4f}")
        print(f"  ✅ Recall@Top10%: {metrics['recall_at_top_10_percent']:.4f}")
        
        # Log confusion matrix
        cm_path = plot_confusion_matrix(y_val, y_val_pred, model_type)
        mlflow.log_artifact(cm_path)
        
        # Log feature importance
        feature_importance = trainer.get_feature_importance(feature_names)
        if feature_importance:
            # Save as artifact
            importance_df = pd.DataFrame([
                {'feature': k, 'importance': v}
                for k, v in sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
            ])
            importance_path = f'/tmp/feature_importance_{model_type}.csv'
            importance_df.to_csv(importance_path, index=False)
            mlflow.log_artifact(importance_path)
        
        # Log model
        if model_type == 'xgboost':
            mlflow.xgboost.log_model(trainer.model, "model")
        else:
            mlflow.sklearn.log_model(trainer, "model")
        
        return metrics, trainer


def main():
    """
    Main training pipeline
    """
    print("=" * 80)
    print("🚀 TELCO CHURN MODEL TRAINING")
    print("=" * 80)
    
    # Set MLflow tracking URI
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment("telco_churn_training")
    
    # Load data
    df = load_data_from_postgres()
    
    # Prepare data
    X_train, X_val, X_test, y_train, y_val, y_test = prepare_data(df)
    feature_names = X_train.columns.tolist()
    
    # Train multiple models
    model_types = ['xgboost', 'random_forest', 'logistic_regression']
    results = {}
    
    for model_type in model_types:
        metrics, trainer = train_model(
            model_type, X_train, X_val, y_train, y_val, feature_names
        )
        results[model_type] = {'metrics': metrics, 'trainer': trainer}
    
    # Find best model based on PR-AUC
    best_model_type = max(results.keys(), key=lambda k: results[k]['metrics']['pr_auc'])
    best_metrics = results[best_model_type]['metrics']
    best_trainer = results[best_model_type]['trainer']
    
    print("\n" + "=" * 80)
    print(f"🏆 BEST MODEL: {best_model_type}")
    print(f"  PR-AUC: {best_metrics['pr_auc']:.4f}")
    print(f"  Recall@Top10%: {best_metrics['recall_at_top_10_percent']:.4f}")
    print("=" * 80)
    
    # Test set evaluation for best model
    y_test_pred = best_trainer.predict(X_test)
    y_test_proba = best_trainer.predict_proba(X_test)[:, 1]
    test_metrics = calculate_metrics(y_test, y_test_pred, y_test_proba)
    
    print(f"\n📊 Test Set Performance:")
    print(f"  PR-AUC: {test_metrics['pr_auc']:.4f}")
    print(f"  ROC-AUC: {test_metrics['roc_auc']:.4f}")
    print(f"  Recall@Top10%: {test_metrics['recall_at_top_10_percent']:.4f}")
    
    # Register best model
    with mlflow.start_run(run_name=f"best_model_{best_model_type}"):
        mlflow.log_param("model_type", best_model_type)
        mlflow.log_param("is_best_model", True)
        
        for metric_name, metric_value in test_metrics.items():
            mlflow.log_metric(f"test_{metric_name}", metric_value)
        
        # Register model
        if best_model_type == 'xgboost':
            model_uri = mlflow.xgboost.log_model(
                best_trainer.model, 
                "model",
                registered_model_name="telco_churn_best_model"
            ).model_uri
        else:
            model_uri = mlflow.sklearn.log_model(
                best_trainer,
                "model",
                registered_model_name="telco_churn_best_model"
            ).model_uri
        
        print(f"\n✅ Best model registered: {model_uri}")
    
    print("\n🎉 Training complete! View results at http://localhost:5000")
    
    return best_model_type, test_metrics


if __name__ == "__main__":
    main()
