"""RS + Quality Screener - Production Version 2.0"""
import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
from config import *
from data_fetcher import DataFetcher
from rs_calculator import RSCalculator
from quality_analyzer import QualityAnalyzer
from screener_engine import ScreenerEngine
from ai_analyzer import AIAnalyzer
from cache_manager import get_cache

st.set_page_config(page_title="RS + Quality Screener", page_icon="📈", layout="wide")

st.markdown("""
<style>
.main-header {font-size: 2.5rem; font-weight: 700; color: #1f77b4; text-align: center;}
.stock-card {border: 2px solid #e0e0e0; border-radius: 10px; padding: 1rem; margin: 0.5rem 0;}
.buy-signal {background-color: #d4edda; border-left: 5px solid #28a745;}
.watch-signal {background-color: #fff3cd; border-left: 5px solid #ffc107;}
</style>
""", unsafe_allow_html=True)

if 'results' not in st.session_state:
    st.session_state.results = None
if 'data_fetcher' not in st.session_state:
    st.session_state.data_fetcher = None

def init_components():
    try:
        use_breeze = st.secrets.get("use_breeze_api", False)
        if use_breeze:
            df = DataFetcher(use_breeze=True, api_key=st.secrets.get("breeze_api_key"), 
                           api_secret=st.secrets.get("breeze_api_secret"),
                           session_token=st.secrets.get("breeze_session_token"))
        else:
            df = DataFetcher(use_breeze=False)
        ai = AIAnalyzer(st.secrets.get("groq_api_key"))
        return df, ai
    except Exception as e:
        st.error(f"Init error: {e}")
        return DataFetcher(use_breeze=False), AIAnalyzer()

def render_sidebar():
    st.sidebar.header("🎯 Parameters")
    sector = st.sidebar.selectbox("Sector", get_sector_list())
    strategy = st.sidebar.selectbox("Strategy", list(STRATEGIES.keys()), index=0)
    st.sidebar.subheader("📊 RS Settings")
    rs_thresh = st.sidebar.slider("Min RS Percentile", 60, 95, 80, 5)
    st.sidebar.subheader("💎 Quality Filters")
    min_roe = st.sidebar.slider("Min ROE %", 0, 50, 15, 5)
    max_de = st.sidebar.slider("Max D/E", 0.0, 3.0, 1.0, 0.25)
    with st.sidebar.expander("Advanced"):
        use_ai = st.checkbox("Enable AI Analysis", value=True)
        max_results = st.slider("Max Results", 10, 100, 30, 10)
    return {'sector': sector, 'strategy': strategy, 'rs_threshold': rs_thresh, 
            'min_roe': min_roe, 'max_de': max_de, 'min_margin': 10, 'min_mcap': 5000,
            'use_ai': use_ai, 'max_results': max_results}

def run_screening(params, df, ai):
    with st.spinner("📥 Fetching universe..."):
        universe = df.fetch_universe(params['sector'])
    if universe.empty:
        st.error("No stocks found")
        return None
    st.info(f"Screening {len(universe)} stocks")
    
    with st.spinner("📊 Fetching price data..."):
        prices = df.fetch_historical_prices(universe['symbol'].tolist(), 365)
    
    with st.spinner("💰 Fetching fundamentals..."):
        fundamentals = df.fetch_fundamentals(list(prices.keys()))
    
    with st.spinner("🔍 Calculating RS..."):
        rs_calc = RSCalculator(prices)
        benchmark = df.get_benchmark_data("NIFTY50", 365)
        rs_results = rs_calc.calculate_rs_metrics(benchmark)
    
    with st.spinner("💎 Calculating Quality..."):
        combined = rs_results.merge(fundamentals, on='symbol', how='inner')
        combined = combined.merge(universe[['symbol', 'company_name', 'sector']], on='symbol', how='left')
        qa = QualityAnalyzer(combined)
        with_quality = qa.calculate_quality_scores()
    
    with st.spinner("✨ Applying filters..."):
        screener = ScreenerEngine(params)
        filtered = screener.apply_filters(with_quality)
        final = screener.calculate_composite_scores(filtered)
    
    if params['use_ai'] and ai and ai.api_key:
        with st.spinner("🤖 Generating AI insights..."):
            final = ai.analyze_top_stocks(final, top_n=5)
    
    st.success(f"✅ Found {len(final)} stocks!")
    return final

def main():
    st.markdown('<div class="main-header">📈 RS + Quality Screener v2.0</div>', unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center'>✨ {get_total_stock_count()} Liquid Stocks | 🎯 6 Quality Metrics | 🚀 Breeze API Ready</p>", unsafe_allow_html=True)
    
    params = render_sidebar()
    
    if st.session_state.data_fetcher is None:
        with st.spinner("Initializing..."):
            df, ai = init_components()
            st.session_state.data_fetcher = df
            st.session_state.ai_analyzer = ai
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 RUN SCREENING", use_container_width=True, type="primary"):
            results = run_screening(params, st.session_state.data_fetcher, st.session_state.ai_analyzer)
            if results is not None:
                st.session_state.results = results
    
    if st.session_state.results is not None:
        results = st.session_state.results.head(params['max_results'])
        
        tab1, tab2, tab3 = st.tabs(["🎯 Top Picks", "📋 All Data", "📊 Charts"])
        
        with tab1:
            for _, stock in results.head(10).iterrows():
                emoji = SIGNAL_EMOJIS.get(stock['signal'], '⚪')
                with st.expander(f"{emoji} {stock['symbol']} - {stock.get('company_name', 'N/A')} (Score: {stock['composite_score']:.1f})"):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("RS Percentile", f"{stock['rs_percentile']:.1f}")
                    c2.metric("Quality", f"{stock['quality_score']:.1f}")
                    c3.metric("Price", f"₹{stock['current_price']:.2f}")
                    c4.metric("12M Return", f"{stock.get('return_12m', 0):.1f}%")
                    
                    st.markdown(f"**Sector:** {stock.get('sector', 'N/A')} | **Signal:** {stock['signal']}")
                    st.markdown(f"**ROE:** {stock.get('roe', 0):.1f}% | **D/E:** {stock.get('debt_equity', 0):.2f} | **Op Margin:** {stock.get('operating_margin', 0):.1f}%")
                    
                    if 'ai_analysis' in stock and stock['ai_analysis']:
                        st.info(f"🤖 **AI Analysis:**\n\n{stock['ai_analysis']}")
        
        with tab2:
            st.dataframe(results, use_container_width=True)
            csv = results.to_csv(index=False)
            st.download_button("📥 Download CSV", csv, "screening_results.csv", "text/csv")
        
        with tab3:
            fig1 = px.scatter(results, x='rs_percentile', y='quality_score', color='signal', hover_data=['symbol'], title="RS vs Quality")
            st.plotly_chart(fig1, use_container_width=True)
            
            fig2 = px.bar(results.head(20), x='symbol', y='composite_score', color='signal', title="Top 20 Composite Scores")
            st.plotly_chart(fig2, use_container_width=True)
    
    with st.sidebar:
        st.markdown("---")
        cache = get_cache()
        stats = cache.get_cache_stats()
        st.caption(f"📊 Cache: {stats['memory_entries']} entries | {stats['total_size_mb']:.1f} MB")
        if st.button("🗑️ Clear Cache"):
            cache.clear_all()
            st.success("Cache cleared!")

if __name__ == "__main__":
    main()
