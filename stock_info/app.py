from flask import Flask, render_template, jsonify, request, send_from_directory
# 导入新的数据模块
from data import (
    ensure_cache_directories,
    get_lhb_top10,
    get_stock_financial_data,
    get_hkstock_data,
    get_northbound_data,
    get_hkstock_finance,
    fetch_macro_china_money_supply
)
import os
import logging

# 创建应用实例
app = Flask(__name__)

# 配置日志
logging.basicConfig(level=logging.INFO)

# 确保缓存目录存在
ensure_cache_directories()

# 设置静态文件缓存时间（1天）
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 86400

# 主页
@app.route('/')
def index():
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

# 港股通北向资金页面
@app.route('/northbound')
def northbound():
    return render_template('northbound.html')

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

# API路由 - 港股通北向资金数据
@app.route('/api/northbound')
def api_northbound():
    """获取北向资金数据的API"""
    refresh = request.args.get('refresh', 'false').lower() == 'true'
    data = get_northbound_data(refresh=refresh)
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

if __name__ == '__main__':
    # 生产环境中关闭调试模式
    debug_mode = False  # 局域网访问时设为False
    app.run(host='0.0.0.0', port=8080, debug=debug_mode)