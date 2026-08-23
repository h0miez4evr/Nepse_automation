"""
CSV Manager Module

Manages CSV files for NEPSE market data. Each CSV file contains historical
data with a 'trading_day' column to distinguish data from different trading days.

Files created:
- nepse_top20_gainers.csv      - Top 20 gainers per trading day
- nepse_top20_turnover.csv     - Top 20 turnover stocks per trading day
- nepse_top20_volume.csv       - Top 20 volume stocks per trading day
- nepse_top20_transactions.csv - Top 20 most traded stocks per trading day
- nepse_top20_relative_strength.csv - Top 20 relative strength stocks per trading day
"""

import os
import csv
from datetime import datetime


class CSVManager:
    """
    Manages CSV files for NEPSE market data with daily trading day tracking.
    
    Each CSV file has:
    - trading_day: Date of the trading session (YYYY-MM-DD)
    - rank: Rank of the stock in its category (1-20)
    - Symbol: Stock ticker symbol
    - Security_Name: Full company name
    - Additional data columns specific to each category
    """

    # Default directory for CSV files
    DEFAULT_DIR = "nepse_data"

    def __init__(self, output_dir=None):
        """
        Initialize CSV manager.
        
        Args:
            output_dir: Directory to save CSV files (default: ./nepse_data/)
        """
        self.output_dir = output_dir or self.DEFAULT_DIR
        os.makedirs(self.output_dir, exist_ok=True)

    def _get_csv_path(self, filename):
        """Get the full path for a CSV file."""
        return os.path.join(self.output_dir, filename)

    def _ensure_file_exists(self, filepath, headers):
        """Create a CSV file with headers if it doesn't exist."""
        if not os.path.exists(filepath):
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()

    def _read_existing_data(self, filepath):
        """Read all existing data from a CSV file."""
        if not os.path.exists(filepath):
            return []
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)

    def _write_data(self, filepath, headers, data):
        """Write all data (headers + rows) to a CSV file."""
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(data)

    def _is_duplicate_day(self, existing_data, trading_day):
        """Check if data already exists for the given trading day."""
        return any(row.get("trading_day") == trading_day for row in existing_data)

    def _get_latest_rows(self, filepath, exclude_trading_day=None):
        """
        Get the most recent trading day's rows from a CSV file.
        
        Args:
            filepath: Path to CSV file.
            exclude_trading_day: Optional trading_day to exclude when finding latest.
        
        Returns:
            list: Rows from the most recent trading day, or empty list if none.
        """
        existing = self._read_existing_data(filepath)
        if not existing:
            return []

        # Find all unique trading days
        trading_days = set(r.get("trading_day", "") for r in existing)
        if exclude_trading_day and exclude_trading_day in trading_days:
            trading_days.discard(exclude_trading_day)
        if not trading_days:
            return []

        latest_day = max(trading_days)
        return [r for r in existing if r.get("trading_day") == latest_day]

    def _is_data_same(self, new_rows, existing_rows, compare_keys):
        """
        Compare new data against existing CSV data by key fields.
        
        Ignores trading_day and rank — only compares actual stock data.
        
        Args:
            new_rows: List of dicts with new scraped data.
            existing_rows: List of dicts from the latest CSV trading day.
            compare_keys: List of field names to compare.
        
        Returns:
            bool: True if data is identical, False if different.
        """
        if len(new_rows) != len(existing_rows):
            return False

        # Sort both by symbol for consistent comparison
        new_sorted = sorted(new_rows, key=lambda x: x.get("symbol", ""))
        existing_sorted = sorted(existing_rows, key=lambda x: x.get("symbol", ""))

        for new_row, exist_row in zip(new_sorted, existing_sorted):
            for key in compare_keys:
                new_val = str(new_row.get(key, "")).strip()
                exist_val = str(exist_row.get(key, "")).strip()
                if new_val != exist_val:
                    return False
        return True

    def update_gainers_csv(self, gainers_data, trading_day=None):
        """
        Update the gainers CSV file with new data.
        
        Args:
            gainers_data: List of gainer stock dictionaries from scraper
            trading_day: Trading date string (YYYY-MM-DD).
        """
        if not trading_day:
            trading_day = datetime.now().strftime("%Y-%m-%d")

        filepath = self._get_csv_path("nepse_top20_gainers.csv")
        headers = [
            "trading_day",
            "rank",
            "symbol",
            "security_name",
            "security_id",
            "last_traded_price",
            "closing_price",
            "point_change",
            "percentage_change",
        ]

        compare_keys = ["symbol", "security_name", "last_traded_price", "closing_price",
                        "point_change", "percentage_change"]

        # Build new rows
        new_rows = []
        for i, stock in enumerate(gainers_data, 1):
            new_rows.append(
                {
                    "trading_day": trading_day,
                    "rank": i,
                    "symbol": stock.get("symbol", ""),
                    "security_name": stock.get("securityName", ""),
                    "security_id": stock.get("securityId", ""),
                    "last_traded_price": stock.get("ltp", stock.get("cp", "")),
                    "closing_price": stock.get("cp", ""),
                    "point_change": stock.get("pointChange", ""),
                    "percentage_change": stock.get("percentageChange", ""),
                }
            )

        # Compare with latest data in CSV
        latest_rows = self._get_latest_rows(filepath)
        if latest_rows and self._is_data_same(new_rows, latest_rows, compare_keys):
            print(f"[CSV] {filepath} — no changes detected, skipping update")
            return

        # Remove old data for this trading day if it exists
        existing = self._read_existing_data(filepath)
        if self._is_duplicate_day(existing, trading_day):
            existing = [r for r in existing if r.get("trading_day") != trading_day]

        # Combine and sort by trading_day descending, then rank
        all_data = existing + new_rows
        all_data.sort(key=lambda x: (x["trading_day"], int(x.get("rank", 0))), reverse=True)

        self._write_data(filepath, headers, all_data)
        print(f"[CSV] Updated {filepath} with {len(new_rows)} gainers for {trading_day}")

    def update_turnover_csv(self, turnover_data, trading_day=None):
        """
        Update the turnover CSV file with new data.
        
        Args:
            turnover_data: List of turnover stock dictionaries from scraper
            trading_day: Trading date string (YYYY-MM-DD).
        """
        if not trading_day:
            trading_day = datetime.now().strftime("%Y-%m-%d")

        filepath = self._get_csv_path("nepse_top20_turnover.csv")
        headers = [
            "trading_day",
            "rank",
            "symbol",
            "security_name",
            "security_id",
            "closing_price",
            "turnover_npr",
        ]

        compare_keys = ["symbol", "security_name", "closing_price", "turnover_npr"]

        new_rows = []
        for i, stock in enumerate(turnover_data, 1):
            new_rows.append(
                {
                    "trading_day": trading_day,
                    "rank": i,
                    "symbol": stock.get("symbol", ""),
                    "security_name": stock.get("securityName", ""),
                    "security_id": stock.get("securityId", ""),
                    "closing_price": stock.get("closingPrice", ""),
                    "turnover_npr": stock.get("turnover", ""),
                }
            )

        latest_rows = self._get_latest_rows(filepath)
        if latest_rows and self._is_data_same(new_rows, latest_rows, compare_keys):
            print(f"[CSV] {filepath} — no changes detected, skipping update")
            return

        existing = self._read_existing_data(filepath)
        if self._is_duplicate_day(existing, trading_day):
            existing = [r for r in existing if r.get("trading_day") != trading_day]

        all_data = existing + new_rows
        all_data.sort(key=lambda x: (x["trading_day"], int(x.get("rank", 0))), reverse=True)

        self._write_data(filepath, headers, all_data)
        print(f"[CSV] Updated {filepath} with {len(new_rows)} turnover stocks for {trading_day}")

    def update_volume_csv(self, volume_data, trading_day=None):
        """
        Update the volume CSV file with new data.
        
        Args:
            volume_data: List of volume stock dictionaries from scraper
            trading_day: Trading date string (YYYY-MM-DD).
        """
        if not trading_day:
            trading_day = datetime.now().strftime("%Y-%m-%d")

        filepath = self._get_csv_path("nepse_top20_volume.csv")
        headers = [
            "trading_day",
            "rank",
            "symbol",
            "security_name",
            "security_id",
            "closing_price",
            "shares_traded",
        ]

        compare_keys = ["symbol", "security_name", "closing_price", "shares_traded"]

        new_rows = []
        for i, stock in enumerate(volume_data, 1):
            new_rows.append(
                {
                    "trading_day": trading_day,
                    "rank": i,
                    "symbol": stock.get("symbol", ""),
                    "security_name": stock.get("securityName", ""),
                    "security_id": stock.get("securityId", ""),
                    "closing_price": stock.get("closingPrice", ""),
                    "shares_traded": stock.get("shareTraded", ""),
                }
            )

        latest_rows = self._get_latest_rows(filepath)
        if latest_rows and self._is_data_same(new_rows, latest_rows, compare_keys):
            print(f"[CSV] {filepath} — no changes detected, skipping update")
            return

        existing = self._read_existing_data(filepath)
        if self._is_duplicate_day(existing, trading_day):
            existing = [r for r in existing if r.get("trading_day") != trading_day]

        all_data = existing + new_rows
        all_data.sort(key=lambda x: (x["trading_day"], int(x.get("rank", 0))), reverse=True)

        self._write_data(filepath, headers, all_data)
        print(f"[CSV] Updated {filepath} with {len(new_rows)} volume stocks for {trading_day}")

    def update_transactions_csv(self, transactions_data, trading_day=None):
        """
        Update the transactions CSV file with new data.
        
        Args:
            transactions_data: List of transaction stock dictionaries from scraper
            trading_day: Trading date string (YYYY-MM-DD).
        """
        if not trading_day:
            trading_day = datetime.now().strftime("%Y-%m-%d")

        filepath = self._get_csv_path("nepse_top20_transactions.csv")
        headers = [
            "trading_day",
            "rank",
            "symbol",
            "security_name",
            "security_id",
            "last_traded_price",
            "total_trades",
        ]

        compare_keys = ["symbol", "security_name", "last_traded_price", "total_trades"]

        new_rows = []
        for i, stock in enumerate(transactions_data, 1):
            new_rows.append(
                {
                    "trading_day": trading_day,
                    "rank": i,
                    "symbol": stock.get("symbol", ""),
                    "security_name": stock.get("securityName", ""),
                    "security_id": stock.get("securityId", ""),
                    "last_traded_price": stock.get("lastTradedPrice", ""),
                    "total_trades": stock.get("totalTrades", ""),
                }
            )

        latest_rows = self._get_latest_rows(filepath)
        if latest_rows and self._is_data_same(new_rows, latest_rows, compare_keys):
            print(f"[CSV] {filepath} — no changes detected, skipping update")
            return

        existing = self._read_existing_data(filepath)
        if self._is_duplicate_day(existing, trading_day):
            existing = [r for r in existing if r.get("trading_day") != trading_day]

        all_data = existing + new_rows
        all_data.sort(key=lambda x: (x["trading_day"], int(x.get("rank", 0))), reverse=True)

        self._write_data(filepath, headers, all_data)
        print(f"[CSV] Updated {filepath} with {len(new_rows)} transaction stocks for {trading_day}")

    def update_relative_strength_csv(self, rs_data, trading_day=None):
        """
        Update the relative strength CSV file with new data.
        
        Args:
            rs_data: List of relative strength stock dictionaries from scraper
            trading_day: Trading date string (YYYY-MM-DD).
        """
        if not trading_day:
            trading_day = datetime.now().strftime("%Y-%m-%d")

        filepath = self._get_csv_path("nepse_top20_relative_strength.csv")
        headers = [
            "trading_day",
            "rank",
            "symbol",
            "security_name",
            "security_id",
            "last_traded_price",
            "closing_price",
            "percentage_change",
            "point_change",
            "market_avg_pct_change",
            "relative_strength",
        ]

        compare_keys = ["symbol", "security_name", "last_traded_price", "closing_price",
                        "percentage_change", "point_change", "market_avg_pct_change",
                        "relative_strength"]

        new_rows = []
        for i, stock in enumerate(rs_data, 1):
            new_rows.append(
                {
                    "trading_day": trading_day,
                    "rank": i,
                    "symbol": stock.get("symbol", ""),
                    "security_name": stock.get("securityName", ""),
                    "security_id": stock.get("securityId", ""),
                    "last_traded_price": stock.get("ltp", ""),
                    "closing_price": stock.get("closingPrice", ""),
                    "percentage_change": stock.get("percentageChange", ""),
                    "point_change": stock.get("pointChange", ""),
                    "market_avg_pct_change": stock.get("marketAvgPctChange", ""),
                    "relative_strength": stock.get("relativeStrength", ""),
                }
            )

        latest_rows = self._get_latest_rows(filepath)
        if latest_rows and self._is_data_same(new_rows, latest_rows, compare_keys):
            print(f"[CSV] {filepath} — no changes detected, skipping update")
            return

        existing = self._read_existing_data(filepath)
        if self._is_duplicate_day(existing, trading_day):
            existing = [r for r in existing if r.get("trading_day") != trading_day]

        all_data = existing + new_rows
        all_data.sort(key=lambda x: (x["trading_day"], int(x.get("rank", 0))), reverse=True)

        self._write_data(filepath, headers, all_data)
        print(
            f"[CSV] Updated {filepath} with {len(new_rows)} "
            f"relative strength stocks for {trading_day}"
        )

    def update_all(self, all_data, trading_day=None):
        """
        Update all CSV files with scraped data.
        
        Args:
            all_data: Dictionary with all data categories from scraper.get_all_data()
            trading_day: Trading date string (YYYY-MM-DD).
        """
        if not trading_day:
            trading_day = datetime.now().strftime("%Y-%m-%d")

        print(f"\n[CSV] Updating all CSV files for {trading_day}...")
        print("=" * 60)

        self.update_gainers_csv(all_data.get("top_gainers", []), trading_day)
        self.update_turnover_csv(all_data.get("top_turnover", []), trading_day)
        self.update_volume_csv(all_data.get("top_volume", []), trading_day)
        self.update_transactions_csv(all_data.get("top_transactions", []), trading_day)
        self.update_relative_strength_csv(all_data.get("relative_strength", []), trading_day)

        print("=" * 60)
        print(f"[CSV] All files updated successfully!")

    def get_summary(self):
        """
        Get a summary of all CSV files and their data.
        
        Returns:
            dict: Summary with file names, row counts, and date ranges.
        """
        summary = {}
        csv_files = [
            "nepse_top20_gainers.csv",
            "nepse_top20_turnover.csv",
            "nepse_top20_volume.csv",
            "nepse_top20_transactions.csv",
            "nepse_top20_relative_strength.csv",
        ]

        for filename in csv_files:
            filepath = self._get_csv_path(filename)
            if os.path.exists(filepath):
                data = self._read_existing_data(filepath)
                dates = set(r.get("trading_day", "") for r in data)
                summary[filename] = {
                    "total_rows": len(data),
                    "trading_days": sorted(dates, reverse=True),
                    "latest_date": max(dates) if dates else "N/A",
                }
            else:
                summary[filename] = {
                    "total_rows": 0,
                    "trading_days": [],
                    "latest_date": "N/A",
                }

        return summary
