from flask import Flask, make_response,redirect, request, url_for, send_file,jsonify
from flask_cors import CORS
import requests
import os
import pymysql
import jwt
import datetime
import uuid
import json
app = Flask(__name__)
app.secret_key = os.urandom(24) 
CORS(app)
db = pymysql.connect(host='localhost', 
                     user='root', 
                     password='c107', 
                     database='ipcam')

# LINE Login Credentials
LINE_CLIENT_ID = "2006911351"
LINE_CLIENT_SECRET = "f049a5c4224180099cd88dc599745cdf"
REDIRECT_URI = "http://210.240.202.108"

# LINE Authorization URL
LINE_AUTH_URL = "https://access.line.me/oauth2/v2.1/authorize"
LINE_TOKEN_URL = "https://api.line.me/oauth2/v2.1/token"
LINE_PROFILE_URL = "https://api.line.me/v2/profile"

SECRET_KEY = "11124214"
TOKEN_EXPIRY = 480
token_storage = {}
def generate_token(user_id, user_name, line_id, picture_url=''):
    payload = {
        "user_id": user_id,
        "user_name": user_name,
        "line_id": line_id,
        "picture_url": picture_url
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token
def verify_token(token):
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return True, decoded
    
    except jwt.InvalidTokenError:
        return False, "無效的 Token"

@app.route('/event/abnormal/create', methods=["POST"])
def create_abnormal_event():
    data = request.get_json()
    token = data.get('token', '')
    is_valid = verify_token(token)

    if not is_valid:
        return jsonify({"error": "Token 驗證失敗"}), 401
    project_id = data.get("project_id")
    event_id = data.get("event_id")
    picture_url = data.get("picture_url", "").strip()
    occurred_at = data.get("occurred_at")

    if not occurred_at:
        occurred_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if not project_id or not event_id or not picture_url:
        return jsonify({"error": "缺少必要欄位"}), 400

    cursor = db.cursor()

    try:
        cursor.execute("""
            INSERT INTO AbnormalEvents (project_id, event_id, picture_url, occurred_at)
            VALUES (%s, %s, %s, %s)
        """, (project_id, event_id, picture_url, occurred_at))
        db.commit()
        return jsonify({"message": "異常事件紀錄成功"}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
if __name__ == '__main__':
    app.run(debug=True)