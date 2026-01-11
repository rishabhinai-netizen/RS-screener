"""
Quality Analyzer Module
Analyzes quality metrics: ROE, Debt/Equity, Margins, Cash Flow
"""

import pandas as pd
import numpy as np
from typing import Dict, List

class QualityAnalyzer:
    """Analyzes stock quality metrics"""
    
    def __init__(self, data_fetcher):
        """
        Initialize Quality Analyzer
        
        Args:
            data_fetcher: DataFetcher instance
        """
        self.data_fetcher = data_fetcher
    
    def calculate_quality_scores(self, rs_results: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate quality scores for all stocks
        
        Args:
            rs_results: DataFrame with RS metrics
        
        Returns:
            DataFrame with quality scores merged
        """
        symbols = rs_results['symbol'].tolist()
        
        # Fetch fundamentals
        fundamentals = self.data_fetcher.fetch_fundamentals(symbols)
        
        # Calculate quality score for each stock
        quality_scores = []
        
        for idx, row in fundamentals.iterrows():
            score = self._calculate_composite_quality_score(row)
            quality_scores.append({
                'symbol': row['symbol'],
                'quality_score': score,
                'roe': row['roe'],
                'roa': row['roa'],
                'debt_equity': row['debt_equity'],
                'current_ratio': row['current_ratio'],
                'operating_margin': row['operating_margin'],
                'profit_margin': row['profit_margin'],
                'revenue_growth': row['revenue_growth'],
                'earnings_growth': row['earnings_growth'],
                'free_cash_flow': row['free_cash_flow'],
                'book_value': row['book_value'],
                'price_to_book': row['price_to_book']
            })
        
        quality_df = pd.DataFrame(quality_scores)
        
        # Merge with RS results
        merged = rs_results.merge(quality_df, on='symbol', how='left')
        
        return merged
    
    def _calculate_composite_quality_score(self, row: pd.Series) -> float:
        """
        Calculate composite quality score (0-100)
        
        Scoring components:
        - Profitability (40%): ROE, ROA, Margins
        - Financial Health (30%): Debt/Equity, Current Ratio
        - Growth (20%): Revenue & Earnings growth
        - Cash Generation (10%): Free Cash Flow
        
        Args:
            row: Row with fundamental data
        
        Returns:
            Quality score (0-100)
        """
        score = 0
        
        # 1. Profitability Score (40 points max)
        profitability_score = 0
        
        # ROE (0-15 points)
        roe = row['roe']
        if not np.isnan(roe):
            if roe >= 20:
                profitability_score += 15
            elif roe >= 15:
                profitability_score += 12
            elif roe >= 10:
                profitability_score += 8
            elif roe >= 5:
                profitability_score += 4
        
        # ROA (0-10 points)
        roa = row['roa']
        if not np.isnan(roa):
            if roa >= 10:
                profitability_score += 10
            elif roa >= 7:
                profitability_score += 7
            elif roa >= 5:
                profitability_score += 5
            elif roa >= 3:
                profitability_score += 3
        
        # Operating Margin (0-15 points)
        op_margin = row['operating_margin']
        if not np.isnan(op_margin):
            if op_margin >= 20:
                profitability_score += 15
            elif op_margin >= 15:
                profitability_score += 12
            elif op_margin >= 10:
                profitability_score += 8
            elif op_margin >= 5:
                profitability_score += 4
        
        score += profitability_score
        
        # 2. Financial Health Score (30 points max)
        health_score = 0
        
        # Debt/Equity (0-20 points) - lower is better
        de_ratio = row['debt_equity']
        if not np.isnan(de_ratio):
            if de_ratio <= 0.3:
                health_score += 20
            elif de_ratio <= 0.5:
                health_score += 15
            elif de_ratio <= 1.0:
                health_score += 10
            elif de_ratio <= 2.0:
                health_score += 5
        
        # Current Ratio (0-10 points)
        current_ratio = row['current_ratio']
        if not np.isnan(current_ratio):
            if current_ratio >= 2.0:
                health_score += 10
            elif current_ratio >= 1.5:
                health_score += 7
            elif current_ratio >= 1.0:
                health_score += 5
        
        score += health_score
        
        # 3. Growth Score (20 points max)
        growth_score = 0
        
        # Revenue Growth (0-10 points)
        rev_growth = row['revenue_growth']
        if not np.isnan(rev_growth):
            if rev_growth >= 20:
                growth_score += 10
            elif rev_growth >= 15:
                growth_score += 8
            elif rev_growth >= 10:
                growth_score += 6
            elif rev_growth >= 5:
                growth_score += 4
        
        # Earnings Growth (0-10 points)
        earn_growth = row['earnings_growth']
        if not np.isnan(earn_growth):
            if earn_growth >= 25:
                growth_score += 10
            elif earn_growth >= 20:
                growth_score += 8
            elif earn_growth >= 15:
                growth_score += 6
            elif earn_growth >= 10:
                growth_score += 4
        
        score += growth_score
        
        # 4. Cash Flow Score (10 points max)
        fcf = row['free_cash_flow']
        if not np.isnan(fcf) and fcf > 0:
            # Positive FCF gets full points
            score += 10
        elif not np.isnan(fcf) and fcf > -1000000000:  # Small negative OK
            score += 5
        
        return min(score, 100)  # Cap at 100
    
    def get_quality_grade(self, quality_score: float) -> str:
        """
        Convert quality score to letter grade
        
        Args:
            quality_score: Quality score (0-100)
        
        Returns:
            Letter grade (A+ to F)
        """
        if quality_score >= 90:
            return "A+"
        elif quality_score >= 80:
            return "A"
        elif quality_score >= 70:
            return "B+"
        elif quality_score >= 60:
            return "B"
        elif quality_score >= 50:
            return "C+"
        elif quality_score >= 40:
            return "C"
        elif quality_score >= 30:
            return "D"
        else:
            return "F"
    
    def is_quality_stock(self, 
                        roe: float, 
                        debt_equity: float, 
                        operating_margin: float,
                        min_roe: float = 15,
                        max_de: float = 1.0,
                        min_margin: float = 10) -> bool:
        """
        Check if stock meets quality criteria
        
        Args:
            roe: Return on Equity
            debt_equity: Debt to Equity ratio
            operating_margin: Operating margin percentage
            min_roe: Minimum ROE threshold
            max_de: Maximum D/E threshold
            min_margin: Minimum margin threshold
        
        Returns:
            True if stock is quality
        """
        checks = []
        
        # ROE check
        if not np.isnan(roe):
            checks.append(roe >= min_roe)
        else:
            checks.append(False)
        
        # Debt/Equity check
        if not np.isnan(debt_equity):
            checks.append(debt_equity <= max_de)
        else:
            checks.append(False)
        
        # Operating Margin check
        if not np.isnan(operating_margin):
            checks.append(operating_margin >= min_margin)
        else:
            checks.append(False)
        
        # Must pass all checks
        return all(checks)
