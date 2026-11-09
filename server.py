#!/usr/bin/env python3
import os
import json
from flask import Flask, render_template, jsonify, request
from quota_fetcher import get_quota_data

app = Flask(__name__, template_folder="/home/ubuntu/antigravity-monitor/templates")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/quota")
def api_quota():
    force = request.args.get("force", "false").lower() == "true"
    data = get_quota_data(force_refresh=force)
    return jsonify(data)

@app.route("/api/refresh", methods=["POST", "GET"])
def api_refresh():
    data = get_quota_data(force_refresh=True)
    return jsonify(data)

def run_server(host="0.0.0.0", port=7860):
    print(f"🚀 Antigravity Live Quota Web Dashboard running at http://{host}:{port}")
    app.run(host=host, port=port, debug=False)

if __name__ == "__main__":
    run_server()
