from __future__ import annotations

import argparse
from pathlib import Path

from rotation_v2.data_loader import load_sqlite_data
from rotation_v2.metrics import build_rotation_model
from rotation_v2.report import write_html_report
from rotation_v2.snapshot import render_snapshot_png


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成每日收盘后板块轮动可视化。")
    parser.add_argument("--db", default=None, help="sample_data.db 路径；默认自动寻找旧版数据库。")
    parser.add_argument("--date", default=None, help="指定交易日，例如 2026-04-30；默认使用数据库最新交易日。")
    parser.add_argument("--out", default="outputs", help="输出目录。")
    parser.add_argument("--tail-days", type=int, default=18, help="轮动轨迹回看交易日数量。")
    parser.add_argument("--no-png", action="store_true", help="只生成 HTML/CSV，不生成长图 PNG。")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    stock_daily, stock_industry, db_path = load_sqlite_data(args.db)
    model = build_rotation_model(stock_daily, stock_industry, as_of=args.date, tail_days=args.tail_days)

    out_root = Path(args.out).expanduser()
    day_dir = out_root / model.as_of
    day_dir.mkdir(parents=True, exist_ok=True)

    sector_csv = day_dir / "rotation_data.csv"
    family_csv = day_dir / "rotation_family.csv"
    leaders_csv = day_dir / "rotation_leaders.csv"
    html_path = day_dir / "rotation_report.html"
    png_path = day_dir / "rotation_snapshot.png"

    model.sector_frame.to_csv(sector_csv, index=False, encoding="utf-8-sig")
    model.family_frame.to_csv(family_csv, index=False, encoding="utf-8-sig")
    model.leaders_frame.to_csv(leaders_csv, index=False, encoding="utf-8-sig")
    write_html_report(model, html_path)
    if not args.no_png:
        render_snapshot_png(model, png_path)

    print(f"数据源: {db_path}")
    print(f"交易日: {model.as_of}")
    print(f"市场状态: {model.market_state}")
    print(f"CSV: {sector_csv}")
    print(f"主线家族: {family_csv}")
    print(f"个股穿透: {leaders_csv}")
    print(f"HTML: {html_path}")
    if not args.no_png:
        print(f"PNG: {png_path}")


if __name__ == "__main__":
    main()
