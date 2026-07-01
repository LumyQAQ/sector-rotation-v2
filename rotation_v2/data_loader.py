from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


LEGACY_DB = Path("/Users/ziranfeng/Desktop/洪攻略/CMLM/轮动图/sample_data.db")


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_db_candidates() -> list[Path]:
    root = project_root()
    return [
        root / "sample_data.db",
        root.parent / "轮动图" / "sample_data.db",
        LEGACY_DB,
    ]


def resolve_db_path(db_path: str | Path | None = None) -> Path:
    if db_path:
        path = Path(db_path).expanduser()
        if path.exists():
            return path
        raise FileNotFoundError(f"找不到数据库: {path}")

    for candidate in default_db_candidates():
        if candidate.exists():
            return candidate
    searched = "\n".join(str(path) for path in default_db_candidates())
    raise FileNotFoundError(f"找不到 sample_data.db，已检查:\n{searched}")


def database_signature(db_path: str | Path | None = None) -> tuple[str, int, int]:
    path = resolve_db_path(db_path)
    stat = path.stat()
    return str(path.resolve()), stat.st_mtime_ns, stat.st_size


def load_sqlite_data(db_path: str | Path | None = None) -> tuple[pd.DataFrame, pd.DataFrame, Path]:
    path = resolve_db_path(db_path)
    with sqlite3.connect(path) as conn:
        stock_daily = pd.read_sql("SELECT * FROM stock_daily", conn)
        stock_industry = pd.read_sql("SELECT * FROM stock_industry", conn)
    if stock_daily.empty:
        raise ValueError(f"{path} 的 stock_daily 为空。")
    if stock_industry.empty:
        raise ValueError(f"{path} 的 stock_industry 为空。")
    return stock_daily, stock_industry, path


def available_dates(stock_daily: pd.DataFrame) -> list[str]:
    dates = pd.to_datetime(stock_daily["日期"], errors="coerce").dropna().sort_values().dt.strftime("%Y-%m-%d")
    return dates.drop_duplicates().tolist()
