"""
Relative Strength Calculator Module
Calculates various RS metrics following O'Neil and Weinstein methodologies
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional

class RSCalculator:
    """Calculates Relative Strength metrics"""
    
    def __init__(self, universe_df: pd.DataFrame, lookback_period: int = 252):
        """
        Initialize RS Calculator
        
        Args:
            universe_df: DataFrame with stock universe
            lookback_period: Days to look back for RS calculation (default 252 = 1 year)
        """
        self.universe_df = universe_df
        self.lookback_period = lookback_period
        self.price_data = {}
        self.returns = {}
    
    def calculate_all_rs_metrics(self, 
                                  compare_nifty50: bool = True,
                                  compare_nse500: bool = True,
                                  compare_sector: bool = True) -> pd.DataFrame:
        """
        Calculate comprehensive RS metrics for all stocks
        
        Args:
            compare_nifty50: Calculate RS vs Nifty 50
            compare_nse500: Calculate RS vs NSE 500
            compare_sector: Calculate RS vs sector index
        
        Returns:
            DataFrame with all RS metrics
        """
        from data_fetcher import DataFetcher
        
        # Initialize data fetcher
        data_fetcher = DataFetcher(source="yfinance")
        
        # Fetch historical prices
        symbols = self.universe_df['symbol'].tolist()
        self.price_data = data_fetcher.fetch_historical_prices(symbols, self.lookback_period + 30)
        
        # Calculate returns
        self._calculate_returns()
        
        results = []
        
        # Get benchmark data
        nifty50_data = None
        nse500_data = None
        
        if compare_nifty50:
            nifty50_data = data_fetcher.get_benchmark_data("NIFTY50", self.lookback_period + 30)
        if compare_nse500:
            nse500_data = data_fetcher.get_benchmark_data("NSE500", self.lookback_period + 30)
        
        for idx, row in self.universe_df.iterrows():
            symbol = row['symbol']
            
            if symbol not in self.returns or self.returns[symbol] is None:
                continue
            
            stock_metrics = {
                'symbol': symbol,
                'company_name': row['company_name'],
                'sector': row['sector'],
                'market_cap': row['market_cap'],
                'current_price': row['current_price'],
                'pe_ratio': row.get('pe_ratio', np.nan)
            }
            
            # Calculate O'Neil style RS percentile
            stock_metrics['rs_percentile'] = self._calculate_rs_percentile(symbol)
            stock_metrics['rs_rank'] = self._calculate_rs_rank(symbol)
            
            # Calculate Mansfield RS vs benchmarks
            if compare_nifty50 and nifty50_data is not None:
                stock_metrics['rs_vs_nifty50'] = self._calculate_mansfield_rs(symbol, nifty50_data)
                stock_metrics['mansfield_nifty50'] = self._calculate_mansfield_oscillator(symbol, nifty50_data)
            
            if compare_nse500 and nse500_data is not None:
                stock_metrics['rs_vs_nse500'] = self._calculate_mansfield_rs(symbol, nse500_data)
            
            # Calculate RS vs sector
            if compare_sector:
                sector_data = data_fetcher.get_sector_index_data(row['sector'], self.lookback_period + 30)
                if sector_data is not None:
                    stock_metrics['rs_vs_sector'] = self._calculate_mansfield_rs(symbol, sector_data)
                    stock_metrics['mansfield_sector'] = self._calculate_mansfield_oscillator(symbol, sector_data)
                else:
                    stock_metrics['rs_vs_sector'] = np.nan
                    stock_metrics['mansfield_sector'] = np.nan
            
            # Calculate momentum metrics
            stock_metrics['return_1m'] = self._calculate_period_return(symbol, 21)
            stock_metrics['return_3m'] = self._calculate_period_return(symbol, 63)
            stock_metrics['return_6m'] = self._calculate_period_return(symbol, 126)
            stock_metrics['return_12m'] = self._calculate_period_return(symbol, 252)
            
            # Volatility
            stock_metrics['volatility'] = self._calculate_volatility(symbol)
            
            # Trend strength
            stock_metrics['trend_strength'] = self._calculate_trend_strength(symbol)
            
            results.append(stock_metrics)
        
        return pd.DataFrame(results)
    
    def _calculate_returns(self):
        """Calculate returns for all stocks"""
        for symbol, price_df in self.price_data.items():
            if price_df is not None and not price_df.empty:
                # Calculate daily returns
                returns = price_df['Close'].pct_change()
                self.returns[symbol] = returns
            else:
                self.returns[symbol] = None
    
    def _calculate_rs_percentile(self, symbol: str) -> float:
        """
        Calculate O'Neil style RS percentile ranking (0-100)
        Higher is better - 99 means outperformed 99% of stocks
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Percentile rank (0-100)
        """
        # Get stock's return over lookback period (excluding last month)
        stock_return = self._calculate_period_return(symbol, self.lookback_period, skip_recent=21)
        
        if stock_return is None or np.isnan(stock_return):
            return 0
        
        # Calculate all stocks' returns
        all_returns = []
        for sym in self.returns.keys():
            ret = self._calculate_period_return(sym, self.lookback_period, skip_recent=21)
            if ret is not None and not np.isnan(ret):
                all_returns.append(ret)
        
        if len(all_returns) == 0:
            return 50  # Default to middle if no data
        
        # Calculate percentile using numpy
        percentile = (np.sum(np.array(all_returns) < stock_return) / len(all_returns)) * 100
        return percentile
    
    def _calculate_rs_rank(self, symbol: str) -> int:
        """
        Calculate RS rank (1 = best, higher is worse)
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Rank number
        """
        stock_return = self._calculate_period_return(symbol, self.lookback_period, skip_recent=21)
        
        if stock_return is None or np.isnan(stock_return):
            return 999
        
        # Get all returns and rank
        returns_list = []
        for sym in self.returns.keys():
            ret = self._calculate_period_return(sym, self.lookback_period, skip_recent=21)
            if ret is not None and not np.isnan(ret):
                returns_list.append((sym, ret))
        
        # Sort by return descending
        returns_list.sort(key=lambda x: x[1], reverse=True)
        
        # Find rank
        for i, (sym, _) in enumerate(returns_list):
            if sym == symbol:
                return i + 1
        
        return 999
    
    def _calculate_mansfield_rs(self, symbol: str, benchmark_data: pd.DataFrame) -> float:
        """
        Calculate Mansfield Relative Strength
        RS = [(Stock Price / Benchmark Price) / 52-week MA of ratio - 1] × 100
        
        Args:
            symbol: Stock symbol
            benchmark_data: Benchmark index price data
        
        Returns:
            Mansfield RS value (positive = outperformance)
        """
        if symbol not in self.price_data or self.price_data[symbol] is None:
            return np.nan
        
        stock_data = self.price_data[symbol]
        
        # Align dates
        common_dates = stock_data.index.intersection(benchmark_data.index)
        if len(common_dates) < 252:
            return np.nan
        
        stock_prices = stock_data.loc[common_dates, 'Close']
        bench_prices = benchmark_data.loc[common_dates, 'Close']
        
        # Calculate ratio
        ratio = stock_prices / bench_prices
        
        # Calculate 52-week (252-day) MA of ratio
        ratio_ma = ratio.rolling(window=252).mean()
        
        # Mansfield RS
        current_ratio = ratio.iloc[-1]
        current_ma = ratio_ma.iloc[-1]
        
        if np.isnan(current_ma) or current_ma == 0:
            return np.nan
        
        mansfield_rs = ((current_ratio / current_ma) - 1) * 100
        
        return mansfield_rs
    
    def _calculate_mansfield_oscillator(self, symbol: str, benchmark_data: pd.DataFrame) -> float:
        """
        Calculate Mansfield RS oscillator value (crosses above/below zero)
        
        Args:
            symbol: Stock symbol
            benchmark_data: Benchmark price data
        
        Returns:
            Oscillator value
        """
        return self._calculate_mansfield_rs(symbol, benchmark_data)
    
    def _calculate_period_return(self, symbol: str, period: int, skip_recent: int = 0) -> Optional[float]:
        """
        Calculate return over specific period
        
        Args:
            symbol: Stock symbol
            period: Number of days
            skip_recent: Skip most recent N days (to avoid short-term reversals)
        
        Returns:
            Return as percentage
        """
        if symbol not in self.price_data or self.price_data[symbol] is None:
            return None
        
        price_df = self.price_data[symbol]
        
        if len(price_df) < period + skip_recent:
            return None
        
        try:
            end_idx = -1 - skip_recent if skip_recent > 0 else -1
            start_idx = end_idx - period
            
            end_price = price_df['Close'].iloc[end_idx]
            start_price = price_df['Close'].iloc[start_idx]
            
            if start_price == 0 or np.isnan(start_price) or np.isnan(end_price):
                return None
            
            return ((end_price / start_price) - 1) * 100
        except:
            return None
    
    def _calculate_volatility(self, symbol: str, period: int = 60) -> float:
        """
        Calculate realized volatility (annualized)
        
        Args:
            symbol: Stock symbol
            period: Lookback period for volatility calculation
        
        Returns:
            Annualized volatility percentage
        """
        if symbol not in self.returns or self.returns[symbol] is None:
            return np.nan
        
        returns = self.returns[symbol].dropna()
        
        if len(returns) < period:
            return np.nan
        
        # Calculate rolling volatility
        vol = returns.tail(period).std() * np.sqrt(252) * 100
        
        return vol
    
    def _calculate_trend_strength(self, symbol: str) -> float:
        """
        Calculate trend strength using ADX-like concept
        Returns 0-100, higher = stronger trend
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Trend strength score
        """
        if symbol not in self.price_data or self.price_data[symbol] is None:
            return 0
        
        price_df = self.price_data[symbol]
        
        if len(price_df) < 50:
            return 0
        
        # Simple trend strength: R-squared of price vs time
        prices = price_df['Close'].tail(126).values  # 6 months
        time_idx = np.arange(len(prices))
        
        try:
            # Linear regression using numpy polyfit
            coeffs = np.polyfit(time_idx, prices, 1)
            slope = coeffs[0]
            
            # Calculate R-squared
            y_pred = np.polyval(coeffs, time_idx)
            ss_res = np.sum((prices - y_pred) ** 2)
            ss_tot = np.sum((prices - np.mean(prices)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            # Convert to 0-100 scale
            trend_strength = r_squared * 100
            
            return trend_strength
        except:
            return 0
