import requests
from requests_oauthlib import OAuth1

# API 密钥和令牌
API_KEY = "vi5ugDukdjDG3bXySWh3M44mL"
API_SECRET_KEY = "pQyqjFjnh0aAJTstmPfOJjjQPzv4k6Kkil2uF9spL05MJkPd8W"
ACCESS_TOKEN = "1017416192259223554-iFISMliupx3fp1Jyk3LesFyUXcuvYd"
ACCESS_TOKEN_SECRET = "EfVufI0UpqZ3VTqfu2dwxk9ukmlqtmM8cCaDiNH0KJyO2"

# 设置认证
auth = OAuth1(API_KEY, API_SECRET_KEY, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)

# API 端点 - 获取当前认证用户的信息
url = "https://api.x.com/1.1/account/verify_credentials.json"

# 发送请求
response = requests.get(url, auth=auth)

# 检查请求是否成功
if response.status_code == 200:
    user_info = response.json()
    print(f"用户昵称: {user_info['name']}")
    print(f"用户名: {user_info['screen_name']}")
    print(f"描述: {user_info['description']}")
    print(f"关注者数: {user_info['followers_count']}")
else:
    print(f"请求失败，状态码: {response.status_code}")
    print(f"错误信息: {response.text}")
