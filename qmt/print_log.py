import os
from datetime import datetime
import argparse

def process_logs(log_folder="./log"):
    # 存储日志的列表
    log_entries = []

    # 遍历文件夹下所有文件
    for root, dirs, files in os.walk(log_folder):
        for file in files:
            # 检查文件是否是文本文件（根据扩展名）
            if file.endswith(".log"):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                
                # 遍历文件中的每一行
                for line in lines:
                    if "Use Model file" in line or "Final Portfolio Value" in line:
                        # 提取时间戳
                        try:
                            timestamp_str = line.split(" - ")[0]
                            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S,%f")
                            log_entries.append((timestamp, line.strip()))  # 保存时间戳和行内容
                        except ValueError:
                            # 如果时间戳解析失败，跳过该行
                            continue

    # 按时间戳对日志进行排序
    log_entries.sort(key=lambda x: x[0])

    # 打印排序后的日志
    print("==================================================")
    print("==================================================")
    print("==================================================")
    print("==================================================")
    print("==================================================")
    for _, log in log_entries:
        print(log)

# 设置 argparse 参数
def main():
    parser = argparse.ArgumentParser(description="Process log files and sort them by timestamp.")
    parser.add_argument(
        "--log_folder", 
        type=str, 
        default="./log", 
        help="Path to the folder containing log files (default is './log')."
    )
    
    args = parser.parse_args()
    
    # 调用函数，传入指定的 log_folder
    process_logs(log_folder=args.log_folder)

if __name__ == "__main__":
    main()
