from openai import OpenAI

# 指向本地Ollama服务
client = OpenAI(
    base_url="http://192.168.31.80:11435/v1",  # 注意/v1路径
    api_key="ollama"  # 伪密钥，实际可不填但需占位
)

response = client.chat.completions.create(
    model="70b_self",  # 使用本地已下载的模型名称
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello"},
    ],
    stream=False
)

print(response.choices[0].message.content)