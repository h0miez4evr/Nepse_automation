

import csv
import os
from typing import Dict, List, Tuple
from .data_loader import DailyData
from .strategies import ALL_STRATEGIES


class StockScore:

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.strategy_scores: Dict[str, float] = {}
        self.composite_score: float = 0.0
        self.conviction: str = "LOW"
        self.tags: List[str] = []

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "composite_score": round(self.composite_score, 1),
            "conviction": self.conviction,
            "tags": self.tags,
            "strategy_scores": {k: round(v, 1) for k, v in self.strategy_scores.items()},
        }


class AIScorer:
    
    def __init__(self, strategies=None, min_days: int = 3):
        self.strategies = strategies or ALL_STRATEGIES
        self.min_days = min_days  # Minimum days of data required

    def _get_all_symbols(self, daily_data: List[DailyData]) -> set:
        
        symbols = set()
        for day in daily_data:
            for rec in day.all_stocks().values():
                symbols.add(rec.symbol)
        return symbols

    def _calculate_composite(self, stock_score: StockScore) -> float:
        total_weight = sum(s.weight for s in self.strategies)
        if total_weight == 0:
            return 0

        weighted_sum = 0
        for strategy in self.strategies:
            score = stock_score.strategy_scores.get(strategy.name, 0)
            weighted_sum += score * strategy.weight

        return weighted_sum / total_weight

    def _assign_conviction(self, score: StockScore) -> str:
        cs = score.composite_score
        num_strong = sum(1 for v in score.strategy_scores.values() if v >= 50)

        if cs >= 70 and num_strong >= 4:
            score.tags.append("HIGH CONVICTION")
            return "HIGH"
        elif cs >= 55 and num_strong >= 3:
            score.tags.append("STRONG")
            return "STRONG"
        elif cs >= 40 and num_strong >= 2:
            score.tags.append("MODERATE")
            return "MODERATE"
        elif cs >= 25:
            score.tags.append("WATCH")
            return "WATCH"
        else:
            return "LOW"

    def _add_tags(self, score: StockScore):
        ss = score.strategy_scores

        if ss.get("Momentum Persistence", 0) >= 60:
            score.tags.append("MOMENTUM LEADER")
        if ss.get("Relative Strength", 0) >= 60:
            score.tags.append("RS CHAMPION")
        if ss.get("Smart Money Accumulation", 0) >= 60:
            score.tags.append("INSTITUTIONAL BUYING")
        if ss.get("Confluence Scoring", 0) >= 60:
            score.tags.append("CONFLUENT")
        if ss.get("Full Confluence", 0) >= 60:
            score.tags.append("ULTRA CONFLUENT")
        if ss.get("Volume Leaders", 0) >= 60:
            score.tags.append("VOLUME LEADER")
        if ss.get("Transaction Activity", 0) >= 60:
            score.tags.append("HIGH ACTIVITY")
        if ss.get("Breakout Confirmation", 0) >= 60:
            score.tags.append("BREAKOUT")
        if ss.get("Volume Surge", 0) >= 60:
            score.tags.append(" VOLUME SURGE")
        if ss.get("Risk-Reward Quality", 0) >= 60:
            score.tags.append("GOOD R:R")
        score.tags = list(dict.fromkeys(score.tags))

    def score_all(self, daily_data: List[DailyData]) -> List[StockScore]:
        
        if len(daily_data) < self.min_days:
            print(f"[INFO] Only {len(daily_data)} days of data available. "
                  f"Recommended minimum: {self.min_days} days for reliable signals.")

        symbols = self._get_all_symbols(daily_data)
        all_scores = []

        for symbol in symbols:
            ss = StockScore(symbol)
            for strategy in self.strategies:
                raw_score = strategy.score(symbol, daily_data)
                ss.strategy_scores[strategy.name] = raw_score
            ss.composite_score = self._calculate_composite(ss)
            if ss.composite_score < 15:
                continue
            ss.conviction = self._assign_conviction(ss)
            self._add_tags(ss)
            all_scores.append(ss)
        all_scores.sort(key=lambda x: x.composite_score, reverse=True)
        return all_scores


def format_report(scores: List[StockScore], top_n: int = 20) -> str:
    lines = []
    lines.append("=" * 70)
    lines.append("  NEPSE AI STOCK SELECTION AGENT - PICKS REPORT")
    lines.append("=" * 70)
    lines.append("")

    # Summary stats
    high = sum(1 for s in scores if s.conviction == "HIGH")
    strong = sum(1 for s in scores if s.conviction == "STRONG")
    moderate = sum(1 for s in scores if s.conviction == "MODERATE")
    watch = sum(1 for s in scores if s.conviction == "WATCH")
    lines.append(f"  Stocks Analyzed: {len(scores)}")
    lines.append(f"  High Conviction: {high}  | Strong: {strong}  |  "
                 f"Moderate: {moderate}  |   Watch: {watch}")
    lines.append("")
    lines.append("-" * 70)

    # Top picks
    top = scores[:top_n]
    lines.append(f"   TOP {len(top)} STOCK PICKS (by composite score)")
    lines.append("-" * 70)

    for i, s in enumerate(top, 1):
        lines.append(f"\n  #{i:2d}  {s.symbol:<10s}  Score: {s.composite_score:5.1f}/100  "
                     f"[{s.conviction}]")
        if s.tags:
            lines.append(f"       {' '.join(s.tags)}")
        lines.append(f"       Strategies: ", )
        for name, val in s.strategy_scores.items():
            bar = "█" * int(val / 5) + "░" * (20 - int(val / 5))
            lines.append(f"         {name:<30s} {bar} {val:5.1f}")

    lines.append("")
    lines.append("=" * 70)
    lines.append("   DISCLAIMER: This is an AI-powered analysis tool.")
    lines.append("  Always do your own research (DYOR) before investing.")
    lines.append("  Past performance does not guarantee future results.")
    lines.append("=" * 70)

    return "\n".join(lines)


def format_compact_report(scores: List[StockScore], top_n: int = 15) -> str:
    lines = []
    lines.append(f"\n{'Rank':<5} {'Symbol':<10} {'Score':>7} {'Conviction':<12} {'Tags'}")
    lines.append("-" * 65)
    for i, s in enumerate(scores[:top_n], 1):
        tags = " ".join(s.tags[:2]) if s.tags else ""
        lines.append(f"{i:<5} {s.symbol:<10} {s.composite_score:>6.1f}  {s.conviction:<12} {tags}")
    lines.append("")
    return "\n".join(lines)


def export_possible_stocks_csv(scores: List[StockScore], filepath: str = "possibleStocks.csv",
                               top_n: int = 50) -> str:
    
    top_scores = scores[:top_n]
    strategy_names = []
    if top_scores:
        strategy_names = list(top_scores[0].strategy_scores.keys())

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        header = ["rank", "symbol", "composite_score", "conviction", "tags"]
        header.extend([f"strategy_{name.lower().replace(' ', '_')}" for name in strategy_names])
        writer.writerow(header)

        # Data rows
        for i, s in enumerate(top_scores, 1):
            row = [
                i,
                s.symbol,
                round(s.composite_score, 1),
                s.conviction,
                " | ".join(s.tags) if s.tags else "",
            ]
            for name in strategy_names:
                row.append(round(s.strategy_scores.get(name, 0), 1))
            writer.writerow(row)

    abs_path = os.path.abspath(filepath)
    print(f"\n Exported {len(top_scores)} stocks to: {abs_path}")
    return abs_path
