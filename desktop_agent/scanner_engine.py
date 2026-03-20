import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup


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
            "detail": "Missing Content-Security-Policy header",
            "recommendation": "Add a strong Content-Security-Policy header."
        })

    if "X-Frame-Options" not in headers:
        findings.append({
            "type": "missing_header",
            "severity": "medium",
            "detail": "Missing X-Frame-Options header",
            "recommendation": "Set X-Frame-Options to DENY or SAMEORIGIN."
        })

    if "X-Content-Type-Options" not in headers:
        findings.append({
            "type": "missing_header",
            "severity": "low",
            "detail": "Missing X-Content-Type-Options header",
            "recommendation": "Set X-Content-Type-Options to nosniff."
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
                "detail": f"Possible SQL error pattern found: {pattern}",
                "recommendation": "Hide database errors and use safe parameterized queries."
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
                "detail": "Reflected input detected in response",
                "recommendation": "Escape user input before rendering it in HTML."
            })
    except Exception as e:
        findings.append({
            "type": "reflection_test_error",
            "severity": "low",
            "detail": str(e),
            "recommendation": "Check reflection test handling."
        })

    return findings


def scan_common_paths(base_url: str, timeout: int = 10):
    findings = []
    paths = [
        "/admin",
        "/login",
        "/debug",
        "/robots.txt",
        "/.env",
        "/config",
        "/backup",
        "/phpinfo.php",
        "/server-status"
    ]

    for path in paths:
        try:
            full_url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
            r = requests.get(full_url, timeout=timeout)

            if r.status_code == 200:
                findings.append({
                    "type": "interesting_path",
                    "severity": "info",
                    "detail": f"Accessible path found: {path}",
                    "recommendation": "Review whether this path should be publicly accessible."
                })
        except Exception:
            continue

    return findings


def analyze_forms(response):
    findings = []
    soup = BeautifulSoup(response.text, "html.parser")
    forms = soup.find_all("form")

    if forms:
        findings.append({
            "type": "form_detected",
            "severity": "info",
            "detail": f"{len(forms)} form(s) found on the page",
            "recommendation": "Review form validation and sanitization."
        })

    for idx, form in enumerate(forms, start=1):
        method = (form.get("method") or "GET").upper()
        action = form.get("action") or "(same page)"
        inputs = form.find_all("input")

        password_found = any((inp.get("type") or "").lower() == "password" for inp in inputs)

        findings.append({
            "type": "form_analysis",
            "severity": "info",
            "detail": f"Form #{idx}: method={method}, action={action}, inputs={len(inputs)}",
            "recommendation": "Ensure CSRF protection and input validation are enabled."
        })

        if password_found and method != "POST":
            findings.append({
                "type": "insecure_form_method",
                "severity": "high",
                "detail": f"Form #{idx} has password field but method is {method}",
                "recommendation": "Use POST for forms handling passwords."
            })

    return findings


def check_cookie_security(response):
    findings = []
    set_cookie_headers = response.headers.get("Set-Cookie")

    if not set_cookie_headers:
        return findings

    cookie_text = set_cookie_headers.lower()

    if "httponly" not in cookie_text:
        findings.append({
            "type": "cookie_security",
            "severity": "medium",
            "detail": "Cookie may be missing HttpOnly flag",
            "recommendation": "Add HttpOnly to session cookies."
        })

    if "secure" not in cookie_text:
        findings.append({
            "type": "cookie_security",
            "severity": "medium",
            "detail": "Cookie may be missing Secure flag",
            "recommendation": "Add Secure flag for HTTPS cookies."
        })

    if "samesite" not in cookie_text:
        findings.append({
            "type": "cookie_security",
            "severity": "low",
            "detail": "Cookie may be missing SameSite attribute",
            "recommendation": "Add SameSite=Lax or Strict where appropriate."
        })

    return findings


def check_server_info(response):
    findings = []
    server = response.headers.get("Server")
    powered_by = response.headers.get("X-Powered-By")

    if server:
        findings.append({
            "type": "server_disclosure",
            "severity": "low",
            "detail": f"Server header exposed: {server}",
            "recommendation": "Hide or minimize server version details."
        })

    if powered_by:
        findings.append({
            "type": "tech_disclosure",
            "severity": "low",
            "detail": f"X-Powered-By exposed: {powered_by}",
            "recommendation": "Remove X-Powered-By header in production."
        })

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
        findings.extend(analyze_forms(response))
        findings.extend(check_cookie_security(response))
        findings.extend(check_server_info(response))

        if not findings:
            findings.append({
                "type": "clean",
                "severity": "info",
                "detail": "No obvious issues found in basic local scan",
                "recommendation": "Run deeper authenticated and dynamic tests for better coverage."
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
                    "detail": str(e),
                    "recommendation": "Check whether the target is running and accessible."
                }
            ]
        }