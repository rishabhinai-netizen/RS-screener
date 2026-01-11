"""
Data Fetcher Module
Handles data fetching from Breeze API or yfinance
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
from typing import Optional, Dict, List
import requests
import time

class DataFetcher:
    """Fetches stock data from various sources"""
    
    def __init__(self, source="yfinance", api_key=None, api_secret=None, session_token=None):
        """
        Initialize data fetcher
        
        Args:
            source: "breeze" or "yfinance"
            api_key: Breeze API key (if using Breeze)
            api_secret: Breeze API secret
            session_token: Breeze session token
        """
        self.source = source
        self.api_key = api_key
        self.api_secret = api_secret
        self.session_token = session_token
        
        if source == "breeze":
            self._initialize_breeze()
        
        # NSE 500 symbol list
        self.nse500_symbols = None
        self.sector_mapping = {}
    
    def _initialize_breeze(self):
        """Initialize Breeze API connection"""
        try:
            from breeze_connect import BreezeConnect
            self.breeze = BreezeConnect(api_key=self.api_key)
            self.breeze.generate_session(
                api_secret=self.api_secret,
                session_token=self.session_token
            )
        except Exception as e:
            print(f"Failed to initialize Breeze: {e}")
            self.source = "yfinance"  # Fallback
    
    def fetch_nse500_universe(self) -> pd.DataFrame:
        """
        Fetch NSE 500 stock universe with basic info
        
        Returns:
            DataFrame with symbol, company_name, sector, market_cap
        """
        # NSE 500 constituents - you can update this list or fetch dynamically
        # For now, using a comprehensive list of major NSE stocks
        
        nse500_list = self._get_nse500_list()
        
        data = []
        for symbol in nse500_list:
            try:
                stock_info = self._get_stock_info(symbol)
                if stock_info:
                    data.append(stock_info)
                time.sleep(0.1)  # Rate limiting
            except Exception as e:
                print(f"Error fetching {symbol}: {e}")
                continue
        
        df = pd.DataFrame(data)
        self.nse500_symbols = df['symbol'].tolist()
        
        return df
    
    def _get_nse500_list(self) -> List[str]:
        """Get list of NSE 500 symbols"""
        # Major NSE stocks across sectors (Top 500 by market cap representation)
        # In production, fetch this from NSE website or maintain updated list
        
        major_stocks = [
            # Financials
            "HDFCBANK", "ICICIBANK", "KOTAKBANK", "AXISBANK", "SBIN",
            "BAJFINANCE", "BAJAJFINSV", "HDFC", "LT", "HDFCLIFE",
            "SBILIFE", "ICICIGI", "HDFCAMC", "MUTHOOTFIN", "CHOLAFIN",
            
            # IT
            "TCS", "INFY", "WIPRO", "HCLTECH", "TECHM",
            "LTIM", "COFORGE", "MPHASIS", "PERSISTENT", "LTTS",
            
            # Auto
            "MARUTI", "M&M", "TATAMOTORS", "BAJAJ-AUTO", "EICHERMOT",
            "HEROMOTOCO", "TVSMOTOR", "ASHOKLEY", "APOLLOTYRE", "MRF",
            
            # FMCG
            "HINDUNILVR", "ITC", "NESTLEIND", "BRITANNIA", "DABUR",
            "MARICO", "GODREJCP", "COLPAL", "TATACONSUM", "EMAMILTD",
            
            # Pharma
            "SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB", "AUROPHARMA",
            "LUPIN", "TORNTPHARM", "ALKEM", "BIOCON", "ZYDUSLIFE",
            
            # Energy & Oil/Gas
            "RELIANCE", "ONGC", "IOC", "BPCL", "ADANIGREEN",
            "ADANIPORTS", "ADANIENT", "POWERGRID", "NTPC", "COALINDIA",
            
            # Metals
            "TATASTEEL", "JSWSTEEL", "HINDALCO", "VEDL", "SAIL",
            "NMDC", "HINDCOPPER", "NATIONALUM", "JINDALSTEL", "JSWENERGY",
            
            # Cement
            "ULTRACEMCO", "SHREECEM", "GRASIM", "AMBUJACEM", "ACC",
            "DALMIACEMT", "JKCEMENT", "RAMCOCEM", "HEIDELBERG", "INDIACEM",
            
            # Consumer Durables
            "TITAN", "VOLTAS", "HAVELLS", "DIXON", "CROMPTON",
            "WHIRLPOOL", "BLUESTAR", "BATAINDIA", "RELAXO", "SYMPHONY",
            
            # Capital Goods & Infra
            "LT", "ABB", "SIEMENS", "BEL", "HAL",
            "BHEL", "THERMAX", "CUMMINSIND", "IRFC", "IRCTC",
            
            # Telecom
            "BHARTIARTL", "INDUSINDBK",
            
            # Realty
            "DLF", "GODREJPROP", "OBEROIRLTY", "PRESTIGE", "PHOENIXLTD",
            
            # PSU Banks
            "SBIN", "PNB", "BANKBARODA", "CANBK", "UNIONBANK",
            
            # Private Banks
            "HDFCBANK", "ICICIBANK", "KOTAKBANK", "AXISBANK", "INDUSINDBK",
            
            # Additional top stocks
            "ASIANPAINT", "PIDILITIND", "BERGEPAINT", "AKZOINDIA", "KANSAINER",
            "LTIM", "COFORGE", "MPHASIS", "PERSISTENT", "LTTS",
            "ZOMATO", "NYKAA", "PAYTM", "DMART", "TRENT"
        ]
        
        # Add .NS suffix for Yahoo Finance
        return [f"{symbol}.NS" for symbol in major_stocks]
    
    def _get_stock_info(self, symbol: str) -> Optional[Dict]:
        """Get basic stock information"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            return {
                'symbol': symbol,
                'company_name': info.get('longName', symbol.replace('.NS', '')),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                'market_cap': info.get('marketCap', 0) / 10000000,  # Convert to Cr
                'current_price': info.get('currentPrice', info.get('regularMarketPrice', 0)),
                'pe_ratio': info.get('trailingPE', np.nan),
                'beta': info.get('beta', np.nan)
            }
        except:
            return None
    
    def fetch_historical_prices(self, symbols: List[str], period_days: int = 365) -> Dict[str, pd.DataFrame]:
        """
        Fetch historical price data for multiple symbols
        
        Args:
            symbols: List of stock symbols
            period_days: Number of days of historical data
        
        Returns:
            Dictionary mapping symbol to price DataFrame
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)
        
        price_data = {}
        
        if self.source == "yfinance":
            for symbol in symbols:
                try:
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(start=start_date, end=end_date)
                    if not hist.empty:
                        price_data[symbol] = hist
                    time.sleep(0.1)
                except Exception as e:
                    print(f"Error fetching prices for {symbol}: {e}")
                    continue
        
        return price_data
    
    def fetch_fundamentals(self, symbols: List[str]) -> pd.DataFrame:
        """
        Fetch fundamental data for quality analysis
        
        Args:
            symbols: List of stock symbols
        
        Returns:
            DataFrame with fundamental metrics
        """
        fundamentals = []
        
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                
                # Get financials
                balance_sheet = ticker.balance_sheet
                income_stmt = ticker.income_stmt
                cash_flow = ticker.cashflow
                
                # Calculate metrics
                fund_data = {
                    'symbol': symbol,
                    'roe': info.get('returnOnEquity', np.nan) * 100 if info.get('returnOnEquity') else np.nan,
                    'roa': info.get('returnOnAssets', np.nan) * 100 if info.get('returnOnAssets') else np.nan,
                    'debt_equity': info.get('debtToEquity', np.nan) / 100 if info.get('debtToEquity') else np.nan,
                    'current_ratio': info.get('currentRatio', np.nan),
                    'operating_margin': info.get('operatingMargins', np.nan) * 100 if info.get('operatingMargins') else np.nan,
                    'profit_margin': info.get('profitMargins', np.nan) * 100 if info.get('profitMargins') else np.nan,
                    'revenue_growth': info.get('revenueGrowth', np.nan) * 100 if info.get('revenueGrowth') else np.nan,
                    'earnings_growth': info.get('earningsGrowth', np.nan) * 100 if info.get('earningsGrowth') else np.nan,
                    'free_cash_flow': info.get('freeCashflow', 0),
                    'book_value': info.get('bookValue', np.nan),
                    'price_to_book': info.get('priceToBook', np.nan),
                }
                
                fundamentals.append(fund_data)
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Error fetching fundamentals for {symbol}: {e}")
                continue
        
        return pd.DataFrame(fundamentals)
    
    def get_sector_index_data(self, sector: str, period_days: int = 365) -> Optional[pd.DataFrame]:
        """
        Get sector index data for comparison
        
        Args:
            sector: Sector name
            period_days: Historical period
        
        Returns:
            DataFrame with sector index prices
        """
        # Sector index mapping (Nifty sector indices)
        sector_indices = {
            'IT': '^CNXIT',
            'AUTO': '^CNXAUTO',
            'BANK': '^NSEBANK',
            'FINANCIAL SERVICES': '^NIFTYFIN',
            'FMCG': '^CNXFMCG',
            'PHARMA': '^CNXPHARMA',
            'REALTY': '^CNXREALTY',
            'METALS': '^CNXMETAL',
            'MEDIA': '^CNXMEDIA',
            'OIL & GAS': '^CNXENERGY',
            'PSU BANK': '^CNXPSUBANK',
        }
        
        index_symbol = sector_indices.get(sector.upper())
        if not index_symbol:
            return None
        
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=period_days)
            
            ticker = yf.Ticker(index_symbol)
            hist = ticker.history(start=start_date, end=end_date)
            return hist
        except:
            return None
    
    def get_benchmark_data(self, benchmark: str = "NIFTY50", period_days: int = 365) -> Optional[pd.DataFrame]:
        """
        Get benchmark index data
        
        Args:
            benchmark: "NIFTY50" or "NSE500"
            period_days: Historical period
        
        Returns:
            DataFrame with benchmark prices
        """
        benchmark_map = {
            'NIFTY50': '^NSEI',
            'NSE500': '^CRSLDX'  # CNX500
        }
        
        symbol = benchmark_map.get(benchmark)
        if not symbol:
            return None
        
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=period_days)
            
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start_date, end=end_date)
            return hist
        except:
            return None
