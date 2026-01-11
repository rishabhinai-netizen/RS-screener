"""
NSE 500 Relative Strength + Quality Screener
A world-class stock screening tool combining momentum and quality factors
Author: Built with legendary investor principles in mind
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
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

# Custom CSS for premium look
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .stock-card {
        border: 2px solid #e0e0e0;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        background: white;
    }
    .buy-signal {
        background-color: #d4edda;
        border-left: 5px solid #28a745;
    }
    .watch-signal {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
    }
    .avoid-signal {
        background-color: #f8d7da;
        border-left: 5px solid #dc3545;
    }
    .stButton>button {
        width: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-weight: 600;
        padding: 0.75rem;
        border-radius: 8px;
        border: none;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'data_fetcher' not in st.session_state:
    st.session_state.data_fetcher = None
if 'screener_results' not in st.session_state:
    st.session_state.screener_results = None
if 'last_updated' not in st.session_state:
    st.session_state.last_updated = None

def initialize_components():
    """Initialize all components with API keys"""
    try:
        # Initialize with Breeze API if available, fallback to yfinance
        use_breeze = st.secrets.get("use_breeze_api", False)
        
        if use_breeze and "breeze_api_key" in st.secrets:
            data_fetcher = DataFetcher(
                source="breeze",
                api_key=st.secrets["breeze_api_key"],
                api_secret=st.secrets["breeze_api_secret"],
                session_token=st.secrets.get("breeze_session_token", "")
            )
        else:
            data_fetcher = DataFetcher(source="yfinance")
        
        # Initialize Groq AI analyzer if available
        groq_api_key = st.secrets.get("groq_api_key", None)
        ai_analyzer = AIAnalyzer(groq_api_key) if groq_api_key else None
        
        return data_fetcher, ai_analyzer
    except Exception as e:
        st.error(f"Error initializing components: {e}")
        return None, None

def render_header():
    """Render application header"""
    st.markdown('<div class="main-header">📈 NSE 500 Relative Strength + Quality Screener</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">World-Class Stock Screening Based on Legendary Investor Principles</div>', unsafe_allow_html=True)
    
    # Key metrics row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Strategy", "RS + Quality", "🏆 #1 Combo")
    with col2:
        st.metric("Universe", "NSE 500", "Top Liquid Stocks")
    with col3:
        st.metric("Rebalance", "Monthly", "Quarterly OK")
    with col4:
        if st.session_state.last_updated:
            st.metric("Last Updated", st.session_state.last_updated.strftime("%d-%b %H:%M"), "Live Data")

def render_sidebar():
    """Render sidebar with screening parameters"""
    st.sidebar.header("🎯 Screening Parameters")
    
    # Strategy selection
    st.sidebar.subheader("Strategy")
    strategy = st.sidebar.selectbox(
        "Select Strategy",
        ["RS + Quality (Recommended)", "RS + Value", "RS + Low Volatility", "Pure RS (Advanced)"],
        help="RS + Quality has highest Sharpe ratio (1.55) historically"
    )
    
    # RS Parameters
    st.sidebar.subheader("📊 Relative Strength Settings")
    
    rs_lookback = st.sidebar.selectbox(
        "RS Lookback Period",
        [252, 126, 63, 21],
        index=0,
        format_func=lambda x: f"{x} days (~{x//21} months)",
        help="252 days (12 months) is the academic standard"
    )
    
    rs_threshold = st.sidebar.slider(
        "Minimum RS Percentile",
        min_value=60,
        max_value=95,
        value=80,
        step=5,
        help="O'Neil recommends ≥80, elite stocks have ≥90"
    )
    
    # Comparison levels
    st.sidebar.subheader("🔍 RS Comparison Levels")
    compare_nifty50 = st.sidebar.checkbox("vs Nifty 50", value=True, help="Benchmark comparison")
    compare_nse500 = st.sidebar.checkbox("vs NSE 500", value=True, help="Universe comparison")
    compare_sector = st.sidebar.checkbox("vs Sector Index", value=True, help="Sector leadership")
    
    # Quality filters
    st.sidebar.subheader("💎 Quality Filters")
    
    min_roe = st.sidebar.slider("Minimum ROE (%)", 0, 50, 15, 5, help="Return on Equity ≥15% is quality")
    max_de = st.sidebar.slider("Max Debt/Equity", 0.0, 3.0, 1.0, 0.25, help="Lower is better, <1 is conservative")
    min_margin = st.sidebar.slider("Min Operating Margin (%)", 0, 50, 10, 5, help="Profitability threshold")
    
    # Additional filters
    st.sidebar.subheader("⚙️ Additional Filters")
    
    min_mcap = st.sidebar.number_input(
        "Min Market Cap (₹ Cr)",
        min_value=1000,
        max_value=100000,
        value=5000,
        step=1000,
        help="Minimum ₹5000 Cr recommended for liquidity"
    )
    
    exclude_sectors = st.sidebar.multiselect(
        "Exclude Sectors (Optional)",
        ["FINANCIAL SERVICES", "IT", "OIL & GAS", "METALS", "PHARMA", "AUTO", "FMCG"],
        help="Remove sectors you don't want to invest in"
    )
    
    # Advanced options
    with st.sidebar.expander("🔧 Advanced Options"):
        use_ai_analysis = st.checkbox("Enable AI Analysis (Groq)", value=True, help="Get AI-powered insights")
        show_technical = st.checkbox("Show Technical Charts", value=True)
        max_results = st.slider("Max Results to Show", 10, 100, 30, 10)
    
    return {
        'strategy': strategy,
        'rs_lookback': rs_lookback,
        'rs_threshold': rs_threshold,
        'compare_nifty50': compare_nifty50,
        'compare_nse500': compare_nse500,
        'compare_sector': compare_sector,
        'min_roe': min_roe,
        'max_de': max_de,
        'min_margin': min_margin,
        'min_mcap': min_mcap,
        'exclude_sectors': exclude_sectors,
        'use_ai_analysis': use_ai_analysis,
        'show_technical': show_technical,
        'max_results': max_results
    }

def run_screening(params, data_fetcher, ai_analyzer):
    """Run the screening process"""
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Step 1: Fetch NSE 500 data
        status_text.text("📥 Fetching NSE 500 stock data...")
        progress_bar.progress(10)
        
        nse500_data = data_fetcher.fetch_nse500_universe()
        
        # Step 2: Calculate price data
        status_text.text("📊 Calculating price returns and RS rankings...")
        progress_bar.progress(30)
        
        rs_calculator = RSCalculator(nse500_data, params['rs_lookback'])
        rs_results = rs_calculator.calculate_all_rs_metrics(
            compare_nifty50=params['compare_nifty50'],
            compare_nse500=params['compare_nse500'],
            compare_sector=params['compare_sector']
        )
        
        # Step 3: Fetch fundamental data
        status_text.text("💰 Fetching fundamental data...")
        progress_bar.progress(50)
        
        quality_analyzer = QualityAnalyzer(data_fetcher)
        quality_metrics = quality_analyzer.calculate_quality_scores(rs_results)
        
        # Step 4: Apply screening filters
        status_text.text("🔍 Applying quality filters...")
        progress_bar.progress(70)
        
        screener = ScreenerEngine(params)
        filtered_results = screener.apply_filters(rs_results, quality_metrics)
        
        # Step 5: Rank and score
        status_text.text("🏆 Ranking stocks...")
        progress_bar.progress(85)
        
        final_results = screener.calculate_composite_scores(filtered_results)
        
        # Step 6: AI Analysis (if enabled)
        if params['use_ai_analysis'] and ai_analyzer:
            status_text.text("🤖 Generating AI insights...")
            progress_bar.progress(95)
            
            final_results = ai_analyzer.analyze_top_stocks(final_results, top_n=min(10, params['max_results']))
        
        progress_bar.progress(100)
        status_text.text("✅ Screening complete!")
        time.sleep(0.5)
        progress_bar.empty()
        status_text.empty()
        
        return final_results
    
    except Exception as e:
        st.error(f"Error during screening: {e}")
        progress_bar.empty()
        status_text.empty()
        return None

def display_results(results, params):
    """Display screening results with rich visualizations"""
    
    if results is None or len(results) == 0:
        st.warning("No stocks matched your criteria. Try relaxing the filters.")
        return
    
    # Summary metrics
    st.markdown("---")
    st.subheader("📊 Screening Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Stocks Found", len(results), f"from NSE 500")
    with col2:
        avg_rs = results['rs_percentile'].mean()
        st.metric("Avg RS Percentile", f"{avg_rs:.1f}", f"Min: {params['rs_threshold']}")
    with col3:
        avg_quality = results['quality_score'].mean()
        st.metric("Avg Quality Score", f"{avg_quality:.1f}/100")
    with col4:
        buy_signals = len(results[results['signal'] == 'BUY'])
        st.metric("Strong BUY Signals", buy_signals, f"{buy_signals/len(results)*100:.0f}%")
    
    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 Top Picks", "📈 All Results", "📊 Analytics", "💡 AI Insights"])
    
    with tab1:
        display_top_picks(results.head(10), params)
    
    with tab2:
        display_all_results(results, params)
    
    with tab3:
        display_analytics(results)
    
    with tab4:
        if params['use_ai_analysis']:
            display_ai_insights(results)
        else:
            st.info("Enable 'AI Analysis' in sidebar to get AI-powered insights")

def display_top_picks(top_stocks, params):
    """Display top stock picks with detailed cards"""
    st.subheader("🏆 Top 10 Stock Picks")
    st.markdown("*Based on composite RS + Quality score*")
    
    for idx, stock in top_stocks.iterrows():
        signal_class = {
            'BUY': 'buy-signal',
            'WATCH': 'watch-signal',
            'AVOID': 'avoid-signal'
        }.get(stock['signal'], 'stock-card')
        
        with st.container():
            st.markdown(f'<div class="stock-card {signal_class}">', unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.markdown(f"### {stock['symbol']}")
                st.markdown(f"**{stock['company_name']}**")
                st.markdown(f"*Sector: {stock.get('sector', 'N/A')}*")
            
            with col2:
                st.markdown(f"**Composite Score:** {stock['composite_score']:.1f}/100")
                st.markdown(f"**RS Percentile:** {stock['rs_percentile']:.1f} (Rank: {stock.get('rs_rank', 'N/A')})")
                st.markdown(f"**Quality Score:** {stock['quality_score']:.1f}/100")
            
            with col3:
                signal_emoji = {"BUY": "🟢", "WATCH": "🟡", "AVOID": "🔴"}.get(stock['signal'], "⚪")
                st.markdown(f"## {signal_emoji}")
                st.markdown(f"### {stock['signal']}")
            
            # Expandable details
            with st.expander("📋 View Detailed Metrics"):
                detail_col1, detail_col2, detail_col3 = st.columns(3)
                
                with detail_col1:
                    st.markdown("**Relative Strength**")
                    st.markdown(f"- vs Nifty 50: {stock.get('rs_vs_nifty50', 'N/A'):.2f}%")
                    st.markdown(f"- vs NSE 500: {stock.get('rs_vs_nse500', 'N/A'):.2f}%")
                    st.markdown(f"- vs Sector: {stock.get('rs_vs_sector', 'N/A'):.2f}%")
                
                with detail_col2:
                    st.markdown("**Quality Metrics**")
                    st.markdown(f"- ROE: {stock.get('roe', 'N/A'):.1f}%")
                    st.markdown(f"- Debt/Equity: {stock.get('debt_equity', 'N/A'):.2f}")
                    st.markdown(f"- Op. Margin: {stock.get('operating_margin', 'N/A'):.1f}%")
                
                with detail_col3:
                    st.markdown("**Valuation**")
                    st.markdown(f"- P/E Ratio: {stock.get('pe_ratio', 'N/A'):.1f}")
                    st.markdown(f"- Market Cap: ₹{stock.get('market_cap', 0)/100:.0f} Cr")
                    st.markdown(f"- Price: ₹{stock.get('current_price', 'N/A'):.2f}")
                
                # AI Reasoning if available
                if 'ai_reasoning' in stock and stock['ai_reasoning']:
                    st.markdown("**🤖 AI Analysis:**")
                    st.info(stock['ai_reasoning'])
            
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

def display_all_results(results, params):
    """Display all results in interactive table"""
    st.subheader(f"📋 All {len(results)} Stocks")
    
    # Create display dataframe
    display_df = results[[
        'symbol', 'company_name', 'sector', 'composite_score', 
        'rs_percentile', 'quality_score', 'signal',
        'rs_vs_nifty50', 'rs_vs_sector',
        'roe', 'debt_equity', 'operating_margin',
        'market_cap', 'current_price'
    ]].copy()
    
    # Format columns
    display_df['market_cap'] = display_df['market_cap'].apply(lambda x: f"₹{x/100:.0f} Cr")
    display_df['current_price'] = display_df['current_price'].apply(lambda x: f"₹{x:.2f}")
    
    # Color-code signals
    def highlight_signal(row):
        color_map = {
            'BUY': 'background-color: #d4edda',
            'WATCH': 'background-color: #fff3cd',
            'AVOID': 'background-color: #f8d7da'
        }
        return [color_map.get(row['signal'], '')] * len(row)
    
    styled_df = display_df.style.apply(highlight_signal, axis=1)
    st.dataframe(styled_df, use_container_width=True, height=600)
    
    # Download button
    csv = display_df.to_csv(index=False)
    st.download_button(
        label="📥 Download Results as CSV",
        data=csv,
        file_name=f"rs_quality_screener_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

def display_analytics(results):
    """Display analytics and visualizations"""
    st.subheader("📊 Portfolio Analytics")
    
    # Sector distribution
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Sector Distribution")
        sector_counts = results['sector'].value_counts().head(10)
        fig = px.pie(values=sector_counts.values, names=sector_counts.index, 
                     title="Top 10 Sectors by Stock Count")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### Signal Distribution")
        signal_counts = results['signal'].value_counts()
        fig = px.bar(x=signal_counts.index, y=signal_counts.values,
                     title="Distribution of Signals",
                     labels={'x': 'Signal', 'y': 'Count'},
                     color=signal_counts.index,
                     color_discrete_map={'BUY': 'green', 'WATCH': 'orange', 'AVOID': 'red'})
        st.plotly_chart(fig, use_container_width=True)
    
    # Scatter plot: RS vs Quality
    st.markdown("#### RS Percentile vs Quality Score")
    fig = px.scatter(results, x='rs_percentile', y='quality_score',
                     color='signal', size='market_cap',
                     hover_data=['symbol', 'company_name', 'sector'],
                     title="Relative Strength vs Quality",
                     color_discrete_map={'BUY': 'green', 'WATCH': 'orange', 'AVOID': 'red'})
    st.plotly_chart(fig, use_container_width=True)
    
    # Histogram: Composite scores
    st.markdown("#### Composite Score Distribution")
    fig = px.histogram(results, x='composite_score', nbins=20,
                       title="Distribution of Composite Scores",
                       labels={'composite_score': 'Composite Score', 'count': 'Frequency'})
    st.plotly_chart(fig, use_container_width=True)

def display_ai_insights(results):
    """Display AI-generated insights"""
    st.subheader("💡 AI-Powered Insights")
    
    top_stocks_with_ai = results[results['ai_reasoning'].notna()].head(10)
    
    if len(top_stocks_with_ai) == 0:
        st.info("No AI insights available. Run screening with AI analysis enabled.")
        return
    
    for idx, stock in top_stocks_with_ai.iterrows():
        with st.expander(f"🤖 {stock['symbol']} - {stock['company_name']}"):
            st.markdown(f"**Signal:** {stock['signal']}")
            st.markdown(f"**Composite Score:** {stock['composite_score']:.1f}/100")
            st.markdown("---")
            st.markdown("**AI Analysis:**")
            st.write(stock['ai_reasoning'])

def main():
    """Main application"""
    
    # Render header
    render_header()
    
    # Render sidebar and get parameters
    params = render_sidebar()
    
    # Initialize components
    if st.session_state.data_fetcher is None:
        with st.spinner("Initializing components..."):
            data_fetcher, ai_analyzer = initialize_components()
            st.session_state.data_fetcher = data_fetcher
            st.session_state.ai_analyzer = ai_analyzer
    else:
        data_fetcher = st.session_state.data_fetcher
        ai_analyzer = st.session_state.ai_analyzer
    
    # Main action button
    st.markdown("---")
    if st.button("🚀 RUN SCREENING", use_container_width=True):
        if data_fetcher is None:
            st.error("Failed to initialize data fetcher. Please check API credentials in Streamlit secrets.")
            return
        
        results = run_screening(params, data_fetcher, ai_analyzer)
        
        if results is not None:
            st.session_state.screener_results = results
            st.session_state.last_updated = datetime.now()
            st.success(f"✅ Found {len(results)} stocks matching your criteria!")
    
    # Display results if available
    if st.session_state.screener_results is not None:
        display_results(st.session_state.screener_results, params)
    else:
        # Show welcome message
        st.markdown("---")
        st.info("""
        ### 👋 Welcome to RS + Quality Screener!
        
        **This tool combines:**
        - 📈 **Relative Strength** - William O'Neil's momentum approach
        - 💎 **Quality Factors** - ROE, Debt/Equity, Margins
        - 🤖 **AI Analysis** - Powered by Groq for intelligent insights
        
        **How to use:**
        1. Adjust parameters in the sidebar
        2. Click "RUN SCREENING" button above
        3. Review top picks and detailed analysis
        4. Download results for your records
        
        **Expected Results:**
        - 15-20% CAGR with proper execution
        - Monthly rebalancing recommended
        - Combine with your own research
        
        ⚠️ **Disclaimer:** This is for educational purposes. Not investment advice.
        """)

if __name__ == "__main__":
    main()
