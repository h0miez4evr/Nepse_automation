from typing import Dict, List, Tuple
from .data_loader import DailyData, StockRecord
import statistics


class StrategyEngine:
    """Base class for all trading strategies."""

    def __init__(self, name: str, weight: float = 1.0):
        self.name = name
        self.weight = weight

    def score(self, symbol: str, daily_data: List[DailyData]) -> float:
        """Return a score from 0-100 for the given symbol."""
        raise NotImplementedError


class MomentumPersistence(StrategyEngine):

    def __init__(self, lookback: int = 10):
        super().__init__("Momentum Persistence", weight=1.5)
        self.lookback = lookback

    def score(self, symbol: str, daily_data: List[DailyData]) -> float:
        recent = daily_data[-self.lookback:] if len(daily_data) > self.lookback else daily_data
        if not recent:
            return 0

        gainer_days = 0
        all_pct_changes = []
        consecutive_up = 0
        max_consecutive = 0

        for day in recent:
            stocks = day.all_stocks()
            if symbol in stocks:
                rec = stocks[symbol]
                all_pct_changes.append(rec.percent_change)
                if rec.percent_change > 0:
                    gainer_days += 1
                    consecutive_up += 1
                    max_consecutive = max(max_consecutive, consecutive_up)
                else:
                    consecutive_up = 0

        if not all_pct_changes:
            return 0

        # Score components
        frequency = (gainer_days / len(recent)) * 30  # 0-30
        avg_change = statistics.mean(all_pct_changes)
        consistency_bonus = min(avg_change * 3, 30)  # 0-30
        streak_bonus = min(max_consecutive * 8, 25)  # 0-25
        recency_bonus = 15 if all_pct_changes[-1] > 0 else 0  # 0-15

        return min(frequency + consistency_bonus + streak_bonus + recency_bonus, 100)


class RelativeStrengthStrategy(StrategyEngine):
    def __init__(self, lookback: int = 10):
        super().__init__("Relative Strength", weight=1.4)
        self.lookback = lookback

    def score(self, symbol: str, daily_data: List[DailyData]) -> float:
        recent = daily_data[-self.lookback:] if len(daily_data) > self.lookback else daily_data
        if not recent:
            return 0

        rs_days = 0
        rs_scores = []

        for day in recent:
            for rec in day.relative_strength:
                if rec.symbol == symbol:
                    rs_days += 1
                    rs_scores.append(rec.rs_score)

        if not rs_scores:
            return 0

        frequency = (rs_days / len(recent)) * 30  # 0-30
        avg_rs = statistics.mean(rs_scores)
        rs_magnitude = min((avg_rs / 100) * 35, 35)  # 0-35

        # Improving RS
        if len(rs_scores) >= 3:
            recent_avg = statistics.mean(rs_scores[-3:])
            older_avg = statistics.mean(rs_scores[:3]) if len(rs_scores) > 3 else rs_scores[0]
            improvement = max(0, (recent_avg - older_avg) / max(older_avg, 1)) * 20
            improvement = min(improvement, 20)
        else:
            improvement = 10

        streak_bonus = 15 if rs_days >= 3 else (10 if rs_days >= 2 else 0)

        return min(frequency + rs_magnitude + improvement + streak_bonus, 100)


class SmartMoneyAccumulation(StrategyEngine):
    def __init__(self, lookback: int = 10):
        super().__init__("Smart Money Accumulation", weight=1.3)
        self.lookback = lookback

    def score(self, symbol: str, daily_data: List[DailyData]) -> float:
        recent = daily_data[-self.lookback:] if len(daily_data) > self.lookback else daily_data
        if not recent:
            return 0

        turnover_days = 0
        turnover_values = []
        price_changes = []

        for day in recent:
            for rec in day.turnovers:
                if rec.symbol == symbol:
                    turnover_days += 1
                    turnover_values.append(rec.turnover)
                    price_changes.append(abs(rec.percent_change))

        if not turnover_values:
            return 0

        frequency = (turnover_days / len(recent)) * 25  
        avg_turnover = statistics.mean(turnover_values)
        turnover_score = min((avg_turnover / 10_000_000) * 15, 25)  # 0-25

        
        avg_abs_change = statistics.mean(price_changes) if price_changes else 5
        if avg_abs_change < 2:
            accumulation_score = 25  # Strong accumulation signal
        elif avg_abs_change < 4:
            accumulation_score = 15
        else:
            accumulation_score = 5

        # Volume consistency
        consistency = 15 if turnover_days >= 4 else (10 if turnover_days >= 2 else 0)

        return min(frequency + turnover_score + accumulation_score + consistency, 100)


class ConfluenceScoring(StrategyEngine):

    def __init__(self, lookback: int = 10):
        super().__init__("Confluence Scoring", weight=1.6)
        self.lookback = lookback

    def score(self, symbol: str, daily_data: List[DailyData]) -> float:
        recent = daily_data[-self.lookback:] if len(daily_data) > self.lookback else daily_data
        if not recent:
            return 0

        multi_list_days = 0
        total_confluence = 0

        for day in recent:
            overlap = day.symbols_in_multiple_lists()
            if symbol in overlap:
                count = overlap[symbol]
                multi_list_days += 1
                if count == 3:
                    total_confluence += 30  # All three lists
                elif count == 2:
                    total_confluence += 15  # Two lists

        frequency = min(multi_list_days * 12, 30)  # 0-30
        intensity = min(total_confluence, 40)  # 0-40
        consistency = 30 if multi_list_days >= 3 else (20 if multi_list_days >= 2 else (10 if multi_list_days >= 1 else 0))

        return min(frequency + intensity + consistency, 100)


class BreakoutConfirmation(StrategyEngine):

    def __init__(self, lookback: int = 10):
        super().__init__("Breakout Confirmation", weight=1.2)
        self.lookback = lookback

    def score(self, symbol: str, daily_data: List[DailyData]) -> float:
        recent = daily_data[-self.lookback:] if len(daily_data) > self.lookback else daily_data
        if not recent:
            return 0

        records = []
        volumes = []

        for day in recent:
            stocks = day.all_stocks()
            if symbol in stocks:
                rec = stocks[symbol]
                records.append(rec)
                volumes.append(rec.volume)

        if not records:
            return 0

        # Near highs
        latest = records[-1]
        all_highs = [r.high for r in records if r.high > 0]
        if all_highs:
            recent_high = max(all_highs[-3:]) if len(all_highs) >= 3 else max(all_highs)
            near_high = (latest.ltp / recent_high) * 100 if recent_high > 0 else 50
        else:
            near_high = 50

        high_score = min(((near_high - 80) / 20) * 30, 30) if near_high > 80 else 0

        # Volume surge
        if len(volumes) >= 2:
            avg_vol = statistics.mean(volumes[:-1])
            latest_vol = volumes[-1]
            vol_ratio = latest_vol / max(avg_vol, 1)
            vol_score = min((vol_ratio - 1) * 15, 30) if vol_ratio > 1 else 0
        else:
            vol_score = 10

        # Positive momentum
        pct = latest.percent_change
        momentum_score = min(max(pct, 0) * 3, 25)

        # Price above open (bullish)
        bullish_candle = 15 if latest.ltp > latest.open else 0

        return min(max(high_score, 0) + vol_score + momentum_score + bullish_candle, 100)


class VolumeFromList(StrategyEngine):

    def __init__(self, lookback: int = 10):
        super().__init__("Volume Leaders", weight=1.2)
        self.lookback = lookback

    def score(self, symbol: str, daily_data: List[DailyData]) -> float:
        recent = daily_data[-self.lookback:] if len(daily_data) > self.lookback else daily_data
        if not recent:
            return 0

        vol_days = 0
        vol_values = []

        for day in recent:
            vol_list = getattr(day, 'volume_leaders', [])
            for rec in vol_list:
                if rec.symbol == symbol:
                    vol_days += 1
                    vol_values.append(rec.volume)

        if not vol_values:
            return 0

        # Frequency in volume list
        frequency = (vol_days / len(recent)) * 30  # 0-30

        # Volume magnitude
        avg_vol = statistics.mean(vol_values)
        vol_magnitude = min((avg_vol / 200000) * 25, 30)  # 0-30

        # Consistency
        consistency = min(vol_days * 8, 25)  # 0-25

        # Recent appearance bonus
        last_day_vol = getattr(recent[-1], 'volume_leaders', [])
        recent_bonus = 15 if any(r.symbol == symbol for r in last_day_vol) else 0

        return min(frequency + vol_magnitude + consistency + recent_bonus, 100)


class TransactionMomentum(StrategyEngine):
    def __init__(self, lookback: int = 10):
        super().__init__("Transaction Activity", weight=1.0)
        self.lookback = lookback

    def score(self, symbol: str, daily_data: List[DailyData]) -> float:
        recent = daily_data[-self.lookback:] if len(daily_data) > self.lookback else daily_data
        if not recent:
            return 0

        txn_days = 0
        txn_values = []

        for day in recent:
            txn_list = getattr(day, 'transaction_leaders', [])
            for rec in txn_list:
                if rec.symbol == symbol:
                    txn_days += 1
                    txn_values.append(rec.volume)  # volume field stores total_trades

        if not txn_values:
            return 0

        # Frequency in transactions list
        frequency = (txn_days / len(recent)) * 30  # 0-30

        # Transaction count magnitude
        avg_txn = statistics.mean(txn_values)
        txn_magnitude = min((avg_txn / 1000) * 25, 30)  # 0-30

        # Consistency
        consistency = min(txn_days * 8, 25)  # 0-25

        # Recent appearance bonus
        last_day_txn = getattr(recent[-1], 'transaction_leaders', [])
        recent_bonus = 15 if any(r.symbol == symbol for r in last_day_txn) else 0

        return min(frequency + txn_magnitude + consistency + recent_bonus, 100)


class VolumeSurge(StrategyEngine):

    def __init__(self, lookback: int = 10):
        super().__init__("Volume Surge", weight=1.1)
        self.lookback = lookback

    def score(self, symbol: str, daily_data: List[DailyData]) -> float:
        recent = daily_data[-self.lookback:] if len(daily_data) > self.lookback else daily_data
        if not recent:
            return 0

        all_volumes = []
        latest_vol = 0
        latest_pct = 0

        for day in recent:
            stocks = day.all_stocks()
            if symbol in stocks:
                rec = stocks[symbol]
                all_volumes.append(rec.volume)
                latest_vol = rec.volume
                latest_pct = rec.percent_change

        if len(all_volumes) < 2:
            return 0

        avg_vol = statistics.mean(all_volumes[:-1])
        if avg_vol <= 0:
            return 0

        vol_ratio = latest_vol / avg_vol

        # Volume surge score
        if vol_ratio >= 3:
            surge_score = 40
        elif vol_ratio >= 2:
            surge_score = 30
        elif vol_ratio >= 1.5:
            surge_score = 20
        else:
            surge_score = max(vol_ratio * 10, 0)

        # Price action with volume
        price_action = min(max(latest_pct, 0) * 4, 30)

        # Frequency of high volume days
        high_vol_days = sum(1 for v in all_volumes if v > avg_vol * 1.3)
        consistency = min(high_vol_days * 5, 30)

        return min(surge_score + price_action + consistency, 100)


class ConfluenceAllLists(StrategyEngine):

    def __init__(self, lookback: int = 10):
        super().__init__("Full Confluence", weight=1.8)
        self.lookback = lookback

    def score(self, symbol: str, daily_data: List[DailyData]) -> float:
        recent = daily_data[-self.lookback:] if len(daily_data) > self.lookback else daily_data
        if not recent:
            return 0

        multi_list_days = 0
        max_confluence_per_day = 0

        for day in recent:
            overlap = day.symbols_in_multiple_lists()
            if symbol in overlap:
                count = overlap[symbol]
                multi_list_days += 1
                max_confluence_per_day = max(max_confluence_per_day, count)

        if multi_list_days == 0:
            return 0

        # Frequency across days
        frequency = min(multi_list_days * 12, 35)  # 0-35

        # Max confluence intensity
        if max_confluence_per_day >= 5:
            intensity = 35
        elif max_confluence_per_day >= 4:
            intensity = 30
        elif max_confluence_per_day >= 3:
            intensity = 20
        elif max_confluence_per_day >= 2:
            intensity = 10
        else:
            intensity = 0

        # Consistency
        consistency = min(multi_list_days * 8, 30)  # 0-30

        return min(frequency + intensity + consistency, 100)


class RiskRewardQuality(StrategyEngine):

    def __init__(self, lookback: int = 10):
        super().__init__("Risk-Reward Quality", weight=0.8)
        self.lookback = lookback

    def score(self, symbol: str, daily_data: List[DailyData]) -> float:
        recent = daily_data[-self.lookback:] if len(daily_data) > self.lookback else daily_data
        if not recent:
            return 0

        records = []
        for day in recent:
            stocks = day.all_stocks()
            if symbol in stocks:
                records.append(stocks[symbol])

        if not records:
            return 0

        latest = records[-1]

        # Close near high (bullish candle)
        if latest.high > 0:
            close_to_high = ((latest.ltp - latest.low) / (latest.high - latest.low)) * 100 if latest.high != latest.low else 50
        else:
            close_to_high = 50
        candle_score = min(close_to_high / 4, 25)

        # Not overextended (2-6% daily move is ideal)
        pct = abs(latest.percent_change)
        if 2 <= pct <= 6:
            extension_score = 25
        elif pct < 2:
            extension_score = 10
        else:
            extension_score = max(25 - (pct - 6) * 3, 5)

        # Consistent range (not wild swings)
        if len(records) >= 3:
            ranges = [(r.high - r.low) / max(r.ltp, 1) * 100 for r in records[-3:] if r.ltp > 0]
            avg_range = statistics.mean(ranges) if ranges else 10
            range_score = max(25 - avg_range * 2, 0)
        else:
            range_score = 10

        # Positive trend
        if len(records) >= 2:
            trend = 25 if latest.ltp > records[-2].ltp else 0
        else:
            trend = 10

        return min(candle_score + extension_score + range_score + trend, 100)


# All available strategies
ALL_STRATEGIES = [
    MomentumPersistence(lookback=10),
    RelativeStrengthStrategy(lookback=10),
    SmartMoneyAccumulation(lookback=10),
    ConfluenceScoring(lookback=10),
    ConfluenceAllLists(lookback=10),
    VolumeFromList(lookback=10),
    TransactionMomentum(lookback=10),
    BreakoutConfirmation(lookback=10),
    VolumeSurge(lookback=10),
    RiskRewardQuality(lookback=10),
]
