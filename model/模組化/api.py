from flask import Flask, jsonify, request
from flask_cors import CORS
import pymysql
import json
import os
import jwt
import datetime
from db_config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME

app = Flask(__name__)
app.secret_key = os.urandom(24)
CORS(app)

# -------------------- 資料庫設定 --------------------

def get_db_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

# -------------------- JWT 設定 --------------------
SECRET_KEY = "11124132"
TOKEN_EXPIRY = 480  # 可用來設定過期機制，尚未實作
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

# -------------------- 專案 API --------------------
@app.route("/projects", methods=["GET"])
def get_all_projects():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT 
                p.project_id,
                p.start_time,
                m.model_path,
                c.rtsp_url
            FROM projects p
            JOIN modelprojectrelations mpr ON p.project_id = mpr.project_id
            JOIN models m ON mpr.model_id = m.model_id
            JOIN cameras c ON p.camera_id = c.camera_id
            WHERE p.status = 1
        """)
        project_rows = cursor.fetchall()

        projects = []
        for row in project_rows:
            project_id = row["project_id"]
            cursor.execute("""
                SELECT e.event_name
                FROM events e
                JOIN eventprojectrelations epr ON e.event_id = epr.event_id
                WHERE epr.project_id = %s
            """, (project_id,))
            event_rows = cursor.fetchall()
            event_names = [e["event_name"] for e in event_rows]

            try:
                time_ranges = json.loads(row["start_time"])
                if isinstance(time_ranges, dict):
                    time_ranges = [time_ranges]
            except Exception as e:
                print(f"[錯誤] 專案 {project_id} 的 start_time 格式錯誤: {e}")
                continue

            projects.append({
                "id": str(project_id),
                "model_path": row["model_path"],
                "video_source": row["rtsp_url"],
                "notifications": event_names,
                "time_ranges": time_ranges
            })

        return jsonify(projects)

    finally:
        cursor.close()
        conn.close()

@app.route("/project/<int:project_id>", methods=["GET"])
def get_project(project_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """ 
        SELECT 
            p.project_id,
            p.start_time,
            GROUP_CONCAT(e.event_name) AS notifications,
            ANY_VALUE(m.model_path) AS model_path,
            ANY_VALUE(c.rtsp_url) AS rtsp_url
        FROM Projects p
        LEFT JOIN ModelProjectRelations mpr ON p.project_id = mpr.project_id
        LEFT JOIN Models m ON mpr.model_id = m.model_id
        JOIN Cameras c ON p.camera_id = c.camera_id
        LEFT JOIN EventProjectRelations epr ON p.project_id = epr.project_id
        LEFT JOIN Events e ON epr.event_id = e.event_id
        WHERE p.project_id = %s
        GROUP BY p.project_id
    """  

    cursor.execute(query, (project_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()

    if result:
        try:
            result["notifications"] = result["notifications"].split(",") if result["notifications"] else []
            result["time_ranges"] = json.loads(result["start_time"])
            if isinstance(result["time_ranges"], dict):
                result["time_ranges"] = [result["time_ranges"]]
        except Exception as e:
            return jsonify({"error": f"資料處理錯誤: {str(e)}"}), 500

        return jsonify(result)
    else:
        return jsonify({"error": "找不到該專案"}), 404

# -------------------- 異常事件紀錄 API --------------------
@app.route('/event/abnormal/create', methods=["POST"])
def create_abnormal_event():
    data = request.get_json()
    #token = data.get('token', '')
    #is_valid, payload = verify_token(token)

    #if not is_valid:
    #    return jsonify({"error": "Token 驗證失敗"}), 401

    project_id = data.get("project_id")
    event_id = data.get("event_id")
    picture_url = data.get("picture_url", "").strip()
    occurred_at = data.get("occurred_at") or datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO AbnormalEvents (project_id, event_id, picture_url, occurred_at)
            VALUES (%s, %s, %s, %s)
        """, (project_id, event_id, picture_url, occurred_at))
        conn.commit()
        return jsonify({"message": "異常事件紀錄成功"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    app.run(debug=True, host="127.0.0.1", port=5000)
