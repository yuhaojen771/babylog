import os
import sqlite3
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import *
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()
CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    raise Exception("請設定 CHANNEL_ACCESS_TOKEN 與 CHANNEL_SECRET")

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

app = Flask(__name__)

# 初始化 SQLite
conn = sqlite3.connect('baby_log.db')
c = conn.cursor()
c.execute('''
CREATE TABLE IF NOT EXISTS meal_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    time TEXT,
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')
conn.commit()
conn.close()

# 記錄用戶目前等待輸入食物內容的狀態
user_meal_state = {}  # user_id: selected_time

@app.route("/", methods=['GET'])
def index():
    return "LINE Bot is running."

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except Exception as e:
        print("handle error:", e)
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()

    if text == "我要紀錄":
        buttons_template = TemplateSendMessage(
            alt_text='請選擇紀錄項目',
            template=ButtonsTemplate(
                title='請選擇',
                text='請選擇要紀錄的項目',
                actions=[
                    PostbackAction(label='吃飯', data='action=meal'),
                    PostbackAction(label='睡覺', data='action=sleep'),
                    PostbackAction(label='便便', data='action=poop')
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, buttons_template)

    elif user_id in user_meal_state:
        meal_time = user_meal_state.pop(user_id)
        content = text
        conn = sqlite3.connect('baby_log.db')
        c = conn.cursor()
        c.execute("INSERT INTO meal_records (user_id, time, content) VALUES (?, ?, ?)",
                  (user_id, meal_time, content))
        conn.commit()
        conn.close()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"吃飯紀錄完成！\n時間：{meal_time}\n內容：{content}")
        )

@handler.add(PostbackEvent)
def handle_postback(event):
    data = event.postback.data
    user_id = event.source.user_id

    if data == "action=meal":
        actions = []
        for h in range(8, 22):
            for m in [0, 30]:
                time_str = f"{h:02d}:{m:02d}"
                actions.append(PostbackAction(label=time_str, data=f"meal_time={time_str}"))

        # 分割為多列 carousel（最多每列 3 個按鈕）
        columns = [
            CarouselColumn(text='選擇吃飯時間', actions=actions[i:i+3])
            for i in range(0, len(actions), 3)
        ][:5]  # 最多五列（15 個時間）

        carousel = TemplateSendMessage(
            alt_text='請選擇吃飯時間',
            template=CarouselTemplate(columns=columns)
        )
        line_bot_api.reply_message(event.reply_token, carousel)

    elif data.startswith("meal_time="):
        selected_time = data.split("=")[1]
        user_meal_state[user_id] = selected_time
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"請輸入 {selected_time} 吃的內容（例如：稀飯、蛋）")
        )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
