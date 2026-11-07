import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Blackbox | Quant Engine", page_icon="⬛", layout="centered")

# --- CUSTOM NEON DARK CSS ---
st.markdown("""
<style>
    /* Hide Streamlit default menu and footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Deep black background */
    .stApp { background-color: #050505; color: #E4E4E7; font-family: 'Inter', sans-serif; }
    
    /* Input field styling */
    .stTextInput>div>div>input {
        background-color: #121212;
        color: #39FF14;
        border: 1px solid #39FF14;
        font-family: 'Courier New', monospace;
        font-size: 18px;
    }
    
    /* Neon Button */
    .stButton>button {
        background-color: #000000; color: #39FF14; border: 1px solid #39FF14;
        border-radius: 8px; padding: 10px 24px; font-weight: bold; width: 100%;
        box-shadow: 0 0 15px rgba(57, 255, 20, 0.2); transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #39FF14; color: #000000; box-shadow: 0 0 25px rgba(57, 255, 20, 0.8);
    }
    
    /* Hero Signal Card */
    .signal-card {
        background: linear-gradient(145deg, #121212, #050505);
        border: 1px solid #27272A;
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
    }
    .signal-up { color: #39FF14; font-size: 56px; font-weight: 900; text-shadow: 0 0 20px rgba(57, 255, 20, 0.5); margin: 0; font-family: 'Courier New', monospace;}
    .signal-down { color: #FF3131; font-size: 56px; font-weight: 900; text-shadow: 0 0 20px rgba(255, 49, 49, 0.5); margin: 0; font-family: 'Courier New', monospace;}
    .signal-neutral { color: #A1A1AA; font-size: 56px; font-weight: 900; margin: 0; font-family: 'Courier New', monospace;}
    
    /* Metrics Boxes */
    div[data-testid="stMetricValue"] { color: #39FF14 !important; font-family: 'Courier New', monospace; font-size: 24px;}
    div[data-testid="stMetricLabel"] { color: #A1A1AA !important; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;}
    
    /* Table Styling */
    .stDataFrame { border: 1px solid #27272A; border-radius: 10px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---
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

def calculate_metrics(ticker_symbol):
    df = yf.download(ticker_symbol, period="1y", interval="1d", progress=False)
    if len(df) < 50: return None, None, None, None, None
    
    # Handle MultiIndex columns from yfinance
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    df['Returns'] = df['Close'].pct_change()
    df['SMA_20'] = df['Close'].rolling(20).mean()
    df['SMA_50'] = df['Close'].rolling(50).mean()
    df = df.dropna()
    
    last_close = float(df['Close'].iloc[-1])
    prev_close = float(df['Close'].iloc[-2])
    daily_change = ((last_close - prev_close) / prev_close) * 100
    
    current_vol = float(df['Returns'].rolling(20).std().iloc[-1])
    
    # Simple Quant Logic: Trend + Momentum
    trend_bias = 0.1 if df['SMA_20'].iloc[-1] > df['SMA_50'].iloc[-1] else -0.1
    momentum = float(df['Returns'].tail(5).mean()) * 20
    
    prob_up = 0.5 + trend_bias + momentum
    prob_up = min(max(prob_up, 0.15), 0.85) 
    
    last_bar = df.iloc[-1]
    pattern = get_bar_pattern(float(last_bar['Open']), float(last_bar['High']), float(last_bar['Low']), float(last_bar['Close']))
    
    return df, prob_up, current_vol, pattern, last_close, daily_change

# --- MAIN UI ---
st.markdown("<h1 style='text-align: center; color: #39FF14; font-family: Courier New;'>⬛ BLACKBOX</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #A1A1AA; font-size: 14px; margin-top: -15px;'>QUANTITATIVE DIRECTION ENGINE</p>", unsafe_allow_html=True)

ticker = st.text_input("", value="NVDA", placeholder="Enter Ticker Symbol (e.g. NVDA, BTC-USD)").upper()

if st.button("RUN ANALYSIS"):
    with st.spinner("Decrypting market data..."):
        df, prob_up, current_vol, pattern, last_close, daily_change = calculate_metrics(ticker)
        
        if df is None:
            st.error("Insufficient data for this ticker.")
        else:
            time.sleep(0.4)
            
            # 1. HERO SIGNAL CARD
            if prob_up >= 0.55:
                signal_html = f'<div class="signal-card"><p class="signal-up">BUY / UP</p><p style="color:#A1A1AA; margin-top:10px;">Confidence: {prob_up*100:.1f}%</p></div>'
            elif prob_up <= 0.45:
                signal_html = f'<div class="signal-card"><p class="signal-down">SELL / DOWN</p><p style="color:#A1A1AA; margin-top:10px;">Confidence: {(1-prob_up)*100:.1f}%</p></div>'
            else:
                signal_html = f'<div class="signal-card"><p class="signal-neutral">NO CALL</p><p style="color:#A1A1AA; margin-top:10px;">Market is chopping sideways.</p></div>'
            
            st.markdown(signal_html, unsafe_allow_html=True)
            
            # 2. METRICS ROW
            col1, col2, col3 = st.columns(3)
            col1.metric("Last Close", f"${last_close:.2f}", f"{daily_change:+.2f}%")
            col2.metric("Volatility (20d)", f"{current_vol*100:.2f}%")
            col3.metric("Pattern", pattern)
            
            # 3. PRO CHART
            st.markdown("<br>", unsafe_allow_html=True)
            
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                vertical_spacing=0.03, subplot_titles=('', ''), 
                                row_width=[0.2, 0.8])

            fig.add_trace(go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                increasing_line_color='#39FF14', decreasing_line_color='#FF3131', name="Price"
            ), row=1, col=1)
            
            fig.add_trace(go.Scatter(
                x=df.index, y=df['SMA_20'], line=dict(color='#A1A1AA', width=1.5), name="20 SMA"
            ), row=1, col=1)

            colors = ['#39FF14' if close >= open else '#FF3131' for close, open in zip(df['Close'], df['Open'])]
            fig.add_trace(go.Bar(
                x=df.index, y=df['Volume'], marker_color=colors, name="Volume", showlegend=False
            ), row=2, col=1)

            fig.update_layout(
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis_rangeslider_visible=False,
                margin=dict(l=0, r=0, t=10, b=0),
                height=450,
                showlegend=False
            )
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#1E1E24')
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#1E1E24')
            
            fig.update_xaxes(range=[df.index[-60], df.index[-1]])
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 4. DATA TABLE
            st.markdown("### Recent Bars")
            recent = df.tail(5).copy()
            recent['Date'] = recent.index.strftime('%b %d, %Y')
            
            display_df = recent[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
            display_df['Volume'] = (display_df['Volume'] / 1e6).round(2).astype(str) + "M"
            
            display_df['Pattern'] = [
                get_bar_pattern(row['Open'], row['High'], row['Low'], row['Close']) 
                for _, row in recent.iterrows()
            ]
            
            st.dataframe(
                display_df.style.format({"Open": "{:.2f}", "High": "{:.2f}", "Low": "{:.2f}", "Close": "{:.2f}"}),
                use_container_width=True, hide_index=True
            )
            
            st.markdown("<p style='text-align: center; color: #52525B; font-size: 10px; margin-top: 30px;'>Algorithmic analysis provided by Blackbox. Not financial advice.</p>", unsafe_allow_html=True)
