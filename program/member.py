import pymongo
import certifi  # 確保ssl為最新的
from pymongo import MongoClient
from bson.objectid import ObjectId
import datetime
import hashlib
import os
import qrcode
import requests
import mysql.connector

# 替換為你的 MongoDB 連接字串和憑據(複製mongo網站-cluster-connect)
uri = "mongodb+srv://a0988398645:a0910035817@andrew.3xi60lp.mongodb.net/?retryWrites=true&w=majority&appName=andrew"

# 創建客戶端並連接到伺服器
client = MongoClient(uri, tlsCAFile=certifi.where())

# 请替换为你在 LINE Developers 后台获取的资料
LINE_CLIENT_ID = "2007004922"
LINE_CLIENT_SECRET = "6e36b4d69b8f2b23e446c4dbce29a040"
LINE_REDIRECT_URI = "http://127.0.0.1:3000/line_callback"

# 發送 ping 以確認成功連接
try:
    client.admin.command("ping")
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(f"An error occurred: {e}")

# 把資料放進資料庫
db = client.member  # 創建一個名為 'num1' 的資料庫

from flask import Flask
from flask import request
from flask import redirect
import json
from flask import render_template, url_for, flash
from flask import session

# 影音、文字或其他檔案，可以直接上傳網路，透過建立子資料夾-static，可以用來存放靜態檔案資料，並默認網址為:主機/static/檔案名稱
# 也可以修改網址路徑
app = Flask(
    __name__,
    static_folder="static",  # 資料夾名稱，記得這裡+逗號
    static_url_path="/",  # 網址路徑(http://127.0.0.1:3000/andrew/01.JPG)，如果改成'/'，這樣網址就變成http://127.0.0.1:3000/01.JPG
)

app.secret_key = "secretkey"  # 使用session必須設定secret key


@app.route("/")
def index():
    session["cart1"] = 0
    session["cart2"] = 0
    session["cart3"] = 0
    return render_template("index.html")


@app.route("/member")
def member():
    session["name"] = ""
    session["email"] = ""
    session["account"] = ""
    session["password"] = ""
    return render_template("member.html")


@app.route("/user", methods=["POST"])
def user():
    name = request.form.get("name")
    email = request.form.get("email")
    account = request.form.get("account")
    password = request.form.get("password")
    session["name"] = (
        name  # session可以儲存使用者輸入的資料，['jen']裡面的文字可以任意(記得先from flask import，並且先設定secret key)
    )
    session["email"] = email
    session["account"] = account
    session["password"] = password
    data = {"name": name, "email": email, "account": account, "password": password}
    personal = db.personal
    result1 = personal.find_one({"email": email})
    result2 = personal.find_one({"account": account})

    if len(password) < 8 or len(password) > 16:
        flash("密碼不符合規定", "error")
        return redirect(url_for("member"))

    a = {"!", "@", "#", "$", "%"}
    s = set(password)
    c = {
        "a",
        "b",
        "c",
        "d",
        "e",
        "f",
        "g",
        "h",
        "i",
        "j",
        "k",
        "l",
        "m",
        "n",
        "o",
        "p",
        "q",
        "r",
        "s",
        "t",
        "u",
        "v",
        "w",
        "x",
        "y",
        "z",
    }
    d = {
        "A",
        "B",
        "C",
        "D",
        "E",
        "F",
        "G",
        "H",
        "I",
        "J",
        "K",
        "L",
        "M",
        "N",
        "O",
        "P",
        "Q",
        "R",
        "S",
        "T",
        "U",
        "V",
        "W",
        "X",
        "Y",
        "Z",
    }
    e = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9"}
    A = s & a
    C = s & c
    D = s & d
    E = s & e
    s2 = s - a
    s2 = s2 - c
    s2 = s2 - d
    s2 = s2 - e
    if s2:
        flash("密碼不符合規定", "error")
        return redirect(url_for("member"))

    if A:
        if C:
            if D:
                if E:
                    print(password)
                    if result1 != None:
                        flash("信箱已被註冊", "error")
                        return redirect(url_for("member"))
                    elif result2 != None:
                        flash("帳號已被註冊", "error")
                        return redirect(url_for("member"))
                    else:
                        cart = db.cart
                        inv = cart.find_one(ObjectId("665d8aeaa8a46f4fb4e6e80a"))
                        n1 = inv["勝利"]
                        n2 = inv["暴力丹"]
                        n3 = inv["江山燕"]
                        inventory = {"n1": n1, "n2": n2, "n3": n3}
                        number = []
                        members = {
                            "date1": "6/1",
                            "date2": "6/2",
                            "date3": "6/8",
                            "date4": "6/9",
                            "date5": "6/15",
                            "date6": "6/16",
                            "date7": "6/22",
                            "date8": "6/23",
                            "date9": "6/29",
                            "date10": "6/30",
                            "number": number,
                            "name": name,
                        }
                        personal.insert_one(
                            {
                                "name": name,
                                "email": email,
                                "account": account,
                                "password": password,
                            }
                        )
                        return render_template(
                            "user.html", data=data, members=members, inventory=inventory
                        )  # 第一個data是字典data，第二個data是html的data

    flash("密碼不符合規定", "error")
    return redirect(url_for("member"))


@app.route("/users", methods=["POST"])
def users():
    productions = db.productions
    personal = db.personal
    if session["account"] == "":
        account = request.form.get("account")
        password = request.form.get("password")
        print(account)
        session["account"] = account
        session["password"] = password
    account = session["account"]
    password = session["password"]
    result1 = personal.find_one({"password": password})
    result2 = personal.find_one({"account": account})

    if result1 == None:
        flash("密碼錯誤", "error")
        return redirect(url_for("signin"))
    elif result2 == None:
        flash("帳號錯誤", "error")
        return redirect(url_for("signin"))
    else:
        name = result1["name"]
        session["name"] = name
        name = session["name"]
        account = session["account"]
        password = session["password"]

    data = {"account": account, "password": password, "name": name}
    return render_template("user.html", data=data)


# ...existing code...


@app.route("/backpack", methods=["GET", "POST"])
def backpack():
    if request.method == "POST":
        parent_name = request.form.get("parent_name")  # 家長姓名
        child_name = request.form.get("child_name")  # 小孩姓名
        child_gender = request.form.get("child_gender")  # 小孩性別
        child_line_id = request.form.get("child_line_id")  # 小孩 Line ID
        child_birthdate = request.form.get("child_birthdate")  # 小孩出生年月日
        child_interests = request.form.get("child_interests", "")  # 興趣（可選填）
        child_special_conditions = request.form.get(
            "child_special_conditions", ""
        )  # 特殊狀況（可選填）

        if not all(
            [parent_name, child_name, child_gender, child_line_id, child_birthdate]
        ):
            flash("請填寫所有必填欄位！", "error")
            return redirect(url_for("backpack"))

        # 查找家長是否存在
        parent = db.personal.find_one({"name": parent_name})
        if not parent:
            flash("未找到該家長的帳戶，請先註冊！", "error")
            return redirect(url_for("backpack"))

        # 生成唯一金鑰
        timestamp = datetime.datetime.utcnow().isoformat()
        unique_key = hashlib.sha256(f"{parent_name}{timestamp}".encode()).hexdigest()

        # 構造小孩資料
        child_data = {
            "name": child_name,
            "gender": child_gender,
            "line_id": child_line_id,
            "birthdate": child_birthdate,
            "interests": child_interests,
            "special_conditions": child_special_conditions,
            "unique_key": unique_key,
            "timestamp": timestamp,
        }

        # 更新家長文檔，將小孩資料追加到 `children` 陣列
        db.personal.update_one(
            {"name": parent_name}, {"$push": {"children": child_data}}
        )

        # 生成綁定 URL（用於 QR Code 內容）
        bind_url = url_for("bind", key=unique_key, _external=True)

        # 生成 QR Code 圖片並存檔於 static/qrcodes/
        qr_dir = os.path.join("static", "qrcodes")
        if not os.path.exists(qr_dir):
            os.makedirs(qr_dir)

        qr_filename = f"{unique_key}.png"
        qr_path = os.path.join(qr_dir, qr_filename)  # 确保路径正确

        qr_img = qrcode.make(bind_url)
        qr_img.save(qr_path)  # 存储在正确的路径里

        flash("資料提交成功！請掃描 QR Code 綁定到您的 Line 商店", "success")
        return render_template(
            "qr_display.html", qr_code=qr_filename, bind_url=bind_url
        )

    return render_template("backpack.html")


@app.route("/bind")
def bind():
    # 获取绑定码
    unique_key = request.args.get("key")
    if not unique_key:
        return "無效的綁定請求", 400

    # 构造 LINE OAuth 授权 URL
    # scope: profile openid 表示需要获取用户 profile 信息
    line_auth_url = (
        "https://access.line.me/oauth2/v2.1/authorize?"
        f"response_type=code&client_id={LINE_CLIENT_ID}&redirect_uri={LINE_REDIRECT_URI}"
        f"&state={unique_key}&scope=profile%20openid"
    )

    return render_template(
        "bind.html", unique_key=unique_key, line_auth_url=line_auth_url
    )


@app.route("/line_callback")
def line_callback():
    # 从 LINE OAuth 回调中获取 code 和 state
    code = request.args.get("code")
    state = request.args.get("state")  # state 即之前传入的 unique_key
    if not code or not state:
        return "缺少參數", 400

    # 交换 code 获取 access_token
    token_url = "https://api.line.me/oauth2/v2.1/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": LINE_REDIRECT_URI,
        "client_id": LINE_CLIENT_ID,
        "client_secret": LINE_CLIENT_SECRET,
    }
    token_response = requests.post(token_url, headers=headers, data=data)
    token_data = token_response.json()
    access_token = token_data.get("access_token")
    if not access_token:
        return "獲取 access token 失敗", 400

    # 利用 access_token 获取用户 profile
    profile_url = "https://api.line.me/v2/profile"
    profile_response = requests.get(
        profile_url, headers={"Authorization": f"Bearer {access_token}"}
    )
    profile_data = profile_response.json()
    line_user_id = profile_data.get("userId")
    if not line_user_id:
        return "獲取用戶資料失敗", 400

    # 将获取到的 line_user_id 更新到数据库中对应 unique_key 的记录上
    # 假设每个 unique_key 是唯一的，并且存储在 children 数组中
    result = db.personal.update_one(
        {"children.unique_key": state},
        {"$set": {"children.$.line_user_id": line_user_id}},
    )
    if result.modified_count == 0:
        return "更新資料失敗", 400

    return f"綁定成功！您的 Line userId 為：{line_user_id} <br><a href='/'>回首頁</a>"


@app.route("/signin")
def signin():
    session["name"] = ""
    session["email"] = ""
    session["account"] = ""
    session["password"] = ""
    return render_template("signin.html")


@app.route("/erro")
def erro():
    message = request.args.get("msg", "erro")
    flash(message, "error")
    return redirect(url_for("index"))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/program")
def program():
    return render_template("program.html")


@app.route("/category")
def category():
    return render_template("category.html")


@app.route("/video/<video_id>/<keyword>/<category>")
def video(video_id, keyword, category):
    if "&" in video_id or "?" in video_id:
        video_id = video_id.split("&")[0]  # 移除时间戳或其他参数
    return render_template(
        "yt_video.html", message=video_id, keyword=keyword, category=category
    )


@app.route("/feedback", methods=["POST"])
def feedback():
    thedb = request.form.get("category")
    db_config = {
        "host": "10.167.214.47",
        "user": "admin",
        "password": "dv107",
        "database": thedb,
    }

    video_id = request.form.get("video_id")
    table = request.form.get("keyword")
    new_difficulty = request.form.get("difficulty")
    new_recommendation = request.form.get("rating")
    print(
        f"收到的數據：video_id={video_id}, table={table}, new_difficulty={new_difficulty}, new_recommendation={new_recommendation}"
    )

    # 轉換 `recommendation`
    difficulty_map = {"簡單": 2, "入門": 4, "中等": 6, "進階": 8, "專業": 10}
    new_difficulty = difficulty_map.get(new_difficulty, 0)

    if not new_difficulty or not new_recommendation:
        flash("您未提供完整回饋，資料庫未更新。", "warning")
        return redirect(request.referrer)

    try:
        new_difficulty = float(new_difficulty)
        new_recommendation = float(new_recommendation)
        print(
            f"轉換後的數據：new_difficulty={new_difficulty}, new_recommendation={new_recommendation}"
        )
    except ValueError:
        flash("回饋數據格式錯誤。", "error")
        return redirect(request.referrer)

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        print(f"成功連接到 {db_config['database']} 資料庫")

        select_query = (
            f"SELECT difficulty, recommendation, watch FROM {table} WHERE link = %s"
        )
        cursor.execute(select_query, (video_id,))
        row = cursor.fetchone()

        if row:
            current_watch = row["watch"] or 0
            current_avg_difficulty = row["difficulty"] or 0.0
            current_avg_recommendation = row["recommendation"] or 0.0
            new_watch = current_watch + 1

            # Bayesian 平滑計算
            global_avg_query = f"SELECT AVG(recommendation) AS global_avg FROM {table}"
            cursor.execute(global_avg_query)
            global_avg = cursor.fetchone()["global_avg"] or 5

            C = 10
            if new_watch < C:
                new_avg_recommendation = (
                    C * global_avg
                    + current_watch * current_avg_recommendation
                    + new_recommendation
                ) / (C + new_watch)
            else:
                new_avg_recommendation = (
                    new_recommendation * 0.5 * 10
                    + current_avg_recommendation * 0.5 * 100
                ) / 110

            new_avg_difficulty = (
                current_avg_difficulty
                + (new_difficulty - current_avg_difficulty) / new_watch
            )

            update_query = f"""
                UPDATE {table} 
                SET difficulty = %s, recommendation = %s, watch = %s
                WHERE link = %s
            """
            cursor.execute(
                update_query,
                (new_avg_difficulty, new_avg_recommendation, new_watch, video_id),
            )
            if cursor.rowcount == 0:
                print("⚠️  沒有任何行被更新，請檢查 SQL 條件")
        else:
            watch = 1
            insert_query = f"""
                INSERT INTO {table} (link, difficulty, recommendation, watch)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(
                insert_query, (video_id, new_difficulty, new_recommendation, watch)
            )

        conn.commit()
        print("資料更新成功！")
    except Exception as e:
        flash(f"資料更新失敗: {str(e)}", "error")
        return redirect(request.referrer)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    flash("回饋已成功提交，謝謝您的寶貴意見！", "success")
    return redirect(request.referrer)


app.run(port=3000)  # port主機名
