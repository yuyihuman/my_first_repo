from xtquant import xtdata
import time
import pandas as pd
import backtrader as bt

# Create a Stratey
class TestStrategy(bt.Strategy):

    def log(self, txt, dt=None):
        ''' Logging function for this strategy'''
        dt = dt or self.datas[0].datetime.datetime(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.dataopen = self.datas[0].open
        self.order = None
        self.open_time = None

    def notify(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed, order.Canceled, order.Margin]:
            if order.isbuy():
                self.log('BUY EXECUTED, %.2f' % order.executed.price)
            elif order.issell():
                self.log('SELL EXECUTED, %.2f' % order.executed.price)

            self.bar_executed = len(self)
        self.order = None

    def next(self):
        self.log('Open, %.2f\tClose, %.2f' % (self.dataopen[0], self.dataclose[0]))

        if self.order:
            return

        if not self.position:
            # 获取当前可用现金
            cash = self.broker.get_cash()
            # 获取当前价格
            current_price = self.dataclose[0]
            # 计算可以买入的股数（全仓）
            size = cash // current_price  # 使用整除以确保为整数股数
            if self.dataclose[0] < self.dataclose[-1]:
                if self.dataclose[-1] < self.dataclose[-2]:
                    self.log('BUY CREATE, %.2f' % self.dataclose[0])
                    self.open_time = self.datas[0].datetime.datetime(0).date()
                    self.order = self.buy(size=size)
        else:
            if len(self) >= (self.bar_executed + 5) and self.datas[0].datetime.datetime(0).date() != self.open_time:
                self.log('SELL CREATE, %.2f' % self.dataclose[0])
                self.order = self.sell(size=self.position.size)

# 设定一个标的列表
code_list = ["000001.SZ","000002.SZ"]
period = '10m'

kline_data = xtdata.get_market_data_ex([], code_list, period=period, start_time='20200101')

for code in code_list:
    kline_data[code]['stime'] = pd.to_datetime(kline_data[code]['stime'], format='%Y%m%d%H%M%S')
    kline_data[code].set_index('stime', inplace=True)
    kline_data[code].rename(columns={
        'open': 'open',
        'high': 'high',
        'low': 'low',
        'close': 'close',
        'volume': 'volume'
    }, inplace=True)
    kline_data[code].to_csv(f"{code}.csv", index=True)

    datafeed = bt.feeds.PandasData(dataname=kline_data[code])
    cerebro = bt.Cerebro()
    cerebro.addstrategy(TestStrategy)
    cerebro.adddata(datafeed)
    cerebro.broker.setcash(100000.0)

    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    cerebro.run()
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # Plot the result
    cerebro.plot()
