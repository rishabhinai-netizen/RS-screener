"""
Data Fetcher Module
Handles data fetching from Breeze API (for prices) and yfinance (for fundamentals)
Includes Sector-wise classification to reduce load.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
from typing import Optional, Dict, List
import time

class DataFetcher:
    
    # -------------------------------------------------------------------------
    # STATIC SECTOR UNIVERSE
    # -------------------------------------------------------------------------
    SECTOR_STOCKS = {
        "Banking & Finance": [
            "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS", "AXISBANK.NS", 
            "BAJFINANCE.NS", "BAJAJFINSV.NS", "SBILIFE.NS", "HDFCLIFE.NS", "CHOLAFIN.NS",
            "M&MFIN.NS", "PFC.NS", "RECLTD.NS", "MUTHOOTFIN.NS", "SRTRANSFIN.NS",
            "BANKBARODA.NS", "PNB.NS", "CANBK.NS", "INDUSINDBK.NS", "IDFCFIRSTB.NS"
        ],
        "IT & Tech": [
            "TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS", "LTIM.NS", 
            "TECHM.NS", "PERSISTENT.NS", "COFORGE.NS", "MPHASIS.NS", "LTTS.NS",
            "TATAELXSI.NS", "KPITTECH.NS", "CYIENT.NS", "ZENSARTECH.NS", "SONATSOFTW.NS",
            "NAUKRI.NS", "AFFLE.NS", "HAPPSTMNDS.NS", "TANLA.NS", "JUSTDIAL.NS"
        ],
        "Auto & Ancillary": [
            "MARUTI.NS", "TATAMOTORS.NS", "M&M.NS", "BAJAJ-AUTO.NS", "EICHERMOT.NS",
            "HEROMOTOCO.NS", "TVSMOTOR.NS", "ASHOKLEY.NS", "BHARATFORG.NS", "BALKRISIND.NS",
            "MRF.NS", "APOLLOTYRE.NS", "BOSCHLTD.NS", "EXIDEIND.NS", "AMARAJABAT.NS",
            "MOTHERSON.NS", "SONACOMS.NS", "UNO-MINDA.NS", "TIINDIA.NS", "TUBEINVEST.NS"
        ],
        "Pharma & Healthcare": [
            "SUNPHARMA.NS", "DIVISLAB.NS", "CIPLA.NS", "DRREDDY.NS", "APOLLOHOSP.NS",
            "TORNTPHARM.NS", "MANKIND.NS", "MAXHEALTH.NS", "LUPIN.NS", "AUROPHARMA.NS",
            "ALKEM.NS", "BIOCON.NS", "SYNGENE.NS", "LAURUSLABS.NS", "GRANULES.NS",
            "LALPATHLAB.NS", "METROPOLIS.NS", "NH.NS", "FORTIS.NS", "ASTERDM.NS"
        ],
        "FMCG & Consumption": [
            "HINDUNILVR.NS", "ITC.NS", "NESTLEIND.NS", "BRITANNIA.NS", "TITAN.NS",
            "TATACONSUM.NS", "DABUR.NS", "GODREJCP.NS", "MARICO.NS", "VARUNBEV.NS",
            "ASIANPAINT.NS", "BERGEPAINT.NS", "PIDILITIND.NS", "COLPAL.NS", "PGHH.NS",
            "TRENT.NS", "DMART.NS", "PAGEIND.NS", "BATAINDIA.NS", "RELAXO.NS"
        ],
        "Energy, Oil & Gas": [
            "RELIANCE.NS", "ONGC.NS", "NTPC.NS", "POWERGRID.NS", "BPCL.NS",
            "IOC.NS", "GAIL.NS", "COALINDIA.NS", "ADANIGREEN.NS", "ADANITRANS.NS",
            "TATAPOWER.NS", "JSWENERGY.NS", "NHPC.NS", "SJVN.NS", "TORNTPOWER.NS",
            "IGL.NS", "MGL.NS", "GUJGASLTD.NS", "PETRONET.NS", "OIL.NS"
        ],
        "Metals & Mining": [
            "TATASTEEL.NS", "JSWSTEEL.NS", "HINDALCO.NS", "VEDL.NS", "JINDALSTEL.NS",
            "SAIL.NS", "NMDC.NS", "NATIONALUM.NS", "HINDCOPPER.NS", "APLAPOLLO.NS",
            "RATNAMANI.NS", "WELCORP.NS", "JSL.NS", "MOIL.NS", "GPIL.NS"
        ],
        "Cement & Infra": [
            "LT.NS", "ULTRACEMCO.NS", "GRASIM.NS", "AMBUJACEM.NS", "SHREECEM.NS",
            "ACC.NS", "DALMIACEMT.NS", "RAMCOCEM.NS", "JKCEMENT.NS", "BIRLACORPN.NS",
            "DLF.NS", "GODREJPROP.NS", "LODHA.NS", "OBEROIRLTY.NS", "PHOENIXLTD.NS"
        ]
    }

    def __init__(self, source="yfinance", api_key=None, api_secret=None, session_token=None):
        self.source = source
        self.api_key = api_key
        self.api_secret = api_secret
        self.session_token = session_token
        self.breeze = None
        
        if source == "breeze":
            self._initialize_breeze()

    def _initialize_breeze(self):
        try:
            from breeze_connect import BreezeConnect
            if not self.api_key:
                print("⚠️ Missing Breeze credentials.")
                self.source = "yfinance"
                return
            self.breeze = BreezeConnect(api_key=self.api_key)
            self.breeze.generate_session(api_secret=self.api_secret, session_token=self.session_token)
            print("✅ Breeze API initialized")
        except Exception as e:
            print(f"❌ Failed to initialize Breeze: {e}")
            self.source = "yfinance"

    def fetch_nse500_universe(self, sector_filter="All Top Liquid") -> pd.DataFrame:
        """
        Fetch universe based on selected sector to reduce load.
        """
        selected_symbols = []
        
        # 1. Determine which stocks to fetch
        if sector_filter in self.SECTOR_STOCKS:
            # Specific sector
            selected_symbols = self.SECTOR_STOCKS[sector_filter]
        else:
            # "All Top Liquid" - combine all lists (unique values)
            all_syms = set()
            for stock_list in self.SECTOR_STOCKS.values():
                all_syms.update(stock_list)
            selected_symbols = list(all_syms)
        
        print(f"📁 Selected {sector_filter}: {len(selected_symbols)} stocks")
        
        # 2. Create DataFrame
        data = []
        for symbol in selected_symbols:
            clean_name = symbol.replace('.NS', '')
            # Try to get Sector name from our dictionary reverse lookup
            found_sector = "Unknown"
            for sec, stocks in self.SECTOR_STOCKS.items():
                if symbol in stocks:
                    found_sector = sec
                    break
            
            data.append({
                'symbol': symbol,
                'company_name': clean_name,
                'sector': found_sector,
                'market_cap': 0, # Will be filled by fundamentals check later if needed
                'current_price': 0
            })
            
        return pd.DataFrame(data)

    def fetch_historical_prices(self, symbols: List[str], period_days: int = 365) -> Dict[str, pd.DataFrame]:
        price_data = {}
        
        # --- BREEZE API PATH ---
        if self.source == "breeze" and self.breeze:
            print(f"📥 Fetching via Breeze for {len(symbols)} stocks...")
            to_date = datetime.now().isoformat()[:19] + '.000Z'
            from_date = (datetime.now() - timedelta(days=period_days)).isoformat()[:19] + '.000Z'
            
            for symbol in symbols:
                try:
                    stock_code = symbol.replace('.NS', '')
                    data = self.breeze.get_historical_data_v2(
                        interval="1day", from_date=from_date, to_date=to_date,
                        stock_code=stock_code, exchange_code="NSE", product_type="cash"
                    )
                    
                    if data.get('Status') == 200 and data.get('Success'):
                        df = pd.DataFrame(data['Success'])
                        df['datetime'] = pd.to_datetime(df['datetime'])
                        df.set_index('datetime', inplace=True)
                        
                        # Map Breeze columns to standard
                        df = df.rename(columns={'close': 'Close', 'open': 'Open', 'high': 'High', 'low': 'Low', 'volume': 'Volume'})
                        df[['Close', 'Open', 'High', 'Low', 'Volume']] = df[['Close', 'Open', 'High', 'Low', 'Volume']].apply(pd.to_numeric)
                        price_data[symbol] = df
                except Exception as e:
                    print(f"❌ Breeze error {symbol}: {e}")
                    
        # --- YFINANCE PATH (Fallback) ---
        else:
            print(f"📥 Fetching via yfinance for {len(symbols)} stocks...")
            chunk_size = 50
            for i in range(0, len(symbols), chunk_size):
                chunk = symbols[i:i+chunk_size]
                try:
                    data = yf.download(chunk, period=f"{period_days}d", group_by='ticker', progress=False, threads=True)
                    for symbol in chunk:
                        if symbol in data.columns.levels[0]:
                            df = data[symbol].copy()
                            if not df.empty:
                                price_data[symbol] = df
                    time.sleep(0.5)
                except Exception as e:
                    print(f"YF Batch error: {e}")
                    
        return price_data

    def fetch_fundamentals(self, symbols: List[str]) -> pd.DataFrame:
        fundamentals = []
        for symbol in symbols:
            fund_data = {
                'symbol': symbol, 'roe': np.nan, 'debt_equity': np.nan, 
                'operating_margin': np.nan, 'market_cap': 0, 'pe_ratio': np.nan,
                'current_price': 0
            }
            try:
                # yfinance fetch
                info = yf.Ticker(symbol).info
                if info and 'regularMarketPrice' in info:
                     fund_data.update({
                        'roe': info.get('returnOnEquity', 0) * 100,
                        'debt_equity': info.get('debtToEquity', 0) / 100,
                        'operating_margin': info.get('operatingMargins', 0) * 100,
                        'market_cap': info.get('marketCap', 0),
                        'pe_ratio': info.get('trailingPE', np.nan),
                        'current_price': info.get('currentPrice', info.get('regularMarketPrice', 0))
                    })
            except:
                pass 
            fundamentals.append(fund_data)
        return pd.DataFrame(fundamentals)

    def get_benchmark_data(self, benchmark="NIFTY50", period_days=365):
        # Always use yfinance for indices as they are complex in Breeze
        sym = '^NSEI' if benchmark == 'NIFTY50' else '^CRSLDX'
        try: return yf.Ticker(sym).history(period=f"{period_days}d")
        except: return None
        
    def get_sector_index_data(self, sector, period_days=365):
        return None # Disabled for speed
