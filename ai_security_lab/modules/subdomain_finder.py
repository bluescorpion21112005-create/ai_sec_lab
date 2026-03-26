#!/usr/bin/env python3
"""
AI-powered subdomain discovery with ML ranking
Educational purpose only - Use only in lab environment
"""

import dns.resolver
import dns.exception
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
import joblib
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from pathlib import Path
import time
import argparse
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)

class AISubfinder:
    """AI-powered subdomain discovery tool"""
    
    def __init__(self, model_path: str = "models/"):
        self.model_path = Path(model_path)
        self.model_path.mkdir(exist_ok=True)
        
        self.ml_model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.vectorizer = TfidfVectorizer(max_features=1000)
        self._load_or_train_model()
    
    def _load_or_train_model(self):
        """Load existing model or train a new one"""
        model_file = self.model_path / "subdomain_model.pkl"
        vec_file = self.model_path / "vectorizer.pkl"
        
        if model_file.exists() and vec_file.exists():
            self.ml_model = joblib.load(model_file)
            self.vectorizer = joblib.load(vec_file)
            logger.info("Loaded existing subdomain model")
        else:
            self._train_model()
    
    def _train_model(self):
        """Train ML model with sample data"""
        # Sample training data (in production use real data)
        X_train = np.array([
            [5, 0, 0, 0, 1], [7, 0, 0, 0, 1], [6, 0, 0, 0, 1],
            [8, 0, 0, 0, 1], [4, 0, 0, 0, 1], [3, 0, 0, 0, 0],
            [4, 0, 1, 1, 0], [6, 0, 1, 2, 0]
        ])
        y_train = np.array([1, 1, 1, 1, 1, 1, 0, 0])
        
        common_patterns = ['api', 'admin', 'dev', 'staging', 'test', 'www']
        self.vectorizer.fit(common_patterns)
        self.ml_model.fit(X_train, y_train)
        
        joblib.dump(self.ml_model, self.model_path / "subdomain_model.pkl")
        joblib.dump(self.vectorizer, self.model_path / "vectorizer.pkl")
        logger.info("Trained and saved new subdomain model")
    
    def generate_subdomains(self, domain: str, wordlist_path: str) -> List[str]:
        """Generate subdomains from wordlist"""
        subdomains = []
        try:
            with open(wordlist_path, 'r') as f:
                for word in f.read().splitlines():
                    if word.strip():
                        subdomains.append(f"{word.strip()}.{domain}")
        except FileNotFoundError:
            logger.warning(f"Wordlist not found: {wordlist_path}, using defaults")
            default_words = ['www', 'api', 'admin', 'dev', 'test', 'mail', 'blog']
            subdomains = [f"{w}.{domain}" for w in default_words]
        
        return subdomains
    
    def check_live(self, subdomain: str) -> Tuple[str, bool, float]:
        """Check if subdomain resolves via DNS"""
        try:
            start = time.time()
            dns.resolver.resolve(subdomain, 'A')
            return (subdomain, True, time.time() - start)
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.Timeout):
            return (subdomain, False, 0)
        except Exception as e:
            logger.debug(f"Error checking {subdomain}: {e}")
            return (subdomain, False, 0)
    
    def predict_score(self, subdomain: str) -> float:
        """Predict probability that subdomain is live"""
        try:
            name_part = subdomain.split('.')[0]
            features = np.array([[
                len(name_part),
                name_part.count('.'),
                name_part.count('-'),
                sum(c.isdigit() for c in name_part),
                int(any(w in name_part for w in ['api', 'admin', 'dev', 'test']))
            ]])
            return self.ml_model.predict_proba(features)[0][1]
        except:
            return 0.5
    
    def scan(self, domain: str, wordlist_path: str, max_workers: int = 50) -> List[Dict]:
        """Main scanning function"""
        logger.info(f"Scanning subdomains for: {domain}")
        subdomains = self.generate_subdomains(domain, wordlist_path)
        
        if not subdomains:
            return []
        
        live_results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.check_live, sub): sub for sub in subdomains}
            
            for future in as_completed(futures):
                sub, is_live, resp_time = future.result()
                if is_live:
                    live_results.append({
                        'subdomain': sub,
                        'response_time': resp_time,
                        'ai_score': self.predict_score(sub)
                    })
        
        live_results.sort(key=lambda x: x['ai_score'], reverse=True)
        logger.info(f"Found {len(live_results)} live subdomains")
        return live_results
    
    def print_results(self, results: List[Dict], limit: int = 10):
        """Pretty print results"""
        if not results:
            print("No live subdomains found")
            return
        
        print("\n" + "="*70)
        print(f"🏆 TOP {min(limit, len(results))} AI-RANKED LIVE SUBDOMAINS")
        print("="*70)
        for i, res in enumerate(results[:limit], 1):
            print(f"{i:2}. {res['subdomain']:45} Score: {res['ai_score']:.3f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Subdomain Finder")
    parser.add_argument("domain", help="Target domain")
    parser.add_argument("-w", "--wordlist", default="datasets/subdomains.txt")
    parser.add_argument("-t", "--threads", type=int, default=50)
    
    args = parser.parse_args()
    
    finder = AISubfinder()
    results = finder.scan(args.domain, args.wordlist, args.threads)
    finder.print_results(results)