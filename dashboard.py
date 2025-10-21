# TARGET_FILE: dashboard.py
import streamlit as st
import json
import time
import pandas as pd
import plotly.graph_objs as go
from pathlib import Path
import os

# ----------------------------
# Configuration
# ----------------------------
STATE_FILE = "shared_state.json"
KLINE_FILE = "latest_klines.json"
SYMBOL = "BTCUSDT"

# ----------------------------
# Page config
# ----------------------------
st.set_page_config(
    page_title="COCO Scalping Bot",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for black/red theme
st.markdown("""
    <style>
    body {
        color: #e0e0e0;
        background-color: #000000;
    }
    .stApp {
        background-color: #000000;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #ffffff;
    }
    .stMetric {
        background-color: #111111;
        border-radius: 8px;
        padding: 10px;
        margin: 5px 0;
    }
    .stMetric > div > div {
        color: #ffffff !important;
    }
    .sell {
        color: #ff4d4d !important;
    }
    .buy {
        color: #4dff4d !important;
    }
    .neutral {
        color: #aaaaaa !important;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------------------
# Helper Functions
# ----------------------------
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def load_klines():
    if os.path.exists(KLINE_FILE):
        try:
            with open(KLINE_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def format_side(side):
    if side == "buy":
        return f'<span class="buy">BUY</span>'
    elif side == "sell":
        return f'<span class="sell">SELL</span>'
    else:
        return f'<span class="neutral">NEUTRAL</span>'

# ----------------------------
# Dashboard Layout
# ----------------------------
st.title("⚡ COCO Crypto Scalping Bot")
st.markdown(f"**Symbol**: `{SYMBOL}` | **Mode**: Testnet")

# Auto-refresh every 2 seconds
if st.button("🔄 Refresh Now"):
    st.rerun()

# Load data
state = load_state()
kline_data = load_klines()

# ----------------------------
# Metrics Row
# ----------------------------
col1, col2, col3, col4 = st.columns(4)

portfolio = state.get("portfolio_value_usdt", 1000.0)
pnl_pct = state.get("total_pnl_pct", 0.0)
daily_pnl = state.get("daily_pnl_pct", 0.0)
status = state.get("status", "unknown")

col1.metric("Portfolio (USDT)", f"${portfolio:,.2f}")
col2.metric("Total PnL", f"{pnl_pct:+.2f}%", delta_color="normal")
col3.metric("Daily PnL", f"{daily_pnl:+.2f}%", delta_color="normal")
col4.metric("Status", status.upper())

# ----------------------------
# Candlestick Chart
# ----------------------------
st.subheader("Price Chart (1s)")
if kline_data and "klines" in kline_data:
    klines = kline_data["klines"]
    if len(klines) > 0:
        df = pd.DataFrame(klines)
        df['time'] = pd.to_datetime(df['t'], unit='ms')
        
        fig = go.Figure(data=go.Candlestick(
            x=df['time'],
            open=df['o'],
            high=df['h'],
            low=df['l'],
            close=df['c'],
            increasing_line_color='#4dff4d',
            decreasing_line_color='#ff4d4d'
        ))
        fig.update_layout(
            height=400,
            plot_bgcolor='#000000',
            paper_bgcolor='#000000',
            xaxis=dict(
                showgrid=False,
                color='white'
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='#333333',
                color='white'
            ),
            margin=dict(l=20, r=20, t=20, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No candle data yet")
else:
    st.info("Waiting for candle data...")

# ----------------------------
# Active Position & Signal (same as before)
# ----------------------------
st.subheader("Active Position")
pos = state.get("active_position")
if pos:
    side = pos["side"]
    qty = pos["quantity"]
    entry = pos["entry_price"]
    open_time = pos["open_time"]
    st.markdown(f"""
    - **Side**: {format_side(side)}
    - **Size**: {qty:.6f} BTC
    - **Entry**: ${entry:,.2f}
    - **Opened**: {time.strftime('%H:%M:%S', time.localtime(open_time))}
    """, unsafe_allow_html=True)
else:
    st.info("No active position")

st.subheader("Last Signal")
signal = state.get("last_signal")
if signal:
    side = signal["side"]
    conf = signal["confidence"]
    price = signal["price"]
    ts = signal["time"]
    st.markdown(f"""
    - **Action**: {format_side(side)}
    - **Confidence**: {conf:.2%}
    - **Price**: ${price:,.2f}
    - **Time**: {time.strftime('%H:%M:%S', time.localtime(ts))}
    """, unsafe_allow_html=True)
else:
    st.info("No signal yet")

st.subheader("Log")
errors = state.get("errors", [])
if errors:
    for err in errors[-5:]:
        st.warning(err)
else:
    st.success("No errors")

# ----------------------------
# Auto-refresh
# ----------------------------
time.sleep(2)
st.rerun()