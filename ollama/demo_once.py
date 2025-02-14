import requests
import json

# Ollama 的 API 地址
url = "http://localhost:11434/api/generate"

# 请求数据
data = {
    "model": "deepseek-r1:7b",  # 使用的模型名称
    "prompt": "务必用中文回复：我现在希望你帮我写一个小学三年级的作文，关于香港旅游的",  # 你的输入提示
    "stream": False,  # 不使用流式输出，直接返回完整结果
    "max_tokens": 500  # 生成的最大 token 数量
}

# 发送 POST 请求
response = requests.post(url, json=data)

if response.status_code == 200:
    try:
        # 解析响应的 JSON 数据
        result = response.json()  # 直接解析整个响应的 JSON 数据
        print(result.get("response", "没有返回内容"))
    except json.JSONDecodeError as e:
        print("JSON 解码失败:", e)
else:
    print("请求失败，状态码:", response.status_code)
    print("响应内容:", response.text)

