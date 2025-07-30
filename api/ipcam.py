from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import pymysql
import jwt
import hashlib
import os
import shutil
import json
from werkzeug.utils import secure_filename
import paramiko
import datetime
import re
import uuid

app = Flask(__name__)
app.secret_key = os.urandom(24) 
app = Flask(__name__, static_url_path='/static', static_folder='C:/ip_camera')
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
LINE_CHANNEL_ACCESS_TOKEN = "HNEuVLuOEnGDi+nAoJh7ZIFtOWTmMpTQTVYrx/+L5kjK1YZcW1D3KsNNw/Yt2WhlN9AyTVXIFWZrnwjfMJ8dADbmm1jvTIvxhVzK2aJtjbfvMgUJOnioSetlQ67rZffFWU43PqPcgP+WktjF1Gr2ewdB04t89/1O/w1cDnyilFU="
SECRET_KEY = "11124214"
TOKEN_EXPIRY = 480
token_storage = {}

# 模型檔案上傳基本設定
MODEL_UPLOAD_FOLDER = "C:/models"
ALLOWED_MODEL_EXTENSIONS = {"py", "pt"}
os.makedirs(MODEL_UPLOAD_FOLDER, exist_ok=True)

#照片上傳
PICTURE_UPLOAD_FOLDER = "C:/pictures"
ALLOWED_PICTURE_EXTENSIONS = {'png', 'jpg'}
os.makedirs(PICTURE_UPLOAD_FOLDER, exist_ok=True)
app.config['PICTURE_UPLOAD_FOLDER'] = PICTURE_UPLOAD_FOLDER

#Jetson Nano 路徑
JETSON_DEST_PATH = "/home/yuuu/models"
def generate_token(user_id, user_name, line_id, picture_url=''):
    #expiration_time = datetime.datetime.now() + datetime.timedelta(minutes=TOKEN_EXPIRY)
    payload = {
        "user_id": user_id,
        "user_name": user_name,
        "line_id": line_id,
        "picture_url": picture_url
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token#, expiration_time, payload

#驗證JWT Token
def verify_token(token):
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return True, decoded
    #except jwt.ExpiredSignatureError:
    #return False, "Token 過期"
    except jwt.InvalidTokenError:
        return False, "無效的 Token"
    
#管理者token
def generate_admin_token(admin_id):
    payload = {
        "admin_id": admin_id,
        "is_admin": True, 
        # "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token
    
#驗證管理者token
def verify_admin_token(token):
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        if decoded.get("is_admin", False) or decoded.get("admin_id") == 2:
            return True, decoded
        
        return False, "不是管理者的 Token"
        
    except jwt.ExpiredSignatureError:
        return False, "Token 過期"
    except jwt.InvalidTokenError:
        return False, "無效的 Token"

#發送LINE 訊息的函式
def send_line_message(line_id, text):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    payload = {
        "to": line_id,
        "messages": [
            {
                "type": "text",
                "text": text
            }
        ]
    }

    response = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers=headers,
        data=json.dumps(payload)
    )
    return response.status_code, response.text

def sha256_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

#判斷照片附檔名是否允許
def clean_filename(filename):
    return re.sub(r'[^\u4e00-\u9fa5\w\.\- ]', '', filename)

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

#初始化
@app.route('/admin/init', methods=["POST"])
def init_admin_password():
    data = request.get_json()
    admin_id = int(data.get("admin_id"))
    password = data.get("admin_password")

    if not admin_id or not password:
        return jsonify({"error": "缺少 admin_id 或 admin_password"}), 400

    cursor = db.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT admin_password FROM Admin WHERE admin_id = %s", (admin_id,))
    result = cursor.fetchone()

    if not result:
        return jsonify({"error": "管理者不存在"}), 404

    if result["admin_password"]:
        return jsonify({"error": "密碼已存在，禁止重設"}), 403

    hashed_pw = sha256_password(password)
    cursor.execute("UPDATE Admin SET admin_password = %s WHERE admin_id = %s", (hashed_pw, admin_id))
    db.commit()
    cursor.close()

    return jsonify({"message": "初始化成功"}), 200

#管理者登入
@app.route('/admin/login', methods=["POST"])
def admin_login():
    data = request.get_json()
    admin_id = int(data.get("admin_id"))
    admin_password = data.get("admin_password")

    if not admin_id or not admin_password:
        return jsonify({"error": "缺少 admin_id 或 admin_password"}), 400

    hashed_input = sha256_password(admin_password)
    cursor = db.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT admin_password FROM Admin WHERE admin_id = %s", (admin_id,))
    result = cursor.fetchone()

    if not result or not result["admin_password"]:
        return jsonify({"error": "帳號不存在或尚未初始化"}), 404

    if result["admin_password"] != hashed_input:
        return jsonify({"error": "密碼錯誤"}), 401

    token = generate_admin_token(admin_id)
    cursor.execute("UPDATE Admin SET token = %s WHERE admin_id = %s", (token, admin_id))
    db.commit()
    cursor.close()

    return jsonify({"token": token}), 200

#模型管理者
@app.route('/admin/fixed-token', methods=["POST"])
def get_fixed_admin_token(): 
    data = request.get_json()
    admin_id = data.get("admin_id")

    if not admin_id:
        return jsonify({"error": "缺少 admin_id"}), 400

    cursor = db.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT token FROM Admin WHERE admin_id = %s", (admin_id,))
    result = cursor.fetchone()

    if not result:
        return jsonify({"error": "管理者不存在"}), 404

    if result["token"]:
        return jsonify({"token": result["token"]}), 200
    else:
        token = generate_admin_token(admin_id)
        cursor.execute("UPDATE Admin SET token = %s WHERE admin_id = %s", (token, admin_id))
        db.commit()
        cursor.close()
        return jsonify({"token": token}), 200
    
#管理者登出
@app.route('/admin/logout', methods=["POST"])
def admin_logout():
    data = request.get_json()
    token = data.get('token', '')

    is_valid, payload = verify_admin_token(token)
    if not is_valid:
        return jsonify({"error": "無效的 Token"}), 401

    admin_id = int(payload.get('admin_id', 0))

    cursor = db.cursor()

    if admin_id != 2:
        cursor.execute("UPDATE Admin SET token = NULL WHERE admin_id = %s", (admin_id,))
        db.commit()

    cursor.close()
    return '', 200

#使用者登入
@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return jsonify({"error": "No code received"}), 400

    token_data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'client_id': LINE_CLIENT_ID,
        'client_secret': LINE_CLIENT_SECRET
    }

    token_response = requests.post(LINE_TOKEN_URL, data=token_data)

    if token_response.status_code != 200:
        return jsonify({"error": "Error retrieving access token"}), 400

    token_json = token_response.json()

    if 'access_token' not in token_json:
        return jsonify({"error": "Error retrieving access token"}), 400

    access_token = token_json['access_token']
    headers = {'Authorization': f'Bearer {access_token}'}
    profile_response = requests.get(LINE_PROFILE_URL, headers=headers)
    profile_json = profile_response.json()

    line_user_id = profile_json.get('userId')
    if not line_user_id:
        return jsonify({"error": "userId not found"}), 401

    cursor = db.cursor()
    cursor.execute("SELECT user_id, user_name FROM users WHERE line_id = %s", (line_user_id,))
    result = cursor.fetchone()
    print("LINE ID:", profile_json.get('userId'))
    if result:
        user_id, name = result
        token= generate_token(user_id, name, line_user_id)

        cursor.execute("""
            UPDATE users SET token = %s WHERE user_id = %s
        """, (token, user_id))
        db.commit()
        cursor.close()
        return jsonify({
            "message": f"{name}，歡迎回來",
            "is_new_user": False,
            "token": token
        }),200
    else:
        token= generate_token('', '', line_user_id)
        cursor.close()

        return jsonify({
            "message": "首次登入，請設定您的名字",
            "is_new_user": True,
            "token": token
        }),200
       
#設定名字
@app.route('/set_name', methods=['POST'])
def set_name():
    data = request.get_json()
    token = data.get('token', '')
    is_valid, payload = verify_token(token)
    if not is_valid or 'line_user_id' not in payload:
        return jsonify({"error": "Token 驗證失敗"}), 401
    line_user_id = payload.get('line_user_id', '')
    username = request.json.get('username', '').strip()

    if not line_user_id or not username:
        return jsonify({"error": "請輸入姓名"}), 400

    cursor = db.cursor()
    cursor.execute("SELECT MAX(user_id) AS max_id FROM Users")
    result = cursor.fetchone()
    max_id = result[0] if result[0] else 10000000
    user_id = str(int(max_id) + 1)
    token= generate_token(user_id, username, line_user_id)

    cursor.execute("""
        INSERT INTO users (user_id, line_id, user_name, token)
        VALUES (%s, %s, %s, %s)
    """, (user_id, line_user_id, username, token))
    db.commit()
    cursor.close()
    return jsonify({"token" : token}),200

#取得使用者
@app.route('/user', methods=["POST"])
def user():
    data = request.get_json()
    token = data.get('token', '')
    is_valid, payload = verify_token(token)
    if not is_valid:
        return jsonify({"error": payload}), 401

    user_id = payload.get("user_id")
    name = payload.get("name")
    line_user_id = payload.get("line_user_id")
    picture_url = payload.get("picture_url", "")
    exp = payload.get("exp")
    #expiration_time = datetime.datetime.utcfromtimestamp(exp).strftime('%Y-%m-%d %H:%M:%S')
    return jsonify({
        "user_id": user_id,
        "name": name,
        "line_user_id": line_user_id,
        "picture_url": picture_url,
        #"token_expiration": expiration_time
    }),200

#登出
@app.route('/logout', methods=["POST"])
def logout():
    data = request.get_json()
    token = data.get('token', '')
    is_valid, payload = verify_token(token)

    if not is_valid:
        return jsonify({"error": "無效的 Token"}), 401

    user_id = payload.get('user_id', '')

    cursor = db.cursor()
    cursor.execute("UPDATE users SET token = NULL WHERE user_id = %s", (user_id,))
    db.commit()
    cursor.close()
    return '', 200

#新增聯絡人
@app.route('/contact/create', methods=["POST"])
def create_contact():
    data = request.get_json()
    token = data.get('token', '')
    is_valid, payload = verify_token(token)

    if not is_valid:
        return '', 401

    current_user_id = payload.get("user_id")
    contact_user_id = data.get("contact_user_id")
    contact_name = data.get("contact_name", "").strip()

    if not contact_user_id or not contact_name:
        return '', 400 
    
    if contact_user_id == current_user_id:
        return '', 400

    cursor = db.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT user_id FROM Users WHERE user_id = %s", (contact_user_id,))
    user = cursor.fetchone()
    if not user:
        return '', 404

    try:
        cursor.execute("""
            INSERT INTO Contacts (contact_id, user_id, contact_name)
            VALUES (%s, %s, %s)
        """, (contact_user_id, current_user_id, contact_name))
        db.commit()
    except pymysql.IntegrityError:
        return '', 409

    return '', 200


#刪除聯絡人
@app.route('/contact/delete', methods=["DELETE"])
def delete_contact():
    data = request.get_json()
    token = data.get('token', '')
    if not token:
        return '', 401
    is_valid, payload = verify_token(token)
    if not is_valid:
        return '', 401
    current_user_id = payload.get("user_id")
    data = request.json
    contact_user_id = data.get("contact_user_id")
    if not contact_user_id:
        return '', 400

    cursor = db.cursor(pymysql.cursors.DictCursor)
    cursor.execute(
        "SELECT * FROM Contacts WHERE contact_id = %s AND user_id = %s",
        (contact_user_id, current_user_id)
    )
    contact = cursor.fetchone()
    if not contact:
        return '', 404
    cursor.execute(
        "DELETE FROM Contacts WHERE contact_id = %s AND user_id = %s",
        (contact_user_id, current_user_id)
    )
    db.commit()

    return '', 200


#修改聯絡人
@app.route('/contact/update', methods=["POST"])
def update_contact_name():
    data = request.get_json()
    token = data.get('token', '')
    is_valid, payload = verify_token(token)
    if not is_valid:
        return '', 401
    current_user_id = payload.get("user_id")
    data = request.get_json()
    contact_user_id = data.get("contact_user_id")
    new_contact_name = data.get("contact_name", "").strip()
    if not contact_user_id or not new_contact_name:
        return '', 400
    cursor = db.cursor(pymysql.cursors.DictCursor)
    cursor.execute(
        "SELECT * FROM Contacts WHERE contact_id = %s AND user_id = %s",
        (contact_user_id, current_user_id)
    )
    contact = cursor.fetchone()
    if not contact:
        return '', 404
    cursor.execute(
        "UPDATE Contacts SET contact_name = %s WHERE contact_id = %s AND user_id = %s",
        (new_contact_name, contact_user_id, current_user_id)
    )
    db.commit()
    return '', 200


#讀取聯絡人
@app.route('/contact', methods=["POST"])
def list_contacts():
    data = request.get_json()
    token = data.get('token', '')
    is_valid, payload = verify_token(token)

    if not is_valid:
        return jsonify({"error": payload}), 401

    current_user_id = payload.get("user_id")

    cursor = db.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT contact_id, contact_name FROM Contacts WHERE user_id = %s", (current_user_id,))
    contacts = cursor.fetchall()
    return jsonify({
        "contacts": contacts
    }),200

#新增攝影機
@app.route('/camera/create', methods=["POST"])
def create_camera():
    data = request.get_json()
    token = data.get('token', '')

    is_valid, payload = verify_token(token)
    if not is_valid:
        return '', 401

    user_id = payload.get("user_id")
    camera_name = data.get("camera_name", "").strip()
    brand = data.get("brand", "").strip()
    model = data.get("model", "").strip()
    ip_address = data.get("ip_address", "").strip()
    camera_username = data.get("camera_username", "").strip()
    camera_password = data.get("camera_password", "").strip()
    rtsp_url = data.get("rtsp_url", "").strip()
    device_id = data.get("device_id", "").strip()

    if not all([camera_name, brand, model, ip_address, camera_username, camera_password, rtsp_url]):
        return jsonify({"error": "缺少必要欄位"}), 400

    cursor = db.cursor(pymysql.cursors.DictCursor)

    if device_id:
        cursor.execute("SELECT user_id FROM Devices WHERE device_id = %s", (device_id,))
        device = cursor.fetchone()

        if not device or device['user_id'] != user_id:
            cursor.close()
            return jsonify({"error": "裝置不存在或不屬於此使用者"}), 400

        cursor.execute("SELECT 1 FROM Projects WHERE device_id = %s", (device_id,))
        if cursor.fetchone():
            cursor.close()
            return jsonify({"error": "該裝置已被專案使用，無法綁定"}), 400

        cursor.execute("SELECT 1 FROM Cameras WHERE device_id = %s", (device_id,))
        if cursor.fetchone():
            cursor.close()
            return jsonify({"error": "該裝置已被其他攝影機綁定，無法綁定"}), 400
    else:
        device_id = None

    cursor.execute("""
        INSERT INTO Cameras (user_id, camera_name, brand, model, ip_address, camera_username, camera_password, rtsp_url, device_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (user_id, camera_name, brand, model, ip_address, camera_username, camera_password, rtsp_url, device_id))

    db.commit()
    cursor.close()
    return '', 200

#刪除攝影機
@app.route('/camera/delete', methods=['DELETE'])
def delete_camera():
    data = request.get_json()
    token = data.get('token', '')
    camera_id = data.get('camera_id')

    is_valid, payload = verify_token(token)
    if not is_valid:
        return '', 401

    user_id = payload.get('user_id')
    if not camera_id:
        return jsonify({"error": "缺少 camera_id"}), 400

    cursor = db.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM Cameras WHERE camera_id = %s AND user_id = %s", (camera_id, user_id))
    camera = cursor.fetchone()
    if not camera:
        cursor.close()
        return jsonify({"error": "找不到攝影機"}), 404

    cursor.execute("SELECT 1 FROM Projects WHERE camera_id = %s", (camera_id,))
    if cursor.fetchone():
        cursor.close()
        return jsonify({"error": "此攝影機已有專案綁定，請先移除專案"}), 400

    if camera.get('device_id'):
        cursor.execute("""
            UPDATE Cameras 
            SET device_id = NULL 
            WHERE camera_id = %s
        """, (camera_id,))

    cursor.execute("DELETE FROM Cameras WHERE camera_id = %s AND user_id = %s", (camera_id, user_id))

    db.commit()
    cursor.close()
    return '', 200

#修改攝影機
@app.route('/camera/update', methods=["POST"])
def update_camera():
    data = request.get_json()
    token = data.get('token', '')
    camera_id = data.get('camera_id')

    is_valid, payload = verify_token(token)
    if not is_valid:
        return '', 401

    user_id = payload.get('user_id')
    if not camera_id:
        return jsonify({"error": "缺少 camera_id"}), 400

    cursor = db.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM Cameras WHERE camera_id = %s AND user_id = %s", (camera_id, user_id))
    camera = cursor.fetchone()
    if not camera:
        cursor.close()
        return jsonify({"error": "找不到攝影機"}), 404

    update_fields = {
        "camera_name": data.get("camera_name", "").strip(),
        "brand": data.get("brand", "").strip(),
        "model": data.get("model", "").strip(),
        "ip_address": data.get("ip_address", "").strip(),
        "camera_username": data.get("camera_username", "").strip(),
        "camera_password": data.get("camera_password", "").strip(),
        "rtsp_url": data.get("rtsp_url", "").strip(),
        "device_id": data.get("device_id", "").strip()
    }

    if update_fields["device_id"]:
        cursor.execute("SELECT user_id FROM Devices WHERE device_id = %s", (update_fields["device_id"],))
        device = cursor.fetchone()
        if not device or device['user_id'] != user_id:
            cursor.close()
            return jsonify({"error": "裝置不存在或不屬於此使用者"}), 400

        cursor.execute("""
            SELECT 1 FROM Cameras
            WHERE device_id = %s AND camera_id != %s
        """, (update_fields["device_id"], camera_id))
        if cursor.fetchone():
            cursor.close()
            return jsonify({"error": "該裝置已被其他攝影機綁定"}), 400

        cursor.execute("""
            SELECT 1 FROM Projects
            WHERE device_id = %s
        """, (update_fields["device_id"],))
        if cursor.fetchone():
            cursor.close()
            return jsonify({"error": "該裝置已被專案使用，無法綁定"}), 400

    set_clauses = []
    values = []
    for key, value in update_fields.items():
        if value or (key == "device_id" and value == ""):
            set_clauses.append(f"{key} = %s")
            values.append(value if value != "" else None)

    if not set_clauses:
        cursor.close()
        return jsonify({"error": "沒有提供要更新的資料"}), 400

    values.extend([camera_id, user_id])
    cursor.execute(f"""
        UPDATE Cameras
        SET {", ".join(set_clauses)}
        WHERE camera_id = %s AND user_id = %s
    """, tuple(values))

    db.commit()
    cursor.close()
    return '', 200

#讀取攝影機
@app.route('/camera', methods=["POST"])
def cameras():
    data = request.get_json()
    token = data.get('token', '')

    is_valid, payload = verify_token(token)
    if not is_valid:
        return jsonify({"error": payload}), 401

    user_id = payload.get('user_id')

    cursor = db.cursor(pymysql.cursors.DictCursor)
    cursor.execute("""
        SELECT 
            camera_id,
            camera_name,
            brand,
            model,
            ip_address,
            camera_username,
            camera_password,
            rtsp_url,
            device_id,
            created_at
        FROM Cameras
        WHERE user_id = %s
    """, (user_id,))
    cameras = cursor.fetchall()
    cursor.close()

    for cam in cameras:
        if cam.get('created_at'):
            cam['created_at'] = cam['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        if cam.get('device_id') is None:
            cam['device_id'] = None

    return jsonify({
        "cameras": cameras
    }), 200

#新增模型jeston nano
def upload_to_jetson(ip, local_path, remote_path, username, password):
    try:
        transport = paramiko.Transport((ip, 22))
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.put(local_path, remote_path)
        sftp.close()
        transport.close()
        return True
    except Exception as e:
        print(f"SFTP error: {e}")
        return False
    
@app.route('/model/jeston nano', methods=['POST'])
def create_model_jeston_nano():
    token = request.form.get('token', '').strip()
    if not token:
        return jsonify({"error": "缺少 Token"}), 400

    is_valid, payload = verify_admin_token(token)
    if not is_valid:
        return jsonify({"error": "無效的 Token"}), 401

    jetson_ip = request.form.get('jetson_ip', '').strip()
    jetson_user = request.form.get('jetson_username', '').strip()
    jetson_pass = request.form.get('jetson_password', '').strip()

    if not jetson_ip or not jetson_user or not jetson_pass:
        return jsonify({"error": "缺少 Jetson 連線資訊"}), 400

    model_name = request.form.get('model_name', '').strip()
    model_version = request.form.get('model_version', '').strip()
    event_type = request.form.get('event_type', '').strip()

    if not model_name or not model_version or not event_type:
        return jsonify({"error": "缺少模型資料"}), 400

    py_file = request.files.get("py_file")
    pt_file = request.files.get("pt_file")

    if not py_file or not pt_file:
        return jsonify({"error": "沒有收到完整檔案"}), 400

    model_folder = os.path.join(MODEL_UPLOAD_FOLDER, model_name)
    os.makedirs(model_folder, exist_ok=True)

    filenames = {}
    upload_results = {}

    for ftype, file in [('py', py_file), ('pt', pt_file)]:
        if file and allowed_file(file.filename, ALLOWED_MODEL_EXTENSIONS):
            filename = secure_filename(file.filename)
            local_path = os.path.join(model_folder, filename)
            file.save(local_path)

            remote_path = os.path.join(JETSON_DEST_PATH, model_name, filename)

            try:
                transport = paramiko.Transport((jetson_ip, 22))
                transport.connect(username=jetson_user, password=jetson_pass)
                sftp = paramiko.SFTPClient.from_transport(transport)
                try:
                    sftp.mkdir(os.path.join(JETSON_DEST_PATH, model_name))
                except:
                    pass 
                sftp.put(local_path, remote_path)
                sftp.close()
                transport.close()
                upload_results[ftype] = "success"
            except Exception as e:
                print(f"SFTP error: {e}")
                upload_results[ftype] = "fail"

            filenames[ftype] = os.path.normpath(local_path)
        else:
            return jsonify({"error": f"{ftype} 檔案格式錯誤或遺失"}), 400

    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO Models (model_name, model_version, event_type, model_path)
        VALUES (%s, %s, %s, %s)
    """, (
        model_name,
        model_version,
        event_type,
        json.dumps({
            "py": filenames.get("py", ""),
            "pt": filenames.get("pt", "")
        }, ensure_ascii=False)
    ))
    db.commit()
    cursor.close()

    return '', 200

#刪除模型
@app.route('/model/delete/jeston nano', methods=['DELETE'])
def delete_model_jeston_nano():
    data = request.get_json()
    token = data.get('token', '')
    model_id = data.get('model_id')

    is_valid, payload = verify_admin_token(token)
    if not is_valid:
        return jsonify({"error": "無效的 Token"}), 401

    if not model_id:
        return jsonify({"error": "缺少 model_id"}), 400

    cursor = db.cursor()
    cursor.execute("SELECT model_path FROM Models WHERE model_id = %s", (model_id,))
    row = cursor.fetchone()

    if not row:
        cursor.close()
        return jsonify({"error": "模型不存在"}), 404

    try:
        paths = json.loads(row[0])
        for path in paths.values():
            if os.path.exists(path):
                os.remove(path)
    except:
        pass

    cursor.execute("DELETE FROM Models WHERE model_id = %s", (model_id,))
    db.commit()
    cursor.close()

    return '', 200

#修改模型
@app.route('/model/update/jeston nano', methods=['POST'])
def update_model_jeston_nano():
    token = request.form.get('token', '').strip()
    if not token:
        return jsonify({"error": "缺少 Token"}), 400

    is_valid, payload = verify_admin_token(token)
    if not is_valid:
        return jsonify({"error": "無效的 Token"}), 401

    model_id = request.form.get('model_id', '').strip()
    if not model_id:
        return jsonify({"error": "缺少 model_id"}), 400

    model_name = request.form.get('model_name')
    model_version = request.form.get('model_version')
    event_type = request.form.get('event_type')

    jetson_ip = request.form.get('jetson_ip', '').strip()
    jetson_user = request.form.get('jetson_username', '').strip()
    jetson_pass = request.form.get('jetson_password', '').strip()

    py_file = request.files.get("py_file")
    pt_file = request.files.get("pt_file")

    cursor = db.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM Models WHERE model_id = %s", (model_id,))
    row = cursor.fetchone()
    if not row:
        return jsonify({"error": "找不到模型"}), 404

    current_paths = json.loads(row['model_path'])
    current_name = row['model_name']
    updated_paths = {}

    model_folder = os.path.join(MODEL_UPLOAD_FOLDER, model_name or current_name)
    os.makedirs(model_folder, exist_ok=True)

    for ftype, file in [('py', py_file), ('pt', pt_file)]:
        if file and allowed_file(file.filename, ALLOWED_MODEL_EXTENSIONS):
            filename = secure_filename(file.filename)
            local_path = os.path.join(model_folder, filename)
            file.save(local_path)

            if jetson_ip and jetson_user and jetson_pass:
                try:
                    transport = paramiko.Transport((jetson_ip, 22))
                    transport.connect(username=jetson_user, password=jetson_pass)
                    sftp = paramiko.SFTPClient.from_transport(transport)
                    try:
                        sftp.mkdir(os.path.join(JETSON_DEST_PATH, model_name or current_name))
                    except:
                        pass
                    remote_path = os.path.join(JETSON_DEST_PATH, model_name or current_name, filename)
                    sftp.put(local_path, remote_path)
                    sftp.close()
                    transport.close()
                except Exception as e:
                    print(f"SFTP error: {e}")

            updated_paths[ftype] = local_path.replace("/", "\\")

    current_paths.update(updated_paths)

    update_fields = []
    values = []

    if model_name:
        update_fields.append("model_name = %s")
        values.append(model_name)
    if model_version:
        update_fields.append("model_version = %s")
        values.append(model_version)
    if event_type:
        update_fields.append("event_type = %s")
        values.append(event_type)

    update_fields.append("model_path = %s")
    values.append(json.dumps(current_paths, ensure_ascii=False))
    values.append(model_id)

    sql = f"UPDATE Models SET {', '.join(update_fields)} WHERE model_id = %s"
    cursor.execute(sql, values)
    db.commit()
    cursor.close()

    return '', 200

#讀取模型
@app.route('/models/jeston nano', methods=['GET'])
def get_all_models_jeston_nano():
    data = request.get_json()
    token = data.get('token', '')
    is_valid, payload = verify_admin_token(token)
    if not is_valid:
        return jsonify({"error": "無效的 Token"}), 401

    cursor = db.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM Models")
    models = cursor.fetchall()
    cursor.close()

    for model in models:
        try:
            model_path = json.loads(model['model_path'])
            model['model_path'] = model_path
        except Exception as e:
            model['model_path'] = {}
            model['error'] = f"model_path 解析失敗: {str(e)}"

    return jsonify(models), 200

#==================== 新增模型 ====================
@app.route('/model/create', methods=["POST"])
def create_model():
    # 權限驗證
    token = request.form.get("token", "")
    is_valid, payload = verify_admin_token(token)
    if not is_valid:
        return jsonify({"error": payload}), 401
    if not payload.get("is_admin"):
        return jsonify({"error": "只有管理者可以新增模型"}), 403

    # 取得欄位資料
    name = request.form.get("name", "").strip()
    version = request.form.get("version", "").strip()
    raw_event = request.form.get("event", "").strip()

    if not name or not version or not raw_event:
        return jsonify({"error": "缺少必要欄位"}), 400

    cursor = db.cursor()

    # 檢查模型是否重複
    cursor.execute("SELECT 1 FROM Models WHERE model_name = %s", (name,))
    if cursor.fetchone():
        cursor.close()
        return jsonify({"error": f"模型名稱 '{name}' 已存在，請重新命名"}), 400

    # 處理事件欄位
    event_items = [e.strip() for e in raw_event.split(",") if e.strip()]
    if not event_items:
        return jsonify({"error": "事件格式錯誤，請以逗號分隔"}), 400
    event_type = ",".join(event_items)

    # 檔案處理
    file_py = request.files.get("py")
    file_pt = request.files.get("pt")

    def allowed_file(filename, allowed_exts):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_exts

    if not file_py or not allowed_file(file_py.filename, ALLOWED_MODEL_EXTENSIONS):
        return jsonify({"error": f"缺少或不支援的 py 檔案，允許：{', '.join(ALLOWED_MODEL_EXTENSIONS)}"}), 400
    if not file_pt or not allowed_file(file_pt.filename, ALLOWED_MODEL_EXTENSIONS):
        return jsonify({"error": f"缺少或不支援的 pt 檔案，允許：{', '.join(ALLOWED_MODEL_EXTENSIONS)}"}), 400

    # 建立模型資料夾
    model_folder = os.path.join(MODEL_UPLOAD_FOLDER, name)
    if os.path.exists(model_folder):
        cursor.close()
        return jsonify({"error": f"模型資料夾 '{name}' 已存在，請確認是否命名重複"}), 400
    os.makedirs(model_folder)

    # 儲存檔案
    filepath_py = os.path.join(model_folder, "model.py")
    filepath_pt = os.path.join(model_folder, "model.pt")
    file_py.save(filepath_py)
    file_pt.save(filepath_pt)

    model_path = json.dumps({"py": filepath_py, "pt": filepath_pt})

    # 寫入 Models 資料表
    cursor.execute("""
        INSERT INTO Models (model_name, model_version, event_type, model_path)
        VALUES (%s, %s, %s, %s)
    """, (name, version, event_type, model_path))
    model_id = cursor.lastrowid

    # 寫入 Events 資料表（逐筆 event_name）
    for event_name in event_items:
        cursor.execute("""
            INSERT INTO Events (event_name, model_id)
            VALUES (%s, %s)
        """, (event_name, model_id))

    db.commit()
    cursor.close()

    return jsonify({"message": "模型新增成功", "model_id": model_id}), 200

#==================== 刪除模型 ====================
@app.route('/model/delete', methods=["DELETE"])
def delete_model():
    data = request.get_json()
    token = data.get("token", "")
    model_id = data.get("model_id")
    is_valid, payload = verify_admin_token(token)
    if not is_valid:
        return jsonify({"error": payload}), 401
    if not payload.get("is_admin"):
        return jsonify({"error": "只有管理者可以刪除模型"}), 403
    if not model_id:
        return jsonify({"error": "缺少 model_id"}), 400

    cursor = db.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM Models WHERE model_id = %s", (model_id,))
    model = cursor.fetchone()

    if not model:
        cursor.close()
        return jsonify({"error": "找不到該模型"}), 404

    model_name = model["model_name"]
    model_folder = os.path.join(UPLOAD_FOLDER, model_name)
    if os.path.exists(model_folder):
        try:
            shutil.rmtree(model_folder)
        except Exception as e:
            print(f"刪除資料夾失敗: {e}")

    cursor.execute("DELETE FROM EventProjectRelations WHERE event_id IN (SELECT event_id FROM Events WHERE model_id = %s)", (model_id,))
    cursor.execute("DELETE FROM Events WHERE model_id = %s", (model_id,))
    cursor.execute("DELETE FROM Models WHERE model_id = %s", (model_id,))
    db.commit()
    cursor.close()

    return '', 200

#==================== 修改模型 ====================
@app.route('/model/update', methods=["POST"])
def update_model():
    print("收到的欄位：", request.form.to_dict())  # Debug: 確認收到的欄位
    print("收到的檔案：", list(request.files.keys()))  # Debug: 確認收到的檔案

    token = request.form.get("token", "")
    is_valid, payload = verify_admin_token(token)
    if not is_valid:
        return jsonify({"error": payload}), 401
    if not payload.get("is_admin"):
        return jsonify({"error": "只有管理者可以修改模型"}), 403

    model_id = request.form.get("model_id", "").strip()
    if not model_id:
        return jsonify({"error": "缺少 model_id"}), 400
        
    model_event_info = json.loads(request.form.get("model_event_info", "{}"))
    name = model_event_info.get("name", "").strip()
    version = model_event_info.get("version", "").strip()
    raw_event = model_event_info.get("event", [])
    event_type = ",".join(raw_event) if raw_event else ""

    file_py = request.files.get("py")
    file_pt = request.files.get("pt")

    cursor = db.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM Models WHERE model_id = %s", (model_id,))
    model = cursor.fetchone()
    if not model:
        cursor.close()
        return jsonify({"error": "找不到該模型"}), 404

    old_model_name = model["model_name"]
    old_model_path = json.loads(model["model_path"])
    old_folder = os.path.join(UPLOAD_FOLDER, old_model_name)
    new_folder = os.path.join(UPLOAD_FOLDER, name or old_model_name)

    if name and name != old_model_name and os.path.exists(old_folder):
        shutil.move(old_folder, new_folder)
    else:
        os.makedirs(new_folder, exist_ok=True)

    filepath_py = os.path.join(new_folder, "model.py")
    filepath_pt = os.path.join(new_folder, "model.pt")

    if file_py and allowed_file(file_py.filename):
        if os.path.exists(filepath_py):
            os.remove(filepath_py)
        file_py.save(filepath_py)
        old_model_path["py"] = filepath_py

    if file_pt and allowed_file(file_pt.filename):
        if os.path.exists(filepath_pt):
            os.remove(filepath_pt)
        file_pt.save(filepath_pt)
        old_model_path["pt"] = filepath_pt

    model_path_json = json.dumps(old_model_path)
    update_fields = {
        "model_name": name,
        "model_version": version,
        "event_type": event_type,
        "model_path": model_path_json
    }

    set_clause = ", ".join(f"{k} = %s" for k in update_fields)
    values = list(update_fields.values())
    values.append(model_id)
    
    cursor.execute(f"""
        UPDATE Models
        SET {set_clause}
        WHERE model_id = %s
    """, tuple(values))
    
    db.commit()
    cursor.execute("SELECT * FROM Models WHERE model_id = %s", (model_id,))
    updated_model = cursor.fetchone()

    cursor.close()

    if updated_model:
        return '', 200
    else:
        return jsonify({"error": "更新後的模型資料無法查詢"}), 500
        
#==================== 讀取模型(使用者、管理者都可用) ====================
@app.route('/model', methods=["POST"])
def list_models():
    data = request.get_json()
    token = data.get("token", "")
    is_valid, payload = verify_token(token)
    if not is_valid:
        return jsonify({"error": payload}), 401

    is_admin = payload.get("is_admin", False)

    with db.cursor(pymysql.cursors.DictCursor) as cursor:
        if is_admin:
            cursor.execute("SELECT model_id, model_name, model_version, event_type, model_path FROM Models")
        else:
            cursor.execute("SELECT model_id, model_name, model_version, event_type FROM Models")

        models = cursor.fetchall()

    return jsonify({"models": models}), 200

#新增專案
@app.route('/project/create', methods=['POST'])
def create_project():
    data = request.get_json()
    token = data.get('token', '')
    project_name = data.get('project_name', '').strip()
    camera_id = data.get('camera_id')
    start_time = data.get('start_time')
    status = str(data.get('status')).strip()
    contact_ids = data.get('contacts_ids', [])
    model_ids = data.get('model_ids', [])
    event_items = data.get('event_ids', [])

    is_valid, payload = verify_token(token)
    if not is_valid:
        return jsonify({"error": payload}), 401

    user_id = payload.get('user_id')
    if not (project_name and camera_id and start_time and status in ('0', '1')):
        return jsonify({"error": "缺少必要欄位或 status 格式錯誤"}), 400

    cursor = db.cursor(pymysql.cursors.DictCursor)

    cursor.execute("""
        SELECT device_id FROM Cameras WHERE camera_id = %s AND user_id = %s
    """, (camera_id, user_id))
    cam_row = cursor.fetchone()

    if not cam_row:
        cursor.close()
        return jsonify({"error": "攝影機不存在或不屬於此使用者"}), 403

    device_id = cam_row['device_id']
    if not device_id:
        cursor.close()
        return jsonify({"error": "攝影機尚未綁定裝置，無法建立專案"}), 400

    cursor.execute("""
        SELECT user_id FROM Devices WHERE device_id = %s
    """, (device_id,))
    device_row = cursor.fetchone()
    if not device_row or device_row['user_id'] != user_id:
        cursor.close()
        return jsonify({"error": "裝置不存在或不屬於此使用者"}), 403

    cursor.execute("""
        SELECT 1 FROM Projects WHERE device_id = %s
    """, (device_id,))
    if cursor.fetchone():
        cursor.close()
        return jsonify({"error": "該裝置已被其他專案使用，請先解除綁定"}), 403

    start_time_json = json.dumps(start_time)

    cursor.execute("""
        INSERT INTO Projects (project_name, camera_id, user_id, device_id, start_time, status)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (project_name, camera_id, user_id, device_id, start_time_json, status))
    project_id = cursor.lastrowid

    for contact_id in contact_ids:
        cursor.execute("SELECT 1 FROM Contacts WHERE contact_id = %s AND user_id = %s", (contact_id, user_id))
        if cursor.fetchone():
            cursor.execute("""
                INSERT INTO ContactProjectRelations (contact_id, project_id)
                VALUES (%s, %s)
            """, (contact_id, project_id))

    for model_id in model_ids:
        cursor.execute("SELECT 1 FROM Models WHERE model_id = %s", (model_id,))
        if cursor.fetchone():
            cursor.execute("""
                INSERT INTO ModelProjectRelations (model_id, project_id)
                VALUES (%s, %s)
            """, (model_id, project_id))

    for event_item in event_items:
        if isinstance(event_item, int):
            event_id = event_item
            custom_msg = None
        elif isinstance(event_item, dict):
            event_id = event_item.get("id")
            custom_msg = event_item.get("message")
        else:
            continue

        if not event_id:
            continue

        cursor.execute("SELECT event_name FROM Events WHERE event_id = %s", (event_id,))
        row = cursor.fetchone()
        if not row:
            continue

        notification_content = custom_msg or row['event_name']
        cursor.execute("""
            INSERT INTO EventProjectRelations (event_id, project_id, notification_content)
            VALUES (%s, %s, %s)
        """, (event_id, project_id, notification_content))

    db.commit()
    cursor.close()
    return '', 200

#刪除專案
@app.route('/project/delete', methods=["DELETE"])
def delete_project():
    data = request.get_json()
    token = data.get('token', '')
    project_id = data.get('project_id')

    if not project_id:
        return jsonify({"error": "缺少 project_id"}), 400

    is_valid, payload = verify_token(token)
    if not is_valid:
        return jsonify({"error": payload}), 401

    user_id = payload.get('user_id')
    cursor = db.cursor()

    cursor.execute("""
        SELECT 1 FROM Projects 
        WHERE project_id = %s AND user_id = %s
    """, (project_id, user_id))
    if not cursor.fetchone():
        cursor.close()
        return jsonify({"error": "專案不存在或無權限"}), 404

    cursor.execute("DELETE FROM ContactProjectRelations WHERE project_id = %s", (project_id,))
    cursor.execute("DELETE FROM ModelProjectRelations WHERE project_id = %s", (project_id,))
    cursor.execute("DELETE FROM EventProjectRelations WHERE project_id = %s", (project_id,))
    cursor.execute("DELETE FROM Projects WHERE project_id = %s", (project_id,))

    db.commit()
    cursor.close()
    return '', 200

#修改專案
@app.route('/project/update', methods=["POST"])
def update_project():
    data = request.get_json()
    token = data.get('token', '')
    project_id = data.get('project_id')

    if not project_id:
        return jsonify({"error": "缺少 project_id"}), 400

    is_valid, payload = verify_token(token)
    if not is_valid:
        return jsonify({"error": payload}), 401

    user_id = payload.get('user_id')
    cursor = db.cursor(pymysql.cursors.DictCursor)

    cursor.execute("SELECT * FROM Projects WHERE project_id = %s AND user_id = %s", (project_id, user_id))
    project = cursor.fetchone()
    if not project:
        cursor.close()
        return jsonify({"error": "專案不存在或無權限"}), 404

    project_name = data.get('project_name')
    camera_id = data.get('camera_id')
    start_time = data.get('start_time')
    contact_ids = data.get('contact_ids')
    model_ids = data.get('model_ids')
    event_items = data.get('event_ids')
    status = data.get('status')

    update_fields = []
    params = []

    if camera_id:
        cursor.execute("SELECT device_id FROM Cameras WHERE camera_id = %s AND user_id = %s", (camera_id, user_id))
        camera_row = cursor.fetchone()
        if not camera_row:
            cursor.close()
            return jsonify({"error": "攝影機不存在或不屬於此使用者"}), 403

        if not camera_row["device_id"]:
            cursor.close()
            return jsonify({"error": "此攝影機尚未綁定裝置，請先綁定裝置"}), 400

        device_id = camera_row["device_id"]

        # 檢查裝置是否被其他專案使用
        cursor.execute("SELECT 1 FROM Projects WHERE device_id = %s AND project_id != %s", (device_id, project_id))
        if cursor.fetchone():
            cursor.close()
            return jsonify({"error": "該裝置已被其他專案使用"}), 403

        update_fields.append("camera_id = %s")
        params.append(camera_id)

        update_fields.append("device_id = %s")
        params.append(device_id)

    if project_name:
        update_fields.append("project_name = %s")
        params.append(project_name)

    if start_time:
        update_fields.append("start_time = %s")
        params.append(json.dumps(start_time))

    if status is not None:
        update_fields.append("status = %s")
        params.append(str(status))

    if update_fields:
        params.append(project_id)
        cursor.execute(f"""
            UPDATE Projects
            SET {', '.join(update_fields)}
            WHERE project_id = %s
        """, params)

    if contact_ids is not None:
        cursor.execute("DELETE FROM ContactProjectRelations WHERE project_id = %s", (project_id,))
        for contact_id in contact_ids:
            cursor.execute("SELECT 1 FROM Contacts WHERE contact_id = %s AND user_id = %s", (contact_id, user_id))
            if cursor.fetchone():
                cursor.execute("""
                    INSERT INTO ContactProjectRelations (contact_id, project_id)
                    VALUES (%s, %s)
                """, (contact_id, project_id))

    if model_ids is not None:
        cursor.execute("DELETE FROM ModelProjectRelations WHERE project_id = %s", (project_id,))
        for model_id in model_ids:
            cursor.execute("SELECT 1 FROM Models WHERE model_id = %s", (model_id,))
            if cursor.fetchone():
                cursor.execute("""
                    INSERT INTO ModelProjectRelations (model_id, project_id)
                    VALUES (%s, %s)
                """, (model_id, project_id))

    if event_items is not None:
        cursor.execute("DELETE FROM EventProjectRelations WHERE project_id = %s", (project_id,))
        for event_item in event_items:
            if isinstance(event_item, int):
                event_id = event_item
                custom_msg = None
            elif isinstance(event_item, dict):
                event_id = event_item.get("id")
                custom_msg = event_item.get("message")
            else:
                continue

            if not event_id:
                continue

            cursor.execute("SELECT event_name FROM Events WHERE event_id = %s", (event_id,))
            row = cursor.fetchone()
            if not row:
                continue

            notification_content = custom_msg or row['event_name']
            cursor.execute("""
                INSERT INTO EventProjectRelations (event_id, project_id, notification_content)
                VALUES (%s, %s, %s)
            """, (event_id, project_id, notification_content))

    db.commit()
    cursor.close()
    return '', 200

#讀取專案
@app.route('/project', methods=["GET"])
def read_project():
    data = request.get_json()
    token = data.get('token', '')

    is_valid, payload = verify_token(token)
    if not is_valid:
        return jsonify({"error": payload}), 401

    user_id = payload.get('user_id')
    cursor = db.cursor(pymysql.cursors.DictCursor)

    cursor.execute("""
        SELECT project_id, project_name, camera_id, device_id, start_time, status
        FROM Projects
        WHERE user_id = %s
    """, (user_id,))
    projects = cursor.fetchall()
    if not projects:
        cursor.close()
        return jsonify({"error": "該使用者沒有任何專案"}), 404

    all_project_details = []

    for project in projects:
        project_id = project['project_id']
        camera_id = project['camera_id']
        device_id = project['device_id']

        cursor.execute("""
            SELECT contact_id, contact_name 
            FROM Contacts
            WHERE user_id = %s
            AND contact_id IN (
                SELECT contact_id FROM ContactProjectRelations WHERE project_id = %s
            )
        """, (user_id, project_id))
        contacts = cursor.fetchall()

        cursor.execute("""
            SELECT m.model_id, m.model_name
            FROM Models m
            JOIN ModelProjectRelations mpr ON m.model_id = mpr.model_id
            WHERE mpr.project_id = %s
        """, (project_id,))
        models = cursor.fetchall()

        cursor.execute("""
            SELECT e.event_id, e.event_name
            FROM Events e
            JOIN EventProjectRelations epr ON e.event_id = epr.event_id
            WHERE epr.project_id = %s
        """, (project_id,))
        events = cursor.fetchall()

        camera_name = None
        if camera_id:
            cursor.execute("SELECT camera_name FROM Cameras WHERE camera_id = %s", (camera_id,))
            camera = cursor.fetchone()
            if camera:
                camera_name = camera['camera_name']

        device_name = None
        if device_id:
            cursor.execute("SELECT Model FROM Devices WHERE device_id = %s", (device_id,))
            device = cursor.fetchone()
            if device:
                device_name = device['Model']

        project_details = {
            "project_id": project_id,
            "project_name": project['project_name'],
            "camera_id": camera_id,
            "camera_name": camera_name,
            "device_id": device_id,
            "device_name": device_name,
            "start_time": json.loads(project['start_time']),
            "status": project['status'],
            "contact_ids": [c['contact_id'] for c in contacts],
            "contact_names": [c['contact_name'] for c in contacts],
            "model_ids": [m['model_id'] for m in models],
            "model_names": [m['model_name'] for m in models],
            "event_ids": [e['event_id'] for e in events],
            "event_names": [e['event_name'] for e in events]
        }

        all_project_details.append(project_details)

    cursor.close()
    return jsonify(all_project_details), 200

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
    cursor.execute("""
        SELECT p.project_id, p.start_time, p.camera_id, p.device_id, d.Model AS device_model, c.rtsp_url
        FROM Projects p
        LEFT JOIN Devices d ON p.device_id = d.device_id
        LEFT JOIN Cameras c ON p.camera_id = c.camera_id
        WHERE p.status = 1
    """)
    project_rows = cursor.fetchall()

    projects = []

    for row in project_rows:
        project_id = row["project_id"]

        cursor.execute("""
            SELECT model_name, model_path
            FROM Models m
            JOIN ModelProjectRelations mpr ON m.model_id = mpr.model_id
            WHERE mpr.project_id = %s
        """, (project_id,))
        model_rows = cursor.fetchall()

        model_names = [m["model_name"] for m in model_rows]
        py_path = pt_path = ""

        for m in model_rows:
            try:
                model_path = json.loads(m["model_path"])
                if not py_path:
                    py_path = model_path.get("py", "").replace("\\", "/")
                if not pt_path:
                    pt_path = model_path.get("pt", "").replace("\\", "/")
            except:
                continue

        cursor.execute("""
            SELECT e.event_name
            FROM Events e
            JOIN EventProjectRelations epr ON e.event_id = epr.event_id
            WHERE epr.project_id = %s
        """, (project_id,))
        event_names = [e["event_name"] for e in cursor.fetchall()]

        try:
            time_ranges = json.loads(row["start_time"])
            if isinstance(time_ranges, dict):
                time_ranges = [time_ranges]
        except:
            time_ranges = []

        projects.append({
            "project_id": project_id,
            "start_time": time_ranges,
            "camera_id": row.get("camera_id"),
            "camera": {"rtsp_url": row.get("rtsp_url", "")},
            "device": {"device_id": row.get("device_id"), "model": row.get("device_model")},
            "model_names": model_names,
            "model_paths": {"py": py_path, "pt": pt_path},
            "events": event_names
        })

    cursor.close()
    return jsonify(projects), 200

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
    cursor.execute("""
        SELECT p.project_id, p.project_name, p.start_time, c.rtsp_url, c.camera_id, c.ip_address AS camera_ip_address,
               d.device_id, d.Model AS device_model
        FROM Projects p
        LEFT JOIN Cameras c ON p.camera_id = c.camera_id
        LEFT JOIN Devices d ON p.device_id = d.device_id
        WHERE p.project_id = %s
    """, (project_id,))
    result = cursor.fetchone()

    if not result:
        cursor.close()
        return jsonify({"error": "找不到該專案"}), 404

    try:
        start_time = json.loads(result["start_time"])
        if isinstance(start_time, dict):
            start_time = [start_time]
    except:
        start_time = []

    cursor.execute("""
        SELECT e.event_name
        FROM Events e
        JOIN EventProjectRelations epr ON e.event_id = epr.event_id
        WHERE epr.project_id = %s
    """, (project_id,))
    events = [row["event_name"] for row in cursor.fetchall()]

    cursor.execute("""
        SELECT model_name, model_path
        FROM Models m
        JOIN ModelProjectRelations mpr ON m.model_id = mpr.model_id
        WHERE mpr.project_id = %s
    """, (project_id,))
    models = cursor.fetchall()

    model_names = [m["model_name"] for m in models]
    py_path = pt_path = ""

    for m in models:
        try:
            model_path = json.loads(m["model_path"])
            if not py_path:
                py_path = model_path.get("py", "").replace("\\", "/")
            if not pt_path:
                pt_path = model_path.get("pt", "").replace("\\", "/")
        except:
            continue

    cursor.close()

    return jsonify({
        "project_id": result["project_id"],
        "project_name": result["project_name"],
        "start_time": start_time,
        "rtsp_url": result["rtsp_url"],
        "camera_id": result["camera_id"],
        "camera_ip_address": result["camera_ip_address"],
        "device": {"device_id": result["device_id"], "model": result["device_model"]},
        "events": events,
        "model_names": model_names,
        "model_paths": {"py": py_path, "pt": pt_path}
    }), 200

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

    cursor.execute("""
        SELECT * FROM Projects 
        WHERE project_id > %s
        ORDER BY project_id ASC
        LIMIT 1
    """, (current_project_id,))
    project = cursor.fetchone()

    if not project:
        cursor.close()
        return jsonify({"message": "沒有下一筆專案"}), 200

    project_id = project['project_id']

    cursor.execute("SELECT rtsp_url FROM Cameras WHERE camera_id = %s", (project['camera_id'],))
    cam = cursor.fetchone()
    rtsp_url = cam['rtsp_url'] if cam else ""

    cursor.execute("SELECT Model FROM Devices WHERE device_id = %s", (project['device_id'],))
    device = cursor.fetchone()
    device_info = {
        "device_id": project["device_id"],
        "model": device["Model"] if device else ""
    }

    cursor.execute("""
        SELECT c.contact_name FROM Contacts c
        JOIN ContactProjectRelations cpr ON c.contact_id = cpr.contact_id
        WHERE cpr.project_id = %s
    """, (project_id,))
    contacts = [row['contact_name'] for row in cursor.fetchall()]

    cursor.execute("""
        SELECT model_name, model_path FROM Models m
        JOIN ModelProjectRelations mpr ON m.model_id = mpr.model_id
        WHERE mpr.project_id = %s
    """, (project_id,))
    models = cursor.fetchall()
    model_names = [m['model_name'] for m in models]
    model_paths = []
    for m in models:
        try:
            path_obj = json.loads(m['model_path'])
            model_paths.append({
                "py": path_obj.get("py", "").replace("\\", "/"),
                "pt": path_obj.get("pt", "").replace("\\", "/")
            })
        except:
            model_paths.append({"py": "", "pt": ""})

    cursor.execute("""
        SELECT event_name FROM Events e
        JOIN EventProjectRelations epr ON e.event_id = epr.event_id
        WHERE epr.project_id = %s
    """, (project_id,))
    events = [row['event_name'] for row in cursor.fetchall()]

    try:
        start_time = json.loads(project['start_time'])
        if isinstance(start_time, dict):
            start_time = [start_time]
    except:
        start_time = []

    cursor.close()

    return jsonify({
        "project_id": project['project_id'],
        "project_name": project['project_name'],
        "camera_id": project['camera_id'],
        "start_time": start_time,
        "camera": {
            "rtsp_url": rtsp_url
        },
        "device": device_info,
        "contacts": contacts,
        "model_names": model_names,
        "model_paths": model_paths,
        "events": events,
        "status": project["status"]
    }), 200

#新增裝置(管理者)
@app.route('/device/create', methods=['POST'])
def create_device():
    data = request.get_json()
    token = data.get("token", "")
    model = data.get("model", "").strip()

    is_valid, payload = verify_admin_token(token)
    if not is_valid:
        return jsonify({"status": "error", "message": payload}), 401

    if not model:
        return jsonify({"status": "error", "message": "缺少 model"}), 400

    device_id = str(uuid.uuid1())
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO Devices (device_id, user_id, Model)
        VALUES (%s, %s, %s)
    """, (device_id, None, model))

    db.commit()
    cursor.close()

    return jsonify({"device_id": device_id}), 200

#查詢裝置(管理者)
@app.route('/admin/device/list', methods=["POST"])
def admin_list_devices():
    data = request.get_json()
    token = data.get("token", "")
    
    is_valid, payload = verify_token(token)
    if not is_valid:
        return jsonify({"error": payload}), 401

    is_admin = payload.get("is_admin", False)
    cursor = db.cursor(pymysql.cursors.DictCursor)

    if is_admin:
        cursor.execute("""
            SELECT device_id, user_id, Model, Manufacture_date
            FROM Devices
        """)
    else:
        cursor.execute("""
            SELECT device_id, Model, Manufacture_date
            FROM Devices
            WHERE user_id IS NULL
        """)

    devices = cursor.fetchall()
    cursor.close()

    return jsonify({"devices": devices}), 200

#修改裝置(管理者)
@app.route('/device/update', methods=['POST'])
def update_device():
    data = request.get_json()
    token = data.get("token", "")
    model = data.get("model", "")
    device_id = data.get("device_id", None)

    if device_id is None:
        return jsonify({"status": "error", "message": "缺少 device_id"}), 400

    is_valid, payload = verify_token(token)
    if not is_valid:
        return jsonify({"status": "error", "message": payload}), 401

    is_admin = payload.get("is_admin", False)
    cursor = db.cursor()

    if not is_admin:
        cursor.execute("SELECT user_id FROM Devices WHERE device_id = %s", (device_id,))
        row = cursor.fetchone()
        if row is None or row[0] != payload["user_id"]:
            cursor.close()
            return jsonify({"status": "error", "message": "您無權修改此裝置"}), 403

    cursor.execute("""
            UPDATE Devices
            SET Model = %s
            WHERE device_id = %s
        """, (model, device_id))

    db.commit()
    cursor.close()

    return '', 200

#刪除裝置(管理者)
@app.route('/admin/device/delete', methods=['DELETE'])
def admin_delete_device():
    data = request.get_json()

    if not data:
        return jsonify({"error": "請提供 JSON 資料"}), 400

    token = data.get("token", "")
    device_id = data.get("device_id")

    if not device_id:
        return jsonify({"error": "缺少 device_id"}), 400

    is_valid, payload = verify_admin_token(token)
    if not is_valid:
        return jsonify({"error": payload}), 401

    cursor = db.cursor()

    cursor.execute("SELECT COUNT(*) FROM Projects WHERE device_id = %s", (device_id,))
    if cursor.fetchone()[0] > 0:
        cursor.close()
        return jsonify({"error": "該裝置已被專案使用，無法刪除"}), 400

    cursor.execute("SELECT device_id FROM Devices WHERE device_id = %s", (device_id,))
    if not cursor.fetchone():
        cursor.close()
        return jsonify({"error": "裝置不存在"}), 404

    cursor.execute("DELETE FROM Devices WHERE device_id = %s", (device_id,))
    db.commit()
    cursor.close()

    return '', 200

#綁定裝置(使用者)
@app.route('/device/bind', methods=['POST'])
def bind_device():
    data = request.get_json()
    token = data.get("token", "")
    device_id = data.get("device_id")

    is_valid, payload = verify_token(token)
    if not is_valid:
        return jsonify({"status": "error", "message": payload}), 401

    user_id = payload["user_id"]

    cursor = db.cursor()
    cursor.execute("""
        SELECT device_id FROM Devices
        WHERE device_id = %s AND user_id IS NULL
    """, (device_id,))
    device = cursor.fetchone()

    if not device:
        cursor.close()
        return jsonify({"status": "error", "message": "裝置不存在或已被綁定"}), 400

    cursor.execute("""
        UPDATE Devices
        SET user_id = %s
        WHERE device_id = %s
    """, (user_id, device_id))

    db.commit()
    cursor.close()

    return '', 200

#刪除裝置(使用者)
@app.route('/device/delete', methods=['DELETE'])
def delete_device():
    data = request.get_json()
    token = data.get("token", "")
    device_id = data.get("device_id")

    is_valid, payload = verify_token(token)
    if not is_valid:
        return jsonify({"status": "error", "message": payload}), 401

    user_id = payload["user_id"]

    cursor = db.cursor(pymysql.cursors.DictCursor)

    cursor.execute("""
        SELECT device_id FROM Devices
        WHERE device_id = %s AND user_id = %s
    """, (device_id, user_id))
    if not cursor.fetchone():
        cursor.close()
        return jsonify({"status": "error", "message": "裝置不存在或不屬於此使用者"}), 403

    cursor.execute("""
        SELECT COUNT(*) AS count FROM Projects
        WHERE device_id = %s
    """, (device_id,))
    if cursor.fetchone()['count'] > 0:
        cursor.close()
        return jsonify({"status": "error", "message": "此裝置正在被專案使用，請先移除專案"}), 400

    cursor.execute("""
        SELECT camera_id FROM Cameras
        WHERE device_id = %s AND user_id = %s
    """, (device_id, user_id))
    cameras = cursor.fetchall()

    for cam in cameras:
        camera_id = cam['camera_id']
        cursor.execute("""
            SELECT COUNT(*) AS count FROM Projects
            WHERE camera_id = %s
        """, (camera_id,))
        if cursor.fetchone()['count'] > 0:
            cursor.close()
            return jsonify({"status": "error", "message": f"攝影機 {camera_id} 已被專案使用，請先解除專案"}), 400

    cursor.execute("""
        DELETE FROM Cameras
        WHERE device_id = %s AND user_id = %s
    """, (device_id, user_id))

    cursor.execute("""
        UPDATE Devices
        SET user_id = NULL
        WHERE device_id = %s AND user_id = %s
    """, (device_id, user_id))

    db.commit()
    cursor.close()

    return '', 200

#查詢裝置(使用者)
@app.route('/device/list', methods=['GET'])
def list_user_devices():
    data = request.get_json()
    token = data.get("token", "")
    is_valid, payload = verify_token(token)
    if not is_valid:
        return jsonify({"status": "error", "message": payload}), 401

    user_id = payload["user_id"]

    cursor = db.cursor(pymysql.cursors.DictCursor)
    cursor.execute("""
        SELECT Manufacture_date, Model
        FROM Devices
        WHERE user_id = %s
    """, (user_id,))
    devices = cursor.fetchall()
    cursor.close()

    return jsonify(devices), 200

@app.route('/events/user', methods=['POST'])
def get_abnormal_events():
    data = request.get_json()
    token = data.get('token', '')
    event_name_filter = data.get('event_name')  
    start_time = data.get('start_time')         
    end_time = data.get('end_time')             

    is_valid, payload = verify_token(token)
    if not is_valid:
        return jsonify({"error": payload}), 401

    user_id = payload.get('user_id')

    cursor = db.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute("SELECT project_id, start_time FROM Projects WHERE user_id = %s", (user_id,))
        projects = cursor.fetchall()

        if not projects:
            return jsonify({"total": 0, "abnormal_events": []}), 200

        project_ids = [project['project_id'] for project in projects]

        base_query = """
            SELECT DISTINCT ae.abnormal_id, e.event_name, m.model_name, ae.occurred_at, p.start_time
            FROM AbnormalEvents ae
            JOIN EventProjectRelations epr ON ae.event_id = epr.event_id
            JOIN Events e ON ae.event_id = e.event_id
            JOIN ModelProjectRelations mpr ON epr.project_id = mpr.project_id
            JOIN Models m ON mpr.model_id = m.model_id
            JOIN Projects p ON epr.project_id = p.project_id
            WHERE epr.project_id IN ({})

        """.format(','.join(['%s'] * len(project_ids)))
        params = project_ids.copy()

        if event_name_filter:
            base_query += " AND e.event_name = %s"
            params.append(event_name_filter)

        if start_time and end_time:
            base_query += " AND ae.occurred_at BETWEEN %s AND %s"
            params.append(start_time)
            params.append(end_time)

        count_query = f"SELECT COUNT(*) as total FROM ({base_query}) as sub"
        cursor.execute(count_query, params)
        total = cursor.fetchone()['total']

        cursor.execute(base_query, params)
        abnormal_events = cursor.fetchall()

        import json
        for event in abnormal_events:
            if 'abnormal_id' in event:
                del event['abnormal_id']
            if 'picture_url' in event:
                del event['picture_url']
            if 'start_time' in event:
                try:
                    event['start'] = json.loads(event['start_time'])
                except (TypeError, json.JSONDecodeError):
                    event['start'] = {}
                del event['start_time']
        
        #print(abnormal_events)
        
        return jsonify({
            "abnormal_events": abnormal_events
        }), 200

    except Exception as e:
        return jsonify({"error": f"異常事件查詢失敗: {str(e)}"}), 500

    finally:
        cursor.close()

@app.route('/events/event_types', methods=['POST'])
def get_event_types():
    data = request.get_json()
    token = data.get('token', '')           

    is_valid, payload = verify_token(token)
    if not is_valid:
        return jsonify({"error": payload}), 401

    user_id = payload.get('user_id')

    cursor = db.cursor(pymysql.cursors.DictCursor)
    try:
        print('if stop here means wrong before query')
        cursor.execute("select e.event_name,m.model_name, m.model_version from events e inner join models m on e.model_id=m.model_id")
        print('if stop here means wrong after query')
        event_types = cursor.fetchall()
        print(event_types)
        if not event_types:
            return jsonify({"total": 0, "event_types": []}), 200
        
        
        return jsonify({
            "event_types": event_types
        }), 200

    except Exception as e:
        return jsonify({"error": f"事件類型查詢失敗: {str(e)}"}), 500

    finally:
        cursor.close()

#加好友
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    for event in data.get("events", []):
        if event.get("type") == "follow":
            messaging_user_id = event["source"]["userId"]
            print("✅ 使用者加好友，Messaging userId:", messaging_user_id)
    return "OK"

#綁定
@app.route("/bind_message_line_id", methods=["POST"])
def bind_message_line_id():
    data = request.get_json()
    token = data.get("token", "")
    messaging_user_id = data.get("messaging_user_id", "")

    is_valid, payload = verify_token(token)
    if not is_valid:
        return jsonify({"error": payload}), 401

    user_id = payload.get("user_id")
    if not user_id or not messaging_user_id:
        return jsonify({"error": "缺少必要欄位"}), 400

    cursor = db.cursor()
    try:
        cursor.execute("""
            UPDATE Users SET message_line_id = %s WHERE user_id = %s
        """, (messaging_user_id, user_id))
        db.commit()
        return jsonify({"message": "Message API 綁定成功"}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()

def shorten_url(long_url):
    api_url = f"https://tinyurl.com/api-create.php?url={long_url}"
    try:
        response = requests.get(api_url, timeout=5)
        if response.status_code == 200:
            return response.text
    except:
        pass
    return long_url

#事件通知
@app.route('/event/abnormal', methods=["POST"])
def create_abnormal_event():
    data = request.get_json()
    token = data.get("token", "")
    is_valid, payload = verify_token(token)
    if not is_valid:
        return jsonify({"error": payload}), 401
    if not payload.get("is_admin"):
        return jsonify({"error": "只有管理者可以發送異常通知"}), 403

    project_id = data.get("project_id")
    event_id = data.get("event_id")
    picture_url = data.get("picture_url", "").strip()

    if not all([project_id, event_id, picture_url]):
        return jsonify({"error": "缺少必要欄位"}), 400

    occurred_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor = db.cursor(pymysql.cursors.DictCursor)

    try:
        cursor.execute("""
            SELECT notification_content 
            FROM EventProjectRelations 
            WHERE project_id = %s AND event_id = %s
        """, (project_id, event_id))
        row = cursor.fetchone()
        if not row:
            cursor.close()
            return jsonify({"error": "找不到通知內容"}), 404

        notification_content = row["notification_content"]

        cursor.execute("SELECT project_name, user_id FROM Projects WHERE project_id = %s", (project_id,))
        project = cursor.fetchone()
        if not project:
            cursor.close()
            return jsonify({"error": "找不到該專案"}), 404

        project_name = project["project_name"]
        owner_id = project["user_id"]

        cursor.execute("""
            SELECT COALESCE(u.message_line_id, u.line_id) AS line_id
            FROM ContactProjectRelations cp
            JOIN Contacts c ON cp.contact_id = c.contact_id AND cp.project_id = %s
            JOIN Users u ON c.user_id = u.user_id
        """, (project_id,))
        contacts = cursor.fetchall()

        cursor.execute("""
            SELECT COALESCE(message_line_id, line_id) AS line_id FROM Users WHERE user_id = %s
        """, (owner_id,))
        owner = cursor.fetchone()

        cursor.close()

        line_ids = set()
        if owner and owner.get("line_id"):
            line_ids.add(owner["line_id"])
        for contact in contacts:
            if contact.get("line_id"):
                line_ids.add(contact["line_id"])

        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO AbnormalEvents (project_id, event_id, picture_url, occurred_at)
            VALUES (%s, %s, %s, %s)
        """, (project_id, event_id, picture_url, occurred_at))
        db.commit()
        cursor.close()
        short_url = shorten_url(picture_url)

        message = (
            "⚠️事件通知\n"
            f"專案名稱：{project_name}\n"
            f"事件名稱：{notification_content}\n"
            f"發生時間：{occurred_at}\n"
            f"圖片連結：{short_url}"
        )

        for line_id in line_ids:
            status, resp = send_line_message(line_id, message)
            if status != 200:
                print(f"❌ 通知失敗：{line_id}, 狀態碼: {status}, 回應: {resp}")

        return '', 200

    except Exception as e:
        db.rollback()
        cursor.close()
        return jsonify({"error": f"發送通知失敗: {str(e)}"}), 500

#即時串流(可能要改、因為改成樹梅派)
'''
@app.route('/streaming', methods=['POST'])
def streaming():
    try:
        data = request.get_json()
        token = data.get("token", "")
        is_valid, payload = verify_token(token)
        if not is_valid:
            return jsonify({"error": "無效的 Token"}), 401

        user_id = payload["user_id"]
        camera_id = data.get("camera_id")

        cursor = db.cursor(pymysql.cursors.DictCursor)

        sql = "SELECT * FROM Cameras WHERE camera_id = %s AND user_id = %s"
        cursor.execute(sql, (camera_id, user_id))
        camera = cursor.fetchone()

        if not camera:
            return jsonify({"error": "找不到攝影機資料"}), 404
        if camera['rtsp_url']:
            rtsp_url = camera['rtsp_url']
        else:
            rtsp_url = f"rtsp://{camera['camera_username']}:{camera['camera_password']}@{camera['ip_address']}/live/profile.1"

        output_dir = os.path.join("C:/ip_camera/stream", f"user_{user_id}_cam_{camera_id}")
        os.makedirs(output_dir, exist_ok=True)
        output_m3u8 = os.path.join(output_dir, "index.m3u8")

        if os.path.exists(output_m3u8):
            return jsonify({
                "stream_url": f"/static/stream/user_{user_id}_cam_{camera_id}/index.m3u8"
            }), 200

        cmd = [
            "ffmpeg",
            "-rtsp_transport", "tcp",
            "-i", rtsp_url,
            "-c:v", "copy",
            "-c:a", "copy",
            "-f", "hls",
            "-hls_time", "4",
            "-hls_list_size", "5",
            "-hls_flags", "delete_segments",
            output_m3u8
        ]

        def run_ffmpeg():
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        threading.Thread(target=run_ffmpeg, daemon=True).start()

        return jsonify({
            "rtsp_url": rtsp_url ,
            "stream_url": f"/static/stream/user_{user_id}_cam_{camera_id}/index.m3u8"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
'''

#抓取照片
@app.route('/upload/photo', methods=['POST'])
def upload_photo():
    token = request.form.get('token', '').strip()

    if not token:
        return jsonify({"error": "缺少 Token"}), 400

    is_valid, payload = verify_admin_token(token)
    if not is_valid:
        return jsonify({"error": "無效的 Token"}), 401

    if 'file' not in request.files:
        return jsonify({"error": "未提供檔案"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "檔案名稱為空"}), 400

    if file and allowed_file(file.filename, ALLOWED_PICTURE_EXTENSIONS):
        cleaned_name = clean_filename(file.filename)
        save_path = os.path.join(app.config['PICTURE_UPLOAD_FOLDER'], cleaned_name)
        file.save(save_path)

        return jsonify({
            "filename": cleaned_name,
            "path": save_path.replace("\\", "/")
        }), 200

    return jsonify({"error": "不支援的檔案格式"}), 400


#測試
@app.route('/generate_test_token', methods=['GET'])
def generate_test_token():
    line_user_id = 'U123456789012345679'
    token = generate_token('', '', line_user_id)
    return jsonify({"token": token})
@app.route('/test_callback', methods=['GET'])
def test_callback():
    line_user_id = 'Ua1fb77086eff14f21babde9857491d79'

    cursor = db.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM users WHERE line_id = %s", (line_user_id,))
    result = cursor.fetchone()

    if result:
        user_id = result["user_id"]
        name = result["user_name"]
        token = generate_token(user_id, name, line_user_id)

        cursor.execute("""
    UPDATE users 
    SET token = %s
    WHERE user_id = %s
    """, (token, user_id))
        db.commit()
        cursor.close()

        return jsonify({
            "token": token
        })
    else:
        return jsonify({"message": "找不到使用者"}), 404

if __name__ == '__main__':
    app.run(debug=True)
