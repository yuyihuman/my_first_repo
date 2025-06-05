# 导入所有模块的主要函数，方便外部调用
from .cache_utils import ensure_cache_directories
from .lhb_data import get_lhb_top10
from .stock_finance import get_stock_financial_data
from .hkstock_data import get_hkstock_data

from .hkstock_finance import get_hkstock_finance
from .macro_data import fetch_macro_china_money_supply

# 版本信息
__version__ = '1.0.0'