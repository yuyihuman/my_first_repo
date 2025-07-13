import os
import re
import shutil

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

def check_chapters_new(max_chapter):
    # 获取当前文件夹下的所有文件和文件夹
    files_in_folder = os.listdir()

    missing_chapters = []

    for i in range(1, max_chapter + 1):
        chapter_name = number_to_chapter(i)
        # 检查章节文件是否存在
        if chapter_name not in files_in_folder:
            missing_chapters.append(chapter_name)

    # 如果有缺失的章节
    if missing_chapters:
        first_missing = missing_chapters[0]
        # 提取缺失章节的卷号和章号
        volume = int(first_missing.split("卷")[0].replace("第", ""))
        chapter = int(first_missing.split("卷")[1].replace("第", "").replace("章", ""))
        total_num = (volume - 1) * 20 + chapter

        if total_num > 1:
            previous_chapter = number_to_chapter(total_num - 1)
        else:
            previous_chapter = "无前一个章节"
        next_chapter = number_to_chapter(total_num + 1)
        return first_missing, previous_chapter, next_chapter
    else:
        return "所有章节都存在", None

def get_content_between_hashes(content):
    # 按行分割字符串
    lines = content.splitlines()
    pattern = r'第.*?章'
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

def check_content(content, last_chapter="", number = 1500):
    if not content:
        return 1
    # 分割字符串为行
    lines = content.splitlines()
    # 检查第一行是否以 ### 开头和结尾
    first_line_condition = len(lines) > 0 and lines[0].startswith("###") and lines[0].endswith("###")
    # 检查整个字符串长度是否在 1500 到 2500 之间
    length_condition = number < len(content) < 4000
    # 检查文章中是否包含英文字母
    has_english_letters = any(char.isalpha() and char.isascii() for char in content)
    # has_english_letters = False
    # 使用正则表达式检查文章中是否包含任意数量的 # 连接 篇章正文结束 再连接任意数量的 # 的结构
    pattern = r'#+\s*篇章正文结束\s*#+'
    has_end_marker = bool(re.search(pattern, content))
    # 新增检查：检查 last_chapter 列表中的字符串是否出现在 content 中
    check_last_chapter = True
    last_chapter_lines = [line.strip() for line in last_chapter.splitlines() if line.strip()]
    content_lines = [line.strip() for line in content.splitlines() if line.strip()]
    for i in range(len(last_chapter_lines) - 1):
        current_line = last_chapter_lines[i]
        next_line = last_chapter_lines[i + 1]
        try:
            # 查找当前行在 content_lines 中的索引
            index = content_lines.index(current_line)
            # 检查下一行是否在 content_lines 中紧接着当前行出现
            if content_lines[index + 1] == next_line:
                print(f'duplicat_chapter_lines are {current_line} and {next_line}')
                check_last_chapter = False
                break
        except (IndexError, ValueError):
            continue
    # 新增检查：按换行符分割，检查是否有完全重复的行
    unique_lines = set()
    no_duplicate_lines = True
    for line in lines:
        line = line.strip()
        if line:
            if line in unique_lines:
                no_duplicate_lines = False
                break
            unique_lines.add(line)
    # 如果所有条件都满足，返回 0，否则返回 1
    if first_line_condition and length_condition and not has_english_letters and has_end_marker and check_last_chapter and no_duplicate_lines:
        print(f'check_content pass')
        return 0
    print(f'check_content fail first_line_condition is {first_line_condition} length_condition is {length_condition} has_english_letters is {has_english_letters} has_end_marker is {has_end_marker} check_last_chapter is {check_last_chapter} no_duplicate_lines is {no_duplicate_lines}')
    return 1

def check_outline(content, last_chapter=""):
    if not content:
        return 1
    # 分割字符串为行
    lines = content.splitlines()
    # # 检查第一行是否以 ### 开头和结尾
    # first_line_condition = len(lines) > 0 and lines[0].startswith("###") and lines[0].endswith("###")
    # 检查整个字符串长度是否在 1500 到 2500 之间
    length_condition = 2000 < len(content)
    # 检查文章中是否包含英文字母
    has_english_letters = any(char.isalpha() and char.isascii() for char in content)
    # 使用正则表达式检查文章中是否包含任意数量的 # 连接 篇章正文结束 再连接任意数量的 # 的结构
    pattern = r'#+\s*.+\s*章节细纲结束\s*.+\s*#+'
    has_end_marker = bool(re.search(pattern, content))
    # 新增检查：检查 last_chapter 列表中的字符串是否出现在 content 中
    check_last_chapter = True
    last_chapter_lines = last_chapter.splitlines()
    for line in last_chapter_lines:
        line = line.strip()  # 去除每行首尾空格
        if line and line in content:  # 检查非空行且该行在 content 中
            print(f'duplicat_chapter_line is {line}')
            check_last_chapter = False
            break
    # 新增检查：按换行符分割，检查是否有完全重复的行
    unique_lines = set()
    no_duplicate_lines = True
    for line in lines:
        line = line.strip()
        if line:
            if line in unique_lines:
                no_duplicate_lines = False
                break
            unique_lines.add(line)
    # 如果所有条件都满足，返回 0，否则返回 1
    if length_condition and not has_english_letters and has_end_marker and check_last_chapter and no_duplicate_lines:
        print(f'check_content pass')
        return 0
    print(f'check_content fail length_condition is {length_condition} has_english_letters is {has_english_letters} has_end_marker is {has_end_marker} check_last_chapter is {check_last_chapter} no_duplicate_lines is {no_duplicate_lines}')
    return 1

def check_summerize(content):
    # 分割字符串为行
    lines = content.splitlines()
    # 是否只有1行
    only_one_line_condition = len(lines) == 1
    # 检查整个字符串长度是否小于 250
    length_condition = len(content) < 350
    # 检查文章中是否包含英文字母
    has_english_letters = any(char.isalpha() and char.isascii() for char in content)
    has_english_letters = False
    # 如果两个条件都满足，返回 0，否则返回 1
    if only_one_line_condition and length_condition and not has_english_letters:
        print(f'check_summerize pass')
        return 0
    print(f'check_summerize fail only_one_line_condition is {only_one_line_condition} length_condition is {length_condition} has_english_letters is {has_english_letters}')
    return 1

def extract_character_names(content):
    """
    从字符串内容中提取人物名称并返回一个列表（去掉序号）。

    参数:
    content (str): 包含人物档案的字符串

    返回:
    list: 包含所有人物名称的列表（不带序号）
    """
    # 初始化一个空列表来存储人物名称
    character_names = []

    # 按行分割字符串内容
    lines = content.splitlines()

    # 遍历每一行，提取人物名称
    for line in lines:
        if line.startswith('$$'):
            # 提取人物名称，并去掉序号
            name = line.strip('$$').strip().split('. ')[-1]  # 去掉序号
            character_names.append(name)
    print(character_names)
    return character_names

def is_list_a_contains_list_b(list_a, list_b):
    """
    检查列表 A 是否包含列表 B 的所有元素（使用集合）。
    """
    return set(list_b).issubset(set(list_a))

def copy_file(source_file, destination_file):
    """
    此函数用于将源文件复制到目标文件。

    :param source_file: 源文件的路径
    :param destination_file: 目标文件的路径
    :return: 若复制成功返回 True，若出现错误返回 False
    """
    try:
        # 复制文件，同时保留文件元数据
        shutil.copy2(source_file, destination_file)
        print(f"文件 {source_file} 已成功复制为 {destination_file}。")
        return True
    except FileNotFoundError:
        print(f"源文件 {source_file} 未找到，请检查文件路径。")
    except PermissionError:
        print("没有足够的权限进行文件复制操作，请检查文件权限。")
    except Exception as e:
        print(f"复制文件时出现错误: {e}")
    return False

def remove_lines_starting_with_text(file_path):
    """
    此函数用于移除指定文件中以文字（包括空格加文字）开头的行。

    :param file_path: 要处理的文件的路径
    :return: 若处理成功返回 True，若出现错误返回 False
    """
    try:
        temp_file = 'temp.txt'

        def starts_with_text(line):
            stripped_line = line.lstrip()
            pattern = r'^[a-zA-Z\u4e00-\u9fa5]'
            return bool(re.match(pattern, stripped_line))

        with open(file_path, 'r', encoding='utf-8') as infile, open(temp_file, 'w', encoding='utf-8') as outfile:
            for line in infile:
                if not starts_with_text(line):
                    outfile.write(line)

        os.replace(temp_file, file_path)
        print(f"文件 {file_path} 已重新整理，以文字开头的行已删除。")
        return True
    except FileNotFoundError:
        print(f"源文件 {file_path} 未找到，请检查文件路径。")
    except Exception as e:
        print(f"处理文件时出现错误: {e}")
    return False

def number_to_chapter(number):
    # 计算卷号，卷号从 1 开始，使用整除运算得到卷数
    volume = (number - 1) // 20 + 1
    # 计算章号，章号从 1 开始，使用取模运算得到每卷内的章数
    chapter = (number - 1) % 20 + 1

    # 组合成最终的篇章序号字符串
    result = f"第{volume}卷第{chapter}章"
    return result

def get_chapter_content(chapter_title):
    # 从传入的字符串中提取卷号和当前章号
    pattern = r'第(\d+)卷第(\d+)章'
    match = re.match(pattern, chapter_title)
    if not match:
        print("输入的章节标题格式不正确，请使用 '第X卷第Y章' 的形式。")
        return None
    volume_num = match.group(1)
    current_chapter_num = match.group(2)
    next_chapter_num = int(current_chapter_num) + 1

    # 构建卷文件的名称
    volume_file = f"第{volume_num}卷"

    try:
        with open(volume_file, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        start_index = None
        end_index = None

        # 查找包含当前章号的行的索引
        for i, line in enumerate(lines):
            if f"第{current_chapter_num}章" in line:
                start_index = i
                break

        if start_index is None:
            print(f"未找到 '{chapter_title}' 的相关内容。")
            return None

        # 查找包含下一章号的行的索引
        for i in range(start_index + 1, len(lines)):
            if f"第{next_chapter_num}章" in lines[i]:
                end_index = i
                break

        if end_index is None:
            # 如果没有找到下一章的行，返回从当前章开始到文件末尾的内容
            content = ''.join(lines[start_index:])
        else:
            # 返回当前章到下一章之间的内容
            content = ''.join(lines[start_index:end_index])

        return content

    except FileNotFoundError:
        print(f"未找到文件 '{volume_file}'。")
        return None

def reverse_chapters_string(chapters_string):
    # 提取标题​
    lines = chapters_string.split('\n')
    # 提取标题，假设标题就是第一行​
    title = lines[0]
    # 去除标题行，保留剩余内容​
    chapters_content = '\n'.join(lines[1:])
    # 按章节号拆分字符串​
    chapter_pattern = re.compile(r'^第\d+章\s.*', re.MULTILINE)
    chapter_list = chapter_pattern.split(chapters_content)
    chapter_list = [chapter.strip() for chapter in chapter_list if chapter.strip()]
    # 组合章节号和章节内容​
    full_chapter_list = []
    chapter_numbers = re.findall(r'第\d+章\s.*', chapters_content, re.MULTILINE)
    for i in range(len(chapter_numbers)):
        full_chapter_list.append(chapter_numbers[i] + "\n" + chapter_list[i])
    # 倒排章节列表​
    reversed_chapter_list = full_chapter_list[::-1]
    # 重新组合成字符串​
    reversed_chapters_string = title + '\n\n' + '\n\n'.join(reversed_chapter_list)
    return reversed_chapters_string

if __name__ == "__main__":
    print(number_to_chapter(5))