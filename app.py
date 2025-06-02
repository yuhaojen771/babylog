import os
import sqlite3
from datetime import datetime
from flask import Flask, request, abort
from dotenv import load_dotenv
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *

# 載入環境變數
load_dotenv()
CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# 初始化資料庫
conn = sqlite3.connect("babylog.db", check_same_thread=False)
c = conn.cursor()
c.execute('''
    CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT,
        time TEXT,
        content TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
conn.commit()

app = Flask(__name__)

# 首頁
@app.route("/")
def home():
    return "OK"

# 接收 LINE Webhook
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# 處理文字訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text

    if text == "我要紀錄":
        buttons = TemplateSendMessage(
            alt_text='請選擇紀錄類型',
            template=ButtonsTemplate(
                title='紀錄選單',
                text='請選擇要紀錄的類別',
                actions=[
                    MessageAction(label="吃飯", text="紀錄吃飯"),
                    MessageAction(label="睡覺", text="紀錄睡覺"),
                    MessageAction(label="便便", text="紀錄便便"),
                    MessageAction(label="查詢", text="查詢紀錄")
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, buttons)

    elif text == "紀錄吃飯":
        reply_eat_time(event)

    elif text == "紀錄睡覺":
        reply_sleep_start(event)

    elif text == "紀錄便便":
        reply_poop_time(event)

    elif text == "查詢紀錄":
        records = query_today()
        if not records:
            line_bot_api.reply_message(event.reply_token, TextSendMessage("今天尚無紀錄"))
        else:
            msg = "今天的紀錄：\n"
            for r in records:
                msg += f"[{r[1]}] {r[2]} {r[3]}\n"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(msg))

# 吃飯時間選擇
@handler.add(PostbackEvent)
def handle_postback(event):
    data = event.postback.data

    if data.startswith("eat_time:"):
        time = data.split(":")[1]
        line_bot_api.reply_message(event.reply_token, TextSendMessage(f"請輸入吃的內容：{time}"))
        # 儲存暫存時間
        user_id = event.source.user_id
        temp[user_id] = {"type": "eat", "time": time}

    elif data.startswith("poop_time:"):
        time = data.split(":")[1]
        line_bot_api.reply_message(event.reply_token, TextSendMessage(f"請輸入便便備註（顏色、形狀等）：{time}"))
        temp[event.source.user_id] = {"type": "poop", "time": time}

    elif data.startswith("sleep_start:"):
        time = data.split(":")[1]
        line_bot_api.reply_message(event.reply_token, make_sleep_end_picker())
        temp[event.source.user_id] = {"type": "sleep", "start": time}

    elif data.startswith("sleep_end:"):
        time = data.split(":")[1]
        user_id = event.source.user_id
        start_time = temp.get(user_id, {}).get("start", "")
        save_record("sleep", f"{start_time}-{time}", "")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(f"睡覺紀錄完成：{start_time}-{time}"))

# 處理吃飯/便便備註
@handler.add(MessageEvent, message=TextMessage)
def handle_input_content(event):
    user_id = event.source.user_id
    info = temp.get(user_id)
    if not info:
        return

    if info['type'] == "eat":
        save_record("eat", info['time'], event.message.text)
        line_bot_api.reply_message(event.reply_token, TextSendMessage("吃飯紀錄完成！"))
    elif info['type'] == "poop":
        save_record("poop", info['time'], event.message.text)
        line_bot_api.reply_message(event.reply_token, TextSendMessage("便便紀錄完成！"))

    del temp[user_id]

# 回傳吃飯按鈕
def reply_eat_time(event):
    actions = [PostbackAction(label=f"{h:02d}:{m:02d}", data=f"eat_time:{h:02d}:{m:02d}")
               for h in range(8, 22) for m in (0, 30)]
    columns = [CarouselColumn(text="請選擇時間", actions=actions[i:i+3]) for i in range(0, len(actions), 3)]
    carousel = TemplateSendMessage(alt_text="吃飯時間", template=CarouselTemplate(columns=columns[:10]))
    line_bot_api.reply_message(event.reply_token, carousel)

# 回傳便便時間按鈕
def reply_poop_time(event):
    actions = [PostbackAction(label=f"{h:02d}:{m:02d}", data=f"poop_time:{h:02d}:{m:02d}")
               for h in range(8, 22) for m in (0, 30)]
    buttons = TemplateSendMessage(
        alt_text='請選擇時間',
        template=ButtonsTemplate(
            title='便便時間',
            text='請選擇便便時間',
            actions=actions[:4]  # 前幾個示意，Carousel 可擴充
        )
    )
    line_bot_api.reply_message(event.reply_token, buttons)

# 回傳睡覺起始時間選擇
def reply_sleep_start(event):
    actions = [PostbackAction(label=f"{h:02d}:{m:02d}", data=f"sleep_start:{h:02d}:{m:02d}")
               for h in range(8, 22) for m in (0, 30)]
    buttons = TemplateSendMessage(
        alt_text='請選擇開始時間',
        template=ButtonsTemplate(
            title='睡覺起始',
            text='請選擇睡覺開始時間',
            actions=actions[:4]  # 示意，Carousel 可擴充
        )
    )
    line_bot_api.reply_message(event.reply_token, buttons)

def make_sleep_end_picker():
    actions = [PostbackAction(label=f"{h:02d}:{m:02d}", data=f"sleep_end:{h:02d}:{m:02d}")
               for h in range(8, 22) for m in (0, 30)]
    return TemplateSendMessage(
        alt_text='請選擇結束時間',
        template=ButtonsTemplate(
            title='睡覺結束',
            text='請選擇睡覺結束時間',
            actions=actions[:4]  # 示意
        )
    )

# 儲存紀錄
def save_record(type_, time_, content):
    c.execute("INSERT INTO records (type, time, content) VALUES (?, ?, ?)", (type_, time_, content))
    conn.commit()

# 查詢今日紀錄
def query_today():
    today = datetime.now().strftime('%Y-%m-%d')
    c.execute("SELECT * FROM records WHERE DATE(created_at) = ? ORDER BY created_at", (today,))
    return c.fetchall()

# 暫存使用者輸入資訊
temp = {}

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
