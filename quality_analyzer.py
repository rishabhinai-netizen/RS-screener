"""Quality Analyzer - Simplified 6-Metric Version"""
import pandas as pd
import numpy as np
from config import QUALITY_THRESHOLDS, QUALITY_WEIGHTS

class QualityAnalyzer:
    def __init__(self, fundamentals_df: pd.DataFrame):
        self.fundamentals_df = fundamentals_df
    
    def calculate_quality_scores(self) -> pd.DataFrame:
        df = self.fundamentals_df.copy()
        df['quality_score'] = df.apply(self._calc_quality_score, axis=1)
        df['quality_grade'] = df['quality_score'].apply(self._get_grade)
        return df
    
    def _calc_quality_score(self, row: pd.Series) -> float:
        score = 0
        for metric, weight in QUALITY_WEIGHTS.items():
            if metric in row and not pd.isna(row[metric]):
                metric_score = self._score_metric(metric, row[metric])
                score += weight * metric_score
            else:
                score += weight * 50
        return min(score * 100, 100)
    
    def _score_metric(self, metric: str, value: float) -> float:
        thresholds = QUALITY_THRESHOLDS[metric]
        if metric == 'debt_equity':
            if value <= thresholds['excellent']:
                return 1.0
            elif value <= thresholds['good']:
                return 0.75
            elif value <= thresholds['acceptable']:
                return 0.50
            elif value <= thresholds['poor']:
                return 0.25
            else:
                return 0
        else:
            if value >= thresholds['excellent']:
                return 1.0
            elif value >= thresholds['good']:
                return 0.75
            elif value >= thresholds['acceptable']:
                return 0.50
            elif value >= thresholds['poor']:
                return 0.25
            else:
                return 0
    
    def _get_grade(self, score: float) -> str:
        if score >= 90: return "A+"
        elif score >= 80: return "A"
        elif score >= 70: return "B+"
        elif score >= 60: return "B"
        elif score >= 50: return "C"
        else: return "D"
    
    def is_quality_stock(self, row: pd.Series, min_roe: float = 15, max_de: float = 1.0, min_margin: float = 10) -> bool:
        checks = []
        if 'roe' in row and not pd.isna(row['roe']):
            checks.append(row['roe'] >= min_roe)
        if 'debt_equity' in row and not pd.isna(row['debt_equity']):
            checks.append(row['debt_equity'] <= max_de)
        if 'operating_margin' in row and not pd.isna(row['operating_margin']):
            checks.append(row['operating_margin'] >= min_margin)
        return len(checks) >= 2 and all(checks)
