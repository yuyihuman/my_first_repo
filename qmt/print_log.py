import os

# 设置要遍历的文件夹路径
log_folder = "./log"

# 遍历文件夹下所有文件
for root, dirs, files in os.walk(log_folder):
    for file in files:
        # 检查文件是否是文本文件（根据扩展名）
        if file.endswith(".txt"):
            file_path = os.path.join(root, file)
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            # 初始化变量以存储目标行
            use_model_line = None
            final_portfolio_line = None

            # 遍历文件中的每一行
            for line in lines:
                if "Use Model file" in line:
                    use_model_line = line.strip()
                    print(use_model_line)
                if "Final Portfolio Value" in line:
                    final_portfolio_line = line.strip()  # 保存匹配的行
                    print(final_portfolio_line)
