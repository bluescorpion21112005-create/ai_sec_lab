# api_client.py
import requests
import json
from datetime import datetime
from config import SERVER_URL, DEFAULT_TIMEOUT

def submit_scan_results(server_url, api_token, target_url, findings):
    if not server_url.endswith('/'):
        server_url += '/'
    endpoint = server_url + 'api/scan_results'
    payload = {
        "api_token": api_token,
        "target_url": target_url,
        "findings": findings,
        "timestamp": str(datetime.now())
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_token}"
    }
    try:
        response = requests.post(endpoint, json=payload, headers=headers, timeout=DEFAULT_TIMEOUT)
        return response
    except requests.exceptions.RequestException as e:
        class MockResponse:
            def __init__(self, status_code, text):
                self.status_code = status_code
                self.text = text
        return MockResponse(500, f"Connection error: {e}")