from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage, TemplateSendMessage, ButtonsTemplate, PostbackAction
import os
import sqlite3
from datetime import datetime

app = Flask(__name__)

# 環境變數
CHANNEL_ACCESS_TOKEN = os.environ.get("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.environ.get("CHANNEL_SECRET")

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# 建立 SQLite 資料表
def init_db():
    conn = sqlite3.connect('baby_log.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS meals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# 接收 LINE Webhook
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except:
        abort(400)
    return 'OK'

# 文字訊息處理
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text

    if user_message == "我要紀錄":
        buttons_template = ButtonsTemplate(
            title="選擇要紀錄的項目",
            text="請選擇：",
            actions=[
                PostbackAction(label="吃飯", data="action=meal")
            ]
        )
        template_message = TemplateSendMessage(
            alt_text='請選擇要紀錄的項目',
            template=buttons_template
        )
        line_bot_api.reply_message(event.reply_token, template_message)

    elif user_message.startswith("吃飯內容:"):
        # 格式為：吃飯內容:08:30 白粥+蛋
        try:
            parts = user_message.replace("吃飯內容:", "").strip().split(" ", 1)
            time_str = parts[0]
            content = parts[1]
            save_meal_record(time_str, content)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="已紀錄吃飯資料 🍚"))
        except:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="格式錯誤，請用：吃飯內容:08:30 白粥+蛋"))

# Postback 處理
@handler.add(MessageEvent)
def handle_postback(event):
    if hasattr(event.message, 'text') and event.message.text == 'action=meal':
        send_meal_time_options(event.reply_token)

# 發送時間選單
def send_meal_time_options(reply_token):
    times = [f"{h:02}:{m:02}" for h in range(8, 22) for m in [0, 30]]
    text = "請輸入吃飯內容，格式為：\n吃飯內容:時間 內容\n\n例如：吃飯內容:08:30 白粥+蛋"
    line_bot_api.reply_message(reply_token, TextSendMessage(text=text))

# 寫入 SQLite
def save_meal_record(time, content):
    conn = sqlite3.connect('baby_log.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO meals (time, content) VALUES (?, ?)", (time, content))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
