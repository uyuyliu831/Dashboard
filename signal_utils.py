from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Iterable
from urllib.parse import quote_plus

import numpy as np
import pandas as pd
from sqlalchemy import create_engine


APP_NAME = "多资产信号仪表盘"

DEFAULT_DB_CONFIG = {
    "host": "rm-bp18ts6lq1shnvk949o.mysql.rds.aliyuncs.com",
    "port": "3306",
    "user": "sz_read",
    "password": "SZ666888r!",
    "database": "sz_hist_db",
    "table": "strategies_daily_data",
}

ASSET_NAME_MAP: Dict[str, str] = {
    "A.DCE.M": "豆1",
    "AL.SHF.M": "沪铝",
    "AU.SHF.M": "沪金",
    "B.DCE.M": "豆2",
    "BU.SHF.M": "沥青",
    "CF.CZC.M": "棉花",
    "CS.DCE.M": "玉米淀粉",
    "CU.SHF.M": "沪铜",
    "FG.CZC.M": "玻璃",
    "HC.SHF.M": "热卷",
    "I.DCE.M": "铁矿石",
    "IC.CFE.M": "中证500",
    "IF.CFE.M": "沪深300",
    "JD.DCE.M": "鸡蛋",
    "JM.DCE.M": "焦煤",
    "L.DCE.M": "塑料",
    "M.DCE.M": "豆粕",
    "MA.CZC.M": "甲醇",
    "OI.CZC.M": "菜油",
    "P.DCE.M": "棕榈油",
    "PP.DCE.M": "聚丙烯",
    "RB.SHF.M": "螺纹钢",
    "RM.CZC.M": "菜粕",
    "RU.SHF.M": "橡胶",
    "SA.CZC.M": "纯碱",
    "SC.INE.M": "原油",
    "SF.CZC.M": "硅铁",
    "SM.CZC.M": "锰硅",
    "SR.CZC.M": "白糖",
    "T.CFE.M": "十年国债",
    "TA.CZC.M": "PTA",
    "TF.CFE.M": "五年国债",
    "V.DCE.M": "PVC",
    "Y.DCE.M": "豆油",
    "ZN.SHF.M": "沪锌",
}

ASSET_GROUPS: Dict[str, list[str]] = {
    "油脂油料": ["A.DCE.M", "B.DCE.M", "M.DCE.M", "OI.CZC.M", "P.DCE.M", "RM.CZC.M", "Y.DCE.M"],
    "软商品": ["CF.CZC.M", "RU.SHF.M", "SR.CZC.M"],
    "黑色金属": ["HC.SHF.M", "I.DCE.M", "JM.DCE.M", "RB.SHF.M", "SF.CZC.M", "SM.CZC.M"],
    "有色金属": ["AL.SHF.M", "CU.SHF.M", "ZN.SHF.M"],
    "贵金属": ["AU.SHF.M"],
    "能源": ["BU.SHF.M", "SC.INE.M"],
    "化工": ["L.DCE.M", "MA.CZC.M", "PP.DCE.M", "TA.CZC.M", "V.DCE.M"],
    "权益": ["IC.CFE.M", "IF.CFE.M"],
    "债券": ["T.CFE.M", "TF.CFE.M"],
    "谷物与禽畜": ["JD.DCE.M", "CS.DCE.M"],
    "非金属建材": ["FG.CZC.M", "SA.CZC.M"],
}

ASSET_CATEGORY_MAP: Dict[str, str] = {
    ASSET_NAME_MAP[code]: group
    for group, codes in ASSET_GROUPS.items()
    for code in codes
}

ASSET_CODES = list(ASSET_NAME_MAP.keys())
MOMCO_WINDOWS = {"1个月": 21, "3个月": 63, "6个月": 126}
SKNS_WINDOWS = {"6个月": 126, "1年": 252, "2年": 504}
VOL_CONFIG = {
    "短期波动率": (21, 252),
    "中期波动率": (63, 504),
}


@dataclass
class SnapshotResult:
    snapshot_date: pd.Timestamp
    table: pd.DataFrame
    price_matrix: pd.DataFrame


def get_db_config() -> dict[str, str]:
    return {
        "host": os.getenv("DB_HOST", DEFAULT_DB_CONFIG["host"]),
        "port": os.getenv("DB_PORT", DEFAULT_DB_CONFIG["port"]),
        "user": os.getenv("DB_USER", DEFAULT_DB_CONFIG["user"]),
        "password": os.getenv("DB_PASSWORD", DEFAULT_DB_CONFIG["password"]),
        "database": os.getenv("DB_NAME", DEFAULT_DB_CONFIG["database"]),
        "table": os.getenv("DB_TABLE", DEFAULT_DB_CONFIG["table"]),
    }


def fetch_price_history(
    start_date: str = "2020-01-01",
    asset_codes: Iterable[str] | None = None,
    db_config: dict[str, str] | None = None,
) -> pd.DataFrame:
    codes = list(asset_codes or ASSET_CODES)
    cfg = db_config or get_db_config()

    quoted_password = quote_plus(cfg["password"])
    engine = create_engine(
        f"mysql+pymysql://{cfg['user']}:{quoted_password}@{cfg['host']}:{cfg['port']}/{cfg['database']}"
    )

    quoted_codes = ", ".join([f"'{code}'" for code in codes])
    query = f"""
        SELECT strategy_code, date, `close`
        FROM `{cfg['table']}`
        WHERE strategy_code IN ({quoted_codes})
          AND date >= '{start_date}'
        ORDER BY date, strategy_code
    """

    with engine.begin() as conn:
        df = pd.read_sql_query(query, conn)

    df["date"] = pd.to_datetime(df["date"])
    return df


def prepare_price_matrix(df: pd.DataFrame) -> pd.DataFrame:
    prices = (
        df.pivot_table(index="date", columns="strategy_code", values="close", aggfunc="last")
        .sort_index()
        .sort_index(axis=1)
    )
    return prices[[code for code in ASSET_CODES if code in prices.columns]]


def get_available_snapshot_dates(df: pd.DataFrame) -> pd.DatetimeIndex:
    prices = prepare_price_matrix(df)
    common_dates = prices.dropna(how="any").index.sort_values()
    return pd.DatetimeIndex(common_dates)


def resolve_snapshot_date(
    prices: pd.DataFrame,
    as_of_date: str | pd.Timestamp | None = None,
    exact_match: bool = False,
) -> pd.Timestamp | None:
    common_dates = prices.dropna(how="any").index.sort_values()
    if common_dates.empty:
        return None

    if as_of_date is None:
        return pd.Timestamp(common_dates.max())

    target_date = pd.Timestamp(as_of_date).normalize()
    matching_dates = common_dates[common_dates.normalize() == target_date]
    if exact_match:
        if len(matching_dates) == 0:
            return None
        return pd.Timestamp(matching_dates.max())

    eligible_dates = common_dates[common_dates <= target_date]
    if len(eligible_dates) == 0:
        return None
    return pd.Timestamp(eligible_dates.max())


def momco(series: pd.Series, fast: int, slow: int, window: int) -> pd.Series:
    fast_ema = series.ewm(span=fast, adjust=False).mean()
    slow_ema = series.ewm(span=slow, adjust=False).mean()
    spread = fast_ema - slow_ema
    spread_std = spread.ewm(span=window, adjust=False).std()
    return spread / spread_std.replace(0, np.nan)


def reg_skewness(series: pd.Series) -> float:
    clean = series.dropna()
    n = len(clean)
    if n == 0:
        return np.nan

    mean = clean.mean()
    third_moment = ((clean - mean) ** 3).mean()
    std_cubed = clean.std(ddof=1) ** 3
    if std_cubed == 0 or np.isnan(std_cubed):
        return np.nan

    skew = third_moment / std_cubed
    return skew * np.sqrt(n / 6.0)


def rolling_zscore(series: pd.Series, window: int) -> pd.Series:
    rolling_mean = series.rolling(window).mean()
    rolling_std = series.rolling(window).std()
    return (series - rolling_mean) / rolling_std.replace(0, np.nan)


def scale_minus1_to_1(series: pd.Series, cap: float) -> pd.Series:
    return (series / cap).clip(-1, 1)


def scale_zero_to_one(series: pd.Series, lower: float = -2.0, upper: float = 2.0) -> pd.Series:
    return ((series - lower) / (upper - lower)).clip(0, 1)


def compute_snapshot(
    df: pd.DataFrame,
    as_of_date: str | pd.Timestamp | None = None,
    exact_match: bool = False,
) -> SnapshotResult | None:
    prices = prepare_price_matrix(df)
    snapshot_date = resolve_snapshot_date(prices, as_of_date=as_of_date, exact_match=exact_match)
    if snapshot_date is None:
        return None

    prices = prices.loc[:snapshot_date]
    simple_returns = prices.pct_change()
    log_returns = np.log(prices / prices.shift(1))

    table_parts: dict[tuple[str, str], pd.Series] = {}

    for label, slow_window in MOMCO_WINDOWS.items():
        signal = prices.apply(lambda col: momco(col, fast=5, slow=slow_window, window=slow_window))
        table_parts[("趋势", label)] = scale_minus1_to_1(signal.loc[snapshot_date], cap=2.0)

    for label, window in SKNS_WINDOWS.items():
        raw_signal = -log_returns.loc[:snapshot_date].apply(lambda col: reg_skewness(col.tail(window)))
        table_parts[("反转", label)] = scale_minus1_to_1(raw_signal, cap=3.0)

    for label, (vol_window, z_window) in VOL_CONFIG.items():
        rolling_vol = simple_returns.rolling(vol_window).std()
        z_signal = rolling_vol.apply(lambda col: rolling_zscore(col, z_window))
        table_parts[("波动", label)] = scale_zero_to_one(z_signal.loc[snapshot_date])

    snapshot = pd.DataFrame(table_parts).reindex(ASSET_CODES)
    snapshot.index = [ASSET_NAME_MAP[code] for code in snapshot.index]
    snapshot.index.name = "资产名称"

    return SnapshotResult(snapshot_date=snapshot_date, table=snapshot, price_matrix=prices)


def _blend_color(start: tuple[int, int, int], end: tuple[int, int, int], weight: float) -> tuple[int, int, int]:
    weight = float(np.clip(weight, 0, 1))
    return tuple(int(round(s + (e - s) * weight)) for s, e in zip(start, end))


def heatmap_style(value: object, group: str | None = None, difference_mode: bool = False) -> str:
    if isinstance(value, str) or pd.isna(value):
        return ""

    numeric = float(value)
    red = (224, 153, 153)
    white = (250, 250, 252)
    blue = (157, 184, 232)

    if difference_mode:
        caps = {"趋势": 2.0, "反转": 2.0, "波动": 1.0}
        cap = caps.get(group)
        if cap is None:
            return ""
        normalized = float(np.clip((numeric / cap + 1) / 2, 0, 1))
    elif group in ("趋势", "反转"):
        normalized = float(np.clip((numeric + 1) / 2, 0, 1))
    elif group == "波动":
        normalized = float(np.clip(numeric, 0, 1))
    else:
        return ""

    if normalized <= 0.5:
        rgb = _blend_color(blue, white, normalized / 0.5)
    else:
        rgb = _blend_color(white, red, (normalized - 0.5) / 0.5)

    return f"background-color: rgb({rgb[0]}, {rgb[1]}, {rgb[2]}); color: #243142;"
