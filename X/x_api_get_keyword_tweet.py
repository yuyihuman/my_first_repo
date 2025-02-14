import requests
from requests_oauthlib import OAuth1

# API 密钥和令牌
API_KEY = "vi5ugDukdjDG3bXySWh3M44mL"
API_SECRET_KEY = "pQyqjFjnh0aAJTstmPfOJjjQPzv4k6Kkil2uF9spL05MJkPd8W"
ACCESS_TOKEN = "1017416192259223554-iFISMliupx3fp1Jyk3LesFyUXcuvYd"
ACCESS_TOKEN_SECRET = "EfVufI0UpqZ3VTqfu2dwxk9ukmlqtmM8cCaDiNH0KJyO2"

# 设置认证
auth = OAuth1(API_KEY, API_SECRET_KEY, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)

# API 端点 URL
url = "https://api.x.com/2/tweets/search/recent"

# 请求参数
keyword = "technology"
params = {
    "query": keyword,  # 查询关键词
    "max_results": 100,  # 返回最多 10 条推文
    "expansions": "attachments.media_keys",  # 扩展推文中的媒体信息
    "media.fields": "url,type"  # 返回媒体的 URL 和类型
}

# 发送请求
response = requests.get(url, auth=auth, params=params)

# 检查响应状态码
if response.status_code == 200:
    data = response.json()
    tweets = data.get("data", [])
    media = data.get("includes", {}).get("media", [])
    
    # 构建 media_key 到 URL 和类型的映射
    media_map = {m["media_key"]: {"url": m.get("url", "无 URL"), "type": m.get("type", "unknown")} for m in media}

    # 输出每条推文的信息
    for tweet in tweets:
        print(f"推文 ID: {tweet['id']}")
        print(f"推文内容: {tweet['text']}")
        
        # 输出推文中包含的图片或视频 URL
        media_keys = tweet.get("attachments", {}).get("media_keys", [])
        if media_keys:
            for key in media_keys:
                media_info = media_map.get(key, {})
                media_url = media_info.get("url", "无 URL")
                media_type = media_info.get("type", "unknown")
                print(f"媒体类型: {media_type}, URL: {media_url}")
        else:
            print("无媒体")
        print()
else:
    print(f"请求失败，状态码: {response.status_code}")
    print(f"错误信息: {response.text}")
