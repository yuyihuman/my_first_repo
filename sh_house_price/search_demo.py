import subprocess
import time
import os
import logging
from datetime import datetime
import re
import glob

# 清除之前的所有日志文件
def clear_previous_logs():
    """清除之前的所有日志文件"""
    log_dir = "logs"
    if os.path.exists(log_dir):
        log_files = glob.glob(os.path.join(log_dir, "*.log"))
        for log_file in log_files:
            try:
                os.remove(log_file)
                print(f"已删除日志文件: {log_file}")
            except Exception as e:
                print(f"删除日志文件 {log_file} 失败: {e}")
    
    # 清除之前的所有截图
    screenshot_dir = "screenshots"
    if os.path.exists(screenshot_dir):
        screenshot_files = glob.glob(os.path.join(screenshot_dir, "*.png"))
        for screenshot_file in screenshot_files:
            try:
                os.remove(screenshot_file)
                print(f"已删除截图文件: {screenshot_file}")
            except Exception as e:
                print(f"删除截图文件 {screenshot_file} 失败: {e}")
    
    # 清除之前的所有UI层次结构文件
    ui_dir = "ui_dumps"
    if os.path.exists(ui_dir):
        ui_files = glob.glob(os.path.join(ui_dir, "*.xml"))
        for ui_file in ui_files:
            try:
                os.remove(ui_file)
                print(f"已删除UI层次结构文件: {ui_file}")
            except Exception as e:
                print(f"删除UI层次结构文件 {ui_file} 失败: {e}")

# 在程序开始时清除之前的所有日志
clear_previous_logs()

# 设置日志
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_adb_search.log")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

def adb_command(command):
    """执行ADB命令并返回结果"""
    logger.info(f"执行ADB命令: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True, encoding='utf-8')
    if result.returncode != 0:
        logger.error(f"命令执行失败: {result.stderr}")
    else:
        logger.info(f"命令执行成功: {result.stdout[:100]}..." if len(result.stdout) > 100 else f"命令执行成功: {result.stdout}")
    return result.stdout.strip()

def get_device_info():
    """获取设备信息"""
    logger.info("获取设备信息...")
    # 获取设备型号
    model = adb_command("adb shell getprop ro.product.model")
    # 获取屏幕分辨率
    resolution = adb_command("adb shell wm size")
    # 获取Android版本
    android_version = adb_command("adb shell getprop ro.build.version.release")
    
    logger.info(f"设备型号: {model}")
    logger.info(f"屏幕分辨率: {resolution}")
    logger.info(f"Android版本: {android_version}")
    
    return {
        "model": model,
        "resolution": resolution,
        "android_version": android_version
    }

def get_screen_resolution():
    """获取屏幕分辨率"""
    resolution_str = adb_command("adb shell wm size")
    # 解析分辨率字符串，例如 "Physical size: 1080x2340"
    try:
        width, height = resolution_str.split(": ")[1].split("x")
        return int(width), int(height)
    except (IndexError, ValueError) as e:
        logger.error(f"解析分辨率失败: {e}")
        logger.error(f"原始分辨率字符串: {resolution_str}")
        # 返回默认分辨率
        return 1080, 1920

def tap_screen(x, y):
    """点击屏幕上的指定坐标"""
    logger.info(f"点击屏幕坐标: ({x}, {y})")
    adb_command(f"adb shell input tap {x} {y}")
    time.sleep(1)  # 等待点击操作完成

def input_text(text):
    """根据按键坐标表点击拼音输入，每输入一个字母就检查候选词区域"""
    logger.info(f"输入文本: {text}")

    import json
    import pypinyin
    from PIL import Image
    import pytesseract

    pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'

    # 读取按键坐标表
    with open("keyboard_layout.json", "r", encoding="utf-8") as f:
        key_pos = json.load(f)

    width, height = get_screen_resolution()

    def check_candidate_area(target_char):
        """检查候选词区域是否已经出现目标汉字"""
        logger.info(f"检查候选词区域是否已出现'{target_char}'")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        screenshot_file = f"{timestamp}_candidate_check_{target_char}.png"
        capture_screenshot(screenshot_file)
        img = Image.open(f"screenshots/{screenshot_file}")
        y_start = 1163  # 固定起始像素
        y_end = 1316    # 固定结束像素
        candidate_area = img.crop((0, y_start, width, y_end))
        
        crop_filename = f"{timestamp}_candidate_check_crop_{target_char}.png"
        candidate_area.save(f"screenshots/{crop_filename}")
        
        ocr_result = pytesseract.image_to_data(candidate_area, lang='chi_sim', config='--psm 7', output_type=pytesseract.Output.DICT)
        
        # 存储所有识别到的文本及其位置
        all_texts = []
        for i, txt in enumerate(ocr_result['text']):
            if txt.strip():  # 只考虑非空文本
                # 只考虑汉字字符
                is_chinese_char = False
                for char in txt.strip():
                    if '\u4e00' <= char <= '\u9fff':
                        is_chinese_char = True
                        break
                
                if not is_chinese_char:
                    logger.info(f"跳过非汉字文本: '{txt.strip()}'")
                    continue
                    
                # 计算中心点坐标
                center_x = ocr_result['left'][i] + ocr_result['width'][i] // 2
                center_y = ocr_result['top'][i] + ocr_result['height'][i] // 2
                
                all_texts.append({
                    'text': txt.strip(),
                    'x': center_x,
                    'y': center_y,
                    'center_x': center_x,
                    'center_y': center_y,
                    'left': ocr_result['left'][i],
                    'right': ocr_result['left'][i] + ocr_result['width'][i],
                    'width': ocr_result['width'][i],
                    'height': ocr_result['height'][i]
                })
        
        # 查找目标字符
        for item in all_texts:
            if item['text'] == target_char:
                # 检查与其他字符中心点的距离是否小于100像素
                has_nearby_char = False
                for other in all_texts:
                    if other['text'] != target_char:  # 不与自己比较
                        # 计算两个字符中心点之间的距离
                        distance = ((item['center_x'] - other['center_x']) ** 2 + 
                                   (item['center_y'] - other['center_y']) ** 2) ** 0.5
                        
                        if distance < 100:
                            has_nearby_char = True
                            logger.info(f"字符'{target_char}'中心点100像素内有其他汉字'{other['text']}'，距离为{distance:.2f}像素，跳过")
                            break
                    
                if not has_nearby_char:
                    # 没有临近字符，可以选择
                    tap_x = item['x']
                    tap_y = y_start + item['y']
                    logger.info(f"OCR识别到目标汉字'{target_char}'，且中心点100像素内无其他汉字，点击坐标: ({tap_x}, {tap_y})")
                    tap_screen(tap_x, tap_y)
                    return True
                
        # 如果没有找到合适的目标字符（要么没找到，要么都有临近字符）
        logger.warning(f"未找到合适的目标汉字'{target_char}'或所有候选都有临近汉字")
        return False

    def check_full_screen_area(target_char):
        """在1165像素下方的区域中分段识别目标汉字"""
        logger.info(f"在分段区域中查找目标汉字'{target_char}'")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        screenshot_file = f"{timestamp}_full_screen_check_{target_char}.png"
        screenshot_path = capture_screenshot(screenshot_file)
        
        img = Image.open(screenshot_path)
        width, height = img.size
        
        # 定义分段区域
        segments = [
            (1165, 1290),
            (1290, 1416),
            (1416, 1542),  # 将1416-1666分成两个区域
            (1542, 1666),
            (1666, 1793),
            (1793, height)
        ]
        
        # 依次检查每个区域
        for i, (y_start, y_end) in enumerate(segments):
            logger.info(f"检查区域 {i+1}: {y_start}-{y_end}像素")
            
            # 裁剪当前区域
            segment_area = img.crop((0, y_start, width, y_end))
            
            # 保存裁剪区域图片
            crop_filename = f"{timestamp}_segment_{i+1}_crop_{target_char}.png"
            crop_path = os.path.join("screenshots", crop_filename)
            segment_area.save(crop_path)
            
            # OCR识别当前区域
            ocr_result = pytesseract.image_to_data(segment_area, lang='chi_sim', config='--psm 7', output_type=pytesseract.Output.DICT)
            logger.info(f'区域{i+1} OCR结果: {ocr_result}')
            
            # 存储所有识别到的汉字及其位置
            all_texts = []
            for j, txt in enumerate(ocr_result['text']):
                if txt.strip():
                    # 只考虑汉字
                    is_chinese_char = False
                    for char in txt.strip():
                        if '\u4e00' <= char <= '\u9fff':
                            is_chinese_char = True
                            break
                    
                    if not is_chinese_char:
                        logger.info(f"跳过非汉字文本: '{txt.strip()}'")
                        continue
                    
                    center_x = ocr_result['left'][j] + ocr_result['width'][j] // 2
                    center_y = ocr_result['top'][j] + ocr_result['height'][j] // 2
                    all_texts.append({
                        'text': txt.strip(),
                        'center_x': center_x,
                        'center_y': center_y
                    })
            
            # 查找目标字符
            for item in all_texts:
                if item['text'] == target_char:
                    tap_x = item['center_x']
                    tap_y = y_start + item['center_y']  # 转换为全屏坐标
                    logger.info(f"在区域{i+1}中找到目标汉字'{target_char}'，点击坐标: ({tap_x}, {tap_y})")
                    tap_screen(tap_x, tap_y)
                    return True
        
        logger.warning(f"在所有分段区域中均未找到目标汉字'{target_char}'")
        return False

    # 记录是否有任何字符输入失败
    any_char_failed = False
    
    for char in text:
        if ord(char) > 127:  # 中文字符
            py = pypinyin.lazy_pinyin(char)[0]
            logger.info(f"为'{char}'输入拼音: {py}")
            
            # 记录当前字符是否成功输入
            current_char_success = False
            
            # 先检查一次候选区，可能之前输入的拼音已经产生了候选词
            if check_candidate_area(char):
                # 已经找到并选中了目标字符，标记成功并继续下一个字符
                current_char_success = True
                continue
                
            # 逐个输入拼音字母，每输入一个字母后检查候选区
            found_char = False
            for i, letter in enumerate(py):
                if letter in key_pos:
                    tap_screen(key_pos[letter][0], key_pos[letter][1])
                    time.sleep(0.5)  # 等待候选词更新
                    
                    # 每输入一个字母后就检查
                    if check_candidate_area(char):
                        # 找到目标字符，标记为已找到并跳出循环
                        found_char = True
                        current_char_success = True
                        break
                else:
                    logger.warning(f"未找到字母键'{letter}'，跳过")
            
            # 如果输入完所有拼音字母后仍未找到目标字符
            if not found_char:
                logger.warning(f"输入完整拼音后仍未识别到目标汉字'{char}'")
                
                # 新增步骤：点击992, 1243位置
                logger.info(f"点击坐标(992, 1243)以查看更多候选字")
                tap_screen(992, 1243)
                time.sleep(0.8)  # 等待更多候选字显示
                
                # 在1165像素下方的全部区域中识别目标汉字
                if check_full_screen_area(char):
                    # 已找到并点击了目标字符
                    current_char_success = True
                    continue
                else:
                    # 如果仍未找到，清空输入并标记失败，但不立即返回
                    logger.warning(f"在全屏区域中仍未识别到目标汉字'{char}'，放弃当前搜索词的输入")
                    # 清空当前输入
                    adb_command("adb shell input keyevent 123")  # 移动光标到行尾
                    adb_command("adb shell input keyevent --longpress 67 67 67 67 67")  # 长按删除键
                    time.sleep(0.5)
                    # 标记有字符输入失败
                    any_char_failed = True
                    # 不再继续尝试后续字符，直接跳出循环
                    break
            
            time.sleep(0.8)
            
            # 如果当前字符输入失败，不再继续尝试后续字符
            if not current_char_success:
                any_char_failed = True
                break

    # 根据是否有字符输入失败来返回结果
    if any_char_failed:
        logger.warning(f"部分字符输入失败，整体输入失败: '{text}'")
        return False
    else:
        logger.info(f"成功输入所有文本: '{text}'")
        return True

def capture_screenshot(filename="screenshot.png"):
    """截取屏幕并保存到本地"""
    # 确保目录存在
    screenshot_dir = "screenshots"
    os.makedirs(screenshot_dir, exist_ok=True)
    
    full_path = os.path.join(screenshot_dir, filename)
    logger.info(f"截取屏幕并保存至: {full_path}")
    
    adb_command(f"adb shell screencap -p /sdcard/{filename}")
    adb_command(f"adb pull /sdcard/{filename} {full_path}")
    adb_command(f"adb shell rm /sdcard/{filename}")
    
    logger.info(f"截图已保存: {full_path}")
    return full_path

def dump_ui_hierarchy(filename="ui_hierarchy.xml"):
    """导出当前界面的UI层次结构"""
    ui_dir = "ui_dumps"
    os.makedirs(ui_dir, exist_ok=True)
    
    full_path = os.path.join(ui_dir, filename)
    logger.info(f"导出UI层次结构至: {full_path}")
    
    adb_command(f"adb shell uiautomator dump /sdcard/{filename}")
    adb_command(f"adb pull /sdcard/{filename} {full_path}")
    adb_command(f"adb shell rm /sdcard/{filename}")
    
    logger.info(f"UI层次结构已保存: {full_path}")
    return full_path

def find_search_box_by_text(hint_text="输入小区或板块查询二手房/新房成交"):
    """通过提示文字查找搜索框位置"""
    logger.info(f"尝试通过提示文字 '{hint_text}' 查找搜索框...")
    
    # 导出UI层次结构
    dump_ui_hierarchy("search_box.xml")
    
    # 读取UI层次结构文件
    ui_dir = "ui_dumps"
    xml_path = os.path.join(ui_dir, "search_box.xml")
    
    try:
        with open(xml_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        # 查找包含提示文字的节点
        pattern = rf'text="{hint_text}"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
        match = re.search(pattern, xml_content)
        
        if match:
            x1, y1, x2, y2 = map(int, match.groups())
            # 计算搜索框中心点
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            logger.info(f"找到搜索框，中心点坐标: ({center_x}, {center_y})")
            return center_x, center_y
        else:
            logger.warning(f"未找到包含文字 '{hint_text}' 的元素")
            
            # 尝试查找任何可能的搜索框
            edit_text_pattern = r'class="android.widget.EditText"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
            edit_matches = re.findall(edit_text_pattern, xml_content)
            
            if edit_matches:
                # 使用第一个EditText元素
                x1, y1, x2, y2 = map(int, edit_matches[0])
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                logger.info(f"找到可能的搜索框(EditText)，中心点坐标: ({center_x}, {center_y})")
                return center_x, center_y
            
            return None
    except Exception as e:
        logger.error(f"查找搜索框时出错: {e}")
        return None

def click_first_search_result(search_term):
    """点击第一个匹配的搜索结果"""
    logger.info(f"尝试通过OCR识别并点击包含 '{search_term}' 的第一个搜索结果")
    
    # 截取屏幕
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    screenshot_file = f"{timestamp}_search_results_ocr_{search_term}.png"
    capture_screenshot(screenshot_file)
    
    # 使用OCR识别
    from PIL import Image
    import pytesseract
    
    pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'
    
    # 读取截图
    img = Image.open(f"screenshots/{screenshot_file}")
    width, height = img.size
    
    # 只识别纵向大于190像素的区域
    y_start = 190
    search_area = img.crop((0, y_start, width, height))
    crop_filename = f"{timestamp}_search_area_crop_{search_term}.png"
    search_area.save(f"screenshots/{crop_filename}")
    
    # OCR识别
    ocr_result = pytesseract.image_to_data(search_area, lang='chi_sim', config='--psm 11', output_type=pytesseract.Output.DICT)
    
    # 查找匹配的文本
    found = False
    for i, txt in enumerate(ocr_result['text']):
        # 检查文本是否包含搜索词
        if search_term in txt.strip() and ocr_result['conf'][i] > 60:  # 置信度大于60
            # 获取坐标
            x = ocr_result['left'][i] + ocr_result['width'][i] // 2
            y = ocr_result['top'][i] + ocr_result['height'][i] // 2
            
            # 检查横向坐标是否小于500
            if x < 500:
                # 转换为全屏坐标
                tap_x = x
                tap_y = y_start + y
                logger.info(f"OCR识别到搜索结果 '{txt.strip()}'，点击坐标: ({tap_x}, {tap_y})")
                tap_screen(tap_x, tap_y)
                found = True
                break
    
    if not found:
        logger.warning(f"OCR未识别到包含 '{search_term}' 的搜索结果")
        return False

def verify_search_results(search_term):
    """验证搜索结果页面中包含多少个搜索词"""
    logger.info(f"验证搜索结果页面中包含多少个'{search_term}'")
    
    # 截取屏幕
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    screenshot_file = f"{timestamp}_search_results_verify_{search_term}.png"
    capture_screenshot(screenshot_file)
    
    # 使用OCR识别
    from PIL import Image
    import pytesseract
    
    pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'
    
    # 读取截图
    img = Image.open(f"screenshots/{screenshot_file}")
    
    # OCR识别整个屏幕
    ocr_result = pytesseract.image_to_string(img, lang='chi_sim')
    # 去除所有空格
    ocr_result = ocr_result.replace(" ", "").replace("\t", "").replace("\n", "").replace("\r", "")
    
    # 记录完整的OCR识别结果
    logger.info(f"OCR识别结果(已去除空格):\n{ocr_result}")
    
    # 计算搜索词在结果中出现的次数
    count = ocr_result.count(search_term)
    logger.info(f"在搜索结果页面中找到{count}个'{search_term}'")
    
    return count

def search_for_location(location_name, max_retries=5):
    """在搜索框中搜索指定位置"""
    logger.info(f"开始搜索位置: {location_name}")
    
    retry_count = 0
    search_success = False
    
    while not search_success and retry_count < max_retries:
        if retry_count > 0:
            logger.warning(f"第{retry_count}次重试搜索'{location_name}'")
        
        # 获取屏幕分辨率
        width, height = get_screen_resolution()
        logger.info(f"屏幕分辨率: {width}x{height}")
        
        # 1. 先截图查看当前界面
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        capture_screenshot(f"01_before_search_{location_name}_{timestamp}.png")
        
        # 2. 直接使用固定坐标
        search_box_x = 548
        search_box_y = 139
        logger.info(f"使用固定搜索框位置: ({search_box_x}, {search_box_y})")
        
        logger.info(f"点击搜索框位置: ({search_box_x}, {search_box_y})")
        tap_screen(search_box_x, search_box_y)
        
        # 等待搜索框获得焦点
        time.sleep(1)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        capture_screenshot(f"02_after_tap_search_{location_name}_{timestamp}.png")
        
        # 3. 清空搜索框
        logger.info("清空搜索框...")
        adb_command("adb shell input keyevent 123")  # 移动光标到行尾
        adb_command("adb shell input keyevent --longpress 67 67 67 67 67")  # 长按删除键
        time.sleep(1)
        
        # 4. 输入搜索文本
        logger.info(f"输入搜索文本: {location_name}")
        input_success = input_text(location_name)
        logger.info(f"输入文本结果: {'成功' if input_success else '失败'}")
        
        # 如果输入失败，直接进入下一次尝试
        if not input_success:
            logger.warning(f"输入'{location_name}'失败，进入下一次尝试")
            retry_count += 1
            continue
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        capture_screenshot(f"03_after_input_{location_name}_{timestamp}.png")
        
        # 5. 点击搜索按钮或按回车键
        logger.info("点击搜索按钮或按回车键...")
        # 方法1: 点击键盘上的搜索/回车键
        adb_command("adb shell input keyevent 66")  # 66是回车键/搜索键的keycode
        
        # 6. 等待搜索结果加载
        logger.info("等待搜索结果加载...")
        time.sleep(3)
        
        # 7. 截图查看搜索结果
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        capture_screenshot(f"04_search_results_{location_name}_{timestamp}.png")
        
        # 8. 使用OCR识别并点击第一个搜索结果
        result_clicked = click_first_search_result(location_name)
        
        if not result_clicked:
            logger.warning("无法通过OCR找到搜索结果，尝试点击屏幕上的第一个结果位置")
            # 如果无法通过OCR找到结果，尝试点击屏幕上可能的第一个结果位置
            first_result_x = width // 2
            first_result_y = 250  # 固定在纵向190+60像素处
            tap_screen(first_result_x, first_result_y)
        
        # 9. 最终截图
        time.sleep(2)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        capture_screenshot(f"05_final_result_{location_name}_{timestamp}.png")
        
        # 10. 验证搜索结果
        result_count = verify_search_results(location_name)
        if result_count >= 3:
            logger.info(f"搜索成功，找到{result_count}个'{location_name}'")
            search_success = True
        else:
            logger.warning(f"搜索结果不足，仅找到{result_count}个'{location_name}'，需要重试")
            retry_count += 1
            time.sleep(2)
 
    return search_success

def check_adb_connection():
    """检查ADB连接状态"""
    logger.info("检查ADB连接状态...")
    devices = adb_command("adb devices")
    if "device" not in devices:
        logger.error("未检测到已连接的设备，请确保您的设备已通过ADB连接")
        return False
    else:
        logger.info(f"设备已连接: {devices}")
        return True

def process_location_list(location_list):
    """依次处理多个位置关键词，成功则调用house_price.py脚本"""
    logger.info(f"开始处理位置列表: {location_list}")
    
    # 移除单独创建日志文件的代码
    
    for location in location_list:
        logger.info(f"===== 开始处理位置: {location} =====")
        
        # 搜索位置
        search_success = search_for_location(location)
        
        if search_success:
            logger.info(f"搜索'{location}'成功，调用house_price.py脚本")
            
            # 记录开始执行的时间
            start_time = datetime.now()
            logger.info(f"开始执行house_price.py: {start_time}")
            
            # 执行命令并重定向输出
            house_price_cmd = f"python house_price.py -n \"{location}\""
            logger.info(f"执行命令: {house_price_cmd}")
            return_code = os.system(house_price_cmd)
            
            # 记录结束时间
            end_time = datetime.now()
            if return_code == 0:
                logger.info(f"house_price.py脚本执行成功，结束时间: {end_time}")
            else:
                logger.error(f"house_price.py脚本执行失败，返回代码: {return_code}，结束时间: {end_time}")
        
        logger.info(f"===== 完成处理位置: {location} =====")
    
    logger.info("所有位置处理完毕")
    return None  # 不再返回日志文件路径

if __name__ == "__main__":
    # 检查ADB连接
    if not check_adb_connection():
        logger.error("ADB连接失败，脚本终止")
        exit(1)
    
    # 获取设备信息
    device_info = get_device_info()
    
    # 定义要搜索的位置列表
    locations = ["嘉定新城","嘉定老城","松江新城","徐家汇","中信泰富又一城","金地世家","张江汤臣豪园","上海康城","紫竹半岛","​​翠湖天地","​汤臣一品","苏河湾","仁恒河滨城","世茂滨江花园","​​大宁金茂府","中远两湾城","五角场","唐镇"]
    # locations = ["嘉定老城"]
    locations = [location.replace('\u200b', '') for location in locations]
    # 处理位置列表
    process_location_list(locations)
    
    logger.info("=== ADB搜索演示脚本执行完毕 ===")