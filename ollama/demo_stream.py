import requests
import json

# Ollama 的 API 地址
url = "http://192.168.31.80:11434/api/generate"

# 请求数据
data = {
    "model": "deepseek-r1:32b",  # 使用的模型名称
    "prompt": "我现在希望你用中文帮我写一个小学三年级的作文，关于香港旅游的",  # 你的输入提示
    "stream": True,  # 是否流式输出（False 表示一次性返回完整结果）
    "max_tokens": 500  # 生成的最大 token 数量
}

# 发送 POST 请求
with requests.post(url, json=data, stream=True) as response:
    if response.status_code == 200:
        for line in response.iter_lines():
            if line:
                try:
                    # 解析每行的 JSON 数据
                    chunk = json.loads(line.decode('utf-8'))  # Decode and load each line separately
                    print(chunk.get("response"), end="", flush=True)
                except json.JSONDecodeError as e:
                    print("JSON 解码失败:", e)
    else:
        print("请求失败，状态码:", response.status_code)
        print("响应内容:", response.text)
