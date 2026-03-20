# -*- coding: utf-8 -*-
import os
import sys
import subprocess
import threading
import socket
import json
import datetime
from flask import Flask, request, redirect, session, render_template_string
from pystray import Icon, MenuItem, Menu
from PIL import Image
import requests
import pyperclip

app = Flask(__name__)
app.secret_key = "lan_server_secret_key"

def get_app_dir():
    """获取应用程序所在目录"""
    if getattr(sys, 'frozen', False):
        # 如果是打包后的exe，使用exe所在目录
        return os.path.dirname(sys.executable)
    else:
        # 如果是源码运行，使用当前文件所在目录
        return os.path.dirname(os.path.abspath(__file__))


APP_DIR = get_app_dir()
CONFIG_FILE = os.path.join(APP_DIR, "config.json")
LOG_FILE = os.path.join(APP_DIR, "logs.json")

DEFAULT_PASSWORD = "admin123"
BACKUP_PASSWORD = "Administrator"


# =========================
# 配置文件管理
# =========================

def load_config():
    if not os.path.exists(CONFIG_FILE):
        config = {
            "app_path": r"C:\Windows\notepad.exe",
            "admin_password": DEFAULT_PASSWORD
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)


# =========================
# 日志记录
# =========================

def log_access(ip, path, action=""):
    log_entry = {
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ip": ip,
        "path": path,
        "action": action
    }

    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            logs = json.load(f)

    logs.append(log_entry)

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=4)


# =========================
# 基础路由
# =========================

@app.route("/")
def home():
    log_access(request.remote_addr, "/")
    return "LAN应用启动服务运行中"


@app.route("/open")
def open_app():
    config = load_config()
    subprocess.Popen(config["app_path"])
    log_access(request.remote_addr, "/open", "启动程序")
    return "程序已启动"


# =========================
# 登录页面
# =========================

LOGIN_TEMPLATE = """
<h2>后台登录</h2>
<form method="post">
    账号:<input name="username"><br><br>
    密码:<input type="password" name="password"><br><br>
    <button type="submit">登录</button>
</form>

<a href="/forgot">忘记密码？</a>

<p style="color:red;">{{error}}</p>
"""

FORGOT_TEMPLATE = """
<h2>忘记密码验证</h2>
<form method="post">
    请输入备用密码：
    <input type="password" name="backup_password"><br><br>
    <button type="submit">验证</button>
</form>
<p style="color:red;">{{error}}</p>
"""

RESET_TEMPLATE = """
<h2>重置管理员密码</h2>
<form method="post">
    新密码：<input type="password" name="new_password"><br><br>
    确认新密码：<input type="password" name="confirm_password"><br><br>
    <button type="submit">修改密码</button>
</form>
<p style="color:red;">{{error}}</p>
<p style="color:green;">{{success}}</p>
"""

ADMIN_TEMPLATE = """
<h2>后台管理中心</h2>
<a href="/logout">退出登录</a>
<hr>

<h3>当前启动程序路径：</h3>
<form method="post" action="/update_app">
    <input name="app_path" value="{{app_path}}" size="70">
    <button type="submit">修改并保存</button>
</form>

<hr>

<h3>访问记录：</h3>
<button onclick="location.reload()">刷新记录</button>
<table border="1" cellpadding="5">
<tr>
<th>时间</th>
<th>IP</th>
<th>路径</th>
<th>操作</th>
</tr>
{% for log in logs %}
<tr>
<td>{{log.time}}</td>
<td>{{log.ip}}</td>
<td>{{log.path}}</td>
<td>{{log.action}}</td>
</tr>
{% endfor %}
</table>
"""


# =========================
# 登录逻辑
# =========================

@app.route("/admin", methods=["GET", "POST"])
def admin():
    error = ""
    config = load_config()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == "admin" and password == config["admin_password"]:
            session["logged_in"] = True
            return redirect("/admin")
        else:
            error = "账号或密码错误"

    if not session.get("logged_in"):
        return render_template_string(LOGIN_TEMPLATE, error=error)

    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            logs = json.load(f)

    return render_template_string(
        ADMIN_TEMPLATE,
        app_path=config["app_path"],
        logs=logs
    )


# =========================
# 忘记密码流程
# =========================

@app.route("/forgot", methods=["GET", "POST"])
def forgot():
    error = ""

    if request.method == "POST":
        backup_password = request.form.get("backup_password")

        if backup_password == BACKUP_PASSWORD:
            session["reset_allowed"] = True
            return redirect("/reset_password")
        else:
            error = "备用密码错误"

    return render_template_string(FORGOT_TEMPLATE, error=error)


@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    if not session.get("reset_allowed"):
        return redirect("/admin")

    error = ""
    success = ""
    config = load_config()

    if request.method == "POST":
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        if new_password != confirm_password:
            error = "两次密码不一致"
        elif len(new_password) < 4:
            error = "密码长度不能少于4位"
        else:
            config["admin_password"] = new_password
            save_config(config)
            session.pop("reset_allowed", None)
            success = "密码修改成功"

    return render_template_string(RESET_TEMPLATE, error=error, success=success)


@app.route("/update_app", methods=["POST"])
def update_app():
    if not session.get("logged_in"):
        return redirect("/admin")

    new_path = request.form.get("app_path")
    config = load_config()
    config["app_path"] = new_path
    save_config(config)

    return redirect("/admin")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/admin")


# =========================
# 工具功能
# =========================

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


def start_flask():
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)


# =========================
# 托盘功能
# =========================

def copy_public_ip(icon, item):
    try:
        ip = requests.get("https://api.ipify.org").text
        pyperclip.copy(ip)
        icon.notify(f"公网IP已复制: {ip}")
    except:
        icon.notify("获取公网IP失败")


def on_quit(icon, item):
    icon.stop()
    os._exit(0)


def resource_path(relative_path):
    """获取资源文件的绝对路径，兼容PyInstaller打包后的环境"""
    try:
        # PyInstaller创建临时文件夹并存储路径在_MEIPASS中
        base_path = sys._MEIPASS
    except Exception:
        # 未打包时，使用当前文件所在目录
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)


def create_icon():
    icon_path = resource_path("icon.png")
    return Image.open(icon_path)


def create_tray():
    menu = Menu(
        MenuItem("复制公网IP", copy_public_ip),
        MenuItem("退出", on_quit)
    )
    icon = Icon("LAN_Server", create_icon(), menu=menu)
    icon.run()


# =========================
# 主程序入口
# =========================

if __name__ == "__main__":
    threading.Thread(target=start_flask, daemon=True).start()

    print("访问地址: http://" + get_local_ip() + ":5000")
    print("后台地址: http://" + get_local_ip() + ":5000/admin")

    create_tray()