# scanner_engine.py
import requests
import re
from urllib.parse import urlparse

def scan_target(target, timeout=30):
    if not target.startswith(('http://', 'https://')):
        target = 'http://' + target
    findings = []
    try:
        response = requests.get(target, timeout=timeout, allow_redirects=True)
        content = response.text
        headers = response.headers

        # Security headers
        if 'X-XSS-Protection' not in headers:
            findings.append({
                "severity": "medium",
                "type": "Missing Security Header",
                "detail": "X-XSS-Protection header is missing.",
                "recommendation": "Add 'X-XSS-Protection: 1; mode=block'."
            })
        if 'Content-Security-Policy' not in headers:
            findings.append({
                "severity": "high",
                "type": "Missing Security Header",
                "detail": "Content-Security-Policy header is missing.",
                "recommendation": "Implement a strict CSP policy."
            })

        # SQL Injection simulation (simplified)
        test_payloads = ["'", "\"", "1' OR '1'='1"]
        for payload in test_payloads:
            test_url = f"{target}?id={payload}"
            try:
                test_resp = requests.get(test_url, timeout=timeout)
                if "sql" in test_resp.text.lower() or "mysql" in test_resp.text.lower():
                    findings.append({
                        "severity": "critical",
                        "type": "SQL Injection",
                        "detail": f"Possible SQL injection via parameter 'id' with payload: {payload}",
                        "recommendation": "Use parameterized queries; validate all inputs."
                    })
                    break
            except:
                pass

        # XSS simulation
        xss_payload = "<script>alert('XSS')</script>"
        test_url = f"{target}?q={xss_payload}"
        try:
            test_resp = requests.get(test_url, timeout=timeout)
            if xss_payload in test_resp.text:
                findings.append({
                    "severity": "high",
                    "type": "Cross-Site Scripting (XSS)",
                    "detail": f"Reflected XSS detected with payload: {xss_payload}",
                    "recommendation": "Encode output; use CSP; sanitize input."
                })
        except:
            pass

        # Server info
        server = headers.get('Server', '')
        if server:
            findings.append({
                "severity": "info",
                "type": "Server Information Disclosure",
                "detail": f"Server header reveals: {server}",
                "recommendation": "Remove or obscure Server header."
            })

        # HTTPS check
        if target.startswith('http://'):
            findings.append({
                "severity": "medium",
                "type": "Missing HTTPS",
                "detail": "The site is served over HTTP, not HTTPS.",
                "recommendation": "Redirect all traffic to HTTPS and enable HSTS."
            })

        # Cookie security
        if 'Set-Cookie' in headers:
            cookies = headers.get('Set-Cookie', '')
            if 'HttpOnly' not in cookies:
                findings.append({
                    "severity": "low",
                    "type": "Missing HttpOnly Flag",
                    "detail": "Cookies are missing HttpOnly flag.",
                    "recommendation": "Set HttpOnly flag on all session cookies."
                })
            if 'Secure' not in cookies and target.startswith('https://'):
                findings.append({
                    "severity": "low",
                    "type": "Missing Secure Flag",
                    "detail": "Cookies are missing Secure flag on HTTPS site.",
                    "recommendation": "Set Secure flag on all cookies."
                })

        if not findings:
            findings.append({
                "severity": "info",
                "type": "No Issues Found",
                "detail": "Automated scan did not detect common vulnerabilities.",
                "recommendation": "Consider manual penetration testing."
            })

        return {
            "status": "success",
            "target_url": target,
            "findings": findings
        }

    except requests.exceptions.Timeout:
        return {
            "status": "error",
            "target_url": target,
            "findings": [{
                "severity": "high",
                "type": "Timeout",
                "detail": f"Request timed out after {timeout} seconds.",
                "recommendation": "Check server availability or increase timeout."
            }]
        }
    except requests.exceptions.ConnectionError:
        return {
            "status": "error",
            "target_url": target,
            "findings": [{
                "severity": "high",
                "type": "Connection Error",
                "detail": f"Could not connect to {target}. Check URL and network.",
                "recommendation": "Verify the URL and ensure the server is reachable."
            }]
        }
    except Exception as e:
        return {
            "status": "error",
            "target_url": target,
            "findings": [{
                "severity": "high",
                "type": "Unexpected Error",
                "detail": str(e),
                "recommendation": "Check scanner logs for details."
            }]
        }