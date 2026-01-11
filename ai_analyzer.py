"""
AI Analyzer Module
Uses Groq API for intelligent stock analysis and insights
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List
import json
import requests

class AIAnalyzer:
    """AI-powered stock analysis using Groq"""
    
    def __init__(self, groq_api_key: Optional[str] = None):
        """
        Initialize AI Analyzer
        
        Args:
            groq_api_key: Groq API key for AI analysis
        """
        self.groq_api_key = groq_api_key
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "mixtral-8x7b-32768"  # or "llama2-70b-4096"
    
    def analyze_top_stocks(self, results_df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
        """
        Analyze top stocks and provide AI insights
        
        Args:
            results_df: DataFrame with screening results
            top_n: Number of top stocks to analyze
        
        Returns:
            DataFrame with AI analysis added
        """
        if not self.groq_api_key:
            results_df['ai_reasoning'] = None
            return results_df
        
        # Sort by composite score and get top N
        top_stocks = results_df.nlargest(top_n, 'composite_score')
        
        analyses = []
        
        for idx, stock in top_stocks.iterrows():
            try:
                analysis = self._analyze_single_stock(stock)
                analyses.append({
                    'symbol': stock['symbol'],
                    'ai_reasoning': analysis
                })
            except Exception as e:
                print(f"Error analyzing {stock['symbol']}: {e}")
                analyses.append({
                    'symbol': stock['symbol'],
                    'ai_reasoning': None
                })
        
        # Create analysis dataframe
        analysis_df = pd.DataFrame(analyses)
        
        # Merge with original results
        results_with_ai = results_df.merge(analysis_df, on='symbol', how='left')
        
        return results_with_ai
    
    def _analyze_single_stock(self, stock: pd.Series) -> str:
        """
        Generate AI analysis for a single stock
        
        Args:
            stock: Stock data series
        
        Returns:
            AI-generated analysis text
        """
        # Prepare stock data for analysis
        stock_summary = self._prepare_stock_summary(stock)
        
        # Create prompt
        prompt = self._create_analysis_prompt(stock_summary)
        
        # Call Groq API
        response = self._call_groq_api(prompt)
        
        return response
    
    def _prepare_stock_summary(self, stock: pd.Series) -> str:
        """Prepare stock summary for AI analysis"""
        
        summary = f"""
Stock: {stock['symbol']} - {stock['company_name']}
Sector: {stock['sector']}

RELATIVE STRENGTH METRICS:
- RS Percentile: {stock['rs_percentile']:.1f} (Rank: {stock.get('rs_rank', 'N/A')})
- vs Nifty 50: {stock.get('rs_vs_nifty50', 'N/A'):.2f}%
- vs Sector: {stock.get('rs_vs_sector', 'N/A'):.2f}%
- 12M Return: {stock.get('return_12m', 'N/A'):.2f}%
- 6M Return: {stock.get('return_6m', 'N/A'):.2f}%
- 3M Return: {stock.get('return_3m', 'N/A'):.2f}%
- Trend Strength: {stock.get('trend_strength', 'N/A'):.1f}/100
- Volatility: {stock.get('volatility', 'N/A'):.1f}%

QUALITY METRICS:
- Quality Score: {stock['quality_score']:.1f}/100
- ROE: {stock.get('roe', 'N/A'):.1f}%
- Debt/Equity: {stock.get('debt_equity', 'N/A'):.2f}
- Operating Margin: {stock.get('operating_margin', 'N/A'):.1f}%
- Profit Margin: {stock.get('profit_margin', 'N/A'):.1f}%
- Revenue Growth: {stock.get('revenue_growth', 'N/A'):.1f}%
- Earnings Growth: {stock.get('earnings_growth', 'N/A'):.1f}%

VALUATION:
- P/E Ratio: {stock.get('pe_ratio', 'N/A'):.1f}
- Price to Book: {stock.get('price_to_book', 'N/A'):.2f}
- Market Cap: ₹{stock['market_cap']:.0f} Cr
- Current Price: ₹{stock['current_price']:.2f}

COMPOSITE ANALYSIS:
- Composite Score: {stock['composite_score']:.1f}/100
- Signal: {stock['signal']}
"""
        return summary
    
    def _create_analysis_prompt(self, stock_summary: str) -> str:
        """Create detailed prompt for AI analysis"""
        
        prompt = f"""You are a legendary stock market analyst with deep expertise in William O'Neil's CAN SLIM methodology, Stan Weinstein's Stage Analysis, and quality investing principles like Warren Buffett.

Analyze the following stock using a combination of Relative Strength (momentum) and Quality factors:

{stock_summary}

Provide a concise, actionable analysis covering:

1. **Momentum Analysis** (2-3 sentences):
   - Evaluate the RS percentile and trend strength
   - Compare performance vs benchmark and sector
   - Assess if momentum is accelerating or decelerating

2. **Quality Assessment** (2-3 sentences):
   - Evaluate financial health (ROE, debt levels, margins)
   - Assess growth sustainability
   - Identify any quality red flags

3. **Risk Factors** (2-3 sentences):
   - Key risks based on the data (volatility, valuation, sector dynamics)
   - What could go wrong with this investment?

4. **Investment Verdict** (2-3 sentences):
   - Clear BUY/WATCH/AVOID recommendation with reasoning
   - Ideal entry/exit strategy
   - Expected holding period

Keep the analysis:
- Brutally honest (don't sugarcoat weaknesses)
- Actionable (specific recommendations)
- Evidence-based (reference the numbers)
- Concise (max 300 words total)
- Professional yet accessible

Remember: A high RS stock with poor quality is speculation, not investment. A high-quality stock with low RS might be dead money. We want BOTH.
"""
        return prompt
    
    def _call_groq_api(self, prompt: str) -> str:
        """
        Call Groq API for text generation
        
        Args:
            prompt: Analysis prompt
        
        Returns:
            Generated analysis text
        """
        if not self.groq_api_key:
            return "AI analysis not available (no API key)"
        
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert stock analyst combining momentum and quality investing principles. Provide clear, actionable insights."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 800,
            "top_p": 1,
            "stream": False
        }
        
        try:
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            analysis = result['choices'][0]['message']['content']
            
            return analysis.strip()
            
        except requests.exceptions.RequestException as e:
            print(f"Groq API error: {e}")
            return f"AI analysis unavailable: {str(e)}"
        except Exception as e:
            print(f"Unexpected error: {e}")
            return "AI analysis unavailable due to unexpected error"
    
    def generate_portfolio_summary(self, results_df: pd.DataFrame) -> str:
        """
        Generate overall portfolio-level insights
        
        Args:
            results_df: Full screening results
        
        Returns:
            Portfolio summary text
        """
        if not self.groq_api_key:
            return "Portfolio analysis not available"
        
        # Calculate portfolio statistics
        stats = {
            'total_stocks': len(results_df),
            'buy_signals': len(results_df[results_df['signal'] == 'BUY']),
            'avg_rs': results_df['rs_percentile'].mean(),
            'avg_quality': results_df['quality_score'].mean(),
            'top_sectors': results_df['sector'].value_counts().head(5).to_dict(),
            'avg_volatility': results_df['volatility'].mean(),
            'high_momentum_count': len(results_df[results_df['rs_percentile'] >= 90])
        }
        
        prompt = f"""Analyze this stock screening portfolio and provide strategic insights:

PORTFOLIO STATISTICS:
- Total Stocks Screened: {stats['total_stocks']}
- Strong BUY Signals: {stats['buy_signals']}
- Average RS Percentile: {stats['avg_rs']:.1f}
- Average Quality Score: {stats['avg_quality']:.1f}
- Average Volatility: {stats['avg_volatility']:.1f}%
- High Momentum Stocks (RS ≥90): {stats['high_momentum_count']}

TOP SECTORS:
{json.dumps(stats['top_sectors'], indent=2)}

Provide:
1. Overall portfolio characterization (growth/quality/balanced?)
2. Sector concentration risks
3. Market timing considerations based on average RS
4. Recommended position sizing approach
5. Key risks to monitor

Keep it concise (200 words max) and actionable.
"""
        
        return self._call_groq_api(prompt)
