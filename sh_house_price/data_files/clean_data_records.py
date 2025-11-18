import argparse
import json
from pathlib import Path
import datetime as dt
from typing import List, Tuple, Optional


def parse_cutoff(date_str: str) -> dt.date:
    """Parse user input date to a date object.

    Supported formats:
    - YYYY-MM-DD
    - YYYY.MM.DD
    - YYYY/MM/DD
    - YYYYMMDD
    """
    fmts = ["%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d", "%Y%m%d"]
    for fmt in fmts:
        try:
            return dt.datetime.strptime(date_str, fmt).date()
        except ValueError:
            pass
    raise ValueError(
        f"无法解析日期 '{date_str}'，请使用格式：YYYY-MM-DD、YYYY.MM.DD、YYYY/MM/DD 或 YYYYMMDD"
    )


def parse_record_date(date_str: str) -> Optional[dt.date]:
    """Parse record date string from files (commonly 'YYYY.MM.DD')."""
    fmts = ["%Y.%m.%d", "%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"]
    for fmt in fmts:
        try:
            return dt.datetime.strptime(date_str.strip(), fmt).date()
        except Exception:
            continue
    return None


def filter_records(records: List[dict], cutoff: dt.date) -> Tuple[List[dict], int]:
    """Keep records whose date <= cutoff. Return filtered list and removed count.

    If a record has no parsable date, it is retained (and counted as kept).
    """
    kept: List[dict] = []
    removed = 0
    for rec in records:
        ds = rec.get("date")
        rdate = parse_record_date(ds) if isinstance(ds, str) else None
        if rdate is None:
            kept.append(rec)
        else:
            if rdate <= cutoff:
                kept.append(rec)
            else:
                removed += 1
    return kept, removed


def process_file(fpath: Path, cutoff: dt.date, write: bool) -> Tuple[int, int, int]:
    """Process a single JSON file. Returns (total, kept, removed)."""
    try:
        text = fpath.read_text(encoding="utf-8")
    except Exception as e:
        print(f"读取失败: {fpath} -> {e}")
        return (0, 0, 0)

    try:
        data = json.loads(text)
    except Exception as e:
        print(f"解析JSON失败: {fpath} -> {e}")
        return (0, 0, 0)

    if not isinstance(data, list):
        print(f"跳过（非数组JSON）: {fpath}")
        return (0, 0, 0)

    filtered, removed = filter_records(data, cutoff)
    total = len(data)
    kept = len(filtered)

    if write:
        try:
            fpath.write_text(json.dumps(filtered, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"写入失败: {fpath} -> {e}")
    return (total, kept, removed)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "按指定日期清理 data_files 中的记录：删除所有记录日期严格晚于该日期的条目。\n"
            "例如传入 2025-10-31，将删除 2025.11.01 及之后的记录。"
        )
    )
    parser.add_argument("--date", required=True, help="指定日期，例如 2025-10-31 或 2025.10.31")
    parser.add_argument(
        "--dir",
        default=r"c:\Users\17701\github\my_first_repo\sh_house_price\data_files",
        help="根目录，默认为项目的 data_files",
    )
    parser.add_argument(
        "--file",
        help="仅处理指定文件名（例如 sjxc 或 sjxc.json），不填则处理目录下所有JSON文件",
    )
    parser.add_argument("--write", action="store_true", help="实际写回（不加则为预览）")

    args = parser.parse_args()

    try:
        cutoff = parse_cutoff(args.date)
    except ValueError as e:
        print(str(e))
        raise SystemExit(2)

    root = Path(args.dir)
    if not root.exists() or not root.is_dir():
        print(f"目录不存在或不是文件夹: {root}")
        raise SystemExit(2)

    print(f"目标目录: {root}")
    print(f"日期阈值: {cutoff}（保留 <= 阈值；删除 > 阈值）")

    targets: List[Path] = []
    if args.file:
        candidate = root / args.file
        if candidate.exists() and candidate.is_file():
            targets.append(candidate)
        else:
            # 试试无后缀/加后缀两种情况
            if not candidate.suffix:
                alt = candidate.with_suffix(".json")
                if alt.exists() and alt.is_file():
                    targets.append(alt)
            if not targets:
                print(f"指定文件不存在: {candidate}")
                raise SystemExit(2)
    else:
        # 处理目录下所有可能的JSON文件（包含无后缀但为JSON的）
        for p in root.iterdir():
            if p.is_file() and (p.suffix.lower() in {".json", ""}):
                targets.append(p)

    if not targets:
        print("未找到可处理的文件。")
        return

    total_all = kept_all = removed_all = 0
    for f in targets:
        total, kept, removed = process_file(f, cutoff, args.write)
        total_all += total
        kept_all += kept
        removed_all += removed
        print(
            f"{f.name}: 总计 {total}，保留 {kept}，删除 {removed}"
            + ("（已写回）" if args.write else "（预览）")
        )

    print(
        f"汇总: 总计 {total_all}，保留 {kept_all}，删除 {removed_all}"
        + ("（已写回）" if args.write else "（预览）")
    )


if __name__ == "__main__":
    main()