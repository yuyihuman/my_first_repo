import os
import sys
# 获取项目根目录的绝对路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
# 将项目根目录添加到 sys.path
if project_root not in sys.path:
    sys.path.append(project_root)
# 现在可以正常导入 ollama 下的模块
from ollama.ollama_util import *
from util import *
model = "70b_3w_2"
clean_txt_files()

with open('material', 'r', encoding='utf-8') as file:
    content = file.read()
outline = ""
outline_chapter = ""

print("========================================================================")
print("========================================================================")
while not outline:
    outline = Outline_Generator_Short(material=content, model=model)
print("========================================================================")
print("========================================================================")    
while not outline_chapter:    
    outline_chapter = Outline_Chapter_Generator_Short(material=outline, model=model)

