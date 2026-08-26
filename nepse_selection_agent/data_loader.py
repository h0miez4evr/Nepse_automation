import os
import glob
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class StockRecord:
    def __init__(
        self,
        symbol: str,
        ltp: float = 0.0,
        change: float = 0.0,
        percent_change: float = 0.0,
        volume: float = 0.0,
        turnover: float = 0.0,
        high: float = 0.0,
        low: float = 0.0,
        open: float = 0.0,
        prev_close: float = 0.0,
        rs_score: float = 0.0,
        source_list: str = "",
    ):
        self.symbol = symbol.strip().upper()
        self.ltp = ltp
        self.change = change
        self.percent_change = percent_change
        self.volume = volume
        self.turnover = turnover
        self.high = high
        self.low = low
        self.open = open
        self.prev_close = prev_close
        self.rs_score = rs_score
        self.source_list = source_list  # "gainer", "turnover", "rs"


class DailyData:

    def __init__(self, date: str):
        self.date = date
        self.gainers: List[StockRecord] = []
        self.turnovers: List[StockRecord] = []
        self.relative_strength: List[StockRecord] = []
        self.volume_leaders: List[StockRecord] = []
        self.transaction_leaders: List[StockRecord] = []

    def all_stocks(self) -> Dict[str, StockRecord]:
        merged = {}
        all_records = self.gainers + self.turnovers + self.relative_strength + self.volume_leaders + self.transaction_leaders
        for record in all_records:
            if record.symbol in merged:
                existing = merged[record.symbol]
                # Keep best values
                existing.percent_change = max(existing.percent_change, record.percent_change)
                existing.turnover = max(existing.turnover, record.turnover)
                existing.volume = max(existing.volume, record.volume)
                existing.rs_score = max(existing.rs_score, record.rs_score)
                if record.source_list not in existing.source_list:
                    existing.source_list += f",{record.source_list}"
            else:
                merged[record.symbol] = record
        return merged

    def symbols_in_multiple_lists(self) -> Dict[str, int]:
        count = {}
        for record in self.gainers + self.turnovers + self.relative_strength + self.volume_leaders + self.transaction_leaders:
            count[record.symbol] = count.get(record.symbol, 0) + 1
        return {s: c for s, c in count.items() if c >= 2}


def _normalize_column(col: str) -> str:
    col = col.strip().lower()
    mappings = {
        "symbol": "symbol",
        "stock": "symbol",
        "name": "symbol",
        "company": "symbol",
        "code": "symbol",
        "scrip": "symbol",
        "ltp": "ltp",
        "last traded price": "ltp",
        "last_price": "ltp",
        "close": "ltp",
        "price": "ltp",
        "change": "change",
        "change%": "percent_change",
        "% change": "percent_change",
        "%change": "percent_change",
        "percent_change": "percent_change",
        "%chg": "percent_change",
        "change (%)": "percent_change",
        "pct_change": "percent_change",
        "volume": "volume",
        "vol": "volume",
        "turnover": "turnover",
        "turnover (rs)": "turnover",
        "amount": "turnover",
        "high": "high",
        "52w high": "high",
        "low": "low",
        "52w low": "low",
        "open": "open",
        "prev_close": "prev_close",
        "previous close": "prev_close",
        "prev close": "prev_close",
        "rs": "rs_score",
        "rs_score": "rs_score",
        "relative strength": "rs_score",
        "rsi": "rs_score",
    }
    return mappings.get(col, col)


def _parse_numeric(val) -> float:
    """Safely parse a numeric value, handling commas and percentages."""
    if pd.isna(val):
        return 0.0
    s = str(val).strip().replace(",", "").replace("%", "").replace("Rs.", "").replace("Rs", "")
    try:
        return float(s)
    except ValueError:
        return 0.0


def load_csv_file(filepath: str) -> Tuple[List[StockRecord], str]:
    filename = Path(filepath).stem.lower()
    df = pd.read_csv(filepath)
    col_map = {}
    for col in df.columns:
        col_map[col] = _normalize_column(col)
    df = df.rename(columns=col_map)
    list_type = "unknown"
    if "gain" in filename or "top_gainer" in filename or "gainer" in filename:
        list_type = "gainer"
    elif "turnover" in filename or "volume" in filename or "turn" in filename:
        list_type = "turnover"
    elif "rs" in filename or "relative" in filename or "strength" in filename:
        list_type = "rs"
    elif "strong" in filename:
        list_type = "rs"
    if list_type == "unknown":
        if "rs_score" in df.columns and df["rs_score"].sum() > 0:
            list_type = "rs"
        elif "turnover" in df.columns and df["turnover"].sum() > df.get("volume", pd.Series([0])).sum():
            list_type = "turnover"
        else:
            list_type = "gainer"

    records = []
    for _, row in df.iterrows():
        symbol = str(row.get("symbol", "")).strip()
        if not symbol or symbol.lower() == "nan":
            continue
        record = StockRecord(
            symbol=symbol,
            ltp=_parse_numeric(row.get("ltp", 0)),
            change=_parse_numeric(row.get("change", 0)),
            percent_change=_parse_numeric(row.get("percent_change", 0)),
            volume=_parse_numeric(row.get("volume", 0)),
            turnover=_parse_numeric(row.get("turnover", 0)),
            high=_parse_numeric(row.get("high", 0)),
            low=_parse_numeric(row.get("low", 0)),
            open=_parse_numeric(row.get("open", 0)),
            prev_close=_parse_numeric(row.get("prev_close", 0)),
            rs_score=_parse_numeric(row.get("rs_score", 0)),
            source_list=list_type,
        )
        records.append(record)

    return records, list_type


def load_day_directory(dirpath: str) -> Optional[DailyData]:
    csv_files = glob.glob(os.path.join(dirpath, "*.csv"))
    if not csv_files:
        return None

    dirname = Path(dirpath).name
    day = DailyData(date=dirname)

    for f in csv_files:
        records, list_type = load_csv_file(f)
        if list_type == "gainer":
            day.gainers.extend(records)
        elif list_type == "turnover":
            day.turnovers.extend(records)
        elif list_type == "rs":
            day.relative_strength.extend(records)
        else:
            day.gainers.extend(records)

    return day


def load_all_data(data_dir: str) -> List[DailyData]:
    
    all_days = []
    if data_dir is None:
        return _generate_sample_data()
    data_path = Path(data_dir)

    if not data_path.exists():
        print(f"[WARN] Data directory not found: {data_dir}")
        print("[INFO] Using embedded sample data for demonstration.")
        return _generate_sample_data()

    subdirs = [d for d in data_path.iterdir() if d.is_dir()]
    csv_files = list(data_path.glob("*.csv"))

    if subdirs:
        
        for subdir in sorted(subdirs):
            day = load_day_directory(str(subdir))
            if day:
                all_days.append(day)
    elif csv_files:
        
        date_groups = {}
        for f in csv_files:
            parts = f.stem.split("_")
            date_str = parts[0] if len(parts) > 1 else "unknown"
            date_groups.setdefault(date_str, []).append(f)

        for date_str, files in sorted(date_groups.items()):
            day = DailyData(date=date_str)
            for f in files:
                records, list_type = load_csv_file(str(f))
                if list_type == "gainer":
                    day.gainers.extend(records)
                elif list_type == "turnover":
                    day.turnovers.extend(records)
                elif list_type == "rs":
                    day.relative_strength.extend(records)
                else:
                    day.gainers.extend(records)
            all_days.append(day)

    if not all_days:
        return _generate_sample_data()

    return sorted(all_days, key=lambda d: d.date)


def _generate_sample_data() -> List[DailyData]:
    import random
    random.seed(42)

    # Realistic NEPSE stock symbols
    symbols = [
        "NAB", "NICA", "SANIMA", "NMB", "SBL", "LSL", "PCBL", "NABIL",
        "EBL", "HBL", "SCB", "CZB", "MEGA", "PRV", "KBL", "SIDDH",
        "GBIME", "LBL", "MIDBL", "NIMB", "UPCL", "NHPC", "AKPL", "BPCL",
        "CHCL", "EDCL", "JPL", "NHDL", "NEA", "PPCL", "RADHI", "AKO",
        "BBL", "CMBL", "CZBL", "DLBL", "EDBL", "Everest", "FFCL", "GFCL",
        "GRU", "HDL", "HURU", "ICFC", "JBL", "KBL", "LBSL", "MBBL",
        "NBB", "NCF", "NDR", "NFS", "NIL", "NML", "OHL", "PFL",
        "PHCL", "PMHL", "PMLI", "PPCL", "PRDB", "RBBL", "RSDC", "SAPDBL",
        "SBL", "SCL", "SDL", "SHL", "SICL", "SJCL", "SKBBL", "SLBSL",
        "SMB", "SMFED", "SSHL", "STC", "SWMF", "TBBL", "TML", "TPCL",
        "TRH", "TSHL", "TWL", "ULBSL", "UNB", "USHL", "VRLC", "WNL",
    ]

    all_days = []

    for day_offset in range(10):
        date_str = f"2025-01-{13 + day_offset:02d}"
        day = DailyData(date=date_str)

        
        gainers = random.sample(symbols, 20)
        for sym in gainers:
            pct = round(random.uniform(1.0, 9.98), 2)
            ltp = round(random.uniform(50, 2000), 2)
            vol = round(random.uniform(10000, 500000), 0)
            turnover = round(vol * ltp, 0)
            day.gainers.append(StockRecord(
                symbol=sym, ltp=ltp, percent_change=pct,
                change=round(ltp * pct / 100, 2),
                volume=vol, turnover=turnover,
                high=round(ltp * 1.02, 2), low=round(ltp * 0.98, 2),
                open=round(ltp * random.uniform(0.99, 1.01), 2),
                prev_close=round(ltp - ltp * pct / 100, 2),
                source_list="gainer",
            ))

        turnover_stocks = random.sample([s for s in symbols if s not in gainers[:5]], 20)
        for sym in turnover_stocks:
            ltp = round(random.uniform(50, 2000), 2)
            vol = round(random.uniform(200000, 2000000), 0)
            turnover = round(vol * ltp, 0)
            pct = round(random.uniform(-3, 7), 2)
            day.turnovers.append(StockRecord(
                symbol=sym, ltp=ltp, percent_change=pct,
                change=round(ltp * pct / 100, 2),
                volume=vol, turnover=turnover,
                high=round(ltp * 1.03, 2), low=round(ltp * 0.97, 2),
                open=round(ltp * random.uniform(0.99, 1.01), 2),
                prev_close=round(ltp - ltp * pct / 100, 2),
                source_list="turnover",
            ))

        rs_stocks = random.sample([s for s in symbols if s not in gainers[:3] and s not in turnover_stocks[:3]], 20)
        for sym in rs_stocks:
            rs = round(random.uniform(60, 99), 1)
            ltp = round(random.uniform(50, 2000), 2)
            pct = round(random.uniform(0.5, 8), 2)
            vol = round(random.uniform(50000, 800000), 0)
            turnover = round(vol * ltp, 0)
            day.relative_strength.append(StockRecord(
                symbol=sym, ltp=ltp, percent_change=pct,
                change=round(ltp * pct / 100, 2),
                volume=vol, turnover=turnover,
                high=round(ltp * 1.02, 2), low=round(ltp * 0.98, 2),
                open=round(ltp * random.uniform(0.99, 1.01), 2),
                prev_close=round(ltp - ltp * pct / 100, 2),
                rs_score=rs, source_list="rs",
            ))

        all_days.append(day)

    return all_days
