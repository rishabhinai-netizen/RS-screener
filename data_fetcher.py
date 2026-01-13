"""
Data Fetcher Module - PRODUCTION VERSION
Breeze-first approach with yfinance fallback
Robust error handling and data validation
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
from typing import Optional, Dict, List, Tuple
import time
from config import SECTOR_STOCKS, DATA_CONFIG, BENCHMARKS
from cache_manager import get_cache
from data_validator import DataValidator

class DataFetcher:
    """Fetches price and fundamental data with intelligent caching and fallbacks"""
    
    def __init__(self, use_breeze=False, api_key=None, api_secret=None, session_token=None):
        """
        Initialize Data Fetcher
        
        Args:
            use_breeze: Use Breeze API for prices
            api_key: Breeze API key
            api_secret: Breeze API secret
            session_token: Breeze session token
        """
        self.use_breeze = use_breeze
        self.api_key = api_key
        self.api_secret = api_secret
        self.session_token = session_token
        self.breeze = None
        self.cache = get_cache()
        self.validator = DataValidator()
        
        if use_breeze and api_key:
            self._initialize_breeze()
    
    def _initialize_breeze(self) -> bool:
        """Initialize Breeze API connection"""
        try:
            from breeze_connect import BreezeConnect
            
            if not self.api_key:
                print("⚠️  Breeze credentials missing, using yfinance")
                self.use_breeze = False
                return False
            
            self.breeze = BreezeConnect(api_key=self.api_key)
            self.breeze.generate_session(
                api_secret=self.api_secret,
                session_token=self.session_token
            )
            
            print("✅ Breeze API initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ Breeze initialization failed: {e}")
            print("   Falling back to yfinance")
            self.use_breeze = False
            self.breeze = None
            return False
    
    def fetch_universe(self, sector_filter: str = "All Sectors") -> pd.DataFrame:
        """
        Fetch stock universe for selected sector
        
        Args:
            sector_filter: Sector name or "All Sectors"
        
        Returns:
            DataFrame with stock universe
        """
        if sector_filter == "All Sectors":
            # Combine all sectors
            all_stocks = []
            for sector_name, sector_data in SECTOR_STOCKS.items():
                for symbol in sector_data["stocks"]:
                    all_stocks.append({
                        'symbol': symbol,
                        'company_name': symbol.replace('.NS', ''),
                        'sector': sector_name
                    })
        else:
            # Specific sector
            if sector_filter not in SECTOR_STOCKS:
                print(f"⚠️  Unknown sector: {sector_filter}")
                return pd.DataFrame()
            
            sector_data = SECTOR_STOCKS[sector_filter]
            all_stocks = []
            for symbol in sector_data["stocks"]:
                all_stocks.append({
                    'symbol': symbol,
                    'company_name': symbol.replace('.NS', ''),
                    'sector': sector_filter
                })
        
        df = pd.DataFrame(all_stocks)
        print(f"📁 Universe: {len(df)} stocks in {sector_filter}")
        
        return df
    
    def fetch_historical_prices(self, 
                               symbols: List[str], 
                               period_days: int = 365) -> Dict[str, pd.DataFrame]:
        """
        Fetch historical price data with Breeze-first approach
        
        Args:
            symbols: List of stock symbols
            period_days: Days of historical data
        
        Returns:
            Dictionary of symbol -> price DataFrame
        """
        # Check cache first
        cached_data = self.cache.get_price_data(symbols, period_days)
        if cached_data is not None:
            print(f"✅ Loaded {len(cached_data)} stocks from cache")
            return cached_data
        
        print(f"📥 Fetching price data for {len(symbols)} stocks...")
        
        price_data = {}
        
        # Try Breeze first
        if self.use_breeze and self.breeze:
            price_data = self._fetch_prices_breeze(symbols, period_days)
            print(f"   Breeze: {len(price_data)}/{len(symbols)} stocks fetched")
        
        # Fallback to yfinance for missing stocks
        missing_symbols = [s for s in symbols if s not in price_data]
        if missing_symbols:
            print(f"   Fetching {len(missing_symbols)} stocks via yfinance...")
            yf_data = self._fetch_prices_yfinance(missing_symbols, period_days)
            price_data.update(yf_data)
        
        # Validate data quality
        valid_data, issues = self.validator.validate_price_data(price_data, min_days=period_days)
        
        if issues:
            print(f"⚠️  {len(issues)} stocks excluded due to data quality issues")
        
        # Cache valid data
        self.cache.set_price_data(symbols, period_days, valid_data)
        
        print(f"✅ {len(valid_data)}/{len(symbols)} stocks with valid price data")
        
        return valid_data
    
    def _fetch_prices_breeze(self, symbols: List[str], period_days: int) -> Dict[str, pd.DataFrame]:
        """Fetch prices using Breeze API"""
        price_data = {}
        
        to_date = datetime.now().isoformat()[:19] + '.000Z'
        from_date = (datetime.now() - timedelta(days=period_days + 30)).isoformat()[:19] + '.000Z'
        
        for symbol in symbols:
            try:
                stock_code = symbol.replace('.NS', '')
                
                data = self.breeze.get_historical_data_v2(
                    interval="1day",
                    from_date=from_date,
                    to_date=to_date,
                    stock_code=stock_code,
                    exchange_code="NSE",
                    product_type="cash"
                )
                
                if data.get('Status') == 200 and data.get('Success'):
                    df = pd.DataFrame(data['Success'])
                    df['datetime'] = pd.to_datetime(df['datetime'])
                    df.set_index('datetime', inplace=True)
                    
                    # Standardize column names
                    df = df.rename(columns={
                        'close': 'Close',
                        'open': 'Open',
                        'high': 'High',
                        'low': 'Low',
                        'volume': 'Volume'
                    })
                    
                    # Convert to numeric
                    for col in ['Close', 'Open', 'High', 'Low', 'Volume']:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    price_data[symbol] = df
                    
            except Exception as e:
                print(f"   Breeze error for {symbol}: {str(e)[:50]}")
                continue
        
        return price_data
    
    def _fetch_prices_yfinance(self, symbols: List[str], period_days: int) -> Dict[str, pd.DataFrame]:
        """Fetch prices using yfinance with chunking and delays"""
        price_data = {}
        
        chunk_size = DATA_CONFIG['yfinance_chunk_size']
        delay = DATA_CONFIG['yfinance_delay']
        
        for i in range(0, len(symbols), chunk_size):
            chunk = symbols[i:i+chunk_size]
            
            try:
                # Fetch data
                data = yf.download(
                    chunk,
                    period=f"{period_days}d",
                    group_by='ticker',
                    progress=False,
                    threads=True,
                    timeout=DATA_CONFIG['yfinance_timeout']
                )
                
                # Extract individual stock data
                if len(chunk) == 1:
                    # Single stock
                    symbol = chunk[0]
                    if not data.empty:
                        price_data[symbol] = data
                else:
                    # Multiple stocks
                    for symbol in chunk:
                        try:
                            if symbol in data.columns.levels[0]:
                                df = data[symbol].copy()
                                if not df.empty and len(df) > 0:
                                    price_data[symbol] = df
                        except Exception as e:
                            print(f"   Error extracting {symbol}: {str(e)[:30]}")
                
                # Delay between chunks
                if i + chunk_size < len(symbols):
                    time.sleep(delay)
                    
            except Exception as e:
                print(f"   yfinance chunk error: {str(e)[:50]}")
                continue
        
        return price_data
    
    def fetch_fundamentals(self, symbols: List[str]) -> pd.DataFrame:
        """
        Fetch fundamental data for stocks
        
        Args:
            symbols: List of stock symbols
        
        Returns:
            DataFrame with fundamental metrics
        """
        # Check cache
        cached_data = self.cache.get_fundamentals(symbols)
        if cached_data is not None:
            print(f"✅ Loaded fundamentals from cache")
            return cached_data
        
        print(f"💰 Fetching fundamentals for {len(symbols)} stocks...")
        
        fundamentals = []
        
        for symbol in symbols:
            fund_data = {
                'symbol': symbol,
                'roe': np.nan,
                'roa': np.nan,
                'debt_equity': np.nan,
                'current_ratio': np.nan,
                'operating_margin': np.nan,
                'profit_margin': np.nan,
                'market_cap': 0,
                'pe_ratio': np.nan,
                'price_to_book': np.nan,
                'current_price': 0
            }
            
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                
                if info and 'symbol' in info:
                    # Extract metrics
                    fund_data.update({
                        'roe': info.get('returnOnEquity', np.nan) * 100 if info.get('returnOnEquity') else np.nan,
                        'roa': info.get('returnOnAssets', np.nan) * 100 if info.get('returnOnAssets') else np.nan,
                        'debt_equity': info.get('debtToEquity', np.nan) / 100 if info.get('debtToEquity') else np.nan,
                        'current_ratio': info.get('currentRatio', np.nan),
                        'operating_margin': info.get('operatingMargins', np.nan) * 100 if info.get('operatingMargins') else np.nan,
                        'profit_margin': info.get('profitMargins', np.nan) * 100 if info.get('profitMargins') else np.nan,
                        'market_cap': info.get('marketCap', 0) / 10000000,  # Convert to Crores
                        'pe_ratio': info.get('trailingPE', np.nan),
                        'price_to_book': info.get('priceToBook', np.nan),
                        'current_price': info.get('currentPrice', info.get('regularMarketPrice', 0))
                    })
                    
            except Exception as e:
                print(f"   Error fetching {symbol}: {str(e)[:30]}")
            
            fundamentals.append(fund_data)
        
        df = pd.DataFrame(fundamentals)
        
        # Validate data
        valid_df, issues = self.validator.validate_fundamentals(df)
        
        if issues:
            print(f"⚠️  {len(issues)} stocks with incomplete/invalid fundamentals")
        
        # Cache results
        self.cache.set_fundamentals(symbols, valid_df)
        
        print(f"✅ {len(valid_df)}/{len(symbols)} stocks with valid fundamentals")
        
        return valid_df
    
    def get_benchmark_data(self, benchmark: str = "NIFTY50", period_days: int = 365) -> Optional[pd.DataFrame]:
        """
        Fetch benchmark index data
        
        Args:
            benchmark: Benchmark name (NIFTY50, NIFTY500, etc.)
            period_days: Days of historical data
        
        Returns:
            DataFrame with benchmark prices
        """
        if benchmark not in BENCHMARKS:
            print(f"⚠️  Unknown benchmark: {benchmark}")
            return None
        
        symbol = BENCHMARKS[benchmark]
        
        try:
            data = yf.Ticker(symbol).history(period=f"{period_days}d")
            if not data.empty:
                return data
        except Exception as e:
            print(f"Error fetching {benchmark}: {e}")
        
        return None
