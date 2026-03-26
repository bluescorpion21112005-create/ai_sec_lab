#!/usr/bin/env python3
"""
Core AI Engine for Security Lab
"""

import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

class AISecurityEngine:
    """Core AI engine for security analysis"""
    
    def __init__(self, model_path: str = "models/"):
        self.model_path = Path(model_path)
        self.model_path.mkdir(exist_ok=True)
        
        # Models
        self.subdomain_model: Optional[RandomForestClassifier] = None
        self.sqli_model: Optional[GradientBoostingClassifier] = None
        self.vectorizer = TfidfVectorizer(max_features=1000)
        self.scaler = StandardScaler()
        
        self._load_models()
    
    def _load_models(self):
        """Load saved models if they exist"""
        subdomain_path = self.model_path / "subdomain_model.pkl"
        sqli_path = self.model_path / "sqli_model.pkl"
        
        if subdomain_path.exists():
            self.subdomain_model = joblib.load(subdomain_path)
            logger.info("Loaded subdomain model")
        
        if sqli_path.exists():
            self.sqli_model = joblib.load(sqli_path)
            logger.info("Loaded SQLi model")
    
    def save_models(self):
        """Save models to disk"""
        if self.subdomain_model:
            joblib.dump(self.subdomain_model, self.model_path / "subdomain_model.pkl")
        
        if self.sqli_model:
            joblib.dump(self.sqli_model, self.model_path / "sqli_model.pkl")
        
        logger.info("Models saved")
    
    def extract_subdomain_features(self, subdomain: str) -> np.ndarray:
        """Extract features from subdomain for ML"""
        name_part = subdomain.split('.')[0]
        
        features = np.array([[
            len(name_part),
            name_part.count('.'),
            name_part.count('-'),
            sum(c.isdigit() for c in name_part),
            int(any(w in name_part for w in ['api', 'admin', 'dev', 'test']))
        ]])
        
        return features
    
    def predict_subdomain_live(self, subdomain: str) -> float:
        """Predict if subdomain is likely live"""
        if self.subdomain_model is None:
            return 0.5
        
        features = self.extract_subdomain_features(subdomain)
        proba = self.subdomain_model.predict_proba(features)[0][1]
        return float(proba)
    
    def predict_sqli(self, text: str) -> float:
        """Predict if text contains SQL injection"""
        if self.sqli_model is None:
            return 0.0
        
        features = self.vectorizer.transform([text]).toarray()
        proba = self.sqli_model.predict_proba(features)[0][1]
        return float(proba)