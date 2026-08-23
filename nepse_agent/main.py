#!/usr/bin/env python3
"""
NEPSE Data Scraper Agent - Main Entry Point

An AI agent that scrapes Nepal Stock Exchange (NEPSE) data and updates
CSV files with daily trading day data.

Usage:
    python -m nepse_agent.main              # Scrape today's data
    python -m nepse_agent.main --date 2083-05-08  # Specify trading day
    python -m nepse_agent.main --summary    # Show CSV file summary
    python -m nepse_agent.main --help       # Show help

The agent fetches:
    - Top 20 gainers (stocks with highest % price increase)
    - Top 20 turnover stocks (highest NPR trading volume)
    - Top 20 volume stocks (most shares traded)
    - Top 20 transaction stocks (most individual trades)
    - Top 20 relative strength stocks (outperforming market average)

Output CSV files (in ./nepse_data/ directory):
    - nepse_top20_gainers.csv
    - nepse_top20_turnover.csv
    - nepse_top20_volume.csv
    - nepse_top20_transactions.csv
    - nepse_top20_relative_strength.csv
"""

import argparse
import sys
import os
from datetime import datetime

# Ensure the package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nepse_agent.auth import NepseAuth
from nepse_agent.scraper import NepseScraper
from nepse_agent.csv_manager import CSVManager


def run_scraper(trading_day=None, output_dir=None, top_n=20, verbose=False):
    """
    Main scraping workflow.
    
    Args:
        trading_day: Trading date (YYYY-MM-DD). Auto-detected if None.
        output_dir: Directory for CSV output files.
        top_n: Number of top stocks per category.
        verbose: Enable verbose output.
    """
    print("=" * 60)
    print("  NEPSE Data Scraper Agent")
    print("  Nepal Stock Exchange Daily Data Collection")
    print("=" * 60)
    print()

    # Step 1: Initialize authentication
    print("[1/4] Initializing NEPSE API authentication...")
    try:
        auth = NepseAuth()
    except Exception as e:
        print(f"[ERROR] Failed to initialize authentication: {e}")
        print("[ERROR] Please check your internet connection and try again.")
        return False

    # Step 2: Get authenticated session
    print("[2/4] Establishing authenticated session...")
    try:
        session = auth.get_authenticated_session()
    except Exception as e:
        print(f"[ERROR] Failed to authenticate: {e}")
        return False

    # Step 3: Scrape data
    print("[3/4] Scraping NEPSE market data...")
    try:
        scraper = NepseScraper(session)
        all_data = scraper.get_all_data(limit=top_n)
    except Exception as e:
        print(f"[ERROR] Failed to scrape data: {e}")
        return False

    # Step 4: Determine trading day from API response if not provided
    if not trading_day:
        market_status = all_data.get("market_status", {})
        as_of = market_status.get("asOf", "")
        if as_of:
            # Extract date portion from ISO timestamp (e.g., "2026-08-23T15:30:00+05:45")
            trading_day = as_of[:10]
            print(f"[INFO] Detected last trading day from API: {trading_day}")
        else:
            trading_day = datetime.now().strftime("%Y-%m-%d")
            print(f"[INFO] No trading day from API, using today: {trading_day}")

    # Step 5: Save to CSV
    print("[4/4] Saving data to CSV files...")
    try:
        csv_manager = CSVManager(output_dir=output_dir)
        csv_manager.update_all(all_data, trading_day=trading_day)
    except Exception as e:
        print(f"[ERROR] Failed to save CSV files: {e}")
        return False

    # Print summary
    print()
    print("=" * 60)
    print("  Scraping Complete!")
    print("=" * 60)

    market_status = all_data.get("market_status", {})
    print(f"\n  Market Status: {market_status.get('isOpen', 'UNKNOWN')}")
    print(f"  As of: {market_status.get('asOf', 'N/A')}")
    print(f"  Trading Day: {trading_day or 'Auto-detected'}")
    print()

    # Print top results
    if all_data.get("top_gainers"):
        print("  Top 5 Gainers:")
        for i, stock in enumerate(all_data["top_gainers"][:5], 1):
            pct = stock.get("percentageChange", 0)
            print(f"    {i}. {stock['symbol']}: {pct:+.2f}% (Rs {stock.get('ltp', stock.get('cp', 'N/A'))})")

    if all_data.get("top_turnover"):
        print("\n  Top 5 Turnover:")
        for i, stock in enumerate(all_data["top_turnover"][:5], 1):
            turnover = stock.get("turnover", 0)
            turnover_cr = turnover / 10_000_000  # Convert to Crore
            print(f"    {i}. {stock['symbol']}: Rs {turnover_cr:.2f} Cr")

    if all_data.get("relative_strength"):
        print("\n  Top 5 Relative Strength:")
        for i, stock in enumerate(all_data["relative_strength"][:5], 1):
            rs = stock.get("relativeStrength", 0)
            print(f"    {i}. {stock['symbol']}: RS={rs:+.2f} ({stock.get('percentageChange', 0):+.2f}%)")

    # Show CSV file locations
    print("\n  CSV Files:")
    csv_dir = output_dir or CSVManager.DEFAULT_DIR
    csv_files = [
        "nepse_top20_gainers.csv",
        "nepse_top20_turnover.csv",
        "nepse_top20_volume.csv",
        "nepse_top20_transactions.csv",
        "nepse_top20_relative_strength.csv",
    ]
    for f in csv_files:
        filepath = os.path.join(csv_dir, f)
        exists = "✓" if os.path.exists(filepath) else "✗"
        print(f"    [{exists}] {filepath}")

    print()
    return True


def show_summary(output_dir=None):
    """Show summary of existing CSV data."""
    csv_manager = CSVManager(output_dir=output_dir)
    summary = csv_manager.get_summary()

    print("\n" + "=" * 60)
    print("  NEPSE Data CSV Summary")
    print("=" * 60)

    for filename, info in summary.items():
        print(f"\n  📊 {filename}")
        print(f"     Total Rows: {info['total_rows']}")
        print(f"     Latest Date: {info['latest_date']}")
        if info["trading_days"]:
            print(f"     Trading Days: {', '.join(info['trading_days'][:5])}")
            if len(info["trading_days"]) > 5:
                print(f"                    ... and {len(info['trading_days']) - 5} more")

    print()


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="NEPSE Data Scraper Agent - Scrape daily NEPSE market data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m nepse_agent.main                          # Scrape today's data
    python -m nepse_agent.main --date 2083-05-08       # Specify trading day
    python -m nepse_agent.main --summary               # Show data summary
    python -m nepse_agent.main --top 30                # Get top 30 per category
    python -m nepse_agent.main --output ./my_data      # Custom output directory
        """,
    )

    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Trading day date in YYYY-MM-DD format (default: auto-detect)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help=f"Output directory for CSV files (default: {CSVManager.DEFAULT_DIR})",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="Number of top stocks per category (default: 20)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show summary of existing CSV data",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    args = parser.parse_args()

    if args.summary:
        show_summary(output_dir=args.output)
    else:
        success = run_scraper(
            trading_day=args.date,
            output_dir=args.output,
            top_n=args.top,
            verbose=args.verbose,
        )
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
