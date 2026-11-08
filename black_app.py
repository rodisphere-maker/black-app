import streamlit as st
import yfinance as yf
import pandas_datareader.data as web
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time
from datetime import datetime, timedelta

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Vantage | Quant", page_icon="📈", layout="centered")

# --- CUSTOM VANTAGE CSS ---
st.markdown("""
<style>
    /* Base Theme */
    .stApp { background-color: #0B0C10; color: #FFFFFF; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
    
    /* Hide Streamlit headers */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] { gap: 20px; background-color: transparent; border-bottom: 1px solid #2D2F3A; }
    .stTabs [data-baseweb="tab"] { color: #8A8F98; font-weight: 600; background-color: transparent; padding: 10px 0px; }
    .stTabs [aria-selected="true"] { color: #FFFFFF !important; border-bottom: 2px solid #FFFFFF !important; }
    
    /* Market Card Styling */
    .market-card {
        background-color: #121319;
        border: 1px solid #232530;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 8px;
        display: flex;
        flex-direction: column;
        gap: 8px;
    }
    .market-pct { font-size: 24px; font-weight: 800; color: #FFFFFF; }
    .market-question { font-size: 15px; font-weight: 500; color: #D1D5DB; line-height: 1.3; padding-right: 15px; }
    .market-meta { font-size: 12px; color: #6B7280; margin-bottom: 8px;}
    
    /* Yes/No Pills */
    .trade-row { display: flex; gap: 8px; }
    .pill-yes { 
        background-color: #1A2E22; color: #34D399; border: 1px solid #34D399; 
        border-radius: 20px; padding: 6px 12px; font-size: 13px; font-weight: bold; text-align: center; flex: 1;
    }
    .pill-no { 
        background-color: #2E1A1A; color: #F87171; border: 1px solid #F87171; 
        border-radius: 20px; padding: 6px 12px; font-size: 13px; font-weight: bold; text-align: center; flex: 1;
    }
    
    /* Detail View Styling */
    .detail-title { font-size: 22px; font-weight: 700; line-height: 1.3; margin-bottom: 20px; }
    .price-display { font-size: 28px; font-weight: 800; }
    .price-yes { color: #34D399; }
    .price-no { color: #F87171; }
    
    /* Stat Boxes */
    .stat-box { background-color: #121319; border-radius: 8px; padding: 12px; text-align: center; border: 1px solid #232530;}
    .stat-label { font-size: 10px; color: #6B7280; text-transform: uppercase; }
    .stat-val { font-size: 14px; font-weight: 600; color: #FFFFFF; margin-top: 4px;}
    
    /* Trade Plan Box */
    .trade-plan { background-color: #121319; border: 1px solid #232530; border-radius: 12px; padding: 20px; margin-top: 10px; margin-bottom: 20px; }
    .trade-plan-title { font-size: 16px; font-weight: bold; color: #FFFFFF; margin-bottom: 12px; border-bottom: 1px solid #2D2F3A; padding-bottom: 8px;}
    .plan-row { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px; }
    .plan-label { color: #8A8F98; }
    .plan-val { color: #FFFFFF; font-weight: bold; font-family: monospace;}
    
    /* Buttons */
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; padding: 12px 0; transition: all 0.2s; border: none;}
    .btn-back > button { background-color: transparent !important; color: #8A8F98 !important; text-align: left; padding: 0 0 10px 0; }
    
    /* View Analysis Button on Feed */
    div.stButton > button {
        background-color: transparent;
        color: #8A8F98;
        border: 1px solid #2D2F3A;
        border-radius: 8px;
        margin-top: -5px;
        margin-bottom: 15px;
        font-size: 13px;
    }
    div.stButton > button:hover { border-color: #FFFFFF; color: #FFFFFF; }
    
    /* Bottom Nav */
    .bottom-nav {
        position: fixed; bottom: 0; left: 0; right: 0;
        background-color: #0B0C10; border-top: 1px solid #2D2F3A;
        display: flex; justify-content: space-around; padding: 12px 0 20px 0;
        z-index: 1000;
    }
    .nav-item { color: #6B7280; font-size: 10px; text-align: center; display: flex; flex-direction: column; align-items: center; gap: 4px;}
    .nav-item.active { color: #FFFFFF; }
    .nav-icon { font-size: 18px; }
    
    /* Spacing for bottom nav */
    .main-container { padding-bottom: 80px; }
</style>
""", unsafe_allow_html=True)

# --- TICKERS TO TRACK ---
MARKETS = [
    {"id": "NVDA", "name": "NVIDIA Corp", "cat": "Tech·closes tomorrow", "tag": "Tech"},
    {"id": "BTC-USD", "name": "Bitcoin", "cat": "Crypto·closes tomorrow", "tag": "Crypto"},
    {"id": "SPY", "name": "S&P 500 ETF", "cat": "Finance·closes tomorrow", "tag": "Finance"},
    {"id": "AAPL", "name": "Apple Inc", "cat": "Tech·closes tomorrow", "tag": "Tech"}
]

# --- STATE MANAGEMENT ---
if 'view' not in st.session_state:
    st.session_state.view = 'feed'
if 'active_ticker' not in st.session_state:
    st.session_state.active_ticker = None

# --- TRIPLE FALLBACK DATA FETCHING ---
@st.cache_data(ttl=3600)
def get_market_data(ticker):
    df = None
    # 1. Yahoo
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        if len(df) < 50: df = None
        if df is not None and isinstance(df.columns, pd.MultiIndex): 
            df.columns = df.columns.get_level_values(0)
    except Exception: pass

    # 2. Stooq
    if df is None and "-USD" not in ticker:
        try:
            end = datetime.now()
            start = end - timedelta(days=365)
            df = web.DataReader(f"{ticker}.us", 'stooq', start, end)
            df = df.sort_index()
            if len(df) < 50: df = None
        except Exception: pass

    # 3. Mock Data
    if df is None:
        dates = pd.date_range(end=pd.Timestamp.today(), periods=100)
        prices = np.random.normal(100, 5, 100).cumsum()
        df = pd.DataFrame({'Open': prices, 'High': prices+2, 'Low': prices-2, 'Close': prices, 'Volume': np.random.randint(1000, 5000, 100)}, index=dates)

    df['Returns'] = df['Close'].pct_change()
    df['SMA_20'] = df['Close'].rolling(20).mean()
    df['SMA_50'] = df['Close'].rolling(50).mean()
    df = df.dropna()
    
    last_close = float(df['Close'].iloc[-1])
    prev_close = float(df['Close'].iloc[-2])
    daily_change = ((last_close - prev_close) / prev_close) * 100
    current_vol = float(df['Returns'].rolling(20).std().iloc[-1])
    
    # Quant Logic
    trend_bias = 0.1 if df['SMA_20'].iloc[-1] > df['SMA_50'].iloc[-1] else -0.1
    momentum = float(df['Returns'].tail(5).mean()) * 20
    prob_up = 0.5 + trend_bias + momentum
    prob_up = min(max(prob_up, 0.15), 0.85) 
    
    return df, prob_up, current_vol, last_close, daily_change

def get_bar_pattern(o, h, l, c):
    rng = h - l
    if rng < 1e-9: return "Flat"
    body = abs(c - o)
    if body / rng < 0.15: return "Doji"
    if c > o:
        if (c - l) / rng > 0.75: return "Strong Bull"
        if (h - c) / rng > 0.6:  return "Inv. Hammer"
        return "Bullish"
    else:
        if (h - c) / rng > 0.75: return "Strong Bear"
        if (c - l) / rng > 0.6:  return "Hammer"
        return "Bearish"

def go_to_detail(ticker_data):
    st.session_state.active_ticker = ticker_data
    st.session_state.view = 'detail'

def go_to_feed():
    st.session_state.view = 'feed'
    st.session_state.active_ticker = None

def render_card(m, data, tab_id):
    df, prob, vol, price, change = data
    prob_pct = int(prob * 100)
    no_pct = 100 - prob_pct
    
    st.markdown(f"""
    <div class="market-card">
        <div style="display:flex; justify-content: space-between; align-items: flex-start;">
            <div class="market-question">Will <b>{m['id']}</b> close higher tomorrow?</div>
            <div class="market-pct">{prob_pct}%</div>
        </div>
        <div class="market-meta">{m['cat']}</div>
        <div class="trade-row">
            <div class="pill-yes">Yes {prob_pct}¢</div>
            <div class="pill-no">No {no_pct}¢</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Changed from "Trade" to "View Analysis"
    if st.button(f"View {m['id']} Analysis", key=f"btn_{m['id']}_{tab_id}", use_container_width=True):
        go_to_detail({**m, "data": data})
        st.rerun()

# --- MAIN APP ---
st.markdown('<div class="main-container">', unsafe_allow_html=True)

if st.session_state.view == 'feed':
    # --- PAGE 1: DISCOVER FEED ---
    st.markdown("""
    <div style="display:flex; align-items:center; gap:10px; margin-bottom: 20px;">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
            <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
            <line x1="12" y1="22.08" x2="12" y2="12"></line>
        </svg>
        <h1 style="margin:0; font-size: 28px; font-weight: 800; color: white;">Vantage</h1>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["All", "Tech", "Crypto", "Finance"])
    
    with tab1:
        for m in MARKETS:
            render_card(m, get_market_data(m['id']), "tab1")
    with tab2:
        for m in MARKETS:
            if m['tag'] == 'Tech': render_card(m, get_market_data(m['id']), "tab2")
    with tab3:
        for m in MARKETS:
            if m['tag'] == 'Crypto': render_card(m, get_market_data(m['id']), "tab3")
    with tab4:
        for m in MARKETS:
            if m['tag'] == 'Finance': render_card(m, get_market_data(m['id']), "tab4")

elif st.session_state.view == 'detail':
    # --- PAGE 2: DETAIL VIEW & TRADE PLAN ---
    m = st.session_state.active_ticker
    df, prob, vol, price, change = m['data']
    prob_pct = int(prob * 100)
    no_pct = 100 - prob_pct
    
    # Back Button
    st.markdown('<div class="btn-back">', unsafe_allow_html=True)
    if st.button("← Back to Discover"):
        go_to_feed()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
        
    st.markdown(f'<div class="detail-title">Will <b>{m["id"]}</b> close higher tomorrow?</div>', unsafe_allow_html=True)
    
    # Chart
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index[-30:], open=df['Open'][-30:], high=df['High'][-30:], 
        low=df['Low'][-30:], close=df['Close'][-30:],
        increasing_line_color='#34D399', decreasing_line_color='#F87171'
    ))
    fig.update_layout(
        template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=10, b=10), height=220, showlegend=False,
        xaxis=dict(showgrid=False, showticklabels=False), 
        yaxis=dict(showgrid=True, gridcolor='#2D2F3A', side='right')
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    
    # Prices
    st.markdown(f"""
    <div style="display:flex; justify-content: space-between; margin-bottom: 20px;">
        <div><span class="price-display price-yes">Yes {prob_pct}¢</span></div>
        <div><span class="price-display price-no">No {no_pct}¢</span></div>
    </div>
    """, unsafe_allow_html=True)
    
    # --- TRADE PLAN LOGIC ---
    last_bar = df.iloc[-1]
    pattern = get_bar_pattern(float(last_bar['Open']), float(last_bar['High']), float(last_bar['Low']), float(last_bar['Close']))
    
    # Calculate ATR for Stop Loss
    df['High-Low'] = df['High'] - df['Low']
    df['High-Close'] = abs(df['High'] - df['Close'].shift())
    df['Low-Close'] = abs(df['Low'] - df['Close'].shift())
    df['TR'] = df[['High-Low', 'High-Close', 'Low-Close']].max(axis=1)
    atr = float(df['TR'].rolling(14).mean().iloc[-1])
    
    recent_low = float(df['Low'].tail(10).min())
    recent_high = float(df['High'].tail(10).max())
    
    if prob_up >= 0.55:
        bias = "BULLISH"
        bias_color = "#34D399"
        reasoning = f"Momentum is positive and the 20-day trend is above the 50-day. Recent pattern: <b>{pattern}</b>."
        entry = price
        stop_loss = min(recent_low, price - (1.5 * atr))
        target = price + (2.0 * (price - stop_loss)) # 2:1 Risk/Reward
    elif prob_up <= 0.45:
        bias = "BEARISH"
        bias_color = "#F87171"
        reasoning = f"Momentum is weak and the 20-day trend is below the 50-day. Recent pattern: <b>{pattern}</b>."
        entry = price
        stop_loss = max(recent_high, price + (1.5 * atr))
        target = price - (2.0 * (stop_loss - price)) # 2:1 Risk/Reward
    else:
        bias = "NEUTRAL / WAIT"
        bias_color = "#A1A1AA"
        reasoning = "The asset is chopping sideways. No clear trend or momentum edge right now."
        entry = price
        stop_loss = price - atr
        target = price + atr
    
    # Render Trade Plan Box
    st.markdown(f"""
    <div class="trade-plan">
        <div class="trade-plan-title">Today's Trade Setup</div>
        <div style="color: {bias_color}; font-weight: bold; font-size: 18px; margin-bottom: 10px;">Model Bias: {bias}</div>
        <p style="color: #D1D5DB; font-size: 13px; margin-bottom: 15px;">{reasoning}</p>
        
        <div class="plan-row"><span class="plan-label">Entry Zone</span><span class="plan-val">${entry:.2f}</span></div>
        <div class="plan-row"><span class="plan-label">Take Profit (Target)</span><span class="plan-val" style="color:#34D399;">${target:.2f}</span></div>
        <div class="plan-row"><span class="plan-label">Stop Loss (Risk)</span><span class="plan-val" style="color:#F87171;">${stop_loss:.2f}</span></div>
    </div>
    """, unsafe_allow_html=True)

    # Stats Row
    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="stat-box"><div class="stat-label">Pattern</div><div class="stat-val">{pattern}</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="stat-box"><div class="stat-label">Volatility</div><div class="stat-val">{vol*100:.1f}%</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="stat-box"><div class="stat-label">Current Price</div><div class="stat-val">${price:.2f}</div></div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# --- BOTTOM NAVIGATION ---
st.markdown("""
<div class="bottom-nav">
    <div class="nav-item active"><div class="nav-icon">🔍</div>Discover</div>
    <div class="nav-item"><div class="nav-icon">💼</div>Portfolio</div>
    <div class="nav-item"><div class="nav-icon">⭐</div>Watchlist</div>
    <div class="nav-item"><div class="nav-icon">👤</div>Profile</div>
</div>
""", unsafe_allow_html=True)
