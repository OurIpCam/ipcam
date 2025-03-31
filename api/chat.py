from flask import Flask, request, jsonify

# 載入 json 標準函式庫，處理回傳的資料格式
import json

# 載入 LINE Message API 相關函式庫
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

@app.route("/callback", methods=['POST'])
def linebot():
    body = request.get_data(as_text=True)                    # 取得收到的訊息內容
    try:
        json_data = json.loads(body)                         # json 格式化訊息內容
        access_token = 'fVCoNO0ngCzftfIarmDem5zXiGaGRQ5hDxO/LKatg3eVgo9VdZgVY9SnM9LLDkMxiyQId1o5h/k826cebvr/iUhF8gpJjV/fDL89/zYG23L0WS1S4xB6uSDvS5O7Owwoy7NCVyfiVXzz1pNHEGm7YAdB04t89/1O/w1cDnyilFU='
        secret = 'bc2264d5bd45de23e2c4d1c9269acef9'
        line_bot_api = LineBotApi(access_token)              # 確認 token 是否正確
        handler = WebhookHandler(secret)                     # 確認 secret 是否正確
        signature = request.headers['X-Line-Signature']      # 加入回傳的 headers
        handler.handle(body, signature)                      # 綁定訊息回傳的相關資訊
        tk = json_data['events'][0]['replyToken']            # 取得回傳訊息的 Token
        type = json_data['events'][0]['message']['type']     # 取得 LINe 收到的訊息類型
        if type=='text':
            msg = json_data['events'][0]['message']['text']  # 取得 LINE 收到的文字訊息
            print(json_data['events'].source.user_id,msg)                                       # 印出內容
            reply = msg
        else:
            reply = '你傳的不是文字呦～'
        print(reply)
        line_bot_api.reply_message(tk,TextSendMessage(reply))# 回傳訊息
    except:
        print(body)                                          # 如果發生錯誤，印出收到的內容
    return 'OK'                                              # 驗證 Webhook 使用，不能省略




"""
# 管理者定義的事件 (使用者不能新增，只能修改通知內容)
EVENTS = {
    "human_fall": "⚠️ 偵測到跌倒！",
    "human_appear": "🚶 有人出現！"
}

# 存放使用者的通知內容 (預設為管理者定義的事件)
notification_settings = EVENTS.copy()
"""

"""
@app.route("/set_notification", methods=['POST'])
def set_notification():
    #讓使用者設定已定義事件的通知內容
    try:
        data = request.json
        event = data.get("event")
        message = data.get("message")

        if not event or not message:
            return jsonify({"status": "error", "message": "請提供 event 和 message"})

        if event not in EVENTS:
            return jsonify({"status": "error", "message": "此事件無法設定"})

        # 更新使用者的通知內容
        notification_settings[event] = message
        return jsonify({"status": "success", "message": f"{event} 通知設定為：{message}"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    
"""


""" /send_alert/human/fall
model: human, event: fall, notification: ''

@app.route("/send_alert/human/fall", methods=['POST'])
def send_alert_human_fall():
    pass
"""

"""
@app.route("/send_alert/human/fall", methods=['POST'])
def send_alert_human_fall():
    # 發送 human_fall 事件通知 
    try:
        message = notification_settings.get("human_fall", EVENTS["human_fall"])
        line_bot_api.push_message(USER_ID, TextSendMessage(text=message))
        return jsonify({"status": "success", "message": message})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
"""

""" /send_alert/human/appear
model: human, event: appear, notification: ''

@app.route("/send_alert/human/appear", methods=['POST'])
def send_alert_humal_appear():
    pass
"""
if __name__ == "__main__":
    app.run()