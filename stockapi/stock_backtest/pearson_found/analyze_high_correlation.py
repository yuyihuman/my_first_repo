#!/usr/bin/env python
# -*- coding: utf-8 -*-

import csv
import re
import argparse
import os
import logging
import datetime
import sys
from collections import defaultdict
import pandas as pd
from data_loader import StockDataLoader
import unicodedata

def analyze_csv_data(file_path, min_correlation_count=10):
    """分析CSV数据，找出高性能指标（适配新CSV表头，使用实际计算数量）"""
    results = {'total': 0, 'correlated': 0, 'high_performance': 0, 'by_stock': {}, 'details': []}

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)  # 读取标题行

            # 按表头定位列索引（适配扩展后的CSV表头）
            code_index = header.index('代码')
            date_index = header.index('评测日期')
            actual_index = header.index('实际计算数量')

            # 动态识别指标列：仅纳入“下1日高开”和“下1日上涨”，不考虑2-10日上涨
            metric_labels = []
            for col in header:
                if col.startswith('下') and (('上涨' in col) or ('高开' in col)):
                    # 兼容“下一日”与“下1日”的写法
                    col_norm = col.replace('下一日', '下1日')
                    m = re.search(r'下(\d+)日', col_norm)
                    if m:
                        try:
                            d = int(m.group(1))
                            if d == 1:
                                metric_labels.append(col)
                        except Exception:
                            pass
            # 保持原有顺序（按CSV表头）
            metrics_indices = [header.index(lbl) for lbl in metric_labels]

            def parse_pct(val):
                if not val or val == 'N/A':
                    return 0.0
                try:
                    return float(val.strip('%'))
                except Exception:
                    return 0.0

            for row in reader:
                results['total'] += 1

                stock_code = row[code_index]
                date = row[date_index]
                actual_calc_count = int(row[actual_index]) if row[actual_index] not in ('', 'N/A') else 0
                metric_values = [parse_pct(row[i]) for i in metrics_indices]

                # 以实际计算数量作为阈值判断
                if actual_calc_count >= min_correlation_count:
                    results['correlated'] += 1

                    if stock_code not in results['by_stock']:
                        results['by_stock'][stock_code] = {'correlated': 0, 'high_performance': 0}
                    results['by_stock'][stock_code]['correlated'] += 1

                    performance_metrics = list(zip(metric_labels, metric_values))
                    high_performance_count = sum(1 for _, v in performance_metrics if v >= 80)

                    if high_performance_count > 0:
                        results['high_performance'] += 1
                        results['by_stock'][stock_code]['high_performance'] += 1

                        # 找出最高百分比及对应天数（适配2/4/6/7/8/9日）
                        max_percentage = -1.0
                        max_percentage_metric = ''
                        max_percentage_days = 0
                        for metric_name, value in performance_metrics:
                            if value > max_percentage:
                                max_percentage = value
                                max_percentage_metric = metric_name
                                # 从指标名中提取“下X日”数字（兼容高开/上涨）
                                m = re.search(r'下(\d+)日', metric_name)
                                if m:
                                    try:
                                        max_percentage_days = int(m.group(1))
                                    except Exception:
                                        max_percentage_days = 1
                                else:
                                    # 默认回退到1日
                                    max_percentage_days = 1

                        # 根据最佳指标确定卖出方式（仅 sell_days==1 生效）
                        sell_mode = None
                        if max_percentage_days == 1:
                            base_label = max_percentage_metric.split('(')[0]
                            if '高开' in base_label:
                                sell_mode = 'open'
                            elif '上涨' in base_label:
                                sell_mode = 'close'
                        price_data = get_stock_price_data(stock_code, date, max_percentage_days, sell_mode=sell_mode)

                        # 汇总详情（包含全部指标文本，便于后续展示）
                        results['details'].append({
                            'stock_code': stock_code,
                            'date': date,
                            'buy_date': date,
                            'actual_calc_count': actual_calc_count,
                            'high_performance_count': high_performance_count,
                            'valid_metrics_count': len(performance_metrics),
                            'metrics': [f"{name}({value:.2f}%)" for name, value in performance_metrics],
                            'max_percentage': max_percentage,
                            'max_percentage_metric': max_percentage_metric,
                            'sell_days': max_percentage_days,
                            'buy_price': price_data['买入价'] if '买入价' in price_data else price_data['buy_price'],
                            'sell_price': price_data['卖出价'] if '卖出价' in price_data else price_data['sell_price'],
                            'change_percent': price_data.get('change_percent', 'N/A'),
                            'max_up_percent': price_data.get('max_up_percent', 'N/A'),
                            'max_down_percent': price_data.get('max_down_percent', 'N/A')
                        })

        return results
    except Exception as e:
        logging.error(f"分析CSV数据时出错: {e}")
        return results

def get_stock_price_data(stock_code, date_str, sell_days, sell_mode=None):
    """
    获取买入/卖出价格与最大涨跌幅。
    优先使用真实日线数据；若数据不可用，则使用模拟数据并保证数值一致性。

    参数说明：
    - stock_code: 股票代码
    - date_str: 买入日期字符串
    - sell_days: 持股天数（整数）
    - sell_mode: 可选的卖出方式，'open' 表示按开盘价卖出，'close' 表示按收盘价卖出；
                 当 sell_days == 1 时生效；为 None 时默认按收盘价卖出。
    """
    try:
        import pandas as pd
        from data_loader import StockDataLoader
        loader = StockDataLoader()
        df = loader.load_stock_data(stock_code, 'daily')
        buy_dt = pd.to_datetime(date_str)

        # 判断1日持股时的卖出方式（开盘/收盘）
        # 优先使用调用方指定的 sell_mode；若未指定则默认按收盘价卖出。
        if sell_days == 1:
            if sell_mode == 'open':
                is_open_sell = True
            elif sell_mode == 'close':
                is_open_sell = False
            else:
                is_open_sell = False
        else:
            is_open_sell = False

        if df is not None and not df.empty:
            # 使用真实数据
            if buy_dt not in df.index:
                # 使用买入日前的最近一个交易日
                prior = df.index[df.index <= buy_dt]
                if len(prior) == 0:
                    raise ValueError("无可用历史数据")
                buy_idx = df.index.get_loc(prior[-1])
            else:
                buy_idx = df.index.get_loc(buy_dt)

            sell_idx = buy_idx + sell_days
            if sell_idx >= len(df):
                sell_idx = len(df) - 1

            buy_price = float(df.iloc[buy_idx]['close'])
            if is_open_sell:
                # 开盘卖出：次日开盘价（或目标卖出日开盘价）
                if buy_idx + 1 < len(df):
                    sell_price = float(df.iloc[buy_idx + 1]['open'])
                else:
                    sell_price = float(df.iloc[sell_idx]['open'])
            else:
                sell_price = float(df.iloc[sell_idx]['close'])

            # 计算持有期内最大涨幅（相对买入价的最高点）与最大跌幅（相对买入价的最低点）
            start = buy_idx + 1 if buy_idx + 1 < len(df) else buy_idx
            end = sell_idx
            window = df.iloc[start:end + 1] if end >= start else df.iloc[buy_idx:buy_idx + 1]

            high_max = float(window['high'].max()) if 'high' in window.columns else buy_price
            low_min = float(window['low'].min()) if 'low' in window.columns else buy_price

            max_up_percent = max(0.0, (high_max - buy_price) / buy_price * 100)
            drawdown = (low_min - buy_price) / buy_price * 100
            max_down_percent = abs(min(0.0, drawdown))

            change_percent = (sell_price - buy_price) / buy_price * 100

            # 一致性保障：最大涨/跌幅至少覆盖最终涨跌幅的绝对值
            if change_percent >= 0:
                max_up_percent = max(max_up_percent, change_percent)
            else:
                max_down_percent = max(max_down_percent, abs(change_percent))

            return {
                'buy_price': f"{buy_price:.2f}",
                'sell_price': f"{sell_price:.2f}",
                'change_percent': f"{change_percent:.2f}%",
                'max_up_percent': f"{max_up_percent:.2f}%",
                'max_down_percent': (f"-{max_down_percent:.2f}%" if max_down_percent > 0 else "0.00%")
            }

        # 数据不可用：使用原模拟逻辑，但做一致性修正
        import numpy as np
        code_seed = int(stock_code[-4:]) if len(stock_code) >= 4 else 1000
        seed = code_seed + sell_days
        np.random.seed(seed)

        buy_price = round(np.random.uniform(20, 100), 2)
        if sell_days <= 1:
            change_percent = round(np.random.uniform(-3, 5), 2)
            max_up_percent = round(np.random.uniform(0.5, 6), 2)
            max_down_percent = round(np.random.uniform(0.5, 4), 2)
        elif sell_days <= 3:
            change_percent = round(np.random.uniform(-5, 8), 2)
            max_up_percent = round(np.random.uniform(1, 10), 2)
            max_down_percent = round(np.random.uniform(1, 7), 2)
        elif sell_days <= 5:
            change_percent = round(np.random.uniform(-8, 12), 2)
            max_up_percent = round(np.random.uniform(2, 15), 2)
            max_down_percent = round(np.random.uniform(2, 10), 2)
        else:
            change_percent = round(np.random.uniform(-10, 15), 2)
            max_up_percent = round(np.random.uniform(3, 20), 2)
            max_down_percent = round(np.random.uniform(3, 15), 2)

        sell_price = round(buy_price * (1 + change_percent / 100), 2)

        # 一致性保障
        if change_percent >= 0:
            max_up_percent = max(max_up_percent, change_percent)
        else:
            max_down_percent = max(max_down_percent, abs(change_percent))

        return {
            'buy_price': f"{buy_price:.2f}",
            'sell_price': f"{sell_price:.2f}",
            'change_percent': f"{change_percent:.2f}%",
            'max_up_percent': f"{max_up_percent:.2f}%",
            'max_down_percent': (f"-{max_down_percent:.2f}%" if max_down_percent > 0 else "0.00%")
        }
    except Exception as e:
        logging.error(f"生成/计算股票价格数据时出错: {e}")
        return {'buy_price': '50.00', 'sell_price': '52.50', 'change_percent': '5.00%', 'max_up_percent': '10.00%', 'max_down_percent': '5.00%'}

def setup_logging(log_dir='logs'):
    """设置日志记录"""
    # 创建日志目录（使用绝对路径）
    log_dir = os.path.abspath(log_dir)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 生成日志文件名
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(log_dir, f'analyze_high_correlation_{timestamp}.log')
    
    print(f"日志文件将保存到: {log_file}")
    
    # 配置日志
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # 清除之前的处理器
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 添加文件处理器（包含文件名与代码行号）
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'))
    logger.addHandler(file_handler)
    
    # 添加控制台处理器（包含文件名与代码行号）
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'))
    logger.addHandler(console_handler)
    
    # 测试日志
    logger.info(f"日志系统初始化完成，日志文件: {log_file}")

    # 统计并输出当前脚本的代码行数
    try:
        with open(__file__, 'r', encoding='utf-8') as _f:
            _line_count = sum(1 for _ in _f)
        logger.info(f"当前脚本代码行数: {_line_count}")
    except Exception as e:
        logger.warning(f"无法统计代码行数: {e}")
    
    return logger, log_file

def _display_width(text):
    """计算文本的显示宽度，CJK宽字符按宽度2，其他按1"""
    s = str(text)
    width = 0
    for ch in s:
        width += 2 if unicodedata.east_asian_width(ch) in ('W', 'F') else 1
    return width

def _pad(text, width, align='left'):
    """将文本填充到指定显示宽度"""
    s = str(text)
    w = _display_width(s)
    if w >= width:
        return s
    pad_len = width - w
    if align == 'right':
        return ' ' * pad_len + s
    elif align == 'center':
        left = pad_len // 2
        right = pad_len - left
        return (' ' * left) + s + (' ' * right)
    else:
        return s + (' ' * pad_len)

def _format_table(headers, rows, aligns=None, sep='  '):
    """按列对齐生成表格字符串，考虑CJK宽字符显示宽度"""
    if not rows:
        return ''
    col_count = len(headers)
    aligns = aligns or ['left'] * col_count
    # 计算每列最大显示宽度
    widths = [max(_display_width(headers[i]), max(_display_width(r[i]) for r in rows)) for i in range(col_count)]
    # 构建表头和行
    lines = []
    header_line = sep.join(_pad(headers[i], widths[i], aligns[i]) for i in range(col_count))
    lines.append(header_line)
    for r in rows:
        line = sep.join(_pad(r[i], widths[i], aligns[i]) for i in range(col_count))
        lines.append(line)
    return '\n'.join(lines) + '\n'

def _format_table_with_originals(headers, rows, original_lines, csv_file_path, aligns=None, sep='  '):
    """生成带原始CSV记录前置输出的表格字符串"""
    if not rows:
        return ''
    col_count = len(headers)
    aligns = aligns or ['left'] * col_count
    widths = [max(_display_width(headers[i]), max(_display_width(r[i]) for r in rows)) for i in range(col_count)]
    lines = []
    header_line = sep.join(_pad(headers[i], widths[i], aligns[i]) for i in range(col_count))
    lines.append(header_line)
    for r, orig in zip(rows, original_lines):
        # 在每条对齐行之前输出对应的原始CSV记录
        lines.append(f"原始记录({csv_file_path}): {orig}")
        line = sep.join(_pad(r[i], widths[i], aligns[i]) for i in range(col_count))
        lines.append(line)
    return '\n'.join(lines) + '\n'

def save_results_to_file(results, output_file, count_threshold=100, eval_days=15, selected_day=5, selected_days=None):
    """将结果保存到文件"""
    try:
        # 确保输出目录存在
        abs_path = os.path.abspath(output_file)
        out_dir = os.path.dirname(abs_path)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("===== 分析结果 =====\n")
            f.write(f"总记录数: {results['total_records']}\n")
            f.write(f"实际计算数量超过阈值的记录数: {results['filtered_records']}\n")
            f.write(f"有高性能指标的记录数: {results['high_performance_records']}\n")
            if results['filtered_records'] > 0:
                ratio = results['high_performance_records'] / results['filtered_records'] * 100
                f.write(f"高性能记录占比: {ratio:.2f}% (在实际计算数量超过阈值的记录中)\n\n")
            else:
                f.write("高性能记录占比: N/A (在实际计算数量超过阈值的记录中)\n\n")
            
            f.write("----- 按股票代码统计 -----\n")
            # 按高性能记录数量排序
            sorted_stocks = sorted(
                results['stock_stats'].items(), 
                key=lambda x: x[1]['high_performance'], 
                reverse=True
            )
            
            f.write("股票代码\t符合条件记录数\t高性能记录数\t高性能占比\n")
            for stock_code, stats in sorted_stocks:  # 输出所有记录
                if stats['filtered'] > 0:
                    ratio = stats['high_performance'] / stats['filtered'] * 100
                    f.write(f"{stock_code}\t{stats['filtered']}\t{stats['high_performance']}\t{ratio:.2f}%\n")
            
            f.write("\n----- 按日期统计 -----\n")
            # 按日期排序
            sorted_dates = sorted(results['date_stats'].items())
            
            f.write("日期\t\t符合条件记录数\t高性能记录数\t高性能占比\n")
            for date, stats in sorted_dates:  # 输出所有记录
                if stats['filtered'] > 0:
                    ratio = stats['high_performance'] / stats['filtered'] * 100
                    f.write(f"{date}\t{stats['filtered']}\t{stats['high_performance']}\t{ratio:.2f}%\n")
            
            f.write("\n----- 高性能记录详情 -----\n")
            details_rows = []
            details_headers = [
                "股票代码", "日期", "实际计算数量", "高性能指标数/总指标数", "最佳指标",
                "买入日期", "卖出天数", "交易建议", "买入价", "卖出价", "涨跌幅", "最大涨幅", "最大跌幅"
            ]
            details_aligns = ['left','left','right','right','left','left','left','left','right','right','right','right','right']
            
            # 选择器：统计“所选持股天数列表”内的记录
            days_list = []
            if isinstance(selected_days, (list, tuple)) and len(selected_days) > 0:
                days_list = [int(x) for x in selected_days]
            else:
                days_list = [int(selected_day)]

            def _is_selected_detail(d):
                # 依据持股天数是否在选择列表中
                try:
                    sd = int(d.get('sell_days', 0))
                except Exception:
                    return False
                return sd in days_list

            # 统计涨跌情况
            up_count = 0
            down_count = 0
            flat_count = 0
            na_count = 0
            
            # 按持股天数统计（统计所选持股天数列表：均为收盘卖出一类）
            allowed_days = days_list
            days_stats = {
                f"{d}_close": {'up': 0, 'down': 0, 'flat': 0, 'na': 0, 'total': 0}
                for d in days_list
            }
            
            # 相关数量大于阈值的统计（统计所选持股天数列表：收盘卖出一类）
            high_corr_stats = {
                f"{d}_close": {'up': 0, 'down': 0, 'flat': 0, 'na': 0, 'total': 0}
                for d in days_list
            }

            # 新增：按区间位置条件分组统计（过去 eval_days 个交易日，含当日）
            from data_loader import StockDataLoader
            loader = StockDataLoader()
            # 这里返回中文标签，便于直接用于输出
            price_zone_stats = {
                '满足条件': {'up': 0, 'down': 0, 'flat': 0, 'na': 0, 'total': 0},
                '不满足条件': {'up': 0, 'down': 0, 'flat': 0, 'na': 0, 'total': 0},
            }

            def _ma10_condition_for_date(stock_code, date_str, window_days):
                """
                分组条件（过去 window_days 个交易日，含当日）：
                计算窗口内的总交易区间：使用 min(low) 与 max(high)（如无则退化为 min(close) 与 max(close)）。
                当日收盘在该区间的位置占比 pos = (close_today - min_low) / (max_high - min_low)。
                若 pos <= 0.10 则返回 '满足条件'，否则返回 '不满足条件'。
                """
                try:
                    import pandas as pd
                    # 需要 close/low/high 列（low/high优先，缺失则退化为close）
                    df = loader.load_stock_data(stock_code, 'daily', fields=['close', 'low', 'high'])
                    if df is None or df.empty:
                        return '不满足条件'
                    buy_dt = pd.to_datetime(date_str)
                    # 若买入日期不在索引，使用最近不晚于买入日的日期
                    if buy_dt not in df.index:
                        prior = df.index[df.index <= buy_dt]
                        if len(prior) == 0:
                            return '不满足条件'
                        buy_idx = df.index.get_loc(prior[-1])
                    else:
                        buy_idx = df.index.get_loc(buy_dt)

                    # 窗口：过去 window_days 个交易日
                    wd = max(1, int(window_days))
                    start_idx = max(0, buy_idx - (wd - 1))
                    end_idx = buy_idx
                    window = df.iloc[start_idx:end_idx + 1]
                    if window is None or window.empty:
                        return '不满足条件'
                    # 计算区间上下界
                    if 'low' in window.columns and 'high' in window.columns and window['low'].notna().any() and window['high'].notna().any():
                        min_low = float(window['low'].min())
                        max_high = float(window['high'].max())
                    else:
                        # 退化为 close 的极值
                        min_low = float(window['close'].min())
                        max_high = float(window['close'].max())
                    price_range = max_high - min_low
                    if price_range <= 0:
                        return '不满足条件'
                    close_today = float(window.iloc[-1]['close'])
                    pos = (close_today - min_low) / price_range
                    return '满足条件' if pos <= 0.10 else '不满足条件'
                except Exception:
                    return '不满足条件'
            
            # 改为按持股时间排序：先按天数升序，1日中“开盘卖出”优先于“收盘卖出”
            def _holding_sort_key(d):
                try:
                    sd = int(d.get('sell_days', 99))
                except Exception:
                    sd = 99
                mode_order = 2
                if sd == 1:
                    base_label = d.get('max_percentage_metric', '').split('(')[0]
                    # "高开"表示开盘卖出优先，其次为收盘卖出（含“上涨”）
                    mode_order = 0 if ('高开' in base_label) else 1
                return (sd, mode_order)

            for detail in sorted(results['details'], key=_holding_sort_key):
                metrics_str = ', '.join(detail['metrics'])
                
                # 仅展示所选持股天数的记录
                if not _is_selected_detail(detail):
                    continue
                sell_days = int(detail['sell_days'])
                sell_time_info = "收盘卖出"
                
                # 构建卖出描述
                sell_desc = f"买入{detail['stock_code']}，{detail['sell_days']}日后"
                if sell_time_info:
                    sell_desc += f"{sell_time_info}"
                
                details_rows.append([
                    detail['stock_code'],
                    detail['date'],
                    str(detail.get('actual_calc_count', detail.get('correlation_count', 0))),
                    f"{detail['high_performance_count']}/{detail['valid_metrics_count']}",
                    detail['max_percentage_metric'],
                    detail['buy_date'],
                    f"{detail['sell_days']}日后",
                    sell_desc,
                    str(detail['buy_price']),
                    str(detail['sell_price']),
                    detail['change_percent'],
                    str(detail.get('max_up_percent', 'N/A')),
                    str(detail.get('max_down_percent', 'N/A'))
                ])
                
                # 统计涨跌情况（统计所选持股天数列表）
                sell_days = int(detail['sell_days'])  # 确保sell_days是整数
                if sell_days not in days_list:
                    continue
                days_key = f"{sell_days}_close"
                
                # 10日均线条件分组（过去 eval_days 个交易日，含当日）
                zone_key = _ma10_condition_for_date(detail['stock_code'], detail['date'], eval_days)
                price_zone_stats[zone_key]['total'] += 1

                # 涨跌
                if detail['change_percent'] != 'N/A':
                    change_value = float(detail['change_percent'].strip('%'))
                    if change_value > 0:
                        up_count += 1
                        days_stats[days_key]['up'] += 1
                        price_zone_stats[zone_key]['up'] += 1
                        if detail.get('actual_calc_count', detail.get('correlation_count', 0)) >= count_threshold:
                            high_corr_stats[days_key]['up'] += 1
                            high_corr_stats[days_key]['total'] += 1
                    elif change_value < 0:
                        down_count += 1
                        days_stats[days_key]['down'] += 1
                        price_zone_stats[zone_key]['down'] += 1
                        if detail.get('actual_calc_count', detail.get('correlation_count', 0)) >= count_threshold:
                            high_corr_stats[days_key]['down'] += 1
                            high_corr_stats[days_key]['total'] += 1
                    else:
                        flat_count += 1
                        days_stats[days_key]['flat'] += 1
                        price_zone_stats[zone_key]['flat'] += 1
                        if detail.get('actual_calc_count', detail.get('correlation_count', 0)) >= count_threshold:
                            high_corr_stats[days_key]['flat'] += 1
                            high_corr_stats[days_key]['total'] += 1
                    days_stats[days_key]['total'] += 1
                else:
                    # 无法计算数量
                    na_count += 1
                    days_stats[days_key]['na'] += 1
                    price_zone_stats[zone_key]['na'] += 1
                    if detail.get('actual_calc_count', detail.get('correlation_count', 0)) >= count_threshold:
                        high_corr_stats[days_key]['na'] += 1
            
            # 添加涨跌统计
            total_valid = up_count + down_count + flat_count
            f.write("\n----- 涨跌统计 -----\n")
            if total_valid > 0:
                f.write(f"上涨记录数: {up_count} ({up_count/total_valid*100:.2f}% 如果不计算N/A)\n")
                f.write(f"下跌记录数: {down_count} ({down_count/total_valid*100:.2f}% 如果不计算N/A)\n")
                f.write(f"持平记录数: {flat_count} ({flat_count/total_valid*100:.2f}% 如果不计算N/A)\n")
            else:
                f.write(f"上涨记录数: {up_count} (0.00%)\n")
                f.write(f"下跌记录数: {down_count} (0.00%)\n")
                f.write(f"持平记录数: {flat_count} (0.00%)\n")
            f.write(f"无法计算记录数: {na_count}\n")
            
            # 输出高性能记录详情表格，且在每条记录前打印原始CSV行
            details_original_lines = []
            # 保持与details_rows一致的顺序，收集对应的原始CSV记录
            # 原始CSV行也按持股时间的排序保持一致
            for detail in sorted(results['details'], key=_holding_sort_key):
                details_original_lines.append(','.join(detail.get('original_row', [])) if detail.get('original_row') else detail.get('original_csv_line', ''))
            f.write(_format_table_with_originals(details_headers, details_rows, details_original_lines, results.get('csv_file_path', ''), details_aligns))

            # 添加按持股天数的涨跌统计（所选持股天数）
            f.write(f"\n----- 按持股天数的涨跌统计（所选持股天数） -----\n")
            for d in days_list:
                days = f"{d}_close"
                stats = days_stats[days]
                days_label = f"{d}日持股(收盘卖出/下{d}日上涨)"
                total_valid_days = stats['up'] + stats['down'] + stats['flat']
                if total_valid_days > 0:
                    up_percent = stats['up'] / total_valid_days * 100
                    down_percent = stats['down'] / total_valid_days * 100
                    flat_percent = stats['flat'] / total_valid_days * 100
                    
                    f.write(f"\n{days_label}统计:\n")
                    f.write(f"  总记录数: {total_valid_days}\n")
                    f.write(f"  上涨记录数: {stats['up']} ({up_percent:.2f}%)\n")
                    f.write(f"  下跌记录数: {stats['down']} ({down_percent:.2f}%)\n")
                    f.write(f"  持平记录数: {stats['flat']} ({flat_percent:.2f}%)\n")
            
            # 添加实际计算数量大于等于阈值的统计
            f.write(f"\n----- 实际计算数量大于等于{count_threshold}的统计 -----\n")

            # 显示相关数量≥阈值的统计结果（所选持股天数）
            for d in days_list:
                days = f"{d}_close"
                stats = high_corr_stats[days]
                
                # 标签（收盘卖出）
                days_label = f"{d}日持股(收盘卖出/下{d}日上涨)"
                
                total_valid_days = stats['up'] + stats['down'] + stats['flat']
                
                if total_valid_days > 0:
                    up_percent = stats['up'] / total_valid_days * 100
                    down_percent = stats['down'] / total_valid_days * 100
                    flat_percent = stats['flat'] / total_valid_days * 100
                    
                    f.write(f"\n{days_label}统计(实际计算数量>={count_threshold}):\n")
                    f.write(f"  总记录数: {total_valid_days}\n")
                    f.write(f"  上涨记录数: {stats['up']} ({up_percent:.2f}%)\n")
                    f.write(f"  下跌记录数: {stats['down']} ({down_percent:.2f}%)\n")
                    f.write(f"  持平记录数: {stats['flat']} ({flat_percent:.2f}%)\n")
                    if stats['na'] > 0:
                        f.write(f"  无法计算记录数: {stats['na']}\n")

                    # 追加对应分类的明细列表（实际计算数量>=100），并对齐输出
                    f.write("  详细记录:\n")
                    sub_rows = []
                    sub_headers = details_headers
                    sub_aligns = details_aligns
                    for detail in sorted(results['details'], key=lambda x: x.get('actual_calc_count', x.get('correlation_count', 0)), reverse=True):
                        if detail.get('actual_calc_count', detail.get('correlation_count', 0)) < count_threshold:
                            continue
                        if not _is_selected_detail(detail):
                            continue
                        if int(detail.get('sell_days', 0)) != d:
                            continue
                        # 展示卖出方式文案（5日上涨为收盘卖出）
                        sell_time_info = "收盘卖出"
                        sell_desc = f"买入{detail['stock_code']}，{detail['sell_days']}日后"
                        if sell_time_info:
                            sell_desc += f"{sell_time_info}"
                        sub_rows.append([
                            detail['stock_code'],
                            detail['date'],
                            str(detail.get('actual_calc_count', detail.get('correlation_count', 0))),
                            f"{detail['high_performance_count']}/{detail.get('valid_metrics_count', detail.get('total_metrics', 0))}",
                            detail['max_percentage_metric'],
                            detail.get('buy_date', detail['date']),
                            f"{detail['sell_days']}日后",
                            sell_desc,
                            str(detail['buy_price']),
                            str(detail['sell_price']),
                            detail['change_percent'],
                            str(detail.get('max_up_percent', 'N/A')),
                            str(detail.get('max_down_percent', 'N/A'))
                        ])
                    # 在分类详细记录中，同样在每条表格行前打印原始CSV行
                    sub_original_lines = []
                    for detail in sorted(results['details'], key=lambda x: x.get('actual_calc_count', x.get('correlation_count', 0)), reverse=True):
                        if not _is_selected_detail(detail):
                            continue
                        if int(detail.get('sell_days', 0)) != d:
                            continue
                        if detail.get('actual_calc_count', detail.get('correlation_count', 0)) >= count_threshold:
                            sub_original_lines.append(','.join(detail.get('original_row', [])) if detail.get('original_row') else detail.get('original_csv_line', ''))
                    f.write(_format_table_with_originals(sub_headers, sub_rows, sub_original_lines, results.get('csv_file_path', ''), sub_aligns))

            # 输出按区间位置的条件分组统计（过去 eval_days 个交易日，所选持股天数）
            f.write(f"\n----- 按15日区间位置分组统计（过去{eval_days}个交易日） -----\n")
            for zone in ['满足条件', '不满足条件']:
                stats = price_zone_stats[zone]
                total_valid = stats['up'] + stats['down'] + stats['flat']
                # 在分组标题后写清具体条件（过去15日总区间位置）
                if zone == '满足条件':
                    cond_desc = (
                        f"过去{eval_days}个交易日总区间内，当日收盘位于底部0-10%"
                    )
                else:
                    cond_desc = (
                        f"过去{eval_days}个交易日总区间内，当日收盘高于底部10%"
                    )
                f.write(f"\n条件 {zone}：{cond_desc}\n")
                f.write(f"  总记录数: {stats['total']}\n")
                if total_valid > 0:
                    up_percent = stats['up'] / total_valid * 100
                    down_percent = stats['down'] / total_valid * 100
                    flat_percent = stats['flat'] / total_valid * 100
                    f.write(f"  上涨记录数: {stats['up']} ({up_percent:.2f}%)\n")
                    f.write(f"  下跌记录数: {stats['down']} ({down_percent:.2f}%)\n")
                    f.write(f"  持平记录数: {stats['flat']} ({flat_percent:.2f}%)\n")
                else:
                    f.write(f"  上涨记录数: {stats['up']} (0.00%)\n")
                    f.write(f"  下跌记录数: {stats['down']} (0.00%)\n")
                    f.write(f"  持平记录数: {stats['flat']} (0.00%)\n")
                if stats['na'] > 0:
                    f.write(f"  无法计算记录数: {stats['na']}\n")

                # 条件分组对应的详细记录清单（与详情表同样的格式，所选持股天数）
                f.write("  详细记录:\n")
                sub_rows = []
                sub_headers = details_headers
                sub_aligns = details_aligns
                sub_original_lines = []
                # 保持与主详情一致的排序（先按持股天数升序，1日高开优先）
                for detail in sorted(results['details'], key=_holding_sort_key):
                    if not _is_selected_detail(detail):
                        continue
                    # 计算该记录的条件分组
                    zone_key = _ma10_condition_for_date(detail['stock_code'], detail['date'], eval_days)
                    if zone_key != zone:
                        continue
                    # 卖出方式文案（5日上涨为收盘卖出）
                    try:
                        sell_days = int(detail['sell_days'])
                    except Exception:
                        sell_days = detail.get('sell_days', 0)
                    sell_time_info = "收盘卖出"
                    sell_desc = f"买入{detail['stock_code']}，{detail['sell_days']}日后"
                    if sell_time_info:
                        sell_desc += f"{sell_time_info}"
                    # 构建子表行
                    sub_rows.append([
                        detail['stock_code'],
                        detail['date'],
                        str(detail.get('actual_calc_count', detail.get('correlation_count', 0))),
                        f"{detail['high_performance_count']}/{detail.get('valid_metrics_count', detail.get('total_metrics', 0))}",
                        detail['max_percentage_metric'],
                        detail.get('buy_date', detail['date']),
                        f"{detail['sell_days']}日后",
                        sell_desc,
                        str(detail['buy_price']),
                        str(detail['sell_price']),
                        detail['change_percent'],
                        str(detail.get('max_up_percent', 'N/A')),
                        str(detail.get('max_down_percent', 'N/A'))
                    ])
                    # 原始CSV行
                    sub_original_lines.append(','.join(detail.get('original_row', [])) if detail.get('original_row') else detail.get('original_csv_line', ''))
                # 输出该价格区间的详细清单（含原始记录）
                if sub_rows:
                    f.write(_format_table_with_originals(sub_headers, sub_rows, sub_original_lines, results.get('csv_file_path', ''), sub_aligns))

            # 按年度的持股天数涨跌统计（所选持股天数）
            f.write(f"\n----- 按年度的持股天数涨跌统计（所选持股天数） -----\n")
            from collections import defaultdict as _dd
            import re
            year_days_stats = _dd(lambda: {
                f"{d}_close": {'up': 0, 'down': 0, 'flat': 0, 'na': 0, 'total': 0}
                for d in days_list
            })
            for detail in results['details']:
                # 解析年份
                year_val = None
                try:
                    year_val = pd.to_datetime(str(detail.get('date')), errors='coerce').year
                except Exception:
                    year_val = None
                if year_val is None:
                    m = re.search(r'(\d{4})', str(detail.get('date')))
                    year_val = int(m.group(1)) if m else '未知'
                # 分类键
                sell_days = int(detail['sell_days'])
                if sell_days not in days_list:
                    continue
                days_key = f"{sell_days}_close"
                # 统计涨跌
                if detail['change_percent'] != 'N/A':
                    change_value = float(str(detail['change_percent']).strip('%'))
                    if change_value > 0:
                        year_days_stats[year_val][days_key]['up'] += 1
                    elif change_value < 0:
                        year_days_stats[year_val][days_key]['down'] += 1
                    else:
                        year_days_stats[year_val][days_key]['flat'] += 1
                    year_days_stats[year_val][days_key]['total'] += 1
                else:
                    year_days_stats[year_val][days_key]['na'] += 1
            # 输出每年度统计
            def _year_sort_key(y):
                return (9999 if isinstance(y, str) else int(y))
            for year in sorted(year_days_stats.keys(), key=_year_sort_key):
                f.write(f"\n[年度: {year}]\n")
                # 年度持股天数统计（收盘卖出）
                for d in days_list:
                    days = f"{d}_close"
                    stats = year_days_stats[year][days]
                    days_label = f"{d}日持股(收盘卖出/下{d}日上涨)"
                    total_valid_days = stats['up'] + stats['down'] + stats['flat']
                    f.write(f"{days_label}统计:\n")
                    f.write(f"  总记录数: {total_valid_days}\n")
                    if total_valid_days > 0:
                        up_percent = stats['up'] / total_valid_days * 100
                        down_percent = stats['down'] / total_valid_days * 100
                        flat_percent = stats['flat'] / total_valid_days * 100
                        f.write(f"  上涨记录数: {stats['up']} ({up_percent:.2f}%)\n")
                        f.write(f"  下跌记录数: {stats['down']} ({down_percent:.2f}%)\n")
                        f.write(f"  持平记录数: {stats['flat']} ({flat_percent:.2f}%)\n")
                    else:
                        f.write(f"  上涨记录数: {stats['up']} (0.00%)\n")
                        f.write(f"  下跌记录数: {stats['down']} (0.00%)\n")
                        f.write(f"  持平记录数: {stats['flat']} (0.00%)\n")

            # 按年度且实际计算数量≥阈值的持股天数统计（所选持股天数）
            f.write(f"\n----- 按年度且实际计算数量>={count_threshold}的持股天数统计（所选持股天数） -----\n")
            year_high_corr_stats = _dd(lambda: {
                f"{d}_close": {'up': 0, 'down': 0, 'flat': 0, 'na': 0, 'total': 0}
                for d in days_list
            })
            for detail in results['details']:
                # 过滤阈值
                if detail.get('actual_calc_count', detail.get('correlation_count', 0)) < count_threshold:
                    continue
                # 解析年份
                year_val = None
                try:
                    year_val = pd.to_datetime(str(detail.get('date')), errors='coerce').year
                except Exception:
                    year_val = None
                if year_val is None:
                    m = re.search(r'(\d{4})', str(detail.get('date')))
                    year_val = int(m.group(1)) if m else '未知'
                # 分类键
                sell_days = int(detail['sell_days'])
                if sell_days not in days_list:
                    continue
                days_key = f"{sell_days}_close"
                # 统计涨跌
                if detail['change_percent'] != 'N/A':
                    change_value = float(str(detail['change_percent']).strip('%'))
                    if change_value > 0:
                        year_high_corr_stats[year_val][days_key]['up'] += 1
                    elif change_value < 0:
                        year_high_corr_stats[year_val][days_key]['down'] += 1
                    else:
                        year_high_corr_stats[year_val][days_key]['flat'] += 1
                    year_high_corr_stats[year_val][days_key]['total'] += 1
                else:
                    year_high_corr_stats[year_val][days_key]['na'] += 1
            # 输出每年度高相关统计（仅selected_day日上涨）
            for year in sorted(year_high_corr_stats.keys(), key=_year_sort_key):
                f.write(f"\n[年度: {year}]\n")
                for d in days_list:
                    days = f"{d}_close"
                    stats = year_high_corr_stats[year][days]
                    days_label = f"{d}日持股(收盘卖出/下{d}日上涨)"
                    total_valid_days = stats['up'] + stats['down'] + stats['flat']
                    f.write(f"{days_label}统计(实际计算数量>={count_threshold}):\n")
                    f.write(f"  总记录数: {total_valid_days}\n")
                    if total_valid_days > 0:
                        up_percent = stats['up'] / total_valid_days * 100
                        down_percent = stats['down'] / total_valid_days * 100
                        flat_percent = stats['flat'] / total_valid_days * 100
                        f.write(f"  上涨记录数: {stats['up']} ({up_percent:.2f}%)\n")
                        f.write(f"  下跌记录数: {stats['down']} ({down_percent:.2f}%)\n")
                        f.write(f"  持平记录数: {stats['flat']} ({flat_percent:.2f}%)\n")
                    else:
                        f.write(f"  上涨记录数: {stats['up']} (0.00%)\n")
                        f.write(f"  下跌记录数: {stats['down']} (0.00%)\n")
                        f.write(f"  持平记录数: {stats['flat']} (0.00%)\n")

            # 按年度统计总结
            f.write("\n----- 按年度统计 -----\n")
            from collections import defaultdict as _dd
            import re
            year_stats = _dd(lambda: {'filtered': 0, 'high_performance': 0})
            for date, stats in results['date_stats'].items():
                # 尝试解析年份
                year_val = None
                try:
                    year_val = pd.to_datetime(str(date), errors='coerce').year
                except Exception:
                    year_val = None
                if year_val is None:
                    m = re.search(r'(\d{4})', str(date))
                    year_val = int(m.group(1)) if m else '未知'
                year_stats[year_val]['filtered'] += stats.get('filtered', 0)
                year_stats[year_val]['high_performance'] += stats.get('high_performance', 0)
            # 输出年度统计，按年份排序（未知放在最后）
            def _year_sort_key(y):
                return (9999 if isinstance(y, str) else int(y))
            f.write("年份\t符合条件记录数\t高性能记录数\t高性能占比\n")
            for year in sorted(year_stats.keys(), key=_year_sort_key):
                fil = year_stats[year]['filtered']
                hp = year_stats[year]['high_performance']
                ratio = (hp / fil * 100) if fil > 0 else 0.0
                f.write(f"{year}\t{fil}\t{hp}\t{ratio:.2f}%\n")
        
        logging.info(f"结果已保存到文件: {output_file}")
        return True
    except Exception as e:
        # 记录详细异常信息（包含类型与堆栈）
        logging.exception(f"保存结果到文件时出错: {repr(e)}")
        return False

def analyze_csv(csv_file_path, min_correlation_count=10, high_percentage=80.0, selected_day=5, selected_days=None):
    """
    分析CSV文件中相关数量超过指定阈值的数据，统计5个统计值中超过指定百分比的数量
    
    Args:
        csv_file_path: CSV文件路径
        min_correlation_count: 最小相关数量阈值，默认为10
        high_percentage: 高百分比阈值，默认为80.0
    
    Returns:
        统计结果
    """
    if not os.path.exists(csv_file_path):
        logging.error(f"错误: 文件 {csv_file_path} 不存在")
        return None
    
    results = {
        'total_records': 0,
        'filtered_records': 0,
        'high_performance_records': 0,
        'stock_stats': defaultdict(lambda: {'total': 0, 'filtered': 0, 'high_performance': 0}),
        'date_stats': defaultdict(lambda: {'total': 0, 'filtered': 0, 'high_performance': 0}),
        'details': [],
        'csv_file_path': csv_file_path
    }
    
    try:
        # 尝试不同的编码方式
        encodings = ['utf-8', 'gbk', 'gb2312', 'utf-8-sig']
        for encoding in encodings:
            try:
                logging.info(f"尝试使用 {encoding} 编码读取文件")
                with open(csv_file_path, 'r', encoding=encoding) as f:
                    # 读取第一行来获取列名
                    header = f.readline().strip().split(',')
                    f.seek(0)  # 回到文件开头
                    reader = csv.reader(f)
                    next(reader)  # 跳过标题行
                    
                    # 列名映射
                    code_index = header.index('代码')
                    date_index = header.index('评测日期')
                    actual_count_index = header.index('实际计算数量')
                    comp_count_index = header.index('对比股票数量')
                    # 动态识别指标列：仅纳入“下N日上涨”指标（N来自 selected_days 列表或 selected_day）
                    metric_labels = []
                    days_list = []
                    if isinstance(selected_days, (list, tuple)) and len(selected_days) > 0:
                        days_list = [int(x) for x in selected_days]
                    else:
                        days_list = [int(selected_day)]
                    for col in header:
                        if col.startswith('下') and ('上涨' in col):
                            # 兼容“下一日”与“下1日”的写法；匹配所选持股天数
                            col_norm = col.replace('下一日', '下1日')
                            m = re.search(r'下(\d+)日', col_norm)
                            if m:
                                try:
                                    d = int(m.group(1))
                                    if d in days_list:
                                        metric_labels.append(col)
                                except Exception:
                                    pass
                    metrics_indices = [header.index(lbl) for lbl in metric_labels]
                    
                    logging.info(f"开始分析CSV文件: {csv_file_path}")
                    for row in reader:
                        results['total_records'] += 1
                        
                        # 获取股票代码和日期
                        stock_code = row[code_index]
                        eval_date = row[date_index]
                        
                        # 实际计算数量与对比股票数量
                        actual_calc_count = int(row[actual_count_index]) if row[actual_count_index] != 'N/A' else 0
                        comparison_stock_count = int(row[comp_count_index]) if row[comp_count_index] != 'N/A' else 0
                        
                        # 使用实际计算数量进行阈值过滤：保留 >= 阈值
                        if actual_calc_count < min_correlation_count:
                            continue
                        
                        results['filtered_records'] += 1
                        results['stock_stats'][stock_code]['total'] += 1
                        results['stock_stats'][stock_code]['filtered'] += 1
                        results['date_stats'][eval_date]['total'] += 1
                        results['date_stats'][eval_date]['filtered'] += 1
                        
                        # 统计全部指标值
                        performance_metrics = [row[i] for i in metrics_indices]
                        
                        # 计算超过高百分比的指标数量
                        high_performance_count = 0
                        valid_metrics_count = 0

                        for metric in performance_metrics:
                            if metric not in ('', 'N/A'):
                                valid_metrics_count += 1
                                # 去掉百分号并转换为浮点数
                                try:
                                    value = float(metric.strip('%'))
                                except Exception:
                                    value = 0.0
                                if value >= high_percentage:
                                    high_performance_count += 1
                        
                        # 如果有任何一个指标超过高百分比，记录下来
                        if high_performance_count > 0:
                            results['high_performance_records'] += 1
                            results['stock_stats'][stock_code]['high_performance'] += 1
                            results['date_stats'][eval_date]['high_performance'] += 1
                            
                            # 记录详细信息
                            # 找出百分比最大的指标及其对应的天数（平手时选择更长持股期）
                            max_percentage = -1.0
                            max_percentage_index = 0
                            max_percentage_day = 0
                            for i, metric in enumerate(performance_metrics):
                                if metric not in ('', 'N/A'):
                                    try:
                                        value = float(metric.strip('%'))
                                    except Exception:
                                        value = 0.0
                                    # 解析该指标对应的持股天数
                                    base_label = metric_labels[i].replace('下一日', '下1日')
                                    mm = re.search(r'下(\d+)日', base_label)
                                    dday = int(mm.group(1)) if mm else 0
                                    if (value > max_percentage) or (value == max_percentage and dday > max_percentage_day):
                                        max_percentage = value
                                        max_percentage_index = i
                                        max_percentage_day = dday

                            # 计算买入时间和卖出时间
                            buy_date = eval_date
                            # 设置持股天数为所选最佳指标对应天数
                            sell_days_offset = max_percentage_day if max_percentage_day > 0 else selected_day
                            
                            # 获取价格数据
                            # 解析 1 日持股的卖出方式并传入价格计算
                            sell_mode = None
                            if sell_days_offset == 1:
                                base_label = metric_labels[max_percentage_index]
                                if '高开' in base_label:
                                    sell_mode = 'open'
                                elif '上涨' in base_label:
                                    sell_mode = 'close'
                            price_data = get_stock_price_data(stock_code, buy_date, sell_days_offset, sell_mode=sell_mode)
                            
                            results['details'].append({
                                'stock_code': stock_code,
                                'date': eval_date,
                                'actual_calc_count': actual_calc_count,
                                'metrics': [f"{metric_labels[i]}({performance_metrics[i]})" for i in range(len(performance_metrics))],
                                'high_performance_count': high_performance_count,
                                'valid_metrics_count': valid_metrics_count,
                                'buy_date': buy_date,
                                'sell_days': sell_days_offset,
                                'max_percentage': max_percentage,
                                'max_percentage_metric': f"{metric_labels[max_percentage_index]}({max_percentage}%)",
                                'buy_price': price_data['buy_price'],
                                'sell_price': price_data['sell_price'],
                                'change_percent': price_data['change_percent'],
                                'max_up_percent': price_data.get('max_up_percent', 'N/A'),
                                'max_down_percent': price_data.get('max_down_percent', 'N/A'),
                                'original_row': row,
                                'original_csv_line': ','.join(row)
                            })
                    
                    logging.info(f"CSV文件分析完成，共处理 {results['total_records']} 条记录")
                    # 如果成功读取，跳出循环
                    break
            except Exception as e:
                if encoding == encodings[-1]:  # 如果是最后一种编码方式
                    raise e
                logging.warning(f"使用 {encoding} 编码读取失败: {e}，尝试下一种编码")
                continue
        
        return results
    
    except Exception as e:
        logging.error(f"处理CSV文件时出错: {e}")
        return None

def print_results(results):
    """打印分析结果"""
    if not results:
        return
    
    logging.info("\n===== 分析结果 =====")
    logging.info(f"总记录数: {results['total_records']}")
    logging.info(f"实际计算数量超过阈值的记录数: {results['filtered_records']}")
    logging.info(f"有高性能指标的记录数: {results['high_performance_records']}")
    if results['filtered_records'] > 0:
        ratio = results['high_performance_records'] / results['filtered_records'] * 100
        logging.info(f"高性能记录占比: {ratio:.2f}% (在实际计算数量超过阈值的记录中)")
    else:
        logging.info("高性能记录占比: N/A (在实际计算数量超过阈值的记录中)")
    
    logging.info("\n----- 按股票代码统计 (前10条) -----")
    # 按高性能记录数量排序
    sorted_stocks = sorted(
        results['stock_stats'].items(), 
        key=lambda x: x[1]['high_performance'], 
        reverse=True
    )
    
    logging.info("股票代码\t符合条件记录数\t高性能记录数\t高性能占比")
    for stock_code, stats in sorted_stocks[:10]:  # 只显示前10个
        if stats['filtered'] > 0:
            ratio = stats['high_performance'] / stats['filtered'] * 100
            logging.info(f"{stock_code}\t{stats['filtered']}\t{stats['high_performance']}\t{ratio:.2f}%")
    
    logging.info("\n----- 按日期统计 (前10条) -----")
    # 按日期排序
    sorted_dates = sorted(results['date_stats'].items())
    
    logging.info("日期\t\t符合条件记录数\t高性能记录数\t高性能占比")
    for date, stats in sorted_dates[:10]:  # 只显示前10个
        if stats['filtered'] > 0:
            ratio = stats['high_performance'] / stats['filtered'] * 100
            logging.info(f"{date}\t{stats['filtered']}\t{stats['high_performance']}\t{ratio:.2f}%")

    # 按年度统计（完整列表）
    logging.info("\n----- 按年度统计 -----")
    from collections import defaultdict as _dd
    import re
    year_stats = _dd(lambda: {'filtered': 0, 'high_performance': 0})
    for date, stats in results['date_stats'].items():
        year_val = None
        try:
            year_val = pd.to_datetime(str(date), errors='coerce').year
        except Exception:
            year_val = None
        if year_val is None:
            m = re.search(r'(\d{4})', str(date))
            year_val = int(m.group(1)) if m else '未知'
        year_stats[year_val]['filtered'] += stats.get('filtered', 0)
        year_stats[year_val]['high_performance'] += stats.get('high_performance', 0)
    def _year_sort_key(y):
        return (9999 if isinstance(y, str) else int(y))
    logging.info("年份\t符合条件记录数\t高性能记录数\t高性能占比")
    for year in sorted(year_stats.keys(), key=_year_sort_key):
        fil = year_stats[year]['filtered']
        hp = year_stats[year]['high_performance']
        ratio = (hp / fil * 100) if fil > 0 else 0.0
        logging.info(f"{year}\t{fil}\t{hp}\t{ratio:.2f}%")
    
    logging.info("\n----- 高性能记录详情 (前10条) -----")
    logging.info("股票代码\t日期\t\t实际计算数量\t高性能指标数/总指标数\t最佳指标\t买入日期\t卖出天数\t交易建议\t买入价\t卖出价\t涨跌幅\t最大涨幅\t最大跌幅")
    for detail in sorted(results['details'], key=lambda x: x.get('actual_calc_count', x.get('correlation_count', 0)), reverse=True)[:10]:
        logging.info(f"{detail['stock_code']}\t{detail['date']}\t{detail.get('actual_calc_count', detail.get('correlation_count', 0))}\t{detail['high_performance_count']}/{detail.get('valid_metrics_count', detail.get('total_metrics', 0))}\t{detail['max_percentage_metric']}\t{detail.get('buy_date', detail['date'])}\t{detail['sell_days']}日后\t买入{detail['stock_code']}，{detail['sell_days']}日后卖出\t{detail['buy_price']}\t{detail['sell_price']}\t{detail['change_percent']}\t{detail.get('max_up_percent', 'N/A')}\t{detail.get('max_down_percent', 'N/A')}")

def main():
    parser = argparse.ArgumentParser(description='分析股票相关性CSV文件')
    parser.add_argument('--file', type=str, 
                        default='c:\\Users\\17701\\github\\my_first_repo\\stockapi\\stock_backtest\\pearson_found\\evaluation_results.csv',
                        help='CSV文件路径')
    parser.add_argument('--min-count', type=int, default=30,
                        help='最小相关数量阈值 (默认: 30')
    parser.add_argument('--high-percentage', type=float, default=70.0,
                        help='高百分比阈值 (默认: 65.0)')
    parser.add_argument('--detail-threshold', type=int, default=95,
                        help='“实际计算数量≥N统计”使用的独立阈值 (默认: 95)')
    parser.add_argument('--output', type=str, default='',
                        help='结果输出文件路径 (默认: results_YYYYMMDD_HHMMSS.txt)')
    parser.add_argument('--eval-days', type=int, default=15,
                        help='评测日期数：包括当日，往前数N个交易日 (默认: 15)')
    parser.add_argument('--days', type=str, default='5',
                        help='持股天数：传单个或逗号分隔列表。例如 5 或 3,5,8（范围: 2-10）')
    
    args = parser.parse_args()
    
    # 时间戳
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

    # 创建logs目录并初始化标准日志（包含文件名与代码行号）
    script_dir = os.path.dirname(os.path.abspath(__file__))
    logs_dir = os.path.join(script_dir, 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    logger, log_file = setup_logging(log_dir=logs_dir)
    logger.info("分析开始")
    
    # 如果未指定输出文件，生成默认文件名
    if not args.output:
        args.output = os.path.join(os.path.dirname(args.file), f'results_{timestamp}.txt')
    
    logger.info(f"日志文件: {log_file}")
    logger.info(f"分析文件: {args.file}")
    logger.info(f"最小相关数量阈值: {args.min_count}")
    logger.info(f"高百分比阈值: {args.high_percentage}%")
    logger.info(f"明细统计阈值: {args.detail_threshold}")
    logger.info(f"结果输出文件: {args.output}")
    logger.info(f"评测日期数: {args.eval_days} (含当日)")
    # 解析 --days 参数，支持逗号与中文逗号
    raw_days = (args.days or '').strip()
    tokens = [t.strip() for t in raw_days.replace('，', ',').split(',') if t.strip()]
    try:
        parsed_days = [int(t) for t in tokens] if tokens else [5]
    except Exception:
        logger.error(f"持股天数解析失败: {args.days}，请传如 5 或 3,5,8")
        return
    # 校验范围 2-10
    invalid = [d for d in parsed_days if d < 2 or d > 10]
    if invalid:
        logger.error(f"持股天数超出范围(2-10): {invalid}")
        return
    # 去重并排序，避免重复
    selected_days_list = sorted(set(parsed_days))
    if len(selected_days_list) > 1:
        logger.info(f"持股天数选择: 下{','.join(str(d) for d in selected_days_list)}日上涨（同时分析）")
    else:
        logger.info(f"持股天数选择: 仅下{selected_days_list[0]}日上涨")
    
    results = analyze_csv(
        args.file,
        args.min_count,
        args.high_percentage,
        selected_day=selected_days_list[0],
        selected_days=selected_days_list
    )
    if results:
        print_results(results)
        ok = save_results_to_file(
            results,
            args.output,
            count_threshold=args.detail_threshold,
            eval_days=args.eval_days,
            selected_day=selected_days_list[0],
            selected_days=selected_days_list
        )
        if ok:
            logger.info(f"分析完成，结果已保存到: {args.output}")
        else:
            logger.error(f"分析完成，但保存结果到文件失败: {args.output}")
    else:
        logger.error("错误: 分析失败，请检查文件路径和格式是否正确。")

if __name__ == "__main__":
    main()