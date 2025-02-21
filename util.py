import os
import re

def clean_txt_files():
    # 获取当前工作目录
    current_directory = os.getcwd()
    
    # 遍历当前目录下的所有文件
    for filename in os.listdir(current_directory):
        # 检查文件是否以 .txt 结尾
        if filename.endswith(".txt"):
            # 构建文件的完整路径
            file_path = os.path.join(current_directory, filename)
            
            try:
                # 删除文件
                os.remove(file_path)
                print(f"已删除文件: {filename}")
            except Exception as e:
                print(f"删除文件 {filename} 时出错: {e}")

def check_chapters(max_chapter):
    # 获取当前文件夹下的所有文件和文件夹
    files_in_folder = os.listdir()
    
    missing_chapters = []
    
    for i in range(1, max_chapter + 1):
        chapter_name = f"第{i}章"
        
        # 检查章节文件是否存在
        if chapter_name not in files_in_folder:
            missing_chapters.append(chapter_name)
    
    # 如果有缺失的章节
    if missing_chapters:
        first_missing = missing_chapters[0]
        # 找到缺失章节的前一个章节
        missing_index = int(first_missing[1:-1])  # 提取章节数字
        if missing_index > 1:
            previous_chapter = f"第{missing_index - 1}章"
        else:
            previous_chapter = "无前一个章节"  # 如果缺失的是第1章，则没有前一个章节
        return first_missing, previous_chapter
    else:
        return "所有章节都存在", None
    
def get_content_between_hashes(content):
    # 按行分割字符串
    lines = content.splitlines()
    pattern = r'第.*?章：'
    if lines:
        # 获取第一行并去除首尾空白字符
        first_line = lines[0].strip()
        first_line = first_line.replace("###","")
        first_line = re.sub(pattern, '', first_line)
        result = first_line.strip()
        return result
    else:
        print("传入的内容为空。")
    return None

def check_content(content):
    # 分割字符串为行
    lines = content.splitlines()
    # 检查第一行是否以 ### 开头和结尾
    first_line_condition = len(lines) > 0 and lines[0].startswith("###") and lines[0].endswith("###")
    # 检查整个字符串长度是否大于 2100
    length_condition = 1500 < len(content) < 3000
    # 检查文章中是否包含英文字母
    has_english_letters = any(char.isalpha() and char.isascii() for char in content)
    # 如果两个条件都满足，返回 0，否则返回 1
    if first_line_condition and length_condition and not has_english_letters:
        print(f'check_content pass')
        return 0
    print(f'check_content fail first_line_condition is {first_line_condition} length_condition is {length_condition} has_english_letters is {has_english_letters}')
    return 1

if __name__ == "__main__":
    print(get_content_between_hashes(content="### 第二章：命运转折"))