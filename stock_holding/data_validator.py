#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据验证和清洗模块

提供数据质量检查、异常值检测和数据清洗功能
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import warnings


class DataValidator:
    """
    数据验证器
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        初始化数据验证器
        
        Args:
            logger: 日志记录器
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # 定义数据质量规则
        self.validation_rules = {
            'stock_code': {
                'required': True,
                'type': str,
                'pattern': r'^[0-9]{6}$',  # 严格要求6位数字
                'description': '股票代码应为6位数字'
            },
            'stock_name': {
                'required': True,
                'type': str,
                'min_length': 1,
                'max_length': 20,
                'description': '股票名称长度应在1-20字符之间'
            },
            'hold_num': {
                'required': False,
                'type': (int, float),
                'min_value': 0,
                'description': '持股数量应为非负数'
            },
            'share_hold_num': {
                'required': False,
                'type': (int, float),
                'min_value': 0,
                'description': '持股数量应为非负数'
            },
            'value_position': {
                'required': False,
                'type': (int, float),
                'min_value': 0,
                'description': '持仓市值应为非负数'
            },
            'hold_value_change': {
                'required': False,
                'type': (int, float),
                'description': '持仓市值变化可以为任意数值'
            },
            'hold_rate_change': {
                'required': False,
                'type': (int, float),
                'min_value': -1.0,
                'max_value': 1.0,
                'description': '持股比例变化应在-100%到100%之间'
            },
            'institution_type': {
                'required': True,
                'type': str,
                'allowed_values': ["基金持仓", "QFII持仓", "社保持仓", "券商持仓", "保险持仓", "信托持仓"],
                'description': '机构类型应为预定义的类型之一'
            },
            'report_date': {
                'required': True,
                'type': str,
                'pattern': r'^\d{8}$',  # 8位数字格式如20250331
                'description': '报告日期应为8位数字格式（如20250331）'
            }
        }
    
    def validate_dataframe(self, df: pd.DataFrame, strict: bool = False) -> Dict:
        """
        验证DataFrame的数据质量
        
        Args:
            df: 要验证的DataFrame
            strict: 是否严格模式（严格模式下会抛出异常）
            
        Returns:
            验证结果字典
        """
        self.logger.info(f"开始验证数据，共 {len(df)} 行")
        
        validation_result = {
            'is_valid': True,
            'total_rows': len(df),
            'errors': [],
            'warnings': [],
            'statistics': {},
            'cleaned_rows': 0
        }
        
        if df.empty:
            validation_result['errors'].append("数据为空")
            validation_result['is_valid'] = False
            return validation_result
        
        # 检查必需列
        required_columns = [col for col, rules in self.validation_rules.items() 
                          if rules.get('required', False)]
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            error_msg = f"缺少必需列: {missing_columns}"
            validation_result['errors'].append(error_msg)
            validation_result['is_valid'] = False
            
            if strict:
                raise ValueError(error_msg)
        
        # 逐列验证
        for column in df.columns:
            if column in self.validation_rules:
                column_result = self._validate_column(df[column], column)
                validation_result['errors'].extend(column_result['errors'])
                validation_result['warnings'].extend(column_result['warnings'])
                validation_result['statistics'][column] = column_result['statistics']
        
        # 检查重复行
        duplicate_count = df.duplicated().sum()
        if duplicate_count > 0:
            warning_msg = f"发现 {duplicate_count} 行重复数据"
            validation_result['warnings'].append(warning_msg)
            self.logger.warning(warning_msg)
        
        # 检查数据一致性
        consistency_errors = self._check_data_consistency(df)
        validation_result['errors'].extend(consistency_errors)
        
        # 更新验证状态
        if validation_result['errors']:
            validation_result['is_valid'] = False
        
        self.logger.info(f"数据验证完成 - 错误: {len(validation_result['errors'])}, "
                        f"警告: {len(validation_result['warnings'])}")
        
        return validation_result
    
    def _validate_column(self, series: pd.Series, column_name: str) -> Dict:
        """
        验证单列数据
        
        Args:
            series: 要验证的Series
            column_name: 列名
            
        Returns:
            验证结果
        """
        rules = self.validation_rules[column_name]
        result = {
            'errors': [],
            'warnings': [],
            'statistics': {
                'null_count': series.isnull().sum(),
                'null_percentage': series.isnull().mean() * 100,
                'unique_count': series.nunique(),
                'total_count': len(series)
            }
        }
        
        # 检查空值
        null_count = series.isnull().sum()
        if null_count > 0:
            if rules.get('required', False):
                result['errors'].append(f"{column_name}: 发现 {null_count} 个空值（必需字段）")
            else:
                result['warnings'].append(f"{column_name}: 发现 {null_count} 个空值")
        
        # 对非空值进行验证
        non_null_series = series.dropna()
        if len(non_null_series) == 0:
            return result
        
        # 类型检查
        expected_type = rules.get('type')
        if expected_type:
            if not self._check_type(non_null_series, expected_type):
                result['errors'].append(f"{column_name}: 数据类型不符合要求 {expected_type}")
        
        # 数值范围检查
        if 'min_value' in rules or 'max_value' in rules:
            numeric_series = pd.to_numeric(non_null_series, errors='coerce')
            
            if 'min_value' in rules:
                min_violations = (numeric_series < rules['min_value']).sum()
                if min_violations > 0:
                    result['errors'].append(f"{column_name}: {min_violations} 个值小于最小值 {rules['min_value']}")
            
            if 'max_value' in rules:
                max_violations = (numeric_series > rules['max_value']).sum()
                if max_violations > 0:
                    result['errors'].append(f"{column_name}: {max_violations} 个值大于最大值 {rules['max_value']}")
        
        # 字符串长度检查
        if 'min_length' in rules or 'max_length' in rules:
            string_lengths = non_null_series.astype(str).str.len()
            
            if 'min_length' in rules:
                short_count = (string_lengths < rules['min_length']).sum()
                if short_count > 0:
                    result['errors'].append(f"{column_name}: {short_count} 个值长度小于 {rules['min_length']}")
            
            if 'max_length' in rules:
                long_count = (string_lengths > rules['max_length']).sum()
                if long_count > 0:
                    result['errors'].append(f"{column_name}: {long_count} 个值长度大于 {rules['max_length']}")
        
        # 正则表达式检查
        if 'pattern' in rules:
            pattern_violations = ~non_null_series.astype(str).str.match(rules['pattern'])
            violation_count = pattern_violations.sum()
            if violation_count > 0:
                result['errors'].append(f"{column_name}: {violation_count} 个值不符合格式要求")
        
        # 允许值检查
        if 'allowed_values' in rules:
            invalid_values = ~non_null_series.isin(rules['allowed_values'])
            invalid_count = invalid_values.sum()
            if invalid_count > 0:
                unique_invalid = non_null_series[invalid_values].unique()[:5]  # 只显示前5个
                result['errors'].append(f"{column_name}: {invalid_count} 个无效值，例如: {list(unique_invalid)}")
        
        return result
    
    def _check_type(self, series: pd.Series, expected_type) -> bool:
        """
        检查数据类型
        
        Args:
            series: 要检查的Series
            expected_type: 期望的类型
            
        Returns:
            是否符合类型要求
        """
        if isinstance(expected_type, tuple):
            # 多种类型中的任意一种
            return any(self._check_single_type(series, t) for t in expected_type)
        else:
            return self._check_single_type(series, expected_type)
    
    def _check_single_type(self, series: pd.Series, expected_type) -> bool:
        """
        检查单一数据类型
        """
        if expected_type == str:
            # 对于字符串类型，更宽松的检查，允许数字字符串
            return True  # 任何类型都可以转换为字符串
        elif expected_type == int:
            return pd.api.types.is_integer_dtype(series)
        elif expected_type == float:
            return pd.api.types.is_float_dtype(series) or pd.api.types.is_integer_dtype(series)
        else:
            return False
    
    def _check_data_consistency(self, df: pd.DataFrame) -> List[str]:
        """
        检查数据一致性
        
        Args:
            df: 要检查的DataFrame
            
        Returns:
            一致性错误列表
        """
        errors = []
        
        # 检查日期格式一致性
        if 'report_date' in df.columns:
            try:
                pd.to_datetime(df['report_date'], format='%Y%m%d', errors='raise')
            except ValueError:
                errors.append("report_date: 日期格式不一致")
        
        # 检查股票代码和名称的对应关系
        if 'stock_code' in df.columns and 'stock_name' in df.columns:
            code_name_mapping = df.groupby('stock_code')['stock_name'].nunique()
            inconsistent_codes = code_name_mapping[code_name_mapping > 1]
            if len(inconsistent_codes) > 0:
                errors.append(f"发现 {len(inconsistent_codes)} 个股票代码对应多个股票名称")
        
        # 检查数值字段的合理性
        if 'value_position' in df.columns and 'share_hold_num' in df.columns:
            # 持仓市值不应该为0而持股数量不为0
            inconsistent_holdings = (
                (df['value_position'] == 0) & (df['share_hold_num'] > 0)
            ).sum()
            if inconsistent_holdings > 0:
                errors.append(f"发现 {inconsistent_holdings} 行持仓市值为0但持股数量大于0")
        
        return errors
    
    def clean_data(self, df: pd.DataFrame, remove_duplicates: bool = True, 
                   fill_missing: bool = True) -> Tuple[pd.DataFrame, Dict]:
        """
        清洗数据
        
        Args:
            df: 要清洗的DataFrame
            remove_duplicates: 是否移除重复行
            fill_missing: 是否填充缺失值
            
        Returns:
            清洗后的DataFrame和清洗报告
        """
        self.logger.info(f"开始清洗数据，原始数据 {len(df)} 行")
        
        cleaned_df = df.copy()
        cleaning_report = {
            'original_rows': len(df),
            'removed_duplicates': 0,
            'filled_missing': 0,
            'converted_types': [],
            'final_rows': 0
        }
        
        # 移除重复行
        if remove_duplicates:
            before_count = len(cleaned_df)
            cleaned_df = cleaned_df.drop_duplicates()
            removed_count = before_count - len(cleaned_df)
            cleaning_report['removed_duplicates'] = removed_count
            if removed_count > 0:
                self.logger.info(f"移除了 {removed_count} 行重复数据")
        
        # 数据类型转换
        type_conversions = {
            'hold_num': 'float64',
            'share_hold_num': 'float64',
            'value_position': 'float64',
            'hold_value_change': 'float64',
            'hold_rate_change': 'float64'
        }
        
        for column, target_type in type_conversions.items():
            if column in cleaned_df.columns:
                try:
                    original_type = cleaned_df[column].dtype
                    cleaned_df[column] = pd.to_numeric(cleaned_df[column], errors='coerce')
                    if target_type == 'float64':
                        cleaned_df[column] = cleaned_df[column].astype('float64')
                    cleaning_report['converted_types'].append(f"{column}: {original_type} -> {target_type}")
                except Exception as e:
                    self.logger.warning(f"转换 {column} 类型失败: {e}")
        
        # 填充缺失值
        if fill_missing:
            fill_strategies = {
                'hold_num': 0,
                'share_hold_num': 0,
                'value_position': 0,
                'hold_value_change': 0,
                'hold_rate_change': 0
            }
            
            filled_count = 0
            for column, fill_value in fill_strategies.items():
                if column in cleaned_df.columns:
                    null_count = cleaned_df[column].isnull().sum()
                    if null_count > 0:
                        cleaned_df[column] = cleaned_df[column].fillna(fill_value)
                        filled_count += null_count
                        self.logger.info(f"填充了 {column} 列的 {null_count} 个缺失值")
            
            cleaning_report['filled_missing'] = filled_count
        
        # 移除无效行
        # 移除股票代码或机构类型为空的行
        required_columns = ['stock_code', 'institution_type']
        for column in required_columns:
            if column in cleaned_df.columns:
                before_count = len(cleaned_df)
                cleaned_df = cleaned_df.dropna(subset=[column])
                removed_count = before_count - len(cleaned_df)
                if removed_count > 0:
                    self.logger.info(f"移除了 {removed_count} 行 {column} 为空的数据")
        
        cleaning_report['final_rows'] = len(cleaned_df)
        
        self.logger.info(f"数据清洗完成，最终数据 {len(cleaned_df)} 行")
        
        return cleaned_df, cleaning_report
    
    def detect_outliers(self, df: pd.DataFrame, columns: List[str] = None, 
                       method: str = 'iqr') -> Dict:
        """
        检测异常值
        
        Args:
            df: 要检测的DataFrame
            columns: 要检测的列，为None时检测所有数值列
            method: 检测方法 ('iqr', 'zscore')
            
        Returns:
            异常值检测结果
        """
        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()
        
        outlier_result = {
            'method': method,
            'outliers_by_column': {},
            'total_outliers': 0
        }
        
        for column in columns:
            if column not in df.columns:
                continue
            
            series = df[column].dropna()
            if len(series) == 0:
                continue
            
            if method == 'iqr':
                outliers = self._detect_outliers_iqr(series)
            elif method == 'zscore':
                outliers = self._detect_outliers_zscore(series)
            else:
                self.logger.warning(f"未知的异常值检测方法: {method}")
                continue
            
            outlier_count = outliers.sum()
            outlier_result['outliers_by_column'][column] = {
                'count': outlier_count,
                'percentage': outlier_count / len(series) * 100,
                'indices': df.index[outliers].tolist() if outlier_count > 0 else []
            }
            outlier_result['total_outliers'] += outlier_count
        
        return outlier_result
    
    def _detect_outliers_iqr(self, series: pd.Series) -> pd.Series:
        """
        使用IQR方法检测异常值
        """
        Q1 = series.quantile(0.25)
        Q3 = series.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        return (series < lower_bound) | (series > upper_bound)
    
    def _detect_outliers_zscore(self, series: pd.Series, threshold: float = 3.0) -> pd.Series:
        """
        使用Z-score方法检测异常值
        """
        z_scores = np.abs((series - series.mean()) / series.std())
        return z_scores > threshold
    
    def validate_holdings_data(self, df: pd.DataFrame, strict: bool = False) -> pd.DataFrame:
        """
        验证持仓数据
        
        Args:
            df: 要验证的持仓数据DataFrame
            strict: 是否严格模式
            
        Returns:
            验证后的DataFrame
        """
        if df is None or df.empty:
            self.logger.warning("持仓数据为空")
            return df
        
        # 执行数据验证
        validation_result = self.validate_dataframe(df, strict=strict)
        
        if not validation_result['is_valid']:
            self.logger.warning(f"持仓数据验证失败: {validation_result['errors']}")
            if strict:
                raise ValueError(f"数据验证失败: {validation_result['errors']}")
        
        # 清洗数据
        cleaned_df, cleaning_report = self.clean_data(df)
        
        self.logger.info(f"持仓数据验证完成，原始行数: {len(df)}, 清洗后行数: {len(cleaned_df)}")
        
        return cleaned_df
    
    def generate_quality_report(self, df: pd.DataFrame) -> str:
        """
        生成数据质量报告
        
        Args:
            df: 要分析的DataFrame
            
        Returns:
            质量报告文本
        """
        validation_result = self.validate_dataframe(df)
        outlier_result = self.detect_outliers(df)
        
        report_lines = []
        report_lines.append("# 数据质量报告")
        report_lines.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 基本信息
        report_lines.append("\n## 基本信息")
        report_lines.append(f"- 总行数: {validation_result['total_rows']:,}")
        report_lines.append(f"- 总列数: {len(df.columns)}")
        report_lines.append(f"- 数据质量: {'✓ 通过' if validation_result['is_valid'] else '✗ 未通过'}")
        
        # 错误和警告
        if validation_result['errors']:
            report_lines.append("\n## 数据错误")
            for i, error in enumerate(validation_result['errors'], 1):
                report_lines.append(f"{i}. {error}")
        
        if validation_result['warnings']:
            report_lines.append("\n## 数据警告")
            for i, warning in enumerate(validation_result['warnings'], 1):
                report_lines.append(f"{i}. {warning}")
        
        # 列统计
        report_lines.append("\n## 列统计信息")
        for column, stats in validation_result['statistics'].items():
            report_lines.append(f"\n### {column}")
            report_lines.append(f"- 空值数量: {stats['null_count']} ({stats['null_percentage']:.1f}%)")
            report_lines.append(f"- 唯一值数量: {stats['unique_count']}")
            report_lines.append(f"- 总数量: {stats['total_count']}")
        
        # 异常值
        if outlier_result['total_outliers'] > 0:
            report_lines.append("\n## 异常值检测")
            report_lines.append(f"检测方法: {outlier_result['method'].upper()}")
            for column, outlier_info in outlier_result['outliers_by_column'].items():
                if outlier_info['count'] > 0:
                    report_lines.append(f"\n### {column}")
                    report_lines.append(f"- 异常值数量: {outlier_info['count']} ({outlier_info['percentage']:.1f}%)")
        
        return "\n".join(report_lines)


def validate_and_clean_data(df: pd.DataFrame, logger: Optional[logging.Logger] = None) -> Tuple[pd.DataFrame, Dict]:
    """
    便捷函数：验证和清洗数据
    
    Args:
        df: 要处理的DataFrame
        logger: 日志记录器
        
    Returns:
        清洗后的DataFrame和处理报告
    """
    validator = DataValidator(logger)
    
    # 验证数据
    validation_result = validator.validate_dataframe(df)
    
    # 清洗数据
    cleaned_df, cleaning_report = validator.clean_data(df)
    
    # 合并报告
    combined_report = {
        'validation': validation_result,
        'cleaning': cleaning_report,
        'final_quality': validator.validate_dataframe(cleaned_df)
    }
    
    return cleaned_df, combined_report


if __name__ == "__main__":
    # 测试数据验证器
    print("数据验证器测试")
    print("=" * 30)
    
    # 创建测试数据
    test_data = pd.DataFrame({
        'stock_code': ['000001', '000002', '000003', 'INVALID', None],
        'stock_name': ['平安银行', '万科A', '国农科技', '测试股票', None],
        'hold_num': [1000, 2000, -100, 1500, None],  # 包含负值
        'value_position': [1000000, 2000000, 1500000, None, 500000],
        'institution_type': ['基金持仓', 'QFII持仓', '无效类型', '基金持仓', '基金持仓'],
        'report_date': ['20231231', '20231231', '2023-12-31', '20231231', '20231231']
    })
    
    # 创建验证器
    validator = DataValidator()
    
    # 验证数据
    result = validator.validate_dataframe(test_data)
    print(f"验证结果: {'通过' if result['is_valid'] else '未通过'}")
    print(f"错误数量: {len(result['errors'])}")
    print(f"警告数量: {len(result['warnings'])}")
    
    # 清洗数据
    cleaned_data, cleaning_report = validator.clean_data(test_data)
    print(f"\n清洗前: {cleaning_report['original_rows']} 行")
    print(f"清洗后: {cleaning_report['final_rows']} 行")
    
    # 生成质量报告
    quality_report = validator.generate_quality_report(test_data)
    print("\n质量报告已生成")