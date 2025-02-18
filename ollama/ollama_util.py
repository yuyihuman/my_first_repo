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
    prompt1=str(f'{material}\n')
    prompt2=str('根据上面的文章创作一篇引人入胜的小短文，字数在1200字左右，每个段落不要超过300字，整个文章都使用简体中文，不要出现其他语言，给整个文章起一个引人入胜的标题，文章格式应该是###标题###\\n段落1\\n段落2\n')  # 你的输入提示
    prompt=prompt1+prompt2
    data = {
        "model": model_name,  # 使用的模型名称
        "prompt": prompt,
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
            with open(f"{title}_1.txt", "w", encoding="utf-8") as f:
                f.write(output)
            # 删除 </think> 之前的部分
            output = re.sub(r'^.*?</think>', '', output, flags=re.DOTALL)
            with open(f"{title}_2.txt", "w", encoding="utf-8") as f:
                f.write(output)
            print("处理后的内容已保存到文件中")
            return output
        except json.JSONDecodeError as e:
            print("JSON 解码失败:", e)
    else:
        print("请求失败，状态码:", response.status_code)
        print("响应内容:", response.text)

def translator(model="70b_2", material="", title="default"):
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
    prompt1=str(f'{material}\n')
    prompt2=str('你现在是一个翻译人员，请你翻译上面这段文字，删除所有特殊字符，将所有人名队名公司名称都翻译成中文，不要改变原文的格式\n')
    prompt=prompt1+prompt2
    data = {
        "model": model_name,  # 使用的模型名称
        "prompt": prompt,
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
            with open(f"{title}_translate1.txt", "w", encoding="utf-8") as f:
                f.write(output)
            # 删除 </think> 之前的部分
            output = re.sub(r'^.*?</think>', '', output, flags=re.DOTALL)
            output = output.replace("\n\n","\n\t")
            with open(f"{title}_translate2.txt", "w", encoding="utf-8") as f:
                f.write(output)
            print("处理后的内容已保存到文件中")
        except json.JSONDecodeError as e:
            print("JSON 解码失败:", e)
    else:
        print("请求失败，状态码:", response.status_code)
        print("响应内容:", response.text)

def article_motifier(model="70b_3", material="", title="default"):
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
    prompt1=str(f'{material}\n')
    prompt2=str('你现在是一个专栏作家，请你根据上面这段文字的内容，写一篇专栏，字数在800字左右，每个段落不要超过300字，语言尽量轻快简洁，给整个文章起一个引人入胜的标题，小段落不需要标题，文章格式应该是###标题###\\n段落1\\n段落2\n')
    prompt=prompt1+prompt2
    data = {
        "model": model_name,  # 使用的模型名称
        "prompt": prompt,
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
            with open(f"{title}_modify1.txt", "w", encoding="utf-8") as f:
                f.write(output)
            # 删除 </think> 之前的部分
            output = re.sub(r'^.*?</think>', '', output, flags=re.DOTALL)
            output = re.sub(r'\*\*.*?\*\*', '', output)
            output = output.replace("\n\n","\n\t")
            with open(f"{title}_modify2.txt", "w", encoding="utf-8") as f:
                f.write(output)
            print("处理后的内容已保存到文件中")
        except json.JSONDecodeError as e:
            print("JSON 解码失败:", e)
    else:
        print("请求失败，状态码:", response.status_code)
        print("响应内容:", response.text)