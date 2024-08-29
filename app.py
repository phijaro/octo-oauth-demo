import csv
import smtplib
import sqlite3
from email.mime.text import MIMEText
from pathlib import Path

import jwt
import requests
from authlib.integrations.flask_client import OAuth
from flask import Flask, render_template, request, url_for

app = Flask("oauth-demo")
app.config.from_pyfile("oauth-demo-config.cfg")
app.secret_key = app.config["SECRET_KEY"].encode("ascii")

oauth = OAuth(app)
oegb_authserver = oauth.register(
    name="oegb",
    access_token_url="https://auth.octopus.energy/token/",
    authorize_url="https://auth.octopus.energy/authorize/",
    api_base_url="https://api.octopus.energy/",
    client_kwargs={"code_challenge_method": "S256"},
)


@app.route(f"{app.config['ROUTE_PREFIX']}/")
def index():
    return render_template("index.html", authorize_uri=url_for("authorize"))


@app.route(f"{app.config['ROUTE_PREFIX']}/authorize/")
def authorize():
    redirect_uri = url_for("callback", _external=True)
    return oauth.oegb.authorize_redirect(redirect_uri)


@app.route(f"{app.config['ROUTE_PREFIX']}/callback/")
def callback():
    if "code" not in request.args:
        return render_template("failure.html")

    tokens = oauth.oegb.authorize_access_token()
    access_token = tokens["access_token"]
    refresh_token = redact_refresh_token(tokens["refresh_token"])

    user_name = redact_user_name(fetch_user_name(access_token))
    user_email = redact_user_email(get_user_email(access_token))
    email_refresh_token(refresh_token, user_name, user_email)
    write_refresh_token_to_database(refresh_token, user_name, user_email)
    write_refresh_token_to_csv(refresh_token, user_name, user_email)

    return render_template("success.html")


def redact_refresh_token(refresh_token: str) -> str:
    redaction_length = len(refresh_token) - 8
    return f"{refresh_token[:4]}{'*' * redaction_length}{refresh_token[-4:]}"


def redact_user_name(user_name: str) -> str:
    return "John Doe"


def redact_user_email(user_email: str) -> str:
    return f"{user_email[0]}{'*' * 8}@{'*' * 8}{user_email[-1]}"


def get_user_email(access_token: str) -> str:
    payload = jwt.decode(access_token, options={"verify_signature": False})
    return payload["email"]


def fetch_user_name(access_token: str) -> str:
    query_string = "query getViewer {viewer{fullName}}"
    response = requests.post(
        oauth.oegb.api_base_url + "v1/graphql/",
        headers={"Authorization": access_token, "Content-Type": "application/graphql"},
        data=query_string,
    )
    return response.json()["data"]["viewer"]["fullName"]


def email_refresh_token(refresh_token: str, user_name: str, user_email: str) -> None:
    if not app.config["SMTP_SERVER"]:
        return

    email_body = f"""
Great news! {user_name} ({user_email}) has enrolled in the study.

Their refresh token is as follows:

{refresh_token}
"""
    msg = MIMEText(email_body)
    msg["Subject"] = f"Enrolment from the OAuth app: {user_email}"
    msg["From"] = app.config["ENROLMENT_EMAIL_FROM"]
    msg["To"] = app.config["ENROLMENT_EMAIL_TO"]

    smtp = smtplib.SMTP(app.config["SMTP_SERVER"])
    smtp.sendmail(
        app.config["ENROLMENT_EMAIL_FROM"],
        [app.config["ENROLMENT_EMAIL_TO"]],
        msg.as_string(),
    )
    smtp.quit()


def write_refresh_token_to_csv(
    refresh_token: str, user_name: str, user_email: str
) -> None:
    if not app.config["ENROLMENTS_CSV_FILE_PATH"]:
        return

    csv_file_path = Path(app.config["ENROLMENTS_CSV_FILE_PATH"])
    write_headers = not csv_file_path.exists()
    with open(csv_file_path, "a", newline="") as f:
        fieldnames = ["Name", "Email", "Refresh Token"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_headers:
            writer.writeheader()
        writer.writerow(
            {"Name": user_name, "Email": user_email, "Refresh Token": refresh_token}
        )


def write_refresh_token_to_database(
    refresh_token: str, user_name: str, user_email: str
) -> None:
    if not app.config["SQLITE_DB_PATH"]:
        return

    connection = sqlite3.connect(app.config["SQLITE_DB_PATH"])
    cursor = connection.cursor()

    cursor.execute("CREATE TABLE IF NOT EXISTS enrolments(name, email, refresh_token);")
    cursor.execute(
        "INSERT INTO enrolments VALUES (?, ?, ?);",
        (user_name, user_email, refresh_token),
    )

    connection.commit()
