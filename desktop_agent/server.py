# server.py
from flask import Flask, request, jsonify

app = Flask(__name__)

# Tokenlar ro‘yxati (odatda bazada saqlanadi)
VALID_TOKENS = ["your-secret-token-123"]

@app.route('/api/scan_results', methods=['POST'])
def receive_scan():
    # API tokenni tekshirish
    auth_header = request.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '')
    if token not in VALID_TOKENS:
        return jsonify({"error": "Invalid token"}), 401

    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data"}), 400

    # Ma'lumotlarni saqlash (masalan, faylga yoki bazaga)
    import json
    with open('scan_results.json', 'a') as f:
        f.write(json.dumps(data) + '\n')

    print(f"Received scan for {data.get('target_url')}")
    return jsonify({"status": "success", "message": "Results stored"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)