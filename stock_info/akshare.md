龙虎榜详情
接口: stock_lhb_detail_em

目标地址: https://data.eastmoney.com/stock/tradedetail.html

描述: 东方财富网-数据中心-龙虎榜单-龙虎榜详情

限量: 单次返回所有历史数据

输入参数

名称	类型	描述
start_date	str	start_date="20220314"
end_date	str	end_date="20220315"
输出参数

名称	类型	描述
序号	int64	-
代码	object	-
名称	object	-
上榜日	object	-
解读	object	-
收盘价	float64	-
涨跌幅	float64	注意单位: %
龙虎榜净买额	float64	注意单位: 元
龙虎榜买入额	float64	注意单位: 元
龙虎榜卖出额	float64	注意单位: 元
龙虎榜成交额	float64	注意单位: 元
市场总成交额	int64	注意单位: 元
净买额占总成交比	float64	注意单位: %
成交额占总成交比	float64	注意单位: %
换手率	float64	注意单位: %
流通市值	float64	注意单位: 元
上榜原因	object	-
上榜后1日	float64	注意单位: %
上榜后2日	float64	注意单位: %
上榜后5日	float64	注意单位: %
上榜后10日	float64	注意单位: %


接口示例

import akshare as ak

stock_lhb_detail_em_df = ak.stock_lhb_detail_em(start_date="20230403", end_date="20230417")
print(stock_lhb_detail_em_df)


数据示例

      序号  代码    名称    上榜日  ...     上榜后1日      上榜后2日      上榜后5日    上榜后10日
0      1  000021   深科技  2023-04-06  ... -1.304348  -0.193237  -8.212560       NaN
1      2  000021   深科技  2023-04-03  ...  2.338227  12.561175  11.201740  7.667210
2      3  000021   深科技  2023-04-03  ...  2.338227  12.561175  11.201740  7.667210
3      4  000032  深桑达A  2023-04-06  ...  2.087576  -2.214868  -2.265784       NaN
4      5  000063  中兴通讯  2023-04-07  ... -3.783784  -5.270270  -7.027027       NaN
..   ...     ...   ...         ...  ...       ...        ...        ...       ...
630  631  688698  伟创电气  2023-04-12  ... -4.407407  -2.592593        NaN       NaN
631  632  688787  海天瑞声  2023-04-10  ...  2.028249   5.644068   6.073446       NaN
632  633  873593  鼎智科技  2023-04-17  ... -7.805655        NaN        NaN       NaN
633  634  900915  中路B股  2023-04-12  ...  2.981030   1.490515        NaN       NaN
634  635  900915  中路B股  2023-04-03  ...  5.807365   3.824363  12.039660  3.399433


历史行情数据-东财
接口: stock_zh_a_hist

目标地址: https://quote.eastmoney.com/concept/sh603777.html?from=classic(示例)

描述: 东方财富-沪深京 A 股日频率数据; 历史数据按日频率更新, 当日收盘价请在收盘后获取

限量: 单次返回指定沪深京 A 股上市公司、指定周期和指定日期间的历史行情日频率数据

输入参数

名称	类型	描述
symbol	str	symbol='603777';
period	str	period='daily'; choice of {'daily', 'weekly', 'monthly'}
start_date	str	start_date='20210301'; 开始查询的日期
end_date	str	end_date='20210616'; 结束查询的日期
adjust	str	默认返回不复权的数据; qfq: 返回前复权后的数据; hfq: 返回后复权后的数据
timeout	float	timeout=None; 默认不设置超时参数
股票数据复权

为何要复权：由于股票存在配股、分拆、合并和发放股息等事件，会导致股价出现较大的缺口。 若使用不复权的价格处理数据、计算各种指标，将会导致它们失去连续性，且使用不复权价格计算收益也会出现错误。 为了保证数据连贯性，常通过前复权和后复权对价格序列进行调整。

前复权：保持当前价格不变，将历史价格进行增减，从而使股价连续。 前复权用来看盘非常方便，能一眼看出股价的历史走势，叠加各种技术指标也比较顺畅，是各种行情软件默认的复权方式。 这种方法虽然很常见，但也有两个缺陷需要注意。

2.1 为了保证当前价格不变，每次股票除权除息，均需要重新调整历史价格，因此其历史价格是时变的。 这会导致在不同时点看到的历史前复权价可能出现差异。

2.2 对于有持续分红的公司来说，前复权价可能出现负值。

后复权：保证历史价格不变，在每次股票权益事件发生后，调整当前的股票价格。 后复权价格和真实股票价格可能差别较大，不适合用来看盘。 其优点在于，可以被看作投资者的长期财富增长曲线，反映投资者的真实收益率情况。

在量化投资研究中普遍采用后复权数据。

输出参数-历史行情数据

名称	类型	描述
日期	object	交易日
股票代码	object	不带市场标识的股票代码
开盘	float64	开盘价
收盘	float64	收盘价
最高	float64	最高价
最低	float64	最低价
成交量	int64	注意单位: 手
成交额	float64	注意单位: 元
振幅	float64	注意单位: %
涨跌幅	float64	注意单位: %
涨跌额	float64	注意单位: 元
换手率	float64	注意单位: %
接口示例-历史行情数据-不复权

import akshare as ak

stock_zh_a_hist_df = ak.stock_zh_a_hist(symbol="000001", period="daily", start_date="20170301", end_date='20240528', adjust="")
print(stock_zh_a_hist_df)


数据示例-历史行情数据-不复权

            日期    股票代码   开盘   收盘  ... 振幅  涨跌幅  涨跌额 换手率
0     2017-03-01  000001   9.49   9.49  ...  0.84  0.11  0.01  0.21
1     2017-03-02  000001   9.51   9.43  ...  1.26 -0.63 -0.06  0.24
2     2017-03-03  000001   9.41   9.40  ...  0.74 -0.32 -0.03  0.20
3     2017-03-06  000001   9.40   9.45  ...  0.74  0.53  0.05  0.24
4     2017-03-07  000001   9.44   9.45  ...  0.63  0.00  0.00  0.17
...          ...     ...    ...    ...  ...   ...   ...   ...   ...
1755  2024-05-22  000001  11.56  11.56  ...  2.42  0.09  0.01  1.09
1756  2024-05-23  000001  11.53  11.40  ...  1.90 -1.38 -0.16  0.95
1757  2024-05-24  000001  11.37  11.31  ...  1.67 -0.79 -0.09  0.72
1758  2024-05-27  000001  11.31  11.51  ...  1.95  1.77  0.20  0.75
1759  2024-05-28  000001  11.50  11.40  ...  1.91 -0.96 -0.11  0.62
[1760 rows x 12 columns]


接口示例-历史行情数据-前复权

import akshare as ak

stock_zh_a_hist_df = ak.stock_zh_a_hist(symbol="000001", period="daily", start_date="20170301", end_date='20240528', adjust="qfq")
print(stock_zh_a_hist_df)


数据示例-历史行情数据-前复权

           日期    股票代码   开盘    收盘  ...  振幅  涨跌幅  涨跌额 换手率
0     2017-03-01  000001   8.14   8.14  ...  0.98  0.12  0.01  0.21
1     2017-03-02  000001   8.16   8.08  ...  1.47 -0.74 -0.06  0.24
2     2017-03-03  000001   8.06   8.05  ...  0.87 -0.37 -0.03  0.20
3     2017-03-06  000001   8.05   8.10  ...  0.87  0.62  0.05  0.24
4     2017-03-07  000001   8.09   8.10  ...  0.74  0.00  0.00  0.17
...          ...     ...    ...    ...  ...   ...   ...   ...   ...
1755  2024-05-22  000001  11.56  11.56  ...  2.42  0.09  0.01  1.09
1756  2024-05-23  000001  11.53  11.40  ...  1.90 -1.38 -0.16  0.95
1757  2024-05-24  000001  11.37  11.31  ...  1.67 -0.79 -0.09  0.72
1758  2024-05-27  000001  11.31  11.51  ...  1.95  1.77  0.20  0.75
1759  2024-05-28  000001  11.50  11.40  ...  1.91 -0.96 -0.11  0.62
[1760 rows x 12 columns]


接口示例-历史行情数据-后复权

import akshare as ak

stock_zh_a_hist_df = ak.stock_zh_a_hist(symbol="000001", period="daily", start_date="20170301", end_date='20240528', adjust="hfq")
print(stock_zh_a_hist_df)


数据示例-历史行情数据-后复权

           日期    股票代码   开盘     收盘  ...    振幅   涨跌幅   涨跌额 换手率
0     2017-03-01  000001  1575.20  1575.20  ...  0.83  0.10   1.63  0.21
1     2017-03-02  000001  1578.45  1565.45  ...  1.24 -0.62  -9.75  0.24
2     2017-03-03  000001  1562.20  1560.57  ...  0.73 -0.31  -4.88  0.20
3     2017-03-06  000001  1560.57  1568.70  ...  0.73  0.52   8.13  0.24
4     2017-03-07  000001  1567.07  1568.70  ...  0.62  0.00   0.00  0.17
...          ...     ...      ...      ...  ...   ...   ...    ...   ...
1755  2024-05-22  000001  2131.04  2131.04  ...  2.14  0.08   1.62  1.09
1756  2024-05-23  000001  2126.17  2105.04  ...  1.68 -1.22 -26.00  0.95
1757  2024-05-24  000001  2100.16  2090.41  ...  1.47 -0.69 -14.63  0.72
1758  2024-05-27  000001  2090.41  2122.92  ...  1.71  1.56  32.51  0.75
1759  2024-05-28  000001  2121.29  2105.04  ...  1.68 -0.84 -17.88  0.62
[1760 rows x 12 columns]


财务报表-同花顺
资产负债表
接口: stock_financial_debt_ths

目标地址: https://basic.10jqka.com.cn/new/000063/finance.html

描述: 同花顺-财务指标-资产负债表

限量: 单次获取资产负债表所有历史数据

输入参数

名称	类型	描述
symbol	str	symbol="000063"; 股票代码
indicator	str	indicator="按报告期"; choice of {"按报告期", "按年度", "按单季度"}


输出参数

Data columns (total 81 columns):
 #   Column                  Non-Null Count  Dtype
---  ------                  --------------  -----
 0   报告期                     31 non-null     int64
 1   报表核心指标                  31 non-null     object
 2   *所有者权益（或股东权益）合计         31 non-null     object
 3   *资产合计                   31 non-null     object
 4   *负债合计                   31 non-null     object
 5   *归属于母公司所有者权益合计          31 non-null     object
 6   报表全部指标                  31 non-null     object
 7   流动资产                    31 non-null     object
 8   货币资金                    31 non-null     object
 9   交易性金融资产                 31 non-null     object
 10  应收票据及应收账款               31 non-null     object
 11  其中：应收票据                 31 non-null     object
 12  应收账款                    31 non-null     object
 13  预付款项                    31 non-null     object
 14  其他应收款合计                 31 non-null     object
 15  其中：应收利息                 31 non-null     object
 16  其他应收款                   31 non-null     object
 17  存货                      31 non-null     object
 18  划分为持有待售的资产              31 non-null     object
 19  一年内到期的非流动资产             31 non-null     object
 20  其他流动资产                  31 non-null     object
 21  总现金                     31 non-null     object
 22  流动资产合计                  31 non-null     object
 23  非流动资产                   31 non-null     object
 24  可供出售金融资产                31 non-null     object
 25  持有至到期投资                 31 non-null     object
 26  长期股权投资                  31 non-null     object
 27  其他非流动金融资产               31 non-null     object
 28  投资性房地产                  31 non-null     object
 29  固定资产合计                  31 non-null     object
 30  其中：固定资产                 31 non-null     object
 31  固定资产清理                  31 non-null     object
 32  在建工程合计                  31 non-null     object
 33  其中：在建工程                 31 non-null     object
 34  无形资产                    31 non-null     object
 35  商誉                      31 non-null     object
 36  长期待摊费用                  31 non-null     object
 37  递延所得税资产                 31 non-null     object
 38  其他非流动资产                 31 non-null     object
 39  非流动资产合计                 31 non-null     object
 40  资产合计                    31 non-null     object
 41  流动负债                    31 non-null     object
 42  短期借款                    31 non-null     object
 43  以公允价值计量且其变动计入当期损益的金融负债  31 non-null     object
 44  衍生金融负债                  31 non-null     object
 45  应付票据及应付账款               31 non-null     object
 46  其中：应付票据                 31 non-null     object
 47  应付账款                    31 non-null     object
 48  预收款项                    31 non-null     object
 49  合同负债                    31 non-null     object
 50  应付职工薪酬                  31 non-null     object
 51  应交税费                    31 non-null     object
 52  其他应付款合计                 31 non-null     object
 53  其中：应付利息                 31 non-null     object
 54  应付股利                    31 non-null     object
 55  其他应付款                   31 non-null     object
 56  一年内到期的非流动负债             31 non-null     object
 57  流动负债合计                  31 non-null     object
 58  非流动负债                   31 non-null     object
 59  长期借款                    31 non-null     object
 60  应付债券                    31 non-null     object
 61  长期应付款合计                 31 non-null     object
 62  其中：长期应付款                31 non-null     object
 63  专项应付款                   31 non-null     object
 64  预计负债                    31 non-null     object
 65  递延所得税负债                 31 non-null     object
 66  递延收益-非流动负债              31 non-null     object
 67  其他非流动负债                 31 non-null     object
 68  非流动负债合计                 31 non-null     object
 69  负债合计                    31 non-null     object
 70  所有者权益（或股东权益）            31 non-null     object
 71  实收资本（或股本）               31 non-null     object
 72  资本公积                    31 non-null     object
 73  减：库存股                   31 non-null     object
 74  其他综合收益                  31 non-null     object
 75  盈余公积                    31 non-null     object
 76  未分配利润                   31 non-null     object
 77  归属于母公司所有者权益合计           31 non-null     object
 78  少数股东权益                  31 non-null     object
 79  所有者权益（或股东权益）合计          31 non-null     object
 80  负债和所有者权益（或股东权益）合计       31 non-null     object


接口示例

import akshare as ak

stock_financial_debt_ths_df = ak.stock_financial_debt_ths(symbol="000063", indicator="按单季度")
print(stock_financial_debt_ths_df)


数据示例

     报告期 报表核心指标 *所有者权益（或股东权益）合计  ...    少数股东权益 所有者权益（或股东权益）合计 负债和所有者权益（或股东权益）合计
0   2022                595.43亿  ...     9.02亿        595.43亿          1809.54亿
1   2021                532.88亿  ...    18.06亿        532.88亿          1687.63亿
2   2020                461.23亿  ...    28.26亿        461.23亿          1506.35亿
3   2019                379.54亿  ...    28.75亿        379.54亿          1412.02亿
4   2018                329.61亿  ...    38.11亿        329.61亿          1293.51亿
5   2017                453.80亿  ...    44.12亿        453.80亿          1439.62亿
6   2016                408.85亿  ...    51.63亿        408.85亿          1416.41亿
7   2015                433.49亿  ...    43.67亿        433.49亿          1248.32亿
8   2014                262.93亿  ...    14.14亿        262.93亿          1062.14亿
9   2013                236.26亿  ...    10.93亿        236.26亿          1000.79亿
10  2012                225.93亿  ...    11.36亿        225.93亿          1074.46亿
11  2011                262.89亿  ...    20.57亿        262.89亿          1053.68亿
12  2010                249.62亿  ...    18.68亿        249.62亿           841.52亿
13  2009                179.49亿  ...    11.24亿        179.49亿           683.42亿
14  2008                151.84亿  ...     9.34亿        151.84亿           508.66亿
15  2007                128.88亿  ...     7.51亿        128.88亿           391.73亿
16  2006                113.26亿  ...     5.62亿        113.26亿           257.61亿
17  2005                105.96亿  ...     4.71亿        105.96亿           217.79亿
18  2004                 96.39亿  ...     4.65亿         96.39亿           208.30亿
19  2003                 52.77亿  ...     2.33亿         52.77亿           157.67亿
20  2002                 46.04亿  ...     2.17亿         46.04亿           122.17亿
21  2001                 39.18亿  ...  9910.63万         39.18亿            90.55亿
22  2000                 19.50亿  ...  6403.16万         19.50亿            63.21亿
23  1999                 15.79亿  ...  4952.78万         15.79亿            33.85亿
24  1998                  9.60亿  ...  2223.74万          9.60亿            21.94亿
25  1997                  7.01亿  ...   589.60万          7.01亿            13.57亿
26  1996                  1.30亿  ...    10.00万          1.30亿             3.83亿
27  1995               7839.06万  ...     False       7839.06万             2.36亿
28  1994               4254.78万  ...     False       4254.78万             1.45亿
[29 rows x 80 columns]


利润表
接口: stock_financial_benefit_ths

目标地址: https://basic.10jqka.com.cn/new/000063/finance.html

描述: 同花顺-财务指标-利润表

限量: 单次获取利润表所有历史数据

输入参数

名称	类型	描述
symbol	str	symbol="000063"; 股票代码
indicator	str	indicator="按报告期"; choice of {"按报告期", "按年度", "按单季度"}

输出参数

 #   Column             Non-Null Count  Dtype
---  ------             --------------  -----
 0   报告期                92 non-null     object
 1   报表核心指标             92 non-null     object
 2   *净利润               92 non-null     object
 3   *营业总收入             92 non-null     object
 4   *营业总成本             92 non-null     object
 5   *归属于母公司所有者的净利润     92 non-null     object
 6   *扣除非经常性损益后的净利润     92 non-null     object
 7   报表全部指标             92 non-null     object
 8   一、营业总收入            92 non-null     object
 9   其中：营业收入            92 non-null     object
 10  二、营业总成本            92 non-null     object
 11  其中：营业成本            92 non-null     object
 12  营业税金及附加            92 non-null     object
 13  销售费用               92 non-null     object
 14  管理费用               92 non-null     object
 15  研发费用               70 non-null     object
 16  财务费用               92 non-null     object
 17  其中：利息费用            46 non-null     object
 18  利息收入               46 non-null     object
 19  资产减值损失             80 non-null     object
 20  信用减值损失             43 non-null     object
 21  加：公允价值变动收益         77 non-null     object
 22  投资收益               90 non-null     object
 23  其中：联营企业和合营企业的投资收益  72 non-null     object
 24  资产处置收益             35 non-null     object
 25  其他收益               47 non-null     object
 26  三、营业利润             92 non-null     object
 27  加：营业外收入            92 non-null     object
 28  减：营业外支出            92 non-null     object
 29  其中：非流动资产处置损失       52 non-null     object
 30  四、利润总额             92 non-null     object
 31  减：所得税费用            92 non-null     object
 32  五、净利润              92 non-null     object
 33  （一）持续经营净利润         44 non-null     object
 34  归属于母公司所有者的净利润      92 non-null     object
 35  少数股东损益             92 non-null     object
 36  扣除非经常性损益后的净利润      92 non-null     object
 37  六、每股收益             92 non-null     object
 38  （一）基本每股收益          80 non-null     object
 39  （二）稀释每股收益          80 non-null     object
 40  七、其他综合收益           71 non-null     object
 41  归属母公司所有者的其他综合收益    56 non-null     object
 42  八、综合收益总额           71 non-null     object
 43  归属于母公司股东的综合收益总额    71 non-null     object
 44  归属于少数股东的综合收益总额     71 non-null     object


接口示例

import akshare as ak

stock_financial_benefit_ths_df = ak.stock_financial_benefit_ths(symbol="000063", indicator="按单季度")
print(stock_financial_benefit_ths_df)


数据示例

           报告期 报表核心指标      *净利润  ... 八、综合收益总额 归属于母公司股东的综合收益总额 归属于少数股东的综合收益总额
0   2023-09-30           77.57亿  ...   77.05亿          77.94亿      -8842.60万
1   2023-06-30           53.92亿  ...   53.41亿          54.24亿      -8317.50万
2   2023-03-31           26.14亿  ...   24.85亿          25.17亿      -3237.00万
3   2022-12-31           77.92亿  ...   77.24亿          80.15亿         -2.90亿
4   2022-09-30           66.90亿  ...   66.52亿          67.88亿         -1.36亿
..         ...    ...       ...  ...      ...             ...            ...
95  1997-12-31            1.21亿  ...    False           False          False
96  1997-06-30         4124.14万  ...    False           False          False
97  1996-12-31         9905.67万  ...    False           False          False
98  1995-12-31         7314.86万  ...    False           False          False
99  1994-12-31         8071.26万  ...    False           False          False
[100 rows x 45 columns]


现金流量表
接口: stock_financial_cash_ths

目标地址: https://basic.10jqka.com.cn/new/000063/finance.html

描述: 同花顺-财务指标-现金流量表

限量: 单次获取现金流量表所有历史数据

输入参数

名称	类型	描述
symbol	str	symbol="000063"; 股票代码
indicator	str	indicator="按报告期"; choice of {"按报告期", "按年度", "按单季度"}

输出参数

 #   Column                     Non-Null Count  Dtype
---  ------                     --------------  -----
 0   报告期                        88 non-null     object
 1   报表核心指标                     88 non-null     object
 2   *现金及现金等价物净增加额              76 non-null     object
 3   *经营活动产生的现金流量净额             88 non-null     object
 4   *投资活动产生的现金流量净额             88 non-null     object
 5   *筹资活动产生的现金流量净额             88 non-null     object
 6   *期末现金及现金等价物余额              79 non-null     object
 7   报表全部指标                     88 non-null     object
 8   一、经营活动产生的现金流量              88 non-null     object
 9   销售商品、提供劳务收到的现金             88 non-null     object
 10  收到的税费与返还                   88 non-null     object
 11  收到其他与经营活动有关的现金             88 non-null     object
 12  经营活动现金流入小计                 88 non-null     object
 13  购买商品、接受劳务支付的现金             88 non-null     object
 14  支付给职工以及为职工支付的现金            88 non-null     object
 15  支付的各项税费                    88 non-null     object
 16  支付其他与经营活动有关的现金             88 non-null     object
 17  经营活动现金流出小计                 88 non-null     object
 18  经营活动产生的现金流量净额              88 non-null     object
 19  二、投资活动产生的现金流量              88 non-null     object
 20  收回投资收到的现金                  72 non-null     object
 21  取得投资收益收到的现金                79 non-null     object
 22  处置固定资产、无形资产和其他长期资产收回的现金净额  87 non-null     object
 23  处置子公司及其他营业单位收到的现金净额        38 non-null     object
 24  收到其他与投资活动有关的现金             25 non-null     object
 25  投资活动现金流入小计                 87 non-null     object
 26  购建固定资产、无形资产和其他长期资产支付的现金    88 non-null     object
 27  投资支付的现金                    86 non-null     object
 28  取得子公司及其他营业单位支付的现金净额        22 non-null     object
 29  支付其他与投资活动有关的现金             32 non-null     object
 30  投资活动现金流出小计                 88 non-null     object
 31  投资活动产生的现金流量净额              88 non-null     object
 32  三、筹资活动产生的现金流量              88 non-null     object
 33  吸收投资收到的现金                  70 non-null     object
 34  其中：子公司吸收少数股东投资收到的现金        55 non-null     object
 35  取得借款收到的现金                  88 non-null     object
 36  发行债券收到的现金                  25 non-null     object
 37  收到其他与筹资活动有关的现金             32 non-null     object
 38  筹资活动现金流入小计                 88 non-null     object
 39  偿还债务支付的现金                  88 non-null     object
 40  分配股利、利润或偿付利息支付的现金          88 non-null     object
 41  其中：子公司支付给少数股东的股利、利润        52 non-null     object
 42  支付其他与筹资活动有关的现金             42 non-null     object
 43  筹资活动现金流出小计                 88 non-null     object
 44  筹资活动产生的现金流量净额              88 non-null     object
 45  四、汇率变动对现金及现金等价物的影响         79 non-null     object
 46  五、现金及现金等价物净增加额             76 non-null     object
 47  加：期初现金及现金等价物余额             79 non-null     object
 48  六、期末现金及现金等价物余额             79 non-null     object
 49  补充资料：                      88 non-null     object
 50  1、将净利润调节为经营活动现金流量：         88 non-null     object
 51  净利润                        31 non-null     object
 52  加：资产减值准备                   31 non-null     object
 53  固定资产折旧、油气资产折耗、生产性生物资产折旧    31 non-null     object
 54  无形资产摊销                     31 non-null     object
 55  长期待摊费用摊销                   31 non-null     object
 56  处置固定资产、无形资产和其他长期资产的损失      30 non-null     object
 57  固定资产报废损失                   28 non-null     object
 58  公允价值变动损失                   22 non-null     object
 59  财务费用                       31 non-null     object
 60  投资损失                       30 non-null     object
 61  递延所得税资产减少                  22 non-null     object
 62  递延所得税负债增加                  22 non-null     object
 63  存货的减少                      31 non-null     object
 64  经营性应收项目的减少                 31 non-null     object
 65  经营性应付项目的增加                 31 non-null     object
 66  其他                         22 non-null     object
 67  间接法-经营活动产生的现金流量净额          31 non-null     object
 68  2、不涉及现金收支的重大投资和筹资活动：       88 non-null     object
 69  3、现金及现金等价物净变动情况：           88 non-null     object
 70  现金的期末余额                    31 non-null     object
 71  减：现金的期初余额                  31 non-null     object
 72  加：现金等价物的期末余额               22 non-null     object
 73  减：现金等价物的期初余额               22 non-null     object
 74  间接法-现金及现金等价物净增加额           31 non-null     object


接口示例

import akshare as ak

stock_financial_cash_ths_df = ak.stock_financial_cash_ths(symbol="000063", indicator="按单季度")
print(stock_financial_cash_ths_df)


数据示例

    报告期 报表核心指标 *现金及现金等价物净增加额  ... 加：现金等价物的期末余额 减：现金等价物的期初余额 间接法-现金及现金等价物净增加额
0   2023-09-30               15.54亿  ...
1   2023-06-30               52.02亿  ...
2   2023-03-31               26.73亿  ...        False        False            False
3   2022-12-31              107.72亿  ...
4   2022-09-30              -77.82亿  ...
..         ...    ...           ...  ...          ...          ...              ...
78  2004-03-31              -16.81亿  ...        False        False          -16.81亿
79  2003-12-31               19.40亿  ...                                     19.40亿
80  2003-09-30              -10.76亿  ...                                    -10.76亿
81  2003-06-30               13.89亿  ...                                     13.89亿
82  2003-03-31              -14.06亿  ...        False        False          -14.06亿
[83 rows x 75 columns]

沪深港通历史数据
接口: stock_hsgt_hist_em

目标地址: https://data.eastmoney.com/hsgt/index.html

描述: 东方财富网-数据中心-资金流向-沪深港通资金流向-沪深港通历史数据

限量: 单次获取指定 symbol 的所有数据

输入参数

名称	类型	描述
symbol	str	symbol="北向资金"; choice of {"北向资金", "沪股通", "深股通", "南向资金", "港股通沪", "港股通深"}
输出参数-北向资金

名称	类型	描述
日期	object	-
当日成交净买额	float64	注意单位: 亿元
买入成交额	float64	注意单位: 亿元
卖出成交额	float64	注意单位: 亿元
历史累计净买额	float64	注意单位: 万亿元
当日资金流入	float64	注意单位: 亿元
当日余额	float64	注意单位: 亿元
持股市值	float64	注意单位: 元
领涨股	object	-
领涨股-涨跌幅	float64	注意单位: %
沪深300	float64	-
沪深300-涨跌幅	float64	注意单位: %
领涨股-代码	object	-
接口示例-北向资金

import akshare as ak

stock_hsgt_hist_em_df = ak.stock_hsgt_hist_em(symbol="南向资金")
print(stock_hsgt_hist_em_df)
数据示例-南向资金

           日期   当日成交净买额  买入成交额  ...  沪深300  沪深300-涨跌幅  领涨股-代码
0     2014-11-17  120.8233  120.8233  ...  2474.01      -0.19  601000.SH
1     2014-11-18   47.1967   49.4367  ...  2456.37      -0.71  600755.SH
2     2014-11-19   24.9677   26.6951  ...  2450.99      -0.22  601216.SH
3     2014-11-20   21.4194   23.0973  ...  2452.66       0.07  600755.SH
4     2014-11-21   21.9953   24.3055  ...  2486.79       1.39  600635.SH
          ...       ...       ...  ...      ...        ...        ...
2175  2024-04-08  -30.4468  676.5491  ...  3047.05      -0.72  603110.SH
2176  2024-04-09   10.5503  609.6675  ...  3048.54       0.05  605366.SH
2177  2024-04-10  -41.1411  565.4525  ...  3027.33      -0.70  605376.SH
2178  2024-04-11   20.2153  635.6282  ...  3034.25       0.23  002455.SZ
2179  2024-04-12  -73.8533  584.2191  ...  3019.47      -0.49  600984.SH
[2180 rows x 13 columns]


历史行情数据-新浪
接口: stock_hk_index_daily_sina

目标地址: https://stock.finance.sina.com.cn/hkstock/quotes/CES100.html

描述: 新浪财经-港股指数-历史行情数据

限量: 单次返回指定 symbol 的所有数据

输入参数

名称	类型	描述
symbol	str	symbol="CES100"
输出参数

名称	类型	描述
date	object	-
open	object	-
close	float64	-
high	float64	-
low	float64	注意单位: %
volume	float64	-
接口示例

import akshare as ak

stock_hk_index_daily_sina_df = ak.stock_hk_index_daily_sina(symbol="CES100")
print(stock_hk_index_daily_sina_df)
数据示例

            date      open      high       low     close      volume
0     2014-12-15  4354.014  4362.220  4331.394  4355.359  1087163017
1     2014-12-16  4334.295  4347.367  4275.529  4280.410  1303011243
2     2014-12-17  4278.770  4280.350  4223.895  4227.100  2002919200
3     2014-12-18  4281.007  4296.184  4264.265  4282.028  1547580777
4     2014-12-19  4347.982  4354.488  4321.534  4331.438  1515374212
          ...       ...       ...       ...       ...         ...
2293  2024-04-08  3645.559  3688.903  3624.238  3654.013  2067842312
2294  2024-04-09  3678.340  3719.132  3677.429  3686.826  1588737425
2295  2024-04-10  3706.046  3752.432  3701.602  3741.842  1947224622
2296  2024-04-11  3678.382  3736.533  3676.288  3725.992  1829890643
2297  2024-04-12  3702.688  3712.628  3647.700  3648.330  2097570788
[2298 rows x 6 columns]


历史行情数据-东方财富
接口: stock_zh_index_daily_em

目标地址: http://quote.eastmoney.com/center/hszs.html

描述: 东方财富股票指数数据, 历史数据按日频率更新

限量: 单次返回具体指数的所有历史行情数据

输入参数

名称	类型	描述
symbol	str	symbol="sz399552"; 支持 sz: 深交所, sh: 上交所, csi: 中证指数 + id(000905)
start_date	str	start_date="19900101"
end_date	str	end_date="20500101"
输出参数

名称	类型	描述
date	object	东方财富的数据开始时间, 不是证券上市时间
open	float64	-
close	float64	-
high	float64	-
low	float64	-
volume	int64	-
amount	float64	-
接口示例

import akshare as ak

stock_zh_index_daily_em_df = ak.stock_zh_index_daily_em(symbol="sz399812")
print(stock_zh_index_daily_em_df)
数据示例

            date     open    close     high      low    volume        amount
0     2005-01-04   996.03   989.56   996.03   986.46    675733  4.986503e+08
1     2005-01-05   989.87  1008.59  1011.29   989.46   1037894  9.068431e+08
2     2005-01-06  1008.88  1002.81  1008.88   999.76    779152  5.631133e+08
3     2005-01-07  1002.10  1004.06  1015.61   999.56    898377  7.554397e+08
4     2005-01-10  1002.63  1014.12  1014.12  1000.90    651187  5.609582e+08
          ...      ...      ...      ...      ...       ...           ...
4566  2023-10-23  5659.09  5590.27  5666.15  5563.09   7956295  1.752549e+10
4567  2023-10-24  5608.75  5692.22  5700.26  5590.94   8032521  1.902381e+10
4568  2023-10-25  5735.01  5713.71  5751.73  5713.65   8597481  2.057249e+10
4569  2023-10-26  5694.04  5749.56  5755.59  5684.16   8636096  2.021819e+10
4570  2023-10-27  5747.77  5952.02  5969.61  5741.26  11493696  3.220613e+10
[4571 rows x 7 columns]

港股财务报表
接口: stock_financial_hk_report_em

目标地址: https://emweb.securities.eastmoney.com/PC_HKF10/FinancialAnalysis/index?type=web&code=00700

描述: 东方财富-港股-财务报表-三大报表

限量: 单次获取指定股票、指定报告且指定报告期的数据

输入参数

名称	类型	描述
stock	str	stock="00700"; 股票代码
symbol	str	symbol="现金流量表"; choice of {"资产负债表", "利润表", "现金流量表"}
indicator	str	indicator="年度"; choice of {"年度", "报告期"}
输出参数

名称	类型	描述
SECUCODE	object	-
SECURITY_CODE	object	-
SECURITY_NAME_ABBR	object	-
ORG_CODE	object	-
REPORT_DATE	object	-
DATE_TYPE_CODE	object	-
FISCAL_YEAR	object	-
STD_ITEM_CODE	object	-
STD_ITEM_NAME	object	-
AMOUNT	float64	-
STD_REPORT_DATE	object	-
import akshare as ak

stock_financial_hk_report_em_df = ak.stock_financial_hk_report_em(stock="00700", symbol="资产负债表", indicator="年度")
print(stock_financial_hk_report_em_df)
数据示例

     SECUCODE SECURITY_CODE  ...        AMOUNT      STD_REPORT_DATE
0    00700.HK         00700  ...  5.397800e+10  2022-12-31 00:00:00
1    00700.HK         00700  ...  5.590000e+08  2022-12-31 00:00:00
2    00700.HK         00700  ...  1.618020e+11  2022-12-31 00:00:00
3    00700.HK         00700  ...  1.804600e+10  2022-12-31 00:00:00
4    00700.HK         00700  ...  9.229000e+09  2022-12-31 00:00:00
..        ...           ...  ...           ...                  ...
965  00700.HK         00700  ...  4.817800e+07  2001-12-31 00:00:00
966  00700.HK         00700  ...  4.832400e+07  2001-12-31 00:00:00
967  00700.HK         00700  ...  4.832400e+07  2001-12-31 00:00:00
968  00700.HK         00700  ...  4.832400e+07  2001-12-31 00:00:00
969  00700.HK         00700  ...  6.554200e+07  2001-12-31 00:00:00
[970 rows x 11 columns]