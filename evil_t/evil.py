import os
from flask import Flask, request, redirect, render_template, session

app = Flask(__name__)
app.secret_key = "supersecretkey"

@app.route("/")
def index():
    return redirect("/login")


@app.route("/login", methods=["GET", "POST"])
def login():
    csrf_token = request.args.get("csrf_token", "")
    return render_template("csrf.html", csrf_token=csrf_token)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005, debug=True)
