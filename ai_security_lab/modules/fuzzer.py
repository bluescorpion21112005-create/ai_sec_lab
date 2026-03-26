#!/usr/bin/env python3
"""
ML-powered fuzzer with crash detection
Educational purpose only - Use only in lab environment
"""

import requests
import random
import string
import time
import logging
from sklearn.ensemble import IsolationForest
import numpy as np
import argparse

logger = logging.getLogger(__name__)

class AIFuzzer:
    """ML-powered web application fuzzer"""
    
    def __init__(self):
        self.model = IsolationForest(contamination=0.1, random_state=42)
        self.responses = []
    
    def generate_payload(self, length: int = 100) -> str:
        """Generate random payload for fuzzing"""
        chars = string.ascii_letters + string.digits + string.punctuation
        return ''.join(random.choice(chars) for _ in range(length))
    
    def generate_payloads(self, count: int = 100) -> list:
        """Generate multiple payloads"""
        return [self.generate_payload(random.randint(10, 500)) for _ in range(count)]
    
    def fuzz_endpoint(self, url: str, param_name: str = "input", 
                      max_requests: int = 100) -> Optional[str]:
        """Fuzz endpoint with random payloads"""
        payloads = self.generate_payloads(max_requests)
        
        for i, payload in enumerate(payloads):
            try:
                full_url = f"{url}?{param_name}={payload}"
                resp = requests.get(full_url, timeout=3)
                
                response_data = {
                    'status': resp.status_code,
                    'length': len(resp.text),
                    'time': resp.elapsed.total_seconds()
                }
                self.responses.append(response_data)
                
                # Check for crashes
                if resp.status_code >= 500:
                    logger.warning(f"Potential crash with payload: {payload[:50]}...")
                    return payload
                
                if i % 20 == 0:
                    logger.debug(f"Fuzzing progress: {i+1}/{max_requests}")
                    
            except requests.RequestException as e:
                logger.warning(f"Request failed: {e}, payload: {payload[:50]}")
                return payload
        
        # Train anomaly detector
        if len(self.responses) > 10:
            self._detect_anomalies()
        
        return None
    
    def _detect_anomalies(self) -> bool:
        """Detect anomalous responses using ML"""
        if len(self.responses) < 10:
            return False
        
        X = np.array([[r['status'], r['length'], r['time']] for r in self.responses])
        self.model.fit(X)
        predictions = self.model.predict(X)
        
        anomalies = np.where(predictions == -1)[0]
        if len(anomalies) > 0:
            logger.warning(f"Detected {len(anomalies)} anomalous responses")
            return True
        
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Fuzzer")
    parser.add_argument("-u", "--url", required=True, help="Target URL")
    parser.add_argument("-p", "--param", default="input", help="Parameter name")
    parser.add_argument("-r", "--requests", type=int, default=100, help="Max requests")
    
    args = parser.parse_args()
    
    fuzzer = AIFuzzer()
    crash = fuzzer.fuzz_endpoint(args.url, args.param, args.requests)
    
    if crash:
        print(f"💥 Crash detected with payload: {crash[:100]}")
    else:
        print("✅ Fuzzing completed - no crashes detected")