from flask import Flask, render_template, session, request, redirect, url_for, flash
from flask_session import Session
from helper import login_required

app = Flask(__name__)

@app.route("/login", methods=['POST','GET'])
def login():
    return render_template("login.html")

@app.route("/")
@login_required
def dashboard():
    return render_template("dashboard.html")

@app.route("/logout")
def logout():
    ...


@app.route("/mines")
@login_required
def mines():
    ...


@app.route("/mines/<mine_id>")
@login_required
def mine_detail(mine_id):
    ...


@app.route("/inspections")
@login_required
def inspections():
    ...


@app.route("/inspections/create", methods=["GET", "POST"])
@login_required
def create_inspection():
    ...


@app.route("/inspections/<inspection_id>")
@login_required
def inspection_detail(inspection_id):
    ...


@app.route("/risk")
@login_required
def risk():
    ...


@app.route("/alerts")
@login_required
def alerts():
    ...


@app.route("/gis")
@login_required
def gis_map():
    ...
