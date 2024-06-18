from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *

import os
import datetime
import time
import threading
import traceback

app = Flask(__name__)

# Channel Access Token
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
# Channel Secret
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# 用於存儲用戶的吃藥狀態
user_reminders = {}
reminder_interval = 15  # 重新提醒的間隔時間（分鐘）

# 監聽所有來自 /callback 的 Post Request
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# 處理訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text.lower()
    user_id = event.source.user_id

    if '吃了' in msg:
        user_reminders[user_id] = {'status': 'done', 'last_reminder': None}
        line_bot_api.reply_message(event.reply_token, TextSendMessage('好的，記得明天同樣時間吃藥哦！'))
    else:
        line_bot_api.reply_message(event.reply_token, TextSendMessage('請在每天晚上10點後回覆 "吃了" 以停止提醒。'))

# 檢查並發送提醒
def check_reminders():
    while True:
        now = datetime.datetime.now()
        if now.hour == 22 and now.minute == 0:
            for user_id in user_reminders:
                user_reminders[user_id] = {'status': 'pending', 'last_reminder': None}
                try:
                    line_bot_api.push_message(user_id, TextSendMessage('該吃藥了！請回覆 "吃了" 以停止提醒。'))
                except Exception as e:
                    print(f'Failed to send initial reminder to {user_id}: {e}')
        else:
            for user_id, reminder_info in user_reminders.items():
                if reminder_info['status'] == 'pending':
                    last_reminder = reminder_info['last_reminder']
                    if last_reminder is None or (now - last_reminder).total_seconds() > reminder_interval * 60:
                        try:
                            line_bot_api.push_message(user_id, TextSendMessage('該吃藥了！請回覆 "吃了" 以停止提醒。'))
                            user_reminders[user_id]['last_reminder'] = now
                        except Exception as e:
                            print(f'Failed to send follow-up reminder to {user_id}: {e}')
        time.sleep(60)

# 在後台運行檢查提醒的函數
reminder_thread = threading.Thread(target=check_reminders)
reminder_thread.start()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
