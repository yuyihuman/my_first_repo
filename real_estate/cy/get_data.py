import pytesseract
import os
import re
import json
from PIL import Image, ImageOps
import matplotlib.pyplot as plt
from pypinyin import pinyin, Style

# 设置Tesseract OCR的路径（如果不在系统路径中）
pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'

def split_image(image, chunk_height, border_size=2, border_color='black'):
    chunks = []
    width, height = image.size
    for i in range(410, height, chunk_height):
        box = (0, i, width, min(i + chunk_height, height-200))
        chunk = image.crop(box)
        chunk_with_border = ImageOps.expand(chunk, border=(border_size, border_size), fill=border_color)
        chunks.append(chunk_with_border)
    return chunks

def remove_duplicates(entries):
    unique_entries = []
    seen = set()
    for entry in entries:
        key = (entry['date'], entry['area'], entry['price'])
        if key not in seen:
            unique_entries.append(entry)
            seen.add(key)
    return unique_entries

# 定义解析函数
current_community = "曹杨"
filename = ''.join([c[0] for c in pinyin(current_community, style=Style.FIRST_LETTER)]) + ".json"
entries = {current_community: []}
def parse_text(text):
    print("parse text")
    lines = text.split('\n')
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        if current_community in line:
            date_line = lines[i + 2].strip()
            print(date_line)
            area_line = lines[i + 1].strip()
            print(area_line)
            price_line = lines[i + 2].strip()
            print(price_line)
            match_date = re.search(r'(\d{4}\.\d{2}\.\d{2})成交', date_line)
            print(match_date)
            match_area = re.search(r'(\d+)m', area_line)
            print(match_area)
            match_price = re.search(r'(\d+)元/m', price_line)
            print(match_price)
            if match_date and match_area and match_price:
                date = match_date.group(1)
                area = int(match_area.group(1))
                price = int(match_price.group(1))
                entries[current_community].append({
                    'date': date,
                    'area': area,
                    'price': price
                })
    return entries

# 设置每个小图片的高度
chunk_height = 4970*2

if __name__ == "__main__":
    # 打开图片文件
    i = 1
    while True:
        img_path = f'{i}.jpg'
        if not os.path.exists(img_path):
            break
        img = Image.open(img_path)
        image_chunks = split_image(img, chunk_height)

        # 分割图片
        image_chunks = split_image(img, chunk_height)

        # 逐个处理小图片并提取文本
        for j, chunk in enumerate(image_chunks):
            # plt.figure()
            # plt.imshow(chunk)
            # plt.title(f"Chunk {j+1}")
            # plt.axis('off')
            # plt.show()
            text = pytesseract.image_to_string(chunk, lang='chi_sim', config='--psm 6')
            print(f"文本提取结果（第 {j+1} 部分）：\n{text}\n")
            # 去除空格
            text = text.replace(' ', '')
            entries = parse_text(text)
            entries[current_community] = remove_duplicates(entries[current_community])
            # 将current_community转换为拼音首字母并拼接成文件名
            with open(filename, 'w') as f:
                json.dump(entries, f , indent=4)
            # if j == 0:
            #     break
        i += 1
        # if i == 2:
        #     break
