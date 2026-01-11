"""
NSE 500 Relative Strength + Quality Screener
A world-class stock screening tool combining momentum and quality factors
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
import time

# Import custom modules
from data_fetcher import DataFetcher
from rs_calculator import RSCalculator
from quality_analyzer import QualityAnalyzer
from ai_analyzer import AIAnalyzer
from screener_engine import ScreenerEngine

# Page configuration
st.set_page_config(
    page_title="RS + Quality Screener | NSE 500",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header { font-size: 2.5rem; font-weight: 700; color: #1f77b4; text-align: center; margin-bottom: 1rem; }
    .sub-header { font-size: 1.2rem; color: #666; text-align: center; margin-bottom: 2rem; }
    .stock-card { border: 2px solid #e0e0e0; border-radius: 10px; padding: 1rem; margin: 0.5rem 0; background: white; }
    .buy-signal { background-color: #d4edda; border-left: 5px solid #28a745; }
    .watch-signal { background-color: #fff3cd; border-left: 5px solid #ffc107; }
    .avoid-signal { background-color: #f8d7da; border-left: 5px solid #dc3545; }
    .stButton>button { width: 100%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; font-weight: 600; padding: 0.75rem; border: none; }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'data_fetcher' not in st.session_state:
    st.session_state.data_fetcher = None
if 'screener_results' not in st.session_state:
    st.session_state.screener_results = None

def initialize_components():
    """Initialize all components with API keys"""
    try:
        use_breeze = st.secrets.get("use_breeze_api", False)
        
        # Initialize Data Fetcher
        if use_breeze and "breeze_api_key" in st.secrets:
            data_fetcher = DataFetcher(
                source="breeze",
                api_key=st.secrets["breeze_api_key"],
                api_secret=st.secrets["breeze_api_secret"],
                session_token=st.secrets.get("breeze_session_token", "")
            )
        else:
            data_fetcher = DataFetcher(source="yfinance")
        
        # Initialize Groq
        groq_api_key = st.secrets.get("groq_api_key", None)
        ai_analyzer = AIAnalyzer(groq_api_key) if groq_api_key else None
        
        return data_fetcher, ai_analyzer
    except Exception as e:
        st.error(f"Error initializing components: {e}")
        return None, None

def render_sidebar():
    """Render sidebar with screening parameters"""
    st.sidebar.header("🎯 Screening Parameters")
    
    # 1. Sector Selection (CRITICAL FOR PERFORMANCE)
    st.sidebar.subheader("📂 Universe Selection")
    
    # Get available sectors from DataFetcher class directly or hardcoded list for UI
    available_sectors = ["All Top Liquid", "Banking & Finance", "IT & Tech", "Auto & Ancillary", 
                        "Pharma & Healthcare", "FMCG & Consumption", "Energy, Oil & Gas", 
                        "Metals & Mining", "Cement & Infra"]
    
    selected_sector = st.sidebar.selectbox(
        "Select Sector to Screen",
        available_sectors,
        help="Screening by sector is faster and more reliable than 'All'"
    )

    # Strategy selection
    st.sidebar.subheader("Strategy")
    strategy = st.sidebar.selectbox(
        "Select Strategy",
        ["RS + Quality (Recommended)", "RS + Value", "RS + Low Volatility", "Pure RS (Advanced)"]
    )
    
    # RS Parameters
    st.sidebar.subheader("📊 Relative Strength Settings")
    rs_lookback = st.sidebar.selectbox("RS Lookback Period", [252, 126, 63], index=0)
    rs_threshold = st.sidebar.slider("Minimum RS Percentile", 60, 95, 80, 5)
    
    # Quality filters
    st.sidebar.subheader("💎 Quality Filters")
    min_roe = st.sidebar.slider("Minimum ROE (%)", 0, 50, 15, 5)
    max_de = st.sidebar.slider("Max Debt/Equity", 0.0, 3.0, 1.0, 0.25)
    
    # Advanced options
    with st.sidebar.expander("🔧 Advanced Options"):
        use_ai_analysis = st.checkbox("Enable AI Analysis (Groq)", value=True)
        max_results = st.slider("Max Results to Show", 10, 100, 30, 10)
    
    return {
        'selected_sector': selected_sector,
        'strategy': strategy,
        'rs_lookback': rs_lookback,
        'rs_threshold': rs_threshold,
        'min_roe': min_roe,
        'max_de': max_de,
        'use_ai_analysis': use_ai_analysis,
        'max_results': max_results,
        'min_margin': 10,       # Defaults
        'min_mcap': 5000,       # Defaults
        'exclude_sectors': [],  # Defaults
        'compare_nifty50': True,
        'compare_nse500': True,
        'compare_sector': True
    }

def run_screening(params, data_fetcher, ai_analyzer):
    """Run the screening process"""
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Step 1: Fetch Universe based on Sector Selection
        status_text.text(f"📥 Fetching universe for: {params['selected_sector']}...")
        progress_bar.progress(10)
        
        # This now passes the sector to data_fetcher to filter UPFRONT
        universe_data = data_fetcher.fetch_nse500_universe(sector_filter=params['selected_sector'])
        
        if universe_data.empty:
            st.error("No stocks found for this selection.")
            return None

        st.info(f"Screening {len(universe_data)} stocks in {params['selected_sector']}")
        
        # Step 2: Calculate price data
        status_text.text("📊 Fetching history & calculating RS...")
        progress_bar.progress(30)
        
        rs_calculator = RSCalculator(universe_data, params['rs_lookback'])
        rs_results = rs_calculator.calculate_all_rs_metrics(
            compare_nifty50=True,
            compare_nse500=False, # Disable to save time if needed
            compare_sector=False
        )
        
        # Step 3: Fetch fundamental data
        status_text.text("💰 Fetching fundamental data...")
        progress_bar.progress(60)
        
        quality_analyzer = QualityAnalyzer(data_fetcher)
        quality_metrics = quality_analyzer.calculate_quality_scores(rs_results)
        
        # Step 4: Apply filters
        status_text.text("🔍 Applying filters...")
        progress_bar.progress(80)
        
        screener = ScreenerEngine(params)
        filtered_results = screener.apply_filters(rs_results, quality_metrics)
        
        # Step 5: Rank
        final_results = screener.calculate_composite_scores(filtered_results)
        
        # Step 6: AI Analysis
        if params['use_ai_analysis'] and ai_analyzer:
            status_text.text("🤖 Generating AI insights...")
            progress_bar.progress(90)
            final_results = ai_analyzer.analyze_top_stocks(final_results, top_n=5)
        
        progress_bar.progress(100)
        status_text.empty()
        
        return final_results
    
    except Exception as e:
        st.error(f"Error during screening: {e}")
        return None

def main():
    st.markdown('<div class="main-header">📈 NSE 500 RS + Quality Screener</div>', unsafe_allow_html=True)
    
    params = render_sidebar()
    
    # Initialize components
    if st.session_state.data_fetcher is None:
        with st.spinner("Initializing API connections..."):
            data_fetcher, ai_analyzer = initialize_components()
            st.session_state.data_fetcher = data_fetcher
            st.session_state.ai_analyzer = ai_analyzer
    else:
        data_fetcher = st.session_state.data_fetcher
        ai_analyzer = st.session_state.ai_analyzer
    
    if st.button("🚀 RUN SCREENING", use_container_width=True):
        results = run_screening(params, data_fetcher, ai_analyzer)
        if results is not None:
            st.session_state.screener_results = results
            st.success(f"✅ Found {len(results)} stocks!")

    # Display results
    if st.session_state.screener_results is not None:
        results = st.session_state.screener_results
        
        # Tabs
        tab1, tab2 = st.tabs(["🎯 Top Picks", "📋 Data Table"])
        
        with tab1:
            st.subheader("Top Picks")
            for idx, stock in results.head(10).iterrows():
                signal_emoji = {"BUY": "🟢", "WATCH": "🟡", "AVOID": "🔴"}.get(stock['signal'], "⚪")
                
                with st.expander(f"{signal_emoji} {stock['symbol']} (Score: {stock['composite_score']:.1f})"):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("RS Percentile", f"{stock['rs_percentile']:.1f}")
                    c2.metric("Quality Score", f"{stock['quality_score']:.1f}")
                    c3.metric("Price", f"₹{stock['current_price']:.2f}")
                    
                    if 'ai_reasoning' in stock and stock['ai_reasoning']:
                        st.info(f"🤖 **AI Analysis:**\n\n{stock['ai_reasoning']}")

        with tab2:
            st.dataframe(results)

if __name__ == "__main__":
    main()
