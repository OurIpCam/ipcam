from flask import Flask, make_response,redirect, request, session, url_for, send_file, render_template,jsonify
from flask_cors import CORS
import requests
import os
import pymysql
import jwt
import datetime
import uuid

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secret key for session handling
CORS(app, supports_credentials =True)
db = pymysql.connect(host='localhost', 
                     user='root', 
                     password='c107', 
                     database='ipcam')

# LINE Login Credentials
LINE_CLIENT_ID = "2006911351"
LINE_CLIENT_SECRET = "f049a5c4224180099cd88dc599745cdf"
REDIRECT_URI = "http://127.0.0.1:5000/callback"

# LINE Authorization URL
LINE_AUTH_URL = "https://access.line.me/oauth2/v2.1/authorize"
LINE_TOKEN_URL = "https://api.line.me/oauth2/v2.1/token"
LINE_PROFILE_URL = "https://api.line.me/v2/profile"

SECRET_KEY = "11124214"
TOKEN_EXPIRY = 480
token_storage = {}
def generate_token(payload):
    expiration_time = datetime.datetime.now() + datetime.timedelta(minutes=TOKEN_EXPIRY)
    payload['exp'] = expiration_time
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    token_storage[token] = expiration_time
    return token, expiration_time

# 驗證 JWT Token
def verify_token(token):
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        if token not in token_storage:
            return None, "Token 已被登出或無效"
        return decoded, None  
    except jwt.ExpiredSignatureError:
        if token in token_storage:
            del token_storage[token]
        return None, "Token 過期"
    except jwt.InvalidTokenError:
        return None, "無效的 Token"

"""回傳templates/auth/index.html(選擇不同方式登入頁面)"""
@app.route('/')
def index():
    return render_template('auth/index.html')

"""回傳templates/auth/login.html(Line登入頁面)"""
@app.route('/login')
def login():
    return render_template('auth/login.html')

@app.route('/home') #, methods = ['']
def home():
    token = request.cookies.get('token')
    if not token:
        return redirect(url_for('index'))
    decoded, err = verify_token(token)
    if err:
        return redirect(url_for('index'))
    return render_template("main.html",
                           picture_url=decoded.get('pictureUrl', ''),
                           user_id=decoded.get('user_id', decoded.get('line_userId', 'Unknown')),
                           name=decoded.get('name', ''))


"""回傳Line官方登入頁面"""
@app.route('/login/Line')
def loginLine():
    """ Redirect to LINE login page """
    login_url = f"{LINE_AUTH_URL}?response_type=code&client_id={LINE_CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope=profile%20openid%20email&state=123456"
    #print("Generated Login URL:", login_url)  # Debugging
    return redirect(login_url)

@app.route('/callback', methods=['GET'])
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

    # 檢查回應狀態碼
    if token_response.status_code != 200:
        return f"Error: Failed to retrieve access token, status code {token_response.status_code}, response: {token_response.text}", 400

    token_json = token_response.json()

    if 'access_token' not in token_json:
        return f"Error retrieving access token. Response: {token_json}", 400

    access_token = token_json['access_token']
    expires_in = token_json['expires_in']

    headers = {'Authorization': f'Bearer {access_token}'}
    profile_response = requests.get(LINE_PROFILE_URL, headers=headers)
    
    if profile_response.status_code != 200:
        return f"Error: Failed to retrieve profile, status code {profile_response.status_code}, response: {profile_response.text}", 400
    
    profile_json = profile_response.json()

    user_id = profile_json.get('userId', 'Unknown')
    picture_url = profile_json.get('pictureUrl', '')

    jwt_payload = {
    'userId': user_id,
    'pictureUrl': picture_url,
    'access_token': access_token,
    'expires_in': expires_in
    }

    jwt_token = generate_token(jwt_payload)
    response = make_response(redirect(url_for('home')))
    response.set_cookie('token',  jwt_token)
    print(f"Token data: {token_data}")
    print(f"Token response: {token_response.text}")
    return response

#登入
@app.route('/login/user', methods=['POST'])
def login_user():
    token = request.cookies.get('token')
    if not token:
        return jsonify({"error": "User not logged in via JWT"})
    jwt_payload, err = verify_token(token)
    if err:
        return jsonify({"error": err})

    line_id = jwt_payload.get('userId')
    if not line_id:
        return jsonify({"error": "LINE userId not found in token"})

    cursor = db.cursor()
    cursor.execute("SELECT * FROM Users WHERE line_id = %s", (line_id,))
    user_record = cursor.fetchone()
    if user_record:
        user_id = user_record[0] 
        new_token, token_expiry = generate_token({'user_id': user_id,
                                                   'userId': line_id,
                                                   'pictureUrl': jwt_payload.get('pictureUrl')})
        cursor.execute("""
            UPDATE Users SET token = %s, token_expiration = %s WHERE user_id = %s
        """, (new_token, token_expiry, user_id))
        db.commit()
        message = "登入成功"
    else:
        data = request.get_json()
        user_name = data.get("name", "").strip()
        if not user_name:
            cursor.close()
            return jsonify({"error": "Name is required for first login"})
        user_id = uuid.uuid4().hex 
        new_token, token_expiry = generate_token({'user_id': user_id,
                                                   'userId': line_id,
                                                   'pictureUrl': jwt_payload.get('pictureUrl')})
        cursor.execute("""
            INSERT INTO Users (user_id, line_id, user_name, token, token_expiration, created_at) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, line_id, user_name, new_token, token_expiry, datetime.datetime.now()))
        db.commit()
        message = "New user created."
        jwt_payload['user_id'] = user_id  

    new_jwt = jwt.encode(jwt_payload, SECRET_KEY, algorithm="HS256")
    response = make_response(jsonify({
        "message": message,
        "user_id": user_id,
        "token": new_token,
        "token_expiration": token_expiry.strftime("%Y-%m-%d %H:%M:%S")}))
    response.set_cookie('token', new_jwt)
    cursor.close()
    return response

#測試用
'''
@app.route('/test/token')
def test_token():
    jwt_payload = {
        'userId': 'U12345678901234567890123456789013',
        "user_id": "12345678901234567890123456789013",
        'pictureUrl': 'http://test.com/avatar.jpg',
        'access_token': 'test_access_token',
        'expires_in': 480
    }
    jwt_token, exp = generate_token(jwt_payload)
    response = make_response(jsonify({"message": "Test token created"}))
    response.set_cookie('token', jwt_token)
    return response
'''
#登出
@app.route('/logout')
def logout():
    response = make_response(jsonify({"message": "登出成功"}))

    response.delete_cookie('token')
    return response
    #return redirect('/')

#取得使用者資料
@app.route('/user/info', methods=['GET'])
def user_info():
    token = request.cookies.get('token')
    if not token:
        return jsonify({"error": "Missing token"})

    decoded, err = verify_token(token)
    if err:
        return jsonify({"error": err})

    user_id = decoded.get("user_id")
    if not user_id:
        return jsonify({"error": "LINE userId not found in token"})

    cursor = db.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM Users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()

    if not user:
        return jsonify({"error": "User not found"})

    return jsonify({"user": user})

    

#新增聯絡人
@app.route('/contact/create', methods=["POST"])
def create_contact():
    data = request.json
    contact_user_id = data.get("contact_user_id")
    
    if not contact_user_id:
        return jsonify({"error": "Missing contact_user_id"})

    token = request.cookies.get("token")
    is_valid, current_user_id = verify_token(token)
    if not is_valid:
        return jsonify({"error": "Invalid or missing token"})

    if contact_user_id == current_user_id:
        return jsonify({"error": "Cannot add yourself as a contact"})

    cursor = db.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM Users WHERE user_id = %s", (contact_user_id,))
    user = cursor.fetchone()
    
    if not user:
        return jsonify({"error": "User not found"})

    line_id = user.get("line_id")
    contact_name = user.get("user_name")
    
    cursor.execute(
        "INSERT INTO Contacts (user_id, line_id, contact_name) VALUES (%s, %s, %s)",
        (contact_user_id, line_id, contact_name)
    )
    db.commit()
    
    contact_id = cursor.lastrowid

    return jsonify({
        "message": "Contact created successfully",
        "contact": {
            "contact_id": contact_id,
            "user_id": contact_user_id,
            "line_id": line_id,
            "contact_name": contact_name
        }
    })

@app.route('/contact/delete', methods=["DELETE"])
def delete_contact():
    token = request.cookies.get("token")
    if not token:
        return jsonify({"error": "Missing token in cookies"})

    valid, current_user_id = verify_token(token)
    if not valid:
        return jsonify({"error": current_user_id})
    data = request.json
    contact_id = data.get("contact_id")
    if not contact_id:
        return jsonify({"error": "Missing contact_id"})
    
    cursor = db.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM Contacts WHERE contact_id = %s", (contact_id,))
    contact = cursor.fetchone()
    if not contact:
        return jsonify({"error": "Contact not found"})

    cursor.execute("DELETE FROM Contacts WHERE contact_id = %s", (contact_id,))
    db.commit()

    return jsonify({"message": "Contact deleted successfully"})


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