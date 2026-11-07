import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time
from datetime import datetime

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Vantage | Quant", page_icon="⬛", layout="centered")

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
    .stat-box { background-color: #121319; border-radius: 8px; padding: 12px; text-align: center; border: 1px solid #232530;}
    .stat-label { font-size: 10px; color: #6B7280; text-transform: uppercase; }
    .stat-val { font-size: 14px; font-weight: 600; color: #FFFFFF; margin-top: 4px;}
    
    /* Buttons */
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; padding: 12px 0; transition: all 0.2s; border: none;}
    .btn-buy-yes > button { background-color: #10B981 !important; color: white !important; }
    .btn-buy-no > button { background-color: #EF4444 !important; color: white !important; }
    .btn-back > button { background-color: transparent !important; color: #8A8F98 !important; text-align: left; padding: 0 0 10px 0; }
    
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
    {"id": "NVDA", "name": "NVIDIA Corp", "cat": "Tech·closes tomorrow"},
    {"id": "BTC-USD", "name": "Bitcoin", "cat": "Crypto·closes tomorrow"},
    {"id": "SPY", "name": "S&P 500 ETF", "cat": "Finance·closes tomorrow"},
    {"id": "AAPL", "name": "Apple Inc", "cat": "Tech·closes tomorrow"}
]

# --- STATE MANAGEMENT ---
if 'view' not in st.session_state:
    st.session_state.view = 'feed'
if 'active_ticker' not in st.session_state:
    st.session_state.active_ticker = None

# --- CACHED DATA FETCHING & MODEL ---
@st.cache_data(ttl=3600)
def get_market_data(ticker):
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        if len(df) < 50: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
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
    except:
        return None

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

# --- MAIN APP ---
st.markdown('<div class="main-container">', unsafe_allow_html=True)

if st.session_state.view == 'feed':
    # --- PAGE 1: DISCOVER FEED ---
    st.markdown('<div style="display:flex; align-items:center; gap:10px; margin-bottom: 20px;">'
                '<div style="font-size: 32px;">⬛</div>'
                '<h1 style="margin:0; font-size: 28px; font-weight: 800;">Vantage</h1>'
                '</div>', unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["All", "Tech", "Crypto", "Finance"])
    
    with tab1:
        for m in MARKETS:
            data = get_market_data(m['id'])
            if data:
                df, prob, vol, price, change = data
                prob_pct = int(prob * 100)
                no_pct = 100 - prob_pct
                
                # Card HTML
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
                
                # Invisible button mapping to the card
                if st.button(f"Trade {m['id']}", key=f"btn_{m['id']}", use_container_width=True):
                    go_to_detail({**m, "data": data})
                    st.rerun()
                st.markdown('<div style="margin-bottom: -25px;"></div>', unsafe_allow_html=True)

elif st.session_state.view == 'detail':
    # --- PAGE 2: DETAIL VIEW ---
    m = st.session_state.active_ticker
    df, prob, vol, price, change = m['data']
    prob_pct = int(prob * 100)
    no_pct = 100 - prob_pct
    
    # Back Button
    st.markdown('<div class="btn-back">', unsafe_allow_html=True)
    if st.button("← Back"):
        go_to_feed()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
        
    st.markdown(f'<div class="detail-title">Will {m["id"]} close higher tomorrow?</div>', unsafe_allow_html=True)
    
    # Timeframes
    st.markdown("""
    <div style="display:flex; gap: 20px; color: #8A8F98; font-size: 14px; font-weight: 600; margin-bottom: 20px;">
        <span style="color:white; border-bottom: 2px solid white; padding-bottom:4px;">1D</span>
        <span>1W</span><span>1M</span><span>3M</span><span>All</span>
    </div>
    """, unsafe_allow_html=True)
    
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
    
    # Order Box
    st.markdown('<div style="background: #121319; border: 1px solid #232530; border-radius: 12px; padding: 16px; margin-bottom: 20px;">', unsafe_allow_html=True)
    amount = st.number_input("Amount", min_value=1.0, value=25.0, step=5.0, format="%.2f")
    
    payout = amount / (prob_pct / 100.0) if prob_pct > 0 else 0
    
    st.markdown(f"<div style='display:flex; justify-content:space-between; font-size:14px; color:#8A8F98; margin-bottom:16px;'><span>Pays out if Yes</span><span style='color:white; font-weight:bold;'>${payout:.2f}</span></div>", unsafe_allow_html=True)
    
    # Buy Buttons
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="btn-buy-yes">', unsafe_allow_html=True)
        st.button("Buy Yes", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="btn-buy-no">', unsafe_allow_html=True)
        st.button("Buy No", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Stats Row
    last_bar = df.iloc[-1]
    pattern = get_bar_pattern(float(last_bar['Open']), float(last_bar['High']), float(last_bar['Low']), float(last_bar['Close']))
    
    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="stat-box"><div class="stat-label">Pattern</div><div class="stat-val">{pattern}</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="stat-box"><div class="stat-label">Volatility</div><div class="stat-val">{vol*100:.1f}%</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="stat-box"><div class="stat-label">Price</div><div class="stat-val">${price:.2f}</div></div>', unsafe_allow_html=True)

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
