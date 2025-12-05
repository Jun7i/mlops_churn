"""
Model definitions and preprocessing pipeline for churn prediction
"""

from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import numpy as np
import pandas as pd


class ChurnModelTrainer:
    """
    Unified trainer for different model types with preprocessing
    """
    
    def __init__(self, model_type='xgboost', **model_params):
        """
        Initialize model trainer
        
        Args:
            model_type: 'xgboost', 'random_forest', or 'logistic_regression'
            **model_params: Additional parameters for the model
        """
        self.model_type = model_type
        self.model = self._get_model(model_params)
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.numeric_columns = None
        self.categorical_columns = None
        
    def _get_model(self, params):
        """Get model instance based on type"""
        default_params = {
            'xgboost': {
                'max_depth': 6,
                'learning_rate': 0.1,
                'n_estimators': 100,
                'scale_pos_weight': 3,  # Handle class imbalance
                'random_state': 42,
                'eval_metric': 'aucpr'
            },
            'random_forest': {
                'n_estimators': 100,
                'max_depth': 10,
                'class_weight': 'balanced',  # Handle class imbalance
                'random_state': 42,
                'n_jobs': -1
            },
            'logistic_regression': {
                'class_weight': 'balanced',  # Handle class imbalance
                'max_iter': 1000,
                'random_state': 42
            }
        }
        
        # Merge default params with provided params
        model_params = {**default_params.get(self.model_type, {}), **params}
        
        if self.model_type == 'xgboost':
            return XGBClassifier(**model_params)
        elif self.model_type == 'random_forest':
            return RandomForestClassifier(**model_params)
        elif self.model_type == 'logistic_regression':
            return LogisticRegression(**model_params)
        else:
            raise ValueError(f"Unknown model type: {self.model_type}")
    
    def _identify_column_types(self, X):
        """Identify numeric and categorical columns"""
        self.numeric_columns = X.select_dtypes(include=['int64', 'float64', 'bool']).columns.tolist()
        self.categorical_columns = X.select_dtypes(include=['object', 'category']).columns.tolist()
        
    def _encode_features(self, X, is_training=True):
        """Encode categorical features to numeric"""
        X = X.copy()
        
        for col in self.categorical_columns:
            if is_training:
                # Fit encoder on training data
                self.label_encoders[col] = LabelEncoder()
                X[col] = self.label_encoders[col].fit_transform(X[col].astype(str))
            else:
                # Use fitted encoder
                # Handle unseen categories
                le = self.label_encoders[col]
                X[col] = X[col].astype(str).map(lambda x: le.transform([x])[0] if x in le.classes_ else -1)
        
        return X
    
    def fit(self, X_train, y_train):
        """
        Fit the model with preprocessing
        """
        # Identify column types
        self._identify_column_types(X_train)
        
        # Encode categorical features
        X_train_encoded = self._encode_features(X_train, is_training=True)
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train_encoded)
        
        # Train model
        self.model.fit(X_train_scaled, y_train)
        
        return self
    
    def predict(self, X):
        """Predict class labels"""
        X_encoded = self._encode_features(X, is_training=False)
        X_scaled = self.scaler.transform(X_encoded)
        return self.model.predict(X_scaled)
    
    def predict_proba(self, X):
        """Predict class probabilities"""
        X_encoded = self._encode_features(X, is_training=False)
        X_scaled = self.scaler.transform(X_encoded)
        return self.model.predict_proba(X_scaled)
    
    def get_feature_importance(self, feature_names):
        """
        Get feature importance (works for tree-based models)
        """
        if hasattr(self.model, 'feature_importances_'):
            importance = self.model.feature_importances_
            return dict(zip(feature_names, importance))
        elif hasattr(self.model, 'coef_'):
            # For logistic regression, use absolute coefficients
            importance = np.abs(self.model.coef_[0])
            return dict(zip(feature_names, importance))
        else:
            return None
