from flask import Flask, render_template, session, request, redirect, url_for, flash, jsonify,abort
from flask_session import Session
from helper import login_required
import os
import json
from pathlib import Path
from datetime import datetime,timedelta,timezone
import re
import pymupdf
import torch
import mariadb
import pandas as pd
import joblib
from load_model import model_1,tokenizer_1,label_mappings,device_1,model_2,tokenizer_2,device_2,gen_pipeline
from dotenv import load_dotenv
from werkzeug.security import check_password_hash,generate_password_hash
from flask_jwt_extended import create_access_token,get_jwt,get_jwt_identity,jwt_required,JWTManager,set_access_cookies,unset_jwt_cookies

app = Flask(__name__)
load_dotenv() 
# If true this will only allow the cookies that contain your JWTs to be sent
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY")

# JWT
app.config["JWT_SECRET_KEY"] = os.getenv("jwt_secret_key")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)

# Store JWT in cookies
app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
app.config["JWT_ACCESS_COOKIE_NAME"] = "access_token_cookie"

# Local development: HTTP, not HTTPS
app.config["JWT_COOKIE_SECURE"] = False
app.config["JWT_COOKIE_HTTPONLY"] = True
app.config["JWT_COOKIE_SAMESITE"] = "Lax"
db_config = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME")
}

jwt = JWTManager(app)


def get_db_connection():
    try:
        conn = mariadb.connect(**db_config)
        return conn
    except mariadb.Error as e:
        print(f"Error connecting to MariaDB: {e}")
        return None

PDF_PATH = './data/Coal_Mine_Inspection_Report_Concise.pdf'
RISK_MODEL_PATH = './models/mira-risk-classifier.pkl'
ENCODER_PATH = "./models/mira-risk-encoder.pkl"

risk_model = joblib.load(RISK_MODEL_PATH)
risk_encoder = joblib.load(ENCODER_PATH)

# Using an `after_request` callback, we refresh any token that is within 30
# minutes of expiring. Change the timedeltas to match the needs of your application.
# @app.after_request
# def refresh_expiring_jwts(response):
#     """
#     Refresh the JWT if it is close to expiration.

#     This runs for every request, so we must safely handle requests
#     that do not have a JWT (for example /login).
#     """
#     try:
#         # get_jwt() raises RuntimeError when there is no JWT
#         claims = get_jwt()

#         exp_timestamp = claims["exp"]
#         now = datetime.now(timezone.utc)
#         target_timestamp = datetime.timestamp(
#             now + timedelta(minutes=30)
#         )

#         if target_timestamp > exp_timestamp:
#             # Preserve the existing claims when refreshing
#             access_token = create_access_token(
#                 identity=get_jwt_identity(),
#                 additional_claims={
#                     "name": claims.get("name"),
#                     "role": claims.get("role"),
#                     "regional_office": claims.get("regional_office"),
#                 }
#             )

#             set_access_cookies(
#                 response,
#                 access_token
#             )

#         return response

    # except (RuntimeError, KeyError):
    #     # No JWT on this request.
    #     # This is normal for /login, static files, etc.
    #     return response

@jwt.unauthorized_loader
def unauthorized_callback(reason):
    print("JWT UNAUTHORIZED:", reason)

    flash(
        "Please log in to continue.",
        "warning"
    )

    return redirect(url_for("login"))

@jwt.invalid_token_loader
def invalid_token_callback(reason):
    print("JWT INVALID:", reason)

    flash(
        "Your login session is invalid. Please log in again.",
        "danger"
    )

    return redirect(url_for("login"))

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    print("JWT EXPIRED")

    flash(
        "Your session has expired. Please log in again.",
        "warning"
    )

    return redirect(url_for("login"))

@app.context_processor
def inject_user_role():
    try:
        claims = get_jwt()
        return {"current_user_role": claims.get("role")}

    except Exception:
        return {"current_user_role": None}

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("name", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash(
                "Username and password are required.",
                "danger"
            )
            return redirect(url_for("login"))

        conn = None
        cursor = None

        try:
            conn = get_db_connection()

            if conn is None:
                flash(
                    "Database connection failed. Please try again later.",
                    "danger"
                )
                return redirect(url_for("login"))

            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT
                    id,
                    name,
                    role,
                    regional_office,
                    password_hash,
                    is_active
                FROM users
                WHERE name = ?
                LIMIT 1
                """,
                (username,)
            )

            user = cursor.fetchone()

            if not user:
                flash(
                    "Invalid username or password.",
                    "danger"
                )
                return redirect(url_for("login"))

            if not user["is_active"]:
                flash(
                    "Your account has been deactivated. "
                    "Contact an administrator.",
                    "danger"
                )
                return redirect(url_for("login"))

            if not check_password_hash(
                user["password_hash"],
                password
            ):
                flash(
                    "Invalid username or password.",
                    "danger"
                )
                return redirect(url_for("login"))

            # Create JWT
            access_token = create_access_token(
                identity=str(user["id"]),
                additional_claims={
                    "name": user["name"],
                    "role": user["role"],
                    "regional_office": user["regional_office"]
                }
            )

            # Optional Flask session data
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["role"] = user["role"]
            session["regional_office"] = user["regional_office"]

            response = redirect(url_for("dashboard"))

            set_access_cookies(
                response,
                access_token
            )

            return response

        except mariadb.Error as e:
            app.logger.exception("MariaDB login error")

            flash(
                "Database error while logging in. Please try again.",
                "danger"
            )

            return redirect(url_for("login"))

        except Exception:
            app.logger.exception("Login error")

            flash(
                "An error occurred while logging in. "
                "Please try again.",
                "danger"
            )

            return redirect(url_for("login"))

        finally:
            if cursor:
                cursor.close()

            if conn:
                conn.close()

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
@jwt_required()
def register():
    claims = get_jwt()

    # Only administrators can register users
    if claims.get("role") != "admin":
        flash(
            "Administrator access required.",
            "danger"
        )
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        role = request.form.get("role", "").strip()

        regional_office = request.form.get(
            "regional_office",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        # Basic validation
        if not name or not password or not role:
            flash(
                "Name, role and password are required.",
                "danger"
            )
            return redirect(url_for("register"))

        if role not in ["inspector", "admin"]:
            flash(
                "Invalid role selected.",
                "danger"
            )
            return redirect(url_for("register"))

        if password != confirm_password:
            flash(
                "Passwords do not match.",
                "danger"
            )
            return redirect(url_for("register"))

        if len(password) < 8:
            flash(
                "Password must contain at least 8 characters.",
                "danger"
            )
            return redirect(url_for("register"))

        conn = None
        cursor = None

        try:
            conn = get_db_connection()

            if conn is None:
                flash(
                    "Database connection failed. Please try again later.",
                    "danger"
                )
                return redirect(url_for("register"))

            cursor = conn.cursor(dictionary=True)

            # Check whether username already exists
            cursor.execute(
                """
                SELECT id
                FROM users
                WHERE name = ?
                LIMIT 1
                """,
                (name,)
            )

            existing_user = cursor.fetchone()

            if existing_user:
                flash(
                    "A user with this name already exists.",
                    "danger"
                )
                return redirect(url_for("register"))

            # Hash password
            password_hash = generate_password_hash(password)

            # Insert user
            cursor.execute(
                """
                INSERT INTO users
                (
                    name,
                    role,
                    regional_office,
                    password_hash,
                    is_active
                )
                VALUES (?, ?, ?, ?, 1)
                """,
                (
                    name,
                    role,
                    regional_office or None,
                    password_hash
                )
            )

            conn.commit()

            flash(
                f"User '{name}' created successfully.",
                "success"
            )

            return redirect(url_for("dashboard"))

        except mariadb.IntegrityError:
            if conn:
                conn.rollback()

            flash(
                "A user with this name already exists.",
                "danger"
            )

            return redirect(url_for("register"))

        except mariadb.Error:
            if conn:
                conn.rollback()

            app.logger.exception(
                "MariaDB user registration error"
            )

            flash(
                "Database error while creating the user.",
                "danger"
            )

            return redirect(url_for("register"))

        except Exception:
            if conn:
                conn.rollback()

            app.logger.exception(
                "User registration error"
            )

            flash(
                "Unable to create user. Please try again.",
                "danger"
            )

            return redirect(url_for("register"))

        finally:
            if cursor:
                cursor.close()

            if conn:
                conn.close()

    return render_template("register.html")

@app.route("/logout", methods=["POST"])
def logout():
    response = jsonify({
        "msg": "logout successful"
    })
    unset_jwt_cookies(response)
    session.clear()
    return response

@app.route("/")
@jwt_required()
def dashboard():

    conn = get_db_connection()

    if conn is None:
        return "Database connection failed", 500

    cursor = None

    try:
        cursor = conn.cursor(dictionary=True)

        # ====================================================
        # 1. MAIN DASHBOARD KPIs
        # Uses: v_dashboard_kpis
        # ====================================================

        cursor.execute("""
            SELECT *
            FROM v_dashboard_kpis
        """)

        kpis = cursor.fetchone()

        if not kpis:
            kpis = {
                "total_active_mines": 0,
                "high_risk_mines": 0,
                "critical_risk_mines": 0,
                "open_alerts": 0,
                "inspections_last_30_days": 0,
                "overdue_actions": 0,
                "avg_risk_score": 0
            }

        # ====================================================
        # 2. RISK DISTRIBUTION
        # Uses indexed mines(risk_level, status)
        # ====================================================

        cursor.execute("""
            SELECT
                risk_level,
                COUNT(*) AS total
            FROM mines
            WHERE status = 'Active'
            GROUP BY risk_level
        """)

        risk_rows = cursor.fetchall()

        risk_distribution = {
            "LOW": 0,
            "MEDIUM": 0,
            "HIGH": 0,
            "CRITICAL": 0
        }

        for row in risk_rows:
            level = row["risk_level"]

            if level in risk_distribution:
                risk_distribution[level] = row["total"]

        low_risk_mines = risk_distribution["LOW"]
        medium_risk_mines = risk_distribution["MEDIUM"]
        high_risk_mines = risk_distribution["HIGH"]
        critical_risk_mines = risk_distribution["CRITICAL"]

        # ====================================================
        # 3. HIGH / CRITICAL RISK MINES
        # Uses: v_high_risk_mines
        # ====================================================

        cursor.execute("""
            SELECT *
            FROM v_high_risk_mines
            LIMIT 10
        """)

        high_risk_mines_data = cursor.fetchall()

        # ====================================================
        # 4. OPEN ALERTS
        # Uses: v_open_alerts
        # ====================================================

        cursor.execute("""
            SELECT *
            FROM v_open_alerts
            LIMIT 10
        """)

        alerts_data = cursor.fetchall()

        # ====================================================
        # 5. RECENT INSPECTIONS
        # Uses: v_recent_inspections
        # ====================================================

        cursor.execute("""
            SELECT *
            FROM v_recent_inspections
            LIMIT 10
        """)

        recent_inspections = cursor.fetchall()

        # ====================================================
        # 6. MINES BY LOCATION
        # Uses: v_mines_by_location
        # ====================================================

        cursor.execute("""
            SELECT *
            FROM v_mines_by_location
        """)

        mines_by_location = cursor.fetchall()

        # ====================================================
        # 7. OVERDUE ACTIONS
        # Uses: v_overdue_actions
        # ====================================================

        cursor.execute("""
            SELECT *
            FROM v_overdue_actions
            LIMIT 10
        """)

        overdue_actions = cursor.fetchall()

        # ====================================================
        # 8. SEND EVERYTHING TO DASHBOARD
        # ====================================================

        return render_template(
            "dashboard.html",

            # KPI
            kpis=kpis,

            # Risk distribution
            low_risk_mines=low_risk_mines,
            medium_risk_mines=medium_risk_mines,
            high_risk_mines=high_risk_mines,
            critical_risk_mines=critical_risk_mines,

            # Dashboard sections
            high_risk_mines_data=high_risk_mines_data,
            alerts=alerts_data,
            recent_inspections=recent_inspections,
            mines_by_location=mines_by_location,
            overdue_actions=overdue_actions
        )

    except mariadb.Error as e:

        app.logger.exception(
            "Dashboard database error"
        )

        return "Unable to load dashboard", 500

    finally:

        if cursor:
            cursor.close()

        conn.close()


# ============================================================
# MINES
# ============================================================

@app.route("/mines")
@jwt_required()
def mines():

    conn = get_db_connection()

    if conn is None:
        return "Database connection failed", 500

    cursor = None

    try:

        cursor = conn.cursor(dictionary=True)

        # Uses:
        # v_mines_gis
        # idx_mines_risk_level_status
        # idx_mines_state_district
        # idx_mines_region_id

        cursor.execute("""
            SELECT
                id,
                name,
                code,
                operator,
                state,
                district,
                status,
                method,
                risk_score,
                risk_level,
                latitude,
                longitude,
                region_id,
                region_code,
                region_name,
                region_level
            FROM v_mines_gis
            ORDER BY id DESC
        """)

        mines_data = cursor.fetchall()

        return render_template(
            "mines/index.html",
            mines=mines_data
        )

    except mariadb.Error as e:

        app.logger.exception(
            "Error fetching mines"
        )

        return "Unable to load mines", 500

    finally:

        if cursor:
            cursor.close()

        conn.close()


# ============================================================
# MINE DETAIL
# ============================================================

@app.route("/mines/<mine_id>")
@jwt_required()
def mine_detail(mine_id):

    conn = get_db_connection()

    if conn is None:
        abort(500)

    cursor = None

    try:

        cursor = conn.cursor(dictionary=True)

        # Uses v_mines_gis instead of rebuilding
        # the mines + gis_regions JOIN.

        cursor.execute("""
            SELECT *
            FROM v_mines_gis
            WHERE id = ?
            LIMIT 1
        """, (mine_id,))

        row = cursor.fetchone()

        if row is None:
            abort(404)

        mine = {
            "id": row["id"],
            "name": row["name"],
            "code": row["code"],
            "operator": row["operator"],
            "state": row["state"],
            "district": row["district"],
            "status": row["status"],
            "method": row["method"],

            "risk_score": (
                float(row["risk_score"])
                if row["risk_score"] is not None
                else None
            ),

            "risk_level": row["risk_level"],

            "region_id": row.get("region_id"),
            "region_code": row.get("region_code"),
            "region_name": row.get("region_name"),
            "region_level": row.get("region_level"),

            "latitude": (
                float(row["latitude"])
                if row["latitude"] is not None
                else None
            ),

            "longitude": (
                float(row["longitude"])
                if row["longitude"] is not None
                else None
            )
        }

        return render_template(
            "mines/detail.html",
            mine=mine
        )

    except mariadb.Error as e:

        app.logger.exception(
            "Error fetching mine details"
        )

        abort(500)

    finally:

        if cursor:
            cursor.close()

        conn.close()


# ============================================================
# INSPECTIONS
# ============================================================

@app.route("/inspections")
@jwt_required()
def inspections():

    conn = get_db_connection()

    if conn is None:
        abort(500)

    cursor = None

    try:

        cursor = conn.cursor(dictionary=True)

        # Uses v_recent_inspections.
        #
        # NOTE:
        # This view currently contains LIMIT 20.
        # Therefore this page will display the latest 20 inspections.

        cursor.execute("""
            SELECT *
            FROM v_recent_inspections
            ORDER BY inspection_date DESC, id DESC
        """)

        rows = cursor.fetchall()

        inspections_data = []

        for row in rows:

            inspections_data.append({
                "id": row["id"],
                "report_no": row["report_no"],

                "mine_id": None,

                "mine_name": row["mine_name"],
                "mine_code": row["mine_code"],
                "mine_state": row["state"],
                "mine_district": row["district"],

                "inspector_id": None,
                "inspector_name": row["inspector_name"],

                "inspection_date": row["inspection_date"],
                "duration": None,
                "remarks": None,

                "status": row["status"],
                "pdf_path": row["pdf_path"],

                "created_at": None,

                "risk_score": row["risk_score"],
                "risk_level": row["risk_level"]
            })

        return render_template(
            "inspections/index.html",
            inspections=inspections_data
        )

    except mariadb.Error as e:

        app.logger.exception(
            "Error fetching inspections"
        )

        abort(500)

    finally:

        if cursor:
            cursor.close()

        conn.close()


# ============================================================
# INSPECTION DETAIL
# ============================================================

@app.route("/inspections/<inspection_id>")
@jwt_required()
def inspection_detail(inspection_id):

    conn = get_db_connection()

    if conn is None:
        abort(500)

    cursor = None

    try:

        cursor = conn.cursor(dictionary=True)

        # ====================================================
        # INSPECTION + MINE + INSPECTOR
        # ====================================================

        cursor.execute("""
            SELECT
                i.id,
                i.report_no,
                i.mine_id,
                i.inspector_id,
                i.inspection_date,
                i.duration,
                i.remarks,
                i.status,
                i.pdf_path,
                i.created_at,
                i.updated_at,

                m.name AS mine_name,
                m.code AS mine_code,
                m.operator AS mine_operator,
                m.state AS mine_state,
                m.district AS mine_district,
                m.status AS mine_status,
                m.method AS mine_method,
                m.latitude AS mine_latitude,
                m.longitude AS mine_longitude,

                u.name AS inspector_name

            FROM inspections i

            INNER JOIN mines m
                ON i.mine_id = m.id

            INNER JOIN users u
                ON i.inspector_id = u.id

            WHERE i.id = ?

            LIMIT 1
        """, (inspection_id,))

        row = cursor.fetchone()

        if row is None:
            abort(404)

        inspection = {
            "id": row["id"],
            "report_no": row["report_no"],
            "mine_id": row["mine_id"],
            "inspector_id": row["inspector_id"],
            "inspection_date": row["inspection_date"],
            "duration": row["duration"],
            "remarks": row["remarks"],
            "status": row["status"],
            "pdf_path": row["pdf_path"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],

            "mine": {
                "id": row["mine_id"],
                "name": row["mine_name"],
                "code": row["mine_code"],
                "operator": row["mine_operator"],
                "state": row["mine_state"],
                "district": row["mine_district"],
                "status": row["mine_status"],
                "method": row["mine_method"],
                "latitude": row["mine_latitude"],
                "longitude": row["mine_longitude"]
            },

            "inspector": {
                "id": row["inspector_id"],
                "name": row["inspector_name"]
            },

            "findings": [],
            "evidence": []
        }

        # ====================================================
        # FINDINGS
        # Uses idx_findings_severity_recurring
        # and idx_findings_category
        # ====================================================

        cursor.execute("""
            SELECT
                f.id,
                f.inspection_id,
                f.issue,
                f.category,
                f.severity,
                f.recurring,
                f.finding_code,
                f.note,
                ft.text AS finding_text

            FROM inspection_findings f

            LEFT JOIN finding_texts ft
                ON f.id = ft.finding_id

            WHERE f.inspection_id = ?

            ORDER BY f.id ASC
        """, (inspection_id,))

        finding_rows = cursor.fetchall()

        for row in finding_rows:

            inspection["findings"].append({
                "id": row["id"],
                "inspection_id": row["inspection_id"],
                "issue": row["issue"],
                "category": row["category"],
                "severity": row["severity"],
                "recurring": bool(row["recurring"]),
                "finding_code": row["finding_code"],
                "note": row["note"],
                "text": row["finding_text"]
            })

        # ====================================================
        # EVIDENCE
        # Uses idx_evidence_insp_finding
        # ====================================================

        cursor.execute("""
            SELECT
                id,
                inspection_id,
                finding_id,
                file_path,
                latitude,
                longitude,
                evidence_type,
                description,
                created_at

            FROM inspection_evidence

            WHERE inspection_id = ?

            ORDER BY id ASC
        """, (inspection_id,))

        evidence_rows = cursor.fetchall()

        for row in evidence_rows:

            inspection["evidence"].append({
                "id": row["id"],
                "inspection_id": row["inspection_id"],
                "finding_id": row["finding_id"],
                "file_path": row["file_path"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "evidence_type": row["evidence_type"],
                "description": row["description"],
                "created_at": row["created_at"]
            })

        return render_template(
            "inspections/detail.html",
            inspection=inspection
        )

    except mariadb.Error as e:

        app.logger.exception(
            "Error fetching inspection details"
        )

        abort(500)

    finally:

        if cursor:
            cursor.close()

        conn.close()


# ============================================================
# RISK
# ============================================================

@app.route("/risk")
@jwt_required()
def risk():

    conn = get_db_connection()

    if conn is None:
        return "Database connection failed", 500

    cursor = None

    try:

        cursor = conn.cursor(dictionary=True)

        # Uses idx_risk_level_created
        # and idx_risk_mine_created

        cursor.execute("""
            SELECT
                rs.id,
                rs.inspection_id,
                rs.mine_id,
                rs.risk_score,
                rs.risk_level,
                rs.risk_factors,
                rs.model_version,
                rs.created_at,

                i.report_no,
                i.inspection_date,
                i.status AS inspection_status,

                m.name AS mine_name,
                m.code AS mine_code,
                m.state,
                m.district

            FROM risk_scores rs

            INNER JOIN inspections i
                ON rs.inspection_id = i.id

            INNER JOIN mines m
                ON rs.mine_id = m.id

            ORDER BY rs.created_at DESC
        """)

        risk_records = cursor.fetchall()

        # ====================================================
        # SUMMARY STATISTICS
        # ====================================================

        total = len(risk_records)

        high_count = sum(
            1
            for r in risk_records
            if r["risk_level"] == "HIGH"
        )

        critical_count = sum(
            1
            for r in risk_records
            if r["risk_level"] == "CRITICAL"
        )

        medium_count = sum(
            1
            for r in risk_records
            if r["risk_level"] == "MEDIUM"
        )

        low_count = sum(
            1
            for r in risk_records
            if r["risk_level"] == "LOW"
        )

        return render_template(
            "risk.html",

            risk_records=risk_records,

            total=total,
            high_count=high_count,
            critical_count=critical_count,
            medium_count=medium_count,
            low_count=low_count
        )

    except mariadb.Error as e:

        app.logger.exception(
            "Error fetching risk data"
        )

        return "Unable to load risk analytics", 500

    finally:

        if cursor:
            cursor.close()

        conn.close()


# ============================================================
# ALERTS
# ============================================================

@app.route("/alerts")
@jwt_required()
def alerts():

    conn = get_db_connection()

    if conn is None:
        return "Database connection failed", 500

    cursor = None

    try:

        cursor = conn.cursor(dictionary=True)

        # Uses v_open_alerts
        # and idx_alerts_status_severity
        # and idx_alerts_mine_status

        cursor.execute("""
            SELECT *
            FROM v_open_alerts
        """)

        alert_records = cursor.fetchall()

        return render_template(
            "alert.html",
            alerts=alert_records
        )

    except mariadb.Error as e:

        app.logger.exception(
            "Error fetching alerts"
        )

        return "Unable to load alerts", 500

    finally:

        if cursor:
            cursor.close()

        conn.close()


# ============================================================
# GIS MAP PAGE
# ============================================================

@app.route("/map")
@jwt_required()
def gis_map():

    return render_template("map.html")


# ============================================================
# GIS MINES API
# ============================================================

@app.route("/api/v1/gis/mines")
@jwt_required()
def gis_mines():

    conn = get_db_connection()

    if conn is None:

        return jsonify({
            "type": "FeatureCollection",
            "features": [],
            "error": "Database connection failed"
        }), 500

    cursor = None

    try:

        cursor = conn.cursor(dictionary=True)

        # ====================================================
        # Uses v_mines_gis
        # ====================================================

        cursor.execute("""
            SELECT
                id,
                name,
                code,
                operator,
                state,
                district,
                status,
                method,
                risk_score,
                risk_level,
                latitude,
                longitude,
                region_id,
                region_code,
                region_name,
                region_level

            FROM v_mines_gis

            WHERE latitude IS NOT NULL
              AND longitude IS NOT NULL

            ORDER BY id DESC
        """)

        rows = cursor.fetchall()

        features = []

        for row in rows:

            feature = {
                "type": "Feature",

                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        float(row["longitude"]),
                        float(row["latitude"])
                    ]
                },

                "properties": {
                    "id": row["id"],
                    "name": row["name"],
                    "code": row["code"],
                    "operator": row["operator"],
                    "state": row["state"],
                    "district": row["district"],
                    "status": row["status"],
                    "method": row["method"],

                    "risk_score": (
                        float(row["risk_score"])
                        if row["risk_score"] is not None
                        else None
                    ),

                    "risk_level": row["risk_level"],

                    "region": {
                        "id": row["region_id"],
                        "code": row["region_code"],
                        "name": row["region_name"],
                        "level": row["region_level"]
                    }
                }
            }

            features.append(feature)

        return jsonify({
            "type": "FeatureCollection",
            "features": features
        })

    except mariadb.Error as e:

        app.logger.exception(
            "GIS mines API error"
        )

        return jsonify({
            "type": "FeatureCollection",
            "features": [],
            "error": str(e)
        }), 500

    finally:

        if cursor:
            cursor.close()

        conn.close()


# ============================================================
# FINDINGS
# ============================================================

@app.route("/findings")
@jwt_required()
def findings():

    try:

        results = process_pdf()

        risk_results = calculate_risk(results)

        return render_template(
            "findings.html",
            results=risk_results,
            count=len(risk_results)
        )

    except Exception as e:

        app.logger.exception(
            "Finding processing error"
        )

        return "Unable to process findings", 500

def extract_pdf_text(pdf_path):
    document = pymupdf.open(pdf_path)
    text = ""
    for page in document:
        text += page.get_text()
    document.close()
    return text
    
def extract_findings(text):

    pattern = r'Finding\s+(F-\d+):\s*(.*?)(?=Finding\s+F-\d+:|(?:\n|\s)5\.\s*INSPECTOR[\'’]?S\s+REMARKS|$)'

    matches = re.findall(
        pattern,
        text,
        flags=re.DOTALL | re.IGNORECASE
    )

    findings = []

    for finding_id, finding_text in matches:

        findings.append({
            'finding_id': finding_id,
            'finding_text': finding_text.strip()
        })

    return findings

def get_label(mapping, index):
    """
    Convert model prediction index into label.

    label_mappings.json stores labels as lists:
        ["label1", "label2", "label3"]

    Therefore the prediction index is used directly.
    """

    if not isinstance(mapping, list):
        raise TypeError(
            f"Expected label mapping to be a list, "
            f"got {type(mapping).__name__}"
        )

    if index < 0 or index >= len(mapping):
        raise IndexError(
            f"Label index {index} is outside "
            f"the mapping range 0-{len(mapping)-1}"
        )

    return mapping[index]


def classify_finding(text):

    # --------------------------------------------------------
    # Tokenize using MODEL 1
    # --------------------------------------------------------

    inputs = tokenizer_1(
        text,
        return_tensors="pt",
        truncation=True,
        padding=True
    )

    inputs = {
        key: value.to(device_1)
        for key, value in inputs.items()
    }

    # --------------------------------------------------------
    # MODEL 1 prediction
    # --------------------------------------------------------

    with torch.no_grad():

        outputs = model_1(
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"]
        )

    # --------------------------------------------------------
    # Get prediction indexes
    # --------------------------------------------------------

    issue_id = torch.argmax(
        outputs["issue"],
        dim=1
    ).item()

    category_id = torch.argmax(
        outputs["category"],
        dim=1
    ).item()

    severity_id = torch.argmax(
        outputs["severity"],
        dim=1
    ).item()

    recurring_id = torch.argmax(
        outputs["recurring"],
        dim=1
    ).item()

    # --------------------------------------------------------
    # Convert indexes -> actual labels
    # --------------------------------------------------------

    issue = get_label(
        label_mappings["issue"],
        issue_id
    )

    category = get_label(
        label_mappings["category"],
        category_id
    )

    severity = get_label(
        label_mappings["severity"],
        severity_id
    )

    recurring = get_label(
        label_mappings["recurring"],
        recurring_id
    )

    # --------------------------------------------------------
    # Return classification
    # --------------------------------------------------------

    return {
        "issue": issue,
        "category": category,
        "severity": severity,
        "recurring": recurring
    }

def process_pdf():

    pdf_text = extract_pdf_text(
        PDF_PATH
    )

    findings = extract_findings(
        pdf_text
    )

    results = []

    for finding in findings:

        prediction = classify_finding(
            finding['finding_text']
        )

        results.append({
            'finding_id': finding['finding_id'],
            'finding_text': finding['finding_text'],
            'issue': prediction['issue'],
            'category': prediction['category'],
            'severity': prediction['severity'],
            'recurring': prediction['recurring']
        })

    return results

def calculate_risk(results):

    risk_results = []

    for result in results:

        risk_input = pd.DataFrame([{
            "issue": result["issue"],
            "category": result["category"],
            "severity": result["severity"],
            "recurring": result["recurring"]
        }])

        # ----------------------------------------------------
        # Encode input
        # ----------------------------------------------------

        risk_input_encoded = risk_encoder.transform(
            risk_input
        )

        # ----------------------------------------------------
        # Predict risk
        # ----------------------------------------------------

        predicted_risk = risk_model.predict(
            risk_input_encoded
        )[0]

        # ----------------------------------------------------
        # Prediction probability
        # ----------------------------------------------------

        probabilities = risk_model.predict_proba(
            risk_input_encoded
        )[0]

        predicted_index = list(
            risk_model.classes_
        ).index(predicted_risk)

        risk_confidence = (
            probabilities[predicted_index] * 100
        )

        # ----------------------------------------------------
        # Store result
        # ----------------------------------------------------

        risk_results.append({

            **result,

            "predicted_risk":
                predicted_risk,

            "risk_confidence":
                round(
                    float(risk_confidence),
                    2
                )
        })

    # IMPORTANT:
    # Return a normal Python list, NOT a DataFrame
    return risk_results

        
if __name__ == "__main__":
    app.run(debug=True)