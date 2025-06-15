from flask import Flask, request,jsonify
from flask_cors import CORS
import requests
import os
import pymysql
import jwt
import datetime
import json
import re
from werkzeug.utils import secure_filename
app = Flask(__name__)
app.secret_key = os.urandom(24) 
app = Flask(__name__, static_url_path='/static', static_folder='C:/ip_camera')
CORS(app)
db = pymysql.connect(host='localhost', 
                     user='root', 
                     password='c107', 
                     database='ipcam')
SECRET_KEY = "11124214"
TOKEN_EXPIRY = 480
token_storage = {}

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

#管理者token
def generate_admin_token(admin_id):
    payload = {
        "admin_id": admin_id,
        "is_admin": True, 
        #"exp": datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    }
    
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token
    
def verify_admin_token(token):
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        if decoded.get("is_admin", False):
            return True, decoded
        if decoded.get("admin_id") == 2:
            return True, decoded
        
        return False, "不是管理者的 Token"
        
    except jwt.ExpiredSignatureError:
        return False, "Token 過期"
    except jwt.InvalidTokenError:
        return False, "無效的 Token"


#固定管理者登入
@app.route('/admin/fixed-token', methods=["POST"])
def get_fixed_admin_token(): 
    cursor = db.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT token FROM Admin WHERE admin_id = 2")
    admin = cursor.fetchone()

    if not admin or not admin["token"]:
        token = generate_admin_token(2)
        cursor.execute("UPDATE Admin SET token = %s WHERE admin_id = 2", (token,))
        db.commit()
        cursor.close()
        return jsonify({"token": token}), 200
    else:
        cursor.close()
        return jsonify({"token": admin["token"]}), 200
    
#取得所有啟用的專案列表
@app.route("/projects", methods=["GET"])
def get_all_projects():
    data = request.get_json()
    token = data.get('token', '')
    is_valid, payload = verify_admin_token(token)
    if not is_valid:
        return jsonify({"error": "無效的 Token"}), 401

    if not payload.get('is_admin', False):
        return jsonify({"error": "只有管理者能查看所有專案"}), 403

    cursor = db.cursor(pymysql.cursors.DictCursor)
    projects = []
    try:
        cursor.execute("""
        SELECT 
        p.project_id,
        p.start_time,
        p.camera_id,
        m.model_path
        FROM projects p
        LEFT JOIN modelprojectrelations mpr ON p.project_id = mpr.project_id
        LEFT JOIN models m ON mpr.model_id = m.model_id
        WHERE p.status = 1
        """)
        project_rows = cursor.fetchall()

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
                continue

            model_path_str = row.get("model_path", None)

            if model_path_str:
                try:
                    model_paths = json.loads(model_path_str)
                    py_path = model_paths.get("py", "").replace("\\", "/")
                    pt_path = model_paths.get("pt", "").replace("\\", "/")
                    
                    if not py_path or not pt_path:
                        raise ValueError("模型路徑無效")
                except Exception as e:
                    print(f"[錯誤] 無法解析模型路徑，專案 {project_id}: {e}")
                    py_path = pt_path = "" 
            else:
                py_path = pt_path = ""  

            projects.append({
                "project_id": row["project_id"],
                "model_paths": {
                    "py": py_path,
                    "pt": pt_path
                },
                "start_time": time_ranges,
                "camera": {
                    "rtsp_url": row.get("rtsp_url", "") 
                },
                "events": event_names
            })

        return jsonify(projects)

    finally:
        cursor.close()

#取得單個專案的詳細資料
@app.route("/project/<int:project_id>", methods=["GET"])
def get_project(project_id):
    data = request.get_json()
    token = data.get('token', '')
    is_valid, payload = verify_admin_token(token)
    if not is_valid:
        return jsonify({"error": "無效的 Token"}), 401
  
    if not payload.get('is_admin', False):
        return jsonify({"error": "只有管理者能查看專案"}), 403

    cursor = db.cursor(pymysql.cursors.DictCursor)
    try:
        query = """ 
           SELECT 
                p.project_id,
                p.start_time,
                GROUP_CONCAT(e.event_name) AS event_name,
                ANY_VALUE(m.model_path) AS model_path,
                ANY_VALUE(c.rtsp_url) AS rtsp_url,
                c.camera_id,
                c.ip_address AS camera_ip_address
            FROM Projects p
            LEFT JOIN ModelProjectRelations mpr ON p.project_id = mpr.project_id
            LEFT JOIN Models m ON mpr.model_id = m.model_id
            JOIN Cameras c ON p.camera_id = c.camera_id
            LEFT JOIN EventProjectRelations epr ON p.project_id = epr.project_id
            LEFT JOIN Events e ON epr.event_id = e.event_id
            WHERE p.project_id = %s
            GROUP BY p.project_id, c.camera_id
        """  
        cursor.execute(query, (project_id,))
        result = cursor.fetchone()

        if result:
            try:
                result["event_name"] = result["event_name"].split(",") if result["event_name"] else []
                result["start_time"] = json.loads(result["start_time"])
                if isinstance(result["start_time"], dict):
                    result["start_time"] = [result["start_time"]]
            except Exception as e:
                return jsonify({"error": f"資料處理錯誤: {str(e)}"}), 500


            if result["model_path"]:
                model_path = json.loads(result["model_path"]) 
                py_path = model_path.get("py", "").replace("\\\\", "/") 
                pt_path = model_path.get("pt", "").replace("\\\\", "/") 
            else:
                py_path = pt_path = ""

            return jsonify({
                "project_id": result["project_id"],
                "event_name": result["event_name"],
                "model_path": {
                    "py": py_path,
                    "pt": pt_path
                },
                "rtsp_url": result["rtsp_url"],
                "start_time": result["start_time"],
                "camera_id": result["camera_id"],
                "camera_ip_address": result["camera_ip_address"]
            })
        else:
            return jsonify({"error": "找不到該專案"}), 404

    except Exception as e:
        return jsonify({"error": f"查詢專案資料失敗: {str(e)}"}), 500

    finally:
        cursor.close()

#找下一筆專案
@app.route('/project/next', methods=['GET'])
def get_next_project():
    data = request.get_json()
    token = data.get('token', '') 
    current_project_id = data.get('project_id')
    if not current_project_id:
        return jsonify({"error": "缺少 project_id"}), 400
    
    is_valid, payload = verify_admin_token(token)
    if not is_valid:
        return jsonify({"error": payload}), 401

    if not payload.get('is_admin', False):
        return jsonify({"error": "只有管理者可以查看專案"}), 403

    cursor = db.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute("""
            SELECT * FROM Projects 
            WHERE project_id > %s
            ORDER BY project_id ASC
            LIMIT 1
        """, (current_project_id,))
        project = cursor.fetchone()

        if not project:
            return jsonify({"message": "沒有下一筆專案"}), 200

        project_id = project['project_id']

        cursor.execute("""
            SELECT contact_id FROM ContactProjectRelations 
            WHERE project_id = %s
        """, (project_id,))
        contacts = [row['contact_id'] for row in cursor.fetchall()]

        cursor.execute("""
            SELECT model_id FROM ModelProjectRelations 
            WHERE project_id = %s
        """, (project_id,))
        models = [row['model_id'] for row in cursor.fetchall()]

        cursor.execute("""
            SELECT event_id FROM EventProjectRelations 
            WHERE project_id = %s
        """, (project_id,))
        events = [row['event_id'] for row in cursor.fetchall()]

        result = {
            "project_id": project['project_id'],
            "project_name": project['project_name'],
            "camera_id": project['camera_id'],
            "start_time": json.loads(project['start_time']),
            "contacts_id": contacts,
            "model_id": models,
            "event_ids": events,
            "status": project['status']
        }

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": f"讀取下一筆專案失敗: {str(e)}"}), 500

    finally:
        cursor.close()

#抓取照片
@app.route('/download_image', methods=['POST'])
def download_image():
    data = request.get_json()
    token = data.get("token", "")
    is_valid, payload = verify_admin_token(token)
    if not is_valid:
        return jsonify({"error": "無效的 token"}), 401

    if not payload.get("is_admin"):
        return jsonify({"error": "只有管理者可以使用此功能"}), 403

    image_url = data.get("image_url", "").strip()
    project_id = data.get("project_id")
    event_id = data.get("event_id")
    occurred_at = data.get("occurred_at")

    if not all([image_url, project_id, event_id, occurred_at]):
        return jsonify({"error": "缺少必要欄位"}), 400
    if not re.match(r'^https?://', image_url):
        return jsonify({"error": "圖片 URL 格式錯誤"}), 400

    try:
        cursor = db.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT user_id, camera_id FROM Projects WHERE project_id = %s", (project_id,))
        project = cursor.fetchone()
        cursor.close()
        if not project:
            return jsonify({"error": "找不到專案"}), 404

        user_id = project["user_id"]
        camera_id = project["camera_id"]
        cursor = db.cursor(pymysql.cursors.DictCursor)
        cursor.execute("""
            SELECT m.model_name
            FROM Events e
            JOIN Models m ON e.model_id = m.model_id
            WHERE e.event_id = %s
        """, (event_id,))
        model_row = cursor.fetchone()
        cursor.close()
        model_name = model_row["model_name"] if model_row else "unknown_model"
        model_name = re.sub(r'[^a-zA-Z0-9_-]', '_', model_name)

        save_dir = f"C:/ip_camera/snapshots/user_{user_id}_cam_{camera_id}"
        os.makedirs(save_dir, exist_ok=True)
        filename = f"{model_name}.jpg"
        local_path = os.path.join(save_dir, filename)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": image_url
        }

        response = requests.get(image_url, stream=True, timeout=10, headers=headers)
        if response.status_code != 200:
            return jsonify({"error": f"圖片下載失敗: HTTP {response.status_code}"}), 400

        with open(local_path, "wb") as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)

        picture_url = f"/static/snapshots/user_{user_id}_cam_{camera_id}/{filename}"

        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO AbnormalEvents (project_id, event_id, picture_url, occurred_at)
            VALUES (%s, %s, %s, %s)
        """, (project_id, event_id, picture_url, occurred_at))
        db.commit()
        cursor.close()

        return jsonify({
            "picture_url": picture_url
        }), 200

    except Exception as e:
        return jsonify({"error": f"系統例外錯誤: {str(e)}"}), 500

@app.route('/event/abnormal', methods=["POST"])
def create_abnormal_event():
    data = request.get_json()
    token = data.get("token", "")
    is_valid, payload = verify_admin_token(token)
    if not is_valid:
        return jsonify({"error": payload}), 401
    if not payload.get("is_admin"):
        return jsonify({"error": "只有管理者可以發送異常通知"}), 403

    if not is_valid:
        return jsonify({"error": "Token 驗證失敗"}), 401

    project_id = data.get("project_id")
    event_id = data.get("event_id")
    picture_url = data.get("picture_url", "").strip()
    occurred_at = data.get("occurred_at")

    if not project_id or not event_id or not picture_url or not occurred_at:
        return jsonify({"error": "缺少必要欄位"}), 400

    try:
        datetime.datetime.strptime(occurred_at, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return jsonify({"error": "發生時間格式錯誤，需為 YYYY-MM-DD HH:MM:SS"}), 400

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