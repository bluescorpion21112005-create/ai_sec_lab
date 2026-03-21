# ============================================
# AI SECURITY LAB - CONFIGURATION FILE
# ============================================

import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent

# ============================================
# SECURITY
# ============================================
SECRET_KEY = "change-this-to-a-long-random-secret-key-please-change-in-production"
# Ishlab chiqarish uchun:
# SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)

# ============================================
# DATABASE
# ============================================
SQLALCHEMY_DATABASE_URI = "sqlite:///" + str(BASE_DIR / "siteguard.db")
SQLALCHEMY_TRACK_MODIFICATIONS = False

# ============================================
# MODEL PATHS (FIXED - only once)
# ============================================
MODEL_PATH = str(BASE_DIR / "models" / "sql_error_model.joblib")
VECTORIZER_PATH = str(BASE_DIR / "models" / "vectorizer.joblib")

# ============================================
# EXPORT PATHS
# ============================================
EXPORT_DIR = str(BASE_DIR / "exports")
EXPORT_HISTORY_CSV = str(BASE_DIR / "exports" / "scan_history.csv")
EXPORT_LAB_CSV = str(BASE_DIR / "exports" / "lab_case_results.csv")
EXPORT_LAST_REPORT_JSON = str(BASE_DIR / "exports" / "last_lab_report.json")
EXPORT_CSV_PATH = EXPORT_HISTORY_CSV
EXPORT_JSON_PATH = EXPORT_LAST_REPORT_JSON

# ============================================
# APPLICATION SETTINGS
# ============================================
MAX_HISTORY = 25
PREVIEW_LIMIT = 4000
MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB

# ============================================
# EMAIL SETTINGS (for password reset, etc.)
# ============================================
MAIL_SERVER = "smtp.gmail.com"
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = "bluescorpion21112005@gmail.com"  # O'z emailingiz bilan almashtiring
MAIL_PASSWORD = "1234"     # O'z app password bilan almashtiring

# ============================================
# FEATURE FLAGS
# ============================================
ENABLE_EMAIL = False  # Email xabarlarini yoqish/uchirish
ENABLE_API = True
ENABLE_BATCH_SCAN = True

# ============================================
# ADMIN SETTINGS
# ============================================
ADMIN_EMAIL = "admin@aisecuritylab.uz"
ADMIN_PASSWORD = "admin123"  # Ishlab chiqarishda o'zgartiring

# ============================================
# Create directories if they don't exist
# ============================================
os.makedirs(BASE_DIR / "models", exist_ok=True)
os.makedirs(BASE_DIR / "exports", exist_ok=True)