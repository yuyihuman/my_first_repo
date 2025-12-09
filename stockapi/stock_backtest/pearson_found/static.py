import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def _parse_bin(col):
    parts = col.split('_')
    idx = col.find('_')
    s = col[idx+1:]
    a, b = s.split('_to_')
    return float(a), float(b)

def _field_columns(df, field):
    cols = [c for c in df.columns if c.startswith(f"{field}_")]
    cols_sorted = sorted(cols, key=lambda c: _parse_bin(c)[0], reverse=True)
    return cols_sorted

def _aggregate(df, field):
    cols = _field_columns(df, field)
    counts = df[cols].sum(axis=0).to_numpy(dtype=np.float64)
    total = counts.sum()
    if total <= 0:
        pct = np.zeros_like(counts)
    else:
        pct = counts / total * 100.0
    labels = [c[len(field)+1:] for c in cols]
    return labels, pct

def _plot_on_ax(ax, labels, pct, title):
    x = np.arange(len(labels))
    ax.bar(x, pct, color='#4C78A8')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha='right')
    ax.set_ylabel('Percent (%)')
    ax.set_title(title)
    for i, v in enumerate(pct):
        ax.text(x[i], v + (max(pct)*0.01 if len(pct) else 0.1), f"{v:.2f}%", ha='center', va='bottom', fontsize=8)

def main():
    base_dir = os.path.dirname(__file__)
    csv_path = os.path.join(base_dir, 'static.csv')
    if not os.path.exists(csv_path):
        print('static.csv not found')
        sys.exit(1)
    try:
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
    except Exception:
        df = pd.read_csv(csv_path)
    if df.empty:
        print('static.csv is empty')
        sys.exit(1)
    labels_diff_10, pct_diff_10 = _aggregate(df, 'diff_10')
    labels_close_10, pct_close_10 = _aggregate(df, 'close_10')
    labels_volume_10, pct_volume_10 = _aggregate(df, 'volume_10')
    labels_diff_5, pct_diff_5 = _aggregate(df, 'diff_5')
    labels_close_5, pct_close_5 = _aggregate(df, 'close_5')
    labels_volume_5, pct_volume_5 = _aggregate(df, 'volume_5')
    fig, axes = plt.subplots(nrows=6, ncols=1, figsize=(16, 24))
    _plot_on_ax(axes[0], labels_diff_10, pct_diff_10, 'diff_10')
    _plot_on_ax(axes[1], labels_close_10, pct_close_10, 'close_10')
    _plot_on_ax(axes[2], labels_volume_10, pct_volume_10, 'volume_10')
    _plot_on_ax(axes[3], labels_diff_5, pct_diff_5, 'diff_5')
    _plot_on_ax(axes[4], labels_close_5, pct_close_5, 'close_5')
    _plot_on_ax(axes[5], labels_volume_5, pct_volume_5, 'volume_5')
    fig.tight_layout()
    out_path = os.path.join(base_dir, 'static.png')
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    print('saved: static.png')

if __name__ == '__main__':
    main()

