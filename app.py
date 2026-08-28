from flask import (
    Flask, render_template, session, request, redirect, url_for, flash,
    jsonify, abort, send_from_directory
)
from flask_session import Session
from helper import login_required
import os
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
import re
import pymupdf
import torch
import mariadb
import pandas as pd
import joblib
from xml.sax.saxutils import escape
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
    KeepTogether
)
from werkzeug.utils import secure_filename
from load_model import model_1, tokenizer_1, label_mappings, device_1, model_2, tokenizer_2, device_2, gen_pipeline
from dotenv import load_dotenv
from werkzeug.security import check_password_hash, generate_password_hash
from flask_jwt_extended import (
    create_access_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
    JWTManager,
    set_access_cookies,
    unset_jwt_cookies
)

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
app.config["JWT_COOKIE_CSRF_PROTECT"] = False

# Local development: HTTP, not HTTPS.
# IMPORTANT: flip JWT_COOKIE_SECURE to True (and serve over HTTPS) before
# deploying to production, or session cookies can be intercepted.
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
        app.logger.error(f"Error connecting to MariaDB: {e}")
        return None


REPORT_DIR = Path("./data/generated_reports").resolve()
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# PDF snapshots auto-generated the moment a raw mobile submission lands in
# the validation queue - distinct from REPORT_DIR, which holds the FINAL
# report generated after admin approval.
RAW_REPORT_DIR = Path("./data/raw_reports").resolve()
RAW_REPORT_DIR.mkdir(parents=True, exist_ok=True)

UPLOAD_DIR = Path("./data/uploads").resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

EVIDENCE_UPLOAD_DIR = UPLOAD_DIR / "evidence"
EVIDENCE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

RISK_MODEL_PATH = "./models/mira-risk-classifier.pkl"
ENCODER_PATH = "./models/mira-risk-encoder.pkl"

risk_model = joblib.load(RISK_MODEL_PATH)
risk_encoder = joblib.load(ENCODER_PATH)


class ApprovalError(Exception):
    """Raised when an inspection approval cannot proceed for a business reason."""

    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# Using an `after_request` callback, we refresh any token that is within 30
# minutes of expiring. Currently disabled: users are hard-logged-out after
# JWT_ACCESS_TOKEN_EXPIRES with no silent refresh. Uncomment to enable.
#
# @app.after_request
# def refresh_expiring_jwts(response):
#     try:
#         claims = get_jwt()
#         exp_timestamp = claims["exp"]
#         now = datetime.now(timezone.utc)
#         target_timestamp = datetime.timestamp(now + timedelta(minutes=30))
#
#         if target_timestamp > exp_timestamp:
#             access_token = create_access_token(
#                 identity=get_jwt_identity(),
#                 additional_claims={
#                     "name": claims.get("name"),
#                     "role": claims.get("role"),
#                     "regional_office": claims.get("regional_office"),
#                 }
#             )
#             set_access_cookies(response, access_token)
#
#         return response
#     except (RuntimeError, KeyError):
#         # No JWT on this request (e.g. /login, static files).
#         return response


@jwt.unauthorized_loader
def unauthorized_callback(reason):
    app.logger.warning(f"JWT UNAUTHORIZED: {reason}")
    flash("Please log in to continue.", "warning")
    return redirect(url_for("login"))


@jwt.invalid_token_loader
def invalid_token_callback(reason):
    app.logger.warning(f"JWT INVALID: {reason}")
    flash("Your login session is invalid. Please log in again.", "danger")
    return redirect(url_for("login"))


@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    app.logger.info("JWT EXPIRED")
    flash("Your session has expired. Please log in again.", "warning")
    return redirect(url_for("login"))


@app.context_processor
def inject_user_role():
    try:
        claims = get_jwt()
        return {"current_user_role": claims.get("role")}
    except Exception:
        return {"current_user_role": None}


@app.context_processor
def inject_pending_inspection_count():
    """
    Powers the "Verification Queue" badge in the sidebar. Admin-only and
    fails silently (returns None, which the template just doesn't render a
    badge for) rather than breaking page loads if the DB is unreachable.
    """

    try:
        claims = get_jwt()
    except Exception:
        return {"pending_inspection_count": None}

    if claims.get("role") != "admin":
        return {"pending_inspection_count": None}

    conn = get_db_connection()

    if conn is None:
        return {"pending_inspection_count": None}

    cursor = None

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM inspection_raw WHERE status = 'PENDING_APPROVAL'")
        row = cursor.fetchone()
        return {"pending_inspection_count": row[0] if row else 0}

    except mariadb.Error:
        app.logger.exception("Unable to load pending inspection count")
        return {"pending_inspection_count": None}

    finally:
        if cursor:
            cursor.close()
        conn.close()


def safe_json_load(value, default=None):
    """Safely convert a JSON string/database value into a Python object."""

    if default is None:
        default = []

    if value is None:
        return default

    if isinstance(value, (dict, list)):
        return value

    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default


def wants_json():
    """
    True when the caller expects a JSON response (fetch/AJAX or an explicit
    Accept: application/json), False for a plain HTML form submission -
    which should get a redirect + flash message instead.
    """

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return True

    best = request.accept_mimetypes.best_match(["application/json", "text/html"])
    return best == "application/json" and request.accept_mimetypes[best] >= request.accept_mimetypes["text/html"]


# ============================================================
# AUTH
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("name", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Username and password are required.", "danger")
            return redirect(url_for("login"))

        conn = None
        cursor = None

        try:
            conn = get_db_connection()

            if conn is None:
                flash("Database connection failed. Please try again later.", "danger")
                return redirect(url_for("login"))

            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT id, name, role, regional_office, password_hash, is_active
                FROM users
                WHERE name = ?
                LIMIT 1
                """,
                (username,)
            )

            user = cursor.fetchone()

            if not user:
                flash("Invalid username or password.", "danger")
                return redirect(url_for("login"))

            if not user["is_active"]:
                flash(
                    "Your account has been deactivated. Contact an administrator.",
                    "danger"
                )
                return redirect(url_for("login"))

            if not check_password_hash(user["password_hash"], password):
                flash("Invalid username or password.", "danger")
                return redirect(url_for("login"))

            access_token = create_access_token(
                identity=str(user["id"]),
                additional_claims={
                    "name": user["name"],
                    "role": user["role"],
                    "regional_office": user["regional_office"]
                }
            )

            # Flask session mirrors the identity for use in templates
            # (e.g. session["user_name"]); auth itself is JWT-based.
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["role"] = user["role"]
            session["regional_office"] = user["regional_office"]

            response = redirect(url_for("dashboard"))
            set_access_cookies(response, access_token)

            return response

        except mariadb.Error:
            app.logger.exception("MariaDB login error")
            flash("Database error while logging in. Please try again.", "danger")
            return redirect(url_for("login"))

        except Exception:
            app.logger.exception("Login error")
            flash("An error occurred while logging in. Please try again.", "danger")
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

    if claims.get("role") != "admin":
        flash("Administrator access required.", "danger")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        role = request.form.get("role", "").strip()
        regional_office = request.form.get("regional_office", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or not password or not role:
            flash("Name, role and password are required.", "danger")
            return redirect(url_for("register"))

        if role not in ["inspector", "admin"]:
            flash("Invalid role selected.", "danger")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "danger")
            return redirect(url_for("register"))

        conn = None
        cursor = None

        try:
            conn = get_db_connection()

            if conn is None:
                flash("Database connection failed. Please try again later.", "danger")
                return redirect(url_for("register"))

            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                "SELECT id FROM users WHERE name = ? LIMIT 1",
                (name,)
            )

            if cursor.fetchone():
                flash("A user with this name already exists.", "danger")
                return redirect(url_for("register"))

            password_hash = generate_password_hash(password)

            cursor.execute(
                """
                INSERT INTO users (name, role, regional_office, password_hash, is_active)
                VALUES (?, ?, ?, ?, 1)
                """,
                (name, role, regional_office or None, password_hash)
            )

            conn.commit()

            flash(f"User '{name}' created successfully.", "success")
            return redirect(url_for("dashboard"))

        except mariadb.IntegrityError:
            if conn:
                conn.rollback()
            flash("A user with this name already exists.", "danger")
            return redirect(url_for("register"))

        except mariadb.Error:
            if conn:
                conn.rollback()
            app.logger.exception("MariaDB user registration error")
            flash("Database error while creating the user.", "danger")
            return redirect(url_for("register"))

        except Exception:
            if conn:
                conn.rollback()
            app.logger.exception("User registration error")
            flash("Unable to create user. Please try again.", "danger")
            return redirect(url_for("register"))

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template("register.html")


@app.route("/logout", methods=["POST"])
def logout():
    response = jsonify({"msg": "logout successful"})
    unset_jwt_cookies(response)
    session.clear()
    return response


# ============================================================
# MOBILE INSPECTION SUBMISSION
# ============================================================

def _image_aspect_ratio(image_path):
    """
    height/width for an image file, used to embed evidence photos in the PDF
    without distorting them. Falls back to a 3:4 portrait guess (typical
    phone-camera shot) if the file can't be read.
    """

    try:
        img_doc = pymupdf.open(image_path)
        rect = img_doc[0].rect
        img_doc.close()

        if rect.width:
            return rect.height / rect.width

    except Exception:
        app.logger.warning("Unable to read image dimensions for %s", image_path)

    return 4 / 3

def _pdf_text(value):
    """
    Safely convert arbitrary values into ReportLab XML-safe text.
    Prevents &, <, > and similar characters in inspection notes from
    breaking Paragraph rendering.
    """
    if value is None:
        return "-"

    return escape(str(value))


def _format_coordinate(value, positive_suffix, negative_suffix):
    """
    Format a latitude/longitude value for the report.

    Example:
        19.9156 -> 19.9156° N
       -19.9156 -> 19.9156° S
    """
    if value is None:
        return "-"

    try:
        value = float(value)

        if value >= 0:
            return f"{abs(value):.4f}° {positive_suffix}"

        return f"{abs(value):.4f}° {negative_suffix}"

    except (TypeError, ValueError):
        return str(value)


def generate_raw_submission_pdf(inspection, notes, evidence):
    """
    Generates a RAW/PENDING version of the MIRA Coal Mine Inspection Report.

    The layout intentionally follows the structure of the concise reference
    inspection report:

        GOVERNMENT OF INDIA
        MINISTRY OF COAL
        DIRECTORATE OF MINES SAFETY
        COAL MINE INSPECTION REPORT

        1. MINE & LOCATION DETAILS
        2. INSPECTING OFFICER
        3. AREAS INSPECTED
        4. INSPECTION OBSERVATIONS
        5. INSPECTOR'S REMARKS

    Unlike the final report, this document is clearly marked as:
        RAW FIELD SUBMISSION
        PENDING ADMINISTRATIVE VERIFICATION

    No AI-generated risk/severity/classification is added here because the
    raw submission has not yet passed the approval/AI pipeline.
    """

    report_no = (
        inspection.get("report_no")
        or f"RAW-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    )

    filename = secure_filename(f"{report_no}_raw.pdf")
    pdf_path = RAW_REPORT_DIR / filename

    RAW_REPORT_DIR.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"Coal Mine Inspection Report - {report_no}",
        author="MIRA"
    )

    styles = getSampleStyleSheet()

    # ============================================================
    # STYLES
    # ============================================================

    government_style = ParagraphStyle(
        "GovernmentHeader",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        spaceAfter=2
    )

    main_title_style = ParagraphStyle(
        "MainTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        spaceBefore=4,
        spaceAfter=3
    )

    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        spaceAfter=8
    )

    pending_style = ParagraphStyle(
        "PendingBadge",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#92400e"),
        backColor=colors.HexColor("#fef3c7"),
        borderColor=colors.HexColor("#d97706"),
        borderWidth=0.7,
        borderPadding=5,
        spaceBefore=3,
        spaceAfter=10
    )

    section_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        spaceBefore=10,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8.8,
        leading=12.5,
        spaceAfter=4
    )

    finding_heading_style = ParagraphStyle(
        "FindingHeading",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        spaceBefore=5,
        spaceAfter=3
    )

    footer_style = ParagraphStyle(
        "FooterText",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=colors.grey
    )

    # ============================================================
    # HEADER
    # ============================================================

    story = [
        Paragraph("GOVERNMENT OF INDIA", government_style),
        Paragraph("MINISTRY OF COAL", government_style),
        Paragraph("DIRECTORATE OF MINES SAFETY", government_style),
        Spacer(1, 3 * mm),
        Paragraph("COAL MINE INSPECTION REPORT", main_title_style),
        Paragraph(
            "SYNTHETIC PROTOTYPE DOCUMENT — FOR AI/ML PROTOTYPE DEVELOPMENT ONLY",
            subtitle_style
        ),
        Paragraph(
            "RAW FIELD SUBMISSION — PENDING ADMINISTRATIVE VERIFICATION",
            pending_style
        )
    ]

    # ============================================================
    # REPORT METADATA
    # ============================================================

    report_date = inspection.get("report_date")

    if not report_date:
        report_date = datetime.now().strftime("%d %B %Y")

    metadata_rows = [
        [
            Paragraph("<b>Inspection Report No.</b>", body_style),
            Paragraph(_pdf_text(report_no), body_style),
            Paragraph("<b>Inspection Date</b>", body_style),
            Paragraph(
                _pdf_text(inspection.get("inspection_date")),
                body_style
            )
        ],
        [
            Paragraph("<b>Report Date</b>", body_style),
            Paragraph(_pdf_text(report_date), body_style),
            Paragraph("<b>Inspection Type</b>", body_style),
            Paragraph(
                _pdf_text(
                    inspection.get(
                        "inspection_type",
                        "Periodic Safety Inspection"
                    )
                ),
                body_style
            )
        ]
    ]

    metadata_table = Table(
        metadata_rows,
        colWidths=[38 * mm, 55 * mm, 38 * mm, 44 * mm]
    )

    metadata_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.45, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eeeeee")),
            ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#eeeeee")),
        ])
    )

    story.append(metadata_table)

    # ============================================================
    # 1. MINE & LOCATION DETAILS
    # ============================================================

    story.append(
        Paragraph("1. MINE &amp; LOCATION DETAILS", section_style)
    )

    latitude = _format_coordinate(
        inspection.get("latitude"),
        "N",
        "S"
    )

    longitude = _format_coordinate(
        inspection.get("longitude"),
        "E",
        "W"
    )

    coordinates = "-"

    if latitude != "-" and longitude != "-":
        coordinates = f"{latitude}, {longitude}"

    mine_rows = [
        [
            Paragraph("<b>Mine ID</b>", body_style),
            Paragraph(_pdf_text(inspection.get("mine_code")), body_style),
            Paragraph("<b>Mine Name</b>", body_style),
            Paragraph(_pdf_text(inspection.get("mine_name")), body_style)
        ],
        [
            Paragraph("<b>Operator</b>", body_style),
            Paragraph(_pdf_text(inspection.get("operator")), body_style),
            Paragraph("<b>Mine Status</b>", body_style),
            Paragraph(_pdf_text(inspection.get("mine_status")), body_style)
        ],
        [
            Paragraph("<b>State</b>", body_style),
            Paragraph(_pdf_text(inspection.get("state")), body_style),
            Paragraph("<b>District</b>", body_style),
            Paragraph(_pdf_text(inspection.get("district")), body_style)
        ],
        [
            Paragraph("<b>Coordinates</b>", body_style),
            Paragraph(_pdf_text(coordinates), body_style),
            Paragraph("<b>Mining Method</b>", body_style),
            Paragraph(_pdf_text(inspection.get("method")), body_style)
        ]
    ]

    mine_table = Table(
        mine_rows,
        colWidths=[32 * mm, 58 * mm, 32 * mm, 53 * mm]
    )

    mine_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.45, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eeeeee")),
            ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#eeeeee")),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4)
        ])
    )

    story.append(mine_table)

    # ============================================================
    # 2. INSPECTING OFFICER
    # ============================================================

    story.append(
        Paragraph("2. INSPECTING OFFICER", section_style)
    )

    inspector_rows = [
        [
            Paragraph("<b>Inspector Name</b>", body_style),
            Paragraph(
                _pdf_text(inspection.get("inspector_name")),
                body_style
            )
        ],
        [
            Paragraph("<b>Designation</b>", body_style),
            Paragraph(
                _pdf_text(
                    inspection.get(
                        "inspector_designation",
                        "Field Inspector"
                    )
                ),
                body_style
            )
        ],
        [
            Paragraph("<b>Regional Office</b>", body_style),
            Paragraph(
                _pdf_text(
                    inspection.get(
                        "regional_office",
                        "Directorate of Mines Safety"
                    )
                ),
                body_style
            )
        ],
        [
            Paragraph("<b>Inspection Duration</b>", body_style),
            Paragraph(
                _pdf_text(inspection.get("duration")),
                body_style
            )
        ]
    ]

    inspector_table = Table(
        inspector_rows,
        colWidths=[45 * mm, 130 * mm]
    )

    inspector_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.45, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eeeeee")),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4)
        ])
    )

    story.append(inspector_table)

    # ============================================================
    # 3. AREAS INSPECTED
    # ============================================================

    story.append(
        Paragraph("3. AREAS INSPECTED", section_style)
    )

    areas = inspection.get("areas_inspected")

    if isinstance(areas, list):
        areas_text = "; ".join(
            str(area) for area in areas if str(area).strip()
        )
    else:
        areas_text = str(areas) if areas else "Not specified in raw submission."

    story.append(
        Paragraph(
            _pdf_text(areas_text),
            body_style
        )
    )

    # ============================================================
    # 4. INSPECTION OBSERVATIONS
    # ============================================================

    story.append(
        Paragraph("4. INSPECTION OBSERVATIONS", section_style)
    )

    if notes:

        finding_number = 0

        for index, note in enumerate(notes, start=1):

            if isinstance(note, dict):

                text = (
                    note.get("content")
                    or note.get("text")
                    or note.get("note")
                    or ""
                )

                finding_id = (
                    note.get("finding_id")
                    or note.get("code")
                    or f"F-{index:02d}"
                )

            else:

                text = str(note)
                finding_id = f"F-{index:02d}"

            text = str(text).strip()

            if not text:
                continue

            finding_number += 1

            # If the mobile note already starts with F-01:, don't duplicate it.
            if text.upper().startswith("F-"):
                finding_title = text
            else:
                finding_title = f"Finding {finding_id}"

            story.append(
                Paragraph(
                    _pdf_text(finding_title),
                    finding_heading_style
                )
            )

            # Remove F-XX prefix from the body if it already exists.
            clean_text = re.sub(
                r"^F-\d+\s*:\s*",
                "",
                text,
                flags=re.IGNORECASE
            )

            story.append(
                Paragraph(
                    _pdf_text(clean_text),
                    body_style
                )
            )

    else:

        story.append(
            Paragraph(
                "No inspection observations were submitted.",
                body_style
            )
        )

    # ============================================================
    # 5. INSPECTOR'S REMARKS
    # ============================================================

    story.append(
        Paragraph("5. INSPECTOR'S REMARKS", section_style)
    )

    remarks = inspection.get("remarks")

    if remarks:
        story.append(
            Paragraph(
                _pdf_text(remarks),
                body_style
            )
        )
    else:
        story.append(
            Paragraph(
                "No inspector remarks were submitted.",
                body_style
            )
        )

    # ============================================================
    # 6. FIELD EVIDENCE
    # ============================================================

    story.append(
        Paragraph("6. FIELD EVIDENCE", section_style)
    )

    if evidence:

        for index, item in enumerate(evidence, start=1):

            if not isinstance(item, dict):
                continue

            evidence_type = (
                item.get("type")
                or item.get("evidence_type")
                or "Photo"
            )

            description = item.get("description")

            caption = (
                f"<b>Evidence {index} — "
                f"{_pdf_text(str(evidence_type).title())}</b>"
            )

            if description:
                caption += f" — {_pdf_text(description)}"

            latitude_value = item.get("latitude")
            longitude_value = item.get("longitude")

            if (
                latitude_value is not None
                and longitude_value is not None
            ):
                caption += (
                    f" ({_pdf_text(latitude_value)}, "
                    f"{_pdf_text(longitude_value)})"
                )

            story.append(
                Paragraph(
                    caption,
                    body_style
                )
            )

            file_path = (
                item.get("file_path")
                or item.get("uri")
            )

            if file_path and os.path.isfile(file_path):

                try:

                    aspect = _image_aspect_ratio(file_path)

                    image_width = 75 * mm
                    image_height = min(
                        image_width * aspect,
                        95 * mm
                    )

                    story.append(
                        Image(
                            file_path,
                            width=image_width,
                            height=image_height
                        )
                    )

                except Exception:

                    app.logger.warning(
                        "Could not embed evidence image %s",
                        file_path
                    )

                    story.append(
                        Paragraph(
                            "[Evidence image unavailable]",
                            body_style
                        )
                    )

            elif file_path:

                story.append(
                    Paragraph(
                        f"File: {_pdf_text(file_path)}",
                        body_style
                    )
                )

            story.append(
                Spacer(1, 5)
            )

    else:

        story.append(
            Paragraph(
                "No field evidence was attached to this submission.",
                body_style
            )
        )

    # ============================================================
    # SIGNATURE / STATUS INFORMATION
    # ============================================================

    story.append(Spacer(1, 8))

    signature_rows = [
        [
            Paragraph(
                "<b>Inspector</b><br/>"
                f"{_pdf_text(inspection.get('inspector_name'))}",
                body_style
            ),
            Paragraph(
                "<b>Status</b><br/>"
                "PENDING ADMINISTRATIVE VERIFICATION",
                body_style
            )
        ],
        [
            Paragraph(
                "<b>Inspection Date</b><br/>"
                f"{_pdf_text(inspection.get('inspection_date'))}",
                body_style
            ),
            Paragraph(
                "<b>Document Type</b><br/>"
                "RAW FIELD SUBMISSION",
                body_style
            )
        ]
    ]

    signature_table = Table(
        signature_rows,
        colWidths=[87.5 * mm, 87.5 * mm]
    )

    signature_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.45, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5)
        ])
    )

    story.append(signature_table)

    story.append(Spacer(1, 8))

    story.append(
        Paragraph(
            "RAW DOCUMENT — FOR AI PROTOTYPE / DEMONSTRATION PURPOSES ONLY",
            footer_style
        )
    )

    story.append(
        Paragraph(
            "This document represents the information submitted from the "
            "field mobile application. It has not yet been administratively "
            "approved and has not undergone MIRA AI risk assessment.",
            footer_style
        )
    )

    # ============================================================
    # BUILD PDF
    # ============================================================

    doc.build(story)

    return str(pdf_path)

@app.route("/api/mobile/inspection-raw", methods=["POST"])
def create_raw_inspection():
    """
    Mobile inspection submission endpoint.

    Supports:
        1. application/json
        2. multipart/form-data

    Creates:
        - inspection_raw record
        - raw submission PDF
        - evidence files when multipart photos are uploaded

    Current prototype authentication:
        inspector_id is supplied by the mobile app.

    IMPORTANT:
        Before production, replace inspector_id from the request
        with the authenticated user's JWT identity.
    """

    is_multipart = (
        bool(request.content_type)
        and "multipart/form-data" in request.content_type
    )

    # ------------------------------------------------------------
    # 1. READ REQUEST DATA
    # ------------------------------------------------------------

    evidence = []
    areas_inspected = []

    if is_multipart:

        form = request.form

        inspector_id = form.get("inspector_id")
        mine_id = form.get("mine_id")

        inspection_date = form.get("inspection_date")
        report_no = form.get("report_no")
        duration = form.get("duration")
        remarks = form.get("remarks")

        notes = safe_json_load(
            form.get("notes"),
            []
        )

        areas_inspected = safe_json_load(
            form.get("areas_inspected"),
            []
        )

        evidence_meta = safe_json_load(
            form.get("evidence_meta"),
            []
        )

        uploaded_photos = request.files.getlist("photos")

        # --------------------------------------------------------
        # Save uploaded photos
        # --------------------------------------------------------

        if uploaded_photos:

            submission_dir = EVIDENCE_UPLOAD_DIR / (
                f"{inspector_id or 'unknown'}_"
                f"{datetime.now().strftime('%Y%m%d%H%M%S')}"
            )

            submission_dir.mkdir(
                parents=True,
                exist_ok=True
            )

            for index, photo in enumerate(uploaded_photos):

                if not photo or photo.filename == "":
                    continue

                safe_name = (
                    secure_filename(photo.filename)
                    or f"photo_{index}.jpg"
                )

                dest_path = (
                    submission_dir /
                    f"{index}_{safe_name}"
                )

                photo.save(str(dest_path))

                meta = (
                    evidence_meta[index]
                    if index < len(evidence_meta)
                    and isinstance(evidence_meta[index], dict)
                    else {}
                )

                evidence.append({
                    "file_path": str(dest_path),
                    "latitude": meta.get("latitude"),
                    "longitude": meta.get("longitude"),
                    "type": meta.get("type", "photo"),
                    "description": meta.get("description")
                })

    else:

        data = request.get_json(silent=True)

        if not data:

            return jsonify({
                "success": False,
                "message": (
                    "JSON body or multipart/form-data "
                    "is required."
                )
            }), 400

        inspector_id = data.get("inspector_id")
        mine_id = data.get("mine_id")

        inspection_date = data.get("inspection_date")
        report_no = data.get("report_no")
        duration = data.get("duration")
        remarks = data.get("remarks")

        notes = data.get("notes", [])

        evidence = data.get("evidence", [])

        areas_inspected = data.get(
            "areas_inspected",
            []
        )

    # ------------------------------------------------------------
    # 2. BASIC VALIDATION
    # ------------------------------------------------------------

    if not inspector_id:

        return jsonify({
            "success": False,
            "message": "inspector_id is required."
        }), 400

    if not mine_id:

        return jsonify({
            "success": False,
            "message": "mine_id is required."
        }), 400

    # Convert IDs to integers
    try:
        inspector_id = int(inspector_id)
        mine_id = int(mine_id)

    except (TypeError, ValueError):

        return jsonify({
            "success": False,
            "message": "inspector_id and mine_id must be integers."
        }), 400

    inspection_date = (
        inspection_date
        or datetime.now().strftime("%Y-%m-%d")
    )

    report_no = (
        report_no
        or f"RAW-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    )

    # ------------------------------------------------------------
    # 3. DATABASE CONNECTION
    # ------------------------------------------------------------

    conn = get_db_connection()

    if conn is None:

        return jsonify({
            "success": False,
            "message": "Database connection failed."
        }), 500

    cursor = None

    try:

        cursor = conn.cursor(dictionary=True)

        # ========================================================
        # 4. VALIDATE INSPECTOR
        # ========================================================

        cursor.execute(
            """
            SELECT
                id,
                name,
                role,
                regional_office,
                is_active
            FROM users
            WHERE id = ?
              AND is_active = 1
            LIMIT 1
            """,
            (inspector_id,)
        )

        inspector = cursor.fetchone()

        if not inspector:

            return jsonify({
                "success": False,
                "message": (
                    "inspector_id does not match "
                    "an active user."
                )
            }), 400

        # Optional but strongly recommended:
        # Only users with inspector role can submit
        if inspector["role"] != "inspector":

            return jsonify({
                "success": False,
                "message": (
                    "The specified user is not an inspector."
                )
            }), 403

        inspector_name = inspector["name"]

        # Use database regional office if available
        regional_office = (
            inspector.get("regional_office")
            or "Directorate of Mines Safety"
        )

        # ========================================================
        # 5. VALIDATE MINE
        # ========================================================

        cursor.execute(
            """
            SELECT
                id,
                name,
                code,
                operator,
                state,
                district,
                status,
                method,
                latitude,
                longitude
            FROM mines
            WHERE id = ?
            LIMIT 1
            """,
            (mine_id,)
        )

        mine = cursor.fetchone()

        if not mine:

            return jsonify({
                "success": False,
                "message": "mine_id does not exist."
            }), 400

        # ========================================================
        # 6. GENERATE RAW PDF
        # ========================================================

        raw_pdf_path = None

        try:

            raw_pdf_path = generate_raw_submission_pdf(

                {
                    # ------------------------------------------------
                    # Report metadata
                    # ------------------------------------------------
                    "report_no": report_no,

                    "inspection_date": inspection_date,

                    "report_date": datetime.now().strftime(
                        "%d %B %Y"
                    ),

                    "inspection_type": (
                        "Periodic Safety Inspection"
                    ),

                    # ------------------------------------------------
                    # Mine details
                    # ------------------------------------------------
                    "mine_name": mine["name"],
                    "mine_code": mine["code"],
                    "operator": mine["operator"],
                    "state": mine["state"],
                    "district": mine["district"],
                    "mine_status": mine["status"],
                    "method": mine["method"],
                    "latitude": mine["latitude"],
                    "longitude": mine["longitude"],

                    # ------------------------------------------------
                    # Inspector
                    # ------------------------------------------------
                    "inspector_name": inspector_name,

                    "inspector_designation": (
                        "Field Inspector"
                    ),

                    "regional_office": regional_office,

                    # ------------------------------------------------
                    # Inspection
                    # ------------------------------------------------
                    "duration": duration,
                    "remarks": remarks,

                    "areas_inspected": areas_inspected
                },

                notes,

                evidence
            )

        except Exception:

            app.logger.exception(
                "Raw submission PDF generation failed "
                "for report %s - continuing without it",
                report_no
            )

        # ========================================================
        # 7. INSERT RAW INSPECTION
        # ========================================================

        cursor.execute(
            """
            INSERT INTO inspection_raw
            (
                inspector_id,
                mine_id,
                report_no,
                inspection_date,
                duration,
                remarks,
                notes_json,
                evidence_json,
                raw_pdf_path,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING_APPROVAL')
            """,
            (
                inspector_id,
                mine_id,
                report_no,
                inspection_date,
                duration,
                remarks,
                json.dumps(notes),
                json.dumps(evidence),
                raw_pdf_path
            )
        )

        raw_id = cursor.lastrowid

        conn.commit()

        # ========================================================
        # 8. RESPONSE
        # ========================================================

        return jsonify({

            "success": True,

            "message": (
                "Inspection submitted for admin approval."
            ),

            "raw_inspection_id": raw_id,

            "status": "PENDING_APPROVAL",

            "raw_pdf_path": raw_pdf_path,

            "inspector": {
                "id": inspector["id"],
                "name": inspector_name
            },

            "mine": {
                "id": mine["id"],
                "name": mine["name"],
                "code": mine["code"]
            }

        }), 201

    # ============================================================
    # DATABASE ERROR
    # ============================================================

    except mariadb.Error as e:

        if conn:
            conn.rollback()

        app.logger.exception(
            "Failed to create raw inspection"
        )

        return jsonify({
            "success": False,
            "message": "Unable to save inspection.",
            "error": str(e)
        }), 500

    # ============================================================
    # UNEXPECTED ERROR
    # ============================================================

    except Exception as e:

        if conn:
            conn.rollback()

        app.logger.exception(
            "Unexpected raw inspection error"
        )

        return jsonify({
            "success": False,
            "message": "Unexpected server error.",
            "error": str(e)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()

@app.route("/api/admin/reports/raw/<filename>")
@jwt_required()
def download_raw_report(filename):
    """Serves an auto-generated raw-submission PDF to an admin for review."""

    claims = get_jwt()

    if claims.get("role") != "admin":
        abort(403)

    safe_name = secure_filename(filename)

    if not safe_name or not (RAW_REPORT_DIR / safe_name).is_file():
        abort(404)

    return send_from_directory(str(RAW_REPORT_DIR), safe_name)


@app.route("/api/admin/reports/final/<filename>")
@jwt_required()
def download_final_report(filename):
    """Serves a final, AI-processed inspection report PDF."""

    claims = get_jwt()

    if claims.get("role") != "admin":
        abort(403)

    safe_name = secure_filename(filename)

    if not safe_name or not (REPORT_DIR / safe_name).is_file():
        abort(404)

    return send_from_directory(str(REPORT_DIR), safe_name)


# ============================================================
# AI ENGINE
# ============================================================

def get_label(mapping, index):
    """
    Convert a model prediction index into its label.
    label_mappings.json stores labels as lists: ["label1", "label2", ...]
    """

    if not isinstance(mapping, list):
        raise TypeError(f"Expected label mapping to be a list, got {type(mapping).__name__}")

    if index < 0 or index >= len(mapping):
        raise IndexError(f"Label index {index} is outside the mapping range 0-{len(mapping) - 1}")

    return mapping[index]


def classify_finding(text):
    """Run MODEL 1 over a single finding's text and return issue/category/severity/recurring."""

    inputs = tokenizer_1(text, return_tensors="pt", truncation=True, padding=True)
    inputs = {key: value.to(device_1) for key, value in inputs.items()}

    with torch.no_grad():
        outputs = model_1(input_ids=inputs["input_ids"], attention_mask=inputs["attention_mask"])

    issue_id = torch.argmax(outputs["issue"], dim=1).item()
    category_id = torch.argmax(outputs["category"], dim=1).item()
    severity_id = torch.argmax(outputs["severity"], dim=1).item()
    recurring_id = torch.argmax(outputs["recurring"], dim=1).item()

    return {
        "issue": get_label(label_mappings["issue"], issue_id),
        "category": get_label(label_mappings["category"], category_id),
        "severity": get_label(label_mappings["severity"], severity_id),
        "recurring": get_label(label_mappings["recurring"], recurring_id)
    }


def process_raw_findings(notes):
    """Classify each raw mobile note into a structured finding."""

    results = []

    for index, note in enumerate(notes):
        if isinstance(note, dict):
            text = note.get("content") or note.get("text") or note.get("note") or ""
        else:
            text = str(note)

        text = text.strip()

        if not text:
            continue

        prediction = classify_finding(text)

        results.append({
            "finding_id": f"F-{index + 1:03d}",
            "finding_text": text,
            "issue": prediction["issue"],
            "category": prediction["category"],
            "severity": prediction["severity"],
            "recurring": prediction["recurring"]
        })

    return results


def calculate_risk(results):
    """Run MODEL 2 (the risk classifier) over already-classified findings."""

    risk_results = []

    for result in results:
        risk_input = pd.DataFrame([{
            "issue": result["issue"],
            "category": result["category"],
            "severity": result["severity"],
            "recurring": result["recurring"]
        }])

        risk_input_encoded = risk_encoder.transform(risk_input)

        predicted_risk = risk_model.predict(risk_input_encoded)[0]
        probabilities = risk_model.predict_proba(risk_input_encoded)[0]
        predicted_index = list(risk_model.classes_).index(predicted_risk)
        risk_confidence = probabilities[predicted_index] * 100

        risk_results.append({
            **result,
            "predicted_risk": predicted_risk,
            "risk_confidence": round(float(risk_confidence), 2)
        })

    # IMPORTANT: return a plain Python list, not a DataFrame.
    return risk_results


def run_ai_engine(notes):
    """Full pipeline: raw mobile notes -> classified findings -> risk-scored findings."""

    return calculate_risk(process_raw_findings(notes))


def generate_inspection_kpis(risk_results):
    total = len(risk_results)

    critical = high = medium = low = recurring = 0
    risk_scores = []

    for finding in risk_results:
        severity = str(finding.get("severity", "")).upper()

        if severity == "CRITICAL":
            critical += 1
        elif severity == "HIGH":
            high += 1
        elif severity == "MEDIUM":
            medium += 1
        elif severity == "LOW":
            low += 1

        recurring_value = finding.get("recurring")

        if (
            recurring_value is True
            or str(recurring_value).lower() == "true"
            or str(recurring_value) == "1"
            or str(recurring_value).upper() == "YES"
        ):
            recurring += 1

        if finding.get("risk_confidence") is not None:
            risk_scores.append(float(finding["risk_confidence"]))

    if total == 0:
        risk_score = 0
    else:
        severity_points = critical * 100 + high * 75 + medium * 50 + low * 25
        risk_score = (severity_points / (total * 100)) * 100

    if risk_score >= 75:
        risk_level = "CRITICAL"
    elif risk_score >= 50:
        risk_level = "HIGH"
    elif risk_score >= 25:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    compliance_score = max(0, round(100 - risk_score, 2))

    return {
        "total_findings": total,
        "critical_findings": critical,
        "high_findings": high,
        "medium_findings": medium,
        "low_findings": low,
        "recurring_findings": recurring,
        "risk_score": round(risk_score, 2),
        "risk_level": risk_level,
        "compliance_score": compliance_score
    }

def _pdf_text(value):
    """
    Safely convert arbitrary values to text that can be used inside
    a ReportLab Paragraph.
    """
    if value is None:
        return "-"

    return escape(str(value))


def _draw_pdf_header_footer(canvas, doc):
    """
    Adds a professional header/footer to every page.
    """

    canvas.saveState()

    width, height = A4

    # ------------------------------------------------------------
    # HEADER
    # ------------------------------------------------------------

    canvas.setStrokeColor(colors.HexColor("#222222"))
    canvas.setLineWidth(0.6)

    canvas.line(
        15 * mm,
        height - 12 * mm,
        width - 15 * mm,
        height - 12 * mm
    )

    canvas.setFont("Helvetica-Bold", 8)

    canvas.drawString(
        15 * mm,
        height - 9 * mm,
        "MIRA"
    )

    canvas.setFont("Helvetica", 7)

    canvas.drawRightString(
        width - 15 * mm,
        height - 9 * mm,
        "Mine Intelligence and Risk Assessment"
    )

    # ------------------------------------------------------------
    # FOOTER
    # ------------------------------------------------------------

    canvas.line(
        15 * mm,
        12 * mm,
        width - 15 * mm,
        12 * mm
    )

    canvas.setFont("Helvetica", 7)

    canvas.drawString(
        15 * mm,
        8 * mm,
        "Coal Mine Inspection Report"
    )

    canvas.drawCentredString(
        width / 2,
        8 * mm,
        "Generated automatically by MIRA AI Engine"
    )

    canvas.drawRightString(
        width - 15 * mm,
        8 * mm,
        f"Page {doc.page}"
    )

    canvas.restoreState()


def _severity_text(value):
    """
    Normalize severity for PDF display.
    """
    if value is None:
        return "LOW"

    return str(value).upper()


def _risk_level_text(value):
    """
    Normalize risk level for display.
    """
    if value is None:
        return "-"

    return str(value).upper()


def generate_inspection_pdf(
    inspection,
    findings,
    kpis,
    evidence=None
):
    """
    Generates the final approved MIRA Coal Mine Inspection Report.

    This PDF is generated only after:
        mobile submission
            ->
        admin approval
            ->
        AI analysis
            ->
        KPI/risk calculation

    Parameters
    ----------
    inspection : dict
        Mine and inspection metadata.

    findings : list
        AI-generated findings.

    kpis : dict
        Risk and KPI information.

    evidence : list
        Uploaded field evidence including file paths and GPS data.
    """

    evidence = evidence or []
    findings = findings or []
    kpis = kpis or {}

    # ============================================================
    # FILE PATH
    # ============================================================

    report_no = (
        inspection.get("report_no")
        or f"REPORT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    )

    filename = secure_filename(
        f"{report_no}.pdf"
    )

    pdf_path = REPORT_DIR / filename

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # ============================================================
    # DOCUMENT
    # ============================================================

    doc = SimpleDocTemplate(
        str(pdf_path),

        pagesize=A4,

        rightMargin=15 * mm,
        leftMargin=15 * mm,

        topMargin=20 * mm,
        bottomMargin=18 * mm
    )

    # ============================================================
    # STYLES
    # ============================================================

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "MIRATitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=21,
        spaceAfter=2
    )

    subtitle_style = ParagraphStyle(
        "MIRASubtitle",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        spaceAfter=3
    )

    report_title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        spaceBefore=6,
        spaceAfter=10
    )

    section_style = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        spaceBefore=10,
        spaceAfter=5,
        textColor=colors.HexColor("#111111")
    )

    body_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        spaceAfter=3
    )

    small_style = ParagraphStyle(
        "Small",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9,
        textColor=colors.white
    )

    table_body_style = ParagraphStyle(
        "TableBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10
    )

    finding_id_style = ParagraphStyle(
        "FindingID",
        parent=table_body_style,
        fontName="Helvetica-Bold",
        fontSize=7.5
    )

    # ============================================================
    # STORY
    # ============================================================

    story = []

    # ============================================================
    # REPORT HEADER
    # ============================================================

    story.append(
        Paragraph(
            "MIRA",
            title_style
        )
    )

    story.append(
        Paragraph(
            "MINE INTELLIGENCE AND RISK ASSESSMENT",
            subtitle_style
        )
    )

    story.append(
        Paragraph(
            "COAL MINE INSPECTION REPORT",
            report_title_style
        )
    )

    # ============================================================
    # REPORT INFORMATION
    # ============================================================

    inspection_info = [

        [
            Paragraph("<b>Report No.</b>", table_body_style),
            Paragraph(
                _pdf_text(inspection.get("report_no")),
                table_body_style
            ),

            Paragraph("<b>Inspection Date</b>", table_body_style),
            Paragraph(
                _pdf_text(inspection.get("inspection_date")),
                table_body_style
            )
        ],

        [
            Paragraph("<b>Mine</b>", table_body_style),
            Paragraph(
                _pdf_text(inspection.get("mine_name")),
                table_body_style
            ),

            Paragraph("<b>Mine Code</b>", table_body_style),
            Paragraph(
                _pdf_text(inspection.get("mine_code")),
                table_body_style
            )
        ],

        [
            Paragraph("<b>Operator</b>", table_body_style),
            Paragraph(
                _pdf_text(inspection.get("operator")),
                table_body_style
            ),

            Paragraph("<b>Method</b>", table_body_style),
            Paragraph(
                _pdf_text(inspection.get("method")),
                table_body_style
            )
        ],

        [
            Paragraph("<b>State</b>", table_body_style),
            Paragraph(
                _pdf_text(inspection.get("state")),
                table_body_style
            ),

            Paragraph("<b>District</b>", table_body_style),
            Paragraph(
                _pdf_text(inspection.get("district")),
                table_body_style
            )
        ],

        [
            Paragraph("<b>Inspector</b>", table_body_style),
            Paragraph(
                _pdf_text(inspection.get("inspector_name")),
                table_body_style
            ),

            Paragraph("<b>Duration</b>", table_body_style),
            Paragraph(
                _pdf_text(inspection.get("duration")),
                table_body_style
            )
        ]
    ]

    info_table = Table(
        inspection_info,
        colWidths=[
            30 * mm,
            60 * mm,
            30 * mm,
            55 * mm
        ],
        repeatRows=0
    )

    info_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#777777")),

            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eeeeee")),
            ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#eeeeee")),

            ("VALIGN", (0, 0), (-1, -1), "TOP"),

            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),

            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ])
    )

    story.append(info_table)

    # ============================================================
    # LOCATION
    # ============================================================

    latitude = inspection.get("latitude")
    longitude = inspection.get("longitude")

    if latitude is not None or longitude is not None:

        story.append(
            Paragraph(
                "Mine Location",
                section_style
            )
        )

        location_text = (
            f"Latitude: {_pdf_text(latitude)} &nbsp;&nbsp;&nbsp; "
            f"Longitude: {_pdf_text(longitude)}"
        )

        story.append(
            Paragraph(
                location_text,
                body_style
            )
        )

    # ============================================================
    # EXECUTIVE SUMMARY
    # ============================================================

    story.append(
        Paragraph(
            "Executive Summary",
            section_style
        )
    )

    total_findings = kpis.get(
        "total_findings",
        len(findings)
    )

    critical = kpis.get(
        "critical_findings",
        0
    )

    high = kpis.get(
        "high_findings",
        0
    )

    medium = kpis.get(
        "medium_findings",
        0
    )

    low = kpis.get(
        "low_findings",
        0
    )

    recurring = kpis.get(
        "recurring_findings",
        0
    )

    risk_score = kpis.get(
        "risk_score",
        0
    )

    risk_level = kpis.get(
        "risk_level",
        "-"
    )

    compliance_score = kpis.get(
        "compliance_score",
        0
    )

    summary_text = (
        f"The inspection of <b>{_pdf_text(inspection.get('mine_name'))}</b> "
        f"identified <b>{total_findings}</b> AI-assessed observations. "
        f"The assessment recorded <b>{critical}</b> critical, "
        f"<b>{high}</b> high, <b>{medium}</b> medium and "
        f"<b>{low}</b> low severity findings. "
        f"<b>{recurring}</b> finding(s) were identified as recurring. "
        f"The resulting risk score is <b>{risk_score}%</b>, "
        f"with an overall risk level of "
        f"<b>{_pdf_text(risk_level)}</b>."
    )

    story.append(
        Paragraph(
            summary_text,
            body_style
        )
    )

    # ============================================================
    # RISK / KPI SUMMARY
    # ============================================================

    story.append(
        Paragraph(
            "Risk & Compliance Summary",
            section_style
        )
    )

    kpi_data = [
        [
            Paragraph("Metric", table_header_style),
            Paragraph("Value", table_header_style),
            Paragraph("Metric", table_header_style),
            Paragraph("Value", table_header_style)
        ],

        [
            Paragraph("Total Findings", table_body_style),
            Paragraph(str(total_findings), table_body_style),

            Paragraph("Risk Score", table_body_style),
            Paragraph(f"{risk_score}%", table_body_style)
        ],

        [
            Paragraph("Critical", table_body_style),
            Paragraph(str(critical), table_body_style),

            Paragraph("Risk Level", table_body_style),
            Paragraph(
                _pdf_text(_risk_level_text(risk_level)),
                table_body_style
            )
        ],

        [
            Paragraph("High", table_body_style),
            Paragraph(str(high), table_body_style),

            Paragraph("Compliance Score", table_body_style),
            Paragraph(f"{compliance_score}%", table_body_style)
        ],

        [
            Paragraph("Medium", table_body_style),
            Paragraph(str(medium), table_body_style),

            Paragraph("Recurring", table_body_style),
            Paragraph(str(recurring), table_body_style)
        ],

        [
            Paragraph("Low", table_body_style),
            Paragraph(str(low), table_body_style),

            Paragraph("Evidence Items", table_body_style),
            Paragraph(str(len(evidence)), table_body_style)
        ]
    ]

    kpi_table = Table(
        kpi_data,
        colWidths=[
            42 * mm,
            35 * mm,
            58 * mm,
            40 * mm
        ]
    )

    kpi_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#777777")),

            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#222222")),

            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

            ("ALIGN", (1, 1), (1, -1), "CENTER"),
            ("ALIGN", (3, 1), (3, -1), "CENTER"),

            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),

            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5)
        ])
    )

    story.append(kpi_table)

    # ============================================================
    # INSPECTOR REMARKS
    # ============================================================

    story.append(
        Paragraph(
            "Inspector Remarks",
            section_style
        )
    )

    remarks = inspection.get("remarks")

    story.append(
        Paragraph(
            _pdf_text(
                remarks or
                "No inspector remarks were provided."
            ),
            body_style
        )
    )

    # ============================================================
    # AI FINDINGS
    # ============================================================

    story.append(
        Paragraph(
            "AI-Assessed Findings",
            section_style
        )
    )

    if findings:

        finding_rows = [
            [
                Paragraph("ID", table_header_style),
                Paragraph("Finding / Observation", table_header_style),
                Paragraph("Category", table_header_style),
                Paragraph("Issue", table_header_style),
                Paragraph("Severity", table_header_style),
                Paragraph("Recurring", table_header_style)
            ]
        ]

        for finding in findings:

            finding_id = (
                finding.get("finding_id")
                or "-"
            )

            finding_text = (
                finding.get("finding_text")
                or "No description available."
            )

            category = (
                finding.get("category")
                or "-"
            )

            issue = (
                finding.get("issue")
                or "-"
            )

            severity = _severity_text(
                finding.get("severity")
            )

            recurring_value = finding.get(
                "recurring",
                False
            )

            recurring_text = (
                "YES"
                if str(recurring_value).lower()
                in ["true", "yes", "1"]
                else "NO"
            )

            finding_rows.append(
                [
                    Paragraph(
                        _pdf_text(finding_id),
                        finding_id_style
                    ),

                    Paragraph(
                        _pdf_text(finding_text),
                        table_body_style
                    ),

                    Paragraph(
                        _pdf_text(category),
                        table_body_style
                    ),

                    Paragraph(
                        _pdf_text(issue),
                        table_body_style
                    ),

                    Paragraph(
                        _pdf_text(severity),
                        table_body_style
                    ),

                    Paragraph(
                        recurring_text,
                        table_body_style
                    )
                ]
            )

        findings_table = Table(
            finding_rows,
            colWidths=[
                12 * mm,
                67 * mm,
                27 * mm,
                25 * mm,
                20 * mm,
                24 * mm
            ],
            repeatRows=1
        )

        findings_table.setStyle(
            TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#777777")),

                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#222222")),

                ("VALIGN", (0, 0), (-1, -1), "TOP"),

                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),

                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ])
        )

        story.append(
            findings_table
        )

    else:

        story.append(
            Paragraph(
                "No AI findings were generated.",
                body_style
            )
        )

    # ============================================================
    # FIELD EVIDENCE
    # ============================================================

    story.append(
        Paragraph(
            "Field Evidence",
            section_style
        )
    )

    if evidence:

        for index, item in enumerate(
            evidence,
            start=1
        ):

            if not isinstance(item, dict):
                continue

            evidence_type = (
                item.get("type")
                or item.get("evidence_type")
                or "Photo"
            )

            description = (
                item.get("description")
                or "Field evidence"
            )

            latitude = item.get(
                "latitude"
            )

            longitude = item.get(
                "longitude"
            )

            caption = (
                f"<b>Evidence {index} — "
                f"{_pdf_text(str(evidence_type).title())}</b>"
            )

            story.append(
                Paragraph(
                    caption,
                    body_style
                )
            )

            story.append(
                Paragraph(
                    _pdf_text(description),
                    small_style
                )
            )

            if (
                latitude is not None
                and longitude is not None
            ):

                story.append(
                    Paragraph(
                        f"GPS: {_pdf_text(latitude)}, "
                        f"{_pdf_text(longitude)}",
                        small_style
                    )
                )

            file_path = (
                item.get("file_path")
                or item.get("uri")
            )

            # ----------------------------------------------------
            # EMBED IMAGE
            # ----------------------------------------------------

            if (
                file_path
                and os.path.isfile(file_path)
            ):

                try:

                    aspect = _image_aspect_ratio(
                        file_path
                    )

                    image_width = 80 * mm

                    image_height = (
                        image_width * aspect
                    )

                    # Prevent extremely tall phone images
                    if image_height > 90 * mm:

                        image_height = 90 * mm

                    image = Image(
                        file_path,
                        width=image_width,
                        height=image_height
                    )

                    story.append(
                        image
                    )

                except Exception:

                    app.logger.exception(
                        "Unable to embed evidence image: %s",
                        file_path
                    )

                    story.append(
                        Paragraph(
                            "[Evidence image could not be embedded]",
                            small_style
                        )
                    )

            elif file_path:

                story.append(
                    Paragraph(
                        f"Evidence file: "
                        f"{_pdf_text(file_path)}",
                        small_style
                    )
                )

            story.append(
                Spacer(1, 6)
            )

    else:

        story.append(
            Paragraph(
                "No field evidence was attached to this inspection.",
                body_style
            )
        )

    # ============================================================
    # CONCLUSION
    # ============================================================

    story.append(
        Paragraph(
            "Inspection Conclusion",
            section_style
        )
    )

    conclusion_text = (
        f"The inspection assessment resulted in an overall risk "
        f"score of <b>{risk_score}%</b> and a risk level of "
        f"<b>{_pdf_text(risk_level)}</b>. "
        f"Management attention should be directed toward the "
        f"identified critical and high-severity observations, "
        f"particularly recurring deficiencies requiring corrective "
        f"action and verification."
    )

    story.append(
        Paragraph(
            conclusion_text,
            body_style
        )
    )

    # ============================================================
    # RECOMMENDATION
    # ============================================================

    story.append(
        Paragraph(
            "Recommended Action",
            section_style
        )
    )

    recommendation_text = (
        "Corrective actions should be initiated for all identified "
        "non-compliances. Critical and high-risk observations should "
        "receive priority treatment, with management verification "
        "and documented closure. Recurring observations should be "
        "reviewed to determine the underlying cause and prevent "
        "repetition."
    )

    story.append(
        Paragraph(
            recommendation_text,
            body_style
        )
    )

    # ============================================================
    # SIGN-OFF
    # ============================================================

    story.append(
        Spacer(
            1,
            15 * mm
        )
    )

    signoff_table = Table(
        [
            [
                Paragraph(
                    "<b>Prepared By</b>",
                    table_body_style
                ),
                Paragraph(
                    "<b>Reviewed By</b>",
                    table_body_style
                )
            ],

            [
                Paragraph(
                    _pdf_text(
                        inspection.get(
                            "inspector_name"
                        )
                    ),
                    table_body_style
                ),

                Paragraph(
                    "MIRA Administrator",
                    table_body_style
                )
            ]
        ],
        colWidths=[
            87.5 * mm,
            87.5 * mm
        ]
    )

    signoff_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#777777")),

            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),

            ("VALIGN", (0, 0), (-1, -1), "TOP"),

            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),

            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6)
        ])
    )

    story.append(
        signoff_table
    )

    # ============================================================
    # BUILD PDF
    # ============================================================

    doc.build(
        story,
        onFirstPage=_draw_pdf_header_footer,
        onLaterPages=_draw_pdf_header_footer
    )

    app.logger.info(
        "Final inspection PDF generated: %s",
        pdf_path
    )

    return str(pdf_path)

def process_inspection_approval(conn, cursor, raw_id, reviewer_id):
    """
    Approves a raw mobile inspection and converts it into a completed
    MIRA inspection.

    Lifecycle:

        PENDING_APPROVAL
                |
                v
           PROCESSING
                |
        +-------+--------+
        |                |
        v                v
    COMPLETED          FAILED

    The original inspection_raw record is retained as an audit trail.

    Processing steps:
        1. Load raw inspection
        2. Validate status
        3. Mark PROCESSING
        4. Load notes/evidence
        5. Run MIRA AI engine
        6. Generate KPIs
        7. Create final inspection
        8. Store AI findings
        9. Store evidence
        10. Store risk score
        11. Store KPIs
        12. Update mine risk/GIS data
        13. Generate final inspection PDF
        14. Save PDF path
        15. Mark raw inspection COMPLETED
    """

    # ============================================================
    # STEP 1 — LOAD RAW INSPECTION
    # ============================================================

    cursor.execute(
        """
        SELECT
            r.*,

            u.name AS inspector_name,
            u.role AS inspector_role,

            m.name AS mine_name,
            m.code AS mine_code,
            m.operator AS operator,
            m.state AS state,
            m.district AS district,
            m.status AS mine_status,
            m.method AS method,
            m.latitude AS latitude,
            m.longitude AS longitude

        FROM inspection_raw r

        INNER JOIN users u
            ON r.inspector_id = u.id

        INNER JOIN mines m
            ON r.mine_id = m.id

        WHERE r.id = ?

        LIMIT 1
        """,
        (raw_id,)
    )

    raw = cursor.fetchone()

    if not raw:
        raise ApprovalError(
            "Raw inspection not found.",
            404
        )

    # ============================================================
    # STEP 2 — VALIDATE STATUS
    # ============================================================

    if raw["status"] != "PENDING_APPROVAL":
        raise ApprovalError(
            f"Inspection is already {raw['status']}.",
            409
        )

    # ============================================================
    # STEP 3 — MARK AS PROCESSING
    # ============================================================

    cursor.execute(
        """
        UPDATE inspection_raw
        SET
            status = 'PROCESSING',
            reviewed_by = ?,
            reviewed_at = CURRENT_TIMESTAMP,
            error_message = NULL
        WHERE id = ?
          AND status = 'PENDING_APPROVAL'
        """,
        (
            reviewer_id,
            raw_id
        )
    )

    if cursor.rowcount == 0:
        conn.rollback()

        raise ApprovalError(
            "Inspection could not be moved to PROCESSING. "
            "It may already have been processed.",
            409
        )

    # Commit this state separately.
    #
    # This is intentional. If the AI engine crashes afterwards,
    # the database still knows that this inspection was being processed.
    conn.commit()

    try:

        # ========================================================
        # STEP 4 — LOAD MOBILE SUBMISSION DATA
        # ========================================================

        notes = safe_json_load(
            raw["notes_json"],
            []
        )

        evidence = safe_json_load(
            raw["evidence_json"],
            []
        )

        # Make sure malformed JSON does not break later loops.
        if not isinstance(notes, list):
            notes = []

        if not isinstance(evidence, list):
            evidence = []

        app.logger.info(
            "Loaded raw inspection %s: %s notes, %s evidence items",
            raw_id,
            len(notes),
            len(evidence)
        )

        # ========================================================
        # STEP 5 — RUN MIRA AI ENGINE
        # ========================================================

        app.logger.info(
            "Starting MIRA AI engine for raw inspection %s",
            raw_id
        )

        risk_results = run_ai_engine(notes)

        if risk_results is None:
            risk_results = []

        if not isinstance(risk_results, list):
            raise ValueError(
                "MIRA AI engine returned an invalid result format."
            )

        app.logger.info(
            "MIRA AI engine completed for raw inspection %s: "
            "%s findings generated",
            raw_id,
            len(risk_results)
        )

        # ========================================================
        # STEP 6 — GENERATE KPIs
        # ========================================================

        kpis = generate_inspection_kpis(
            risk_results
        )

        if not isinstance(kpis, dict):
            raise ValueError(
                "KPI generator returned an invalid result."
            )

        # ========================================================
        # STEP 7 — CREATE FINAL INSPECTION
        # ========================================================
        # STEP 5 — create final inspection
        cursor.execute(
            """
            INSERT INTO inspections
                (
                    report_no,
                    mine_id,
                    inspector_id,
                    inspection_date,
                    duration,
                    remarks,
                    status,
                    pdf_path,
                    ai_status,
                    processed_at
                )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                raw["report_no"],
                raw["mine_id"],
                raw["inspector_id"],
                raw["inspection_date"],
                raw["duration"],
                raw["remarks"],
                "analysed",
                None,
                "COMPLETED"
            )
        )

        inspection_id = cursor.lastrowid

        if not inspection_id:
            raise ValueError(
                "Unable to create final inspection record."
            )

        app.logger.info(
            "Created final inspection %s from raw inspection %s",
            inspection_id,
            raw_id
        )

        # ========================================================
        # STEP 8 — INSERT AI FINDINGS
        # ========================================================

        for finding in risk_results:

            # Defensive defaults.
            finding_id = finding.get(
                "finding_id",
                f"F-{cursor.lastrowid or 'UNKNOWN'}"
            )

            finding_text = finding.get(
                "finding_text",
                ""
            )

            issue = finding.get(
                "issue",
                "General"
            )

            category = finding.get(
                "category",
                "Safety"
            )

            severity = finding.get(
                "severity",
                "LOW"
            )

            recurring = (
                1
                if str(
                    finding.get("recurring", False)
                ).lower()
                in ["true", "yes", "1"]
                else 0
            )

            cursor.execute(
                """
                INSERT INTO inspection_findings
                    (
                        inspection_id,
                        issue,
                        category,
                        severity,
                        recurring,
                        finding_code,
                        note
                    )
                VALUES
                    (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    inspection_id,
                    issue,
                    category,
                    severity,
                    recurring,
                    finding_id,
                    finding_text
                )
            )

            finding_db_id = cursor.lastrowid

            # Preserve the original finding text separately.
            cursor.execute(
                """
                INSERT INTO finding_texts
                    (finding_id, text)
                VALUES
                    (?, ?)
                """,
                (
                    finding_db_id,
                    finding_text
                )
            )

        # ========================================================
        # STEP 9 — INSERT FIELD EVIDENCE
        # ========================================================

        for item in evidence:

            if not isinstance(item, dict):
                continue

            file_path = (
                item.get("file_path")
                or item.get("uri")
            )

            latitude = item.get(
                "latitude"
            )

            longitude = item.get(
                "longitude"
            )

            evidence_type = (
                item.get("type")
                or item.get("evidence_type")
                or "photo"
            )

            description = item.get(
                "description"
            )

            cursor.execute(
                """
                INSERT INTO inspection_evidence
                    (
                        inspection_id,
                        finding_id,
                        file_path,
                        latitude,
                        longitude,
                        evidence_type,
                        description
                    )
                VALUES
                    (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    inspection_id,
                    None,
                    file_path,
                    latitude,
                    longitude,
                    evidence_type,
                    description
                )
            )

        # ========================================================
        # STEP 10 — STORE RISK SCORE
        # ========================================================

        risk_factors = {
            "total_findings": kpis.get(
                "total_findings",
                0
            ),

            "critical": kpis.get(
                "critical_findings",
                0
            ),

            "high": kpis.get(
                "high_findings",
                0
            ),

            "medium": kpis.get(
                "medium_findings",
                0
            ),

            "low": kpis.get(
                "low_findings",
                0
            ),

            "recurring": kpis.get(
                "recurring_findings",
                0
            )
        }

        # STEP 8 — store risk score
        cursor.execute(
            """
            INSERT INTO risk_scores
                (
                    inspection_id,
                    mine_id,
                    risk_score,
                    risk_level,
                    risk_factors,
                    model_version
                )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                inspection_id,
                raw["mine_id"],
                kpis["risk_score"],
                kpis["risk_level"],
                json.dumps({
                    "total_findings": kpis["total_findings"],
                    "critical": kpis["critical_findings"],
                    "high": kpis["high_findings"],
                    "medium": kpis["medium_findings"],
                    "low": kpis["low_findings"],
                    "recurring": kpis["recurring_findings"]
                }),
                "MIRA-v1"
            )
        )

        # ========================================================
        # STEP 11 — STORE INSPECTION KPIs
        # ========================================================

        # STEP 9 — store inspection KPIs
        cursor.execute(
            """
            INSERT INTO inspection_kpis
                (
                    inspection_id,
                    total_findings,
                    low_findings,
                    medium_findings,
                    high_findings,
                    critical_findings,
                    overall_risk_score,
                    overall_risk_level,
                    recurring_findings
                )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                inspection_id,
                kpis["total_findings"],
                kpis["low_findings"],
                kpis["medium_findings"],
                kpis["high_findings"],
                kpis["critical_findings"],
                kpis["risk_score"],
                kpis["risk_level"],
                kpis["recurring_findings"]
            )
        )
        cursor.execute(
            """
            UPDATE inspections
            SET
                risk_score = ?,
                risk_level = ?,
                ai_status = 'COMPLETED',
                processed_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                kpis["risk_score"],
                kpis["risk_level"],
                inspection_id
            )
        )
        # ========================================================
        # STEP 12 — UPDATE MINE RISK / GIS
        # ========================================================
        # STEP 11 — update mine GIS / risk
        cursor.execute(
            """
            UPDATE mines
            SET
                risk_score = ?,
                risk_level = ?
            WHERE id = ?
            """,
            (
                kpis["risk_score"],
                kpis["risk_level"],
                raw["mine_id"]
            )
        )
        # ========================================================
        # STEP 13 — PREPARE FINAL PDF DATA
        # ========================================================

        inspection_for_pdf = {
            "report_no": raw["report_no"],
            "inspection_date": raw["inspection_date"],

            "mine_name": raw["mine_name"],
            "mine_code": raw["mine_code"],
            "operator": raw.get("operator"),

            "state": raw["state"],
            "district": raw["district"],

            "method": raw.get("method"),
            "mine_status": raw.get("mine_status"),

            "latitude": raw.get("latitude"),
            "longitude": raw.get("longitude"),

            "inspector_name": raw["inspector_name"],
            "duration": raw["duration"],
            "remarks": raw["remarks"]
        }

        # ========================================================
        # STEP 14 — GENERATE FINAL PDF
        # ========================================================

        app.logger.info(
            "Generating final inspection PDF for inspection %s",
            inspection_id
        )

        pdf_path = generate_inspection_pdf(
            inspection_for_pdf,
            risk_results,
            kpis,
            evidence
        )
        if not pdf_path:
            raise ValueError(
                "Final inspection PDF generation returned no path."
            )

        # ========================================================
        # STEP 15 — SAVE PDF PATH
        # ========================================================

        cursor.execute(
            """
            UPDATE inspections
            SET pdf_path = ?
            WHERE id = ?
            """,
            (pdf_path, inspection_id)
        )

        # ========================================================
        # STEP 16 — MARK RAW RECORD COMPLETED
        # ========================================================
        cursor.execute(
            """
            UPDATE inspection_raw
            SET
                status = 'COMPLETED',
                error_message = NULL
            WHERE id = ?
              AND status = 'PROCESSING'
            """,
            (
                raw_id,
            )
        )
        if cursor.rowcount == 0:
            raise ValueError(
                "Unable to mark raw inspection as COMPLETED."
            )
        cursor.execute(
            """
            UPDATE inspections
            SET
                ai_status = 'COMPLETED',
                processed_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (inspection_id,)
        )
        # ========================================================
        # STEP 17 — COMMIT EVERYTHING
        # ========================================================
        conn.commit()
        app.logger.info(
            "Inspection approval successful: "
            "raw=%s -> inspection=%s",
            raw_id,
            inspection_id
        )

        # ========================================================
        # RETURN RESULT
        # ========================================================

        return {
            "raw_inspection_id": raw_id,
            "inspection_id": inspection_id,
            "status": "COMPLETED",
            "risk": {
                "score": kpis["risk_score"],
                "level": kpis["risk_level"]
            },
            "kpis": kpis,
            "findings": risk_results,
            "evidence_count": len(evidence),
            "pdf_path": pdf_path
        }

    # ============================================================
    # FAILURE HANDLING
    # ============================================================

    except Exception as e:
        # Roll back all inspection/risk/KPI inserts.
        conn.rollback()
        app.logger.exception(
            "Inspection approval failed for raw inspection %s",
            raw_id
        )

        # The PROCESSING transition was committed before entering
        # the try block, therefore this update survives the rollback.
        try:
            cursor.execute(
                """
                UPDATE inspection_raw
                SET
                    status = 'FAILED',
                    error_message = ?
                WHERE id = ?
                """,
                (
                    str(e)[:2000],
                    raw_id
                )
            )
            conn.commit()
        except mariadb.Error:
            app.logger.exception(
                "Unable to record FAILED status "
                "for raw inspection %s",
                raw_id
            )
        raise

def reject_raw_inspection_record(conn, cursor, raw_id, reason):
    """
    Marks a PENDING inspection_raw record REJECTED. Shared by the JSON API
    and the /validate UI route so "reject" only has one implementation.
    Raises ApprovalError if the record is missing or already processed.
    """

    cursor.execute(
        """
        UPDATE inspection_raw
        SET status = 'REJECTED', rejection_reason = ?
        WHERE id = ? AND status = 'PENDING_APPROVAL'
        """,
        (reason, raw_id)
    )

    if cursor.rowcount == 0:
        conn.rollback()
        raise ApprovalError("Inspection not found or already processed.", 404)

    conn.commit()

    app.logger.info("Raw inspection %s rejected: %s", raw_id, reason)

    return {"raw_inspection_id": raw_id, "status": "REJECTED", "reason": reason}


# ============================================================
# ADMIN — INSPECTION APPROVAL QUEUE (JSON API)
# ============================================================

@app.route("/api/admin/inspection-queue", methods=["GET"])
@jwt_required()
def inspection_approval_queue():
    claims = get_jwt()

    if claims.get("role") != "admin":
        return jsonify({"success": False, "message": "Administrator access required."}), 403

    conn = get_db_connection()

    if conn is None:
        return jsonify({"success": False, "message": "Database connection failed."}), 500

    cursor = None

    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                r.id, r.report_no, r.inspection_date, r.duration, r.remarks, r.status,
                r.created_at, r.raw_pdf_path,
                u.id AS inspector_id, u.name AS inspector_name,
                m.id AS mine_id, m.name AS mine_name, m.code AS mine_code, m.state, m.district
            FROM inspection_raw r
            INNER JOIN users u ON r.inspector_id = u.id
            INNER JOIN mines m ON r.mine_id = m.id
            WHERE r.status = 'PENDING_APPROVAL'
            ORDER BY r.created_at DESC
            """
        )

        rows = cursor.fetchall()

        result = [
            {
                "id": row["id"],
                "report_no": row["report_no"],
                "inspection_date": row["inspection_date"],
                "duration": row["duration"],
                "remarks": row["remarks"],
                "status": row["status"],
                "created_at": row["created_at"],
                "raw_pdf_filename": Path(row["raw_pdf_path"]).name if row["raw_pdf_path"] else None,
                "inspector": {"id": row["inspector_id"], "name": row["inspector_name"]},
                "mine": {
                    "id": row["mine_id"],
                    "name": row["mine_name"],
                    "code": row["mine_code"],
                    "state": row["state"],
                    "district": row["district"]
                }
            }
            for row in rows
        ]

        return jsonify({"success": True, "count": len(result), "inspections": result})

    except mariadb.Error:
        app.logger.exception("Approval queue error")
        return jsonify({"success": False, "message": "Unable to load approval queue."}), 500

    finally:
        if cursor:
            cursor.close()
        conn.close()


@app.route("/api/admin/inspection-queue/<int:raw_id>", methods=["GET"])
@jwt_required()
def get_raw_inspection(raw_id):
    claims = get_jwt()

    if claims.get("role") != "admin":
        return jsonify({"success": False, "message": "Administrator access required."}), 403

    conn = get_db_connection()

    if conn is None:
        return jsonify({"success": False, "message": "Database connection failed."}), 500

    cursor = None

    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT r.*, u.name AS inspector_name,
                   m.name AS mine_name, m.code AS mine_code, m.state, m.district
            FROM inspection_raw r
            INNER JOIN users u ON r.inspector_id = u.id
            INNER JOIN mines m ON r.mine_id = m.id
            WHERE r.id = ?
            LIMIT 1
            """,
            (raw_id,)
        )

        row = cursor.fetchone()

        if not row:
            return jsonify({"success": False, "message": "Inspection not found."}), 404

        return jsonify({
            "success": True,
            "inspection": {
                "id": row["id"],
                "report_no": row["report_no"],
                "inspection_date": row["inspection_date"],
                "duration": row["duration"],
                "remarks": row["remarks"],
                "status": row["status"],
                "inspector": {"id": row["inspector_id"], "name": row["inspector_name"]},
                "mine": {
                    "id": row["mine_id"],
                    "name": row["mine_name"],
                    "code": row["mine_code"],
                    "state": row["state"],
                    "district": row["district"]
                },
                "notes": safe_json_load(row["notes_json"]),
                "evidence": safe_json_load(row["evidence_json"]),
                "raw_pdf_filename": Path(row["raw_pdf_path"]).name if row.get("raw_pdf_path") else None
            }
        })

    except mariadb.Error:
        app.logger.exception("Unable to retrieve raw inspection")
        return jsonify({"success": False, "message": "Database error."}), 500

    finally:
        if cursor:
            cursor.close()
        conn.close()


@app.route("/api/admin/inspection-queue/<int:raw_id>/approve", methods=["POST"])
@jwt_required()
def approve_raw_inspection(raw_id):
    claims = get_jwt()

    if claims.get("role") != "admin":
        return jsonify({"success": False, "message": "Administrator access required."}), 403

    conn = get_db_connection()

    if conn is None:
        return jsonify({"success": False, "message": "Database connection failed."}), 500

    cursor = None

    try:
        cursor = conn.cursor(dictionary=True)

        result = process_inspection_approval(conn, cursor, raw_id, int(get_jwt_identity()))

        return jsonify({
            "success": True,
            "message": "Inspection approved and processed successfully.",
            **result
        }), 201

    except ApprovalError as e:
        if conn:
            conn.rollback()
        return jsonify({"success": False, "message": e.message}), e.status_code

    except Exception as e:
        if conn:
            conn.rollback()
        app.logger.exception("Inspection approval pipeline failed")
        return jsonify({
            "success": False,
            "message": "Inspection processing failed.",
            "error": str(e)
        }), 500

    finally:
        if cursor:
            cursor.close()
        conn.close()


@app.route("/api/admin/inspection-queue/<int:raw_id>/reject", methods=["POST"])
@jwt_required()
def reject_raw_inspection(raw_id):
    claims = get_jwt()

    if claims.get("role") != "admin":
        return jsonify({"success": False, "message": "Administrator access required."}), 403

    data = request.get_json(silent=True) or {}
    reason = data.get("reason", "Rejected by administrator.")

    conn = get_db_connection()

    if conn is None:
        return jsonify({"success": False, "message": "Database connection failed."}), 500

    cursor = None

    try:
        cursor = conn.cursor()

        result = reject_raw_inspection_record(conn, cursor, raw_id, reason)

        return jsonify({"success": True, "message": "Inspection rejected.", **result})

    except ApprovalError as e:
        return jsonify({"success": False, "message": e.message}), e.status_code

    except mariadb.Error:
        if conn:
            conn.rollback()
        app.logger.exception("Inspection rejection failed")
        return jsonify({"success": False, "message": "Unable to reject inspection."}), 500

    finally:
        if cursor:
            cursor.close()
        conn.close()


@app.route("/api/admin/inspection/<int:inspection_id>/regenerate", methods=["POST"])
@jwt_required()
def regenerate_inspection(inspection_id):
    claims = get_jwt()

    if claims.get("role") != "admin":
        return jsonify({"success": False, "message": "Administrator access required."}), 403

    conn = get_db_connection()

    if conn is None:
        return jsonify({"success": False, "message": "Database connection failed."}), 500

    cursor = None

    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id, remarks FROM inspections WHERE id = ? LIMIT 1", (inspection_id,))
        inspection = cursor.fetchone()

        if not inspection:
            return jsonify({"success": False, "message": "Inspection not found."}), 404

        cursor.execute(
            "SELECT note FROM inspection_findings WHERE inspection_id = ? ORDER BY id",
            (inspection_id,)
        )

        rows = cursor.fetchall()
        notes = [{"content": row["note"]} for row in rows if row["note"]]

        risk_results = run_ai_engine(notes)
        kpis = generate_inspection_kpis(risk_results)

        return jsonify({
            "success": True,
            "inspection_id": inspection_id,
            "kpis": kpis,
            "findings": risk_results
        })

    except Exception as e:
        app.logger.exception("AI regeneration failed")
        return jsonify({"success": False, "message": "AI regeneration failed.", "error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        conn.close()


@app.route("/api/v1/inspections/<int:inspection_id>/kpi", methods=["GET"])
@jwt_required()
def inspection_kpi(inspection_id):
    conn = get_db_connection()

    if conn is None:
        return jsonify({"success": False, "message": "Database connection failed."}), 500

    cursor = None

    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM inspection_kpis WHERE inspection_id = ? LIMIT 1",
            (inspection_id,)
        )

        kpi = cursor.fetchone()

        if not kpi:
            return jsonify({"success": False, "message": "KPI not available."}), 404

        return jsonify({"success": True, "kpi": kpi})

    except mariadb.Error:
        app.logger.exception("KPI retrieval error")
        return jsonify({"success": False, "message": "Unable to retrieve KPI."}), 500

    finally:
        if cursor:
            cursor.close()
        conn.close()


# ============================================================
# ADMIN — VALIDATION QUEUE (HTML UI)
# ============================================================

@app.route("/inspections/validate")
@jwt_required()
def validation_queue():
    claims = get_jwt()

    if claims.get("role") != "admin":
        flash("Administrator access required.", "danger")
        return redirect(url_for("dashboard"))

    conn = get_db_connection()

    if conn is None:
        abort(500)

    cursor = None

    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                r.id, r.report_no, r.mine_id, r.inspector_id, r.inspection_date,
                r.duration, r.remarks, r.status, r.created_at,
                m.name AS mine_name, m.code AS mine_code,
                u.name AS inspector_name
            FROM inspection_raw r
            LEFT JOIN mines m ON r.mine_id = m.id
            LEFT JOIN users u ON r.inspector_id = u.id
            WHERE r.status = 'PENDING_APPROVAL'
            ORDER BY r.created_at DESC
        """)

        raw_inspections = cursor.fetchall()

        return render_template("inspections/validate.html", inspections=raw_inspections)

    except mariadb.Error:
        app.logger.exception("Validation queue error")
        abort(500)

    finally:
        if cursor:
            cursor.close()
        conn.close()


@app.route("/inspections/validate/<int:raw_id>")
@jwt_required()
def validate_inspection(raw_id):
    claims = get_jwt()

    if claims.get("role") != "admin":
        flash("Administrator access required.", "danger")
        return redirect(url_for("dashboard"))

    conn = get_db_connection()

    if conn is None:
        abort(500)

    cursor = None

    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT r.*, m.name AS mine_name, m.code AS mine_code, u.name AS inspector_name
            FROM inspection_raw r
            LEFT JOIN mines m ON r.mine_id = m.id
            LEFT JOIN users u ON r.inspector_id = u.id
            WHERE r.id = ?
            LIMIT 1
        """, (raw_id,))

        raw = cursor.fetchone()

        if not raw:
            abort(404)

        notes = safe_json_load(raw.get("notes_json"), [])
        evidence = safe_json_load(raw.get("evidence_json"), [])

        raw_pdf_filename = (
            Path(raw["raw_pdf_path"]).name if raw.get("raw_pdf_path") else None
        )

        return render_template(
            "inspections/validate.html",
            inspection=raw,
            notes=notes,
            evidence=evidence,
            raw_pdf_filename=raw_pdf_filename
        )

    except mariadb.Error:
        app.logger.exception("Inspection validation error")
        abort(500)

    finally:
        if cursor:
            cursor.close()
        conn.close()


@app.route("/inspections/validate/<int:raw_id>/approve", methods=["POST"])
@jwt_required()
def approve_inspection(raw_id):
    """
    Approve -> AI Engine -> Findings/Risk/KPI -> Generate PDF -> inspections
    (which then feeds Dashboard / GIS / Risk). Shares process_inspection_approval
    with /api/admin/inspection-queue/<id>/approve so the two entry points
    never drift out of sync.
    """

    claims = get_jwt()

    if claims.get("role") != "admin":
        if wants_json():
            return jsonify({"success": False, "message": "Administrator access required."}), 403
        flash("Administrator access required.", "danger")
        return redirect(url_for("dashboard"))

    conn = get_db_connection()

    if conn is None:
        if wants_json():
            return jsonify({"success": False, "message": "Database connection failed."}), 500
        flash("Database connection failed. Please try again later.", "danger")
        return redirect(url_for("validation_queue"))

    cursor = None

    try:
        cursor = conn.cursor(dictionary=True)

        result = process_inspection_approval(conn, cursor, raw_id, int(get_jwt_identity()))

        if wants_json():
            return jsonify({
                "success": True,
                "message": "Inspection approved and processed successfully.",
                **result
            })

        flash(
            f"Inspection {result['raw_inspection_id']} approved -> "
            f"report {result['inspection_id']} generated (risk: {result['risk']['level']}).",
            "success"
        )
        return redirect(url_for("dashboard"))

    except ApprovalError as e:
        if conn:
            conn.rollback()

        if wants_json():
            return jsonify({"success": False, "message": e.message}), e.status_code

        flash(e.message, "danger")
        return redirect(url_for("validation_queue"))

    except Exception as e:
        if conn:
            conn.rollback()
        app.logger.exception("Inspection approval failed")

        if wants_json():
            return jsonify({
                "success": False,
                "message": "Inspection processing failed.",
                "error": str(e)
            }), 500

        flash("Inspection processing failed. Please try again.", "danger")
        return redirect(url_for("validate_inspection", raw_id=raw_id))

    finally:
        if cursor:
            cursor.close()
        conn.close()


@app.route("/inspections/validate/<int:raw_id>/reject", methods=["POST"])
@jwt_required()
def reject_inspection(raw_id):
    """
    Reject -> rejected/removed. Mirrors approve_inspection's dual response
    style and shares reject_raw_inspection_record with the JSON API route.
    """

    claims = get_jwt()

    if claims.get("role") != "admin":
        if wants_json():
            return jsonify({"success": False, "message": "Administrator access required."}), 403
        flash("Administrator access required.", "danger")
        return redirect(url_for("dashboard"))

    reason = (
        request.form.get("reason")
        or (request.get_json(silent=True) or {}).get("reason")
        or "Rejected by administrator."
    )

    conn = get_db_connection()

    if conn is None:
        if wants_json():
            return jsonify({"success": False, "message": "Database connection failed."}), 500
        flash("Database connection failed. Please try again later.", "danger")
        return redirect(url_for("validation_queue"))

    cursor = None

    try:
        cursor = conn.cursor()

        result = reject_raw_inspection_record(conn, cursor, raw_id, reason)

        if wants_json():
            return jsonify({"success": True, "message": "Inspection rejected.", **result})

        flash(f"Inspection {raw_id} rejected: {reason}", "warning")
        return redirect(url_for("validation_queue"))

    except ApprovalError as e:
        if wants_json():
            return jsonify({"success": False, "message": e.message}), e.status_code
        flash(e.message, "danger")
        return redirect(url_for("validation_queue"))

    except mariadb.Error:
        if conn:
            conn.rollback()
        app.logger.exception("Inspection rejection failed")

        if wants_json():
            return jsonify({"success": False, "message": "Unable to reject inspection."}), 500
        flash("Unable to reject inspection. Please try again.", "danger")
        return redirect(url_for("validation_queue"))

    finally:
        if cursor:
            cursor.close()
        conn.close()


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/")
@jwt_required()
def dashboard():
    conn = get_db_connection()

    if conn is None:
        return "Database connection failed", 500

    cursor = None

    try:
        cursor = conn.cursor(dictionary=True)

        # 1. Main dashboard KPIs (v_dashboard_kpis)
        cursor.execute("SELECT * FROM v_dashboard_kpis")
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

        # 2. Risk distribution
        cursor.execute("""
            SELECT risk_level, COUNT(*) AS total
            FROM mines
            WHERE status = 'Active'
            GROUP BY risk_level
        """)

        risk_distribution = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}

        for row in cursor.fetchall():
            level = row["risk_level"]
            if level in risk_distribution:
                risk_distribution[level] = row["total"]

        # 3. High / critical risk mines (v_high_risk_mines)
        cursor.execute("SELECT * FROM v_high_risk_mines LIMIT 10")
        high_risk_mines_data = cursor.fetchall()

        # 4. Open alerts (v_open_alerts)
        cursor.execute("SELECT * FROM v_open_alerts LIMIT 10")
        alerts_data = cursor.fetchall()

        # 5. Recent inspections (v_recent_inspections)
        cursor.execute("SELECT * FROM v_recent_inspections LIMIT 10")
        recent_inspections = cursor.fetchall()

        # 6. Mines by location (v_mines_by_location)
        cursor.execute("SELECT * FROM v_mines_by_location")
        mines_by_location = cursor.fetchall()

        # 7. Overdue actions (v_overdue_actions)
        cursor.execute("SELECT * FROM v_overdue_actions LIMIT 10")
        overdue_actions = cursor.fetchall()

        return render_template(
            "dashboard.html",
            kpis=kpis,
            low_risk_mines=risk_distribution["LOW"],
            medium_risk_mines=risk_distribution["MEDIUM"],
            high_risk_mines=risk_distribution["HIGH"],
            critical_risk_mines=risk_distribution["CRITICAL"],
            high_risk_mines_data=high_risk_mines_data,
            alerts=alerts_data,
            recent_inspections=recent_inspections,
            mines_by_location=mines_by_location,
            overdue_actions=overdue_actions
        )

    except mariadb.Error:
        app.logger.exception("Dashboard database error")
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

        cursor.execute("""
            SELECT
                id, name, code, operator, state, district, status, method,
                risk_score, risk_level, latitude, longitude,
                region_id, region_code, region_name, region_level
            FROM v_mines_gis
            ORDER BY id DESC
        """)

        mines_data = cursor.fetchall()

        return render_template("mines/index.html", mines=mines_data)

    except mariadb.Error:
        app.logger.exception("Error fetching mines")
        return "Unable to load mines", 500

    finally:
        if cursor:
            cursor.close()
        conn.close()


@app.route("/mines/<int:mine_id>")
@jwt_required()
def mine_detail(mine_id):
    conn = get_db_connection()

    if conn is None:
        abort(500)

    cursor = None

    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM v_mines_gis WHERE id = ? LIMIT 1", (mine_id,))
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
            "risk_score": float(row["risk_score"]) if row["risk_score"] is not None else None,
            "risk_level": row["risk_level"],
            "region_id": row.get("region_id"),
            "region_code": row.get("region_code"),
            "region_name": row.get("region_name"),
            "region_level": row.get("region_level"),
            "latitude": float(row["latitude"]) if row["latitude"] is not None else None,
            "longitude": float(row["longitude"]) if row["longitude"] is not None else None
        }

        return render_template("mines/detail.html", mine=mine)

    except mariadb.Error:
        app.logger.exception("Error fetching mine details")
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

        # Queried directly against the base tables (rather than
        # v_recent_inspections, which does not expose mine_id/inspector_id/
        # duration/remarks) so every field the template needs is populated.
        cursor.execute("""
            SELECT
                i.id, i.report_no, i.mine_id, i.inspector_id, i.inspection_date,
                i.duration, i.remarks, i.status, i.pdf_path, i.created_at,
                m.name AS mine_name, m.code AS mine_code,
                m.state AS mine_state, m.district AS mine_district,
                u.name AS inspector_name,
                rs.risk_score, rs.risk_level
            FROM inspections i
            INNER JOIN mines m ON i.mine_id = m.id
            INNER JOIN users u ON i.inspector_id = u.id
            LEFT JOIN risk_scores rs ON rs.inspection_id = i.id
            ORDER BY i.inspection_date DESC, i.id DESC
            LIMIT 100
        """)

        inspections_data = cursor.fetchall()

        return render_template("inspections/index.html", inspections=inspections_data)

    except mariadb.Error:
        app.logger.exception("Error fetching inspections")
        abort(500)

    finally:
        if cursor:
            cursor.close()
        conn.close()


@app.route("/inspections/<int:inspection_id>")
@jwt_required()
def inspection_detail(inspection_id):
    conn = get_db_connection()

    if conn is None:
        abort(500)

    cursor = None

    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                i.id, i.report_no, i.mine_id, i.inspector_id, i.inspection_date,
                i.duration, i.remarks, i.status, i.pdf_path, i.created_at, i.updated_at,
                m.name AS mine_name, m.code AS mine_code, m.operator AS mine_operator,
                m.state AS mine_state, m.district AS mine_district, m.status AS mine_status,
                m.method AS mine_method, m.latitude AS mine_latitude, m.longitude AS mine_longitude,
                u.name AS inspector_name
            FROM inspections i
            INNER JOIN mines m ON i.mine_id = m.id
            INNER JOIN users u ON i.inspector_id = u.id
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
            "inspector": {"id": row["inspector_id"], "name": row["inspector_name"]},
            "findings": [],
            "evidence": []
        }

        cursor.execute("""
            SELECT f.id, f.inspection_id, f.issue, f.category, f.severity, f.recurring,
                   f.finding_code, f.note, ft.text AS finding_text
            FROM inspection_findings f
            LEFT JOIN finding_texts ft ON f.id = ft.finding_id
            WHERE f.inspection_id = ?
            ORDER BY f.id ASC
        """, (inspection_id,))

        for row in cursor.fetchall():
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

        cursor.execute("""
            SELECT id, inspection_id, finding_id, file_path, latitude, longitude,
                   evidence_type, description, created_at
            FROM inspection_evidence
            WHERE inspection_id = ?
            ORDER BY id ASC
        """, (inspection_id,))

        for row in cursor.fetchall():
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

        return render_template("inspections/detail.html", inspection=inspection)

    except mariadb.Error:
        app.logger.exception("Error fetching inspection details")
        abort(500)

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
    """List findings across all completed inspections."""

    conn = get_db_connection()

    if conn is None:
        abort(500)

    cursor = None

    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                f.id, f.inspection_id, f.issue, f.category, f.severity, f.recurring,
                f.finding_code, f.note, ft.text AS finding_text,
                i.report_no, i.inspection_date,
                m.name AS mine_name, m.code AS mine_code, m.state, m.district
            FROM inspection_findings f
            INNER JOIN inspections i ON f.inspection_id = i.id
            INNER JOIN mines m ON i.mine_id = m.id
            LEFT JOIN finding_texts ft ON f.id = ft.finding_id
            ORDER BY f.id DESC
            LIMIT 200
        """)

        findings_data = cursor.fetchall()

        return render_template("findings.html", findings=findings_data)

    except mariadb.Error:
        app.logger.exception("Error fetching findings")
        abort(500)

    finally:
        if cursor:
            cursor.close()
        conn.close()


# ============================================================
# PDF FINDINGS EXTRACTION UTILITIES (admin tool)
# ============================================================

def extract_pdf_text(pdf_path):
    document = pymupdf.open(pdf_path)
    text = ""

    for page in document:
        text += page.get_text()

    document.close()
    return text


def extract_findings(text):
    pattern = (
        r"Finding\s+(F-\d+):\s*(.*?)"
        r"(?=Finding\s+F-\d+:|(?:\n|\s)5\.\s*INSPECTOR[\'\u2019]?S\s+REMARKS|$)"
    )

    matches = re.findall(pattern, text, flags=re.DOTALL | re.IGNORECASE)

    return [
        {"finding_id": finding_id, "finding_text": finding_text.strip()}
        for finding_id, finding_text in matches
    ]


def process_pdf(pdf_path):
    """Extract structured findings straight from an inspection PDF report."""

    pdf_text = extract_pdf_text(pdf_path)
    findings_found = extract_findings(pdf_text)

    results = []

    for finding in findings_found:
        prediction = classify_finding(finding["finding_text"])

        results.append({
            "finding_id": finding["finding_id"],
            "finding_text": finding["finding_text"],
            "issue": prediction["issue"],
            "category": prediction["category"],
            "severity": prediction["severity"],
            "recurring": prediction["recurring"]
        })

    return results


@app.route("/api/admin/parse-pdf", methods=["POST"])
@jwt_required()
def parse_pdf_findings():
    """Upload a scanned/typed inspection PDF and run it through the AI engine."""

    claims = get_jwt()

    if claims.get("role") != "admin":
        return jsonify({"success": False, "message": "Administrator access required."}), 403

    uploaded_file = request.files.get("file")

    if uploaded_file is None or uploaded_file.filename == "":
        return jsonify({"success": False, "message": "A PDF file is required."}), 400

    filename = secure_filename(uploaded_file.filename)

    if not filename.lower().endswith(".pdf"):
        return jsonify({"success": False, "message": "Only PDF files are supported."}), 400

    temp_path = UPLOAD_DIR / f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"

    try:
        uploaded_file.save(str(temp_path))

        results = process_pdf(str(temp_path))
        risk_results = calculate_risk(results)

        return jsonify({"success": True, "findings": risk_results})

    except Exception as e:
        app.logger.exception("PDF parsing failed")
        return jsonify({
            "success": False,
            "message": "Unable to parse PDF.",
            "error": str(e)
        }), 500

    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass


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

        cursor.execute("""
            SELECT
                rs.id, rs.inspection_id, rs.mine_id, rs.risk_score, rs.risk_level,
                rs.risk_factors, rs.model_version, rs.created_at,
                i.report_no, i.inspection_date, i.status AS inspection_status,
                m.name AS mine_name, m.code AS mine_code, m.state, m.district
            FROM risk_scores rs
            INNER JOIN inspections i ON rs.inspection_id = i.id
            INNER JOIN mines m ON rs.mine_id = m.id
            ORDER BY rs.created_at DESC
        """)

        risk_records = cursor.fetchall()

        total = len(risk_records)
        high_count = sum(1 for r in risk_records if r["risk_level"] == "HIGH")
        critical_count = sum(1 for r in risk_records if r["risk_level"] == "CRITICAL")
        medium_count = sum(1 for r in risk_records if r["risk_level"] == "MEDIUM")
        low_count = sum(1 for r in risk_records if r["risk_level"] == "LOW")

        return render_template(
            "risk.html",
            risk_records=risk_records,
            total=total,
            high_count=high_count,
            critical_count=critical_count,
            medium_count=medium_count,
            low_count=low_count
        )

    except mariadb.Error:
        app.logger.exception("Error fetching risk data")
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
        cursor.execute("SELECT * FROM v_open_alerts")
        alert_records = cursor.fetchall()

        return render_template("alert.html", alerts=alert_records)

    except mariadb.Error:
        app.logger.exception("Error fetching alerts")
        return "Unable to load alerts", 500

    finally:
        if cursor:
            cursor.close()
        conn.close()


# ============================================================
# GIS MAP
# ============================================================

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
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                id, name, code, operator, state, district, status, method,
                risk_score, risk_level, latitude, longitude,
                region_id, region_code, region_name, region_level
            FROM v_mines_gis
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            ORDER BY id DESC
        """)

        features = []

        for row in cursor.fetchall():
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(row["longitude"]), float(row["latitude"])]
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
                    "risk_score": float(row["risk_score"]) if row["risk_score"] is not None else None,
                    "risk_level": row["risk_level"],
                    "region": {
                        "id": row["region_id"],
                        "code": row["region_code"],
                        "name": row["region_name"],
                        "level": row["region_level"]
                    }
                }
            })

        return jsonify({"type": "FeatureCollection", "features": features})

    except mariadb.Error as e:
        app.logger.exception("GIS mines API error")
        return jsonify({"type": "FeatureCollection", "features": [], "error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        conn.close()

def generate_response(user_prompt, max_new_tokens=300):

    genLLM_model.eval()

    messages = [
        {
            "role": "system",
            "content": (
                "You are MIRA (Mine Intelligence and Risk Assessment), "
                "an AI-based coal mine inspection and compliance assistant. "

                "Use only the supplied inspection findings, structured AI "
                "assessment, risk information, and retrieved regulatory guidance "
                "to answer the user's question. "

                "Do not calculate, modify, or override the provided issue, "
                "category, severity, recurring status, risk level, or risk confidence. "

                "Do not invent regulations, rule numbers, legal provisions, "
                "inspection history, or evidence that is not present in the context. "

                "For compliance-related questions, use only the Retrieved Guidance "
                "provided in the user prompt. "

                "If Language is English, respond in clear professional English. "

                "If Language is Hindi, understand Romanized Hindi or Hinglish "
                "input and respond ONLY in standard Hindi using Devanagari script. "
                "Do not respond in Romanized Hindi or English."
            )
        },
        {
            "role": "user",
            "content": user_prompt
        }
    ]

    prompt = genLLM_tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

    inputs = genLLM_tokenizer(
        prompt,
        return_tensors="pt"
    ).to(genLLM_model.device)

    streamer = TextIteratorStreamer(
        genLLM_tokenizer,
        skip_prompt=True,
        skip_special_tokens=True
    )

    generation_kwargs = {
        **inputs,
        "streamer": streamer,
        "max_new_tokens": max_new_tokens,
        "do_sample": False,
        "pad_token_id": genLLM_tokenizer.pad_token_id,
        "eos_token_id": genLLM_tokenizer.eos_token_id
    }

    thread = Thread(
        target = genLLM_model.generate,
        kwargs = generation_kwargs
    )

    thread.start()

    response = ""

    for new_text in streamer:
        print(new_text, end="", flush=True)
        response += new_text

    thread.join()

@app.route("/chatbot")
@jwt_required()
def chatbot():
    mine_id = request.args.get("mine_id", type=int)

    if not mine_id:
        flash("Mine ID is required.", "danger")
        return redirect(url_for("dashboard"))

    conn = get_db_connection()

    if conn is None:
        flash("Database connection failed.", "danger")
        return redirect(url_for("dashboard"))

    cursor = None

    try:
        cursor = conn.cursor(dictionary=True)

        # Get mine details
        cursor.execute(
            """
            SELECT
                id,
                name,
                code,
                operator,
                state,
                district,
                latitude,
                longitude
            FROM mines
            WHERE id = ?
            LIMIT 1
            """,
            (mine_id,)
        )

        mine = cursor.fetchone()

        if not mine:
            flash("Mine not found.", "danger")
            return redirect(url_for("dashboard"))

        # Get latest generated report for this mine
        cursor.execute(
            """
            SELECT
                id,
                report_no,
                pdf_path,
                report_pdf,
                created_at
            FROM inspections
            WHERE mine_id = ?
              AND (
                    pdf_path IS NOT NULL
                    OR report_pdf IS NOT NULL
                  )
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (mine_id,)
        )

        report = cursor.fetchone()

        report_path = None

        if report:
            report_path = report.get("report_pdf") or report.get("pdf_path")

        return render_template(
            "chatbot.html",
            mine_id=int(mine["id"]),
            mine_name=mine["name"],
            mine_code=mine.get("code"),
            operator=mine.get("operator"),
            state=mine.get("state"),
            district=mine.get("district"),
            latitude=mine.get("latitude"),
            longitude=mine.get("longitude"),
            report_path=report_path,
            report_no=report.get("report_no") if report else None
        )

    except mariadb.Error:
        app.logger.exception("Chatbot mine lookup failed")
        flash("Unable to load mine information.", "danger")
        return redirect(url_for("dashboard"))

    finally:
        if cursor:
            cursor.close()
        conn.close()

@app.route("/api/mine-chat", methods=["POST"])
@jwt_required()
def mine_chat():

    claims = get_jwt()

    # Admin-only chatbot
    if claims.get("role") != "admin":
        return jsonify({
            "success": False,
            "message": "Administrator access required."
        }), 403

    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "success": False,
            "message": "JSON body is required."
        }), 400

    mine_id = data.get("mine_id")
    mine_name = data.get("mine_name")
    report_path = data.get("report_path")
    message = data.get("message")
    history = data.get("history", [])

    if not mine_id:
        return jsonify({
            "success": False,
            "message": "mine_id is required."
        }), 400

    if not message:
        return jsonify({
            "success": False,
            "message": "Message is required."
        }), 400

    conn = None
    cursor = None

    try:

        conn = get_db_connection()

        if conn is None:
            return jsonify({
                "success": False,
                "message": "Database connection failed."
            }), 500

        cursor = conn.cursor(dictionary=True)

        # ---------------------------------------------------------
        # Fetch ONLY the mine information required by the chatbot.
        # Do not expose inspector / raw inspection information here.
        # ---------------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                name
            FROM mines
            WHERE id = ?
            LIMIT 1
            """,
            (mine_id,)
        )

        mine = cursor.fetchone()

        if not mine:
            return jsonify({
                "success": False,
                "message": "Mine not found."
            }), 404

        # ---------------------------------------------------------
        # Verify that the supplied mine name belongs to this mine.
        # ---------------------------------------------------------

        if mine_name and mine_name != mine["name"]:
            mine_name = mine["name"]

        # ---------------------------------------------------------
        # Temporary GenLLM placeholder
        #
        # Replace this section later with:
        #
        # response = generate_response(
        #     mine=mine,
        #     report_path=report_path,
        #     message=message,
        #     history=history
        # )
        # ---------------------------------------------------------

        response = (
            f"GenLLM placeholder for {mine['name']} "
            f"(Mine ID: {mine['id']}). "
            f"You asked: {message}"
        )

        return jsonify({
            "success": True,
            "response": response
        })

    except mariadb.Error:

        app.logger.exception("Mine chatbot database error")

        return jsonify({
            "success": False,
            "message": "Database error while processing chatbot request."
        }), 500

    except Exception:

        app.logger.exception("Mine chatbot error")

        return jsonify({
            "success": False,
            "message": "Unable to process chatbot request."
        }), 500

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()

if __name__ == "__main__":
    app.run(debug=True)