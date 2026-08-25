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
from load_model import model, tokenizer, label_mappings, device
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
    return render_template("dashboard.html")

@app.route("/mines")
@jwt_required()
def mines():
    return render_template("./mines/index.html")

@app.route("/mines/<mine_id>")
@jwt_required()
def mine_detail(mine_id):

    conn = get_db_connection()

    if conn is None:
        abort(500)

    cursor = None

    try:

        cursor = conn.cursor()

        query = """
            SELECT
                m.id,
                m.name,
                m.code,
                m.operator,
                m.state,
                m.district,
                m.status,
                m.method,
                m.risk_score,
                m.risk_level,
                m.region_id,
                m.latitude,
                m.longitude,

                g.code AS region_code,
                g.name AS region_name,
                g.level AS region_level

            FROM mines m

            LEFT JOIN gis_regions g
                ON m.region_id = g.id

            WHERE m.id = ?

            LIMIT 1
        """

        cursor.execute(query, (mine_id,))

        row = cursor.fetchone()

        if row is None:
            abort(404)


        (
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
            region_id,
            latitude,
            longitude,
            region_code,
            region_name,
            region_level
        ) = row


        mine = {

            "id": id,

            "name": name,
            "code": code,
            "operator": operator,

            "state": state,
            "district": district,

            "status": status,
            "method": method,

            "risk_score": (
                float(risk_score)
                if risk_score is not None
                else None
            ),

            "risk_level": risk_level,

            "region_id": region_id,
            "region_code": region_code,
            "region_name": region_name,
            "region_level": region_level,

            "latitude": (
                float(latitude)
                if latitude is not None
                else None
            ),
            "longitude": (
                float(longitude)
                if longitude is not None
                else None
            )
        }
        return render_template(
            "mines/detail.html",
            mine=mine
        )
    except mariadb.Error as e:
        print(f"Error fetching mine details: {e}")
        abort(500)
    finally:
        if cursor:
            cursor.close()
        conn.close()

@app.route("/inspections")
@jwt_required()
def inspections():
    return render_template("./inspections/index.html")

@app.route("/inspections/<inspection_id>")
@jwt_required()
def inspection_detail(inspection_id):
    return render_template("./inspections/detail.html")

@app.route("/risk")
@jwt_required()
def risk():
    return render_template("risk.html")

@app.route("/alerts")
@jwt_required()
def alerts():
    return render_template("alert.html")

@app.route("/map")
@jwt_required()
def gis_map():
    return render_template("map.html")

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

        cursor = conn.cursor()

        query = """
            SELECT
                m.id,
                m.name,
                m.code,
                m.operator,
                m.state,
                m.district,
                m.status,
                m.method,
                m.risk_score,
                m.risk_level,
                m.latitude,
                m.longitude,

                g.id AS region_id,
                g.code AS region_code,
                g.name AS region_name,
                g.level AS region_level

            FROM mines m

            LEFT JOIN gis_regions g
                ON m.region_id = g.id

            WHERE m.latitude IS NOT NULL
              AND m.longitude IS NOT NULL

            ORDER BY m.id DESC
        """

        cursor.execute(query)

        rows = cursor.fetchall()

        features = []

        for row in rows:

            (
                mine_id,
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
            ) = row


            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        float(longitude),
                        float(latitude)
                    ]
                },

                "properties": {
                    "id": mine_id,
                    "name": name,
                    "code": code,
                    "operator": operator,
                    "state": state,
                    "district": district,
                    "status": status,
                    "method": method,
                    "risk_score": (
                        float(risk_score)
                        if risk_score is not None
                        else None
                    ),
                    "risk_level": risk_level,
                    "region": {
                        "id": region_id,
                        "code": region_code,
                        "name": region_name,
                        "level": region_level

                    }
                }
            }
            features.append(feature)
        return jsonify({
            "type": "FeatureCollection",
            "features": features
        })
    except mariadb.Error as e:
        return jsonify({
            "type": "FeatureCollection",
            "features": [],
            "error": str(e)
        }), 500
    finally:
        if cursor:
            cursor.close()
        conn.close()
    
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

def classify_finding(text):

    inputs = tokenizer(
        text,
        return_tensors='pt',
        truncation=True,
        padding=True
    )

    inputs = {
        k: v.to(device)
        for k, v in inputs.items()
    }

    with torch.no_grad():

        outputs = model(
            input_ids=inputs['input_ids'],
            attention_mask=inputs['attention_mask']
        )

    issue_id = torch.argmax(
        outputs['issue'],
        dim=1
    ).item()

    category_id = torch.argmax(
        outputs['category'],
        dim=1
    ).item()

    severity_id = torch.argmax(
        outputs['severity'],
        dim=1
    ).item()

    recurring_id = torch.argmax(
        outputs['recurring'],
        dim=1
    ).item()

    return {
        'issue': label_mappings['issue'][issue_id],
        'category': label_mappings['category'][category_id],
        'severity': label_mappings['severity'][severity_id],
        'recurring': label_mappings['recurring'][recurring_id]
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
        risk_input_encoded = risk_encoder.transform(
            risk_input
        )
        predicted_risk = risk_model.predict(
            risk_input_encoded
        )[0]
        probabilities = risk_model.predict_proba(
            risk_input_encoded
        )[0]

        predicted_index = list(risk_model.classes_).index(predicted_risk)
        risk_confidence = (
            probabilities[predicted_index] * 100
        )
        risk_results.append({
            **result,
            "predicted_risk":
                predicted_risk,
            "risk_confidence":
                round(risk_confidence,2)
        })

        risk_results_df = pd.DataFrame(risk_results)
        risk_results_df
    return risk_results_df

@app.route("/findings")
def findings():
    results = process_pdf()
    risk_results = calculate_risk(results)
    return render_template(
        "findings.html",
        results=risk_results,
        count=len(risk_results)
    )
        
if __name__ == "__main__":
    app.run(debug=True)