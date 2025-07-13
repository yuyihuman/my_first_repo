import os
import sys
import random
import datetime
# 获取项目根目录的绝对路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
# 将项目根目录添加到 sys.path
if project_root not in sys.path:
    sys.path.append(project_root)
# 现在可以正常导入 ollama 下的模块
from ollama.ollama_util import *
from util import *
model = "qwq_2"
max_chapter = 100
clean_txt_files()
while "所有章节都存在" not in check_chapters_new(max_chapter):
    # 获取当前日期和时间
    now = datetime.datetime.now()
    print(now)
    title, last_title, next_title = check_chapters_new(max_chapter)
    volume = "第" + title.split("第", 2)[1]
    with open(f'../{title}', 'r', encoding='utf-8') as file:
        content = file.read()
    length = len(content)
    content_chapter=""
    while check_content(content_chapter, "", number=length-100):
        content_chapter = chapter_modifier(material=content, model=model, title=title)