import argparse
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "批量运行 pearson_analyzer_gpu_3.py：以 30 组×30 天（共 900 天）为窗口，"
            "通过 Akshare 获取交易日，逐日执行提测命令。"
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # 以用户示例为默认值，可在命令行覆盖
    parser.add_argument(
        "--stock_code", default="top1500", help="传递给 pearson_analyzer_gpu_3.py 的 --stock_code"
    )
    parser.add_argument(
        "--comparison_mode", default="top1500", help="传递给 pearson_analyzer_gpu_3.py 的 --comparison_mode"
    )
    parser.add_argument(
        "--csv_filename", default="test.csv", help="传递给 pearson_analyzer_gpu_3.py 的 --csv_filename"
    )
    parser.add_argument(
        "--evaluation_days", type=int, default=30, help="传递给 pearson_analyzer_gpu_3.py 的 --evaluation_days"
    )

    # 批量控制参数
    parser.add_argument(
        "--anchor_date",
        default="latest",
        help=(
            "锚定结束日期（含），格式 YYYY-MM-DD；默认 'latest' 表示使用 Akshare 获取的最近一个交易日"
        ),
    )
    parser.add_argument(
        "--groups", type=int, default=20, help="分组数量（默认 20 组）"
    )
    parser.add_argument(
        "--step_trading_days", type=int, default=30, help="每组锚点间相隔的交易日数量（默认 30 个交易日）"
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="仅打印计划（分组与交易日），不实际运行子进程",
    )
    parser.add_argument(
        "--sleep_seconds",
        type=float,
        default=0.0,
        help="每次调用之间的等待秒数（默认 0）",
    )
    parser.add_argument(
        "--append_date_to_csv",
        action="store_true",
        help="为每个交易日给 csv 文件名追加日期后缀，避免覆盖",
    )
    return parser.parse_args()


def get_trading_calendar_upto(end_date: str):
    """获取截至 end_date 的所有交易日（升序列表，YYYY-MM-DD）。"""
    try:
        import akshare as ak
        import pandas as pd
    except Exception as e:
        raise SystemExit(
            "未安装或无法导入 Akshare，请先执行: pip install -U akshare\n"
            f"错误信息: {e}"
        )

    df = ak.tool_trade_date_hist_sina()
    if "trade_date" not in df.columns:
        raise SystemExit("Akshare 接口返回不含 'trade_date' 列，可能版本不兼容。请升级 Akshare。")

    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
    e = pd.to_datetime(end_date).date()
    df = df[df["trade_date"] <= e]
    if df.empty:
        raise SystemExit("交易日数据为空，请检查 Akshare 接口或传入的结束日期。")
    dates = sorted(d.strftime("%Y-%m-%d") for d in df["trade_date"].tolist())
    return dates


def get_latest_trading_date():
    """返回截至今天的最近一个交易日（YYYY-MM-DD）。"""
    try:
        import akshare as ak
        import pandas as pd
    except Exception as e:
        raise SystemExit(
            "未安装或无法导入 Akshare，请先执行: pip install -U akshare\n"
            f"错误信息: {e}"
        )

    df = ak.tool_trade_date_hist_sina()
    if "trade_date" not in df.columns:
        raise SystemExit("Akshare 接口返回不含 'trade_date' 列，可能版本不兼容。请升级 Akshare。")

    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
    today = datetime.today().date()
    df = df[df["trade_date"] <= today]
    if df.empty:
        raise SystemExit("未获取到交易日数据，请检查 Akshare 接口或网络。")
    latest = max(df["trade_date"])  # 按日期最大值即最近交易日
    return latest.strftime("%Y-%m-%d")


def build_anchor_trading_dates(anchor_date_str: str, groups: int, step_trading_days: int):
    """基于交易日历构造锚点日期列表。

    锚点序列：最近交易日、再向前 30 个交易日、再向前 30 个交易日……共 groups 个。
    若交易日数量不足，将自动减少实际组数。
    返回顺序为：从最近到更早（降序执行）。
    """
    calendar = get_trading_calendar_upto(anchor_date_str)
    anchors = []
    last_idx = len(calendar) - 1
    for i in range(groups):
        idx = last_idx - i * step_trading_days
        if idx < 0:
            break
        anchors.append(calendar[idx])
    return anchors


def run_backtests_for_anchors(
    anchors,
    stock_code: str,
    comparison_mode: str,
    csv_filename: str,
    evaluation_days: int,
    append_date_to_csv: bool,
    sleep_seconds: float,
    script_path: Path,
    dry_run: bool,
):
    """按锚点日期（每隔固定交易日）调用 pearson_analyzer_gpu_3.py。"""
    import time

    for d in anchors:
        csv_out = csv_filename
        if append_date_to_csv:
            stem, suffix = Path(csv_filename).stem, Path(csv_filename).suffix
            csv_out = f"{stem}_{d}{suffix or '.csv'}"

        cmd = [
            sys.executable,
            str(script_path),
            "--stock_code",
            stock_code,
            "--comparison_mode",
            comparison_mode,
            "--csv_filename",
            csv_out,
            "--backtest_date",
            d,
            "--evaluation_days",
            str(evaluation_days),
        ]

        prefix = "DRY-RUN:" if dry_run else "RUN:"
        print(prefix, " ".join(cmd))
        if not dry_run:
            subprocess.run(cmd, check=True)

        if sleep_seconds > 0:
            time.sleep(sleep_seconds)


def main():
    args = parse_args()

    # 确定锚定日期：默认使用最近交易日
    anchor_date = (
        get_latest_trading_date()
        if str(args.anchor_date).lower() in {"latest", "auto"}
        else args.anchor_date
    )

    # 基于交易日历构造锚点（每次向前 step_trading_days 个交易日）
    anchors = build_anchor_trading_dates(anchor_date, args.groups, args.step_trading_days)

    # pearson_analyzer_gpu_3.py 路径（与本脚本同目录）
    script_path = Path(__file__).parent / "pearson_analyzer_gpu_3.py"
    if not script_path.exists():
        raise SystemExit(f"未找到 {script_path}，请确认脚本位置正确。")

    total_trading_days = 0
    print(
        f"批量计划：anchor_date={anchor_date}, groups={args.groups}, step_trading_days={args.step_trading_days}, "
        f"evaluation_days={args.evaluation_days}"
    )

    if not anchors:
        print("未构造出任何锚点，可能交易日不足。")
        return

    print("将执行的锚点日期（最近→更早）:", ", ".join(anchors))
    total_trading_days = len(anchors)
    run_backtests_for_anchors(
        anchors=anchors,
        stock_code=args.stock_code,
        comparison_mode=args.comparison_mode,
        csv_filename=args.csv_filename,
        evaluation_days=args.evaluation_days,
        append_date_to_csv=args.append_date_to_csv,
        sleep_seconds=args.sleep_seconds,
        script_path=script_path,
        dry_run=args.dry_run,
    )

    print(f"总执行次数: {total_trading_days}")


if __name__ == "__main__":
    main()