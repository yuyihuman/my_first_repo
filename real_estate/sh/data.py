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
    adb_command(f"adb pull /sdcard/{filename} {filename}")
    adb_command(f"adb shell rm /sdcard/{filename}")

def scroll_up():
    start_x = 500  # X coordinate remains the same
    start_y = 1700  # Starting Y coordinate
    end_x = 500    # X coordinate remains the same
    end_y = 900  # Ending Y coordinate is `pixels` amount up from start_y
    adb_command(f"adb shell input swipe {start_x} {start_y} {end_x} {end_y}")
    time.sleep(1)  # wait for the scroll to finish

def preprocess_image(image_path="screenshot.png"):
    # Open the image
    img = Image.open(image_path)
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
    preprocessed_filename = "preprocessed_screenshot.png"
    img.save(preprocessed_filename)
    return preprocessed_filename

def capture_and_ocr(screenshot_count=5, width=1080, height=1920, save_interval=10, json_filename="entries.json"):
    # 设置设备分辨率
    set_resolution(width, height)
    entries = []
    valid_communities = ['浦东', '嘉定', '金山', '松江', '青浦', '黄浦', '虹口', '崇明', '宝山']
    for i in range(screenshot_count):
        filename = "screenshot.png"
        capture_screenshot(filename)
        print(f"Screenshot saved as {filename}")
        # Preprocess the image
        preprocessed_filename = preprocess_image(filename)
        print(f"Preprocessed image saved as {preprocessed_filename}")
        # OCR
        img = Image.open(preprocessed_filename)
        text = pytesseract.image_to_string(img, lang='chi_sim', config='--psm 6')
        text = text.replace(' ', '')
        print(f"文本提取结果（第 {i+1} 部分）：\n{text}\n")

        # 检查是否包含“没有更多数据”
        if "没有更多数据" in text:
            print("检测到'没有更多数据'，退出循环")
            save_entries(entries, json_filename)
            break

        entry = parse_text(text, valid_communities)
        entries.extend(entry)
        if (i + 1) % save_interval == 0 or i == screenshot_count - 1:
            save_entries(entries, json_filename)
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

def save_entries(entries, filename="entries.json"):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                existing_entries = json.loads(content)
            else:
                existing_entries = []
    else:
        existing_entries = []

    # 合并现有条目和新条目
    all_entries = existing_entries + entries

    # 去重
    unique_entries = []
    seen_entries = set()
    for entry in all_entries:
        entry_tuple = (entry['date'], entry['area'], entry['price'])
        if entry_tuple not in seen_entries:
            seen_entries.add(entry_tuple)
            unique_entries.append(entry)

    # 按照日期从新到旧排序
    unique_entries.sort(key=lambda x: x['date'], reverse=True)

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(unique_entries, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OCR and JSON saving script")
    parser.add_argument("-n", "--name", type=str, default="entries.json", help="The name of the JSON file to save")
    args = parser.parse_args()
    
    json_filename = args.name  # 从命令行参数获取json文件名
    entries = capture_and_ocr(screenshot_count=30000, width=1080, height=1920, save_interval=10, json_filename=json_filename)
    if entries:
        save_entries(entries, json_filename)
