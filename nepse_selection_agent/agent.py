

import sys
import os
import json
import argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from nepse_selection_agent.data_loader import load_all_data, DailyData
from nepse_selection_agent.scorer import AIScorer, format_report, format_compact_report, export_possible_stocks_csv
from nepse_selection_agent.github_fetcher import fetch_github_data


def run_agent(data_dir: str = None, top_n: int = 20, compact: bool = False,
              json_output: bool = False, verbose: bool = True,
              use_github: bool = False, export_csv: bool = False):
    
    if verbose:
        print("\n NEPSE AI Stock Selection Agent v1.0")
        print("=" * 50)

    # Step 1: Load Data
    if use_github:
        daily_data = fetch_github_data(verbose=verbose)
    else:
        if verbose:
            print(f"\n Loading data from: {data_dir if data_dir else 'sample data (no directory provided)'}")
        daily_data = load_all_data(data_dir)
        if verbose:
            print(f"   Loaded {len(daily_data)} trading days")

    if not daily_data:
        print("[ERROR] No data loaded. Please provide a valid data directory or use --github.")
        return []

    # Step 2: Score Stocks
    if verbose:
        print("\n Running AI scoring across 10 strategy engines...")
        print("   - Momentum Persistence")
        print("   - Relative Strength vs Market")
        print("   - Smart Money Accumulation (Turnover)")
        print("   - Multi-List Confluence (Gainers+RS+Turnover)")
        print("   - Full Confluence (All 5 Lists)")
        print("   - Volume Leaders")
        print("   - Transaction Activity")
        print("   - Breakout Confirmation")
        print("   - Volume Surge Detection")
        print("   - Risk-Reward Quality Filter")

    scorer = AIScorer()
    scores = scorer.score_all(daily_data)

    if verbose:
        print(f"\n Evaluated {len(scores)} stocks meeting threshold")

    # Step 3: Output
    if export_csv:
        export_possible_stocks_csv(scores, filepath="possibleStocks.csv", top_n=top_n)

    if json_output:
        output = json.dumps(
            [s.to_dict() for s in scores[:top_n]],
            indent=2
        )
        print(output)
    elif compact:
        print(format_compact_report(scores, top_n))
    else:
        print(format_report(scores, top_n))

    return scores


def main():
    parser = argparse.ArgumentParser(
        description="NEPSE AI Stock Selection Agent"
    )
    parser.add_argument(
        "data_dir", nargs="?", default=None,
        help="Path to nepse_data directory (leave empty for sample data)"
    )
    parser.add_argument(
        "--top", type=int, default=20,
        help="Number of top stocks to display (default: 20)"
    )
    parser.add_argument(
        "--compact", action="store_true",
        help="Show compact table format"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON"
    )
    parser.add_argument(
        "--github", action="store_true",
        help="Fetch data from GitHub (h0miez4evr/Nepse_automation)"
    )
    parser.add_argument(
        "--csv", action="store_true",
        help="Export results to possibleStocks.csv"
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress verbose output"
    )

    args = parser.parse_args()
    run_agent(
        data_dir=args.data_dir,
        top_n=args.top,
        compact=args.compact,
        json_output=args.json,
        verbose=not args.quiet,
        use_github=args.github,
        export_csv=args.csv,
    )


if __name__ == "__main__":
    main()
