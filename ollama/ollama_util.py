import requests
import json
import re
import argparse
from openai import OpenAI

# 定义两组 URL 和模型名称
MODEL_CONFIG = {
    "70b": {
        "url": "http://192.168.31.80:11435/v1",
        "model_name": "70b_self",
        "api_key": "ollama"
    },
    "70b_3w": {
        "url": "http://192.168.31.80:11435/v1",
        "model_name": "70b_3w",
        "api_key": "ollama"
    },
    "qwq": {
        "url": "http://192.168.31.80:11435/v1",
        "model_name": "qwq_5w",
        "api_key": "ollama"
    },
    "70b_3w_2": {
        "url": "http://192.168.31.80:11436/v1",
        "model_name": "70b_3w",
        "api_key": "ollama"
    },
    "qwq_2": {
        "url": "http://192.168.31.80:11436/v1",
        "model_name": "qwq_5w",
        "api_key": "ollama"
    },
    "32b_self": {
        "url": "http://192.168.31.80:11435/v1",
        "model_name": "32b_self",
        "api_key": "ollama"
    },
    "70b_2": {
        "url": "http://192.168.31.80:11436/v1",
        "model_name": "70b_self"
    },
    "32b_self_2": {
        "url": "http://192.168.31.80:11436/v1",
        "model_name": "32b_self",
        "api_key": "ollama"
    },
    "70b_3": {
        "url": "http://192.168.31.80:11437/v1",
        "model_name": "70b_self",
        "api_key": "ollama"
    },
    "32b_self_3": {
        "url": "http://192.168.31.80:11437/v1",
        "model_name": "32b_self",
        "api_key": "ollama"
    },
    "deepseek": {
        "url": "https://api.deepseek.com",
        "model_name": "deepseek-reasoner",
        "api_key": "sk-f54652922efa4939954a19ab03e748e1"
    },
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
        "max_tokens": 50000  # 生成的最大 token 数量
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
        "max_tokens": 50000  # 生成的最大 token 数量
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
        "max_tokens": 50000  # 生成的最大 token 数量
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

def chapter_modifier(model="70b_3", material="", title="default"):
    # 根据参数选择配置
    config = MODEL_CONFIG[model]
    url = config["url"]
    model_name = config["model_name"]
    api_key = config["api_key"]
    client = OpenAI(api_key=api_key, base_url=url)
    # 替换非法字符
    title = title.replace('|', '-')  # 将 | 替换为 -
    title = title.replace(':', '-')  # 将 : 替换为 -
    title = title.replace('?', '-')  # 将 ? 替换为 -
    title = title.replace('*', '-')  # 将 * 替换为 -
    title = title.replace('"', '-')  # 将 " 替换为 -
    title = title.replace('<', '-')  # 将 < 替换为 -
    title = title.replace('>', '-')  # 将 > 替换为 -

    # 请求数据
    prompt=str(f'{material}\n'
               f'请逐句检查是否符合人类作家书写风格，并逐句输出，符合则直接输出，不符合则改进后输出，全部检查完毕后请按照原有格式输出整个文章，文章要符合发表要求，不要有任何注释内容\n')
    print(prompt)
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "你是一个编辑"},
                {"role": "user", "content": prompt},
            ],
            stream=False
        )
        output = response.choices[0].message.content
        with open(f"{title}_init", "w", encoding="utf-8") as f:
            f.write(output)
        # 使用正则表达式替换，删除从字符串开头到第一个 </think> 标签（包含该标签）之间的所有内容
        output = re.sub(r'^.*?</think>', '', output, flags=re.DOTALL)
        # 使用正则表达式替换，删除从 </think> 标签（包含该标签）到字符串末尾的所有内容
        output = re.sub(r'</think>.*$', '', output, flags=re.DOTALL)
        # 使用正则表达式替换，删除每行开头以 ** 包裹文本（中间可有其他内容）的整行内容
        output = re.sub(r'^.*\*\*.*\*\*.*\n?', '', output, flags=re.MULTILINE)
        # 使用正则表达式替换，将连续的换行符替换为单个换行符，并去除字符串首尾的空白字符
        output = re.sub(r'\n+', '\n', output).strip()
        # 使用正则表达式替换，删除只包含一个空格的行
        output = re.sub(r'^ $', '', output, flags=re.MULTILINE)
        # 找到第三次出现 ### 的行
        lines = output.split('\n')  # 将文本按行分割
        # 初始化篇章正文开始和结束的行索引
        start_index = -1
        end_index = -1
        # 遍历每一行，查找包含“篇章正文开始”和“篇章正文结束”的行
        for i, line in enumerate(lines):
            if start_index == -1 and "篇章正文开始" in line:
                start_index = i
            if "篇章正文结束" in line:
                end_index = i
                break
        # 如果找到了篇章正文开始和结束的行
        if start_index != -1 and end_index != -1:
            # 保留从篇章正文开始行到篇章正文结束行的所有行
            output = '\n'.join(lines[start_index:end_index + 1])
        elif start_index != -1:
            # 如果只找到了篇章正文开始行，保留从开始行到最后的所有行
            output = '\n'.join(lines[start_index:])
        else:
            # 如果都没找到，保持原输出
            pass
        output = output.replace("\n\n", "\n")
        with open(f"{title}", "w", encoding="utf-8") as f:
            f.write(output)
        print("处理后的内容已保存到文件中")
        return output
    except Exception as e:
        print("生成失败:", e)
        return ""

def volume_expender(model="70b_3", outline_volume="", outline="", character_document="", wordage=2500, title="第1卷第1章", style=""):
    # 根据参数选择配置
    config = MODEL_CONFIG[model]
    url = config["url"]
    model_name = config["model_name"]
    api_key = config["api_key"]
    client = OpenAI(api_key=api_key, base_url=url)
    # 替换非法字符
    title = title.replace('|', '-')  # 将 | 替换为 -
    title = title.replace(':', '-')  # 将 : 替换为 -
    title = title.replace('?', '-')  # 将 ? 替换为 -
    title = title.replace('*', '-')  # 将 * 替换为 -
    title = title.replace('"', '-')  # 将 " 替换为 -
    title = title.replace('<', '-')  # 将 < 替换为 -
    title = title.replace('>', '-')  # 将 > 替换为 -

    # 请求数据
    prompt=str(f'1、小说的大纲如下\n'
               f'{outline}\n'
               f'2、小说的人物档案如下\n'
               f'{character_document}\n'
               f'3、小说{title}章节细纲如下\n'
               f'{outline_volume}\n'
               f'4、请扩写每一章章节概述的内容，使每章章节概述的字数翻倍，将所有细节和伏笔都完整展示出来，完整输出所有内容\n'
               f'5、输出格式保持不变\n')
    # 打印 prompt 字符串的长度
    print(f"prompt 字符串的长度为: {len(prompt)}")
    # 按行分割字符串
    lines = prompt.splitlines()
    # 取最后 300 行
    last_100_lines = lines[-300:]
    # 重新组合成字符串
    result = '\n'.join(last_100_lines)
    # 打印结果
    print(result)
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": f'模仿人类风格写作，按要求扩写文章，遇到前后剧情不符合逻辑处需进行修正，仅用简体中文完成'},
                {"role": "user", "content": prompt},
            ],
            stream=False
        )
        output = response.choices[0].message.content
        with open(f"{title}_init", "w", encoding="utf-8") as f:
            f.write(output)
        # 使用正则表达式替换，删除从字符串开头到第一个 </think> 标签（包含该标签）之间的所有内容
        output = re.sub(r'^.*?</think>', '', output, flags=re.DOTALL)
        # 使用正则表达式替换，删除从 </think> 标签（包含该标签）到字符串末尾的所有内容
        output = re.sub(r'</think>.*$', '', output, flags=re.DOTALL)
        # 使用正则表达式替换，删除每行开头以 ** 包裹文本（中间可有其他内容）的整行内容
        output = re.sub(r'^.*\*\*.*\*\*.*\n?', '', output, flags=re.MULTILINE)
        # 使用正则表达式替换，将连续的换行符替换为单个换行符，并去除字符串首尾的空白字符
        output = re.sub(r'\n+', '\n', output).strip()
        # 使用正则表达式替换，删除只包含一个空格的行
        output = re.sub(r'^ $', '', output, flags=re.MULTILINE)
        with open(f"{title}_modify", "w", encoding="utf-8") as f:
            f.write(output)
        print("处理后的内容已保存到文件中")
        return output
    except Exception as e:
        print("生成失败:", e)
        return ""

def volume_expender_Short(model="70b_3", outline_volume="", outline="", character_document="", wordage=2500, title="第1卷第1章", style=""):
    # 根据参数选择配置
    config = MODEL_CONFIG[model]
    url = config["url"]
    model_name = config["model_name"]
    api_key = config["api_key"]
    client = OpenAI(api_key=api_key, base_url=url)
    # 替换非法字符
    title = title.replace('|', '-')  # 将 | 替换为 -
    title = title.replace(':', '-')  # 将 : 替换为 -
    title = title.replace('?', '-')  # 将 ? 替换为 -
    title = title.replace('*', '-')  # 将 * 替换为 -
    title = title.replace('"', '-')  # 将 " 替换为 -
    title = title.replace('<', '-')  # 将 < 替换为 -
    title = title.replace('>', '-')  # 将 > 替换为 -

    # 请求数据
    prompt=str(f'1、小说的大纲如下\n'
               f'{outline}\n'
               f'2、小说的人物档案如下\n'
               f'{character_document}\n'
               f'3、小说{title}章节细纲如下\n'
               f'{outline_volume}\n'
               f'4、请根据章节细纲扩写每个章节的故事，使每章章节的字数在1000字左右，请完整输出整本小说的内容\n'
               f'5、输出格式如下\n'
               f'###小说开始###\n'
               f'小说正文\n'
               f'###小说结束###\n')
    # 打印 prompt 字符串的长度
    print(f"prompt 字符串的长度为: {len(prompt)}")
    # 按行分割字符串
    lines = prompt.splitlines()
    # 取最后 300 行
    last_100_lines = lines[-300:]
    # 重新组合成字符串
    result = '\n'.join(last_100_lines)
    # 打印结果
    print(result)
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": f'模仿人类风格写作，按要求扩写文章，遇到前后剧情不符合逻辑处需进行修正，仅用简体中文完成'},
                {"role": "user", "content": prompt},
            ],
            stream=False
        )
        output = response.choices[0].message.content
        with open(f"{title}_init", "w", encoding="utf-8") as f:
            f.write(output)
        # 使用正则表达式替换，删除从字符串开头到第一个 </think> 标签（包含该标签）之间的所有内容
        output = re.sub(r'^.*?</think>', '', output, flags=re.DOTALL)
        # 使用正则表达式替换，删除从 </think> 标签（包含该标签）到字符串末尾的所有内容
        output = re.sub(r'</think>.*$', '', output, flags=re.DOTALL)
        # 使用正则表达式替换，删除每行开头以 ** 包裹文本（中间可有其他内容）的整行内容
        output = re.sub(r'^.*\*\*.*\*\*.*\n?', '', output, flags=re.MULTILINE)
        # 使用正则表达式替换，将连续的换行符替换为单个换行符，并去除字符串首尾的空白字符
        output = re.sub(r'\n+', '\n', output).strip()
        # 使用正则表达式替换，删除只包含一个空格的行
        output = re.sub(r'^ $', '', output, flags=re.MULTILINE)
        with open(f"{title}_modify", "w", encoding="utf-8") as f:
            f.write(output)
        print("处理后的内容已保存到文件中")
        return output
    except Exception as e:
        print("生成失败:", e)
        return ""

def chapter_writer(model="70b_3", outline_volume="", last_chapter="", outline="", character_document="", wordage=2500, title="第1卷第1章", style=""):
    # 根据参数选择配置
    config = MODEL_CONFIG[model]
    url = config["url"]
    model_name = config["model_name"]
    api_key = config["api_key"]
    client = OpenAI(api_key=api_key, base_url=url)
    # 替换非法字符
    title = title.replace('|', '-')  # 将 | 替换为 -
    title = title.replace(':', '-')  # 将 : 替换为 -
    title = title.replace('?', '-')  # 将 ? 替换为 -
    title = title.replace('*', '-')  # 将 * 替换为 -
    title = title.replace('"', '-')  # 将 " 替换为 -
    title = title.replace('<', '-')  # 将 < 替换为 -
    title = title.replace('>', '-')  # 将 > 替换为 -

    # 请求数据
    if title == "第1卷第1章":
        prompt=str(f'1、小说的大纲如下\n'
                f'{outline}\n'
                f'2、小说的人物档案如下\n'
                f'{character_document}\n'
                f'3、小说本章节和下一章节的细纲如下\n'
                f'{outline_volume}\n'
                f'4、请根据前面提供的本章节和下一章节的细纲，结合人物档案，完成{title}，关注下一章概述，本章节的结尾要为下一章的延续做好铺垫，字数{wordage}字左右，不要使用任何英文字母和繁体字符\n'
                f'5、不需要标题，各篇章故事要紧密连贯，不复制之前篇章的内容\n'
                f'6、输出格式如下\n'
                f'###篇章正文开始###\n'
                f'篇章正文\n'
                f'###篇章正文结束###\n')
    else:
        prompt=str(f'1、小说的大纲如下\n'
                f'{outline}\n'
                f'2、小说的人物档案如下\n'
                f'{character_document}\n'
                f'3、小说上一章最后部分如下\n'
                f'{last_chapter}\n'
                f'4、小说本章节和下一章节的细纲如下\n'
                f'{outline_volume}\n'
                f'5、请根据前面提供的本章节和下一章节的细纲，结合人物档案，紧接上一篇章结尾完成{title}，关注下一章概述，本章节的结尾要为下一章的延续做好铺垫，字数{wordage}字左右，不要使用任何英文字母和繁体字符\n'
                f'6、不需要标题，各篇章故事要紧密连贯，不复制之前篇章的内容\n'
                f'7、输出格式如下\n'
                f'###篇章正文开始###\n'
                f'篇章正文\n'
                f'###篇章正文结束###\n')
    # 打印 prompt 字符串的长度
    print(f"prompt 字符串的长度为: {len(prompt)}")
    # 按行分割字符串
    lines = prompt.splitlines()
    # 取最后 300 行
    last_100_lines = lines[-300:]
    # 重新组合成字符串
    result = '\n'.join(last_100_lines)
    # 打印结果
    print(result)
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": f'模仿人类风格写作，内容详实，语言简洁，尽量使用短句，注重细节和心里描写，请始终使用标准的简体中文进行创作，人物对话要口语化。'},
                {"role": "user", "content": prompt},
            ],
            stream=False
        )
        output = response.choices[0].message.content
        with open(f"{title}_init", "w", encoding="utf-8") as f:
            f.write(output)
        # 使用正则表达式替换，删除从字符串开头到第一个 </think> 标签（包含该标签）之间的所有内容
        output = re.sub(r'^.*?</think>', '', output, flags=re.DOTALL)
        # 使用正则表达式替换，删除从 </think> 标签（包含该标签）到字符串末尾的所有内容
        output = re.sub(r'</think>.*$', '', output, flags=re.DOTALL)
        # 使用正则表达式替换，删除每行开头以 ** 包裹文本（中间可有其他内容）的整行内容
        output = re.sub(r'^.*\*\*.*\*\*.*\n?', '', output, flags=re.MULTILINE)
        # 使用正则表达式替换，将连续的换行符替换为单个换行符，并去除字符串首尾的空白字符
        output = re.sub(r'\n+', '\n', output).strip()
        # 使用正则表达式替换，删除只包含一个空格的行
        output = re.sub(r'^ $', '', output, flags=re.MULTILINE)
        # 找到第三次出现 ### 的行
        lines = output.split('\n')  # 将文本按行分割
        # 遍历每一行，查找包含“篇章正文结束”的行
        for i, line in enumerate(lines):
            if "篇章正文结束" in line:
                # 保留当前行及其之前的所有行，删除之后的所有行
                output = '\n'.join(lines[:i + 1])
                break
        output = output.replace("\n\n", "\n")
        with open(f"{title}", "w", encoding="utf-8") as f:
            f.write(output)
        print("处理后的内容已保存到文件中")
        return output
    except Exception as e:
        print("生成失败:", e)
        return ""

def chapter_writer_new(model="70b_3", plot="", last_chapter="", outline="", character_document="", wordage=2500, title="第1章", man="", woman="", style=""):
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
    prompt=str(f'1、小说的大纲如下\n'
               f'{outline}\n'
               f'2、小说的人物档案如下\n'
               f'{character_document}\n'
               f'3、小说之前的剧情概述如下\n'
               f'{plot}\n'
               f'4、小说上一章最后部分如下\n'
               f'{last_chapter}\n'
               f'5、请根据前面提供的小说大纲，人物档案和已经发生的情节，紧接上一篇章结尾续写新的篇章，字数{wordage}字左右，不要使用任何英文字母\n'
               f'6、故事的剧情风格是{style}，不需要标题，各篇章故事要紧密连贯，不复制之前篇章的内容，请模仿张小娴的文笔进行创作，可以使用一些通俗的语言，不要使用刻意的连接，转折，总结词语，去除ai味儿，人物说的话一定要说人话\n'
               f'7、输出格式如下\n'
               f'###篇章正文开始###\n'
               f'篇章正文\n'
               f'###篇章正文结束###\n')
    # 打印 prompt 字符串的长度
    print(f"prompt 字符串的长度为: {len(prompt)}")
    # 按行分割字符串
    lines = prompt.splitlines()
    # 取最后 300 行
    last_100_lines = lines[-300:]
    # 重新组合成字符串
    result = '\n'.join(last_100_lines)
    # 打印结果
    print(result)
    data = {
        "model": model_name,  # 使用的模型名称
        "prompt": prompt,
        "stream": False,  # 不使用流式输出，直接返回完整结果
        "max_tokens": 50000  # 生成的最大 token 数量
    }
    # 发送 POST 请求
    response = requests.post(url, json=data)

    if response.status_code == 200:
        try:
            # 解析响应的 JSON 数据
            result = response.json()  # 直接解析整个响应的 JSON 数据
            output = result.get("response", "没有返回内容")
            with open(f"{title}_init", "w", encoding="utf-8") as f:
                f.write(output)
            # 使用正则表达式替换，删除从字符串开头到第一个 </think> 标签（包含该标签）之间的所有内容
            output = re.sub(r'^.*?</think>', '', output, flags=re.DOTALL)
            # 使用正则表达式替换，删除从 </think> 标签（包含该标签）到字符串末尾的所有内容
            output = re.sub(r'</think>.*$', '', output, flags=re.DOTALL)
            # 使用正则表达式替换，删除每行开头以 ** 包裹文本（中间可有其他内容）的整行内容
            output = re.sub(r'^.*\*\*.*\*\*.*\n?', '', output, flags=re.MULTILINE)
            # 使用正则表达式替换，将连续的换行符替换为单个换行符，并去除字符串首尾的空白字符
            output = re.sub(r'\n+', '\n', output).strip()
            # 使用正则表达式替换，删除包含 --- 的行
            output = re.sub(r'^.*---.*$', '', output, flags=re.MULTILINE)
            # 找到第三次出现 ### 的行
            lines = output.split('\n')  # 将文本按行分割
            count = 0
            for i, line in enumerate(lines):
                if '###' in line:  # 如果当前行包含 ###
                    count += 1
                    if count == 3:  # 如果是第三次出现
                        # 保留当前行，删除之后的所有行
                        output = '\n'.join(lines[:i+1])
                        break
            output = output.replace("\n\n", "\n")
            with open(f"{title}", "w", encoding="utf-8") as f:
                f.write(output)
            print("处理后的内容已保存到文件中")
        except json.JSONDecodeError as e:
            print("JSON 解码失败:", e)
    else:
        print("请求失败，状态码:", response.status_code)
        print("响应内容:", response.text)

def Style_test(model="70b_3", material="", title="default"):
    # 根据参数选择配置
    config = MODEL_CONFIG[model]
    url = config["url"]
    model_name = config["model_name"]
    api_key = config["api_key"]
    client = OpenAI(api_key=api_key, base_url=url)
    # 替换非法字符
    title = title.replace('|', '-')  # 将 | 替换为 -
    title = title.replace(':', '-')  # 将 : 替换为 -
    title = title.replace('?', '-')  # 将 ? 替换为 -
    title = title.replace('*', '-')  # 将 * 替换为 -
    title = title.replace('"', '-')  # 将 " 替换为 -
    title = title.replace('<', '-')  # 将 < 替换为 -
    title = title.replace('>', '-')  # 将 > 替换为 -

    # 请求数据
    prompt=str(f'写一个2000字左右的爱情小品\n')
    print(prompt)
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": f'模仿人类风格写作，内容详实，语言简洁，注重细节和心里描写，请始终使用标准的简体中文进行创作，人物对话要口语化。'},
                {"role": "user", "content": prompt},
            ],
            temperature=0.8,
            top_p=0.95,
            frequency_penalty=0.9,
            presence_penalty=0.9,
            stream=False
        )
        output = response.choices[0].message.content
        with open(f"Style_init.txt", "w", encoding="utf-8") as f:
            f.write(output)
        # 删除 </think> 之前的部分
        output = re.sub(r'^.*?</think>', '', output, flags=re.DOTALL)
        output = re.sub(r'</think>.*$', '', output, flags=re.DOTALL)
        output = output.replace("\n\n","\n")
        with open(f"Style.txt", "w", encoding="utf-8") as f:
            f.write(output)
        print("处理后的内容已保存到文件中")
        return output
    except Exception as e:
        print("创建失败:", e)
        return ""

def Outline_Generator(model="70b_3", material="", title="default"):
    # 根据参数选择配置
    config = MODEL_CONFIG[model]
    url = config["url"]
    model_name = config["model_name"]
    api_key = config["api_key"]
    client = OpenAI(api_key=api_key, base_url=url)
    # 替换非法字符
    title = title.replace('|', '-')  # 将 | 替换为 -
    title = title.replace(':', '-')  # 将 : 替换为 -
    title = title.replace('?', '-')  # 将 ? 替换为 -
    title = title.replace('*', '-')  # 将 * 替换为 -
    title = title.replace('"', '-')  # 将 " 替换为 -
    title = title.replace('<', '-')  # 将 < 替换为 -
    title = title.replace('>', '-')  # 将 > 替换为 -

    # 请求数据
    prompt=str(f'{material}\n'
                f'请你根据上面这段文字的要求，构思一个相应风格长篇小说的大纲\n'
                f'1、首先介绍整个小说的故事背景，核心设定和整体剧情，这部分尽量详细一些\n'
                f'2、构建一个完整的人物档案，列出至少20名主要人物，人名需要有辨识度，格式如下\n'
                f'  $$1. 人物名称$$\n'
                f'  - **性别**：\n'
                f'  - **年龄**：\n'
                f'  - **性格**：\n'
                f'  - **背景**：\n'
                f'  - **关系**：\n'
                f'3、给这个小说起一个吸引人的标题\n'
                f'4、输出文章的格式如下\n'
                f'###文章标题###\n'
                f'  &&你起的标题&&\n'
                f'###故事背景###\n'
                f'###核心设定###\n'
                f'###剧情开端###\n'
                f'###人物档案###\n'
                f'###结束语###\n')
    print(prompt)
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "你是一个中文编辑，请完全使用简体中文完成创作，禁止使用繁体中文和英文，不要出现重复内容"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            top_p=0.9,
            stream=False
        )
        output = response.choices[0].message.content
        with open(f"Outline_modify1.txt", "w", encoding="utf-8") as f:
            f.write(output)
        # 删除 </think> 之前的部分
        output = re.sub(r'^.*?</think>', '', output, flags=re.DOTALL)
        output = re.sub(r'</think>.*$', '', output, flags=re.DOTALL)
        # 使用正则表达式替换，将连续的换行符替换为单个换行符，并去除字符串首尾的空白字符
        output = re.sub(r'\n+', '\n', output).strip()
        # 使用正则表达式替换，删除只包含一个空格的行
        output = re.sub(r'^ $', '', output, flags=re.MULTILINE)
        with open(f"Outline_modify2.txt", "w", encoding="utf-8") as f:
            f.write(output)
        print("处理后的内容已保存到文件中")
        return output
    except Exception as e:
        print("创建失败:", e)
        return ""

def Outline_Generator_Short(model="70b_3", material="", title="default"):
    # 根据参数选择配置
    config = MODEL_CONFIG[model]
    url = config["url"]
    model_name = config["model_name"]
    api_key = config["api_key"]
    client = OpenAI(api_key=api_key, base_url=url)
    # 替换非法字符
    title = title.replace('|', '-')  # 将 | 替换为 -
    title = title.replace(':', '-')  # 将 : 替换为 -
    title = title.replace('?', '-')  # 将 ? 替换为 -
    title = title.replace('*', '-')  # 将 * 替换为 -
    title = title.replace('"', '-')  # 将 " 替换为 -
    title = title.replace('<', '-')  # 将 < 替换为 -
    title = title.replace('>', '-')  # 将 > 替换为 -

    # 请求数据
    prompt=str(f'{material}\n'
                f'请你根据上面这段文字的要求，构思一个相应风格的短篇小说的大纲\n'
                f'1、首先介绍整个小说的故事背景，核心设定和整体剧情，这部分尽量详细一些\n'
                f'2、构建一个完整的人物档案，列出至少10名主要人物，人名需要有辨识度，格式如下\n'
                f'  $$1. 人物名称$$\n'
                f'  - **性别**：\n'
                f'  - **年龄**：\n'
                f'  - **性格**：\n'
                f'  - **背景**：\n'
                f'  - **关系**：\n'
                f'3、给这个小说起一个吸引人的标题\n'
                f'4、输出文章的格式如下\n'
                f'###文章标题###\n'
                f'  &&你起的标题&&\n'
                f'###故事背景###\n'
                f'###核心设定###\n'
                f'###剧情开端###\n'
                f'###人物档案###\n'
                f'###结束语###\n')
    print(prompt)
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "你是一个中文编辑，请完全使用简体中文完成创作，禁止使用繁体中文和英文，不要出现重复内容"},
                {"role": "user", "content": prompt},
            ],
            stream=False
        )
        output = response.choices[0].message.content
        with open(f"Outline_modify1.txt", "w", encoding="utf-8") as f:
            f.write(output)
        # 删除 </think> 之前的部分
        output = re.sub(r'^.*?</think>', '', output, flags=re.DOTALL)
        output = re.sub(r'</think>.*$', '', output, flags=re.DOTALL)
        # 使用正则表达式替换，将连续的换行符替换为单个换行符，并去除字符串首尾的空白字符
        output = re.sub(r'\n+', '\n', output).strip()
        # 使用正则表达式替换，删除只包含一个空格的行
        output = re.sub(r'^ $', '', output, flags=re.MULTILINE)
        with open(f"Outline_modify2.txt", "w", encoding="utf-8") as f:
            f.write(output)
        print("处理后的内容已保存到文件中")
        return output
    except Exception as e:
        print("创建失败:", e)
        return ""

def Outline_Volume_Generator(model="70b_3", material="", title="default"):
    # 根据参数选择配置
    config = MODEL_CONFIG[model]
    url = config["url"]
    model_name = config["model_name"]
    api_key = config["api_key"]
    client = OpenAI(api_key=api_key, base_url=url)
    # 替换非法字符
    title = title.replace('|', '-')  # 将 | 替换为 -
    title = title.replace(':', '-')  # 将 : 替换为 -
    title = title.replace('?', '-')  # 将 ? 替换为 -
    title = title.replace('*', '-')  # 将 * 替换为 -
    title = title.replace('"', '-')  # 将 " 替换为 -
    title = title.replace('<', '-')  # 将 < 替换为 -
    title = title.replace('>', '-')  # 将 > 替换为 -

    # 请求数据
    prompt=str(f'{material}\n'
                f'请你根据上面的小说基本设定，构思每一卷的大纲\n'
                f'1、我希望将这个小说分为五卷（每卷大概40000字）\n'
                f'2、每卷概述要详细，每卷至少需要300字\n'
                f'3、输出的格式如下\n'
                f'###第X卷###\n'
                f'###本卷剧情发展概述###\n'
                f'###本卷预设伏笔###\n')
    print(prompt)
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "你是一个中文编辑，请完全使用简体中文完成创作，禁止使用繁体中文和英文，不要出现重复内容"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            top_p=0.9,
            stream=False
        )
        output = response.choices[0].message.content
        with open(f"Outline_Volume_modify1.txt", "w", encoding="utf-8") as f:
            f.write(output)
        # 删除 </think> 之前的部分
        output = re.sub(r'^.*?</think>', '', output, flags=re.DOTALL)
        output = re.sub(r'</think>.*$', '', output, flags=re.DOTALL)
        output = output.replace("\n\n","\n")
        with open(f"Outline_Volume_modify2.txt", "w", encoding="utf-8") as f:
            f.write(output)
        print("处理后的内容已保存到文件中")
        return output
    except Exception as e:
        print("创建失败:", e)
        return ""

def Outline_Chapter_Generator(model="70b_3", material="", Last_Outline_Chapter="", title="default"):
    # 根据参数选择配置
    config = MODEL_CONFIG[model]
    url = config["url"]
    model_name = config["model_name"]
    api_key = config["api_key"]
    client = OpenAI(api_key=api_key, base_url=url)
    # 替换非法字符
    title = title.replace('|', '-')  # 将 | 替换为 -
    title = title.replace(':', '-')  # 将 : 替换为 -
    title = title.replace('?', '-')  # 将 ? 替换为 -
    title = title.replace('*', '-')  # 将 * 替换为 -
    title = title.replace('"', '-')  # 将 " 替换为 -
    title = title.replace('<', '-')  # 将 < 替换为 -
    title = title.replace('>', '-')  # 将 > 替换为 -

    # 请求数据
    if title == "第一卷":
        prompt=str(f'故事大纲和人物档案如下：\n'
                   f'{material}\n'
                   f'请你根据上面的小说基本设定，完成{title}章节细纲，并为下一卷故事的展开做好铺垫\n'
                   f'重点注意，不要使用任何英语字母和繁体中文，仅使用标准简体中文'
                   f'1、这一卷需要分为20章（每章大概2000字左右）\n'
                   f'2、章节细纲尽量详细，每章至少需要300字，完整输出全部内容\n'
                   f'3、输出的格式如下\n'
                   f'###第X卷章节细纲开始###\n'
                   f'###第X章剧情发展概述###\n'
                   f'###第X卷章节细纲结束###\n')
    else:
        prompt=str(f'故事大纲和人物档案如下：\n'
                   f'{material}\n'
                   f'上一卷细纲如下：\n'
                   f'{Last_Outline_Chapter}\n'
                   f'请你根据上面的小说基本设定，完成{title}章节细纲，，并为下一卷故事的展开做好铺垫\n'
                   f'重点注意，不要使用任何英语字母和繁体中文，仅使用标准简体中文'
                   f'1、这一卷需要分为20章（每章大概2000字左右）\n'
                   f'2、章节细纲尽量详细，每章至少需要300字，完整输出全部内容\n'
                   f'3、输出的格式如下\n'
                   f'###第X卷章节细纲开始###\n'
                   f'###第X章剧情发展概述###\n'
                   f'###第X卷章节细纲结束###\n')
    print(prompt)
    # 打印 prompt 字符串的长度
    print(f"prompt 字符串的长度为: {len(prompt)}")
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "你是一个中文编辑，请完全使用简体中文完成创作，禁止使用繁体中文和英文，不要出现重复内容"},
                {"role": "user", "content": prompt},
            ],
            stream=False
        )
        output = response.choices[0].message.content
        with open(f"{title}_modify1.txt", "w", encoding="utf-8") as f:
            f.write(output)
        # 删除 </think> 之前的部分
        output = re.sub(r'^.*?</think>', '', output, flags=re.DOTALL)
        output = re.sub(r'</think>.*$', '', output, flags=re.DOTALL)
        output = re.sub(r'^\n$', '', output, flags=re.MULTILINE)
        output = output.replace("\n\n","\n")
        output = output.strip()
        with open(f"{title}_modify2.txt", "w", encoding="utf-8") as f:
            f.write(output)
        print("处理后的内容已保存到文件中")
        return output
    except Exception as e:
        print("创建失败:", e)
        return ""

def Outline_Chapter_Generator_Short(model="70b_3", material="", Last_Outline_Chapter="", title="Outline_Chapter"):
    # 根据参数选择配置
    config = MODEL_CONFIG[model]
    url = config["url"]
    model_name = config["model_name"]
    api_key = config["api_key"]
    client = OpenAI(api_key=api_key, base_url=url)
    # 替换非法字符
    title = title.replace('|', '-')  # 将 | 替换为 -
    title = title.replace(':', '-')  # 将 : 替换为 -
    title = title.replace('?', '-')  # 将 ? 替换为 -
    title = title.replace('*', '-')  # 将 * 替换为 -
    title = title.replace('"', '-')  # 将 " 替换为 -
    title = title.replace('<', '-')  # 将 < 替换为 -
    title = title.replace('>', '-')  # 将 > 替换为 -

    # 请求数据
    prompt=str(f'故事大纲和人物档案如下：\n'
                f'{material}\n'
                f'请你根据上面的小说基本设定，完成小说的章节细纲\n'
                f'重点注意，不要使用任何英语字母和繁体中文，仅使用标准简体中文'
                f'1、这个小说总共15000字左右，分为15章\n'
                f'2、章节细纲尽量详细，每章至少需要300字，完整输出全部内容\n'
                f'3、输出的格式如下\n'
                f'###章节细纲开始###\n'
                f'###第X章剧情发展概述###\n'
                f'###章节细纲结束###\n')
    print(prompt)
    # 打印 prompt 字符串的长度
    print(f"prompt 字符串的长度为: {len(prompt)}")
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "你是一个中文编辑，请完全使用简体中文完成创作，禁止使用繁体中文和英文，不要出现重复内容"},
                {"role": "user", "content": prompt},
            ],
            stream=False
        )
        output = response.choices[0].message.content
        with open(f"{title}_modify1.txt", "w", encoding="utf-8") as f:
            f.write(output)
        # 删除 </think> 之前的部分
        output = re.sub(r'^.*?</think>', '', output, flags=re.DOTALL)
        output = re.sub(r'</think>.*$', '', output, flags=re.DOTALL)
        output = re.sub(r'^\n$', '', output, flags=re.MULTILINE)
        output = output.replace("\n\n","\n")
        output = output.strip()
        with open(f"{title}_modify2.txt", "w", encoding="utf-8") as f:
            f.write(output)
        print("处理后的内容已保存到文件中")
        return output
    except Exception as e:
        print("创建失败:", e)
        return ""

def summerizer(model="70b_3", material="", wordage=200):
    # 根据参数选择配置
    config = MODEL_CONFIG[model]
    url = config["url"]
    model_name = config["model_name"]
    api_key = config["api_key"]
    client = OpenAI(api_key=api_key, base_url=url)

    # 请求数据
    prompt=str(f'{material}\n'
               f'请你根据上面材料，总结故事剧情概述，要求：\n'
               f'1、概述中的人物使用人物姓名\n'
               f'2、使用中文进行总结'
               f'3、字数{wordage}字左右，不要分段\n')
    print(prompt)
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "你现在是一个专业编辑"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            top_p=0.9,
            stream=False
        )
        output = response.choices[0].message.content
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
    except Exception as e:
        print("生成失败:", e)
        return ""

def outline_checker(model="70b_3", material=""):
    # 根据参数选择配置
    config = MODEL_CONFIG[model]
    url = config["url"]
    model_name = config["model_name"]

    # 请求数据
    prompt1=str(f'{material}\n')
    prompt2=str(f'请你仔细阅读上面的小说大纲和分章节剧情，检查一下是否有明显的逻辑错误、人物错误、剧情前后矛盾的问题，优化这份材料，出现英文的地方都更改为中文，不要改变整体结构\n')
    prompt=prompt1+prompt2
    print(prompt)
    data = {
        "model": model_name,  # 使用的模型名称
        "prompt": prompt,
        "stream": False,  # 不使用流式输出，直接返回完整结果
        "max_tokens": 50000  # 生成的最大 token 数量
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
    print(prompt)
    data = {
        "model": model_name,  # 使用的模型名称
        "prompt": prompt,
        "stream": False,  # 不使用流式输出，直接返回完整结果
        "max_tokens": 50000  # 生成的最大 token 数量
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

def user_ask(model="70b_3", prompt=""):
    # 根据参数选择配置
    config = MODEL_CONFIG[model]
    url = config["url"]
    model_name = config["model_name"]
    # 请求数据
    prompt=str(f'{prompt}\n')
    print(prompt)
    data = {
        "model": model_name,  # 使用的模型名称
        "prompt": prompt,
        "stream": False,  # 不使用流式输出，直接返回完整结果
        "max_tokens": 50000  # 生成的最大 token 数量
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

def character_document_update(model="70b_3", content="", character_document=""):
    # 根据参数选择配置
    config = MODEL_CONFIG[model]
    url = config["url"]
    model_name = config["model_name"] 
    # 请求数据
    prompt=str(f'下面是最新章节\n'
               f'{content}\n'
               f'下面是人物档案\n'
               f'{character_document}\n'
               f'操作要求：\n'
               f'1、请你根据最新章节，增加新增角色到人物档案\n'
               f'2、注意只增加，不要去掉任何已经存在的角色\n'
               f'3、格式不要有任何变化\n'
               f'4、重新输出整个人物档案，没有新增请不要更改\n')
    print(prompt)
    data = {
        "model": model_name,  # 使用的模型名称
        "prompt": prompt,
        "stream": False,  # 不使用流式输出，直接返回完整结果
        "max_tokens": 50000  # 生成的最大 token 数量
    }
    # 发送 POST 请求
    response = requests.post(url, json=data)

    if response.status_code == 200:
        try:
            # 解析响应的 JSON 数据
            result = response.json()  # 直接解析整个响应的 JSON 数据
            output = result.get("response", "没有返回内容")
            with open(f"character_document_init.txt", "w", encoding="utf-8") as f:
                f.write(output)
            # 删除 </think> 之前的部分
            output = re.sub(r'^.*?</think>', '', output, flags=re.DOTALL)
            output = re.sub(r'</think>.*$', '', output, flags=re.DOTALL)
            output = output.replace("\n\n","\n")
            output = output.strip()
            with open(f"character_document_new.txt", "w", encoding="utf-8") as f:
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
    # character_document_update(file=args.file, character_document=args.character_document)
    # user_define(file=args.file, prompt=args.requirment, model="70b")
    # user_ask(prompt=args.requirment, model="70b_llama")
    with open("第1卷第1章", 'r', encoding='utf-8') as file:
        matrial = file.read()
    chapter_modifier(model="70b", title="第1卷第1章", material=matrial)