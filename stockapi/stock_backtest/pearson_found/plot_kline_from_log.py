"""
从批量Pearson分析日志中解析高相关期间，并绘制上下对比的K线图。

功能概述：
- 解析日志文件，获取评测窗口（源数据窗口）与各条高相关期间（股票代码、开始/结束日期、相关系数）。
- 通过项目中的 StockDataLoader 加载日线数据。
- 上图绘制源数据窗口（目标股票），下图绘制历史数据窗口（来源股票）。
- 每个图包含开盘、收盘的蜡烛图以及成交量柱状图。

用法示例：
python plot_kline_from_log.py \
  --log "c:\\Users\\17701\\github\\my_first_repo\\stockapi\\stock_backtest\\pearson_found\\logs\\batch_pearson_analysis_list_20251111_233136_thread_22560.log" \
  --output-dir ./kline_plots \
  --only-index 1

参数说明：
- --log: 必填，日志文件路径。
- --output-dir: 输出图片目录，默认在日志同目录下的 kline_plots。
- --source-stock: 可选，覆盖源数据股票代码；如不指定则从日志“目标股票”列表取首个。
- --only-index: 仅绘制指定“期间#X”的索引（如1）；不指定则绘制日志中所有解析到的期间。

注意：
- 数据加载依赖 StockDataLoader，需确保历史数据CSV已生成并路径有效。
- 若数据缺失会跳过对应期间并给出提示。
"""

import os
import re
import argparse
from datetime import datetime
from typing import List, Optional, Tuple, Dict

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import mplfinance as mpf

from data_loader import StockDataLoader


# 全局中文字体配置，避免中文标题/标签无法显示
mpl.rcParams['font.family'] = 'sans-serif'
mpl.rcParams['font.sans-serif'] = [
    'Microsoft YaHei', 'SimHei', 'SimSun', 'KaiTi',
    'Arial Unicode MS', 'DejaVu Sans'
]
mpl.rcParams['axes.unicode_minus'] = False

# 日志解析的正则模式
RE_TARGET_STOCKS = re.compile(r"目标股票:\s*\[(.*?)\]")
RE_PROCESS_STOCK = re.compile(r"处理股票\s*\d+\s*:\s*(\d+)")
RE_EVAL_WINDOW = re.compile(r"评测数据窗口:\s*([0-9\-: ]+) 到 ([0-9\-: ]+)")
RE_PERIOD_DEBUG = re.compile(
    r"期间#(?P<idx>\d+): 股票:(?P<stock>\d+), 期间:(?P<start>[0-9\-: ]+)~(?P<end>[0-9\-: ]+), 相关系数:(?P<corr>[0-9\.]+)"
)
RE_PERIOD_INFO_BLOCK = re.compile(
    r"#(?P<idx>\d+) 历史期间 .*: (?P<start>[0-9\-: ]+) 到 (?P<end>[0-9\-: ]+)"
)
RE_SOURCE_STOCK_IN_BLOCK = re.compile(r"来源股票:\s*(?P<stock>\d+)")


def parse_log(log_path: str) -> Tuple[Optional[str], Optional[str], List[Dict]]:
    """
    解析日志文件，提取：
    - 源数据评测窗口（start_datetime_str, end_datetime_str）
    - 源数据股票（目标股票列表首个）
    - 高相关期间列表：[{idx, stock, start, end, corr}]
    """
    if not os.path.exists(log_path):
        raise FileNotFoundError(f"日志文件不存在: {log_path}")

    with open(log_path, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    # 评测窗口
    eval_window_match = RE_EVAL_WINDOW.search(content)
    eval_start, eval_end = None, None
    if eval_window_match:
        eval_start = eval_window_match.group(1).strip()
        eval_end = eval_window_match.group(2).strip()

    # 从结构化日志自动确定源股票：
    # 优先使用“📝 [详细结果构建] 处理股票X: CODE”，否则回退到“目标股票: [...]”首个。
    source_stock: Optional[str] = None

    proc_match = RE_PROCESS_STOCK.search(content)
    if proc_match:
        source_stock = proc_match.group(1)
    else:
        tgt_match = RE_TARGET_STOCKS.search(content)
        if tgt_match:
            raw = tgt_match.group(1)
            # 去掉引号和空格，分割列表
            items = [s.strip().strip("'").strip('"') for s in raw.split(',') if s.strip()]
            if items:
                source_stock = items[0]

    periods: List[Dict] = []

    # 解析 DEBUG 样式的期间行
    for m in RE_PERIOD_DEBUG.finditer(content):
        periods.append({
            'idx': int(m.group('idx')),
            'stock': m.group('stock'),
            'start': m.group('start').strip(),
            'end': m.group('end').strip(),
            'corr': float(m.group('corr')),
        })

    # 解析 INFO 样式的期间块（#n 历史期间 ... 来源股票: ...）
    # 为了稳妥，逐行扫描，将块内来源股票拼接到对应idx
    lines = content.splitlines()
    info_block_buffer: Dict[int, Dict] = {}
    for i, line in enumerate(lines):
        m = RE_PERIOD_INFO_BLOCK.search(line)
        if m:
            idx = int(m.group('idx'))
            info_block_buffer[idx] = {
                'idx': idx,
                'start': m.group('start').strip(),
                'end': m.group('end').strip(),
                'stock': None,
                'corr': None,  # 平均相关系数可能在后续行
            }
            # 向后检查若干行以找“来源股票”与“平均相关系数”
            j = i + 1
            while j < len(lines) and (lines[j].strip().startswith('202') or lines[j].strip().startswith('🔍') or 'INFO' in lines[j] or 'DEBUG' in lines[j]):
                ms = RE_SOURCE_STOCK_IN_BLOCK.search(lines[j])
                if ms:
                    info_block_buffer[idx]['stock'] = ms.group('stock')
                if '平均相关系数:' in lines[j]:
                    try:
                        info_block_buffer[idx]['corr'] = float(lines[j].split('平均相关系数:')[-1].strip())
                    except Exception:
                        pass
                # 到下一个块的分隔就停
                if lines[j].strip().startswith('------------------------------------------------------------'):
                    break
                j += 1

    # 合并 INFO 块到 periods 列表（若该 idx 未出现于 DEBUG 列表中）
    existing_idxs = {p['idx'] for p in periods}
    for idx, info in info_block_buffer.items():
        if idx not in existing_idxs and info.get('stock') and info.get('start') and info.get('end'):
            periods.append(info)

    # 按 idx 排序
    periods.sort(key=lambda x: x['idx'])

    return eval_start, source_stock, periods


def _to_date_str(dt_str: str) -> str:
    """将日志中的日期字符串转换为 YYYY-MM-DD（去掉时间部分）。"""
    if not dt_str:
        return dt_str
    try:
        # 日志格式通常为 "YYYY-MM-DD 00:00:00"
        return datetime.strptime(dt_str.strip(), '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
    except ValueError:
        # 兜底：若已是日期格式，直接返回
        return dt_str.strip().split(' ')[0]


def prepare_ohlcv(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    将 DataFrame 转换为 mplfinance 需要的 OHLCV 列格式。
    若不存在高低价，则以 open/close 合成：
    high=max(open, close), low=min(open, close)
    """
    if df is None or df.empty:
        return None

    # 需要 open/close/volume 三列
    needed = ['open', 'close', 'volume']
    for col in needed:
        if col not in df.columns:
            return None

    out = pd.DataFrame(index=df.index.copy())
    out['Open'] = df['open']
    out['Close'] = df['close']
    out['Volume'] = df['volume'] if 'volume' in df.columns else 0
    # 合成 High/Low
    high = pd.concat([df['open'], df['close']], axis=1).max(axis=1)
    low = pd.concat([df['open'], df['close']], axis=1).min(axis=1)
    out['High'] = high
    out['Low'] = low
    return out[['Open', 'High', 'Low', 'Close', 'Volume']]


def pad_with_blank_rows(df: pd.DataFrame, target_len: int) -> pd.DataFrame:
    """
    将 df 末尾用“空白行”(OHLCV 为 NaN)补齐到 target_len，
    以保证与另一面板的K线数量对齐。

    规则：
    - 若 df 已>=target_len，不做处理。
    - 使用“工作日”频率(B)生成补齐索引，从 df 最后一个日期的下一工作日起连续补齐。
    - 若索引不是 DatetimeIndex，尝试转换为 datetime；失败则保持原索引并直接返回（不补齐）。
    """
    if df is None or df.empty:
        return df

    cur_len = len(df)
    if target_len <= cur_len:
        return df

    # 确保索引为 DatetimeIndex
    try:
        if not isinstance(df.index, pd.DatetimeIndex):
            df = df.copy()
            df.index = pd.to_datetime(df.index)
    except Exception:
        # 索引转换失败则跳过补齐，避免破坏数据
        return df

    last_dt = df.index[-1]
    need = target_len - cur_len
    # 从下一工作日开始补齐
    pad_index = pd.bdate_range(last_dt + pd.Timedelta(days=1), periods=need)
    blank = pd.DataFrame(index=pad_index, columns=df.columns)
    # OHLCV 全部 NaN，mplfinance 会在相应位置不绘制蜡烛，但占位确保数量对齐
    return pd.concat([df, blank])


def plot_two_panels(source_ohlcv: pd.DataFrame,
                    hist_ohlcv: pd.DataFrame,
                    title_top: str,
                    title_bottom: str,
                    save_path: str) -> None:
    """绘制上下两个面板的蜡烛图与成交量，并保存到文件。"""
    # 构造图与四个子轴：上价、上量、下价、下量
    fig = plt.figure(figsize=(12, 8))
    gs = fig.add_gridspec(4, 1, height_ratios=[3, 1, 3, 1], hspace=0.35)

    ax_price_top = fig.add_subplot(gs[0])
    ax_vol_top = fig.add_subplot(gs[1], sharex=ax_price_top)
    ax_price_bottom = fig.add_subplot(gs[2])
    ax_vol_bottom = fig.add_subplot(gs[3], sharex=ax_price_bottom)

    # 设置红涨绿跌的配色
    mc = mpf.make_marketcolors(
        up='red',
        down='green',
        edge='inherit',
        wick='inherit',
        volume='inherit'
    )
    style_rg = mpf.make_mpf_style(marketcolors=mc)

    # 上面板
    mpf.plot(source_ohlcv, type='candle', ax=ax_price_top, volume=ax_vol_top,
             style=style_rg, xrotation=0, datetime_format='%Y-%m-%d')
    ax_price_top.set_title(title_top, fontsize=11)

    # 下面板
    mpf.plot(hist_ohlcv, type='candle', ax=ax_price_bottom, volume=ax_vol_bottom,
             style=style_rg, xrotation=0, datetime_format='%Y-%m-%d')
    ax_price_bottom.set_title(title_bottom, fontsize=11)

    # 保存
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    fig.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description='从Pearson分析日志绘制上下对比K线图')
    parser.add_argument('--log', required=True, help='日志文件路径')
    parser.add_argument('--output-dir', default=None, help='输出图片目录')
    parser.add_argument('--source-stock', default=None, help='覆盖源数据股票代码')
    parser.add_argument('--only-index', type=int, default=None, help='仅绘制指定期间索引，如 1')
    args = parser.parse_args()

    log_path = args.log
    out_dir = args.output_dir

    eval_start, inferred_source_stock, periods = parse_log(log_path)

    # 源股票确定优先级：参数覆盖 > 日志中目标股票首个
    source_stock = args.source_stock or inferred_source_stock
    if source_stock is None:
        raise ValueError('无法确定源数据股票，请通过 --source-stock 指定或确保日志包含“目标股票”行。')

    if eval_start is None:
        raise ValueError('无法在日志中解析“评测数据窗口”，请确认日志包含该行。')

    # 评测窗口日期（截去时间部分）
    eval_start_date = _to_date_str(eval_start)
    # eval_end 在日志中存在，但我们直接按索引切片更稳妥；若解析到则使用
    eval_end_date = None
    # 从日志再取一次 end
    eval_window_match = RE_EVAL_WINDOW.search(open(log_path, 'r', encoding='utf-8-sig').read())
    if eval_window_match:
        eval_end_date = _to_date_str(eval_window_match.group(2).strip())

    if not periods:
        raise ValueError('日志中未解析到任何高相关期间记录。')

    # 输出目录
    if out_dir is None:
        out_dir = os.path.join(os.path.dirname(log_path), 'kline_plots')
    os.makedirs(out_dir, exist_ok=True)

    # 加载器
    loader = StockDataLoader()

    # 加载源股票全量数据并按评测窗口截取（索引为datetime）
    src_df_full = loader.load_stock_data(source_stock, time_frame='daily')
    if src_df_full is None or src_df_full.empty:
        raise ValueError(f'无法加载源股票 {source_stock} 的日线数据。')

    # 只保留 open/close/volume
    src_df_full = src_df_full[['open', 'close', 'volume']].copy()

    # 过滤评测窗口：从 eval_start_date 起，长度与历史期间长度一致；若 eval_end_date 可用则按区间
    # 日志中窗口大小通常为固定值（如15）；我们根据每个历史期间的长度来确定源窗口长度

    drawn_count = 0
    for period in periods:
        if args.only_index is not None and period['idx'] != args.only_index:
            continue

        hist_stock = period['stock']
        hist_start_date = _to_date_str(period['start'])
        hist_end_date = _to_date_str(period['end'])
        corr_value = period.get('corr')

        # 加载历史股票窗口数据
        hist_df_full = loader.load_stock_data(hist_stock, time_frame='daily')
        if hist_df_full is None or hist_df_full.empty:
            print(f"跳过 期间#{period['idx']} - 无法加载历史股票 {hist_stock} 数据")
            continue
        hist_df_full = hist_df_full[['open', 'close', 'volume']].copy()

        try:
            hist_slice = hist_df_full.loc[hist_start_date:hist_end_date]
        except Exception:
            # 若索引不是DatetimeIndex，尝试转换
            hist_df_full.index = pd.to_datetime(hist_df_full.index)
            hist_slice = hist_df_full.loc[hist_start_date:hist_end_date]

        if hist_slice.empty:
            print(f"跳过 期间#{period['idx']} - 历史窗口切片为空: {hist_stock} {hist_start_date}~{hist_end_date}")
            continue

        window_len = len(hist_slice)

        # 历史面板：在对比区间后追加10个交易日
        # 保持源面板长度不变（仍按 window_len 对齐），仅底部面板扩展
        # 确保索引为 DatetimeIndex
        if not isinstance(hist_df_full.index, pd.DatetimeIndex):
            hist_df_full.index = pd.to_datetime(hist_df_full.index)
        extra_after = pd.DataFrame()
        try:
            end_idx = hist_slice.index[-1]
            # 找到结束日期在全量数据中的位置
            pos = hist_df_full.index.get_loc(end_idx)
            extra_after = hist_df_full.iloc[pos + 1: pos + 1 + 10]
        except Exception:
            extra_after = pd.DataFrame()

        # 源窗口切片：从评测窗口终点向前取同样长度，或直接按评测窗口的起止日期
        if eval_end_date is not None:
            try:
                src_eval_slice = src_df_full.loc[eval_start_date:eval_end_date]
            except Exception:
                src_df_full.index = pd.to_datetime(src_df_full.index)
                src_eval_slice = src_df_full.loc[eval_start_date:eval_end_date]
        else:
            # 若缺少评测窗口结束日期，则以评测开始日期作为窗口末尾，向前取 window_len
            src_df_full.index = pd.to_datetime(src_df_full.index)
            # 找到评测开始日期在索引中的位置
            if eval_start_date in src_df_full.index.strftime('%Y-%m-%d'):
                # 定位该日期的索引位置
                idx_pos = src_df_full.index.strftime('%Y-%m-%d').tolist().index(eval_start_date)
                start_pos = max(0, idx_pos - window_len + 1)
                src_eval_slice = src_df_full.iloc[start_pos:idx_pos + 1]
            else:
                # 若找不到，直接取最后 window_len 条作为评测窗口
                src_eval_slice = src_df_full.iloc[-window_len:]

        # 对齐长度：若评测窗口与历史窗口长度不一致，尽量截断为相同长度
        min_len = min(len(src_eval_slice), window_len)
        src_eval_slice = src_eval_slice.tail(min_len)
        # 历史对比用于对齐的主体（与源同长度）
        hist_aligned = hist_slice.tail(min_len)
        # 历史面板用于绘图的切片（附加后续10日）
        hist_plot_slice = pd.concat([hist_aligned, extra_after]) if not extra_after.empty else hist_aligned

        if min_len < 3:
            print(f"跳过 期间#{period['idx']} - 有效长度过短: {min_len}")
            continue

        # 为保证上下面板的K线数量对齐：
        # 若底部面板（hist_plot_slice）比顶部（src_eval_slice）更长，则为顶部补齐空白行
        src_eval_slice = pad_with_blank_rows(src_eval_slice, len(hist_plot_slice))

        # 准备OHLCV
        src_ohlcv = prepare_ohlcv(src_eval_slice)
        hist_ohlcv = prepare_ohlcv(hist_plot_slice)
        if src_ohlcv is None or hist_ohlcv is None:
            print(f"跳过 期间#{period['idx']} - OHLCV准备失败（缺少列）")
            continue

        title_top = f"源数据 {source_stock} | 评测窗口: {src_eval_slice.index.min().strftime('%Y-%m-%d')}~{src_eval_slice.index.max().strftime('%Y-%m-%d')}"
        title_bottom = (
            f"历史 {hist_stock} | {hist_start_date}~{hist_end_date}"
            f" (+后续10交易日) | 相关: {corr_value if corr_value is not None else 'N/A'}"
        )

        # 在文件名中附加相关系数（若可用），便于检索
        if corr_value is not None:
            corr_str = f"{corr_value:.6f}"
            save_name = (
                f"kline_compare_idx{period['idx']}_"
                f"{source_stock}_vs_{hist_stock}_"
                f"{hist_start_date}_{hist_end_date}_corr{corr_str}.png"
            )
        else:
            save_name = (
                f"kline_compare_idx{period['idx']}_"
                f"{source_stock}_vs_{hist_stock}_"
                f"{hist_start_date}_{hist_end_date}.png"
            )
        save_path = os.path.join(out_dir, save_name)

        try:
            plot_two_panels(src_ohlcv, hist_ohlcv, title_top, title_bottom, save_path)
            drawn_count += 1
            print(f"✅ 已生成: {save_path}")
        except Exception as e:
            print(f"❌ 绘制失败 期间#{period['idx']}: {e}")

    if drawn_count == 0:
        print('未生成任何图像，请检查日志格式与数据可用性。')


if __name__ == '__main__':
    main()