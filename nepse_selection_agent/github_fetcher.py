import io
import os
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from datetime import datetime

from .data_loader import DailyData, StockRecord
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/h0miez4evr/Nepse_automation./main/nepse_data"
CSV_FILES = {
    "nepse_top20_gainers.csv": "gainer",
    "nepse_top20_turnover.csv": "turnover",
    "nepse_top20_relative_strength.csv": "rs",
    "nepse_top20_volume.csv": "volume",
    "nepse_top20_transactions.csv": "transactions",
}


def _fetch_csv_from_github(filename: str) -> Optional[pd.DataFrame]:
    url = f"{GITHUB_RAW_BASE}/{filename}"
    try:
        req = Request(url, headers={"User-Agent": "NepseAgent/1.0"})
        with urlopen(req, timeout=30) as response:
            content = response.read().decode("utf-8")
            df = pd.read_csv(io.StringIO(content))
            return df
    except HTTPError as e:
        print(f"[WARN] HTTP {e.code} fetching {filename}: {e.reason}")
        return None
    except URLError as e:
        print(f"[WARN] Network error fetching {filename}: {e.reason}")
        return None
    except Exception as e:
        print(f"[WARN] Error parsing {filename}: {e}")
        return None


def _safe_float(val) -> float:
    if pd.isna(val):
        return 0.0
    s = str(val).strip().replace(",", "").replace("%", "").replace("Rs.", "").replace("Rs", "")
    try:
        return float(s)
    except ValueError:
        return 0.0


def _parse_gainers(df: pd.DataFrame) -> List[StockRecord]:
    records = []
    for _, row in df.iterrows():
        symbol = str(row.get("symbol", "")).strip()
        if not symbol or symbol.lower() == "nan":
            continue
        records.append(StockRecord(
            symbol=symbol,
            ltp=_safe_float(row.get("last_traded_price", row.get("closing_price", 0))),
            change=_safe_float(row.get("point_change", 0)),
            percent_change=_safe_float(row.get("percentage_change", 0)),
            volume=0,
            turnover=0,
            high=_safe_float(row.get("closing_price", 0)),
            low=_safe_float(row.get("closing_price", 0)),
            open=0,
            prev_close=0,
            rs_score=0,
            source_list="gainer",
        ))
    return records


def _parse_turnover(df: pd.DataFrame) -> List[StockRecord]:
    records = []
    for _, row in df.iterrows():
        symbol = str(row.get("symbol", "")).strip()
        if not symbol or symbol.lower() == "nan":
            continue
        turnover_val = _safe_float(row.get("turnover_npr", 0))
        closing = _safe_float(row.get("closing_price", 0))
        records.append(StockRecord(
            symbol=symbol,
            ltp=closing,
            change=0,
            percent_change=0,
            volume=0,
            turnover=turnover_val,
            high=closing,
            low=closing,
            open=0,
            prev_close=0,
            rs_score=0,
            source_list="turnover",
        ))
    return records


def _parse_relative_strength(df: pd.DataFrame) -> List[StockRecord]:
    records = []
    for _, row in df.iterrows():
        symbol = str(row.get("symbol", "")).strip()
        if not symbol or symbol.lower() == "nan":
            continue
        records.append(StockRecord(
            symbol=symbol,
            ltp=_safe_float(row.get("last_traded_price", row.get("closing_price", 0))),
            change=_safe_float(row.get("point_change", 0)),
            percent_change=_safe_float(row.get("percentage_change", 0)),
            volume=0,
            turnover=0,
            high=_safe_float(row.get("closing_price", 0)),
            low=_safe_float(row.get("closing_price", 0)),
            open=0,
            prev_close=0,
            rs_score=_safe_float(row.get("relative_strength", 0)),
            source_list="rs",
        ))
    return records


def _parse_volume(df: pd.DataFrame) -> List[StockRecord]:
    records = []
    for _, row in df.iterrows():
        symbol = str(row.get("symbol", "")).strip()
        if not symbol or symbol.lower() == "nan":
            continue
        closing = _safe_float(row.get("closing_price", 0))
        records.append(StockRecord(
            symbol=symbol,
            ltp=closing,
            change=0,
            percent_change=0,
            volume=_safe_float(row.get("shares_traded", 0)),
            turnover=0,
            high=closing,
            low=closing,
            open=0,
            prev_close=0,
            rs_score=0,
            source_list="volume",
        ))
    return records


def _parse_transactions(df: pd.DataFrame) -> List[StockRecord]:
    records = []
    for _, row in df.iterrows():
        symbol = str(row.get("symbol", "")).strip()
        if not symbol or symbol.lower() == "nan":
            continue
        records.append(StockRecord(
            symbol=symbol,
            ltp=_safe_float(row.get("last_traded_price", 0)),
            change=0,
            percent_change=0,
            volume=_safe_float(row.get("total_trades", 0)),
            turnover=0,
            high=0,
            low=0,
            open=0,
            prev_close=0,
            rs_score=0,
            source_list="transactions",
        ))
    return records
PARSERS = {
    "gainer": _parse_gainers,
    "turnover": _parse_turnover,
    "rs": _parse_relative_strength,
    "volume": _parse_volume,
    "transactions": _parse_transactions,
}


def fetch_github_data(verbose: bool = True) -> List[DailyData]:
    if verbose:
        print("\n Fetching NEPSE data from GitHub...")
        print(f"   Repository: h0miez4evr/Nepse_automation.")
    csv_dfs: Dict[str, Optional[pd.DataFrame]] = {}
    for filename, list_type in CSV_FILES.items():
        if verbose:
            print(f"   Downloading {filename}...", end=" ")
        df = _fetch_csv_from_github(filename)
        csv_dfs[list_type] = df
        if df is not None:
            if verbose:
                print(f"({len(df)} rows)")
        else:
            if verbose:
                print(" (failed)")
    all_dates = set()
    for df in csv_dfs.values():
        if df is not None and "trading_day" in df.columns:
            all_dates.update(df["trading_day"].dropna().unique())

    if not all_dates:
        print("[ERROR] No trading days found in any CSV file.")
        return []
    daily_data = []
    for date_str in sorted(all_dates):
        day = DailyData(date=date_str)

        for list_type, df in csv_dfs.items():
            if df is None or "trading_day" not in df.columns:
                continue

            day_df = df[df["trading_day"] == date_str]
            if day_df.empty:
                continue

            parser = PARSERS.get(list_type)
            if parser:
                records = parser(day_df)
                if list_type == "gainer":
                    day.gainers.extend(records)
                elif list_type == "turnover":
                    day.turnovers.extend(records)
                elif list_type == "rs":
                    day.relative_strength.extend(records)
                elif list_type == "volume":
                    # Store volume data in a new attribute
                    if not hasattr(day, "volume_leaders"):
                        day.volume_leaders = []
                    day.volume_leaders.extend(records)
                elif list_type == "transactions":
                    # Store transaction data in a new attribute
                    if not hasattr(day, "transaction_leaders"):
                        day.transaction_leaders = []
                    day.transaction_leaders.extend(records)

        daily_data.append(day)

    if verbose:
        print(f"\n Loaded {len(daily_data)} trading days from GitHub")
        dates_str = ", ".join(d.date for d in daily_data[:5])
        if len(daily_data) > 5:
            dates_str += f", ... (+{len(daily_data) - 5} more)"
        print(f"   Dates: {dates_str}")

    return daily_data
