from flask import Flask, render_template, jsonify, request, send_from_directory
# 导入新的数据模块
from data import (
    ensure_cache_directories,
    get_lhb_top10,
    get_stock_financial_data,
    get_hkstock_data,
    get_hkstock_finance,
    fetch_macro_china_money_supply,
    institutional_holdings_data
)
import os
import logging
# 从logging.handlers中移除RotatingFileHandler导入
# 使用基本的FileHandler

# 创建应用实例
app = Flask(__name__)

# 确保日志目录存在
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 配置日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 清除现有的处理器（避免重复添加）
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_format)

# 创建文件处理器 - 使用FileHandler，模式设为'w'表示覆盖
file_handler = logging.FileHandler(
    os.path.join(log_dir, 'stock_info.log'), 
    mode='w',  # 'w'模式表示覆盖写入
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)
file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_format)

# 添加处理器到logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# 确保缓存目录存在
ensure_cache_directories()

# 设置静态文件缓存时间（开发模式设为0，禁用缓存）
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# 主页
@app.route('/')
def index():
    logger.info("访问主页")
    return render_template('index.html')

# A股个股信息页面
@app.route('/stock_info')
def stock_info():
    return render_template('stock_info.html')

# 龙虎榜页面
@app.route('/lhb')
def lhb():
    return render_template('lhb.html')

# 港股通南向资金页面
@app.route('/hkstock')
def hkstock():
    return render_template('hkstock.html')



# 港股个股信息页面
@app.route('/hkstock_info')
def hkstock_info():
    return render_template('hkstock_info.html')

# 中国宏观经济数据页面
@app.route('/macro_china')
def macro_china():
    return render_template('macro_china.html')

# API路由 - 龙虎榜数据
@app.route('/api/lhb_data')
def lhb_data():
    # 确保缓存目录存在
    ensure_cache_directories()
    # 获取龙虎榜数据
    data = get_lhb_top10()
    return jsonify(data)

# API路由 - A股财务数据
@app.route('/api/stock_finance')
def stock_finance():
    # 确保缓存目录存在
    ensure_cache_directories()
    stock_code = request.args.get('code', '')
    if not stock_code:
        return jsonify({'error': '请提供股票代码'})
    
    data = get_stock_financial_data(stock_code)
    return jsonify(data)

# API路由 - 港股通南向资金数据
@app.route('/api/hkstock')
def api_hkstock_data():
    """获取港股通南向资金数据API"""
    data = get_hkstock_data()
    return jsonify(data)



# API路由 - 港股个股财务数据
@app.route('/api/hkstock_info/<stock_code>')
def api_hkstock_info(stock_code):
    """获取港股个股信息API"""
    try:
        data = get_hkstock_finance(stock_code)
        return jsonify(data)
    except Exception as e:
        app.logger.error(f"获取港股个股信息出错: {e}")
        return jsonify({"error": str(e)}), 500

# API路由 - 中国货币供应量数据
@app.route('/api/macro/money_supply')
def macro_money_supply():
    """获取中国货币供应量数据API"""
    try:
        data = fetch_macro_china_money_supply()
        return jsonify(data)
    except Exception as e:
        app.logger.error(f"获取货币供应量数据时出错: {e}")
        return jsonify({"status": "error", "message": str(e)})

# 工具路由 - 检查静态资源
@app.route('/check_static')
def check_static():
    """检查静态资源是否正确加载"""
    try:
        static_files = {
            'css': [f for f in os.listdir('static/css') if f.endswith('.css')],
            'js': [f for f in os.listdir('static/js') if f.endswith('.js')]
        }
        return jsonify({'status': 'success', 'files': static_files})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# 工具路由 - 本地CDN资源
@app.route('/cdn/<path:filename>')
def serve_cdn(filename):
    """提供本地CDN资源"""
    return send_from_directory('static/cdn', filename)

# 上海房价页面路由
@app.route('/sh_house_price')
def sh_house_price():
    return render_template('sh_house_price.html')

# 获取上海房价图片列表API
@app.route('/api/sh_house_price/images')
def sh_house_price_images():
    try:
        # 图片目录路径
        image_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                'sh_house_price', 'images', 'final')
        
        # 获取所有图片文件
        image_files = []
        if os.path.exists(image_dir):
            for file in os.listdir(image_dir):
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    # 去掉扩展名
                    image_name = os.path.splitext(file)[0]
                    image_files.append(image_name)
        
        return jsonify({
            'status': 'success',
            'images': sorted(image_files)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

# 提供图片文件
@app.route('/sh_house_price/images/<image_name>')
def serve_house_price_image(image_name):
    image_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                            'sh_house_price', 'images', 'final')
    
    # 查找匹配的图片文件（不考虑扩展名）
    for file in os.listdir(image_dir):
        file_name_without_ext = os.path.splitext(file)[0]
        if file_name_without_ext == image_name:
            return send_from_directory(image_dir, file)
    
    return "图片未找到", 404

# 获取上海房价数据API
@app.route('/api/sh_house_price/data')
def sh_house_price_data():
    try:
        import json
        # 读取上海房价数据文件
        data_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                'cache', 'outsource', 'shanghai_house_price_index.json')
        
        if not os.path.exists(data_file):
            return jsonify({
                'status': 'error',
                'message': '数据文件不存在'
            })
        
        with open(data_file, 'r', encoding='utf-8') as f:
            house_data = json.load(f)
        
        # 获取最新数据日期
        latest_data_date = house_data.get('latest_data_date', '')
        
        # 提取数据用于图表
        chart_data = []
        for date_key, data_item in house_data['data'].items():
            chart_data.append({
                'date': date_key,
                'year': data_item['year'],
                'month': data_item['month'],
                'price_index': data_item['price_index'],
                'total_area': data_item['total_area'],
                'avg_price': data_item['avg_price'],
                'yoy_change': data_item['yoy_change']
            })
        
        # 按日期排序
        chart_data.sort(key=lambda x: (x['year'], x['month']))
        
        # 对最新月份的成交量进行估算（如果是当月数据且不完整）
        if chart_data and latest_data_date:
            latest_item = chart_data[-1]
            latest_year = latest_item['year']
            latest_month = latest_item['month']
            
            # 解析最新数据日期
            try:
                from datetime import datetime
                latest_date = datetime.strptime(latest_data_date, '%Y.%m.%d')
                
                # 如果最新数据是当月的，进行估算
                if latest_date.year == latest_year and latest_date.month == latest_month:
                    # 计算当月总天数
                    import calendar
                    days_in_month = calendar.monthrange(latest_year, latest_month)[1]
                    
                    # 计算已过天数
                    days_passed = latest_date.day
                    
                    # 估算全月成交量（按比例放大）
                    if days_passed > 0 and days_passed < days_in_month:
                        actual_area = latest_item['total_area']  # 保存实际值
                        estimated_total_area = actual_area * (days_in_month / days_passed)
                        latest_item['actual_value'] = actual_area  # 实际值
                        latest_item['total_area'] = round(estimated_total_area, 2)  # 估算总值
                        latest_item['is_estimated'] = True
                    else:
                        latest_item['is_estimated'] = False
                else:
                    latest_item['is_estimated'] = False
            except:
                latest_item['is_estimated'] = False
        
        return jsonify({
            'status': 'success',
            'data': chart_data,
            'base_period': house_data['base_period'],
            'base_index': house_data['base_index'],
            'description': house_data['description'],
            'latest_data_date': latest_data_date
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })



# 提供图片文件
@app.route('/southbound_holdings/images/<image_name>')
def serve_southbound_holdings_image(image_name):
    image_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                            'stockapi', 'charts')
    
    # 查找匹配的图片文件（不考虑扩展名）
    for file in os.listdir(image_dir):
        file_name_without_ext = os.path.splitext(file)[0]
        if file_name_without_ext == image_name:
            return send_from_directory(image_dir, file)
    
    return "图片未找到", 404

# 机构持股页面路由
@app.route('/institutional_holdings')
def institutional_holdings():
    return render_template('institutional_holdings.html')

# API路由 - 机构持股数据
@app.route('/api/institutional_holdings/report_dates')
def get_available_report_dates():
    """获取可用报告期列表API"""
    try:
        dates = institutional_holdings_data.get_available_report_dates()
        return jsonify({
            'status': 'success',
            'data': dates
        })
    except Exception as e:
        logger.error(f"获取可用报告期失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/institutional_holdings/<category>')
def get_institutional_holdings_data(category):
    """获取机构持股数据API"""
    try:
        # 获取报告期参数
        report_date = request.args.get('report_date')
        if report_date:
            try:
                report_date = int(report_date)
            except ValueError:
                return jsonify({
                    'status': 'error',
                    'message': '报告期格式错误，应为整数格式如20240930'
                }), 400
        
        data = institutional_holdings_data.get_top_holdings(category, report_date=report_date)
        return jsonify({
            'status': 'success',
            'data': data,
            'category': category,
            'report_date': report_date
        })
    except Exception as e:
        logger.error(f"获取机构持股数据失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# API路由 - 机构持股趋势数据
@app.route('/api/institutional_holdings/<category>/<stock_code>/trend')
def api_institutional_holdings_trend(category, stock_code):
    """获取机构持股趋势数据API"""
    try:
        data = institutional_holdings_data.get_stock_trend(category, stock_code)
        return jsonify({
            'status': 'success',
            'data': data,
            'category': category,
            'stock_code': stock_code
        })
    except Exception as e:
        app.logger.error(f"获取机构持股趋势数据出错: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# API路由 - 个股详细持股信息
@app.route('/api/stock_holdings_detail/<stock_code>')
def api_stock_holdings_detail(stock_code):
    """获取个股详细持股信息API - 展示各个报告期和不同机构的持股情况"""
    try:
        data = institutional_holdings_data.get_stock_holdings_detail(stock_code)
        return jsonify({
            'status': 'success',
            'data': data,
            'stock_code': stock_code
        })
    except Exception as e:
        app.logger.error(f"获取个股详细持股信息出错: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    # 生产环境中关闭调试模式
    debug_mode = False  # 局域网访问时设为False
    app.run(host='0.0.0.0', port=8080, debug=debug_mode)