"""RS Calculator - Optimized Production Version"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from config import RS_CONFIG
from cache_manager import get_cache

class RSCalculator:
    def __init__(self, price_data: Dict[str, pd.DataFrame]):
        self.price_data = price_data
        self.returns = {}
        self._calculate_all_returns()
        self.cache = get_cache()
    
    def _calculate_all_returns(self):
        for symbol, df in self.price_data.items():
            if df is not None and not df.empty:
                self.returns[symbol] = df['Close'].pct_change()
    
    def calculate_rs_metrics(self, benchmark_data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        results = []
        for symbol in self.price_data.keys():
            metrics = {
                'symbol': symbol,
                'rs_percentile': self._calc_rs_percentile(symbol),
                'rs_rank': self._calc_rs_rank(symbol),
                'return_1m': self._calc_period_return(symbol, 21),
                'return_3m': self._calc_period_return(symbol, 63),
                'return_6m': self._calc_period_return(symbol, 126),
                'return_12m': self._calc_period_return(symbol, 252),
                'volatility': self._calc_volatility(symbol),
                'trend_strength': self._calc_trend_strength(symbol)
            }
            if benchmark_data is not None:
                metrics['rs_vs_benchmark'] = self._calc_mansfield_rs(symbol, benchmark_data)
                metrics['mansfield_oscillator'] = self._calc_mansfield_rs(symbol, benchmark_data)
            results.append(metrics)
        return pd.DataFrame(results)
    
    def _calc_rs_percentile(self, symbol: str) -> float:
        stock_return = self._calc_period_return(symbol, RS_CONFIG['lookback_period'], skip_recent=RS_CONFIG['skip_recent_days'])
        if stock_return is None or np.isnan(stock_return):
            return 0
        all_returns = [self._calc_period_return(s, RS_CONFIG['lookback_period'], skip_recent=RS_CONFIG['skip_recent_days']) 
                      for s in self.returns.keys()]
        all_returns = [r for r in all_returns if r is not None and not np.isnan(r)]
        if len(all_returns) == 0:
            return 50
        return (np.sum(np.array(all_returns) < stock_return) / len(all_returns)) * 100
    
    def _calc_rs_rank(self, symbol: str) -> int:
        stock_return = self._calc_period_return(symbol, RS_CONFIG['lookback_period'], skip_recent=RS_CONFIG['skip_recent_days'])
        if stock_return is None:
            return 999
        returns_list = [(s, self._calc_period_return(s, RS_CONFIG['lookback_period'], skip_recent=RS_CONFIG['skip_recent_days'])) 
                       for s in self.returns.keys()]
        returns_list = [(s, r) for s, r in returns_list if r is not None and not np.isnan(r)]
        returns_list.sort(key=lambda x: x[1], reverse=True)
        for i, (s, _) in enumerate(returns_list):
            if s == symbol:
                return i + 1
        return 999
    
    def _calc_period_return(self, symbol: str, period: int, skip_recent: int = 0) -> Optional[float]:
        if symbol not in self.price_data or self.price_data[symbol] is None:
            return None
        df = self.price_data[symbol]
        if len(df) < period + skip_recent:
            return None
        try:
            end_idx = -1 - skip_recent if skip_recent > 0 else -1
            start_idx = end_idx - period
            end_price = df['Close'].iloc[end_idx]
            start_price = df['Close'].iloc[start_idx]
            if start_price == 0 or np.isnan(start_price) or np.isnan(end_price):
                return None
            return ((end_price / start_price) - 1) * 100
        except:
            return None
    
    def _calc_volatility(self, symbol: str) -> float:
        if symbol not in self.returns or self.returns[symbol] is None:
            return np.nan
        returns = self.returns[symbol].dropna()
        if len(returns) < RS_CONFIG['volatility_period']:
            return np.nan
        return returns.tail(RS_CONFIG['volatility_period']).std() * np.sqrt(252) * 100
    
    def _calc_trend_strength(self, symbol: str) -> float:
        if symbol not in self.price_data or self.price_data[symbol] is None:
            return 0
        df = self.price_data[symbol]
        if len(df) < RS_CONFIG['trend_strength_period']:
            return 0
        prices = df['Close'].tail(RS_CONFIG['trend_strength_period']).values
        time_idx = np.arange(len(prices))
        try:
            coeffs = np.polyfit(time_idx, prices, 1)
            y_pred = np.polyval(coeffs, time_idx)
            ss_res = np.sum((prices - y_pred) ** 2)
            ss_tot = np.sum((prices - np.mean(prices)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            return r_squared * 100
        except:
            return 0
    
    def _calc_mansfield_rs(self, symbol: str, benchmark_data: pd.DataFrame) -> float:
        if symbol not in self.price_data or self.price_data[symbol] is None:
            return np.nan
        stock_data = self.price_data[symbol]
        common_dates = stock_data.index.intersection(benchmark_data.index)
        if len(common_dates) < 252:
            return np.nan
        stock_prices = stock_data.loc[common_dates, 'Close']
        bench_prices = benchmark_data.loc[common_dates, 'Close']
        ratio = stock_prices / bench_prices
        ratio_ma = ratio.rolling(window=252).mean()
        current_ratio = ratio.iloc[-1]
        current_ma = ratio_ma.iloc[-1]
        if np.isnan(current_ma) or current_ma == 0:
            return np.nan
        return ((current_ratio / current_ma) - 1) * 100
