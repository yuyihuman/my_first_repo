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

with open("第1卷第4章", 'r', encoding='utf-8') as file:
    matrial = file.read()
chapter_modifier(model="70b", title="第1卷第4章", material=matrial)