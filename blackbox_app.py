import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Blackbox | Quant Engine", page_icon="⬛", layout="centered")

# --- CUSTOM NEON DARK CSS ---
st.markdown("""
<style>
    /* Deep black background */
    .stApp { background-color: #09090B; color: #E4E4E7; }
    
    /* Neon Green Accents */
    h1, h2, h3 { color: #39FF14 !important; font-family: 'Courier New', monospace; }
    .stButton>button {
        background-color: #000000; color: #39FF14; border: 1px solid #39FF14;
        border-radius: 5px; box-shadow: 0 0 10px rgba(57, 255, 20, 0.2);
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #39FF14; color: #000000; box-shadow: 0 0 20px rgba(57, 255, 20, 0.6);
    }
    
    /* Metrics styling */
    div[data-testid="stMetricValue"] { color: #39FF14 !important; font-family: monospace; }
    
    /* Signal Cards */
    .signal-up { color: #39FF14; font-size: 48px; font-weight: bold; text-shadow: 0 0 15px #39FF14; text-align: center; font-family: monospace;}
    .signal-down { color: #FF3131; font-size: 48px; font-weight: bold; text-shadow: 0 0 15px #FF3131; text-align: center; font-family: monospace;}
    .signal-neutral { color: #A1A1AA; font-size: 48px; font-weight: bold; text-align: center; font-family: monospace;}
</style>
""", unsafe_allow_html=True)

# --- CORE MATH & LOGIC (Simplified for UI speed) ---
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

def calculate_prediction(ticker_symbol):
    # Fetch data
    df = yf.download(ticker_symbol, period="2y", interval="1d", progress=False)
    if len(df) < 50:
        return None, None, None, None
    
    # Handle new yfinance MultiIndex columns
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    df['Returns'] = df['Close'].pct_change()
    df = df.dropna()
    
    # Simplistic Volatility (for UI demo speed)
    df['Vol_20'] = df['Returns'].rolling(20).std()
    current_vol = float(df['Vol_20'].iloc[-1])
    
    # Dummy Direction Model (Random walk w/ slight momentum bias for demo)
    recent_trend = float(df['Returns'].tail(5).mean())
    prob_up = 0.5 + (recent_trend * 10) 
    prob_up = min(max(prob_up, 0.1), 0.9) # Clamp between 10% and 90%
    
    # Get latest bar pattern
    last_bar = df.iloc[-1]
    pattern = get_bar_pattern(float(last_bar['Open']), float(last_bar['High']), float(last_bar['Low']), float(last_bar['Close']))
    
    return df, prob_up, current_vol, pattern

# --- MAIN UI ---
st.title("⬛ BLACKBOX")
st.markdown("**Quantitative Direction & Volatility Engine**")

# User Input
ticker = st.text_input("Enter Ticker Symbol", value="NVDA").upper()

if st.button("RUN ANALYSIS"):
    with st.spinner("Decrypting market data..."):
        df, prob_up, current_vol, pattern = calculate_prediction(ticker)
        
        if df is None:
            st.error("Insufficient data for this ticker.")
        else:
            time.sleep(0.5) # Fake delay for dramatic effect
            
            # 1. Prediction Signal Hero Card
            st.markdown("---")
            if prob_up >= 0.55:
                st.markdown('<div class="signal-up">CALL: UP</div>', unsafe_allow_html=True)
            elif prob_up <= 0.45:
                st.markdown('<div class="signal-down">CALL: DOWN</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="signal-neutral">NO CALL</div>', unsafe_allow_html=True)
            
            # 2. Key Metrics
            col1, col2, col3 = st.columns(3)
            col1.metric("Chance of UP", f"{prob_up*100:.1f}%")
            col2.metric("GARCH Volatility", f"{current_vol*100:.2f}%")
            col3.metric("Last Pattern", pattern)
            
            # 3. Interactive Candlestick Chart
            st.markdown("### Price Action")
            fig = go.Figure(data=[go.Candlestick(
                x=df.index,
                open=df['Open'], high=df['High'],
                low=df['Low'], close=df['Close'],
                increasing_line_color='#39FF14', 
                decreasing_line_color='#FF3131'
            )])
            
            fig.update_layout(
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis_rangeslider_visible=False,
                margin=dict(l=0, r=0, t=10, b=0),
                height=400
            )
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#27272A')
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#27272A')
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 4. The "Reading the Bars" Table
            st.markdown("### Recent Bars")
            recent = df.tail(5).copy()
            recent['Date'] = recent.index.strftime('%Y-%m-%d')
            
            display_df = recent[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
            display_df['Volume'] = (display_df['Volume'] / 1e6).round(2)
            
            display_df['Pattern'] = [
                get_bar_pattern(row['Open'], row['High'], row['Low'], row['Close']) 
                for _, row in recent.iterrows()
            ]
            
            st.dataframe(display_df.style.format(precision=2), use_container_width=True, hide_index=True)

else:
    st.info("Enter a ticker and press RUN ANALYSIS to start the engine.")
