# AKShare 股票数据API接口完整指南

## 📋 项目概述

**AKShare** 是基于 Python 的财经数据接口库，目的是实现对股票、期货、期权、基金、外汇、债券、指数、加密货币等金融产品的基本面数据、实时和历史行情数据、衍生数据从数据采集、数据清洗到数据落地的一套工具，主要用于学术研究目的。

- **官方文档**: https://akshare.akfamily.xyz/
- **GitHub仓库**: https://github.com/akfamily/akshare
- **Python版本要求**: Python 3.9 或更高版本（64位）
- **数据来源**: 公开的权威财经数据网站

## ⚠️ 重要提示

- 所有数据来源于公开数据源，仅用于学术研究
- 需要经常更新到最新版本以保持接口可用性
- 当日数据需要在收盘后获取
- 注意商业使用风险

---

## 🏢 一、A股实时行情数据

### 1.1 沪深A股实时行情

#### `stock_zh_a_spot_em`
**功能**: 东方财富网-沪深京A股实时行情数据
```python
import akshare as ak
stock_zh_a_spot_em_df = ak.stock_zh_a_spot_em()
print(stock_zh_a_spot_em_df)
```

#### `stock_sh_a_spot_em`
**功能**: 东方财富网-上海A股实时行情
```python
import akshare as ak
stock_sh_a_spot_em_df = ak.stock_sh_a_spot_em()
print(stock_sh_a_spot_em_df)
```

#### `stock_sz_a_spot_em`
**功能**: 东方财富网-深圳A股实时行情
```python
import akshare as ak
stock_sz_a_spot_em_df = ak.stock_sz_a_spot_em()
print(stock_sz_a_spot_em_df)
```

#### `stock_bj_a_spot_em`
**功能**: 东方财富网-北京A股实时行情
```python
import akshare as ak
stock_bj_a_spot_em_df = ak.stock_bj_a_spot_em()
print(stock_bj_a_spot_em_df)
```

#### `stock_new_a_spot_em`
**功能**: 东方财富网-新股实时行情
```python
import akshare as ak
stock_new_a_spot_em_df = ak.stock_new_a_spot_em()
print(stock_new_a_spot_em_df)
```

### 1.2 个股详细信息

#### `stock_individual_info_em`
**功能**: 东方财富网-个股详细信息
```python
import akshare as ak
stock_individual_info_em_df = ak.stock_individual_info_em(symbol="000001")
print(stock_individual_info_em_df)
```

#### `stock_bid_ask_em`
**功能**: 东方财富网-个股买卖盘口数据
```python
import akshare as ak
stock_bid_ask_em_df = ak.stock_bid_ask_em(symbol="000001")
print(stock_bid_ask_em_df)
```

---

## 📈 二、A股历史行情数据

### 2.1 日频历史数据

#### `stock_zh_a_hist`
**功能**: 东方财富网-沪深京A股日频率历史数据
**参数说明**:
- `symbol`: 股票代码
- `period`: 周期（daily, weekly, monthly）
- `start_date`: 开始日期
- `end_date`: 结束日期
- `adjust`: 复权类型（"qfq"前复权, "hfq"后复权, ""不复权）

```python
import akshare as ak
stock_zh_a_hist_df = ak.stock_zh_a_hist(
    symbol="000001", 
    period="daily", 
    start_date="20170301", 
    end_date="20231022", 
    adjust="qfq"
)
print(stock_zh_a_hist_df)
```

### 2.2 分时历史数据

#### `stock_zh_a_hist_min_em`
**功能**: 东方财富网-沪深京A股分时历史数据
```python
import akshare as ak
stock_zh_a_hist_min_em_df = ak.stock_zh_a_hist_min_em(
    symbol="000001", 
    start_date="20231201 09:32:00", 
    end_date="20231201 15:00:00", 
    period="1"
)
print(stock_zh_a_hist_min_em_df)
```

#### `stock_zh_a_hist_pre_min_em`
**功能**: 东方财富网-沪深京A股盘前分时历史数据
```python
import akshare as ak
stock_zh_a_hist_pre_min_em_df = ak.stock_zh_a_hist_pre_min_em(symbol="000001")
print(stock_zh_a_hist_pre_min_em_df)
```

---

## 🏭 三、板块数据

### 3.1 行业板块

#### `stock_board_industry_name_em`
**功能**: 东方财富网-行业板块名称
```python
import akshare as ak
stock_board_industry_name_em_df = ak.stock_board_industry_name_em()
print(stock_board_industry_name_em_df)
```

#### `stock_board_industry_cons_em`
**功能**: 东方财富网-行业板块成分股
```python
import akshare as ak
stock_board_industry_cons_em_df = ak.stock_board_industry_cons_em(symbol="小金属")
print(stock_board_industry_cons_em_df)
```

#### `stock_board_industry_spot_em`
**功能**: 东方财富网-行业板块实时行情
```python
import akshare as ak
stock_board_industry_spot_em_df = ak.stock_board_industry_spot_em()
print(stock_board_industry_spot_em_df)
```

#### `stock_board_industry_hist_em`
**功能**: 东方财富网-行业板块历史行情
```python
import akshare as ak
stock_board_industry_hist_em_df = ak.stock_board_industry_hist_em(
    symbol="小金属", 
    start_date="20231201", 
    end_date="20231208", 
    period="日k", 
    adjust=""
)
print(stock_board_industry_hist_em_df)
```

### 3.2 概念板块

#### `stock_board_concept_name_em`
**功能**: 东方财富网-概念板块名称
```python
import akshare as ak
stock_board_concept_name_em_df = ak.stock_board_concept_name_em()
print(stock_board_concept_name_em_df)
```

#### `stock_board_concept_cons_em`
**功能**: 东方财富网-概念板块成分股
```python
import akshare as ak
stock_board_concept_cons_em_df = ak.stock_board_concept_cons_em(symbol="华为概念")
print(stock_board_concept_cons_em_df)
```

#### `stock_board_concept_spot_em`
**功能**: 东方财富网-概念板块实时行情
```python
import akshare as ak
stock_board_concept_spot_em_df = ak.stock_board_concept_spot_em()
print(stock_board_concept_spot_em_df)
```

#### `stock_board_concept_hist_em`
**功能**: 东方财富网-概念板块历史行情
```python
import akshare as ak
stock_board_concept_hist_em_df = ak.stock_board_concept_hist_em(
    symbol="华为概念", 
    start_date="20231201", 
    end_date="20231208", 
    period="日k", 
    adjust=""
)
print(stock_board_concept_hist_em_df)
```

---

## 💰 四、财务数据

### 4.1 财务报表

#### `stock_balance_sheet_by_report_em`
**功能**: 东方财富网-资产负债表-按报告期
```python
import akshare as ak
stock_balance_sheet_by_report_em_df = ak.stock_balance_sheet_by_report_em(symbol="000001")
print(stock_balance_sheet_by_report_em_df)
```

#### `stock_profit_sheet_by_report_em`
**功能**: 东方财富网-利润表-按报告期
```python
import akshare as ak
stock_profit_sheet_by_report_em_df = ak.stock_profit_sheet_by_report_em(symbol="000001")
print(stock_profit_sheet_by_report_em_df)
```

#### `stock_cash_flow_sheet_by_report_em`
**功能**: 东方财富网-现金流量表-按报告期
```python
import akshare as ak
stock_cash_flow_sheet_by_report_em_df = ak.stock_cash_flow_sheet_by_report_em(symbol="000001")
print(stock_cash_flow_sheet_by_report_em_df)
```

### 4.2 财务指标

#### `stock_financial_analysis_indicator`
**功能**: 新浪财经-财务指标
```python
import akshare as ak
stock_financial_analysis_indicator_df = ak.stock_financial_analysis_indicator(symbol="000001")
print(stock_financial_analysis_indicator_df)
```

#### `stock_financial_abstract`
**功能**: 新浪财经-财务摘要
```python
import akshare as ak
stock_financial_abstract_df = ak.stock_financial_abstract(symbol="000001")
print(stock_financial_abstract_df)
```

---

## 🏛️ 五、机构持股数据

### 5.1 基金持股

#### `stock_report_fund_hold`
**功能**: 个股基金持股数据
**参数说明**:
- `symbol`: 持股类型（"基金持仓", "QFII持仓", "社保持仓", "券商持仓", "保险持仓", "信托持仓"）
- `date`: 财报发布日期（季度末：xxxx-03-31, xxxx-06-30, xxxx-09-30, xxxx-12-31）

```python
import akshare as ak
stock_report_fund_hold_df = ak.stock_report_fund_hold(symbol="基金持仓", date="20200630")
print(stock_report_fund_hold_df)
```

#### `stock_report_fund_hold_detail`
**功能**: 个股基金持股明细
```python
import akshare as ak
stock_report_fund_hold_detail_df = ak.stock_report_fund_hold_detail(
    symbol="000001", 
    date="20200630"
)
print(stock_report_fund_hold_detail_df)
```

### 5.2 机构持股统计

#### `stock_institute_hold`
**功能**: 机构持股一览表
```python
import akshare as ak
stock_institute_hold_df = ak.stock_institute_hold(quarter="20203")
print(stock_institute_hold_df)
```

#### `stock_institute_hold_detail`
**功能**: 机构持股详情
```python
import akshare as ak
stock_institute_hold_detail_df = ak.stock_institute_hold_detail(
    symbol="000001", 
    quarter="20203"
)
print(stock_institute_hold_detail_df)
```

---

## 📊 六、交易所数据

### 6.1 上海证券交易所

#### `stock_sse_deal_daily`
**功能**: 上海证券交易所-每日股票情况
```python
import akshare as ak
stock_sse_deal_daily_df = ak.stock_sse_deal_daily(date="20250221")
print(stock_sse_deal_daily_df)
```

### 6.2 深圳证券交易所

#### `stock_szse_summary`
**功能**: 深圳证券交易所-市场总貌
```python
import akshare as ak
stock_szse_summary_df = ak.stock_szse_summary(date="20200619")
print(stock_szse_summary_df)
```

#### `stock_szse_area_summary`
**功能**: 深圳证券交易所-地区统计
```python
import akshare as ak
stock_szse_area_summary_df = ak.stock_szse_area_summary(date="202412")
print(stock_szse_area_summary_df)
```

#### `stock_szse_sector_summary`
**功能**: 深圳证券交易所-行业统计
```python
import akshare as ak
stock_szse_sector_summary_df = ak.stock_szse_sector_summary(symbol="当年", date="202501")
print(stock_szse_sector_summary_df)
```

---

## 🌐 七、港股数据

### 7.1 港股实时行情

#### `stock_hk_spot_em`
**功能**: 东方财富网-港股实时行情
```python
import akshare as ak
stock_hk_spot_em_df = ak.stock_hk_spot_em()
print(stock_hk_spot_em_df)
```

### 7.2 沪深港通

#### `stock_zh_ah_spot_em`
**功能**: 东方财富网-沪深港通-AH股比价-实时行情
```python
import akshare as ak
stock_zh_ah_spot_em_df = ak.stock_zh_ah_spot_em()
print(stock_zh_ah_spot_em_df)
```

#### `stock_hsgt_sh_hk_spot_em`
**功能**: 东方财富网-沪深港通-港股通(沪>港)-股票
```python
import akshare as ak
stock_hsgt_sh_hk_spot_em_df = ak.stock_hsgt_sh_hk_spot_em()
print(stock_hsgt_sh_hk_spot_em_df)
```

---

## 🔥 八、特色数据

### 8.1 股票热度

#### `stock_hot_rank_em`
**功能**: 东方财富网-个股人气榜-人气榜
```python
import akshare as ak
stock_hot_rank_em_df = ak.stock_hot_rank_em()
print(stock_hot_rank_em_df)
```

#### `stock_hot_up_em`
**功能**: 东方财富网-个股人气榜-飙升榜
```python
import akshare as ak
stock_hot_up_em_df = ak.stock_hot_up_em()
print(stock_hot_up_em_df)
```

#### `stock_hot_keyword_em`
**功能**: 东方财富网-个股人气榜-关键词
```python
import akshare as ak
stock_hot_keyword_em_df = ak.stock_hot_keyword_em()
print(stock_hot_keyword_em_df)
```

### 8.2 龙虎榜数据

#### `stock_lhb_detail_daily_sina`
**功能**: 新浪财经-龙虎榜-每日详情
```python
import akshare as ak
stock_lhb_detail_daily_sina_df = ak.stock_lhb_detail_daily_sina(trade_date="20231208")
print(stock_lhb_detail_daily_sina_df)
```

#### `stock_lhb_ggtj_sina`
**功能**: 新浪财经-龙虎榜-个股上榜统计
```python
import akshare as ak
stock_lhb_ggtj_sina_df = ak.stock_lhb_ggtj_sina(symbol="000001")
print(stock_lhb_ggtj_sina_df)
```

---

## 📋 九、股票基本信息

### 9.1 股票代码和名称

#### `stock_info_a_code_name`
**功能**: A股股票代码和简称
```python
import akshare as ak
stock_info_a_code_name_df = ak.stock_info_a_code_name()
print(stock_info_a_code_name_df)
```

#### `stock_info_sh_name_code`
**功能**: 上海证券交易所股票代码和简称
```python
import akshare as ak
stock_info_sh_name_code_df = ak.stock_info_sh_name_code()
print(stock_info_sh_name_code_df)
```

#### `stock_info_sz_name_code`
**功能**: 深圳证券交易所股票代码和简称
```python
import akshare as ak
stock_info_sz_name_code_df = ak.stock_info_sz_name_code()
print(stock_info_sz_name_code_df)
```

#### `stock_info_bj_name_code`
**功能**: 北京证券交易所股票代码和简称
```python
import akshare as ak
stock_info_bj_name_code_df = ak.stock_info_bj_name_code()
print(stock_info_bj_name_code_df)
```

### 9.2 股票状态信息

#### `stock_info_sh_delist`
**功能**: 上海证券交易所暂停和终止上市
```python
import akshare as ak
stock_info_sh_delist_df = ak.stock_info_sh_delist()
print(stock_info_sh_delist_df)
```

#### `stock_info_sz_delist`
**功能**: 深圳证券交易所暂停和终止上市
```python
import akshare as ak
stock_info_sz_delist_df = ak.stock_info_sz_delist()
print(stock_info_sz_delist_df)
```

#### `stock_info_change_name`
**功能**: A股股票曾用名列表
```python
import akshare as ak
stock_info_change_name_df = ak.stock_info_change_name()
print(stock_info_change_name_df)
```

---

## 🛠️ 十、使用建议和最佳实践

### 10.1 安装和更新

```bash
# 安装
pip install akshare

# 升级到最新版本
pip install akshare --upgrade
```

### 10.2 使用注意事项

1. **版本更新**: 经常更新到最新版本以保持接口可用性
2. **数据时效**: 当日数据需要在收盘后获取
3. **请求频率**: 避免过于频繁的请求，建议添加适当的延时
4. **异常处理**: 网络请求可能失败，建议添加异常处理机制
5. **数据验证**: 对获取的数据进行基本的验证和清洗

### 10.3 示例代码模板

```python
import akshare as ak
import pandas as pd
import time

def get_stock_data_safely(func, *args, **kwargs):
    """安全获取股票数据的包装函数"""
    try:
        time.sleep(0.1)  # 添加延时避免请求过于频繁
        data = func(*args, **kwargs)
        return data
    except Exception as e:
        print(f"获取数据失败: {e}")
        return pd.DataFrame()

# 使用示例
stock_data = get_stock_data_safely(
    ak.stock_zh_a_hist, 
    symbol="000001", 
    period="daily", 
    start_date="20230101", 
    end_date="20231201"
)
```

---

## 📚 相关资源

- **官方文档**: https://akshare.akfamily.xyz/
- **GitHub仓库**: https://github.com/akfamily/akshare
- **更新日志**: https://akshare.akfamily.xyz/changelog.html
- **快速入门**: https://akshare.akfamily.xyz/tutorial.html

---

*本文档基于AKShare 1.16.98版本整理，如有疑问请参考官方最新文档。*

**免责声明**: 本文档仅供学习和研究使用，使用者需自行承担商业使用风险。