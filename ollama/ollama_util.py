import requests
import json
import re
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
            output = re.sub(r'</think>.*$', '', output, flags=re.DOTALL)
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

def chapter_writer(model="70b_3", material="", wordage=2500, title="第1章", style="年轻人", first_point=5, second_point=140, last_point=150, key_info="主角名称"):
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
    prompt2=str(f'你现在是一个长篇小说作家，请你仔细思考上面的小说大纲和前情介绍，要求：\n'
                f'1、使用中文完成{title}，不要使用任何英文单词\n'
                f'2、这个章节的字数要在{wordage}字左右，构思好足够的情节推进，防止内容不够无法达到字数要求\n'
                f'3、这个小说是写给{style}，请注意语言风格\n'
                f'4、根据本章节中推动故事发展的核心要素给这个章节起个名字\n'
                f'5、不要和其他章节重名，也不要一直使用类似的命名方式\n'
                f'6、第1章到第{first_point}章是小说世界的构建，第{first_point+1}章到第{second_point}章是主要剧情，第{second_point+1}章到第{last_point}章是小说的结局\n'
                f'7、注意故事的主角是{key_info}，请围绕主角推动剧情\n'
                f'8、输出文章的格式如下\n'
                f'###标题###\n'
                f'段落1\n'
                f'段落2\n')
    prompt=prompt1+prompt2
    # 按行分割字符串
    lines = prompt.splitlines()
    # 取最后 100 行
    last_100_lines = lines[-100:]
    # 重新组合成字符串
    result = '\n'.join(last_100_lines)
    # 打印结果
    print(result)
    data = {
        "model": model_name,  # 使用的模型名称
        "prompt": prompt,
        "stream": False,  # 不使用流式输出，直接返回完整结果
        "max_tokens": 10000  # 生成的最大 token 数量
    }
    # 发送 POST 请求
    response = requests.post(url, json=data)

    if response.status_code == 200:
        try:
            # 解析响应的 JSON 数据
            result = response.json()  # 直接解析整个响应的 JSON 数据
            output = result.get("response", "没有返回内容")
            with open(f"{title}_init.txt", "w", encoding="utf-8") as f:
                f.write(output)
            # 删除 </think> 之前的部分
            output = re.sub(r'^.*?</think>', '', output, flags=re.DOTALL)
            output = re.sub(r'</think>.*$', '', output, flags=re.DOTALL)
            output = re.sub(r'^.*\*\*.*\*\*.*\n?', '', output, flags=re.MULTILINE)
            output = re.sub(r'\n+', '\n', output).strip()
            output = re.sub(r'---.*', '', output, flags=re.DOTALL)
            output = output.replace("\n\n","\n")
            with open(f"{title}", "w", encoding="utf-8") as f:
                f.write(output)
            print("处理后的内容已保存到文件中")
        except json.JSONDecodeError as e:
            print("JSON 解码失败:", e)
    else:
        print("请求失败，状态码:", response.status_code)
        print("响应内容:", response.text)

def Outline_Generator(model="70b_3", material="", title="default"):
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
    prompt2=str(f'你现在是一个长篇小说作家，请你根据上面这段文字的要求，构思一个相应风格长篇小说的大纲，要求：\n'
                f'1、首先介绍整个小说的故事背景，核心设定和整体剧情，这部分尽量详细一些\n'
                f'2、构建一个人物档案，至少首先拟定10名主要人物，格式如下\n'
                f'$$1. 人物名称$$\n'
                f'- **年龄**：\n'
                f'- **性格**：\n'
                f'- **背景**：\n'
                f'- **关系**：\n'
                f'3、最后给这个小说起一个吸引人的标题\n'
                f'4、输出文章的格式如下\n'
                f'###文章标题###\n'
                f'###故事背景###\n'
                f'###核心设定###\n'
                f'###整体剧情###\n'
                f'###人物档案###\n'
                f'###结束语###\n')
    prompt=prompt1+prompt2
    print(prompt)
    data = {
        "model": model_name,  # 使用的模型名称
        "prompt": prompt,
        "stream": False,  # 不使用流式输出，直接返回完整结果
        "max_tokens": 10000  # 生成的最大 token 数量
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
            output = re.sub(r'</think>.*$', '', output, flags=re.DOTALL)
            output = output.replace("\n\n","\n")
            with open(f"{title}_modify2.txt", "w", encoding="utf-8") as f:
                f.write(output)
            print("处理后的内容已保存到文件中")
        except json.JSONDecodeError as e:
            print("JSON 解码失败:", e)
    else:
        print("请求失败，状态码:", response.status_code)
        print("响应内容:", response.text)

def summerizer(model="70b_3", material="", wordage=300):
    # 根据参数选择配置
    config = MODEL_CONFIG[model]
    url = config["url"]
    model_name = config["model_name"]

    # 请求数据
    prompt1=str(f'{material}\n')
    prompt2=str(f'请你根据上面材料，总结故事剧情概述，要求：\n'
                f'1、概述中要清晰的写出人物姓名\n'
                f'2、需要完整的将剧情推进体现出来'
                f'3、字数{wordage}字，不要分段\n')
    prompt=prompt1+prompt2
    data = {
        "model": model_name,  # 使用的模型名称
        "prompt": prompt,
        "stream": False,  # 不使用流式输出，直接返回完整结果
        "max_tokens": 10000  # 生成的最大 token 数量
    }
    # 发送 POST 请求
    response = requests.post(url, json=data)

    if response.status_code == 200:
        try:
            # 解析响应的 JSON 数据
            result = response.json()  # 直接解析整个响应的 JSON 数据
            output = result.get("response", "没有返回内容")
            with open(f"summerize_init.txt", "w", encoding="utf-8") as f:
                f.write(output)
            # 删除 </think> 之前的部分
            output = re.sub(r'^.*?</think>', '', output, flags=re.DOTALL)
            output = re.sub(r'</think>.*$', '', output, flags=re.DOTALL)
            output = output.replace("\n\n","\n")
            output = output.strip()
            with open(f"summerize.txt", "w", encoding="utf-8") as f:
                f.write(output)
            print("处理后的内容已保存到文件中")
            return output
        except json.JSONDecodeError as e:
            print("JSON 解码失败:", e)
    else:
        print("请求失败，状态码:", response.status_code)
        print("响应内容:", response.text)

def outline_checker(model="70b_3", material=""):
    # 根据参数选择配置
    config = MODEL_CONFIG[model]
    url = config["url"]
    model_name = config["model_name"]

    # 请求数据
    prompt1=str(f'{material}\n')
    prompt2=str(f'请你仔细阅读上面的小说大纲和分章节剧情，检查一下是否有明显的逻辑错误、人物错误、剧情前后矛盾的问题，优化这份材料，出现英文的地方都更改为中文，不要改变整体结构\n')
    prompt=prompt1+prompt2
    data = {
        "model": model_name,  # 使用的模型名称
        "prompt": prompt,
        "stream": False,  # 不使用流式输出，直接返回完整结果
        "max_tokens": 10000  # 生成的最大 token 数量
    }
    # 发送 POST 请求
    response = requests.post(url, json=data)

    if response.status_code == 200:
        try:
            # 解析响应的 JSON 数据
            result = response.json()  # 直接解析整个响应的 JSON 数据
            output = result.get("response", "没有返回内容")
            with open(f"outline_modify_init.txt", "w", encoding="utf-8") as f:
                f.write(output)
            # 删除 </think> 之前的部分
            output = re.sub(r'^.*?</think>', '', output, flags=re.DOTALL)
            output = re.sub(r'</think>.*$', '', output, flags=re.DOTALL)
            output = output.replace("\n\n","\n")
            output = output.strip()
            with open(f"outline_modify.txt", "w", encoding="utf-8") as f:
                f.write(output)
            print("处理后的内容已保存到文件中")
            return output
        except json.JSONDecodeError as e:
            print("JSON 解码失败:", e)
    else:
        print("请求失败，状态码:", response.status_code)
        print("响应内容:", response.text)

def user_define(model="70b_3", file="", prompt=""):
    # 根据参数选择配置
    config = MODEL_CONFIG[model]
    url = config["url"]
    model_name = config["model_name"]
    with open(file, 'r', encoding='utf-8') as file:
            material = file.read()
    # 请求数据
    prompt1=str(f'{material}\n')
    prompt2=str(f'{prompt}\n')
    prompt=prompt1+prompt2
    data = {
        "model": model_name,  # 使用的模型名称
        "prompt": prompt,
        "stream": False,  # 不使用流式输出，直接返回完整结果
        "max_tokens": 10000  # 生成的最大 token 数量
    }
    # 发送 POST 请求
    response = requests.post(url, json=data)

    if response.status_code == 200:
        try:
            # 解析响应的 JSON 数据
            result = response.json()  # 直接解析整个响应的 JSON 数据
            output = result.get("response", "没有返回内容")
            print(output)
        except json.JSONDecodeError as e:
            print("JSON 解码失败:", e)
    else:
        print("请求失败，状态码:", response.status_code)
        print("响应内容:", response.text)

def character_document_update(model="70b_3", file="", character_document=""):
    # 根据参数选择配置
    config = MODEL_CONFIG[model]
    url = config["url"]
    model_name = config["model_name"]
    with open(file, 'r', encoding='utf-8') as file:
            material = file.read()
    with open(character_document, 'r', encoding='utf-8') as file:
            character_document_material = file.read()    
    # 请求数据
    prompt=str(f'{material}\n'
               f'要求：\n'
               f'请你根据上面材料，补充最新内容到下面的人物档案\n'
               f'不要删除已经存在的档案\n'
               f'重新输出更改好的全部人物档案\n'
               f'{character_document_material}\n')
    data = {
        "model": model_name,  # 使用的模型名称
        "prompt": prompt,
        "stream": False,  # 不使用流式输出，直接返回完整结果
        "max_tokens": 10000  # 生成的最大 token 数量
    }
    # 发送 POST 请求
    response = requests.post(url, json=data)

    if response.status_code == 200:
        try:
            # 解析响应的 JSON 数据
            result = response.json()  # 直接解析整个响应的 JSON 数据
            output = result.get("response", "没有返回内容")
            with open(f"summerize_init.txt", "w", encoding="utf-8") as f:
                f.write(output)
            # 删除 </think> 之前的部分
            output = re.sub(r'^.*?</think>', '', output, flags=re.DOTALL)
            output = re.sub(r'</think>.*$', '', output, flags=re.DOTALL)
            output = output.replace("\n\n","\n")
            output = output.strip()
            with open(f"summerize.txt", "w", encoding="utf-8") as f:
                f.write(output)
            print("处理后的内容已保存到文件中")
            return output
        except json.JSONDecodeError as e:
            print("JSON 解码失败:", e)
    else:
        print("请求失败，状态码:", response.status_code)
        print("响应内容:", response.text)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="传参")
    parser.add_argument("-f","--file", type=str, default="")
    parser.add_argument("-cd","--character_document", type=str, default="")
    parser.add_argument("-r","--requirment", type=str, default="")
    args = parser.parse_args()
    character_document_update(file=args.file, character_document=args.character_document)
    # user_define(file=args.file, prompt=args.requirment)