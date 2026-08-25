from flask import Flask, render_template, session, request, redirect, url_for, flash, jsonify
from flask_session import Session
from helper import login_required
import os
import json
from pathlib import Path
from datetime import datetime,timedelta,timezone
import re
import pymupdf
import torch
from load_model import model, tokenizer, label_mappings, device
from dotenv import load_dotenv
from flask_jwt_extended import create_access_token,get_jwt,get_jwt_identity,jwt_required,JWTManager,set_access_cookies,unset_jwt_cookies

app = Flask(__name__)
load_dotenv() 
# If true this will only allow the cookies that contain your JWTs to be sent
# over https. In production, this should always be set to True
app.config["JWT_COOKIE_SECURE"] = False
app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
app.config["JWT_SECRET_KEY"] = os.getenv('jwt_secret_key')
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)

jwt = JWTManager(app)

def get_database():
    conn = sqlite3.connect('ledger.db')
    conn.row_factory = sqlite3.Row
    return conn

PDF_PATH = './data/Coal_Mine_Inspection_Report_Concise.pdf'

# Using an `after_request` callback, we refresh any token that is within 30
# minutes of expiring. Change the timedeltas to match the needs of your application.
@app.after_request
def refresh_expiring_jwts(response):
    try:
        exp_timestamp = get_jwt()["exp"]
        now = datetime.now(timezone.utc)
        target_timestamp = datetime.timestamp(now + timedelta(minutes=30))
        if target_timestamp > exp_timestamp:
            access_token = create_access_token(identity=get_jwt_identity())
            set_access_cookies(response, access_token)
        return response
    except (RuntimeError, KeyError):
        # Case where there is not a valid JWT. Just return the original response
        return response

@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        username = request.form.get("name")
        password = request.form.get("password")

        if not username or not password:
            flash("Username and password are required", "danger")
            return redirect(url_for("login"))

        db = get_database()
        try:
            user = db.execute(
                "SELECT id, name, password FROM users WHERE name = ?",
                (username,)
            ).fetchone()

            if not user:
                flash("User not found", "danger")
                return redirect(url_for("login"))

            if not check_password_hash(user["password"], password):
                flash("Incorrect password", "danger")
                return redirect(url_for("login"))

            # Create the token
            access_token = create_access_token(identity=username)

            # Create the real response that will be returned
            response = redirect("/")          # or redirect(url_for("home"))
            set_access_cookies(response, access_token)

            flash(f"Welcome back, {user['name']}!", "success")
            return response

        except Exception as e:
            flash(f"Error: {str(e)}", "danger")
            return redirect(url_for("login"))

        finally:
            db.close()

    return render_template("login.html")

@app.route("/logout", methods=["POST"])
def logout():
    response = jsonify({"msg": "logout successful"})
    unset_jwt_cookies(response)
    return response

@app.route("/")
# @jwt_required()
def dashboard():
    return render_template("dashboard.html")

@app.route("/mines")
# @jwt_required()
def mines():
    return render_template("./mines/index.html")

@app.route("/mines/<mine_id>")
# @jwt_required()
def mine_detail(mine_id):
    geojson_path = (
        Path(app.root_path)
        / "data"
        / "mines.geojson"
    )
    if not geojson_path.exists():
        abort(404)

    with open(geojson_path,"r",encoding="utf-8") as f:
        geojson = json.load(f)
    selected_mine = None

    for feature in geojson.get("features", []):
        properties = feature.get(
            "properties",
            {}
        )
        if str(properties.get("mine_id")) == str(mine_id):
            geometry = feature.get(
                "geometry",
                {}
            )
            coordinates = geometry.get(
                "coordinates",
                []
            )
            selected_mine = {
                **properties,
                "longitude": (
                    coordinates[0]
                    if len(coordinates) >= 2
                    else None
                ),
                "latitude": (
                    coordinates[1]
                    if len(coordinates) >= 2
                    else None
                )
            }
            break

    if selected_mine is None:
        abort(404)

    return render_template(
        "mines/detail.html",
        mine=selected_mine
    )

@app.route("/inspections")
# @jwt_required()
def inspections():
    return render_template("./inspections/index.html")

@app.route("/inspections/<inspection_id>")
# @jwt_required()
def inspection_detail(inspection_id):
    return render_template("./inspections/detail.html")

@app.route("/risk")
# @jwt_required()
def risk():
    return render_template("risk.html")

@app.route("/alerts")
# @jwt_required()
def alerts():
    return render_template("alert.html")

@app.route("/map")
# @jwt_required()
def gis_map():
    return render_template("map.html")

@app.route("/api/v1/gis/mines")
# @jwt_required()
def gis_mines():
    geojson_path = (
        Path(app.root_path)
        / "data"
        / "mines.geojson"
    )

    if not geojson_path.exists():
        return jsonify({
            "type": "FeatureCollection",
            "features": [],
            "error": "GIS dataset not generated"
        }), 404

    try:
        with open(
            geojson_path,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)
        return jsonify(data)

    except Exception as e:
        return jsonify({
            "type": "FeatureCollection",
            "features": [],
            "error": str(e)
        }), 500

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

@app.route('/findings')
def findings():

    results = process_pdf()
    return render_template(
        'findings.html',
        results=results,
        count=len(results)
    )
        
if __name__ == "__main__":
    app.run(debug=True)