import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Vantage | Prediction Market", page_icon="⬛", layout="centered")

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
        margin-bottom: 12px;
        display: flex;
        flex-direction: column;
        gap: 8px;
    }
    .market-pct { font-size: 24px; font-weight: 800; color: #FFFFFF; }
    .market-question { font-size: 15px; font-weight: 500; color: #D1D5DB; line-height: 1.3; }
    .market-meta { font-size: 12px; color: #6B7280; margin-bottom: 8px;}
    
    /* Yes/No Pills */
    .trade-row { display: flex; gap: 8px; }
    .pill-yes { 
        background-color: #1A2E22; color: #34D399; border: 1px solid #34D399; 
        border-radius: 20px; padding: 4px 12px; font-size: 12px; font-weight: bold; text-align: center; flex: 1;
    }
    .pill-no { 
        background-color: #2E1A1A; color: #F87171; border: 1px solid #F87171; 
        border-radius: 20px; padding: 4px 12px; font-size: 12px; font-weight: bold; text-align: center; flex: 1;
    }
    
    /* Detail View Styling */
    .detail-title { font-size: 22px; font-weight: 700; line-height: 1.3; margin-bottom: 20px; }
    .price-display { font-size: 28px; font-weight: 800; }
    .price-yes { color: #34D399; }
    .price-no { color: #F87171; }
    .stat-box { background-color: #121319; border-radius: 8px; padding: 12px; text-align: center; }
    .stat-label { font-size: 10px; color: #6B7280; text-transform: uppercase; }
    .stat-val { font-size: 14px; font-weight: 600; color: #FFFFFF; margin-top: 4px;}
    
    /* Buttons */
    .stButton>button {
        width: 100%; border-radius: 8px; font-weight: bold; padding: 12px 0; transition: all 0.2s;
    }
    .btn-buy-yes > button { background-color: #10B981 !important; color: white !important; border: none; }
    .btn-buy-no > button { background-color: #EF4444 !important; color: white !important; border: none; }
    
    /* Bottom Nav */
    .bottom-nav {
        position: fixed; bottom: 0; left: 0; right: 0;
        background-color: #0B0C10; border-top: 1px solid #2D2F3A;
        display: flex; justify-content: space-around; padding: 10px 0 20px 0;
        z-index: 1000;
    }
    .nav-item { color: #6B7280; font-size: 10px; text-align: center; display: flex; flex-direction: column; align-items: center; gap: 4px;}
    .nav-item.active { color: #FFFFFF; }
    .nav-icon { font-size: 18px; }
    
    /* Spacing for bottom nav */
    .main-container { padding-bottom: 80px; }
</style>
""", unsafe_allow_html=True)

# --- MOCK DATA ---
markets = [
    {"id": 1, "pct": 38, "q": "Will the central bank change its rate at the next meeting?", "cat": "Featured·closes in 3 days", "yes": 38, "no": 62},
    {"id": 2, "pct": 42, "q": "Will Windhoek get more than 30 mm of rain this November?", "cat": "Weather·closes Nov 30", "yes": 42, "no": 58},
    {"id": 3, "pct": 61, "q": "Will an open-source model top the main leaderboard by year end?", "cat": "Tech·closes Dec 31", "yes": 61, "no": 39},
    {"id": 4, "pct": 35, "q": "Will the rand close December below 18 per US dollar?", "cat": "Finance·closes Dec 31", "yes": 35, "no": 65}
]

# --- STATE MANAGEMENT ---
if 'view' not in st.session_state:
    st.session_state.view = 'feed'
if 'active_market' not in st.session_state:
    st.session_state.active_market = None

# --- HELPER FUNCTIONS ---
def go_to_detail(market):
    st.session_state.active_market = market
    st.session_state.view = 'detail'

def go_to_feed():
    st.session_state.view = 'feed'
    st.session_state.active_market = None

# --- MAIN APP ---
st.markdown('<div class="main-container">', unsafe_allow_html=True)

if st.session_state.view == 'feed':
    # --- PAGE 1: DISCOVER FEED ---
    st.markdown('<div style="display:flex; align-items:center; gap:10px; margin-bottom: 20px;">'
                '<div style="font-size: 32px;">⬛</div>'
                '<h1 style="margin:0; font-size: 28px; font-weight: 800;">Vantage</h1>'
                '</div>', unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["All", "Weather", "Tech", "Finance"])
    
    with tab1:
        for m in markets:
            # We use HTML for the visual card, and place an invisible Streamlit button over it via CSS or columns
            # Streamlit doesn't support clickable divs easily, so we use a neat trick with columns.
            
            st.markdown(f"""
            <div class="market-card">
                <div style="display:flex; justify-content: space-between; align-items: flex-start;">
                    <div class="market-question">{m['q']}</div>
                    <div class="market-pct">{m['pct']}%</div>
                </div>
                <div class="market-meta">{m['cat']}</div>
                <div class="trade-row">
                    <div class="pill-yes">Yes {m['yes']}¢</div>
                    <div class="pill-no">No {m['no']}¢</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Invisible button spanning the card to trigger the click
            if st.button(f"View {m['q']}", key=f"btn_{m['id']}", use_container_width=True):
                go_to_detail(m)
                st.rerun()
            
            # Negative margin to pull the next card up to the button
            st.markdown('<div style="margin-bottom: -25px;"></div>', unsafe_allow_html=True)

elif st.session_state.view == 'detail':
    # --- PAGE 2: DETAIL VIEW ---
    m = st.session_state.active_market
    
    # Back Button
    if st.button("← Back to Discover"):
        go_to_feed()
        st.rerun()
        
    st.markdown(f'<div class="detail-title">{m["q"]}</div>', unsafe_allow_html=True)
    
    # Timeframes
    st.markdown("""
    <div style="display:flex; gap: 15px; color: #8A8F98; font-size: 14px; font-weight: 600; margin-bottom: 20px;">
        <span style="color:white; border-bottom: 2px solid white; padding-bottom:4px;">1D</span>
        <span>1W</span><span>1M</span><span>3M</span><span>All</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Fake Chart
    dates = pd.date_range(end=pd.Timestamp.today(), periods=30)
    prices = np.random.normal(m['yes'], 5, 30).cumsum()
    prices = np.clip(prices, 10, 90) # Keep between 10-90
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=prices, mode='lines', line=dict(color='#34D399', width=3), fill='tozeroy', fillcolor='rgba(52, 211, 153, 0.1)'))
    fig.update_layout(
        template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=10, b=10), height=200, showlegend=False,
        xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showgrid=True, gridcolor='#2D2F3A', side='right')
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    
    # Prices
    st.markdown(f"""
    <div style="display:flex; justify-content: space-between; margin-bottom: 20px;">
        <div><span class="price-display price-yes">Yes {m['yes']}¢</span></div>
        <div><span class="price-display price-no">No {m['no']}¢</span></div>
    </div>
    """, unsafe_allow_html=True)
    
    # Order Box
    st.markdown('<div style="background: #121319; border: 1px solid #232530; border-radius: 12px; padding: 16px; margin-bottom: 20px;">', unsafe_allow_html=True)
    amount = st.number_input("Amount", min_value=1.0, value=25.0, step=5.0, format="%.2f")
    
    # Calculate payout
    price_decimal = m['yes'] / 100.0
    payout = amount / price_decimal if price_decimal > 0 else 0
    
    st.markdown(f"<div style='display:flex; justify-content:space-between; font-size:14px; color:#8A8F98; margin-bottom:16px;'><span>Pays out if Yes</span><span style='color:white; font-weight:bold;'>${payout:.2f}</span></div>", unsafe_allow_html=True)
    
    # Buy Buttons
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="btn-buy-yes">', unsafe_allow_html=True)
        st.button(f"Buy Yes", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="btn-buy-no">', unsafe_allow_html=True)
        st.button(f"Buy No", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Stats Row
    c1, c2, c3 = st.columns(3)
    c1.markdown('<div class="stat-box"><div class="stat-label">Volume</div><div class="stat-val">$12.4K</div></div>', unsafe_allow_html=True)
    c2.markdown('<div class="stat-box"><div class="stat-label">Traders</div><div class="stat-val">318</div></div>', unsafe_allow_html=True)
    c3.markdown('<div class="stat-box"><div class="stat-label">Closes in</div><div class="stat-val">23 days</div></div>', unsafe_allow_html=True)

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
