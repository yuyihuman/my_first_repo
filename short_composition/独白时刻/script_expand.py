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
model = "32b_self_2"
max_chapter = 100
clean_txt_files()
with open('outline', 'r', encoding='utf-8') as file:
    outline = file.read()
with open('character_document', 'r', encoding='utf-8') as file:
    character_document = file.read() 
with open('outline_chapter', 'r', encoding='utf-8') as file:
    outline_chapter = file.read() 
volume_expender_Short(outline_volume=outline_chapter, outline=outline, character_document=character_document, title="独白时刻", model=model)