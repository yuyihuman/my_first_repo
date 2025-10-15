# coding:utf-8
import time, datetime, traceback, sys, os, logging
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
from xtquant import xtconstant

# 获取当前文件信息
current_file = os.path.basename(__file__)
current_path = os.path.abspath(__file__)

# 创建logs目录
logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# 配置日志系统
# 基于当前文件名生成日志文件名（去掉.py扩展名）
base_filename = os.path.splitext(current_file)[0]
log_filename = f"{base_filename}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
log_filepath = os.path.join(logs_dir, log_filename)

# 配置日志格式和输出
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filepath, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class MyXtQuantTraderCallback(XtQuantTraderCallback):
    def on_disconnected(self):
        """
        连接断开
        :return:
        """
        logger.warning(f'{current_file} - 连接断开回调')

    def on_stock_order(self, order):
        """
        委托回报推送
        :param order: XtOrder对象
        :return:
        """
        logger.info(f'{current_file} - 委托回调')
        logger.info(f'{current_file} - 股票代码: {order.stock_code}, 委托状态: {order.order_status}, 系统委托编号: {order.order_sysid}')

    def on_stock_asset(self, asset):
        """
        资金变动推送
        :param asset: XtAsset对象
        :return:
        """
        logger.info(f'{current_file} - 资金变动回调')
        logger.info(f'{current_file} - 账户ID: {asset.account_id}, 现金: {asset.cash}, 总资产: {asset.total_asset}')

    def on_stock_trade(self, trade):
        """
        成交变动推送
        :param trade: XtTrade对象
        :return:
        """
        logger.info(f'{current_file} - 成交回调')
        logger.info(f'{current_file} - 账户ID: {trade.account_id}, 股票代码: {trade.stock_code}, 委托编号: {trade.order_id}')

    def on_stock_position(self, position):
        """
        持仓变动推送
        :param position: XtPosition对象
        :return:
        """
        logger.info(f'{current_file} - 持仓变动回调')
        logger.info(f'{current_file} - 股票代码: {position.stock_code}, 持仓数量: {position.volume}')

    def on_order_error(self, order_error):
        """
        委托失败推送
        :param order_error:XtOrderError 对象
        :return:
        """
        logger.error(f'{current_file} - 委托失败回调')
        logger.error(f'{current_file} - 委托编号: {order_error.order_id}, 错误ID: {order_error.error_id}, 错误信息: {order_error.error_msg}')

    def on_cancel_error(self, cancel_error):
        """
        撤单失败推送
        :param cancel_error: XtCancelError 对象
        :return:
        """
        logger.error(f'{current_file} - 撤单失败回调')
        logger.error(f'{current_file} - 委托编号: {cancel_error.order_id}, 错误ID: {cancel_error.error_id}, 错误信息: {cancel_error.error_msg}')

    def on_order_stock_async_response(self, response):
        """
        异步下单回报推送
        :param response: XtOrderResponse 对象
        :return:
        """
        logger.info(f'{current_file} - 异步下单回报')
        logger.info(f'{current_file} - 账户ID: {response.account_id}, 委托编号: {response.order_id}, 序号: {response.seq}')

    def on_account_status(self, status):
        """
        :param response: XtAccountStatus 对象
        :return:
        """
        logger.info(f'{current_file} - 账户状态回调')
        logger.info(f'{current_file} - 账户ID: {status.account_id}, 账户类型: {status.account_type}, 状态: {status.status}')

if __name__ == "__main__":
    try:
        # 记录程序启动信息
        logger.info("=" * 80)
        logger.info(f'{current_file} - 交易程序启动')
        logger.info(f'{current_file} - 当前文件: {current_file}')
        logger.info(f'{current_file} - 完整路径: {current_path}')
        logger.info(f'{current_file} - 日志文件: {log_filepath}')
        logger.info("=" * 80)
        
        logger.info(f'{current_file} - 演示测试开始')
        
        # 获取当前 Unix 时间戳（精确到秒）
        unix_time = int(time.time())
        logger.info(f'{current_file} - 生成会话ID: {unix_time}')
        
        # path为mini qmt客户端安装目录下userdata_mini路径
        path = 'C:\\国金证券QMT交易端\\userdata_mini'
        logger.info(f'{current_file} - 客户端路径: {path}')
        
        # session_id为会话编号，策略使用方对于不同的Python策略需要使用不同的会话编号
        session_id = unix_time
        logger.info(f'{current_file} - 设置会话ID: {session_id}')
        xt_trader = XtQuantTrader(path, session_id)
        logger.info(f'{current_file} - 创建XtQuantTrader对象完成')
        
        # 创建资金账号为8882293965的证券账号对象
        acc = StockAccount('8882293965')
        logger.info(f'{current_file} - 创建证券账号: {acc.account_id}')
        
        # StockAccount可以用第二个参数指定账号类型，如沪港通传'HUGANGTONG'，深港通传'SHENGANGTONG'
        # acc = StockAccount('1000000365','STOCK')
        
        # 创建交易回调类对象，并声明接收回调
        callback = MyXtQuantTraderCallback()
        xt_trader.register_callback(callback)
        logger.info(f'{current_file} - 注册交易回调完成')
        
        # 启动交易线程
        xt_trader.start()
        logger.info(f'{current_file} - 启动交易线程完成')
        
        # 建立交易连接，返回0表示连接成功
        connect_result = xt_trader.connect()
        logger.info(f'{current_file} - 建立交易连接结果: {connect_result} (0表示连接成功)')
        
        # 如果连接失败，尝试重连
        if connect_result != 0:
            logger.warning(f'{current_file} - 首次连接失败，尝试重连...')
            time.sleep(2)  # 等待2秒后重试
            connect_result = xt_trader.connect()
            logger.info(f'{current_file} - 重连结果: {connect_result} (0表示连接成功)')
            
            if connect_result != 0:
                logger.warning(f'{current_file} - 重连失败，但程序继续运行，将在定时检查中继续尝试')
        
        # # 对交易回调进行订阅，订阅后可以收到交易主推，返回0表示订阅成功
        # subscribe_result = xt_trader.subscribe(acc)
        # logger.info(f'{current_file} - 订阅交易回调结果: {subscribe_result}')
        # stock_code = '600000.SH'

        # # 使用指定价下单，接口返回订单编号，后续可以用于撤单操作以及查询委托状态
        # logger.info(f'{current_file} - 使用指定价下单:')
        # fix_result_order_id = xt_trader.order_stock(acc, stock_code, xtconstant.STOCK_BUY, 200, xtconstant.FIX_PRICE, 10.5, 'strategy_name', 'remark')
        # logger.info(f'{current_file} - 指定价下单结果: {fix_result_order_id}')

        # # 使用订单编号撤单
        # logger.info(f'{current_file} - 撤单操作:')
        # cancel_order_result = xt_trader.cancel_order_stock(acc, fix_result_order_id)
        # logger.info(f'{current_file} - 撤单结果: {cancel_order_result}')

        # # 使用异步下单接口，接口返回下单请求序号seq，seq可以和on_order_stock_async_response的委托反馈response对应起来
        # logger.info(f'{current_file} - 使用异步下单接口:')
        # async_seq = xt_trader.order_stock_async(acc, stock_code, xtconstant.STOCK_BUY, 200, xtconstant.FIX_PRICE, 10.5, 'strategy_name', 'remark')
        # logger.info(f'{current_file} - 异步下单序号: {async_seq}')

        # 查询证券资产
        logger.info(f'{current_file} - 查询证券资产:')
        asset = xt_trader.query_stock_asset(acc)
        if asset:
            logger.info(f'{current_file} - 资产信息:')
            logger.info(f'{current_file} - 现金: {asset.cash}')
        else:
            logger.warning(f'{current_file} - 未能获取资产信息')

        # # 根据订单编号查询委托
        # logger.info(f'{current_file} - 查询委托:')
        # order = xt_trader.query_stock_order(acc, fix_result_order_id)
        # if order:
        #     logger.info(f'{current_file} - 委托信息:')
        #     logger.info(f'{current_file} - 委托编号: {order.order_id}')

        # # 查询当日所有的委托
        # logger.info(f'{current_file} - 查询所有委托:')
        # orders = xt_trader.query_stock_orders(acc)
        # logger.info(f'{current_file} - 委托数量: {len(orders)}')
        # if len(orders) != 0:
        #     logger.info(f'{current_file} - 最后一笔委托:')
        #     logger.info(f'{current_file} - 股票代码: {orders[-1].stock_code}, 委托数量: {orders[-1].order_volume}, 价格: {orders[-1].price}')

        # # 查询当日所有的成交
        # logger.info(f'{current_file} - 查询所有成交:')
        # trades = xt_trader.query_stock_trades(acc)
        # logger.info(f'{current_file} - 成交数量: {len(trades)}')
        # if len(trades) != 0:
        #     logger.info(f'{current_file} - 最后一笔成交:')
        #     logger.info(f'{current_file} - 股票代码: {trades[-1].stock_code}, 成交数量: {trades[-1].traded_volume}, 成交价格: {trades[-1].traded_price}')

        # 查询当日所有的持仓
        logger.info(f'{current_file} - 查询所有持仓:')
        positions = xt_trader.query_stock_positions(acc)
        logger.info(f'{current_file} - 持仓数量: {len(positions)}')
        if len(positions) != 0:
            logger.info(f'{current_file} - 最后一笔持仓:')
            logger.info(f'{current_file} - 账户ID: {positions[-1].account_id}, 股票代码: {positions[-1].stock_code}, 持仓数量: {positions[-1].volume}')
        else:
            logger.info(f'{current_file} - 当前无持仓')

        # # 根据股票代码查询对应持仓
        # logger.info(f'{current_file} - 查询指定股票持仓:')
        # position = xt_trader.query_stock_position(acc, stock_code)
        # if position:
        #     logger.info(f'{current_file} - 持仓信息:')
        #     logger.info(f'{current_file} - 账户ID: {position.account_id}, 股票代码: {position.stock_code}, 持仓数量: {position.volume}')

        # 定时检查持仓和资金，每5分钟检查一次
        logger.info(f'{current_file} - 开始定时监控，每5分钟检查一次持仓和资金')
        check_interval = 300  # 5分钟 = 300秒
        check_count = 0
        
        try:
            while True:
                check_count += 1
                logger.info(f'\n{"-" * 60}')
                logger.info(f'{current_file} - 第{check_count}次定时检查 ({datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})')
                logger.info(f'{"-" * 60}')
                
                # 检查资金
                logger.info(f'{current_file} - 检查证券资产:')
                asset = xt_trader.query_stock_asset(acc)
                if asset:
                    logger.info(f'{current_file} - 💰 资产信息:')
                    logger.info(f'{current_file} - 现金: {asset.cash:,.2f}')
                    logger.info(f'{current_file} - 总资产: {asset.total_asset:,.2f}')
                    logger.info(f'{current_file} - 可用资金: {asset.cash:,.2f}')
                else:
                    logger.warning(f'{current_file} - ⚠️ 未能获取资产信息')
                
                # 检查持仓
                logger.info(f'{current_file} - 检查所有持仓:')
                positions = xt_trader.query_stock_positions(acc)
                logger.info(f'{current_file} - 📊 持仓数量: {len(positions)}')
                
                if len(positions) != 0:
                    logger.info(f'{current_file} - 📈 持仓详情:')
                    for i, position in enumerate(positions, 1):
                        logger.info(f'{current_file} - 持仓{i}: 股票代码: {position.stock_code}, 持仓数量: {position.volume}, 可用数量: {position.can_use_volume}')
                    
                    # 显示最后一笔持仓的详细信息
                    last_position = positions[-1]
                    logger.info(f'{current_file} - 最新持仓: 账户ID: {last_position.account_id}, 股票代码: {last_position.stock_code}, 持仓数量: {last_position.volume}')
                else:
                    logger.info(f'{current_file} - 📭 当前无持仓')
                
                logger.info(f'{current_file} - ⏰ 等待{check_interval}秒后进行下次检查...')
                
                # 等待5分钟，但每30秒检查一次是否需要退出
                for i in range(check_interval // 30):
                    time.sleep(30)
                    # 这里可以添加其他条件来提前退出循环
                    
        except KeyboardInterrupt:
            logger.info(f'{current_file} - 定时监控被用户中断')
        
        logger.info(f'{current_file} - 程序正常结束')
        
    except KeyboardInterrupt:
        logger.warning(f'{current_file} - 程序被用户中断')
    except Exception as e:
        logger.error(f'{current_file} - 程序执行出错: {str(e)}')
        logger.error(f'{current_file} - 错误详情: {traceback.format_exc()}')
    finally:
        logger.info("=" * 80)
        logger.info(f'{current_file} - 交易程序结束')
        logger.info("=" * 80)
