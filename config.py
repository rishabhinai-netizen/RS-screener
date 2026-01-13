"""
Configuration Module
Contains all constants, stock universe, and configuration settings
"""

# =============================================================================
# STOCK UNIVERSE - 100 CURATED LIQUID STOCKS
# =============================================================================

SECTOR_STOCKS = {
    "Banking & Finance": {
        "stocks": [
            "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "AXISBANK.NS", "KOTAKBANK.NS",
            "BAJFINANCE.NS", "BAJAJFINSV.NS", "SBILIFE.NS", "HDFCLIFE.NS",
            "INDUSINDBK.NS", "BANDHANBNK.NS", "ICICIGI.NS"
        ],
        "description": "Banks, NBFCs, Insurance"
    },
    "IT & Technology": {
        "stocks": [
            "TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS", "TECHM.NS",
            "LTIM.NS", "PERSISTENT.NS", "COFORGE.NS", "LTTS.NS", "TATAELXSI.NS",
            "MPHASIS.NS", "OFSS.NS"
        ],
        "description": "IT Services, Software"
    },
    "Auto & Ancillaries": {
        "stocks": [
            "MARUTI.NS", "TATAMOTORS.NS", "M&M.NS", "BAJAJ-AUTO.NS", "EICHERMOT.NS",
            "HEROMOTOCO.NS", "TVSMOTOR.NS", "BOSCHLTD.NS", "MOTHERSON.NS", "BALKRISIND.NS"
        ],
        "description": "Auto OEMs, Components, Tyres"
    },
    "Pharma & Healthcare": {
        "stocks": [
            "SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS", "APOLLOHOSP.NS",
            "TORNTPHARM.NS", "LUPIN.NS", "BIOCON.NS", "ALKEM.NS", "LALPATHLAB.NS"
        ],
        "description": "Pharma, Hospitals, Diagnostics"
    },
    "FMCG & Consumer": {
        "stocks": [
            "HINDUNILVR.NS", "ITC.NS", "NESTLEIND.NS", "BRITANNIA.NS", "DABUR.NS",
            "MARICO.NS", "GODREJCP.NS", "TATACONSUM.NS", "ASIANPAINT.NS",
            "PIDILITIND.NS", "TITAN.NS", "TRENT.NS"
        ],
        "description": "FMCG, Paints, Retail, Jewelry"
    },
    "Energy & Utilities": {
        "stocks": [
            "RELIANCE.NS", "ONGC.NS", "BPCL.NS", "IOC.NS", "GAIL.NS",
            "NTPC.NS", "POWERGRID.NS", "ADANIGREEN.NS", "ADANITRANS.NS", "COALINDIA.NS"
        ],
        "description": "Oil & Gas, Power, Utilities"
    },
    "Metals & Mining": {
        "stocks": [
            "TATASTEEL.NS", "JSWSTEEL.NS", "HINDALCO.NS", "VEDL.NS",
            "JINDALSTEL.NS", "SAIL.NS", "NMDC.NS", "HINDZINC.NS"
        ],
        "description": "Steel, Aluminum, Mining"
    },
    "Cement & Infra": {
        "stocks": [
            "LT.NS", "ULTRACEMCO.NS", "GRASIM.NS", "AMBUJACEM.NS", "SHREECEM.NS",
            "ACC.NS", "DLF.NS", "GODREJPROP.NS", "LODHA.NS", "OBEROIRLTY.NS"
        ],
        "description": "Cement, Real Estate, Engineering"
    },
    "Telecom & Media": {
        "stocks": [
            "BHARTIARTL.NS", "ZOMATO.NS", "NYKAA.NS", "ZEEL.NS", "PVRINOX.NS", "DMART.NS"
        ],
        "description": "Telecom, New-Age Tech, Entertainment"
    },
    "Diversified": {
        "stocks": [
            "ADANIENT.NS", "SIEMENS.NS", "ABB.NS", "HAVELLS.NS",
            "CROMPTON.NS", "VOLTAS.NS", "BLUESTAR.NS", "CUMMINSIND.NS", "THERMAX.NS", "BERGEPAINT.NS"
        ],
        "description": "Conglomerates, Capital Goods, Electricals"
    }
}

# =============================================================================
# QUALITY METRIC THRESHOLDS
# =============================================================================

QUALITY_THRESHOLDS = {
    "roe": {
        "excellent": 20,  # ≥20% = 100 points
        "good": 15,       # ≥15% = 75 points
        "acceptable": 10,  # ≥10% = 50 points
        "poor": 5         # ≥5% = 25 points
    },
    "debt_equity": {
        "excellent": 0.3,  # ≤0.3 = 100 points (lower is better)
        "good": 0.5,
        "acceptable": 1.0,
        "poor": 2.0
    },
    "operating_margin": {
        "excellent": 20,
        "good": 15,
        "acceptable": 10,
        "poor": 5
    },
    "current_ratio": {
        "excellent": 2.0,
        "good": 1.5,
        "acceptable": 1.0,
        "poor": 0.8
    },
    "profit_margin": {
        "excellent": 10,
        "good": 7,
        "acceptable": 5,
        "poor": 2
    },
    "roa": {
        "excellent": 10,
        "good": 7,
        "acceptable": 5,
        "poor": 3
    }
}

# Weights for composite quality score
QUALITY_WEIGHTS = {
    "roe": 0.25,
    "debt_equity": 0.20,
    "operating_margin": 0.20,
    "current_ratio": 0.15,
    "profit_margin": 0.10,
    "roa": 0.10
}

# =============================================================================
# RS CALCULATION SETTINGS
# =============================================================================

RS_CONFIG = {
    "lookback_period": 252,  # 12 months
    "skip_recent_days": 21,  # Exclude last month (O'Neil methodology)
    "mansfield_ma_period": 252,  # 52-week MA for Mansfield RS
    "trend_strength_period": 126,  # 6 months for trend calculation
    "volatility_period": 60  # 3 months for volatility
}

# =============================================================================
# STRATEGY CONFIGURATIONS
# =============================================================================

STRATEGIES = {
    "RS + Quality": {
        "rs_weight": 0.60,
        "quality_weight": 0.40,
        "description": "Optimal risk-adjusted returns (Sharpe 1.55)",
        "ideal_for": "Most investors"
    },
    "RS + Value": {
        "rs_weight": 0.50,
        "value_weight": 0.30,
        "quality_weight": 0.20,
        "description": "Momentum + Valuation focus",
        "ideal_for": "Value-oriented investors"
    },
    "RS + Low Volatility": {
        "rs_weight": 0.50,
        "low_vol_weight": 0.50,
        "description": "Smooth, steady returns",
        "ideal_for": "Conservative investors"
    },
    "Pure RS": {
        "rs_weight": 1.00,
        "description": "Maximum returns, maximum risk",
        "ideal_for": "Experienced traders only"
    }
}

# =============================================================================
# SIGNAL GENERATION THRESHOLDS
# =============================================================================

SIGNAL_THRESHOLDS = {
    "BUY": {
        "composite_min": 75,
        "rs_min": 85,
        "quality_min": 60
    },
    "STRONG_WATCH": {
        "composite_min": 70,
        "rs_min": 80,
        "quality_min": 50
    },
    "WATCH": {
        "composite_min": 60,
        "rs_min": 70,
        "quality_min": 40
    }
}

# =============================================================================
# DATA FETCHING SETTINGS
# =============================================================================

DATA_CONFIG = {
    "breeze_timeout": 30,
    "yfinance_timeout": 30,
    "yfinance_chunk_size": 25,  # Reduced from 50 for reliability
    "yfinance_delay": 3,  # Seconds between chunks
    "max_retries": 3,
    "cache_ttl_prices": 3600,  # 1 hour for price data
    "cache_ttl_fundamentals": 86400,  # 24 hours for fundamentals
    "min_data_completeness": 0.90  # 90% of data must be available
}

# =============================================================================
# BENCHMARK INDICES
# =============================================================================

BENCHMARKS = {
    "NIFTY50": "^NSEI",
    "NIFTY500": "^CRSLDX",
    "NIFTYMIDCAP": "^CNXMID",
    "NIFTYBANK": "^NSEBANK"
}

# =============================================================================
# UI CONFIGURATION
# =============================================================================

UI_CONFIG = {
    "default_sector": "All Sectors",
    "default_strategy": "RS + Quality",
    "default_rs_threshold": 80,
    "default_min_roe": 15,
    "default_max_de": 1.0,
    "default_min_margin": 10,
    "max_results_display": 50,
    "top_picks_count": 10,
    "enable_ai_default": True
}

# =============================================================================
# VALIDATION RULES
# =============================================================================

VALIDATION_RULES = {
    "min_market_cap": 5000,  # ₹5,000 Crores
    "min_avg_volume": 50,  # ₹50 Crores daily
    "min_price_history_days": 252,
    "max_missing_data_pct": 10,  # Max 10% missing data allowed
    "exclude_suspended": True,
    "exclude_delisted": True
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_all_stocks():
    """Get list of all stocks across all sectors"""
    all_stocks = []
    for sector_data in SECTOR_STOCKS.values():
        all_stocks.extend(sector_data["stocks"])
    return list(set(all_stocks))  # Remove duplicates

def get_stocks_by_sector(sector_name):
    """Get stocks for a specific sector"""
    if sector_name == "All Sectors":
        return get_all_stocks()
    return SECTOR_STOCKS.get(sector_name, {}).get("stocks", [])

def get_sector_list():
    """Get list of all sector names"""
    return ["All Sectors"] + list(SECTOR_STOCKS.keys())

def get_total_stock_count():
    """Get total number of unique stocks"""
    return len(get_all_stocks())

# =============================================================================
# CONSTANTS
# =============================================================================

TRADING_DAYS_PER_YEAR = 252
TRADING_DAYS_PER_MONTH = 21
TRADING_DAYS_PER_WEEK = 5

# Colors for UI
SIGNAL_COLORS = {
    "BUY": "#28a745",
    "STRONG_WATCH": "#ffc107",
    "WATCH": "#17a2b8",
    "AVOID": "#dc3545"
}

SIGNAL_EMOJIS = {
    "BUY": "🟢",
    "STRONG_WATCH": "🟡",
    "WATCH": "🔵",
    "AVOID": "🔴"
}

# Version
VERSION = "2.0.0"
LAST_UPDATED = "2026-01-13"

print(f"✅ Config loaded: {get_total_stock_count()} stocks across {len(SECTOR_STOCKS)} sectors")
