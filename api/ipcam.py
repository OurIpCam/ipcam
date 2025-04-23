from flask import Flask, make_response,redirect, request, session, url_for, send_file, render_template,jsonify
from flask_cors import CORS
import requests
import os
import pymysql
import jwt
import datetime
import uuid

app = Flask(__name__)
app.secret_key = os.urandom(24) 
CORS(app, supports_credentials =True)
db = pymysql.connect(host='localhost', 
                     user='root', 
                     password='c107', 
                     database='ipcam')

# LINE Login Credentials
LINE_CLIENT_ID = "2006911351"
LINE_CLIENT_SECRET = "f049a5c4224180099cd88dc599745cdf"
REDIRECT_URI = "http://210.240.202.108:5000/callback"

# LINE Authorization URL
LINE_AUTH_URL = "https://access.line.me/oauth2/v2.1/authorize"
LINE_TOKEN_URL = "https://api.line.me/oauth2/v2.1/token"
LINE_PROFILE_URL = "https://api.line.me/v2/profile"

SECRET_KEY = "11124214"
TOKEN_EXPIRY = 480
token_storage = {}
def generate_token(user_id, name, line_user_id, picture_url=''):
    expiration_time = datetime.datetime.now() + datetime.timedelta(minutes=TOKEN_EXPIRY)
    payload = {
        "user_id": user_id,
        "name": name,
        "line_user_id": line_user_id,
        "picture_url": picture_url,
        "exp": expiration_time
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token, expiration_time, payload
# 驗證 JWT Token
def verify_token(token):
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return True, decoded
    except jwt.ExpiredSignatureError:
        return False, "Token 過期"
    except jwt.InvalidTokenError:
        return False, "無效的 Token"


@app.route('/login')
def callback():
    code = request.args.get('code')
    if not code:
        return "Error: No code received", 400

    token_data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'client_id': LINE_CLIENT_ID,
        'client_secret': LINE_CLIENT_SECRET
    }

    token_response = requests.post(LINE_TOKEN_URL, data=token_data)
    token_json = token_response.json()

    if 'access_token' not in token_json:
        return "Error retrieving access token", 400

    access_token = token_json['access_token']
    headers = {'Authorization': f'Bearer {access_token}'}
    profile_response = requests.get(LINE_PROFILE_URL, headers=headers)
    profile_json = profile_response.json()

    line_user_id = profile_json.get('userId')
    if not line_user_id:
        return "Error: userId not found", 400

    cursor = db.cursor()
    cursor.execute("SELECT user_id, user_name FROM users WHERE line_id = %s", (line_user_id,))
    result = cursor.fetchone()

    if result:
        user_id, name = result
        token, expiration_time, _ = generate_token(user_id, name, line_user_id)

        cursor.execute("UPDATE users SET token = %s, token_expiration = %s WHERE user_id = %s",
                       (token, expiration_time, user_id))
        db.commit()
        cursor.close()

        #return jsonify({"message": "登入成功", "token": token})
        return redirect(f'http://210.240.202.108/main.html?token={token}')
    else:
        token, _, _ = generate_token('', '', line_user_id)
        return redirect(f'http://210.240.202.108/inputName.html?token={token}')#此token有Line_id

#設定名字、生成user_id
@app.route('/set_name', methods=['POST'])
def set_name():
    data = request.get_json()
    token = data.get('token', '')
    username = data.get('username', '').strip()

    is_valid, payload = verify_token(token)
    if not is_valid or not payload.get('line_user_id'):
        return jsonify({"error": "Token 驗證失敗"}), 401

    line_user_id = payload['line_user_id']
    if not username:
        return jsonify({"error": "請輸入姓名"}), 400

    user_id = uuid.uuid4().hex
    new_token, expiration_time, _ = generate_token(user_id, username, line_user_id)

    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO users (user_id, line_id, user_name, token, token_expiration)
        VALUES (%s, %s, %s, %s, %s)
    """, (user_id, line_user_id, username, new_token, expiration_time))
    db.commit()
    cursor.close()

    return '', 200


#登出
@app.route('/logout')
def logout():
    data = request.get_json()
    token = data.get('token', '')
    is_valid, payload = verify_token(token)

    if not is_valid:
        return jsonify({"error": "無效的 Token"}), 401

    user_id = payload.get('user_id', '')

    cursor = db.cursor()
    cursor.execute("UPDATE users SET token = NULL, token_expiration = NULL WHERE user_id = %s", (user_id,))
    db.commit()
    cursor.close()

    return jsonify({"message": "登出成功"})

#取得使用者
@app.route('/user', methods=["GET"])
def user():
    token = request.args.get('token', '') 
    is_valid, payload = verify_token(token)

    if not is_valid:
        return jsonify({"error": payload}), 401

    user_id = payload.get("user_id")
    name = payload.get("name")
    line_user_id = payload.get("line_user_id")
    picture_url = payload.get("picture_url", "")
    exp = payload.get("exp")

    expiration_time = datetime.datetime.utcfromtimestamp(exp).strftime('%Y-%m-%d %H:%M:%S')

    return jsonify({
        "user_id": user_id,
        "name": name,
        "line_user_id": line_user_id,
        "picture_url": picture_url,
        "token_expiration": expiration_time
    })


#新增聯絡人
@app.route('/contact/create', methods=["POST"])
def create_contact():
    data = request.get_json()
    token = data.get('token', '')
    is_valid, payload = verify_token(token)
    
    if not is_valid:
        return jsonify({"error": payload}), 401

    current_user_id = payload.get("user_id")

    data = request.json
    contact_user_id = data.get("contact_user_id")
    
    if not contact_user_id:
        return jsonify({"error": "Missing contact_user_id"}), 400

    if contact_user_id == current_user_id:
        return jsonify({"error": "Cannot add yourself as a contact"}), 400

    cursor = db.cursor(pymysql.cursors.DictCursor)

    cursor.execute("SELECT user_id, user_name FROM Users WHERE user_id = %s", (contact_user_id,))
    user = cursor.fetchone()

    if not user:
        return jsonify({"error": "User not found"}), 404

    contact_name = user["user_name"]

    contact_id = uuid.uuid4().hex

    try:
        cursor.execute("""
            INSERT INTO Contacts (contact_id, user_id, contact_name)
            VALUES (%s, %s, %s)
        """, (contact_id, current_user_id, contact_name))
        db.commit()
    except pymysql.IntegrityError:
        return jsonify({"error": "This contact already exists"}), 409

    return jsonify({
        "message": "聯絡人新增成功",
        "contact": {
            "contact_id": contact_id,
            "user_id": current_user_id,
            "contact_name": contact_name
        }
    }), 201

#刪除聯絡人
@app.route('/contact/delete', methods=["DELETE"])
def delete_contact():
    data = request.get_json()
    token = data.get('token', '')
    if not token:
        return jsonify({"error": "Missing token"}), 401
    is_valid, payload = verify_token(token)
    if not is_valid:
        return jsonify({"error": payload}), 401
    current_user_id = payload.get("user_id")
    data = request.json
    contact_id = data.get("contact_id")
    if not contact_id:
        return jsonify({"error": "Missing contact_id"}), 400

    cursor = db.cursor(pymysql.cursors.DictCursor)
    cursor.execute(
        "SELECT * FROM Contacts WHERE contact_id = %s AND user_id = %s",
        (contact_id, current_user_id)
    )
    contact = cursor.fetchone()
    if not contact:
        return jsonify({"error": "Contact not found or no permission"}), 404
    cursor.execute(
        "DELETE FROM Contacts WHERE contact_id = %s AND user_id = %s",
        (contact_id, current_user_id)
    )
    db.commit()

    return jsonify({"message": "聯絡人刪除成功"})

#讀取聯絡人
@app.route('/contact/list', methods=["GET"])
def list_contacts():
    data = request.get_json()
    token = data.get('token', '')
    is_valid, payload = verify_token(token)

    if not is_valid:
        return jsonify({"error": payload}), 401

    current_user_id = payload.get("user_id")

    cursor = db.cursor(pymysql.cursors.DictCursor)

    # 查詢所有聯絡人
    cursor.execute("SELECT contact_id, contact_name FROM Contacts WHERE user_id = %s", (current_user_id,))
    contacts = cursor.fetchall()

    total = len(contacts)

    return jsonify({
        "total": total,
        "contacts": contacts
    })

#修改聯絡人
@app.route('/contact/update', methods=["PUT"])
def update_contact_name():
    data = request.get_json()
    token = data.get('token', '')
    is_valid, payload = verify_token(token)
    if not is_valid:
        return jsonify({"error": payload}), 401
    current_user_id = payload.get("user_id")
    data = request.get_json()
    contact_id = data.get("contact_id")
    new_name = data.get("contact_name", "").strip()
    if not contact_id or not new_name:
        return jsonify({"error": "Missing contact_id or contact_name"}), 400
    cursor = db.cursor(pymysql.cursors.DictCursor)
    cursor.execute(
        "SELECT * FROM Contacts WHERE contact_id = %s AND user_id = %s",
        (contact_id, current_user_id)
    )
    contact = cursor.fetchone()
    if not contact:
        return jsonify({"error": "Contact not found or no permission"}), 404
    cursor.execute(
        "UPDATE Contacts SET contact_name = %s WHERE contact_id = %s AND user_id = %s",
        (new_name, contact_id, current_user_id)
    )
    db.commit()
    return jsonify({"message": "聯絡人名字修改成功", "contact_id": contact_id, "new_name": new_name})



'''
@app.route('/')
def home():
    if 'user' in session:
        user = session['user']
        return render_template("main.html", display_name=user.get('displayName', 'Unknown User'), picture_url=user.get('pictureUrl', ''))
    return render_template("login.html")
'''
    
if __name__ == '__main__':
    app.run(debug=True)
