import json
import os
import shutil
from datetime import datetime
from collections import defaultdict
import statistics
import plotly.graph_objects as go
import plotly.offline as pyo
from datetime import datetime as dt

def load_data_from_file(file_path):
    """从文件加载房价数据"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"加载文件 {file_path} 时出错: {e}")
        return []

def parse_date(date_str):
    """解析日期字符串，返回年月"""
    try:
        date_obj = datetime.strptime(date_str, '%Y.%m.%d')
        return date_obj.year, date_obj.month, date_obj.day
    except:
        return None, None, None

def calculate_monthly_stats(data_files_dir):
    """计算每月统计数据"""
    monthly_data = defaultdict(lambda: defaultdict(lambda: {'total_price': 0, 'total_area': 0, 'count': 0}))  # {(year, month): {day: {total_price, total_area, count}}}
    
    # 指定要处理的文件列表
    target_files = ['jdxc', 'sjxc', 'xjh', 'at', 'tz', 'wjc']
    
    # 遍历指定的数据文件
    for filename in target_files:
        file_path = os.path.join(data_files_dir, filename)
        if os.path.isfile(file_path):
            print(f"处理文件: {filename}")
            data = load_data_from_file(file_path)
            
            for record in data:
                year, month, day = parse_date(record['date'])
                # 添加面积限制：只计算70-140平米之间的数据
                if year and month and day and 70 <= record['area'] <= 140 and record['price'] > 0:
                    # 计算总价 = 面积 × 单价
                    total_price = record['area'] * record['price']
                    monthly_data[(year, month)][day]['total_price'] += total_price
                    monthly_data[(year, month)][day]['total_area'] += record['area']
                    monthly_data[(year, month)][day]['count'] += 1
        else:
            print(f"警告: 文件 {filename} 不存在，跳过处理")
    
    return monthly_data

def calculate_4month_avg_index(monthly_stats, base_avg_price, target_year, target_month):
    """计算指定月份的4个月移动平均价格指数"""
    indices = []
    
    # 收集目标月份前3个月到目标月份的数据（共4个月）
    for i in range(3, -1, -1):  # 3, 2, 1, 0
        year = target_year
        month = target_month - i
        
        # 处理跨年情况
        while month <= 0:
            month += 12
            year -= 1
        
        key = (year, month)
        if key in monthly_stats:
            index = (monthly_stats[key]['avg_price'] / base_avg_price) * 100
            indices.append(index)
    
    # 必须有完整的4个月数据才计算移动平均值
    if len(indices) == 4:
        return sum(indices) / len(indices)
    else:
        return None

def calculate_price_index(monthly_data, base_year=2016, base_month=1):
    """计算价格指数，以指定年月为基数100"""
    # 计算每月统计数据
    monthly_stats = {}
    
    for (year, month), daily_data in monthly_data.items():

            
        # 检查有效天数是否大于15天
        valid_days = len([day for day, data in daily_data.items() if data['count'] > 0])
        
        if valid_days > 15:
            # 汇总当月所有数据
            month_total_price = 0
            month_total_area = 0
            month_total_records = 0
            
            for day_data in daily_data.values():
                month_total_price += day_data['total_price']
                month_total_area += day_data['total_area']
                month_total_records += day_data['count']
            
            if month_total_area > 0:
                # 计算月平均单价 = 总价 / 总面积
                avg_price = month_total_price / month_total_area
                monthly_stats[(year, month)] = {
                    'total_price': month_total_price,
                    'total_area': month_total_area,
                    'avg_price': avg_price,
                    'valid_days': valid_days,
                    'total_records': month_total_records
                }
    
    # 获取基准月份的平均价格
    base_stats = monthly_stats.get((base_year, base_month))
    if not base_stats:
        print(f"警告: 未找到基准月份 {base_year}年{base_month}月 的数据")
        return {}
    
    base_avg_price = base_stats['avg_price']
    print(f"基准月份 {base_year}年{base_month}月 平均单价: {base_avg_price:.2f} 元/平米")
    print(f"基准月份总价: {base_stats['total_price']:,.0f} 元, 总面积: {base_stats['total_area']:,.0f} 平米")
    
    # 计算价格指数
    price_index = {}
    for (year, month), stats in monthly_stats.items():
        index = (stats['avg_price'] / base_avg_price) * 100
        
        # 计算4个月移动平均的同比涨跌幅
        yoy_change = None
        
        # 计算当前月份的4个月移动平均价格指数
        current_4m_avg = calculate_4month_avg_index(monthly_stats, base_avg_price, year, month)
        
        # 计算去年同月的4个月移动平均价格指数
        prev_year_4m_avg = calculate_4month_avg_index(monthly_stats, base_avg_price, year - 1, month)
        
        if current_4m_avg is not None and prev_year_4m_avg is not None:
            yoy_change = round(((current_4m_avg - prev_year_4m_avg) / prev_year_4m_avg) * 100, 2)
        
        price_index[f"{year}-{month:02d}"] = {
            'year': year,
            'month': month,
            'price_index': round(index, 2),
            'yoy_change': yoy_change,
            'total_price': round(stats['total_price'], 2),
            'total_area': round(stats['total_area'], 2),
            'avg_price': round(stats['avg_price'], 2),
            'valid_days': stats['valid_days'],
            'total_records': stats['total_records']
        }
    
    return price_index

def main():
    """主函数"""
    data_files_dir = 'data_files'
    output_file = 'shanghai_house_price_index.json'
    
    print("开始计算上海房价指数...")
    print(f"数据目录: {data_files_dir}")
    print("基准: 2016年1月 = 100")
    print("条件: 月份有效天数 > 15天\n")
    
    # 计算月度统计数据
    monthly_data = calculate_monthly_stats(data_files_dir)
    print(f"\n共处理 {len(monthly_data)} 个月份的数据")
    
    # 计算价格指数
    price_index = calculate_price_index(monthly_data, base_year=2016, base_month=1)
    
    if price_index:
        # 按时间排序
        sorted_index = dict(sorted(price_index.items(), key=lambda x: (x[1]['year'], x[1]['month'])))
        
        # 输出到JSON文件
        output_data = {
            'base_period': '2016-01',
            'base_index': 100,
            'description': '上海房价指数 (以2016年1月为基数100)',
            'calculation_rule': '只有当月有效天数大于15天才计算指数',
            'data': sorted_index
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n价格指数已保存到: {output_file}")
        print(f"共计算出 {len(price_index)} 个月份的价格指数")
        
        # 自动备份JSON文件到outsource文件夹
        backup_dir = r'C:\Users\17701\github\my_first_repo\stock_info\cache\outsource'
        backup_file = os.path.join(backup_dir, output_file)
        try:
            # 确保备份目录存在
            os.makedirs(backup_dir, exist_ok=True)
            # 复制文件
            shutil.copy2(output_file, backup_file)
            print(f"JSON文件已自动备份到: {backup_file}")
        except Exception as e:
            print(f"备份文件时出错: {e}")
        
        # 显示部分结果
        print("\n部分结果预览:")
        for i, (period, data) in enumerate(sorted_index.items()):
            if i < 10:  # 只显示前10个
                print(f"{period}: 指数 {data['price_index']}, 平均单价 {data['avg_price']} 元/平米, 有效天数 {data['valid_days']}")
            elif i == 10:
                print("...")
                break
        
        # 绘制综合交互式图表（包含价格指数、成交面积和同比涨跌幅）
        plot_index_and_volume(sorted_index)
    else:
        print("未能计算出价格指数，请检查数据")

def plot_yoy_change(price_index):
    """绘制交互式同比涨跌幅图表"""
    # 提取有同比数据的月份
    dates = []
    yoy_changes = []
    month_labels = []
    
    for month_key, data in price_index.items():
        if data['yoy_change'] is not None:
            year, month = month_key.split('-')
            date = dt(int(year), int(month), 1)
            dates.append(date)
            yoy_changes.append(data['yoy_change'])
            month_labels.append(f"{year}年{month}月")
    
    if not dates:
        print("\n没有同比数据可绘制")
        return
    
    # 创建交互式图表
    fig = go.Figure()
    
    # 添加同比涨跌幅线图
    fig.add_trace(go.Scatter(
        x=dates,
        y=yoy_changes,
        mode='lines+markers',
        name='同比涨跌幅',
        line=dict(color='#2E86AB', width=2),
        marker=dict(size=6, color='#2E86AB'),
        hovertemplate='<b>%{customdata}</b><br>' +
                      '同比涨跌幅: %{y:.2f}%<br>' +
                      '<extra></extra>',
        customdata=month_labels
    ))
    
    # 添加零线
    fig.add_hline(y=0, line_dash="dash", line_color="red", opacity=0.7)
    
    # 设置布局
    fig.update_layout(
        title={
            'text': '上海房价指数同比涨跌幅变化趋势（交互式图表）',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18}
        },
        xaxis_title='时间',
        yaxis_title='同比涨跌幅 (%)',
        xaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray',
            tickformat='%Y-%m'
        ),
        yaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray',
            ticksuffix='%'
        ),
        hovermode='x unified',
        width=1200,
        height=600,
        font=dict(family="Microsoft YaHei, SimHei, Arial", size=12)
    )
    
    # 保存为HTML文件
    chart_file = 'shanghai_house_price_yoy_change.html'
    pyo.plot(fig, filename=chart_file, auto_open=False)
    print(f"\n交互式同比涨跌幅图表已保存到: {chart_file}")
    print("提示：在浏览器中打开HTML文件可查看交互式图表，鼠标悬停可显示详细数据")
    
    # 统计信息
    max_increase = max(yoy_changes)
    max_decrease = min(yoy_changes)
    max_increase_date = dates[yoy_changes.index(max_increase)]
    max_decrease_date = dates[yoy_changes.index(max_decrease)]
    
    print(f"\n同比涨跌幅统计:")
    print(f"最大涨幅: {max_increase:.2f}% ({max_increase_date.strftime('%Y年%m月')})")
    print(f"最大跌幅: {max_decrease:.2f}% ({max_decrease_date.strftime('%Y年%m月')})")
    print(f"平均同比变化: {sum(yoy_changes)/len(yoy_changes):.2f}%")

def plot_index_and_volume(price_index):
    """绘制价格指数、同比涨跌幅和成交面积的综合交互式图表"""
    # 提取数据
    dates = []
    price_indices = []
    areas = []    # 成交面积
    yoy_changes = []  # 同比涨跌幅
    month_labels = []
    
    for month_key, data in price_index.items():
        year, month = month_key.split('-')
        date = dt(int(year), int(month), 1)
        dates.append(date)
        price_indices.append(data['price_index'])
        areas.append(data['total_area'])
        yoy_changes.append(data['yoy_change'])
        month_labels.append(f"{year}年{month}月")
    
    # 创建子图
    from plotly.subplots import make_subplots
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('价格指数与成交面积', '同比涨跌幅'),
        specs=[[{"secondary_y": True}], [{"secondary_y": False}]],
        vertical_spacing=0.1,
        row_heights=[0.6, 0.4]
    )
    
    # 第一个子图：价格指数线图（主轴）
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=price_indices,
            mode='lines+markers',
            name='价格指数',
            line=dict(color='#2E86AB', width=3),
            marker=dict(size=6, color='#2E86AB'),
            hovertemplate='<b>%{customdata}</b><br>' +
                          '价格指数: %{y:.2f}<br>' +
                          '<extra></extra>',
            customdata=month_labels
        ),
        row=1, col=1, secondary_y=False
    )
    
    # 第一个子图：成交面积柱状图（次轴）
    fig.add_trace(
        go.Bar(
            x=dates,
            y=areas,
            name='成交面积',
            marker_color='rgba(255, 165, 0, 0.6)',
            hovertemplate='<b>%{customdata}</b><br>' +
                          '成交面积: %{y:,.0f}平米<br>' +
                          '<extra></extra>',
            customdata=month_labels
        ),
        row=1, col=1, secondary_y=True
    )
    
    # 第二个子图：同比涨跌幅线图
    yoy_dates = []
    yoy_values = []
    yoy_labels = []
    for i, yoy in enumerate(yoy_changes):
        if yoy is not None:
            yoy_dates.append(dates[i])
            yoy_values.append(yoy)
            yoy_labels.append(month_labels[i])
    
    fig.add_trace(
        go.Scatter(
            x=yoy_dates,
            y=yoy_values,
            mode='lines+markers',
            name='同比涨跌幅',
            line=dict(color='#FF6B6B', width=2),
            marker=dict(size=5, color='#FF6B6B'),
            hovertemplate='<b>%{customdata}</b><br>' +
                          '同比涨跌幅: %{y:.2f}%<br>' +
                          '<extra></extra>',
            customdata=yoy_labels
        ),
        row=2, col=1
    )
    
    # 添加零线到同比涨跌幅图
    fig.add_hline(y=0, line_dash="dash", line_color="red", opacity=0.7, row=2, col=1)
    
    # 设置轴标题
    fig.update_yaxes(title_text="价格指数", row=1, col=1, secondary_y=False)
    fig.update_yaxes(title_text="成交面积 (平米)", row=1, col=1, secondary_y=True)
    fig.update_yaxes(title_text="同比涨跌幅 (%)", row=2, col=1)
    fig.update_xaxes(title_text="时间", row=2, col=1)
    
    # 设置布局
    fig.update_layout(
        title={
            'text': '上海房价综合分析（交互式图表）',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20}
        },
        width=1400,
        height=900,
        font=dict(family="Microsoft YaHei, SimHei, Arial", size=12),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.1,
            xanchor="center",
            x=0.5
        )
    )
    
    # 设置网格
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
    
    # 保存为HTML文件
    chart_file = 'shanghai_house_price_comprehensive.html'
    pyo.plot(fig, filename=chart_file, auto_open=False)
    print(f"\n综合交互式图表已保存到: {chart_file}")
    print("提示：图表包含价格指数与成交面积（上图）、同比涨跌幅（下图）")
    
    # 统计信息
    max_index = max(price_indices)
    min_index = min(price_indices)
    max_area = max(areas)
    min_area = min(areas)
    
    max_index_date = dates[price_indices.index(max_index)]
    min_index_date = dates[price_indices.index(min_index)]
    max_area_date = dates[areas.index(max_area)]
    min_area_date = dates[areas.index(min_area)]
    
    # 同比涨跌幅统计
    valid_yoy = [y for y in yoy_changes if y is not None]
    if valid_yoy:
        max_yoy = max(valid_yoy)
        min_yoy = min(valid_yoy)
        max_yoy_date = dates[yoy_changes.index(max_yoy)]
        min_yoy_date = dates[yoy_changes.index(min_yoy)]
    
    print(f"\n综合统计信息:")
    print(f"最高价格指数: {max_index:.2f} ({max_index_date.strftime('%Y年%m月')})")
    print(f"最低价格指数: {min_index:.2f} ({min_index_date.strftime('%Y年%m月')})")
    print(f"最大成交面积: {max_area:,.0f}平米 ({max_area_date.strftime('%Y年%m月')})")
    print(f"最小成交面积: {min_area:,.0f}平米 ({min_area_date.strftime('%Y年%m月')})")
    if valid_yoy:
        print(f"最大同比涨幅: {max_yoy:.2f}% ({max_yoy_date.strftime('%Y年%m月')})")
        print(f"最大同比跌幅: {min_yoy:.2f}% ({min_yoy_date.strftime('%Y年%m月')})")
        print(f"平均同比变化: {sum(valid_yoy)/len(valid_yoy):.2f}%")

if __name__ == '__main__':
    main()