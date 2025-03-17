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
from ollama.ollama_util import chapter_writer_new, summerizer, character_document_update
from util import *
model = "32b_self"
max_chapter = 100
clean_txt_files()
while "所有章节都存在" not in check_chapters(max_chapter):
    # 获取当前日期和时间
    now = datetime.datetime.now()
    print(now)
    with open('plot', 'r', encoding='utf-8') as file:
        plot = file.read()
    with open('outline', 'r', encoding='utf-8') as file:
        outline = file.read()
    with open('character_document', 'r', encoding='utf-8') as file:
        character_document = file.read()
    title, last_title = check_chapters(max_chapter)
    content_chapter = ""
    last_15_lines = []
    while check_content(content_chapter, last_15_lines):
        try:
            with open(last_title, 'r', encoding='utf-8') as file:
                content_last_chapter = file.read()
        except:
            content_last_chapter = ""
        # 按行分割字符串
        lines = content_last_chapter.splitlines()
        # 生成 15 到 19 之间的随机整数
        random_num = random.randint(15, 19)
        # 提取最后 15 行
        last_15_lines = lines[-random_num:-1]
        # 重新组合成字符串
        result = '\n'.join(last_15_lines)
        chapter_writer_new(plot=plot, last_chapter=result, outline=outline, character_document=character_document, wordage=2500, title=title, style="这是一个具有层层反转的悬疑小说，将黑客题材与心理学元素相结合，对科技发展带来的伦理问题进行深刻的探讨", model=model)
        with open(title, 'r', encoding='utf-8') as file:
            content_chapter = file.read()
    # list_old=[]
    # list_new=[]
    # while not is_list_a_contains_list_b(list_new, list_old) or list_old == []:
    #     list_old = extract_character_names(character_document)
    #     print(list_old)
    #     list_new = extract_character_names(character_document_update(content=content_chapter, character_document=character_document,model=model))
    #     print(list_new)
    # remove_lines_starting_with_text("character_document_new.txt")
    # copy_file(source_file="character_document_new.txt", destination_file="character_document")
    summerize = ""
    while check_summerize(summerize):
        summerize = summerizer(material=content_chapter, wordage=300, model=model)
    # title_text = get_content_between_hashes(content=content_chapter)
    with open('plot', 'a', encoding='utf-8') as file:
        # 将 title 和 summarize 写入文件，每个变量占一行
        file.write(f"{title}：\n")
        file.write(f"{summerize}\n")