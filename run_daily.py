import sys
import os
import argparse
from pathlib import Path
from datetime import datetime

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).parent))

from nepse_selection_agent.github_fetcher import fetch_github_data
from nepse_selection_agent.scorer import AIScorer, export_possible_stocks_csv


def main():
    parser = argparse.ArgumentParser(description="Daily NEPSE Stock Selection Update")
    parser.add_argument("--top", type=int, default=50,
                        help="Number of top stocks to export (default: 50)")
    parser.add_argument("--output", type=str, default="possibleStocks.csv",
                        help="Output CSV filepath (default: possibleStocks.csv)")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress verbose output")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run scoring without writing the CSV file")
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    verbose = not args.quiet

    if verbose:
        print(f"\n{'='*60}")
        print(f"  NEPSE Daily Stock Selection Update")
        print(f"  {timestamp}")
        print(f"{'='*60}")

    # Step 1: Fetch data from GitHub
    try:
        daily_data = fetch_github_data(verbose=verbose)
    except Exception as e:
        print(f"[ERROR] Failed to fetch data from GitHub: {e}")
        sys.exit(1)

    if not daily_data:
        print("[ERROR] No trading data found. Exiting.")
        sys.exit(1)

    if verbose:
        print(f"\n Data summary:")
        print(f"   Trading days loaded: {len(daily_data)}")
        print(f"   Date range: {daily_data[0].date} → {daily_data[-1].date}")

    # Step 2: Run AI scoring
    if verbose:
        print(f"\nRunning AI scoring across 10 strategy engines...")

    scorer = AIScorer()
    scores = scorer.score_all(daily_data)

    if verbose:
        print(f"Evaluated {len(scores)} stocks meeting threshold")

    if not scores:
        print("[WARNING] No stocks scored above threshold. Check data quality.")
        sys.exit(1)

    # Step 3: Export to CSV
    if args.dry_run:
        if verbose:
            print(f"\n DRY RUN - Would export top {args.top} stocks:")
            for i, s in enumerate(scores[:args.top], 1):
                print(f"   {i:2d}. {s.symbol:<10s} Score: {s.composite_score:.1f} [{s.conviction}]")
        return

    try:
        csv_path = export_possible_stocks_csv(
            scores,
            filepath=args.output,
            top_n=args.top,
        )
    except Exception as e:
        print(f"[ERROR] Failed to export CSV: {e}")
        sys.exit(1)

    # Step 4: Summary
    if verbose:
        print(f"\n{'='*60}")
        print(f"   Daily update complete!")
        print(f"  Output: {csv_path}")
        print(f"  Top 5 picks:")
        for i, s in enumerate(scores[:5], 1):
            print(f"     {i}. {s.symbol:<10s} Score: {s.composite_score:.1f} [{s.conviction}]")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()
