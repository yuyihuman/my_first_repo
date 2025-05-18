from utils import logger  # 导入共用日志模块

class BuyStrategy:
    @staticmethod
    def simple_ma_buy(code, date, data_loader):
        """
        简单均线买入策略
        :param code: 股票代码
        :param date: 日期字符串
        :param data_loader: 数据加载函数或对象
        :return: 1=买入, 0=不操作
        """
        logger.debug(f"执行买入策略分析: {code}, 时间: {date}")
        df = data_loader(code)
        # 假设df有'time'和'close'列
        df = df[df['time'] <= date]
        if len(df) < 20:
            logger.warning(f"买入策略数据不足: {code}, 时间: {date}, 数据点: {len(df)}")
            return 0
        ma5 = df['close'].tail(5).mean()
        ma20 = df['close'].tail(20).mean()
        logger.debug(f"买入策略指标: {code}, MA5: {ma5:.2f}, MA20: {ma20:.2f}, 差值: {(ma5-ma20):.2f}")
        if ma5 > ma20:
            logger.info(f"生成买入信号: {code}, 时间: {date}, MA5: {ma5:.2f}, MA20: {ma20:.2f}")
            return 1
        return 0

class SellStrategy:
    @staticmethod
    def simple_ma_sell(code, date, data_loader):
        """
        简单均线卖出策略
        :param code: 股票代码
        :param date: 日期字符串
        :param data_loader: 数据加载函数或对象
        :return: -1=卖出, 0=不操作
        """
        logger.debug(f"执行卖出策略分析: {code}, 时间: {date}")
        df = data_loader(code)
        df = df[df['time'] <= date]
        if len(df) < 20:
            logger.warning(f"卖出策略数据不足: {code}, 时间: {date}, 数据点: {len(df)}")
            return 0
        ma5 = df['close'].tail(5).mean()
        ma20 = df['close'].tail(20).mean()
        logger.debug(f"卖出策略指标: {code}, MA5: {ma5:.2f}, MA20: {ma20:.2f}, 差值: {(ma5-ma20):.2f}")
        if ma5 < ma20:
            logger.info(f"生成卖出信号: {code}, 时间: {date}, MA5: {ma5:.2f}, MA20: {ma20:.2f}")
            return -1
        return 0

# 示例数据加载函数
def load_stock_data(code):
    import pandas as pd
    logger.debug(f"加载股票数据: {code}")
    try:
        df = pd.read_csv(f'stock_data/{code}.csv', dtype={'time':str})
        logger.debug(f"成功加载股票数据: {code}, 数据点: {len(df)}")
        return df
    except Exception as e:
        logger.error(f"加载股票数据失败: {code}, 错误: {e}")
        raise

# 示例用法
if __name__ == "__main__":
    code = "600519.SH"
    date = "20240517100000"
    logger.info(f"开始测试策略: {code}, 时间: {date}")
    buy_signal = BuyStrategy.simple_ma_buy(code, date, load_stock_data)
    sell_signal = SellStrategy.simple_ma_sell(code, date, load_stock_data)
    logger.info(f"策略测试结果 - 买入信号: {buy_signal}, 卖出信号: {sell_signal}")
    print(f"买入信号: {buy_signal}, 卖出信号: {sell_signal}")