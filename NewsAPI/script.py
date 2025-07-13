import requests
import json
import os
import sys
import argparse
from datetime import datetime, timedelta, timezone
from newspaper import Article
# 获取项目根目录的绝对路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# 将项目根目录添加到 sys.path
if project_root not in sys.path:
    sys.path.append(project_root)
# 现在可以正常导入 ollama 下的模块
from ollama.ollama_util import story_writer,translator
from util import *

clean_txt_files()
model = "70b_3"
# 设置命令行参数解析
parser = argparse.ArgumentParser(description="传参")
parser.add_argument("-k","--keyword", type=str, default="historical anecdotes")
args = parser.parse_args()

# 你的 NewsAPI API Key
api_key = "89f9a2078afc46709f0a9806455a7830"

# 获取当前时间和 48 小时前的时间
end_date = datetime.now(timezone.utc)
start_date = end_date - timedelta(hours=36)
end_date = end_date - timedelta(hours=12)

# 格式化时间
end_date_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")
start_date_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")

# 目标 URL
url = "https://newsapi.org/v2/everything"

# 请求参数
keyword = args.keyword
params = {
    "q": keyword,
    "from": start_date_str,
    "to": end_date_str,
    "sortBy": "publishedAt",
    "language": "en",
    "apiKey": api_key,
    "pageSize": 3
}

# 配置代理
proxies = {
    "http": "http://127.0.0.1:10808",
    "https": "http://127.0.0.1:10808"
}

# 发送请求
try:
    response = requests.get(url, params=params, proxies=proxies)
    response.raise_for_status()
    data = response.json()
    articles = data.get("articles", [])
    material_full = ""
    
    if articles:
        print(f"共找到 {len(articles)} 篇过去 48 小时内关于 {keyword} 的新闻：\n")
        for idx, article in enumerate(articles, start=1):
            print(f"{idx}. 标题: {article['title']}")
            print(f"   来源: {article['source']['name']}")
            print(f"   时间: {article['publishedAt']}")
            print(f"   链接: {article['url']}")
            print(f"   描述: {article.get('description', '无描述')}")
            
            # 使用 newspaper3k 获取全文内容
            try:
                news_article = Article(article['url'])
                news_article.download()
                news_article.parse()
                full_content = news_article.text
                print(f"   全文: {full_content}\n")
                article['full_content'] = full_content  # 将全文内容添加到文章数据中
                material = f'{full_content}\n'
                material_full += material
                # 将 material 写入 TXT 文件
                # with open("material.txt", 'w', encoding='utf-8') as txt_file:
                #     txt_file.write(material)
                output = story_writer(material=material,title=article['title'], model=model)
                translator(material=output,title=article['title'], model=model)
            except Exception as e:
                print(f"   无法获取全文内容: {e}")
                article['full_content'] = "无法获取全文内容"
        
        # 将新闻数据保存到 JSON 文件
        # with open("news_data_full.json", "w", encoding="utf-8") as json_file:
        #     json.dump(articles, json_file, ensure_ascii=False, indent=4)
        # print("新闻数据（含全文）已保存到 news_data_full.json 文件中。")
    else:
        print(f"没有找到过去 {start_date_str} 到 {end_date_str} 内的新闻。")
except requests.exceptions.RequestException as e:
    print(f"请求失败：{e}")