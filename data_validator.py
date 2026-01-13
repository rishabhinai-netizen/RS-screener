"""
Data Validator Module
Validates data quality and completeness before calculations
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime, timedelta

class DataValidator:
    """Validates data quality and identifies issues"""
    
    def __init__(self):
        """Initialize Data Validator"""
        self.validation_results = {}
    
    def validate_price_data(self, 
                          price_data: Dict[str, pd.DataFrame],
                          min_days: int = 252) -> Tuple[Dict[str, pd.DataFrame], Dict[str, str]]:
        """
        Validate price data quality
        
        Args:
            price_data: Dictionary of symbol -> price DataFrame
            min_days: Minimum required days of data
        
        Returns:
            Tuple of (valid_data, issues_dict)
        """
        valid_data = {}
        issues = {}
        
        for symbol, df in price_data.items():
            if df is None or df.empty:
                issues[symbol] = "No price data available"
                continue
            
            # Check 1: Sufficient history
            if len(df) < min_days:
                issues[symbol] = f"Insufficient data: {len(df)} days (need {min_days})"
                continue
            
            # Check 2: No excessive missing values
            missing_pct = df['Close'].isna().sum() / len(df) * 100
            if missing_pct > 5:
                issues[symbol] = f"Too many missing values: {missing_pct:.1f}%"
                continue
            
            # Check 3: No extreme outliers (possible data errors)
            returns = df['Close'].pct_change()
            if (returns.abs() > 0.50).any():  # 50% single-day move = likely error
                issues[symbol] = "Extreme price movements detected (possible data error)"
                continue
            
            # Check 4: Recent data available
            last_date = df.index[-1]
            days_old = (datetime.now() - last_date).days
            if days_old > 7:
                issues[symbol] = f"Stale data: Last update {days_old} days ago"
                continue
            
            # Check 5: Volume data available
            if 'Volume' not in df.columns or df['Volume'].isna().all():
                issues[symbol] = "Missing volume data"
                continue
            
            # Passed all checks
            valid_data[symbol] = df
        
        return valid_data, issues
    
    def validate_fundamentals(self, 
                            fundamentals_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, List[str]]]:
        """
        Validate fundamental data quality
        
        Args:
            fundamentals_df: DataFrame with fundamental metrics
        
        Returns:
            Tuple of (valid_df, issues_by_stock)
        """
        required_fields = ['roe', 'debt_equity', 'operating_margin', 
                          'current_ratio', 'profit_margin', 'roa']
        
        issues_by_stock = {}
        
        for idx, row in fundamentals_df.iterrows():
            symbol = row['symbol']
            missing_fields = []
            invalid_fields = []
            
            # Check each required field
            for field in required_fields:
                if field not in row or pd.isna(row[field]):
                    missing_fields.append(field)
                else:
                    # Validate reasonable ranges
                    value = row[field]
                    
                    if field == 'roe' and (value < -100 or value > 200):
                        invalid_fields.append(f"{field}={value:.1f}% (unrealistic)")
                    elif field == 'debt_equity' and (value < 0 or value > 10):
                        invalid_fields.append(f"{field}={value:.2f} (unrealistic)")
                    elif field in ['operating_margin', 'profit_margin'] and (value < -50 or value > 100):
                        invalid_fields.append(f"{field}={value:.1f}% (unrealistic)")
                    elif field == 'current_ratio' and (value < 0 or value > 20):
                        invalid_fields.append(f"{field}={value:.2f} (unrealistic)")
                    elif field == 'roa' and (value < -50 or value > 100):
                        invalid_fields.append(f"{field}={value:.1f}% (unrealistic)")
            
            # Record issues
            all_issues = []
            if missing_fields:
                all_issues.append(f"Missing: {', '.join(missing_fields)}")
            if invalid_fields:
                all_issues.append(f"Invalid: {', '.join(invalid_fields)}")
            
            if all_issues:
                issues_by_stock[symbol] = all_issues
        
        # Create valid subset (stocks with at least 4 out of 6 metrics)
        def count_valid_metrics(row):
            count = 0
            for field in required_fields:
                if field in row and not pd.isna(row[field]):
                    value = row[field]
                    # Basic range check
                    if field == 'roe' and -100 <= value <= 200:
                        count += 1
                    elif field == 'debt_equity' and 0 <= value <= 10:
                        count += 1
                    elif field in ['operating_margin', 'profit_margin'] and -50 <= value <= 100:
                        count += 1
                    elif field == 'current_ratio' and 0 <= value <= 20:
                        count += 1
                    elif field == 'roa' and -50 <= value <= 100:
                        count += 1
            return count
        
        fundamentals_df['valid_metric_count'] = fundamentals_df.apply(count_valid_metrics, axis=1)
        valid_df = fundamentals_df[fundamentals_df['valid_metric_count'] >= 4].copy()
        
        return valid_df, issues_by_stock
    
    def validate_rs_results(self, rs_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
        """
        Validate RS calculation results
        
        Args:
            rs_df: DataFrame with RS metrics
        
        Returns:
            Tuple of (valid_df, issues_dict)
        """
        issues = {}
        
        for idx, row in rs_df.iterrows():
            symbol = row['symbol']
            
            # Check RS percentile is in valid range
            if 'rs_percentile' in row:
                if pd.isna(row['rs_percentile']) or row['rs_percentile'] < 0 or row['rs_percentile'] > 100:
                    issues[symbol] = f"Invalid RS percentile: {row['rs_percentile']}"
                    continue
            else:
                issues[symbol] = "Missing RS percentile"
                continue
            
            # Check for reasonable volatility
            if 'volatility' in row and not pd.isna(row['volatility']):
                if row['volatility'] > 150:  # >150% annualized is extreme
                    issues[symbol] = f"Extreme volatility: {row['volatility']:.1f}%"
        
        # Filter valid rows
        valid_df = rs_df[~rs_df['symbol'].isin(issues.keys())].copy()
        
        return valid_df, issues
    
    def generate_validation_report(self, 
                                  price_issues: Dict,
                                  fundamental_issues: Dict,
                                  rs_issues: Dict) -> pd.DataFrame:
        """
        Generate comprehensive validation report
        
        Args:
            price_issues: Issues from price validation
            fundamental_issues: Issues from fundamental validation
            rs_issues: Issues from RS validation
        
        Returns:
            DataFrame with validation report
        """
        all_symbols = set(list(price_issues.keys()) + 
                         list(fundamental_issues.keys()) + 
                         list(rs_issues.keys()))
        
        report_data = []
        
        for symbol in all_symbols:
            issues_list = []
            
            if symbol in price_issues:
                issues_list.append(f"Price: {price_issues[symbol]}")
            
            if symbol in fundamental_issues:
                issues_list.append(f"Fundamentals: {'; '.join(fundamental_issues[symbol])}")
            
            if symbol in rs_issues:
                issues_list.append(f"RS: {rs_issues[symbol]}")
            
            report_data.append({
                'symbol': symbol,
                'issues': ' | '.join(issues_list),
                'price_issue': symbol in price_issues,
                'fundamental_issue': symbol in fundamental_issues,
                'rs_issue': symbol in rs_issues
            })
        
        return pd.DataFrame(report_data)
    
    def calculate_data_quality_score(self, 
                                    symbol: str,
                                    has_price: bool,
                                    has_fundamentals: bool,
                                    fundamental_count: int,
                                    has_rs: bool) -> float:
        """
        Calculate overall data quality score for a stock (0-100)
        
        Args:
            symbol: Stock symbol
            has_price: Has valid price data
            has_fundamentals: Has fundamental data
            fundamental_count: Number of valid fundamental metrics
            has_rs: Has RS calculations
        
        Returns:
            Quality score 0-100
        """
        score = 0
        
        # Price data (40 points)
        if has_price:
            score += 40
        
        # Fundamental data (40 points)
        if has_fundamentals:
            # Pro-rated based on available metrics
            score += (fundamental_count / 6) * 40
        
        # RS calculations (20 points)
        if has_rs:
            score += 20
        
        return score
    
    def get_quality_grade(self, score: float) -> str:
        """Convert quality score to letter grade"""
        if score >= 90:
            return "A"
        elif score >= 75:
            return "B"
        elif score >= 60:
            return "C"
        elif score >= 40:
            return "D"
        else:
            return "F"
