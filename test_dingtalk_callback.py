"""
测试钉钉回调接口
"""
import requests
import time
import hmac
import hashlib
import base64
from urllib.parse import quote

# 配置
CALLBACK_URL = "http://localhost:8000/api/v1/dingtalk/callback"
SECRET = "your-secret-here"  # 替换为你的密钥

def generate_sign(secret):
    """生成签名"""
    timestamp = str(round(time.time() * 1000))
    secret_enc = secret.encode('utf-8')
    string_to_sign = f'{timestamp}\n{secret}'
    string_to_sign_enc = string_to_sign.encode('utf-8')
    hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
    sign = quote(base64.b64encode(hmac_code))
    return timestamp, sign

# 模拟钉钉回调请求
timestamp, sign = generate_sign(SECRET)

headers = {
    "Content-Type": "application/json",
    "x-dingtalk-timestamp": timestamp,
    "x-dingtalk-sign": sign
}

data = {
    "msgtype": "text",
    "text": {
        "content": "这是个什么任务，我忘了"
    },
    "senderId": "test_user_id",
    "senderNick": "测试用户"
}

try:
    response = requests.post(CALLBACK_URL, json=data, headers=headers, timeout=5)
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
except Exception as e:
    print(f"请求失败: {e}")
