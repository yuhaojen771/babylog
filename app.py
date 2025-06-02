from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    PostbackEvent, PostbackAction,
    TemplateSendMessage, ButtonsTemplate, MessageAction, QuickReply, QuickReplyButton
)
import os

app = Flask(__name__)

# 環境變數設定（請自行填入）
CHANNEL_ACCESS_TOKEN = '0UR4cpzlLkEIBNIWBcx1XEKiXJPVbOlrxILQCoBOd4Hq2IVd8oLCq+kNswm+JR0Q7jj26lNkMCkq1eGkNhA6FAMRMLQigLE1DDlKJ/Rd8NaO+Ax3SS78WxJ8dFLn7hgPE8uDXe1urmNhq3MAyBKF8gdB04t89/1O/w1cDnyilFU='
CHANNEL_SECRET = '287dd374c6ee48c3b7b4239d70571c47'

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# 臨時儲存使用者輸入的紀錄（正式版可替換為資料庫）
user_states = {}
user_notes = {}

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

# 使用者傳送訊息的處理器
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text

    if text == "我要紀錄":
        # 主選單
        buttons_template = ButtonsTemplate(
            title='選擇要紀錄的項目',
            text='請選擇以下其中一項',
            actions=[
                PostbackAction(label='吃飯', data='action=eat'),
                PostbackAction(label='睡覺', data='action=sleep'),
                PostbackAction(label='便便', data='action=poop')
            ]
        )
        template_message = TemplateSendMessage(
            alt_text='請選擇要紀錄的項目',
            template=buttons_template
        )
        line_bot_api.reply_message(event.reply_token, template_message)

    elif user_states.get(user_id) == "awaiting_eat_note":
        # 接收備註
        note = text
        user_states.pop(user_id)
        meal_time = user_notes.get(user_id, {}).get("meal_time", "未知時間")
        meal_type = user_notes.get(user_id, {}).get("meal_type", "未知餐別")
        response = f"✅ 吃飯紀錄完成：\n餐別：{meal_type}\n時間：{meal_time}\n備註：{note}"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response))

@handler.add(PostbackEvent)
def handle_postback(event):
    user_id = event.source.user_id
    data = event.postback.data

    if data.startswith("action=eat"):
        # 提供餐別選擇
        buttons_template = ButtonsTemplate(
            title="吃飯紀錄",
            text="請選擇餐別",
            actions=[
                PostbackAction(label="早餐", data="meal_type=早餐"),
                PostbackAction(label="午餐", data="meal_type=午餐"),
                PostbackAction(label="晚餐", data="meal_type=晚餐"),
                PostbackAction(label="點心", data="meal_type=點心")
            ]
        )
        template_message = TemplateSendMessage(
            alt_text="請選擇餐別",
            template=buttons_template
        )
        line_bot_api.reply_message(event.reply_token, template_message)

    elif data.startswith("meal_type="):
        meal_type = data.split("=")[1]
        user_notes[user_id] = {"meal_type": meal_type}

        # 選擇時間（使用 QuickReply）
        time_options = [f"{hour:02d}:{minute:02d}" for hour in range(8, 21) for minute in (0, 30)]
        quick_reply_items = [
            QuickReplyButton(action=PostbackAction(label=t, data=f"meal_time={t}"))
            for t in time_options[:12]  # 可視情況調整顯示項目數
        ]
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=f"選擇{meal_type}的時間",
                quick_reply=QuickReply(items=quick_reply_items)
            )
        )

    elif data.startswith("meal_time="):
        meal_time = data.split("=")[1]
        user_notes[user_id]["meal_time"] = meal_time
        user_states[user_id] = "awaiting_eat_note"

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請輸入備註（例如吃了什麼）")
        )

if __name__ == "__main__":
    app.run()
