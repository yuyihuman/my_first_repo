import os
import sys
# 获取项目根目录的绝对路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
# 将项目根目录添加到 sys.path
if project_root not in sys.path:
    sys.path.append(project_root)
# 现在可以正常导入 ollama 下的模块
from ollama.ollama_util import chapter_writer, summerizer
from util import *
model = "70b_3"
max_chapter = 20
clean_txt_files()
while "所有章节都存在" not in check_chapters(max_chapter):
    with open('outline', 'r', encoding='utf-8') as file:
        content = file.read()
    title, last_title = check_chapters(max_chapter)
    content_chapter = ""
    while check_content(content_chapter):
        try:
            with open(last_title, 'r', encoding='utf-8') as file:
                content_last_chapter = file.read()
        except:
            content_last_chapter = ""
        chapter_writer(material=f'{content}\n{content_last_chapter}', wordage=3000, title=title, style="喜欢奇幻、权谋与心理博弈的读者", model=model, key_info="苏临和顾清歌")
        with open(title, 'r', encoding='utf-8') as file:
            content_chapter = file.read()
    summerize = summerizer(material=content_chapter, model=model)
    title_text = get_content_between_hashes(content=content_chapter)
    with open('outline', 'a', encoding='utf-8') as file:
        # 将 title 和 summarize 写入文件，每个变量占一行
        file.write(f"{title}： {title_text}\n")
        file.write(f"{summerize}\n")
