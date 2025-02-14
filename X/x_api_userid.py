import requests
import json
from requests_oauthlib import OAuth1

# API 密钥和令牌
API_KEY = "vi5ugDukdjDG3bXySWh3M44mL"
API_SECRET_KEY = "pQyqjFjnh0aAJTstmPfOJjjQPzv4k6Kkil2uF9spL05MJkPd8W"
ACCESS_TOKEN = "1017416192259223554-iFISMliupx3fp1Jyk3LesFyUXcuvYd"
ACCESS_TOKEN_SECRET = "EfVufI0UpqZ3VTqfu2dwxk9ukmlqtmM8cCaDiNH0KJyO2"

# 设置认证
auth = OAuth1(API_KEY, API_SECRET_KEY, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)

# 查询用户名为 'xxxxx' 的用户信息
username = "realDonaldTrump"
url = f"https://api.x.com/2/users/by/username/{username}"

response = requests.get(url, auth=auth)

# 读取现有的 JSON 文件
with open("user_id.json", "r", encoding="utf-8") as file:
    user_data = json.load(file)

if response.status_code == 200:
    # 获取 API 返回的用户数据
    new_user_data = response.json()['data']
    new_user_info = {
        new_user_data['username']: {
            'id': new_user_data['id'],
            'name': new_user_data['name']
        }
    }

    # 检查该用户是否已存在
    if new_user_data['username'] not in user_data:
        # 将新用户数据添加到现有的用户数据中
        user_data.update(new_user_info)

        # 将更新后的数据写回到 JSON 文件
        with open("user_id.json", "w", encoding="utf-8") as file:
            json.dump(user_data, file, ensure_ascii=False, indent=4)

        print(f"成功添加用户 {new_user_data['username']} 的信息到 user_id.json")
    else:
        print(f"用户 {new_user_data['username']} 已存在，未做更新。")
else:
    print(f"请求失败，状态码: {response.status_code}")
    print(f"错误信息: {response.text}")
