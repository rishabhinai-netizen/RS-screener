"""Screener Engine - Optimized Filtering & Scoring"""
import pandas as pd
import numpy as np
from typing import Dict
from config import STRATEGIES, SIGNAL_THRESHOLDS

class ScreenerEngine:
    def __init__(self, params: Dict):
        self.params = params
    
    def apply_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        initial = len(df)
        df = df[df['rs_percentile'] >= self.params['rs_threshold']]
        if self.params.get('min_roe'):
            df = df[(df['roe'] >= self.params['min_roe']) | df['roe'].isna()]
        if self.params.get('max_de'):
            df = df[(df['debt_equity'] <= self.params['max_de']) | df['debt_equity'].isna()]
        if self.params.get('min_margin'):
            df = df[(df['operating_margin'] >= self.params['min_margin']) | df['operating_margin'].isna()]
        if self.params.get('min_mcap', 5000):
            df = df[df['market_cap'] >= self.params['min_mcap']]
        df = df[df['current_price'].notna() & df['rs_percentile'].notna()]
        print(f"🔍 Filtered: {len(df)}/{initial} stocks passed")
        return df
    
    def calculate_composite_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        strategy = self.params.get('strategy', 'RS + Quality')
        if strategy == "RS + Quality":
            df['composite_score'] = (0.60 * df['rs_percentile'] + 0.40 * df['quality_score'].fillna(0))
        elif strategy == "RS + Value":
            pe_norm = 100 - ((df['pe_ratio'] - df['pe_ratio'].min()) / (df['pe_ratio'].max() - df['pe_ratio'].min()) * 100)
            df['composite_score'] = (0.50 * df['rs_percentile'] + 0.30 * pe_norm.fillna(50) + 0.20 * df['quality_score'].fillna(0))
        elif strategy == "RS + Low Volatility":
            vol_norm = 100 - ((df['volatility'] - df['volatility'].min()) / (df['volatility'].max() - df['volatility'].min()) * 100)
            df['composite_score'] = (0.50 * df['rs_percentile'] + 0.50 * vol_norm.fillna(50))
        else:
            df['composite_score'] = df['rs_percentile']
        df['signal'] = df.apply(self._generate_signal, axis=1)
        df = df.sort_values('composite_score', ascending=False)
        return df
    
    def _generate_signal(self, row: pd.Series) -> str:
        if row['composite_score'] >= SIGNAL_THRESHOLDS['BUY']['composite_min'] and row['rs_percentile'] >= SIGNAL_THRESHOLDS['BUY']['rs_min']:
            return "BUY"
        elif row['composite_score'] >= SIGNAL_THRESHOLDS['STRONG_WATCH']['composite_min']:
            return "STRONG_WATCH"
        elif row['composite_score'] >= SIGNAL_THRESHOLDS['WATCH']['composite_min']:
            return "WATCH"
        else:
            return "AVOID"
