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

# 坐标配置（统一修改）
CANDIDATE_AREA_X_START = 0
CANDIDATE_AREA_Y_START = 1096
CANDIDATE_AREA_Y_END = 1196

# 全屏分段区域（Y起止），最后一个以None表示到屏幕底部
FULL_SCREEN_SEGMENTS_BASE = [
    (1195, 1355),
    (1355, 1535),
    (1535, 1685),
]

# 候选字更多按钮点击坐标
MORE_CANDIDATES_TAP_X = 987
MORE_CANDIDATES_TAP_Y = 1151

# 搜索结果OCR识别区域与阈值
SEARCH_RESULTS_Y_START = 260
SEARCH_RESULTS_X_THRESHOLD = 500

# 搜索框点击坐标
SEARCH_BOX_X = 536
SEARCH_BOX_Y = 188

# OCR失败时的回退点击坐标（第一个结果大致位置）
FALLBACK_FIRST_RESULT_Y = 320

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

def clear_search_box():
    """完全清空搜索框内容"""
    logger.info("开始清空搜索框...")
    
    # 方法1: 全选并删除
    adb_command("adb shell input keyevent 124")  # Ctrl+A (全选)
    time.sleep(0.3)
    adb_command("adb shell input keyevent 67")   # 删除键
    time.sleep(0.3)
    
    # 方法2: 移动到行尾，然后多次删除
    adb_command("adb shell input keyevent 123")  # 移动光标到行尾
    time.sleep(0.3)
    
    # 连续按删除键多次，确保清空
    for i in range(20):  # 增加删除次数，确保清空
        adb_command("adb shell input keyevent 67")  # 删除键
        time.sleep(0.1)
    
    # 方法3: 移动到行首，然后向前删除
    adb_command("adb shell input keyevent 122")  # 移动光标到行首
    time.sleep(0.3)
    
    # 连续按向前删除键
    for i in range(20):
        adb_command("adb shell input keyevent 112")  # 向前删除键
        time.sleep(0.1)
    
    logger.info("搜索框清空完成")

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
        """检查候选词区域是否已经出现目标汉字 - 增强版本"""
        logger.info(f"检查候选词区域是否已出现'{target_char}'")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        screenshot_file = f"{timestamp}_candidate_check_{target_char}.png"
        capture_screenshot(screenshot_file)
        img = Image.open(f"screenshots/{screenshot_file}")
        candidate_area = img.crop((CANDIDATE_AREA_X_START, CANDIDATE_AREA_Y_START, width, CANDIDATE_AREA_Y_END))
        
        crop_filename = f"{timestamp}_candidate_check_crop_{target_char}.png"
        candidate_area.save(f"screenshots/{crop_filename}")
        
        logger.info(f"=== 候选区域OCR识别详情 (目标字符: '{target_char}') ===")
        
        # 准备多种预处理方法
        processed_standard = preprocess_image_for_ocr(candidate_area)
        processed_large = preprocess_for_large_text(candidate_area)
        
        # 保存预处理后的图片用于调试
        processed_standard_file = f"{timestamp}_candidate_standard_{target_char}.png"
        processed_large_file = f"{timestamp}_candidate_large_{target_char}.png"
        processed_standard.save(f"screenshots/{processed_standard_file}")
        processed_large.save(f"screenshots/{processed_large_file}")
        
        best_result = None
        best_confidence = 0
        best_method = ""
        
        # 测试配置：(图像, 方法名, PSM模式)
        test_configs = [
            (candidate_area, "原图", 6),
            (processed_standard, "标准预处理", 6),
            (processed_large, "大字体预处理", 6),
            (candidate_area, "原图", 7),
            (processed_standard, "标准预处理", 7),
            (processed_large, "大字体预处理", 7),
            (candidate_area, "原图", 8),
            (processed_standard, "标准预处理", 8),
            (processed_large, "大字体预处理", 8),
            (candidate_area, "原图", 13),
            (processed_standard, "标准预处理", 13),
            (processed_large, "大字体预处理", 13)
        ]
        
        for test_img, method_name, psm_mode in test_configs:
            try:
                custom_config = f'--psm {psm_mode}'
                ocr_result = pytesseract.image_to_data(test_img, lang='chi_sim', config=custom_config, output_type=pytesseract.Output.DICT)
                
                logger.info(f"  {method_name}(PSM{psm_mode}): 开始识别...")
                
                # 存储所有识别到的文本及其位置
                all_texts = []
                valid_texts = []
                
                for i, txt in enumerate(ocr_result['text']):
                    if txt.strip():  # 只考虑非空文本
                        confidence = int(ocr_result['conf'][i])
                        
                        # 只考虑汉字字符
                        is_chinese_char = False
                        for char in txt.strip():
                            if '\u4e00' <= char <= '\u9fff':
                                is_chinese_char = True
                                break
                        
                        if not is_chinese_char:
                            logger.info(f"    跳过非汉字文本: '{txt.strip()}'(置信度:{confidence})")
                            continue
                        
                        valid_texts.append(f"'{txt.strip()}'({confidence})")
                        
                        if confidence > 30:  # 置信度阈值
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
                                'height': ocr_result['height'][i],
                                'confidence': confidence
                            })
                
                logger.info(f"    识别到的有效汉字: {', '.join(valid_texts[:5])}{'...' if len(valid_texts) > 5 else ''}")
                
                # 查找目标字符
                for item in all_texts:
                    if item['text'] == target_char:
                        logger.info(f"    找到目标字符'{target_char}' | 置信度:{item['confidence']} | 位置:({item['center_x']},{item['center_y']})")
                        
                        # 检查与其他字符中心点的距离是否小于100像素
                        has_nearby_char = False
                        for other in all_texts:
                            if other['text'] != target_char:  # 不与自己比较
                                # 计算两个字符中心点之间的距离
                                distance = ((item['center_x'] - other['center_x']) ** 2 + 
                                           (item['center_y'] - other['center_y']) ** 2) ** 0.5
                                
                                if distance < 100:
                                    has_nearby_char = True
                                    logger.info(f"    字符'{target_char}'中心点100像素内有其他汉字'{other['text']}'，距离为{distance:.2f}像素")
                                    break
                        
                        if not has_nearby_char and item['confidence'] > best_confidence:
                            best_result = item
                            best_confidence = item['confidence']
                            best_method = f"{method_name}(PSM{psm_mode})"
                            logger.info(f"    ✓ 更新最佳候选: 置信度{best_confidence} | 方法:{best_method}")
                        elif has_nearby_char:
                            logger.info(f"    ✗ 跳过: 有临近字符")
                        else:
                            logger.info(f"    ✗ 跳过: 置信度{item['confidence']}低于当前最佳{best_confidence}")
                
            except Exception as e:
                logger.warning(f"  {method_name}(PSM{psm_mode})识别失败: {e}")
        
        # 使用最佳结果
        if best_result:
            tap_x = best_result['x']
            tap_y = CANDIDATE_AREA_Y_START + best_result['y']
            logger.info(f"=== 最终选择: 方法{best_method} | 置信度{best_confidence} | 点击坐标:({tap_x}, {tap_y}) ===")
            tap_screen(tap_x, tap_y)
            return True
        else:
            logger.warning(f"=== 所有方法都未找到合适的目标汉字'{target_char}' ===")
            return False

    def check_full_screen_area(target_char):
        """在1165像素下方的区域中分段识别目标汉字 - 增强版本"""
        logger.info(f"在分段区域中查找目标汉字'{target_char}'")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        screenshot_file = f"{timestamp}_full_screen_check_{target_char}.png"
        screenshot_path = capture_screenshot(screenshot_file)
        
        img = Image.open(screenshot_path)
        width, height = img.size
        
        # 定义分段区域（根据全局配置和当前屏幕高度生成）
        segments = []
        for start, end in FULL_SCREEN_SEGMENTS_BASE:
            segments.append((start, height if end is None else end))
        
        best_global_result = None
        best_global_confidence = 0
        best_global_method = ""
        best_global_segment = -1
        
        # 依次检查每个区域
        for i, (y_start, y_end) in enumerate(segments):
            logger.info(f"=== 检查区域 {i+1}: {y_start}-{y_end}像素 ===")
            
            # 裁剪当前区域
            segment_area = img.crop((0, y_start, width, y_end))
            
            # 保存裁剪区域图片
            crop_filename = f"{timestamp}_segment_{i+1}_crop_{target_char}.png"
            crop_path = os.path.join("screenshots", crop_filename)
            segment_area.save(crop_path)
            
            # 准备多种预处理方法
            processed_standard = preprocess_image_for_ocr(segment_area)
            processed_large = preprocess_for_large_text(segment_area)
            
            # 保存预处理后的图片
            processed_standard_file = f"{timestamp}_segment_{i+1}_standard_{target_char}.png"
            processed_large_file = f"{timestamp}_segment_{i+1}_large_{target_char}.png"
            processed_standard.save(f"screenshots/{processed_standard_file}")
            processed_large.save(f"screenshots/{processed_large_file}")
            
            best_segment_result = None
            best_segment_confidence = 0
            best_segment_method = ""
            
            # 测试配置
            test_configs = [
                (segment_area, "原图", 6),
                (processed_standard, "标准预处理", 6),
                (processed_large, "大字体预处理", 6),
                (segment_area, "原图", 7),
                (processed_standard, "标准预处理", 7),
                (processed_large, "大字体预处理", 7),
                (segment_area, "原图", 8),
                (processed_standard, "标准预处理", 8),
                (processed_large, "大字体预处理", 8),
                (segment_area, "原图", 11),
                (processed_standard, "标准预处理", 11),
                (processed_large, "大字体预处理", 11),
                (segment_area, "原图", 13),
                (processed_standard, "标准预处理", 13),
                (processed_large, "大字体预处理", 13)
            ]
            
            for test_img, method_name, psm_mode in test_configs:
                try:
                    custom_config = f'--psm {psm_mode}'
                    ocr_result = pytesseract.image_to_data(test_img, lang='chi_sim', config=custom_config, output_type=pytesseract.Output.DICT)
                    
                    logger.info(f"  {method_name}(PSM{psm_mode}): 开始识别...")
                    
                    # 存储所有识别到的汉字及其位置
                    all_texts = []
                    valid_texts = []
                    
                    for j, txt in enumerate(ocr_result['text']):
                        if txt.strip():
                            confidence = int(ocr_result['conf'][j])
                            
                            # 只考虑汉字
                            is_chinese_char = False
                            for char in txt.strip():
                                if '\u4e00' <= char <= '\u9fff':
                                    is_chinese_char = True
                                    break
                            
                            if not is_chinese_char:
                                logger.info(f"    跳过非汉字文本: '{txt.strip()}'(置信度:{confidence})")
                                continue
                            
                            valid_texts.append(f"'{txt.strip()}'({confidence})")
                            
                            if confidence > 30:  # 置信度阈值
                                center_x = ocr_result['left'][j] + ocr_result['width'][j] // 2
                                center_y = ocr_result['top'][j] + ocr_result['height'][j] // 2
                                all_texts.append({
                                    'text': txt.strip(),
                                    'center_x': center_x,
                                    'center_y': center_y,
                                    'confidence': confidence
                                })
                    
                    logger.info(f"    识别到的有效汉字: {', '.join(valid_texts[:5])}{'...' if len(valid_texts) > 5 else ''}")
                    
                    # 查找目标字符
                    for item in all_texts:
                        if item['text'] == target_char:
                            logger.info(f"    找到目标字符'{target_char}' | 置信度:{item['confidence']} | 位置:({item['center_x']},{item['center_y']})")
                            
                            if item['confidence'] > best_segment_confidence:
                                best_segment_result = item
                                best_segment_confidence = item['confidence']
                                best_segment_method = f"{method_name}(PSM{psm_mode})"
                                logger.info(f"    ✓ 更新区域最佳候选: 置信度{best_segment_confidence}")
                            else:
                                logger.info(f"    ✗ 置信度{item['confidence']}低于当前区域最佳{best_segment_confidence}")
                
                except Exception as e:
                    logger.warning(f"  {method_name}(PSM{psm_mode})识别失败: {e}")
            
            # 更新全局最佳结果
            if best_segment_result and best_segment_confidence > best_global_confidence:
                best_global_result = best_segment_result
                best_global_confidence = best_segment_confidence
                best_global_method = best_segment_method
                best_global_segment = i + 1
                logger.info(f"  ✓ 更新全局最佳候选: 区域{best_global_segment} | 置信度{best_global_confidence} | 方法:{best_global_method}")
            elif best_segment_result:
                logger.info(f"  ✗ 区域{i+1}最佳置信度{best_segment_confidence}低于全局最佳{best_global_confidence}")
            else:
                logger.info(f"  ✗ 区域{i+1}未找到目标字符")
            
            logger.info(f"=== 区域{i+1}识别完成 ===")
        
        # 使用全局最佳结果
        if best_global_result:
            segment_y_start = segments[best_global_segment - 1][0]
            tap_x = best_global_result['center_x']
            tap_y = segment_y_start + best_global_result['center_y']  # 转换为全屏坐标
            logger.info(f"=== 最终选择: 区域{best_global_segment} | 方法{best_global_method} | 置信度{best_global_confidence} | 点击坐标:({tap_x}, {tap_y}) ===")
            tap_screen(tap_x, tap_y)
            return True
        else:
            logger.warning(f"=== 在所有分段区域中均未找到目标汉字'{target_char}' ===")
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
                logger.info(f"点击坐标({MORE_CANDIDATES_TAP_X}, {MORE_CANDIDATES_TAP_Y})以查看更多候选字")
                tap_screen(MORE_CANDIDATES_TAP_X, MORE_CANDIDATES_TAP_Y)
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
                    clear_search_box()
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
    
    # 只识别纵向大于配置起始像素的区域
    y_start = SEARCH_RESULTS_Y_START
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
            
            # 检查横向坐标是否小于配置阈值
            if x < SEARCH_RESULTS_X_THRESHOLD:
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
    else:
        logger.info(f"成功点击包含 '{search_term}' 的搜索结果")
        return True

def preprocess_image_for_ocr(image):
    """图像预处理以提高OCR识别准确性"""
    import cv2
    import numpy as np
    from PIL import Image  # 添加这行导入
    
    # 将PIL图像转换为OpenCV格式
    img_array = np.array(image)
    if len(img_array.shape) == 3:
        img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    else:
        img_cv = img_array
    
    # 转换为灰度图
    if len(img_cv.shape) == 3:
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    else:
        gray = img_cv
    
    # 应用高斯模糊去噪
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    
    # 应用自适应阈值二值化
    binary = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    
    # 形态学操作去除噪点
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    
    # 将OpenCV图像转换回PIL格式
    processed_image = Image.fromarray(cleaned)
    
    return processed_image

def split_image_for_ocr(image, block_height=200, overlap=50):
    """将图片在纵向分割成小块进行OCR识别（横向保持完整）"""
    from PIL import Image
    import math
    
    width, height = image.size
    blocks = []
    block_positions = []
    
    # 只在纵向分块，横向保持完整宽度
    y_blocks = math.ceil((height - overlap) / (block_height - overlap))
    
    for y in range(y_blocks):
        # 计算当前块的纵向坐标
        top = y * (block_height - overlap)
        bottom = min(top + block_height, height)
        
        # 横向使用完整宽度
        left = 0
        right = width
        
        # 确保块有足够的高度
        if bottom - top > 50:
            block = image.crop((left, top, right, bottom))
            blocks.append(block)
            block_positions.append((left, top, right, bottom))
    
    return blocks, block_positions

def preprocess_for_large_text(image):
    """专门针对大字体文本的预处理"""
    import cv2
    import numpy as np
    from PIL import Image
    
    # 将PIL图像转换为OpenCV格式
    img_array = np.array(image)
    if len(img_array.shape) == 3:
        img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    else:
        img_cv = img_array
    
    # 转换为灰度图
    if len(img_cv.shape) == 3:
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    else:
        gray = img_cv
    
    # 对于大字体，使用更轻微的模糊
    blurred = cv2.GaussianBlur(gray, (1, 1), 0)
    
    # 使用OTSU阈值而不是自适应阈值，更适合大字体
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 使用更小的形态学核，避免大字体笔画粘连
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    
    # 将OpenCV图像转换回PIL格式
    processed_image = Image.fromarray(cleaned)
    
    return processed_image

def ocr_image_blocks(image, search_term, timestamp):
    """对图片进行纵向分块OCR识别"""
    import pytesseract
    from PIL import Image
    
    pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'
    
    # 分割图片（只在纵向分割）
    blocks, positions = split_image_for_ocr(image)
    
    all_detected_texts = []
    total_count = 0
    
    logger.info(f"图片已纵向分割为{len(blocks)}个条带进行OCR识别")
    
    for i, (block, pos) in enumerate(zip(blocks, positions)):
        # 对每个小块尝试多种预处理方法
        processed_block_standard = preprocess_image_for_ocr(block)
        processed_block_large = preprocess_for_large_text(block)
        
        # 保存小块图片用于调试
        block_file_standard = f"{timestamp}_strip_{i}_standard_{search_term}.png"
        block_file_large = f"{timestamp}_strip_{i}_large_{search_term}.png"
        processed_block_standard.save(f"screenshots/{block_file_standard}")
        processed_block_large.save(f"screenshots/{block_file_large}")
        
        logger.info(f"=== 条带{i} OCR识别详情 (高度:{pos[1]}-{pos[3]}) ===")
        
        best_count = 0
        best_texts = []
        best_method = ""
        
        # 尝试不同的预处理方法和PSM模式
        test_configs = [
            (processed_block_standard, "标准预处理", 6),
            (processed_block_large, "大字体预处理", 6),
            (block, "原图", 6),
            (processed_block_standard, "标准预处理", 8),
            (processed_block_large, "大字体预处理", 8),
            (processed_block_standard, "标准预处理", 7),
            (processed_block_large, "大字体预处理", 7),
            (processed_block_standard, "标准预处理", 13),
            (processed_block_large, "大字体预处理", 13)
        ]
        
        for test_img, method_name, psm_mode in test_configs:
            try:
                custom_config = f'--psm {psm_mode}'
                ocr_data = pytesseract.image_to_data(test_img, lang='chi_sim', config=custom_config, output_type=pytesseract.Output.DICT)
                
                block_texts = []
                valid_texts = []
                
                for j, conf in enumerate(ocr_data['conf']):
                    text = ocr_data['text'][j].strip()
                    confidence = int(conf)
                    
                    if text and confidence > 20:
                        block_texts.append(text)
                        valid_texts.append(f"'{text}'({confidence})")
                
                block_full_text = ''.join(block_texts)
                block_count = block_full_text.count(search_term)
                
                logger.info(f"  {method_name}(PSM{psm_mode}): 找到{block_count}个'{search_term}' | 有效文字: {', '.join(valid_texts[:3])}{'...' if len(valid_texts) > 3 else ''}")
                
                # 记录最佳结果
                if block_count > best_count:
                    best_count = block_count
                    best_texts = block_texts
                    best_method = f"{method_name}(PSM{psm_mode})"
                    
                    # 详细记录最佳结果的文字信息
                    if block_count > 0:
                        for j, conf in enumerate(ocr_data['conf']):
                            text = ocr_data['text'][j].strip()
                            confidence = int(conf)
                            if text:
                                x = ocr_data['left'][j]
                                y = ocr_data['top'][j]
                                w = ocr_data['width'][j]
                                h = ocr_data['height'][j]
                                logger.info(f"    最佳结果文字: '{text}' | 置信度: {confidence} | 位置: ({x},{y},{x+w},{y+h})")
                
            except Exception as e:
                logger.warning(f"  {method_name}(PSM{psm_mode})识别失败: {e}")
        
        # 使用最佳结果
        if best_count > 0:
            logger.info(f"  ✓ 最佳方法: {best_method} | 找到{best_count}个'{search_term}'")
            total_count += best_count
            all_detected_texts.extend(best_texts)
        else:
            logger.info(f"  ✗ 所有方法都未找到'{search_term}'")
        
        logger.info(f"=== 条带{i} 识别完成 ===")
    
    logger.info(f"所有条带识别完成，总共找到{total_count}个'{search_term}'")
    return total_count, all_detected_texts

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
    
    # 方法1: 分块识别
    logger.info("开始分块识别...")
    block_count, block_texts = ocr_image_blocks(img, search_term, timestamp)
    
    # 方法2: 整图预处理识别（作为对比）
    logger.info("开始整图预处理识别...")
    processed_img = preprocess_image_for_ocr(img)
    processed_file = f"{timestamp}_processed_{search_term}.png"
    processed_img.save(f"screenshots/{processed_file}")
    
    try:
        ocr_data = pytesseract.image_to_data(processed_img, lang='chi_sim', output_type=pytesseract.Output.DICT)
        
        logger.info("=== 整图OCR识别详情 ===")
        detected_texts = []
        valid_whole_texts = []
        
        for i, conf in enumerate(ocr_data['conf']):
            text = ocr_data['text'][i].strip()
            confidence = int(conf)
            
            if text:
                x = ocr_data['left'][i]
                y = ocr_data['top'][i]
                w = ocr_data['width'][i]
                h = ocr_data['height'][i]
                
                logger.info(f"  文字: '{text}' | 置信度: {confidence} | 位置: ({x},{y},{x+w},{y+h})")
                
                if confidence > 30:
                    detected_texts.append(text)
                    valid_whole_texts.append(f"'{text}'({confidence})")
        
        if valid_whole_texts:
            logger.info(f"整图有效文字(置信度>30): {', '.join(valid_whole_texts)}")
        
        full_text = ''.join(detected_texts)
        whole_count = full_text.count(search_term)
        logger.info(f"整图识别完整文本: {full_text}")
        
    except Exception as e:
        logger.warning(f"整图OCR识别失败: {e}")
        whole_count = 0
        full_text = ""
    
    # 方法3: 原始图像识别（作为备用）
    logger.info("开始原始图像识别...")
    try:
        original_ocr = pytesseract.image_to_string(img, lang='chi_sim')
        original_clean = original_ocr.replace(" ", "").replace("\t", "").replace("\n", "").replace("\r", "")
        original_count = original_clean.count(search_term)
        logger.info(f"原始图像识别结果: {original_ocr}")
        logger.info(f"原始图像清理后文本: {original_clean}")
    except Exception as e:
        logger.warning(f"原始图像OCR识别失败: {e}")
        original_count = 0
    
    # 记录结果
    logger.info(f"=== 最终识别结果对比 ===")
    logger.info(f"分块识别找到{block_count}个'{search_term}'")
    logger.info(f"整图预处理识别找到{whole_count}个'{search_term}'")
    logger.info(f"原始图像识别找到{original_count}个'{search_term}'")
    
    # 返回最大的计数值
    final_count = max(block_count, whole_count, original_count)
    logger.info(f"最终结果: 找到{final_count}个'{search_term}'")
    
    return final_count

def search_for_location(location_name, max_retries=3):
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
        
        # 2. 使用统一配置的搜索框坐标
        search_box_x = SEARCH_BOX_X
        search_box_y = SEARCH_BOX_Y
        logger.info(f"使用搜索框位置: ({search_box_x}, {search_box_y})")
        logger.info(f"点击搜索框位置: ({search_box_x}, {search_box_y})")
        tap_screen(search_box_x, search_box_y)
        
        # 等待搜索框获得焦点
        time.sleep(1)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        capture_screenshot(f"02_after_tap_search_{location_name}_{timestamp}.png")
        
        # 3. 清空搜索框
        clear_search_box()
        
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
            first_result_y = FALLBACK_FIRST_RESULT_Y
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
    locations = ["嘉定新城","松江新城","徐家汇","五角场","唐镇","安亭","中信泰富又一城","上海康城","中远两湾城","金地世家"]
    locations = [location.replace('\u200b', '') for location in locations]
    # 处理位置列表
    process_location_list(locations)
    
    logger.info("=== ADB搜索演示脚本执行完毕 ===")
