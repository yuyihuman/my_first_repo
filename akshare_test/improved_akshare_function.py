#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进版本的akshare股东持股明细查询函数
解决原始函数中的TypeError和其他潜在问题
"""

import requests
import pandas as pd
import json
import time
from typing import Optional, Dict, Any
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StockHoldingDataFetcher:
    """
    股东持股数据获取器 - 改进版本
    """
    
    def __init__(self):
        self.base_url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
        self.valid_indicators = ["社保", "基金", "券商", "信托", "QFII"]
        self.valid_symbols = ["新进", "增加", "不变", "减少"]
        self.session = requests.Session()
        
        # 设置请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://data.eastmoney.com/',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        })
    
    def validate_parameters(self, date: str, indicator: str, symbol: str) -> bool:
        """
        验证输入参数
        
        Args:
            date: 日期字符串 (YYYYMMDD)
            indicator: 机构类型
            symbol: 变化类型
            
        Returns:
            参数是否有效
        """
        # 验证日期格式
        try:
            datetime.strptime(date, '%Y%m%d')
        except ValueError:
            logger.error(f"日期格式错误: {date}，应为YYYYMMDD格式")
            return False
        
        # 验证机构类型
        if indicator not in self.valid_indicators:
            logger.error(f"无效的机构类型: {indicator}，有效值: {self.valid_indicators}")
            return False
        
        # 验证变化类型
        if symbol not in self.valid_symbols:
            logger.error(f"无效的变化类型: {symbol}，有效值: {self.valid_symbols}")
            return False
        
        return True
    
    def build_request_params(self, date: str, indicator: str, symbol: str, page: int = 1) -> Dict[str, str]:
        """
        构建请求参数
        
        Args:
            date: 日期
            indicator: 机构类型
            symbol: 变化类型
            page: 页码
            
        Returns:
            请求参数字典
        """
        formatted_date = '-'.join([date[:4], date[4:6], date[6:]])
        
        return {
            "sortColumns": "NOTICE_DATE,SECURITY_CODE,RANK",
            "sortTypes": "-1,1,1",
            "pageSize": "500",
            "pageNumber": str(page),
            "reportName": "RPT_DMSK_HOLDERS",
            "columns": "ALL",
            "source": "WEB",
            "client": "WEB",
            "filter": f'(HOLDER_NEWTYPE="{indicator}")(HOLDNUM_CHANGE_NAME="{symbol}")(END_DATE="{formatted_date}")',
        }
    
    def make_request_with_retry(self, params: Dict[str, str], max_retries: int = 3, delay: float = 1.0) -> Optional[Dict[str, Any]]:
        """
        带重试机制的请求
        
        Args:
            params: 请求参数
            max_retries: 最大重试次数
            delay: 重试延迟（秒）
            
        Returns:
            响应JSON数据或None
        """
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"发送请求 (尝试 {attempt + 1}/{max_retries + 1})")
                
                response = self.session.get(
                    self.base_url, 
                    params=params, 
                    timeout=30
                )
                
                logger.info(f"HTTP状态码: {response.status_code}")
                
                if response.status_code != 200:
                    logger.warning(f"HTTP请求失败，状态码: {response.status_code}")
                    if attempt < max_retries:
                        time.sleep(delay * (attempt + 1))  # 递增延迟
                        continue
                    return None
                
                # 解析JSON
                try:
                    data = response.json()
                    logger.info(f"JSON解析成功")
                    
                    # 检查API响应状态
                    if not data.get('success', False):
                        error_msg = data.get('message', '未知错误')
                        error_code = data.get('code', 'N/A')
                        logger.warning(f"API返回错误: {error_msg} (代码: {error_code})")
                        
                        # 如果是服务器繁忙，可以重试
                        if error_code == 9701 and attempt < max_retries:
                            logger.info(f"服务器繁忙，{delay * (attempt + 1)}秒后重试...")
                            time.sleep(delay * (attempt + 1))
                            continue
                        
                        return data  # 返回错误响应，让调用者处理
                    
                    return data
                    
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析失败: {e}")
                    logger.error(f"响应内容: {response.text[:500]}")
                    if attempt < max_retries:
                        time.sleep(delay * (attempt + 1))
                        continue
                    return None
                
            except requests.exceptions.RequestException as e:
                logger.error(f"网络请求异常: {e}")
                if attempt < max_retries:
                    time.sleep(delay * (attempt + 1))
                    continue
                return None
        
        logger.error(f"所有重试都失败了")
        return None
    
    def fetch_holding_detail(self, date: str, indicator: str, symbol: str) -> pd.DataFrame:
        """
        获取股东持股明细数据 - 改进版本
        
        Args:
            date: 查询日期 (YYYYMMDD)
            indicator: 机构类型
            symbol: 变化类型
            
        Returns:
            包含持股明细的DataFrame
        """
        logger.info(f"开始获取持股明细: 日期={date}, 机构={indicator}, 变化={symbol}")
        
        # 参数验证
        if not self.validate_parameters(date, indicator, symbol):
            return pd.DataFrame()
        
        # 构建请求参数
        params = self.build_request_params(date, indicator, symbol)
        
        # 发送第一次请求获取总页数
        data_json = self.make_request_with_retry(params)
        
        if not data_json:
            logger.error("无法获取数据")
            return pd.DataFrame()
        
        # 检查响应格式
        if not data_json.get('success', False):
            error_msg = data_json.get('message', '未知错误')
            logger.error(f"API返回错误: {error_msg}")
            return pd.DataFrame()
        
        result = data_json.get('result')
        if not result:
            logger.warning("响应中没有result字段或result为空")
            return pd.DataFrame()
        
        # 安全获取总页数
        total_pages = result.get('pages', 0)
        if total_pages == 0:
            logger.warning("没有数据页面")
            return pd.DataFrame()
        
        logger.info(f"总页数: {total_pages}")
        
        # 获取第一页数据
        first_page_data = result.get('data', [])
        if not first_page_data:
            logger.warning("第一页没有数据")
            return pd.DataFrame()
        
        all_data = first_page_data.copy()
        logger.info(f"第1页获取到 {len(first_page_data)} 条数据")
        
        # 获取剩余页面数据
        for page in range(2, total_pages + 1):
            logger.info(f"获取第 {page}/{total_pages} 页数据")
            
            page_params = self.build_request_params(date, indicator, symbol, page)
            page_data_json = self.make_request_with_retry(page_params)
            
            if not page_data_json or not page_data_json.get('success', False):
                logger.warning(f"第{page}页数据获取失败")
                continue
            
            page_result = page_data_json.get('result', {})
            page_data = page_result.get('data', [])
            
            if page_data:
                all_data.extend(page_data)
                logger.info(f"第{page}页获取到 {len(page_data)} 条数据")
            
            # 避免请求过于频繁
            time.sleep(0.5)
        
        # 转换为DataFrame
        if not all_data:
            logger.warning("没有获取到任何数据")
            return pd.DataFrame()
        
        df = pd.DataFrame(all_data)
        logger.info(f"总共获取到 {len(df)} 条数据")
        logger.info(f"数据列: {list(df.columns)}")
        
        return df


def stock_gdfx_holding_detail_em_improved(date: str, indicator: str, symbol: str) -> pd.DataFrame:
    """
    改进版本的股东持股明细查询函数
    
    Args:
        date: 查询日期，格式为 YYYYMMDD
        indicator: 机构类型，可选值: "社保", "基金", "券商", "信托", "QFII"
        symbol: 变化类型，可选值: "新进", "增加", "不变", "减少"
    
    Returns:
        包含持股明细的DataFrame
    
    Example:
        >>> df = stock_gdfx_holding_detail_em_improved("20231231", "社保", "新进")
        >>> print(df.head())
    """
    fetcher = StockHoldingDataFetcher()
    return fetcher.fetch_holding_detail(date, indicator, symbol)


def test_improved_function():
    """
    测试改进版本的函数
    """
    print("=== 测试改进版本的函数 ===")
    
    test_cases = [
        # 有效的测试用例
        {"date": "20231231", "indicator": "社保", "symbol": "新进"},
        {"date": "20231231", "indicator": "基金", "symbol": "增加"},
        
        # 原来出错的测试用例
        {"date": "20250331", "indicator": "个人", "symbol": "新进"},  # 应该会被参数验证拦截
        
        # 其他测试用例
        {"date": "20231231", "indicator": "QFII", "symbol": "不变"},
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n--- 测试用例 {i}: {case} ---")
        try:
            result = stock_gdfx_holding_detail_em_improved(**case)
            print(f"成功: 返回 {len(result)} 行数据")
            if not result.empty:
                print(f"列名: {list(result.columns)}")
                print(f"前3行数据:")
                print(result.head(3).to_string())
        except Exception as e:
            print(f"失败: {type(e).__name__}: {e}")
            import traceback
            print(f"详细错误: {traceback.format_exc()}")


if __name__ == "__main__":
    test_improved_function()