"""
NEPSE Data Scraper Module

Fetches stock market data from the NEPSE API including:
- Top 20 gainers (stocks with highest percentage price increase)
- Top 20 turnover (stocks with highest trading volume in NPR)
- Top 20 relative strength (stocks outperforming the market)

Relative Strength (RS) is calculated as:
  RS = Stock % Change - Market Index % Change
A positive RS means the stock is outperforming the market.
"""

import requests
from datetime import datetime


class NepseScraper:
    """
    Scrapes NEPSE market data using authenticated API sessions.
    """

    BASE_URL = "https://www.nepalstock.com.np"

    # NEPSE API endpoints (discovered from frontend JS analysis)
    ENDPOINTS = {
        "gainers": "/api/nots/top-ten/top-gainer?all=true",
        "losers": "/api/nots/top-ten/top-loser?all=true",
        "turnover": "/api/nots/top-ten/turnover?all=true",
        "volume": "/api/nots/top-ten/trade?all=true",
        "transactions": "/api/nots/top-ten/transaction?all=true",
        "market_open": "/api/nots/nepse-data/market-open",
        "neprise_index": "/api/nots/neprise-index",
        "index": "/api/nots/index",
    }

    def __init__(self, session):
        """
        Initialize scraper with an authenticated session.
        
        Args:
            session: Authenticated requests session from NepseAuth
        """
        self.session = session

    def _fetch(self, endpoint_key):
        """Fetch data from a NEPSE API endpoint."""
        url = f"{self.BASE_URL}{self.ENDPOINTS[endpoint_key]}"
        resp = self.session.get(url)
        resp.raise_for_status()
        if not resp.text:
            return []
        return resp.json()

    def get_market_status(self):
        """
        Check if the NEPSE market is currently open.
        
        Returns:
            dict: Market status with 'isOpen' and 'asOf' fields.
        """
        try:
            return self._fetch("market_open")
        except Exception as e:
            print(f"[Scraper] Warning: Could not fetch market status: {e}")
            return {"isOpen": "CLOSE", "asOf": datetime.now().isoformat()}

    def get_top_gainers(self, limit=20):
        """
        Fetch top gaining stocks from NEPSE.
        
        Args:
            limit: Number of top gainers to return (default: 20)
            
        Returns:
            list: Top N gainers sorted by percentage change (descending).
        """
        print("[Scraper] Fetching top gainers...")
        data = self._fetch("gainers")

        # Sort by percentage change (descending) and take top N
        sorted_data = sorted(data, key=lambda x: x.get("percentageChange", 0), reverse=True)
        result = sorted_data[:limit]

        print(f"[Scraper] Got {len(result)} top gainers (from {len(data)} total)")
        return result

    def get_top_turnover(self, limit=20):
        """
        Fetch top stocks by turnover from NEPSE.
        
        Args:
            limit: Number of top turnover stocks to return (default: 20)
            
        Returns:
            list: Top N turnover stocks sorted by turnover amount (descending).
        """
        print("[Scraper] Fetching top turnover stocks...")
        data = self._fetch("turnover")

        # Sort by turnover (descending) and take top N
        sorted_data = sorted(data, key=lambda x: x.get("turnover", 0), reverse=True)
        result = sorted_data[:limit]

        print(f"[Scraper] Got {len(result)} top turnover stocks (from {len(data)} total)")
        return result

    def get_top_volume(self, limit=20):
        """
        Fetch top stocks by traded volume (shares) from NEPSE.
        
        Args:
            limit: Number of top volume stocks to return (default: 20)
            
        Returns:
            list: Top N volume stocks sorted by shares traded (descending).
        """
        print("[Scraper] Fetching top volume stocks...")
        data = self._fetch("volume")

        # Sort by sharesTraded (descending) and take top N
        sorted_data = sorted(data, key=lambda x: x.get("shareTraded", 0), reverse=True)
        result = sorted_data[:limit]

        print(f"[Scraper] Got {len(result)} top volume stocks (from {len(data)} total)")
        return result

    def get_top_transactions(self, limit=20):
        """
        Fetch top stocks by number of transactions from NEPSE.
        
        Args:
            limit: Number of top transaction stocks to return (default: 20)
            
        Returns:
            list: Top N transaction stocks sorted by total trades (descending).
        """
        print("[Scraper] Fetching top transaction stocks...")
        data = self._fetch("transactions")

        # Sort by totalTrades (descending) and take top N
        sorted_data = sorted(data, key=lambda x: x.get("totalTrades", 0), reverse=True)
        result = sorted_data[:limit]

        print(f"[Scraper] Got {len(result)} top transaction stocks (from {len(data)} total)")
        return result

    def get_relative_strength_stocks(self, limit=20):
        """
        Calculate and return top 20 relative strength stocks.
        
        Relative Strength (RS) = Stock % Change - Market Index % Change
        
        Uses all gaining stocks (positive % change) and ranks them by
        their performance relative to the overall market.
        
        The market average % change is computed from all gainers as a
        proxy for the market direction when direct index data is unavailable.
        
        Args:
            limit: Number of top RS stocks to return (default: 20)
            
        Returns:
            list: Top N relative strength stocks sorted by RS value (descending).
        """
        print("[Scraper] Calculating relative strength stocks...")

        # Get all gainers data (stocks with positive % change)
        gainers_data = self._fetch("gainers")

        if not gainers_data:
            print("[Scraper] No gainers data available for RS calculation")
            return []

        # Filter to only gainers (positive % change)
        gainers_only = [s for s in gainers_data if s.get("percentageChange", 0) > 0]

        if not gainers_only:
            print("[Scraper] No positive-gaining stocks found")
            return []

        # Calculate market average % change from all gainers as a proxy
        market_avg_pct = sum(s["percentageChange"] for s in gainers_only) / len(gainers_only)

        # Calculate Relative Strength for each gainer
        rs_stocks = []
        for stock in gainers_only:
            rs_value = stock["percentageChange"] - market_avg_pct
            rs_stocks.append(
                {
                    "symbol": stock["symbol"],
                    "securityName": stock.get("securityName", ""),
                    "securityId": stock.get("securityId", ""),
                    "ltp": stock.get("ltp", stock.get("cp", 0)),
                    "closingPrice": stock.get("cp", 0),
                    "percentageChange": stock["percentageChange"],
                    "pointChange": stock.get("pointChange", 0),
                    "marketAvgPctChange": round(market_avg_pct, 2),
                    "relativeStrength": round(rs_value, 2),
                }
            )

        # Sort by relative strength (descending) and take top N
        rs_stocks.sort(key=lambda x: x["relativeStrength"], reverse=True)
        result = rs_stocks[:limit]

        print(
            f"[Scraper] Got {len(result)} relative strength stocks "
            f"(market avg: {market_avg_pct:.2f}%)"
        )
        return result

    def get_all_data(self, limit=20):
        """
        Fetch all categories of data in one call.
        
        Args:
            limit: Number of top stocks per category (default: 20)
            
        Returns:
            dict: Dictionary with gainers, turnover, and relative_strength keys.
        """
        market_status = self.get_market_status()
        print(f"\n[Scraper] Market Status: {market_status.get('isOpen', 'UNKNOWN')}")
        print(f"[Scraper] As of: {market_status.get('asOf', 'N/A')}\n")

        return {
            "market_status": market_status,
            "top_gainers": self.get_top_gainers(limit),
            "top_turnover": self.get_top_turnover(limit),
            "top_volume": self.get_top_volume(limit),
            "top_transactions": self.get_top_transactions(limit),
            "relative_strength": self.get_relative_strength_stocks(limit),
        }
