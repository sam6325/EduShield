from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.models import TextSendMessage
import json
from dialogue_agent import DialogueAgent
import pymongo
from datetime import datetime


# MongoDB 連接
uri = "mongodb+srv://a0988398645:a0910035817@andrew.3xi60lp.mongodb.net/?retryWrites=true&w=majority&appName=andrew"
client = pymongo.MongoClient(uri)
db = client.member

# Flask 應用程式
app = Flask(__name__)

# LINE 頻道設定
CHANNEL_SECRET = "3cdc6246947956a632ebeb17203165c3"
CHANNEL_ACCESS_TOKEN = "4ikDdHoArnTBlI9WcHr1GMJgTD2EQFyPqIDB2W7VsYCLnf21OqrpQDbEyIHOznXjqK7yA2Lucmc9lMKl/gO604Pl7lZG2KqW5deeU4nUCKm4lcgkHFu/OGVDbPTlzfVZNbqDI4KpFfnm/NPAJngSJwdB04t89/1O/w1cDnyilFU="

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# 用戶會話管理
user_sessions = {}


@app.route("/", methods=["POST"])
def linebot():
    body = request.get_data(as_text=True)
    json_data = json.loads(body)
    print(json_data)
    try:
        signature = request.headers["X-Line-Signature"]
        handler.handle(body, signature)
        tk = json_data["events"][0]["replyToken"]

        # 如果事件標記為重送，不回覆
        if json_data["events"][0]["deliveryContext"].get("isRedelivery"):
            print("重送事件，跳過回覆")
            return "OK"

        msg = json_data["events"][0]["message"]["text"]
        user_id = json_data["events"][0]["source"]["userId"]

        # 修正查詢語法，確保只查找有 children 的用戶
        user_data = db.personal.find_one(
            {"children": {"$elemMatch": {"line_user_id": user_id}}}
        )

        # 如果 user_data 不存在，或 user_data["children"] 為空，則停止回應
        if not user_data or not user_data.get("children"):
            print("該用戶沒有 children，停止回應")
            return "OK"

        info_dict = {}  # 用來保存年齡與興趣
        for child in user_data["children"]:
            if child.get("line_user_id") == user_id:
                birthdate_str = child.get("birthdate")
                interests = child.get("interests")
                birthdate = datetime.strptime(birthdate_str, "%Y-%m-%d")
                today = datetime.today()
                age = (
                    today.year
                    - birthdate.year
                    - ((today.month, today.day) < (birthdate.month, birthdate.day))
                )
                info_dict = {"age": age, "interests": interests}
                break  # 找到匹配的 child 就跳出迴圈

        # 若 info_dict 仍為空，代表用戶的 children 資料沒有匹配，阻擋 AI 回應
        if not info_dict:
            print("用戶的 children 資料沒有匹配，停止回應")
            return "OK"

        # 確保該 user_id 已建立對話代理
        if user_id not in user_sessions:
            try:
                user_sessions[user_id] = DialogueAgent(
                    api_key="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"
                )
            except Exception as e:
                line_bot_api.reply_message(
                    tk, TextSendMessage(text=f"無法初始化對話代理：{str(e)}")
                )
                return "OK"

        agent = user_sessions[user_id]
        context_info = (
            f"用户年龄: {info_dict.get('age')}, 兴趣: {info_dict.get('interests')}。"
        )
        full_prompt = context_info + "\n" + msg

        response = agent.process_message(full_prompt)
        text_message = TextSendMessage(text=response)
        line_bot_api.reply_message(tk, text_message)

    except Exception as e:
        print("error: " + str(e))
    return "OK"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
