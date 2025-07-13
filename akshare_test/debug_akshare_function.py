import requests
import pandas as pd
import json
from typing import Optional

def stock_gdfx_holding_detail_em_debug(date: str, indicator: str, symbol: str) -> pd.DataFrame:
    """
    带调试功能的股东持股明细查询函数
    
    Args:
        date: 查询日期，格式为 YYYYMMDD
        indicator: 机构类型，如 "社保", "基金", "券商", "信托", "QFII"
        symbol: 变化类型，如 "新进", "增加", "不变", "减少"
    
    Returns:
        包含持股明细的DataFrame
    """
    print(f"[DEBUG] 开始查询持股明细")
    print(f"[DEBUG] 参数 - 日期: {date}, 机构类型: {indicator}, 变化类型: {symbol}")
    
    # 构建请求URL和参数
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    
    # 格式化日期
    formatted_date = '-'.join([date[:4], date[4:6], date[6:]])
    print(f"[DEBUG] 格式化后的日期: {formatted_date}")
    
    params = {
        "sortColumns": "NOTICE_DATE,SECURITY_CODE,RANK",
        "sortTypes": "-1,1,1",
        "pageSize": "500",
        "pageNumber": "1",
        "reportName": "RPT_DMSK_HOLDERS",
        "columns": "ALL",
        "source": "WEB",
        "client": "WEB",
        "filter": f'(HOLDER_NEWTYPE="{indicator}")(HOLDNUM_CHANGE_NAME="{symbol}")(END_DATE="{formatted_date}")',
    }
    
    print(f"[DEBUG] 请求URL: {url}")
    print(f"[DEBUG] 请求参数: {json.dumps(params, ensure_ascii=False, indent=2)}")
    
    try:
        # 发送请求
        print(f"[DEBUG] 发送HTTP请求...")
        r = requests.get(url, params=params, timeout=30)
        print(f"[DEBUG] HTTP状态码: {r.status_code}")
        print(f"[DEBUG] 响应头: {dict(r.headers)}")
        
        # 检查响应状态
        if r.status_code != 200:
            print(f"[ERROR] HTTP请求失败，状态码: {r.status_code}")
            print(f"[ERROR] 响应内容: {r.text[:500]}...")
            return pd.DataFrame()
        
        # 解析JSON响应
        print(f"[DEBUG] 解析JSON响应...")
        print(f"[DEBUG] 响应内容前500字符: {r.text[:500]}")
        
        try:
            data_json = r.json()
            print(f"[DEBUG] JSON解析成功")
            print(f"[DEBUG] 响应JSON结构: {json.dumps(data_json, ensure_ascii=False, indent=2)[:1000]}...")
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON解析失败: {e}")
            print(f"[ERROR] 原始响应: {r.text}")
            return pd.DataFrame()
        
        # 检查响应结构
        if data_json is None:
            print(f"[ERROR] 响应JSON为None")
            return pd.DataFrame()
        
        if "result" not in data_json:
            print(f"[ERROR] 响应中缺少'result'字段")
            print(f"[ERROR] 可用字段: {list(data_json.keys()) if isinstance(data_json, dict) else 'Not a dict'}")
            return pd.DataFrame()
        
        result = data_json["result"]
        if result is None:
            print(f"[ERROR] result字段为None")
            return pd.DataFrame()
        
        if "pages" not in result:
            print(f"[ERROR] result中缺少'pages'字段")
            print(f"[ERROR] result可用字段: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
            return pd.DataFrame()
        
        total_page = result["pages"]
        print(f"[DEBUG] 总页数: {total_page}")
        
        if "data" not in result:
            print(f"[ERROR] result中缺少'data'字段")
            return pd.DataFrame()
        
        data_list = result["data"]
        print(f"[DEBUG] 数据条数: {len(data_list) if data_list else 0}")
        
        if not data_list:
            print(f"[WARNING] 没有找到数据")
            return pd.DataFrame()
        
        # 处理所有页面的数据
        big_df = pd.DataFrame()
        
        for page in range(1, total_page + 1):
            print(f"[DEBUG] 处理第 {page}/{total_page} 页")
            
            if page > 1:
                # 更新页码参数
                params["pageNumber"] = str(page)
                
                # 发送请求获取下一页数据
                r_page = requests.get(url, params=params, timeout=30)
                if r_page.status_code != 200:
                    print(f"[ERROR] 第{page}页请求失败，状态码: {r_page.status_code}")
                    continue
                
                try:
                    data_json_page = r_page.json()
                    if data_json_page and "result" in data_json_page and data_json_page["result"] and "data" in data_json_page["result"]:
                        data_list = data_json_page["result"]["data"]
                    else:
                        print(f"[ERROR] 第{page}页数据格式错误")
                        continue
                except json.JSONDecodeError as e:
                    print(f"[ERROR] 第{page}页JSON解析失败: {e}")
                    continue
            
            # 转换为DataFrame
            if data_list:
                temp_df = pd.DataFrame(data_list)
                print(f"[DEBUG] 第{page}页数据列: {list(temp_df.columns) if not temp_df.empty else 'Empty'}")
                print(f"[DEBUG] 第{page}页数据行数: {len(temp_df)}")
                
                if not temp_df.empty:
                    big_df = pd.concat([big_df, temp_df], ignore_index=True)
        
        print(f"[DEBUG] 最终数据行数: {len(big_df)}")
        print(f"[DEBUG] 最终数据列: {list(big_df.columns) if not big_df.empty else 'Empty'}")
        
        if not big_df.empty:
            print(f"[DEBUG] 前5行数据预览:")
            print(big_df.head().to_string())
        
        return big_df
        
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] 网络请求异常: {e}")
        return pd.DataFrame()
    except Exception as e:
        print(f"[ERROR] 未知异常: {e}")
        import traceback
        print(f"[ERROR] 异常堆栈: {traceback.format_exc()}")
        return pd.DataFrame()


def test_debug_function():
    """
    测试调试函数
    """
    print("=== 开始测试调试函数 ===")
    
    # 测试参数
    test_cases = [
        {"date": "20231231", "indicator": "社保", "symbol": "新进"},
        {"date": "20231231", "indicator": "基金", "symbol": "增加"},
        {"date": "20250331", "indicator": "个人", "symbol": "新进"},  # 这个可能会失败
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n=== 测试用例 {i} ===")
        result = stock_gdfx_holding_detail_em_debug(**case)
        print(f"结果: {len(result)} 行数据")
        print("-" * 50)


if __name__ == "__main__":
    test_debug_function()