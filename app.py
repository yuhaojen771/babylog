from flask import Flask, request, abort
from linebot.v3.webhook import WebhookHandler
from linebot.v3.messaging import (
    MessagingApiClient, ReplyMessageRequest,
    TextMessage, FlexMessage, PostbackAction, QuickReply, QuickReplyItem
)
from linebot.v3.webhook import (
    MessageEvent, PostbackEvent, TextMessageContent
)
from linebot.v3.exceptions import InvalidSignatureError
import os
import sqlite3
import datetime

app = Flask(__name__)

# 環境變數方式
CHANNEL_ACCESS_TOKEN = os.environ.get("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.environ.get("CHANNEL_SECRET")

# 初始化 LINE Bot
handler = WebhookHandler(CHANNEL_SECRET)
line_bot_api = MessagingApiClient(channel_access_token=CHANNEL_ACCESS_TOKEN)

# 建立 SQLite 資料表
def init_db():
    conn = sqlite3.connect('babylog.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS meal_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            time TEXT,
            content TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

# 接收文字訊息
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    text = event.message.text
    if text == "我要紀錄":
        buttons = [QuickReplyItem(action=PostbackAction(label="吃飯", data="record_meal"))]
        message = TextMessage(text="請選擇要記錄的項目", quick_reply=QuickReply(items=buttons))
        line_bot_api.reply_message(ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[message]
        ))
    elif text.startswith("食物內容: "):
        user_id = event.source.user_id
        content = text.replace("食物內容: ", "")
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        conn = sqlite3.connect("babylog.db")
        c = conn.cursor()
        c.execute("INSERT INTO meal_log (user_id, time, content) VALUES (?, ?, ?)", (user_id, now, content))
        conn.commit()
        conn.close()

        line_bot_api.reply_message(ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text="吃飯內容已記錄")]
        ))

# 接收 postback 選單事件
@handler.add(PostbackEvent)
def handle_postback(event):
    data = event.postback.data
    if data == "record_meal":
        # 建立每半小時的時間列表
        buttons = []
        for hour in range(8, 21):
            for minute in [0, 30]:
                time_str = f"{hour:02d}:{minute:02d}"
                buttons.append(QuickReplyItem(action=PostbackAction(label=time_str, data=f"meal_time={time_str}")))
        line_bot_api.reply_message(ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text="請選擇吃飯時間", quick_reply=QuickReply(items=buttons[:13]))]  # 最多 13 個按鈕
        ))

    elif data.startswith("meal_time="):
        time_selected = data.split("=")[1]
        # 暫存時間（實務上應該用資料庫/session 綁 user_id）
        line_bot_api.reply_message(ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text=f"請輸入吃飯內容（格式為：食物內容: xxx）\n時間為 {time_selected}")]
        ))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
