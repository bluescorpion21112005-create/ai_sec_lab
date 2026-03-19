from flask import (
    Flask,
    request,
    render_template,
    make_response,
    redirect,
    url_for,
    flash,
    jsonify,
    g,
)
from predictor import predict_text, scan_url
from lab_analyzer import analyze_case
from markupsafe import Markup
from datetime import datetime, timedelta
from flask_login import LoginManager, login_required, current_user, logout_user
from config import (
    SECRET_KEY,
    SQLALCHEMY_DATABASE_URI,
    SQLALCHEMY_TRACK_MODIFICATIONS,
    MAX_CONTENT_LENGTH,
    MAX_HISTORY,
    EXPORT_LAST_REPORT_JSON,
    EXPORT_LAB_CSV,
)
from models import db, User, Project, ScanRecord, Subscription
from auth import auth_bp
from report_builder import save_lab_report_json, save_lab_report_csv
from functools import wraps
import io
import csv
import json
import difflib
import asyncio
from utils import clip_text
from backend.app.scanner.vulnerability_scanner import VulnerabilityScanner

pentest_scanner = VulnerabilityScanner()

PLAN_FEATURES = {
    "free": ["limited_checks", "basic_sql_detection", "basic_pentest"],
    "professional": [
        "full_sql_analysis",
        "full_pentest_scan",
        "ai_recommendations",
        "export_monitoring",
    ],
    "corporate": [
        "unlimited_checks",
        "batch_scan",
        "api_access",
        "monitoring_20_sites",
        "priority_support",
    ],
}
import os

print("DB PATH:", os.path.abspath("siteguard.db"))

app = Flask(__name__)

app.config["SECRET_KEY"] = SECRET_KEY
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.init_app(app)

app.register_blueprint(auth_bp)

SCAN_HISTORY = []
LAST_LAB_CASE = None


def badge_class_name(label: str) -> str:
    normalized = (label or "").strip().upper().replace("-", "_").replace(" ", "_")

    if normalized in {"SQL_ERROR", "CRITICAL", "HIGH", "FAILED"}:
        return "badge-sql"
    if normalized in {"SUSPICIOUS", "MEDIUM"}:
        return "badge-suspicious"
    if normalized in {"NORMAL", "LOW", "INFO", "SAFE", "COMPLETED"}:
        return "badge-normal"
    return "badge-normal"


def get_user_subscription(user_id):
    return Subscription.query.filter_by(user_id=user_id, is_active=True).first()


def get_active_plan(user):
    if not user.is_authenticated:
        return "free"

    sub = get_user_subscription(user.id)
    if sub and sub.end_date and sub.end_date > datetime.utcnow() and sub.is_active:
        return sub.plan_name

    return "free"


def user_has_feature(user, feature_name):
    plan = get_active_plan(user)
    return feature_name in PLAN_FEATURES.get(plan, [])


def feature_required(feature_name):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Avval login qiling.", "warning")
                return redirect(url_for("auth.login"))

            if not user_has_feature(current_user, feature_name):
                flash("Bu funksiyadan foydalanish uchun mos tarif kerak.", "danger")
                return redirect(url_for("pricing"))

            return func(*args, **kwargs)

        return wrapper

    return decorator


def feature_required(feature_name):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if current_user.subscription_plan != "pro":
                flash("Faqat Pro subscription uchun.", "danger")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)

        return wrapped

    return decorator


def normalize_pentest_result(scan_result: dict) -> dict:
    vulnerabilities = scan_result.get("vulnerabilities", []) or []
    summary = scan_result.get("summary", {}) or {}
    severity_counts = summary.get("severity_counts", {}) or {}

    ai_block = scan_result.get("ai_enhanced", {}) or {}
    ai_risk = ai_block.get("ai_risk_prediction", {}) or {}

    if ai_risk.get("level"):
        risk_level = str(ai_risk.get("level", "INFO")).upper()
        risk_score = float(ai_risk.get("score", 0))
        confidence = ai_risk.get("confidence")
    else:
        risk_level = str(summary.get("risk_level", "INFO")).upper()
        score_map = {
            "CRITICAL": 95,
            "HIGH": 80,
            "MEDIUM": 60,
            "LOW": 35,
            "INFO": 10,
        }
        risk_score = float(score_map.get(risk_level, 0))
        confidence = None

    recommendations = []
    for item in (ai_block.get("ai_remediation") or [])[:5]:
        if isinstance(item, dict):
            title = item.get("title") or item.get("type") or "Recommendation"
            steps = item.get("steps") or item.get("actions") or []
            if isinstance(steps, list):
                recommendations.append({"title": title, "steps": steps[:4]})
            else:
                recommendations.append({"title": title, "steps": [str(steps)]})

    return {
        "target": scan_result.get("url") or scan_result.get("target_url"),
        "status_code": scan_result.get("status_code", "-"),
        "scan_duration": scan_result.get("scan_duration", 0),
        "scan_completed": scan_result.get("scan_completed"),
        "risk_level": risk_level,
        "risk_score": round(risk_score, 2),
        "confidence": confidence,
        "summary": summary,
        "severity_counts": {
            "critical": severity_counts.get("critical", 0),
            "high": severity_counts.get("high", 0),
            "medium": severity_counts.get("medium", 0),
            "low": severity_counts.get("low", 0),
            "info": severity_counts.get("info", 0),
        },
        "vulnerabilities": vulnerabilities,
        "technologies": scan_result.get("technologies", []),
        "headers": scan_result.get("headers", {}),
        "information": scan_result.get("information", {}),
        "recommendations": recommendations,
        "ai_risk_prediction": ai_risk,
    }


def add_to_history(
    source: str,
    label: str,
    risk_score: float,
    status,
    length: int,
    user_id=None,
    project_id=None,
):
    SCAN_HISTORY.insert(
        0,
        {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": source,
            "label": label,
            "risk_score": risk_score,
            "status": status,
            "length": length,
        },
    )
    del SCAN_HISTORY[MAX_HISTORY:]

    if user_id:
        record = ScanRecord(
            user_id=user_id,
            project_id=project_id,
            source=source,
            label=label,
            risk_score=risk_score,
            status=status,
            length=length,
        )
        db.session.add(record)
        db.session.commit()


def build_diff_html(baseline_text: str, payload_text: str) -> str:
    base_lines = baseline_text.splitlines()
    payload_lines = payload_text.splitlines()
    diff = difflib.unified_diff(
        base_lines, payload_lines, fromfile="baseline", tofile="payload", lineterm=""
    )

    rendered = []
    for line in diff:
        safe = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
            rendered.append(f'<span class="diff-meta">{safe}</span>')
        elif line.startswith("+"):
            rendered.append(f'<span class="diff-add">{safe}</span>')
        elif line.startswith("-"):
            rendered.append(f'<span class="diff-del">{safe}</span>')
        else:
            rendered.append(safe)

    return "\n".join(rendered)


def history_counts():
    counts = {"normal": 0, "suspicious": 0, "sql_error": 0, "total": len(SCAN_HISTORY)}
    for item in SCAN_HISTORY:
        if item["label"] == "NORMAL":
            counts["normal"] += 1
        elif item["label"] == "SUSPICIOUS":
            counts["suspicious"] += 1
        elif item["label"] == "SQL_ERROR":
            counts["sql_error"] += 1
    return counts


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.context_processor
def inject_plan_data():
    if current_user.is_authenticated:
        active_plan = get_active_plan(current_user)
        return {
            "active_plan": active_plan,
            "user_has_feature": lambda feature: user_has_feature(current_user, feature),
        }
    return {"active_plan": "free", "user_has_feature": lambda feature: False}


@app.before_request
def check_subscription_status():
    g.active_plan = "free"

    if current_user.is_authenticated:
        sub = get_user_subscription(current_user.id)

        if sub and sub.end_date and datetime.utcnow() > sub.end_date:
            sub.is_active = False
            db.session.commit()

        g.active_plan = get_active_plan(current_user)


@app.route("/pricing")
def pricing():
    return render_template("pricing.html")


@app.route("/batch-scan")
@login_required
@feature_required("batch_scan")
def batch_scan():
    return render_template("batch_scan.html")


@app.route("/api-docs")
@login_required
@feature_required("api_access")
def api_docs():
    return render_template("api_docs.html")


@app.route("/priority-support")
@login_required
@feature_required("priority_support")
def priority_support():
    return render_template("priority_support.html")


@app.route("/monitoring")
@login_required
@feature_required("monitoring_20_sites")
def monitoring():
    return render_template("monitoring.html")


@app.route("/subscribe/<plan>")
@login_required
def subscribe(plan):
    if plan not in ["free", "pro", "corporate"]:
        flash("Invalid plan", "danger")
        return redirect(url_for("dashboard"))

    current_user.subscription_plan = plan

    if plan == "free":
        current_user.subscription_status = "inactive"
        current_user.subscription_start = None
        current_user.subscription_end = None
    else:
        current_user.subscription_status = "active"
        current_user.subscription_start = datetime.utcnow()
        current_user.subscription_end = datetime.utcnow() + timedelta(days=30)

    db.session.commit()
    flash(f"{plan} plan activated", "success")
    return redirect(url_for("dashboard"))


@app.route("/")
def home():
    return "Site is working"

@app.route("/history/clear", methods=["POST"])
@login_required
def clear_history_page():
    ScanRecord.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    SCAN_HISTORY.clear()
    return redirect(url_for("history_page"))


@app.route("/projects", methods=["GET", "POST"])
@login_required
def projects():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        domain = request.form.get("domain", "").strip().lower()

        if not name or not domain:
            flash("Project name and domain are required.", "error")
            return redirect(url_for("projects"))

        project = Project(user_id=current_user.id, name=name, domain=domain)
        db.session.add(project)
        db.session.commit()

        flash("Project created successfully.", "success")
        return redirect(url_for("projects"))

    user_projects = (
        Project.query.filter_by(user_id=current_user.id)
        .order_by(Project.created_at.desc())
        .all()
    )
    return render_template("projects.html", projects=user_projects)


@app.route("/projects/<int:project_id>/verify", methods=["GET", "POST"])
@login_required
def verify_domain(project_id):
    project = Project.query.filter_by(
        id=project_id, user_id=current_user.id
    ).first_or_404()

    if request.method == "POST":
        submitted_token = request.form.get("submitted_token", "").strip()

        if submitted_token == project.verification_token:
            project.is_verified = True
            db.session.commit()
            flash("Domain verified successfully.", "success")
            return redirect(url_for("projects"))
        else:
            flash("Verification token does not match.", "error")

    return render_template("verify_domain.html", project=project)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for("auth.login"))


@app.route("/dashboard")
@login_required
def dashboard():
    projects = Project.query.filter_by(user_id=current_user.id).all()
    recent_scans = (
        ScanRecord.query.filter_by(user_id=current_user.id)
        .order_by(ScanRecord.created_at.desc())
        .limit(10)
        .all()
    )

    stats = {
        "projects": len(projects),
        "scans": ScanRecord.query.filter_by(user_id=current_user.id).count(),
        "verified_projects": Project.query.filter_by(
            user_id=current_user.id, is_verified=True
        ).count(),
        "high_risk": ScanRecord.query.filter(
            ScanRecord.user_id == current_user.id, ScanRecord.risk_score >= 70
        ).count(),
    }

    return render_template(
        "dashboard.html",
        projects=projects,
        recent_scans=recent_scans,
        stats=stats,
        badge_class_name=badge_class_name,
        user=current_user,
    )


@app.route("/api/pentest/scan", methods=["POST"])
@login_required
def pentest_scan_api():
    try:
        if not user_has_feature(current_user, "api_access"):
            return jsonify(
                {
                    "ok": False,
                    "error": "API access faqat Korporativ tarif uchun mavjud.",
                }
            ), 403

        payload = request.get_json(silent=True) or {}
        target = (payload.get("target") or payload.get("url") or "").strip()
        scan_type = (payload.get("scan_type") or "ai_enhanced").strip() or "ai_enhanced"

        if not target:
            return jsonify({"ok": False, "error": "Target URL is required."}), 400

        if not (target.startswith("http://") or target.startswith("https://")):
            target = f"https://{target}"

        raw_result = asyncio.run(pentest_scanner.scan_url(target, scan_type=scan_type))
        normalized = normalize_pentest_result(raw_result)

        add_to_history(
            f"pentest:{normalized['target']}",
            normalized["risk_level"],
            normalized["risk_score"],
            f"PENTEST_{scan_type.upper()}",
            len(json.dumps(normalized.get("vulnerabilities", []), ensure_ascii=False)),
            user_id=current_user.id,
        )

        return jsonify({"ok": True, **normalized})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/export/lab-csv")
def export_lab_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "case",
            "baseline_label",
            "baseline_risk",
            "payload_file",
            "label",
            "risk_score",
            "risk_delta",
            "length",
            "length_delta",
            "matched_sql",
            "matched_suspicious",
        ]
    )

    if LAST_LAB_CASE and LAST_LAB_CASE.get("payloads"):
        for item in LAST_LAB_CASE["payloads"]:
            writer.writerow(
                [
                    LAST_LAB_CASE["case"],
                    LAST_LAB_CASE["baseline"]["label"],
                    LAST_LAB_CASE["baseline"]["risk_score"],
                    item["file"],
                    item["label"],
                    item["risk_score"],
                    item["risk_delta"],
                    item["length"],
                    item["length_delta"],
                    "; ".join(item.get("matched_sql", [])),
                    "; ".join(item.get("matched_suspicious", [])),
                ]
            )

    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv"
    response.headers["Content-Disposition"] = (
        "attachment; filename=lab_case_results.csv"
    )
    return response


@app.route("/export/csv")
def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["timestamp", "source", "label", "risk_score", "status", "length"])

    for item in SCAN_HISTORY:
        writer.writerow(
            [
                item["timestamp"],
                item["source"],
                item["label"],
                item["risk_score"],
                item["status"],
                item["length"],
            ]
        )

    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv"
    response.headers["Content-Disposition"] = "attachment; filename=scan_history.csv"
    return response


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
