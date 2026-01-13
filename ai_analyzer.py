"""AI Analyzer - Improved Prompts"""
import pandas as pd
import requests
from typing import Optional

class AIAnalyzer:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "mixtral-8x7b-32768"
    
    def analyze_top_stocks(self, df: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
        if not self.api_key:
            df['ai_analysis'] = "AI analysis not available (configure Groq API key)"
            return df
        top_stocks = df.nlargest(top_n, 'composite_score')
        analyses = []
        for _, stock in top_stocks.iterrows():
            try:
                analysis = self._analyze_stock(stock)
                analyses.append({'symbol': stock['symbol'], 'ai_analysis': analysis})
            except Exception as e:
                analyses.append({'symbol': stock['symbol'], 'ai_analysis': f"Analysis failed: {str(e)[:50]}"})
        analysis_df = pd.DataFrame(analyses)
        return df.merge(analysis_df, on='symbol', how='left')
    
    def _analyze_stock(self, stock: pd.Series) -> str:
        prompt = f"""Analyze this stock as a legendary investor combining O'Neil's momentum and Buffett's quality:

{stock['symbol']} - {stock.get('company_name', 'N/A')} | Sector: {stock.get('sector', 'N/A')}

MOMENTUM: RS Percentile {stock['rs_percentile']:.1f} (Rank {stock.get('rs_rank', 'N/A')}), 12M Return {stock.get('return_12m', 0):.1f}%, Volatility {stock.get('volatility', 0):.1f}%
QUALITY: Score {stock['quality_score']:.1f}/100, ROE {stock.get('roe', 0):.1f}%, D/E {stock.get('debt_equity', 0):.2f}, Op Margin {stock.get('operating_margin', 0):.1f}%
VALUATION: P/E {stock.get('pe_ratio', 0):.1f}, Price ₹{stock['current_price']:.2f}, MCap ₹{stock['market_cap']:.0f} Cr
SIGNAL: {stock['signal']} (Composite {stock['composite_score']:.1f}/100)

Provide brutally honest 200-word analysis:
1. Momentum Quality (2 sentences)
2. Quality Assessment (2 sentences)  
3. Key Risks (2 sentences)
4. Verdict: BUY/WATCH/AVOID with reasoning (2 sentences)"""
        
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"model": self.model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.7, "max_tokens": 500}
        try:
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content'].strip()
        except Exception as e:
            return f"AI analysis unavailable: {str(e)[:50]}"
