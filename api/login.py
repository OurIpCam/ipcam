from flask import Flask, redirect, request, session, url_for, send_file, render_template
import requests
import os

"""
render_template 函數會自動在templates文件中找到對應的html, 因此不用寫完整的html路徑。
"""

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secret key for session handling
#Flask 使用 secret_key 來簽名和加密 session cookie，從而確保 session 資料的安全性和完整性。

# LINE Login Credentials
LINE_CLIENT_ID = "2006911351"
LINE_CLIENT_SECRET = "f049a5c4224180099cd88dc599745cdf"
REDIRECT_URI = "http://127.0.0.1:5000/callback"

# LINE Authorization URL
LINE_AUTH_URL = "https://access.line.me/oauth2/v2.1/authorize"
LINE_TOKEN_URL = "https://api.line.me/oauth2/v2.1/token"
LINE_PROFILE_URL = "https://api.line.me/v2/profile"

"""回傳templates/auth/index.html(選擇不同方式登入頁面)"""
@app.route('/')
def index():
    return render_template('auth/index.html')

"""回傳templates/auth/login.html(Line登入頁面)"""
@app.route('/login')
def login():
    return render_template('auth/login.html')

"""(包含頭貼、user_id)
確認是否在session的狀態下，true=回傳頭貼跟user_id,false=重新回登入畫面
but id 存到哪去了??????????
使用者姓名該如何儲存到資料庫?????
"""
@app.route('/home') #, methods = ['']
def home():
    
    """session 是一種用來存儲使用者資訊的機制，通常用在網站中，讓伺服器記住某個使用者在不同頁面之間的狀態。"""
    #顯示使用者資訊，並提供姓名輸入框
    if 'user' in session:
        user = session['user']
        return render_template("main.html",
                               picture_url=user.get('pictureUrl', ''),
                               user_id=user.get('userId', 'Unknown ID'),
                               name=user.get('name', ''))  # 取得姓名，若無則為空
    return redirect(url_for('index'))
"""
def home():
    if 'user' in session:
        user = session['user']
        return render_template("main.html", picture_url=user.get('pictureUrl', ''), user_id=user.get('userId', 'Unknown ID'))
    return render_template("auth/index.html")
"""

"""(包含頭貼、姓名、user_id)
@app.route('/home') #, methods = ['']
def home():
    if 'user' in session:
        user = session['user']
        return render_template("main.html", display_name=user.get('displayName', 'Unknown User'), picture_url=user.get('pictureUrl', ''),
                                user_id=user.get('userId', 'Unknown ID'))  # 加入 userId
    return render_template("auth/index.html")
"""

"""
def home():
    if 'user' in session:
        user = session['user']
        display_name = user.get('displayName', 'Unknown User')
        picture_url = user.get('pictureUrl', '')  # Use .get() to avoid KeyError

        # Build HTML response
        response = f"Welcome, {display_name}!<br>"
        if picture_url:  # Only show image if available
            response += f"<img src='{picture_url}' width='100'><br>"

        response += "<a href='/logout'>Logout</a>"
        
        return send_file("main.html",mimetype = "text/html")
    return send_file("login.html",mimetype = "text/html")
"""

"""讓使用者設置姓名"""
@app.route('/set_name', methods=['POST'])
def set_name():
    """ 儲存使用者輸入的姓名 """
    if 'user' in session:
        name = request.form.get('name')  # 取得前端輸入的姓名
        session['user']['name'] = name   # 存入 session
    return redirect(url_for('home'))  # 回到 home 頁面

"""回傳Line官方登入頁面"""
@app.route('/login/Line')
def loginLine():
    """ Redirect to LINE login page """
    login_url = f"{LINE_AUTH_URL}?response_type=code&client_id={LINE_CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope=profile%20openid%20email&state=123456"
    
    """scope 用來定義你在認證過程中需要哪些資料"""
    
    """openid
    身份認證：它讓應用程式能夠確保使用者是誰。
    當你的應用程序要求 openid 範圍時，LINE 會發送一個 ID Token，這個 token 會包含一些基本的身份資料，例如：
    user_id（LINE 使用者的唯一識別碼）
    email（如果 email 也在 scope 中）
    其他身份相關資料。
    
    ID Token 是一個 JSON Web Token (JWT)，它是經過簽名的，包含了關於使用者的訊息。
    這些訊息可能包括：
    sub（subject，代表用戶的唯一 ID）
    name（用戶的名稱）
    email（用戶的電子郵件，若有提供）
    iat（issued at，發行時間）
    exp（expiration time，過期時間）
    """
    #print("Generated Login URL:", login_url)  # Debugging
    return redirect(login_url)

"""處理 LINE OAuth2 認證流程的 Flask 路由。
Callback 流程解析
1. LINE 重導向到 callback，並附帶 code
    使用者點擊「使用 LINE 登入」後，會被導向到 https://access.line.me/oauth2/v2.1/authorize 進行授權。
    使用者同意授權後，LINE 會將他導回 https://你的網站/callback?code=xxx。
2. 伺服器透過 code 向 LINE 請求 access_token
    code 只能用一次，伺服器需要立即交換 access_token，才能進一步存取使用者資料。
    access_token is 讓應用程式 授權 存取使用者的資料的一個憑證
3. 伺服器使用 access_token 向 LINE API 請求使用者資訊
    獲取 LINE User ID（應用內唯一識別碼）。
    取得 使用者大頭貼（如果有）。
4. 存入 session，讓使用者保持登入狀態
    這樣其他頁面可以透過 session['user'] 來判斷使用者是否已登入。
5. 導向首頁 home
    讓使用者成功登入並進入主頁。
"""
@app.route('/callback')
def callback():
    """ Handle the OAuth2 callback from LINE """
    code = request.args.get('code')
    if not code:
        return "Error: No code received", 400

    # Exchange code for access token
    token_data = {
        'grant_type': 'authorization_code',     #使用授權碼換取 access_token
        'code': code,                           #剛剛取得的 code，用來換取 access token
        'redirect_uri': REDIRECT_URI,           #事先設定的回調網址，必須與 LINE 開發者後台設定的一致
        'client_id': LINE_CLIENT_ID,            #你的 LINE 開發者 client_id
        'client_secret': LINE_CLIENT_SECRET     #你的 LINE client_secret（用來驗證應用程式身份）
    }
    
    """
    發送 POST 請求到 LINE_TOKEN_URL（https://api.line.me/oauth2/v2.1/token）
    - 用 requests.post() 發送請求，並將 token_data 傳遞給 LINE。
    - 這個請求的目標是用 code 來換取 access_token。
    將回應轉換為 JSON (token_json)
    - token_response.json() 會解析 LINE 回傳的 JSON 資料。
    """
    token_response = requests.post(LINE_TOKEN_URL, data=token_data)
    token_json = token_response.json()

    if 'access_token' not in token_json:
        return "Error retrieving access token", 400

    access_token = token_json['access_token']
    expires_in = token_json['expires_in']  # Token 過期時間（秒）

    # Get user profile data /個人資料數據
    headers = {'Authorization': f'Bearer {access_token}'}               #設定 Authorization 標頭
    profile_response = requests.get(LINE_PROFILE_URL, headers=headers)  #向 LINE API 請求使用者資料
    profile_json = profile_response.json()                              #將從 LINE API 返回的原始資料解析為 JSON 格式
    # Extract unique user ID

    # Check if 'userId' exists in the response
    if 'userId' in profile_json:
        user_id = profile_json['userId']
    else:
        return "Error: userId not found", 400  # or any other error handling

    """debug:
    確信 profile_json 中一定會有 userId，那麼可以直接使用 profile_json['userId']。
    如果 userId 是可選的，建議使用 .get() 方法來避免程式崩潰。
    """
    picture_url = profile_json.get('pictureUrl', '')
    
    #user_id = profile_json.get('userId', 'Unknown ID')
    #display_name = profile_json.get('displayName', 'Unknown User')
    #return user_id

    #session['user'] = profile_json
    # Store user info in session
    #之後要驗證都要用這塊
    session['user'] = {
        'userId': user_id,  # Unique LINE user ID
        #'displayName': display_name,
        'pictureUrl': picture_url,
        'name': '',          #初始為空
        'access_token': access_token,  # 存取 API 需要用的 Token
        #(讓應用程式 授權 存取使用者的資料的一個憑證，只是用來授權應用程式訪問這些資料的“門票”。)
        'expires_in': expires_in  # 記錄 Token 有效時間
        
    }
    
    #使用者登入後自動跳轉到首頁
    return redirect(url_for('home'))

"""登出"""
@app.route('/logout')
def logout():
    """ Logout user """
    session.pop('user', None)
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
