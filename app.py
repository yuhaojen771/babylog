from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

import os

app = Flask(__name__)

# 改成你自己的 Token 和 Secret
CHANNEL_ACCESS_TOKEN = os.environ.get("0UR4cpzlLkEIBNIWBcx1XEKiXJPVbOlrxILQCoBOd4Hq2IVd8oLCq+kNswm+JR0Q7jj26lNkMCkq1eGkNhA6FAMRMLQigLE1DDlKJ/Rd8NaO+Ax3SS78WxJ8dFLn7hgPE8uDXe1urmNhq3MAyBKF8gdB04t89/1O/w1cDnyilFU=")
CHANNEL_SECRET = os.environ.get("287dd374c6ee48c3b7b4239d70571c47")

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    raise ValueError("請設定 CHANNEL_ACCESS_TOKEN 和 CHANNEL_SECRET 環境變數")

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

@app.route("/")
def home():
    return "OK"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text.strip()

    if msg == "我要紀錄":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請選擇你要記錄的事件：吃飯、睡覺、便便")
        )
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"你說的是：{msg}")
        )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
