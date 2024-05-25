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
            if self.dataclose[0] < self.dataclose[-1]:
                if self.dataclose[-1] < self.dataclose[-2]:
                    self.log('BUY CREATE, %.2f' % self.dataclose[0])
                    self.order = self.buy()
        else:
            if len(self) >= (self.bar_executed + 5):
                self.log('SELL CREATE, %.2f' % self.dataclose[0])
                self.order = self.sell()

# 设定一个标的列表
code_list = ["000001.SZ"]
period = '10m'

for i in code_list:
    xtdata.subscribe_quote(i, period=period, count=-1)
time.sleep(1)
kline_data = xtdata.get_market_data_ex([], code_list, period=period, start_time='20240101')
print(kline_data["000001.SZ"])

kline_data["000001.SZ"]['stime'] = pd.to_datetime(kline_data["000001.SZ"]['stime'], format='%Y%m%d%H%M%S')
kline_data["000001.SZ"].set_index('stime', inplace=True)
kline_data["000001.SZ"].rename(columns={
    'open': 'open',
    'high': 'high',
    'low': 'low',
    'close': 'close',
    'volume': 'volume'
}, inplace=True)

datafeed = bt.feeds.PandasData(dataname=kline_data["000001.SZ"])
cerebro = bt.Cerebro()
cerebro.addstrategy(TestStrategy)
cerebro.adddata(datafeed)
cerebro.broker.setcash(100000.0)

print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
cerebro.run()
print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

# Plot the result
cerebro.plot()
