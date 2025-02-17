import os

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