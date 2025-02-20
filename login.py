from flask import Flask, redirect, request, session, url_for, send_file, render_template
import requests
import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secret key for session handling

# LINE Login Credentials
LINE_CLIENT_ID = os.getenv('LINE_CLIENT_ID')
LINE_CLIENT_SECRET = os.getenv('LINE_CLIENT_SECRET')
REDIRECT_URI = "http://127.0.0.1:5000/callback"

# LINE Authorization URL
LINE_AUTH_URL = "https://access.line.me/oauth2/v2.1/authorize"
LINE_TOKEN_URL = "https://api.line.me/oauth2/v2.1/token"
LINE_PROFILE_URL = "https://api.line.me/v2/profile"

@app.route('/')
def home():
    if 'user' in session:
        user = session['user']
        return render_template("main.html", display_name=user.get('displayName', 'Unknown User'), picture_url=user.get('pictureUrl', ''))
    return render_template("login.html")
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
@app.route('/login')
def login():
    """ Redirect to LINE login page """
    login_url = f"{LINE_AUTH_URL}?response_type=code&client_id={LINE_CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope=profile%20openid%20email&state=123456"
    #print("Generated Login URL:", login_url)  # Debugging
    return redirect(login_url)

@app.route('/callback')
def callback():
    """ Handle the OAuth2 callback from LINE """
    code = request.args.get('code')
    if not code:
        return "Error: No code received", 400

    # Exchange code for access token
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

    # Get user profile data
    headers = {'Authorization': f'Bearer {access_token}'}
    profile_response = requests.get(LINE_PROFILE_URL, headers=headers)
    profile_json = profile_response.json()
    # Extract unique user ID
    user_id = profile_json.get('userId', 'Unknown ID')
    display_name = profile_json.get('displayName', 'Unknown User')
    picture_url = profile_json.get('pictureUrl', '')
   
    # Store user info in session
    #session['user'] = profile_json
    # Store user info in session
    session['user'] = {
        'userId': user_id,  # Unique LINE user ID
        'displayName': display_name,
        'pictureUrl': picture_url
    }
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    """ Logout user """
    session.pop('user', None)
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
