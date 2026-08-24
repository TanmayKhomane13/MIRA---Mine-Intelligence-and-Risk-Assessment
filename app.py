from flask import Flask, render_template, session, request, redirect, url_for, flash
from flask_session import Session
from helper import login_required

app = Flask(__name__)

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
@login_required
def gis_map():
    return render_template("map.html")
