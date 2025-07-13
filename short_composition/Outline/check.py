import os
import time

# 定义要检查的字符串
target_strings = [
    "check_content",
    "check_content fail",
    "check_content pass",
    "first_line_condition is False",
    "length_condition is False",
    "has_english_letters is True",
    "has_end_marker is False",
    "check_last_chapter is False",
    "no_duplicate_lines is False"
]

def check_log_file():
    # 初始化计数字典
    counts = {string: 0 for string in target_strings}
    try:
        # 尝试打开名为 log 的文件
        with open('log', 'r', encoding='utf-8') as file:
            content = file.read()
            # 统计每个字符串的出现次数
            for string in target_strings:
                counts[string] = content.count(string)

        # 获取 check_content 的数量
        check_content_count = counts["check_content"]

        # 获取当前文件夹的名字
        current_folder = os.path.basename(os.getcwd())

        # 打印当前文件夹名字
        print(f"当前文件夹名字: {current_folder}")

        # 打印结果
        print(f"check_content 的数量: {check_content_count}")
        for string in target_strings[1:]:
            if check_content_count > 0:
                percentage = (counts[string] / check_content_count) * 100
                print(f"{string} 的数量: {counts[string]}, 占 check_content 的百分比: {percentage:.2f}%")
            else:
                print(f"{string} 的数量: {counts[string]}, 占 check_content 的百分比: 由于 check_content 数量为 0，无法计算百分比")
    except FileNotFoundError:
        print("未找到名为 'log' 的文件，请检查文件是否存在。")


while True:
    check_log_file()
    time.sleep(10)