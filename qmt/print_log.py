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
                if "Final Portfolio Value" in line:
                    final_portfolio_line = line.strip()
                
                # 如果两行都找到了，可以提前退出循环
                if use_model_line and final_portfolio_line:
                    break

            # 如果找到了目标行，打印文件名和对应的行
            if use_model_line or final_portfolio_line:
                print(f"\nFile: {file_path}")
                if use_model_line:
                    print(f"Use Model file line: {use_model_line}")
                if final_portfolio_line:
                    print(f"Final Portfolio Value line: {final_portfolio_line}")
