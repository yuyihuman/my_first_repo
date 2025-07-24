import pandas as pd
import os
import json
import pandas as pd
from datetime import datetime, timedelta
import logging
import time
import math
from .cache_utils import CACHE_DIR, read_cache, save_cache, is_cache_expired

# 配置日志
logger = logging.getLogger(__name__)

class InstitutionalHoldingsData:
    def __init__(self):
        # 数据目录 - 使用真实数据文件路径
        self.data_dir = r'C:\Users\17701\github\my_first_repo\stock_holding\institutional_holdings_data\processed_data'
        logger.info(f"机构持股数据目录: {self.data_dir}")
        
        # 缓存配置
        self.cache_dir = os.path.join(CACHE_DIR, 'institutional_holdings')
        os.makedirs(self.cache_dir, exist_ok=True)
        self.cache_file = os.path.join(self.cache_dir, 'holdings_data.json')
        self.trend_cache_dir = os.path.join(self.cache_dir, 'trends')
        os.makedirs(self.trend_cache_dir, exist_ok=True)
        
        # 内存缓存
        self._memory_cache = {}
        self._last_update = None
        self._cache_duration = 3600  # 1小时缓存
    
    def _get_data_files(self):
        """获取数据文件列表"""
        # 使用单个合并的数据文件
        merged_file = os.path.join(self.data_dir, 'merged_holdings_data.csv')
        if os.path.exists(merged_file):
            logger.info(f"找到合并数据文件: {merged_file}")
            return [merged_file]
        else:
            logger.warning(f"合并数据文件不存在: {merged_file}")
            return []
    
    def _load_sample_data(self):
        """加载示例数据（当实际数据不可用时）"""
        sample_data = {
            'all': [
                {'stock_code': '000001', 'stock_name': '平安银行', 'holding_ratio': 15.23},
                {'stock_code': '000002', 'stock_name': '万科A', 'holding_ratio': 12.45},
                {'stock_code': '000858', 'stock_name': '五粮液', 'holding_ratio': 11.67},
                {'stock_code': '000876', 'stock_name': '新希望', 'holding_ratio': 10.89},
                {'stock_code': '002415', 'stock_name': '海康威视', 'holding_ratio': 9.34},
                {'stock_code': '002594', 'stock_name': 'BYD', 'holding_ratio': 8.76},
                {'stock_code': '600036', 'stock_name': '招商银行', 'holding_ratio': 8.12},
                {'stock_code': '600519', 'stock_name': '贵州茅台', 'holding_ratio': 7.89},
                {'stock_code': '600887', 'stock_name': '伊利股份', 'holding_ratio': 7.23},
                {'stock_code': '000858', 'stock_name': '五粮液', 'holding_ratio': 6.45}
            ],
            'fund': [
                {'stock_code': '000001', 'stock_name': '平安银行', 'holding_ratio': 8.23},
                {'stock_code': '600519', 'stock_name': '贵州茅台', 'holding_ratio': 7.89},
                {'stock_code': '000858', 'stock_name': '五粮液', 'holding_ratio': 6.67},
                {'stock_code': '600036', 'stock_name': '招商银行', 'holding_ratio': 6.12},
                {'stock_code': '002415', 'stock_name': '海康威视', 'holding_ratio': 5.34},
                {'stock_code': '600887', 'stock_name': '伊利股份', 'holding_ratio': 5.23},
                {'stock_code': '000002', 'stock_name': '万科A', 'holding_ratio': 4.45},
                {'stock_code': '002594', 'stock_name': 'BYD', 'holding_ratio': 4.76},
                {'stock_code': '000876', 'stock_name': '新希望', 'holding_ratio': 3.89},
                {'stock_code': '600276', 'stock_name': '恒瑞医药', 'holding_ratio': 3.45}
            ],
            'insurance': [
                {'stock_code': '000001', 'stock_name': '平安银行', 'holding_ratio': 4.23},
                {'stock_code': '600036', 'stock_name': '招商银行', 'holding_ratio': 3.89},
                {'stock_code': '000002', 'stock_name': '万科A', 'holding_ratio': 3.67},
                {'stock_code': '600519', 'stock_name': '贵州茅台', 'holding_ratio': 3.12},
                {'stock_code': '000858', 'stock_name': '五粮液', 'holding_ratio': 2.34},
                {'stock_code': '600887', 'stock_name': '伊利股份', 'holding_ratio': 2.23},
                {'stock_code': '002415', 'stock_name': '海康威视', 'holding_ratio': 1.45},
                {'stock_code': '002594', 'stock_name': 'BYD', 'holding_ratio': 1.76},
                {'stock_code': '000876', 'stock_name': '新希望', 'holding_ratio': 1.89},
                {'stock_code': '600276', 'stock_name': '恒瑞医药', 'holding_ratio': 1.45}
            ],
            'qfii': [
                {'stock_code': '000858', 'stock_name': '五粮液', 'holding_ratio': 2.23},
                {'stock_code': '600519', 'stock_name': '贵州茅台', 'holding_ratio': 1.89},
                {'stock_code': '002415', 'stock_name': '海康威视', 'holding_ratio': 1.67},
                {'stock_code': '000001', 'stock_name': '平安银行', 'holding_ratio': 1.12},
                {'stock_code': '600036', 'stock_name': '招商银行', 'holding_ratio': 0.89},
                {'stock_code': '600887', 'stock_name': '伊利股份', 'holding_ratio': 0.76},
                {'stock_code': '000002', 'stock_name': '万科A', 'holding_ratio': 0.45},
                {'stock_code': '002594', 'stock_name': 'BYD', 'holding_ratio': 0.34},
                {'stock_code': '000876', 'stock_name': '新希望', 'holding_ratio': 0.23},
                {'stock_code': '600276', 'stock_name': '恒瑞医药', 'holding_ratio': 0.12}
            ],
            'social-security': [
                {'stock_code': '000001', 'stock_name': '平安银行', 'holding_ratio': 2.89},
                {'stock_code': '600036', 'stock_name': '招商银行', 'holding_ratio': 2.12},
                {'stock_code': '000858', 'stock_name': '五粮液', 'holding_ratio': 1.89},
                {'stock_code': '600519', 'stock_name': '贵州茅台', 'holding_ratio': 1.67},
                {'stock_code': '002415', 'stock_name': '海康威视', 'holding_ratio': 1.34},
                {'stock_code': '600887', 'stock_name': '伊利股份', 'holding_ratio': 1.23},
                {'stock_code': '000002', 'stock_name': '万科A', 'holding_ratio': 0.89},
                {'stock_code': '002594', 'stock_name': 'BYD', 'holding_ratio': 0.76},
                {'stock_code': '000876', 'stock_name': '新希望', 'holding_ratio': 0.45},
                {'stock_code': '600276', 'stock_name': '恒瑞医药', 'holding_ratio': 0.34}
            ]
        }
        return sample_data
    
    def _load_real_data(self):
        """加载真实数据 - 按最新报告期筛选机构持股数据（全部机构前30名，其他类别前10名）"""
        try:
            data_files = self._get_data_files()
            if not data_files:
                logger.warning("没有找到数据文件，使用示例数据")
                return self._load_sample_data()
            
            # 读取合并的CSV文件
            file_path = data_files[0]
            df = pd.read_csv(file_path, encoding='utf-8', dtype={'股票代码': str, 'stock_code': str})
            logger.info(f"成功读取合并文件 {file_path}，包含 {len(df)} 行数据")
            
            # 打印列名以便调试
            logger.info(f"CSV文件列名: {list(df.columns)}")
            
            # 获取最新报告期
            latest_report_date = df['report_date'].max()
            logger.info(f"最新报告期: {latest_report_date}")
            
            # 筛选最新报告期的数据
            latest_df = df[df['report_date'] == latest_report_date].copy()
            logger.info(f"最新报告期数据包含 {len(latest_df)} 行")
            
            all_data = {
                'all': [],
                'fund': [],
                'insurance': [],
                'qfii': [],
                'social-security': []
            }
            
            # 用于汇总每个股票的总持股比例
            stock_totals = {}
            
            # 处理每一行数据
            for _, row in latest_df.iterrows():
                try:
                    # 获取基本信息
                    stock_code = str(row.get('股票代码', row.get('stock_code', '')))
                    stock_name = str(row.get('股票名称', row.get('股票简称', row.get('stock_name', ''))))
                    
                    # 获取机构类型
                    institution_type = str(row.get('institution_type', row.get('机构类型', '')))
                    
                    # 优先使用占流通股比例，如果没有则使用占总股本比例
                    holding_ratio = 0
                    if '占流通股比例' in row and pd.notna(row['占流通股比例']):
                        holding_ratio = float(row['占流通股比例'])
                    elif '占总股本比例' in row and pd.notna(row['占总股本比例']):
                        holding_ratio = float(row['占总股本比例'])
                    elif '持股比例' in row and pd.notna(row['持股比例']):
                        holding_ratio = float(row['持股比例'])
                    elif 'holding_ratio' in row and pd.notna(row['holding_ratio']):
                        holding_ratio = float(row['holding_ratio'])
                    
                    # 只处理有效数据
                    if not stock_code or not stock_name or holding_ratio <= 0:
                        continue
                    
                    stock_data = {
                        'stock_code': stock_code,
                        'stock_name': stock_name,
                        'holding_ratio': holding_ratio,
                        'report_date': int(latest_report_date)
                    }
                    
                    # 为"全部机构"汇总每个股票的总持股比例
                    stock_key = (stock_code, stock_name)
                    if stock_key not in stock_totals:
                        stock_totals[stock_key] = {
                            'stock_code': stock_code,
                            'stock_name': stock_name,
                            'holding_ratio': 0,
                            'report_date': int(latest_report_date)
                        }
                    stock_totals[stock_key]['holding_ratio'] += holding_ratio
                    
                    # 根据机构类型分类
                    if '基金' in institution_type or 'fund' in institution_type.lower():
                        all_data['fund'].append(stock_data)
                    elif '保险' in institution_type or 'insurance' in institution_type.lower():
                        all_data['insurance'].append(stock_data)
                    elif 'qfii' in institution_type.lower() or 'QFII' in institution_type:
                        all_data['qfii'].append(stock_data)
                    elif '社保' in institution_type or 'social' in institution_type.lower():
                        all_data['social-security'].append(stock_data)
                        
                except Exception as e:
                    logger.warning(f"处理数据行时出错: {e}")
                    continue
            
            # 将汇总后的股票总持股比例添加到"全部机构"类别
            all_data['all'] = list(stock_totals.values())
            
            # 对每个类别的数据进行去重、排序并取前N名
            for category in all_data:
                # 去重：如果同一股票有多条记录，保留持股比例最高的
                unique_stocks = {}
                for stock in all_data[category]:
                    stock_key = (stock['stock_code'], stock['stock_name'])
                    if stock_key not in unique_stocks or stock['holding_ratio'] > unique_stocks[stock_key]['holding_ratio']:
                        unique_stocks[stock_key] = stock
                
                # 转换回列表并按持股比例排序
                all_data[category] = list(unique_stocks.values())
                all_data[category].sort(key=lambda x: x['holding_ratio'], reverse=True)
                
                # 全部机构显示前30名，其他类别显示前10名
                top_count = 30 if category == 'all' else 10
                all_data[category] = all_data[category][:top_count]
                logger.info(f"类别 {category} 最新报告期({latest_report_date})前{top_count}名包含 {len(all_data[category])} 条记录")
            
            logger.info(f"真实数据加载完成，包含类别: {list(all_data.keys())}")
            return all_data
            
        except Exception as e:
            logger.error(f"加载真实数据失败: {e}")
            return self._load_sample_data()
    
    def _load_real_data_by_report_date(self, target_report_date):
        """按指定报告期加载真实数据"""
        try:
            data_files = self._get_data_files()
            if not data_files:
                logger.warning("没有找到数据文件，使用示例数据")
                return self._load_sample_data()
            
            # 读取合并的CSV文件
            file_path = data_files[0]
            df = pd.read_csv(file_path, encoding='utf-8', dtype={'股票代码': str, 'stock_code': str})
            logger.info(f"成功读取合并文件 {file_path}，包含 {len(df)} 行数据")
            
            # 如果没有指定报告期，使用最新报告期
            if target_report_date is None:
                target_report_date = df['report_date'].max()
            
            logger.info(f"目标报告期: {target_report_date}")
            
            # 筛选指定报告期的数据
            target_df = df[df['report_date'] == target_report_date].copy()
            logger.info(f"目标报告期数据包含 {len(target_df)} 行")
            
            if len(target_df) == 0:
                logger.warning(f"报告期 {target_report_date} 没有数据")
                return self._load_sample_data()
            
            all_data = {
                'all': [],
                'fund': [],
                'insurance': [],
                'qfii': [],
                'social-security': []
            }
            
            # 用于汇总每个股票的总持股比例
            stock_totals = {}
            
            # 处理每一行数据
            for _, row in target_df.iterrows():
                try:
                    # 获取基本信息
                    stock_code = str(row.get('股票代码', row.get('stock_code', '')))
                    stock_name = str(row.get('股票名称', row.get('股票简称', row.get('stock_name', ''))))
                    
                    # 获取机构类型
                    institution_type = str(row.get('institution_type', row.get('机构类型', '')))
                    
                    # 优先使用占流通股比例，如果没有则使用占总股本比例
                    holding_ratio = 0
                    if '占流通股比例' in row and pd.notna(row['占流通股比例']):
                        holding_ratio = float(row['占流通股比例'])
                    elif '占总股本比例' in row and pd.notna(row['占总股本比例']):
                        holding_ratio = float(row['占总股本比例'])
                    elif '持股比例' in row and pd.notna(row['持股比例']):
                        holding_ratio = float(row['持股比例'])
                    elif 'holding_ratio' in row and pd.notna(row['holding_ratio']):
                        holding_ratio = float(row['holding_ratio'])
                    
                    # 只处理有效数据
                    if not stock_code or not stock_name or holding_ratio <= 0:
                        continue
                    
                    stock_data = {
                        'stock_code': stock_code,
                        'stock_name': stock_name,
                        'holding_ratio': holding_ratio,
                        'report_date': int(target_report_date)
                    }
                    
                    # 为"全部机构"汇总每个股票的总持股比例
                    stock_key = (stock_code, stock_name)
                    if stock_key not in stock_totals:
                        stock_totals[stock_key] = {
                            'stock_code': stock_code,
                            'stock_name': stock_name,
                            'holding_ratio': 0,
                            'report_date': int(target_report_date)
                        }
                    stock_totals[stock_key]['holding_ratio'] += holding_ratio
                    
                    # 根据机构类型分类
                    if '基金' in institution_type or 'fund' in institution_type.lower():
                        all_data['fund'].append(stock_data)
                    elif '保险' in institution_type or 'insurance' in institution_type.lower():
                        all_data['insurance'].append(stock_data)
                    elif 'qfii' in institution_type.lower() or 'QFII' in institution_type:
                        all_data['qfii'].append(stock_data)
                    elif '社保' in institution_type or 'social' in institution_type.lower():
                        all_data['social-security'].append(stock_data)
                        
                except Exception as e:
                    logger.warning(f"处理数据行时出错: {e}")
                    continue
            
            # 将汇总后的股票总持股比例添加到"全部机构"类别
            all_data['all'] = list(stock_totals.values())
            
            # 对每个类别的数据进行去重、排序并取前N名
            for category in all_data:
                # 去重：如果同一股票有多条记录，保留持股比例最高的
                unique_stocks = {}
                for stock in all_data[category]:
                    stock_key = (stock['stock_code'], stock['stock_name'])
                    if stock_key not in unique_stocks or stock['holding_ratio'] > unique_stocks[stock_key]['holding_ratio']:
                        unique_stocks[stock_key] = stock
                
                # 转换回列表并按持股比例排序
                all_data[category] = list(unique_stocks.values())
                all_data[category].sort(key=lambda x: x['holding_ratio'], reverse=True)
                
                # 全部机构显示前30名，其他类别显示前10名
                top_count = 30 if category == 'all' else 10
                all_data[category] = all_data[category][:top_count]
                logger.info(f"类别 {category} 报告期({target_report_date})前{top_count}名包含 {len(all_data[category])} 条记录")
            
            logger.info(f"按报告期({target_report_date})数据加载完成，包含类别: {list(all_data.keys())}")
            return all_data
            
        except Exception as e:
            logger.error(f"按报告期加载数据失败: {e}")
            return self._load_sample_data()
    
    def get_available_report_dates(self):
        """获取可用的报告期列表（最近5期）"""
        try:
            data_files = self._get_data_files()
            if not data_files:
                # 返回示例报告期
                return [20240930, 20240630, 20240331, 20231231, 20230930]
            
            # 读取合并的CSV文件
            file_path = data_files[0]
            df = pd.read_csv(file_path, encoding='utf-8')
            
            # 获取所有报告期并排序（降序）
            report_dates = sorted(df['report_date'].unique(), reverse=True)
            
            # 返回最近5期，转换为Python原生int类型以支持JSON序列化
            return [int(date) for date in report_dates[:5]]
            
        except Exception as e:
            logger.error(f"获取报告期列表失败: {e}")
            return [20240930, 20240630, 20240331, 20231231, 20230930]
    
    def get_top_holdings(self, category='all', limit=10, report_date=None):
        """获取指定类别的前N名持股数据"""
        try:
            # 生成缓存键
            cache_key = f"top_holdings_{category}_{limit}_{report_date or 'latest'}"
            
            # 检查内存缓存
            if cache_key in self._memory_cache:
                logger.info(f"从内存缓存获取数据: {cache_key}")
                return self._memory_cache[cache_key]
            
            # 检查文件缓存
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
            if os.path.exists(cache_file):
                cache_time = os.path.getmtime(cache_file)
                if time.time() - cache_time < self._cache_duration:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    self._memory_cache[cache_key] = data
                    logger.info(f"从文件缓存获取数据: {cache_key}")
                    return data
            
            # 加载数据
            if report_date:
                all_data = self._load_real_data_by_report_date(report_date)
            else:
                all_data = self._load_real_data()
            
            # 获取指定类别的数据
            if category not in all_data:
                logger.warning(f"未找到类别 {category} 的数据")
                return []
            
            result = all_data[category][:limit]
            
            # 保存到缓存
            self._memory_cache[cache_key] = result
            os.makedirs(self.cache_dir, exist_ok=True)
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            logger.info(f"获取 {category} 类别前 {limit} 名数据成功，共 {len(result)} 条记录")
            return result
            
        except Exception as e:
            logger.error(f"获取持股数据失败: {e}")
            return []
    
    def get_stock_holdings_detail(self, stock_code):
        """获取指定股票的详细持股信息 - 展示各个报告期和不同机构的持股情况"""
        try:
            # 检查缓存
            detail_cache_file = os.path.join(self.trend_cache_dir, f"detail_{stock_code}.json")
            cached_detail = read_cache(detail_cache_file)
            
            if (cached_detail and not is_cache_expired(cached_detail.get('timestamp', 0), hours=6)):
                logger.info(f"返回缓存的详细持股数据 - {stock_code}")
                return cached_detail.get('data', {})
            
            # 从真实数据中获取详细信息
            data_files = self._get_data_files()
            if not data_files:
                logger.warning("没有找到数据文件")
                return {}
            
            # 读取合并的CSV文件
            file_path = data_files[0]
            df = pd.read_csv(file_path, encoding='utf-8', dtype={'股票代码': str, 'stock_code': str})
            
            # 筛选指定股票的数据
            stock_df = df[
                (df['股票代码'].astype(str) == str(stock_code)) |
                (df.get('stock_code', pd.Series()).astype(str) == str(stock_code))
            ].copy()
            
            if stock_df.empty:
                logger.warning(f"未找到股票 {stock_code} 的数据")
                return {}
            
            # 按报告期和机构类型组织数据
            detail_data = {
                'stock_info': {
                    'stock_code': stock_code,
                    'stock_name': stock_df.iloc[0].get('股票名称', stock_df.iloc[0].get('股票简称', stock_df.iloc[0].get('stock_name', '')))
                },
                'by_report_date': {},
                'by_institution_type': {}
            }
            
            # 按报告期分组
            for report_date in sorted(stock_df['report_date'].unique(), reverse=True):
                report_df = stock_df[stock_df['report_date'] == report_date]
                
                institutions = []
                for _, row in report_df.iterrows():
                    institution_type = str(row.get('institution_type', row.get('机构类型', '')))
                    
                    # 获取持股比例
                    holding_ratio = 0
                    if '占流通股比例' in row and pd.notna(row['占流通股比例']):
                        holding_ratio = float(row['占流通股比例'])
                    elif '占总股本比例' in row and pd.notna(row['占总股本比例']):
                        holding_ratio = float(row['占总股本比例'])
                    elif '持股比例' in row and pd.notna(row['持股比例']):
                        holding_ratio = float(row['持股比例'])
                    elif 'holding_ratio' in row and pd.notna(row['holding_ratio']):
                        holding_ratio = float(row['holding_ratio'])
                    
                    if holding_ratio > 0:
                        institutions.append({
                            'institution_type': institution_type,
                            'holding_ratio': holding_ratio,
                            'holding_count': int(row.get('持有基金家数', row.get('holding_count', 0))),
                            'market_value': float(row.get('持股市值', row.get('market_value', 0)))
                        })
                
                # 按持股比例排序
                institutions.sort(key=lambda x: x['holding_ratio'], reverse=True)
                detail_data['by_report_date'][str(report_date)] = institutions
            
            # 按机构类型分组
            institution_types = ['基金', '保险', 'QFII', '社保']
            for inst_type in institution_types:
                # 安全检查列是否存在
                condition1 = pd.Series([False] * len(stock_df))
                condition2 = pd.Series([False] * len(stock_df))
                
                if 'institution_type' in stock_df.columns:
                    condition1 = stock_df['institution_type'].str.contains(inst_type, case=False, na=False)
                if '机构类型' in stock_df.columns:
                    condition2 = stock_df['机构类型'].str.contains(inst_type, na=False)
                
                type_df = stock_df[condition1 | condition2]
                
                if not type_df.empty:
                    periods = []
                    for report_date in sorted(type_df['report_date'].unique(), reverse=True):
                        period_df = type_df[type_df['report_date'] == report_date]
                        
                        # 计算该报告期该机构类型的总持股比例
                        total_ratio = 0
                        for _, row in period_df.iterrows():
                            if '占流通股比例' in row and pd.notna(row['占流通股比例']):
                                total_ratio += float(row['占流通股比例'])
                            elif '占总股本比例' in row and pd.notna(row['占总股本比例']):
                                total_ratio += float(row['占总股本比例'])
                        
                        if total_ratio > 0:
                            periods.append({
                                'report_date': int(report_date),
                                'holding_ratio': round(total_ratio, 2),
                                'institution_count': int(len(period_df))
                            })
                    
                    detail_data['by_institution_type'][inst_type] = periods
            
            # 保存到缓存
            save_cache(detail_cache_file, detail_data)
            
            logger.info(f"获取股票 {stock_code} 详细持股信息成功")
            return detail_data
            
        except Exception as e:
            logger.error(f"获取股票详细持股信息失败: {e}")
            return {}
    
    def get_stock_trend(self, category, stock_code):
        """获取指定股票的持股变化趋势数据（带缓存优化）"""
        try:
            # 检查缓存
            trend_cache_file = os.path.join(self.trend_cache_dir, f"{category}_{stock_code}.json")
            cached_trend = read_cache(trend_cache_file)
            
            if (cached_trend and not is_cache_expired(cached_trend.get('timestamp', 0), hours=6)):
                logger.info(f"返回缓存的趋势数据 - {category}:{stock_code}")
                return cached_trend.get('data', [])
            
            # 优先使用真实数据生成趋势
            real_trend_data = self._generate_trend_from_real_data(category, stock_code)
            if real_trend_data:
                # 保存到缓存
                save_cache(trend_cache_file, real_trend_data)
                return real_trend_data
            
            # 如果没有真实数据，生成模拟数据
            logger.info(f"生成模拟趋势数据 - {category}:{stock_code}")
            trend_data = self._generate_realistic_trend_data(category, stock_code)
            
            # 保存到缓存
            save_cache(trend_cache_file, trend_data)
            
            return trend_data
            
        except Exception as e:
            logger.error(f"获取股票趋势数据失败: {e}")
            return []
    
    def _generate_trend_from_real_data(self, category, stock_code):
        """从真实数据生成趋势数据"""
        try:
            data_files = self._get_data_files()
            if not data_files:
                return None
            
            # 读取合并的CSV文件
            file_path = data_files[0]
            df = pd.read_csv(file_path, encoding='utf-8', dtype={'股票代码': str, 'stock_code': str})
            
            # 筛选指定股票的数据
            stock_df = df[
                (df['股票代码'].astype(str) == str(stock_code)) |
                (df.get('stock_code', pd.Series()).astype(str) == str(stock_code))
            ].copy()
            
            if stock_df.empty:
                return None
            
            # 按报告期分组并计算趋势
            trend_data = []
            
            # 根据类别筛选机构类型
            if category != 'all':
                category_mapping = {
                    'fund': '基金',
                    'insurance': '保险', 
                    'qfii': 'QFII',
                    'social-security': '社保'
                }
                
                if category in category_mapping:
                    inst_type = category_mapping[category]
                    # 安全检查列是否存在
                    condition1 = pd.Series([False] * len(stock_df))
                    condition2 = pd.Series([False] * len(stock_df))
                    
                    if 'institution_type' in stock_df.columns:
                        condition1 = stock_df['institution_type'].str.contains(inst_type, case=False, na=False)
                    if '机构类型' in stock_df.columns:
                        condition2 = stock_df['机构类型'].str.contains(inst_type, na=False)
                    
                    stock_df = stock_df[condition1 | condition2]
            
            # 按报告期聚合数据
            for report_date in sorted(stock_df['report_date'].unique()):
                period_df = stock_df[stock_df['report_date'] == report_date]
                
                # 计算该报告期的总持股比例
                total_ratio = 0
                for _, row in period_df.iterrows():
                    if '占流通股比例' in row and pd.notna(row['占流通股比例']):
                        total_ratio += float(row['占流通股比例'])
                    elif '占总股本比例' in row and pd.notna(row['占总股本比例']):
                        total_ratio += float(row['占总股本比例'])
                
                if total_ratio > 0:
                    trend_data.append({
                        'date': str(report_date),
                        'holding_ratio': round(total_ratio, 2),
                        'change_ratio': 0  # 变化比例需要计算
                    })
            
            # 计算变化比例
            if len(trend_data) > 1:
                base_ratio = trend_data[0]['holding_ratio']
                for item in trend_data:
                    item['change_ratio'] = round((item['holding_ratio'] / base_ratio - 1) * 100, 2)
            
            return trend_data if trend_data else None
            
        except Exception as e:
            logger.error(f"从真实数据生成趋势失败: {e}")
            return None
    
    def _generate_realistic_trend_data(self, category, stock_code):
        """生成更真实的趋势数据（模拟数据）"""
        import random
        import hashlib
        
        # 使用股票代码作为随机种子，确保数据一致性
        seed = int(hashlib.md5(f"{category}_{stock_code}".encode()).hexdigest()[:8], 16)
        random.seed(seed)
        
        # 根据类别设置基础持股比例范围
        category_ranges = {
            'all': (5.0, 15.0),
            'fund': (3.0, 12.0),
            'insurance': (1.0, 8.0),
            'qfii': (0.5, 3.0),
            'social-security': (1.0, 5.0)
        }
        
        min_ratio, max_ratio = category_ranges.get(category, (1.0, 10.0))
        base_ratio = random.uniform(min_ratio, max_ratio)
        
        # 生成过去18个月的数据
        trend_data = []
        current_ratio = base_ratio
        
        for i in range(18):
            date = datetime.now() - timedelta(days=30 * (17 - i))
            
            # 添加季度性变化和随机波动
            seasonal_factor = 1 + 0.1 * math.sin(2 * math.pi * i / 12)  # 年度周期
            quarterly_factor = 1 + 0.05 * math.sin(2 * math.pi * i / 3)  # 季度周期
            random_change = random.uniform(-0.15, 0.15)  # ±15%随机变化
            
            # 计算新的持股比例
            change_factor = seasonal_factor * quarterly_factor * (1 + random_change)
            current_ratio = current_ratio * change_factor
            
            # 确保在合理范围内
            current_ratio = max(min_ratio * 0.3, min(max_ratio * 1.5, current_ratio))
            
            trend_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'holding_ratio': round(current_ratio, 2),
                'change_ratio': round((current_ratio / base_ratio - 1) * 100, 2)  # 相对变化百分比
            })
        
        return trend_data

# 创建全局实例
institutional_holdings_data = InstitutionalHoldingsData()