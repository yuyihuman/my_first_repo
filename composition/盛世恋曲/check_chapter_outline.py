# 存储所有文件中的非空行
all_lines = []

# 遍历第1卷到第5卷的文件
for i in range(1, 6):
    file_name = f"第{i}卷"
    try:
        # 打开文件并以只读模式读取
        with open(file_name, 'r', encoding='utf-8') as file:
            # 逐行读取文件内容
            for line in file:
                # 去除行首尾的空白字符
                line = line.strip()
                # 如果行不为空，则添加到 all_lines 列表中
                if line:
                    all_lines.append(line)
    except FileNotFoundError:
        print(f"文件 {file_name} 未找到。")

# 用于存储重复的行
duplicate_lines = []
# 用于记录已经检查过的行
checked_lines = set()

# 遍历所有非空行
for line in all_lines:
    if line in checked_lines:
        # 如果行已经在 checked_lines 集合中，且不在 duplicate_lines 列表中，则添加到 duplicate_lines 列表中
        if line not in duplicate_lines:
            duplicate_lines.append(line)
    else:
        # 如果行不在 checked_lines 集合中，则添加到 checked_lines 集合中
        checked_lines.add(line)

# 输出重复的行
if duplicate_lines:
    print("发现以下重复的行：")
    for line in duplicate_lines:
        print(line)
else:
    print("未发现重复的行。")