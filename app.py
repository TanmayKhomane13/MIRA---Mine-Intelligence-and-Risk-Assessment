from flask import Flask, render_template, session, request, redirect, url_for, flash, jsonify
from flask_session import Session
from helper import login_required
import os
import json
from pathlib import Path

app = Flask(__name__)

def get_database():
    conn = sqlite3.connect('ledger.db')
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/login", methods=['POST','GET'])
def login():
    return render_template("login.html")

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

# @app.route("/logout")
# def logout():
#     ...


@app.route("/mines")
def mines():
    return render_template("./mines/index.html")


@app.route("/mines/<mine_id>")
def mine_detail(mine_id):
    return render_template("./mines/detail.html")

@app.route("/inspections")
def inspections():
    return render_template("./inspections/index.html")

@app.route("/inspections/<inspection_id>")
def inspection_detail(inspection_id):
    return render_template("./inspections/detail.html")

@app.route("/risk")
def risk():
    return render_template("risk.html")

@app.route("/alerts")
def alerts():
    return render_template("alert.html")

@app.route("/map")
def gis_map():
    return render_template("map.html")

@app.route("/api/v1/gis/mines")
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
        
if __name__ == "__main__":
    app.run(debug=True)