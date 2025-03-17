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
model = "70b_3w"
clean_txt_files()

with open('material', 'r', encoding='utf-8') as file:
    content = file.read()
outline = ""
outline_chapter = ""

print("========================================================================")
print("========================================================================")
while not outline:
    outline = Outline_Generator(material=content, model=model)
# with open("Outline_modify2.txt", 'r', encoding='utf-8') as file:
#     outline = file.read()
print("========================================================================")
print("========================================================================")    
while not outline_chapter:    
    outline_chapter = Outline_Volume_Generator(material=outline, model=model)
# with open("Outline_Volume_modify2.txt", 'r', encoding='utf-8') as file:
#     outline_chapter = file.read()
# 创建迭代器并输出结果
Last_Outline_Chapter_tmp = ""
Last_Outline_Chapter = ""
# 假设这里要处理 5 卷，可根据实际情况修改范围
for num in range(1, 6):
    chapter = f"第{num}卷"
    print(chapter)
    while check_outline(Last_Outline_Chapter_tmp, last_chapter=Last_Outline_Chapter): 
        print("========================================================================")
        print("========================================================================")
        # 注意：这里假设 Outline_Chapter_Generator 函数已定义
        Last_Outline_Chapter_tmp = Outline_Chapter_Generator(material=f'{outline}\n{outline_chapter}', Last_Outline_Chapter=Last_Outline_Chapter, title=chapter, model=model)
    Last_Outline_Chapter += f'\n\n{Last_Outline_Chapter_tmp}'
    Last_Outline_Chapter_tmp = ""

