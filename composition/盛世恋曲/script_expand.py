import os
import sys
import random
import datetime
# 获取项目根目录的绝对路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
# 将项目根目录添加到 sys.path
if project_root not in sys.path:
    sys.path.append(project_root)
# 现在可以正常导入 ollama 下的模块
from ollama.ollama_util import *
from util import *
model = "32b_self"
max_chapter = 100
clean_txt_files()
with open('outline', 'r', encoding='utf-8') as file:
    outline = file.read()
with open('character_document', 'r', encoding='utf-8') as file:
    character_document = file.read() 
with open('第1卷', 'r', encoding='utf-8') as file:
    outline_volume = file.read() 
for i in range(1, 6):
    title = f"第{i}卷"
    with open(title, 'r', encoding='utf-8') as file:
        outline_volume = file.read() 
    volume_expender(outline_volume=reverse_chapters_string(outline_volume), outline=outline, character_document=character_document, title=title, model=model)