import requests
import json
import re

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

def story_writer(model="70b", material="", title="default"):
    # 根据参数选择配置
    config = MODEL_CONFIG[model]
    url = config["url"]
    model_name = config["model_name"]
    # 替换非法字符
    title = title.replace('|', '-')  # 将 | 替换为 -
    title = title.replace(':', '-')  # 将 : 替换为 -
    title = title.replace('?', '-')  # 将 ? 替换为 -
    title = title.replace('*', '-')  # 将 * 替换为 -
    title = title.replace('"', '-')  # 将 " 替换为 -
    title = title.replace('<', '-')  # 将 < 替换为 -
    title = title.replace('>', '-')  # 将 > 替换为 -

    # 请求数据
    data = {
        "model": model_name,  # 使用的模型名称
        "prompt": f'[材料]{material}[/材料]'+'[材料]与[/材料]之间是素材,请利用这些素材创作一篇引人入胜的小短文,字数在1200字左右,每段不要超过300字,输出时不需要换行符,使用简体中文,给出吸引人的标题',  # 你的输入提示
        "stream": False,  # 不使用流式输出，直接返回完整结果
        "max_tokens": 1500  # 生成的最大 token 数量
    }
    # 发送 POST 请求
    response = requests.post(url, json=data)

    if response.status_code == 200:
        try:
            # 解析响应的 JSON 数据
            result = response.json()  # 直接解析整个响应的 JSON 数据
            output = result.get("response", "没有返回内容")

            # # 删除 </think> 之前的部分
            # output = re.sub(r'^.*?</think>', '', output, flags=re.DOTALL)

            # 替换所有换行符
            output = output.replace('\n\n', '\n\t')

            # 保存到 output.txt 文件
            with open(f"{title}.txt", "w", encoding="utf-8") as f:
                f.write(output)

            print("处理后的内容已保存到 output.txt 文件中")

        except json.JSONDecodeError as e:
            print("JSON 解码失败:", e)
    else:
        print("请求失败，状态码:", response.status_code)
        print("响应内容:", response.text)