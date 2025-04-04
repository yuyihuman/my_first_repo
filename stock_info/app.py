from flask import Flask, render_template, jsonify, request, send_from_directory
import data_fetcher
import os

# 创建应用实例
app = Flask(__name__)

# 确保缓存目录存在
data_fetcher.ensure_cache_directories()

# 设置静态文件缓存时间（1天）
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 86400

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/stock_info')
def stock_info():
    return render_template('stock_info.html')

@app.route('/lhb')
def lhb():
    return render_template('lhb.html')

@app.route('/api/lhb_data')
def lhb_data():
    # 确保缓存目录存在
    data_fetcher.ensure_cache_directories()
    # 获取龙虎榜数据
    data = data_fetcher.get_lhb_top10()
    return jsonify(data)

@app.route('/api/stock_finance')
def stock_finance():
    # 确保缓存目录存在
    data_fetcher.ensure_cache_directories()
    stock_code = request.args.get('code', '')
    if not stock_code:
        return jsonify({'error': '请提供股票代码'})
    
    data = data_fetcher.get_stock_financial_data(stock_code)
    return jsonify(data)

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

# 添加本地CDN资源路由（可选，如果您决定本地化CDN资源）
@app.route('/cdn/<path:filename>')
def serve_cdn(filename):
    return send_from_directory('static/cdn', filename)

if __name__ == '__main__':
    # 生产环境中关闭调试模式
    debug_mode = False  # 局域网访问时设为False
    app.run(host='0.0.0.0', port=8080, debug=debug_mode)