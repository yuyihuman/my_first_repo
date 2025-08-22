import akshare as ak
import pandas as pd
import os
from datetime import datetime
import time

def get_stock_data(stock_code, stock_name, base_folder="all_stocks_data"):
    """
    获取单个股票的所有数据
    """
    print(f"\n开始获取股票 {stock_code} ({stock_name}) 的数据...")
    
    # 创建股票专用数据文件夹
    stock_folder = os.path.join(base_folder, f"stock_{stock_code}_data")
    if not os.path.exists(stock_folder):
        os.makedirs(stock_folder)
    
    success_count = 0
    total_attempts = 6  # 总共尝试获取6种数据
    
    try:
        # 1. 获取历史日线数据
        print(f"  1. 获取历史日线数据...")
        stock_zh_a_hist_df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date="20100101", end_date="20241231", adjust="")
        
        # 保存日线数据
        daily_filename = os.path.join(stock_folder, f"{stock_code}_daily_history.csv")
        stock_zh_a_hist_df.to_csv(daily_filename, index=False, encoding='utf-8-sig')
        print(f"    日线数据已保存: {len(stock_zh_a_hist_df)} 条")
        success_count += 1
        
    except Exception as e:
        print(f"    获取日线数据失败: {e}")

    try:
        # 2. 获取财务摘要数据
        print(f"  2. 获取财务摘要数据...")
        financial_abstract = ak.stock_financial_abstract(symbol=stock_code)
        if financial_abstract is not None and not financial_abstract.empty:
            financial_abstract_filename = os.path.join(stock_folder, f"{stock_code}_financial_abstract.csv")
            financial_abstract.to_csv(financial_abstract_filename, index=False, encoding='utf-8-sig')
            print(f"    财务摘要数据已保存: {len(financial_abstract)} 条")
            success_count += 1
        else:
            print(f"    获取财务摘要数据失败")
    except Exception as e:
        print(f"    获取财务摘要数据时出错: {e}")

    try:
        # 3. 获取财务分析指标数据
        print(f"  3. 获取财务分析指标数据...")
        financial_indicator = ak.stock_financial_analysis_indicator(symbol=stock_code)
        if financial_indicator is not None and not financial_indicator.empty:
            financial_indicator_filename = os.path.join(stock_folder, f"{stock_code}_financial_indicator.csv")
            financial_indicator.to_csv(financial_indicator_filename, index=False, encoding='utf-8-sig')
            print(f"    财务分析指标数据已保存: {len(financial_indicator)} 条")
            success_count += 1
        else:
            print(f"    获取财务分析指标数据失败")
    except Exception as e:
        print(f"    获取财务分析指标数据时出错: {e}")

    try:
        # 4. 获取同花顺财务摘要数据
        print(f"  4. 获取同花顺财务摘要数据...")
        financial_abstract_ths = ak.stock_financial_abstract_ths(symbol=stock_code)
        if financial_abstract_ths is not None and not financial_abstract_ths.empty:
            financial_abstract_ths_filename = os.path.join(stock_folder, f"{stock_code}_financial_abstract_ths.csv")
            financial_abstract_ths.to_csv(financial_abstract_ths_filename, index=False, encoding='utf-8-sig')
            print(f"    同花顺财务摘要数据已保存: {len(financial_abstract_ths)} 条")
            success_count += 1
        else:
            print(f"    获取同花顺财务摘要数据失败")
    except Exception as e:
        print(f"    获取同花顺财务摘要数据时出错: {e}")

    try:
        # 5. 获取东方财富详细财务报表数据
        print(f"  5. 获取东方财富详细财务报表数据...")
        
        # 测试最近几个季度的数据
        test_dates = ["20241231", "20240930", "20240630", "20240331", "20231231"]
        
        all_profit_data = []
        all_balance_data = []
        all_cashflow_data = []
        
        for date in test_dates:
            # 获取利润表数据
            try:
                lrb_data = ak.stock_lrb_em(date=date)
                stock_lrb = lrb_data[lrb_data['股票代码'] == stock_code]
                if not stock_lrb.empty:
                    stock_lrb = stock_lrb.copy()
                    stock_lrb['报告期'] = date
                    all_profit_data.append(stock_lrb)
            except Exception as e:
                pass
            
            # 获取资产负债表数据
            try:
                zcfz_data = ak.stock_zcfz_em(date=date)
                stock_zcfz = zcfz_data[zcfz_data['股票代码'] == stock_code]
                if not stock_zcfz.empty:
                    stock_zcfz = stock_zcfz.copy()
                    stock_zcfz['报告期'] = date
                    all_balance_data.append(stock_zcfz)
            except Exception as e:
                pass
            
            # 获取现金流量表数据
            try:
                xjll_data = ak.stock_xjll_em(date=date)
                stock_xjll = xjll_data[xjll_data['股票代码'] == stock_code]
                if not stock_xjll.empty:
                    stock_xjll = stock_xjll.copy()
                    stock_xjll['报告期'] = date
                    all_cashflow_data.append(stock_xjll)
            except Exception as e:
                pass
        
        # 保存合并后的财务报表数据
        if all_profit_data:
            profit_df = pd.concat(all_profit_data, ignore_index=True)
            profit_filename = os.path.join(stock_folder, f"{stock_code}_profit_statements_em.csv")
            profit_df.to_csv(profit_filename, index=False, encoding='utf-8-sig')
            print(f"    利润表数据已保存: {len(profit_df)} 条记录")
            success_count += 1
        
        if all_balance_data:
            balance_df = pd.concat(all_balance_data, ignore_index=True)
            balance_filename = os.path.join(stock_folder, f"{stock_code}_balance_sheets_em.csv")
            balance_df.to_csv(balance_filename, index=False, encoding='utf-8-sig')
            print(f"    资产负债表数据已保存: {len(balance_df)} 条记录")
            success_count += 1
        
        if all_cashflow_data:
            cashflow_df = pd.concat(all_cashflow_data, ignore_index=True)
            cashflow_filename = os.path.join(stock_folder, f"{stock_code}_cashflow_statements_em.csv")
            cashflow_df.to_csv(cashflow_filename, index=False, encoding='utf-8-sig')
            print(f"    现金流量表数据已保存: {len(cashflow_df)} 条记录")
            
    except Exception as e:
        print(f"    获取东方财富财务报表数据时出错: {e}")
    
    # 生成单个股票的数据报告
    summary_content = f"""股票代码: {stock_code}
股票名称: {stock_name}
数据获取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
成功获取数据类型: {success_count}/{total_attempts}

获取的数据文件:
1. {stock_code}_daily_history.csv - 历史日线数据 (akshare)
2. {stock_code}_financial_abstract.csv - 财务摘要数据 (新浪财经)
3. {stock_code}_financial_abstract_ths.csv - 同花顺财务摘要数据
4. {stock_code}_profit_statements_em.csv - 东方财富利润表数据
5. {stock_code}_balance_sheets_em.csv - 东方财富资产负债表数据
6. {stock_code}_cashflow_statements_em.csv - 东方财富现金流量表数据
7. {stock_code}_financial_indicator.csv - 财务分析指标数据

数据来源说明:
- 历史价格数据：akshare (东方财富)
- 财务摘要：新浪财经 (ak.stock_financial_abstract)
- 同花顺财务摘要：同花顺 (ak.stock_financial_abstract_ths)
- 详细财务报表：东方财富 (ak.stock_lrb_em, ak.stock_zcfz_em, ak.stock_xjll_em)
- 文件编码：UTF-8-BOM，支持中文显示
"""
    
    report_filename = os.path.join(stock_folder, "data_summary.txt")
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(summary_content)
    
    print(f"  股票 {stock_code} 数据获取完成，成功率: {success_count}/{total_attempts}")
    return success_count, total_attempts

def main():
    """
    主函数：批量获取所有股票数据
    """
    # 读取股票列表CSV文件
    csv_file = "stock_data_20250821_000413.csv"
    
    if not os.path.exists(csv_file):
        print(f"错误：找不到文件 {csv_file}")
        return
    
    print(f"读取股票列表文件: {csv_file}")
    
    try:
        # 读取CSV文件
        df = pd.read_csv(csv_file, encoding='utf-8')
        print(f"共找到 {len(df)} 只股票")
        
        # 创建总的数据文件夹
        base_folder = "all_stocks_data"
        if not os.path.exists(base_folder):
            os.makedirs(base_folder)
            print(f"创建总文件夹: {base_folder}")
        
        # 统计信息
        total_stocks = len(df)
        processed_stocks = 0
        successful_stocks = 0
        total_success_count = 0
        total_attempts = 0
        
        # 批量处理股票
        for index, row in df.iterrows():
            stock_code = str(row['代码']).zfill(6)  # 确保股票代码是6位数字
            stock_name = row['名称']
            
            processed_stocks += 1
            print(f"\n{'='*60}")
            print(f"处理进度: {processed_stocks}/{total_stocks} ({processed_stocks/total_stocks*100:.1f}%)")
            print(f"当前股票: {stock_code} - {stock_name}")
            
            try:
                success_count, attempt_count = get_stock_data(stock_code, stock_name, base_folder)
                total_success_count += success_count
                total_attempts += attempt_count
                
                if success_count > 0:
                    successful_stocks += 1
                
                # 添加延时，避免请求过于频繁
                time.sleep(1)
                
            except Exception as e:
                print(f"处理股票 {stock_code} 时发生错误: {e}")
                continue
        
        # 生成总体报告
        print(f"\n{'='*60}")
        print("批量数据获取完成！")
        print(f"总共处理股票: {total_stocks}")
        print(f"成功获取数据的股票: {successful_stocks}")
        print(f"总体成功率: {successful_stocks/total_stocks*100:.1f}%")
        print(f"数据获取成功率: {total_success_count/total_attempts*100:.1f}%")
        
        # 保存总体报告
        overall_report = f"""批量股票数据获取报告
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

统计信息:
- 总共处理股票: {total_stocks}
- 成功获取数据的股票: {successful_stocks}
- 股票处理成功率: {successful_stocks/total_stocks*100:.1f}%
- 数据获取成功率: {total_success_count/total_attempts*100:.1f}%

数据存储位置: {base_folder}/
每个股票的数据存储在独立的子文件夹中

数据来源:
- akshare库
- 新浪财经
- 同花顺
- 东方财富

注意事项:
- 所有文件使用UTF-8-BOM编码
- 部分股票可能因为数据源限制无法获取完整数据
- 建议定期更新数据
"""
        
        report_filename = os.path.join(base_folder, "batch_processing_report.txt")
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(overall_report)
        
        print(f"\n总体报告已保存: {report_filename}")
        print(f"所有数据文件保存在: {base_folder}/")
        
    except Exception as e:
        print(f"读取CSV文件时发生错误: {e}")
        return

if __name__ == "__main__":
    main()