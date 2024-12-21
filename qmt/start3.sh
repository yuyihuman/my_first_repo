#!/bin/bash

# 遍历当前文件夹中的所有文件
for file in final_model*; do
    # 检查文件是否存在并且是常规文件
    if [ -f "$file" ]; then
        echo "Processing file: $file"
        # 执行 Python 脚本，并传递文件名作为参数
        python backtrader_test.py -m "$file"
    fi
done
