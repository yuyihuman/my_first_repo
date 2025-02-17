import requests
import json
import argparse

# 定义两组 URL 和模型名称
MODEL_CONFIG = {
    "32b": {
        "url": "http://192.168.31.80:11434/api/generate",
        "model_name": "deepseek-r1:32b"
    },
    "70b": {
        "url": "http://192.168.31.80:11435/api/generate",
        "model_name": "deepseek-r1:70b"
    },
    "70b_2": {
        "url": "http://192.168.31.80:11436/api/generate",
        "model_name": "deepseek-r1:70b"
    },
    "70b_3": {
        "url": "http://192.168.31.80:11437/api/generate",
        "model_name": "deepseek-r1:70b"
    }
}

# 设置命令行参数解析
parser = argparse.ArgumentParser(description="调用 Ollama API 进行翻译")
parser.add_argument("--model", type=str, choices=["32b", "70b", "70b_2", "70b_3"], default="70b", help="32b 或 70b 或 70b_2 或 70b_3")
args = parser.parse_args()

# 根据参数选择配置
config = MODEL_CONFIG[args.model]
url = config["url"]
model_name = config["model_name"]

# 请求数据
data = {
    "model": model_name,  # 使用的模型名称
    "prompt": "[要求]你现在是一个小学三年级学生，中国人[/要求]写一篇去香港旅游的作文",  # 你的输入提示
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