import requests


def submit_scan_results(server_url, api_token, target_url, findings):
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "target_url": target_url,
        "scan_type": "desktop_local_agent",
        "findings": findings
    }

    response = requests.post(
        f"{server_url.rstrip('/')}/api/submit-local-scan",
        json=payload,
        headers=headers,
        timeout=15
    )

    return response