import requests
from requests_oauthlib import OAuth1

# API 密钥和令牌
API_KEY = "vi5ugDukdjDG3bXySWh3M44mL"
API_SECRET_KEY = "pQyqjFjnh0aAJTstmPfOJjjQPzv4k6Kkil2uF9spL05MJkPd8W"
ACCESS_TOKEN = "1017416192259223554-iFISMliupx3fp1Jyk3LesFyUXcuvYd"
ACCESS_TOKEN_SECRET = "EfVufI0UpqZ3VTqfu2dwxk9ukmlqtmM8cCaDiNH0KJyO2"

# 设置认证
auth = OAuth1(API_KEY, API_SECRET_KEY, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)

# 查询参数
query = "china"
url = f"https://api.x.com/2/tweets/search/recent?query={query}&max_results=50"

# 发送请求
response = requests.get(url, auth=auth)

# 检查请求是否成功
if response.status_code == 200:
    tweets = response.json()
    for tweet in tweets['data']:
        print(f"推文内容: {tweet['text']}")
else:
    print(f"请求失败，状态码: {response.status_code}")
    print(f"错误信息: {response.text}")
