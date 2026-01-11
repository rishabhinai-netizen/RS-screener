"""
Screener Engine Module
Applies filters and calculates composite scores
"""

import pandas as pd
import numpy as np
from typing import Dict

class ScreenerEngine:
    """Main screening engine combining RS and Quality"""
    
    def __init__(self, params: Dict):
        """
        Initialize Screener Engine
        
        Args:
            params: Screening parameters from UI
        """
        self.params = params
    
    def apply_filters(self, rs_df: pd.DataFrame, quality_df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply all screening filters
        
        Args:
            rs_df: DataFrame with RS metrics
            quality_df: DataFrame with quality metrics (already merged)
        
        Returns:
            Filtered DataFrame
        """
        df = quality_df.copy()
        
        initial_count = len(df)
        
        # Filter 1: RS Threshold
        df = df[df['rs_percentile'] >= self.params['rs_threshold']]
        print(f"After RS filter: {len(df)} stocks (removed {initial_count - len(df)})")
        
        # Filter 2: Quality Filters
        if self.params['strategy'] in ["RS + Quality (Recommended)", "Pure RS (Advanced)"]:
            # Apply quality filters
            df = df[
                (df['roe'] >= self.params['min_roe']) |
                (df['roe'].isna())  # Don't exclude if data missing
            ]
            
            df = df[
                (df['debt_equity'] <= self.params['max_de']) |
                (df['debt_equity'].isna())
            ]
            
            df = df[
                (df['operating_margin'] >= self.params['min_margin']) |
                (df['operating_margin'].isna())
            ]
        
        # Filter 3: Market Cap
        df = df[df['market_cap'] >= self.params['min_mcap']]
        
        # Filter 4: Exclude sectors
        if self.params['exclude_sectors']:
            df = df[~df['sector'].isin(self.params['exclude_sectors'])]
        
        # Filter 5: Remove stocks with missing critical data
        df = df[df['current_price'].notna()]
        df = df[df['rs_percentile'].notna()]
        
        print(f"Final count after all filters: {len(df)}")
        
        return df
    
    def calculate_composite_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate composite scores and signals
        
        Args:
            df: Filtered DataFrame
        
        Returns:
            DataFrame with composite scores and signals
        """
        df = df.copy()
        
        # Calculate composite score based on strategy
        if self.params['strategy'] == "RS + Quality (Recommended)":
            # 60% RS, 40% Quality
            df['composite_score'] = (
                0.60 * df['rs_percentile'] +
                0.40 * df['quality_score'].fillna(0)
            )
        
        elif self.params['strategy'] == "RS + Value":
            # 50% RS, 30% Value (inverse P/E), 20% Quality
            # Normalize P/E to 0-100 scale (lower P/E = higher score)
            pe_normalized = 100 - ((df['pe_ratio'] - df['pe_ratio'].min()) / 
                                  (df['pe_ratio'].max() - df['pe_ratio'].min()) * 100)
            pe_normalized = pe_normalized.fillna(50)
            
            df['composite_score'] = (
                0.50 * df['rs_percentile'] +
                0.30 * pe_normalized +
                0.20 * df['quality_score'].fillna(0)
            )
        
        elif self.params['strategy'] == "RS + Low Volatility":
            # 50% RS, 50% Low Volatility (inverse)
            # Normalize volatility (lower = better)
            vol_normalized = 100 - ((df['volatility'] - df['volatility'].min()) /
                                   (df['volatility'].max() - df['volatility'].min()) * 100)
            vol_normalized = vol_normalized.fillna(50)
            
            df['composite_score'] = (
                0.50 * df['rs_percentile'] +
                0.50 * vol_normalized
            )
        
        else:  # Pure RS
            df['composite_score'] = df['rs_percentile']
        
        # Generate signals
        df['signal'] = df.apply(lambda row: self._generate_signal(row), axis=1)
        
        # Sort by composite score
        df = df.sort_values('composite_score', ascending=False)
        
        return df
    
    def _generate_signal(self, row: pd.Series) -> str:
        """
        Generate BUY/WATCH/AVOID signal
        
        Args:
            row: Stock data row
        
        Returns:
            Signal string
        """
        # Strong BUY criteria
        buy_conditions = [
            row['rs_percentile'] >= 85,  # Elite RS
            row['quality_score'] >= 60,  # Good quality
            row['composite_score'] >= 75,  # High composite
        ]
        
        if sum(buy_conditions) >= 2:
            # Additional checks
            if not np.isnan(row.get('rs_vs_nifty50', np.nan)):
                if row['rs_vs_nifty50'] > 0:  # Outperforming benchmark
                    return "BUY"
            else:
                return "BUY"
        
        # WATCH criteria (decent but not strong buy)
        watch_conditions = [
            row['rs_percentile'] >= 70,
            row['quality_score'] >= 40,
            row['composite_score'] >= 60
        ]
        
        if sum(watch_conditions) >= 2:
            return "WATCH"
        
        # Default to AVOID
        return "AVOID"
    
    def calculate_risk_score(self, row: pd.Series) -> float:
        """
        Calculate risk score (0-100, higher = more risk)
        
        Args:
            row: Stock data row
        
        Returns:
            Risk score
        """
        risk_score = 0
        
        # Volatility risk (0-40 points)
        vol = row.get('volatility', 0)
        if vol > 40:
            risk_score += 40
        elif vol > 30:
            risk_score += 30
        elif vol > 20:
            risk_score += 20
        elif vol > 15:
            risk_score += 10
        
        # Debt risk (0-30 points)
        de = row.get('debt_equity', 0)
        if de > 2.0:
            risk_score += 30
        elif de > 1.5:
            risk_score += 20
        elif de > 1.0:
            risk_score += 10
        
        # Valuation risk (0-30 points)
        pe = row.get('pe_ratio', 20)
        if pe > 50:
            risk_score += 30
        elif pe > 35:
            risk_score += 20
        elif pe > 25:
            risk_score += 10
        
        return min(risk_score, 100)
