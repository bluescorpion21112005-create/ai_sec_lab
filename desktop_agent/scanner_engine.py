import requests
from urllib.parse import urljoin, urlparse


def normalize_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "http://" + url
    return url


def safe_get(url: str, timeout: int = 10):
    return requests.get(url, timeout=timeout, allow_redirects=True)


def check_security_headers(response):
    findings = []
    headers = response.headers

    if "Content-Security-Policy" not in headers:
        findings.append({
            "type": "missing_header",
            "severity": "medium",
            "detail": "Missing Content-Security-Policy header"
        })

    if "X-Frame-Options" not in headers:
        findings.append({
            "type": "missing_header",
            "severity": "medium",
            "detail": "Missing X-Frame-Options header"
        })

    if "X-Content-Type-Options" not in headers:
        findings.append({
            "type": "missing_header",
            "severity": "low",
            "detail": "Missing X-Content-Type-Options header"
        })

    return findings


def check_sql_errors(response):
    findings = []
    text = response.text.lower()

    patterns = [
        "sql syntax",
        "mysql",
        "ora-",
        "quoted string not properly terminated",
        "syntax error",
        "sqlite error",
        "unclosed quotation mark"
    ]

    for pattern in patterns:
        if pattern in text:
            findings.append({
                "type": "sql_error",
                "severity": "high",
                "detail": f"Possible SQL error pattern found: {pattern}"
            })
            break

    return findings


def check_reflection(base_url: str, timeout: int = 10):
    findings = []
    payload = "AISecReflection123"
    joiner = "&" if "?" in base_url else "?"
    test_url = f"{base_url}{joiner}q={payload}"

    try:
        r = requests.get(test_url, timeout=timeout)
        if payload.lower() in r.text.lower():
            findings.append({
                "type": "reflection",
                "severity": "medium",
                "detail": "Reflected input detected in response"
            })
    except Exception as e:
        findings.append({
            "type": "reflection_test_error",
            "severity": "low",
            "detail": str(e)
        })

    return findings


def scan_common_paths(base_url: str, timeout: int = 10):
    findings = []
    paths = ["/admin", "/login", "/debug", "/robots.txt", "/.env"]

    for path in paths:
        try:
            full_url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
            r = requests.get(full_url, timeout=timeout)

            if r.status_code == 200:
                findings.append({
                    "type": "interesting_path",
                    "severity": "info",
                    "detail": f"Accessible path found: {path}"
                })
        except Exception:
            continue

    return findings


def scan_target(url: str, timeout: int = 10):
    findings = []
    normalized = normalize_url(url)

    try:
        response = safe_get(normalized, timeout=timeout)

        findings.extend(check_security_headers(response))
        findings.extend(check_sql_errors(response))
        findings.extend(check_reflection(normalized, timeout=timeout))
        findings.extend(scan_common_paths(normalized, timeout=timeout))

        if not findings:
            findings.append({
                "type": "clean",
                "severity": "info",
                "detail": "No obvious issues found in basic local scan"
            })

        return {
            "status": "success",
            "target_url": normalized,
            "findings": findings
        }

    except Exception as e:
        return {
            "status": "error",
            "target_url": normalized,
            "findings": [
                {
                    "type": "scan_error",
                    "severity": "high",
                    "detail": str(e)
                }
            ]
        }