import subprocess
import time
import pytesseract
import os
import re
import json
import argparse
from PIL import Image
from PIL import ImageEnhance

# 设置Tesseract OCR的路径（如果不在系统路径中）
pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'

def adb_command(command):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error executing command: {command}\n{result.stderr}")
    return result.stdout.strip()

def set_resolution(width, height):
    adb_command(f"adb shell wm size {width}x{height}")

def capture_screenshot(filename="screenshot.png"):
    adb_command(f"adb shell screencap -p /sdcard/{filename}")
    adb_command(f"adb pull /sdcard/{filename} images/temp/{filename}")
    adb_command(f"adb shell rm /sdcard/{filename}")

def scroll_up():
    start_x = 500  # X coordinate remains the same
    start_y = 1700  # Starting Y coordinate
    end_x = 500    # X coordinate remains the same
    end_y = 1100  # Ending Y coordinate is `pixels` amount up from start_y
    adb_command(f"adb shell input swipe {start_x} {start_y} {end_x} {end_y}")
    time.sleep(1)  # wait for the scroll to finish

def preprocess_image(filename):
    # 更新文件路径
    input_path = f"images/temp/{filename}"
    output_path = f"images/temp/preprocessed_{filename}"
    
    # 确保目录存在
    os.makedirs("images/temp", exist_ok=True)
    
    # 图像处理代码
    img = Image.open(input_path)
    # Remove top 210 pixels
    img = img.crop((0, 210, img.width, img.height))
    # Enhance image contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)  # Increase contrast
    # Convert the image to grayscale
    img = img.convert("L")
    # Convert the image to binary (black and white) using a threshold
    threshold = 127
    img = img.point(lambda p: p > threshold and 255)
    img.save(output_path)
    return f"preprocessed_{filename}"

def capture_and_ocr(screenshot_count=5, width=1080, height=1920, save_interval=10, json_filename="entries.json"):
    # 设置设备分辨率
    set_resolution(width, height)
    entries = []
    valid_communities = ['浦东', '嘉定', '金山', '松江', '青浦', '黄浦', '虹口', '崇明', '宝山']
    
    # 确保目录存在
    os.makedirs("data_files", exist_ok=True)
    os.makedirs("images/temp", exist_ok=True)
    os.makedirs("images/final", exist_ok=True)
    
    # 更新JSON文件路径
    json_filepath = os.path.join("data_files", json_filename)
    
    # 加载现有条目用于检查重复
    existing_entries = []
    if os.path.exists(json_filepath):
        with open(json_filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                existing_entries = json.loads(content)
    
    # 创建一个集合来快速检查条目是否存在
    existing_entries_set = {(entry['date'], entry['area'], entry['price']) for entry in existing_entries}
    
    # 用于跟踪连续重复的条目数量
    consecutive_duplicates = 0
    
    for i in range(screenshot_count):
        filename = "screenshot.png"
        capture_screenshot(filename)
        print(f"Screenshot saved as images/temp/{filename}")
        # Preprocess the image
        preprocessed_filename = preprocess_image(filename)
        print(f"Preprocessed image saved as images/temp/{preprocessed_filename}")
        # OCR
        img = Image.open(f"images/temp/{preprocessed_filename}")
        text = pytesseract.image_to_string(img, lang='chi_sim', config='--psm 6')
        text = text.replace(' ', '')
        print(f"文本提取结果（第 {i+1} 部分）：\n{text}\n")

        # 检查是否包含"没有更多数据"
        if "没有更多数据" in text:
            print("检测到'没有更多数据'，退出循环")
            save_entries(entries, json_filepath)
            break

        new_entries = parse_text(text, valid_communities)
        
        # 检查新条目是否已存在
        all_duplicates = True
        if new_entries:  # 确保有解析到条目
            for entry in new_entries:
                entry_tuple = (entry['date'], entry['area'], entry['price'])
                if entry_tuple not in existing_entries_set:
                    all_duplicates = False
                    consecutive_duplicates = 0
                    existing_entries_set.add(entry_tuple)  # 添加到已存在集合中
                    
            if all_duplicates:
                consecutive_duplicates += 1
                print(f"连续重复数据: {consecutive_duplicates}/3")
                
            if consecutive_duplicates >= 3:
                print("检测到连续3条重复数据，停止获取")
                save_entries(entries, json_filepath)
                break
        else:
            # 如果没有解析到条目，不计入连续重复
            consecutive_duplicates = 0
            
        entries.extend(new_entries)
        if (i + 1) % save_interval == 0 or i == screenshot_count - 1:
            save_entries(entries, json_filepath)
            entries = []  # 清空已保存的条目
        if i < screenshot_count - 1:
            scroll_up()
    return entries

def parse_text(text, valid_communities):
    entries = []
    print("parse text")
    lines = text.split('\n')
    for i, line in enumerate(lines):
        line = line.strip()
        print(line)
        if not line:
            continue
        if "号楼" in line:
            # Ensure there are enough lines available
            if i + 1 < len(lines):
                date_line = lines[i + 1].strip()
                print(date_line)
                area_line = lines[i].strip().split("号楼")[-1]
                print(area_line)
                price_line = lines[i + 1].strip()
                print(price_line)
                match_date = re.search(r'(\d{4}\.\d{2}\.\d{2})成交', date_line)
                print(match_date)
                match_area = re.search(r'(\d{2,3})[a-zA-Z]', area_line)
                print(match_area)
                match_price = re.search(r'(\d+)元', price_line)
                print(match_price)
                if match_date and match_area and match_price:
                    date = match_date.group(1)
                    area = int(match_area.group(1))
                    price = int(match_price.group(1))
                    entries.append({
                        'date': date,
                        'area': area,
                        'price': price
                    })
    return entries

def save_entries(entries, filename):
    # 确保目录存在
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    # 加载现有数据
    existing_entries = []
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                existing_entries = json.loads(content)
    
    # 合并并保存
    all_entries = existing_entries + entries
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(all_entries, f, ensure_ascii=False, indent=4)
    print(f"已保存 {len(entries)} 条记录到 {filename}，总计 {len(all_entries)} 条")

if __name__ == "__main__":
    # 设置命令行参数解析
    parser = argparse.ArgumentParser(description="Capture and OCR real estate transaction data.")
    parser.add_argument("-c", "--count", type=int, default=100, help="Number of screenshots to capture")
    parser.add_argument("-n", "--name", type=str, required=True, help="Name of the community")
    args = parser.parse_args()
    
    # 获取小区名称并转换为拼音首字母
    from pypinyin import pinyin, Style
    def get_pinyin_initials(text):
        return ''.join([item[0] for item in pinyin(text, style=Style.FIRST_LETTER)])
    
    filename = get_pinyin_initials(args.name)
    
    # 执行截图和OCR
    capture_and_ocr(screenshot_count=args.count, json_filename=filename)