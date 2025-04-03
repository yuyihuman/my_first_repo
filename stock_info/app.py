from flask import Flask, render_template, jsonify, request
import data_fetcher

app = Flask(__name__)

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
    # 获取龙虎榜数据
    data = data_fetcher.get_lhb_top10()
    return jsonify(data)

@app.route('/api/stock_finance')
def stock_finance():
    stock_code = request.args.get('code', '')
    if not stock_code:
        return jsonify({'error': '请提供股票代码'})
    
    data = data_fetcher.get_stock_financial_data(stock_code)
    return jsonify(data)

if __name__ == '__main__':
    # 修改host参数为'0.0.0.0'以允许局域网访问
    app.run(host='0.0.0.0', port=8080, debug=True)