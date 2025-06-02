import os
import sqlite3
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *

# 讀取環境變數
CHANNEL_ACCESS_TOKEN = os.environ.get("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.environ.get("CHANNEL_SECRET")

app = Flask(__name__)
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# 初始化 SQLite 資料庫
def init_db():
    conn = sqlite3.connect("babylog.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS meals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            meal_time TEXT,
            food_content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# 儲存吃飯紀錄
def save_meal(user_id, meal_time, food_content):
    conn = sqlite3.connect("babylog.db")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO meals (user_id, meal_time, food_content)
        VALUES (?, ?, ?)
    ''', (user_id, meal_time, food_content))
    conn.commit()
    conn.close()

# 接收 LINE webhook
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# 使用者輸入文字
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text

    if text == "我要紀錄":
        buttons = [
            QuickReplyButton(action=MessageAction(label=f"吃飯", text="吃飯"))
        ]
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請選擇要紀錄的項目：", quick_reply=QuickReply(items=buttons))
        )

    elif text == "吃飯":
        buttons = []
        for h in range(8, 22):
            for m in [0, 30]:
                t = f"{h:02d}:{m:02d}"
                buttons.append(QuickReplyButton(action=PostbackAction(label=t, data=f"meal_time:{t}")))
                if len(buttons) == 13:
                    break
            if len(buttons) == 13:
                break
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請選擇吃飯時間：", quick_reply=QuickReply(items=buttons))
        )

# 處理時間選擇後的 Postback
@handler.add(PostbackEvent)
def handle_postback(event):
    data = event.postback.data
    user_id = event.source.user_id

    if data.startswith("meal_time:"):
        meal_time = data.split(":")[1]
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"請輸入 {meal_time} 吃了什麼？")
        )
        # 把選擇的時間暫存（開發時可改用 Redis 或全域變數，這裡簡化）
        with open(f"temp_{user_id}.txt", "w") as f:
            f.write(meal_time)

    elif data.startswith("cancel"):
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="已取消。")
        )

# 處理內容輸入
@handler.add(MessageEvent, message=TextMessage)
def handle_meal_content(event):
    user_id = event.source.user_id
    text = event.message.text

    try:
        with open(f"temp_{user_id}.txt", "r") as f:
            meal_time = f.read()
        save_meal(user_id, meal_time, text)
        os.remove(f"temp_{user_id}.txt")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"已紀錄：{meal_time} 吃了「{text}」")
        )
    except FileNotFoundError:
        pass  # 不是輸入食物內容，就交給前面的 handler 處理

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
