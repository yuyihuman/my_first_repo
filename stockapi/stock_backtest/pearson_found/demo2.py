# 用前须知

## xtdata提供和MiniQmt的交互接口，本质是和MiniQmt建立连接，由MiniQmt处理行情数据请求，再把结果回传返回到python层。使用的行情服务器以及能获取到的行情数据和MiniQmt是一致的，要检查数据或者切换连接时直接操作MiniQmt即可。

## 对于数据获取接口，使用时需要先确保MiniQmt已有所需要的数据，如果不足可以通过补充数据接口补充，再调用数据获取接口获取。

## 对于订阅接口，直接设置数据回调，数据到来时会由回调返回。订阅接收到的数据一般会保存下来，同种数据不需要再单独补充。

# 代码讲解

# 从本地python导入xtquant库，如果出现报错则说明安装失败
from xtquant import xtdata
import time
import os
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 引入股票列表配置：使用 top20 参数
from stock_config import get_comparison_stocks

# 设定获取数据的周期（保持不变）
period = "1d"


def to_full_code(code6: str) -> str:
    """将6位代码转换为带交易所后缀的代码，保持与现有保存结构一致。
    0/3开头 -> .SZ，60开头 -> .SH
    其他情况原样返回（极少数特殊标的）。"""
    code6 = str(code6).zfill(6)
    if code6.startswith("60"):
        return f"{code6}.SH"
    elif code6.startswith("0") or code6.startswith("3"):
        return f"{code6}.SZ"
    return code6


# 从配置获取前20个股票代码并转换为带后缀的格式
raw_codes = get_comparison_stocks("top20")
code_list = [to_full_code(c) for c in raw_codes]


def process_one_code(code: str):
    """单只股票的订阅、获取与JSONL追加保存，保持原有数据结构。"""
    # 订阅（盘中实时需要订阅），设置count = -1来取到当天所有实时行情
    xtdata.subscribe_quote(code, period=period, count=-1)
    # 等待订阅完成
    time.sleep(1)

    output_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(output_dir, exist_ok=True)

    def save_once():
        kline_data = xtdata.get_market_data_ex([], [code], period=period, count=1)
        payload = {}
        if isinstance(kline_data, dict):
            df = kline_data.get(code)
            try:
                rows = df.reset_index().to_dict(orient="records")
            except Exception:
                rows = [str(df)]
            payload[code] = rows
        else:
            payload = {"data": kline_data}
        file_path = os.path.join(output_dir, f"latest_kline_{code}_{period}.jsonl")
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "data": payload.get(code, [])
            }, ensure_ascii=False) + "\n")

    # 首次获取并保存
    save_once()

    # 按固定间隔刷新与保存（与原逻辑一致为10次）
    for _ in range(10):
        save_once()
        time.sleep(3)


def main():
    # 使用20线程并发处理每只股票，保持保存结构不变
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(process_one_code, code) for code in code_list]
        for fut in as_completed(futures):
            # 捕获线程中的异常，避免静默失败
            try:
                fut.result()
            except Exception as e:
                print(f"线程执行出错: {e}")


if __name__ == "__main__":
    main()



