# 从本地python导入xtquant库，如果出现报错则说明安装失败
from xtquant import xtdata
import logging
import os
from datetime import datetime

# 获取当前文件信息
current_file = os.path.basename(__file__)
current_path = os.path.abspath(__file__)

# 创建logs目录（如果不存在）
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 配置日志 - 添加文件名和行号信息
# 基于当前文件名生成日志文件名（去掉.py扩展名）
base_filename = os.path.splitext(current_file)[0]
log_filename = os.path.join(log_dir, f"{base_filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()  # 同时输出到控制台
    ]
)

logger = logging.getLogger(__name__)

# 设定一个标的列表
code_list = ["000001.SZ", "601398.SH"]
# 设定获取数据的周期
period = "1m"

# 记录程序启动信息和参数配置
logger.info("="*60)
logger.info(f"程序启动 - 文件: {current_file}")
logger.info(f"完整路径: {current_path}")
logger.info(f"运行参数配置:")
logger.info(f"  - 监控股票列表: {code_list}")
logger.info(f"  - 数据周期: {period}")
logger.info(f"  - 日志文件路径: {log_filename}")
logger.info(f"  - 回调函数: f(data)")
logger.info("="*60)

# 定义的回测函数
    ## 回调函数中，data是本次触发回调的数据，只有一条
def f(data):
    # logger.debug(f"[{current_file}] 收到回调数据: {data}")
    
    code_list_callback = list(data.keys())    # 获取到本次触发的标的代码
    logger.info(f"[回调函数] 触发股票代码: {code_list_callback}, 周期: {period}")

    kline_in_callabck = xtdata.get_market_data_ex([],code_list_callback,period = period)    # 在回调中获取klines数据
    logger.info(f"[回调函数] 获取到K线数据: {kline_in_callabck}")

# 订阅股票行情
logger.info(f"[{current_file}] 开始订阅股票行情...")
for i in code_list:
    xtdata.subscribe_quote(i,period=period,count=-1,callback=f) # 订阅时设定回调函数
    logger.info(f"[{current_file}] 已订阅股票 {i} 的行情数据 (周期: {period}, 回调: f)")

logger.info(f"[{current_file}] 开始运行数据监控...")
# 使用回调时，必须要同时使用xtdata.run()来阻塞程序，否则程序运行到最后一行就直接结束退出了。
try:
    xtdata.run()
except KeyboardInterrupt:
    logger.info(f"[{current_file}] 程序被用户中断")
except Exception as e:
    logger.error(f"[{current_file}] 程序运行出错: {e}")
finally:
    logger.info(f"[{current_file}] 程序结束运行")
    logger.info("="*60)