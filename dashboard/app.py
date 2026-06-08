import os
import time
from typing import Optional, Any
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from config.settings import settings

# Set Streamlit configurations
st.set_page_config(
    page_title="NSE Live ETL Pipeline Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Read API base URL from environment
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Inject premium custom CSS (Dark-mode, Glassmorphism, Google Fonts)
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=Outfit:wght@400;600;800&display=swap');
        
        /* General page layout overrides */
        .main {
            background: radial-gradient(circle at 10% 20%, rgba(20, 20, 35, 1) 0%, rgba(10, 10, 15, 1) 100%);
            color: #E2E8F0;
            font-family: 'Inter', sans-serif;
        }
        
        h1, h2, h3 {
            font-family: 'Outfit', sans-serif;
            font-weight: 800;
            letter-spacing: -0.5px;
        }
        
        /* Header styling with gradient */
        .dashboard-header {
            background: linear-gradient(135deg, #3B82F6 0%, #8B5CF6 50%, #EC4899 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 2.8rem;
            margin-bottom: 0.2rem;
            font-weight: 800;
        }
        
        .dashboard-subheader {
            color: #94A3B8;
            font-size: 1.1rem;
            margin-bottom: 2rem;
            font-weight: 400;
        }
        
        /* Glassmorphic Cards */
        .glass-card {
            background: rgba(30, 41, 59, 0.45);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
            transition: all 0.3s ease-in-out;
        }
        
        .glass-card:hover {
            border: 1px solid rgba(255, 255, 255, 0.15);
            box-shadow: 0 12px 40px 0 rgba(59, 130, 246, 0.15);
            transform: translateY(-2px);
        }
        
        .card-title {
            color: #94A3B8;
            font-size: 0.85rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }
        
        .card-value {
            font-size: 1.8rem;
            font-weight: 700;
            font-family: 'Outfit', sans-serif;
            color: #FFFFFF;
        }
        
        .card-change-pos {
            color: #10B981;
            font-size: 0.95rem;
            font-weight: 600;
        }
        
        .card-change-neg {
            color: #EF4444;
            font-size: 0.95rem;
            font-weight: 600;
        }
        
        /* Alert list styling */
        .alert-ticker-box {
            background: rgba(239, 68, 68, 0.1);
            border-left: 4px solid #EF4444;
            padding: 12px;
            border-radius: 0 8px 8px 0;
            margin-bottom: 8px;
        }
        
        .anomaly-ticker-box {
            background: rgba(245, 158, 11, 0.1);
            border-left: 4px solid #F59E0B;
            padding: 12px;
            border-radius: 0 8px 8px 0;
            margin-bottom: 8px;
        }
    </style>
""", unsafe_allow_html=True)


# Fetch data helper functions with error tolerance
def safe_get(endpoint: str) -> Optional[Any]:
    try:
        response = requests.get(f"{API_URL}/{endpoint}", timeout=2.0)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None


# App layout containers
title_col, status_col = st.columns([3, 1])
with title_col:
    st.markdown('<div class="dashboard-header">NSE Real-time Pipeline</div>', unsafe_allow_html=True)
    st.markdown('<div class="dashboard-subheader">Production-grade FinTech Data Engineering Portfolio</div>', unsafe_allow_html=True)

# System Health Check
summary_data = safe_get("stocks/summary")
latest_stocks = safe_get("stocks/latest")

with status_col:
    st.write("")
    is_ok = summary_data is not None and latest_stocks is not None
    health_color = "🟢" if is_ok else "🔴"
    health_text = "System Online" if is_ok else "Connecting to API..."
    st.markdown(f"**System Status:** {health_color} {health_text}")
    if is_ok and latest_stocks:
        is_sim = latest_stocks[0].get("simulated", True) if len(latest_stocks) > 0 else True
        mode_text = "Simulation Mode (GBM)" if is_sim else "Live Market (yfinance)"
        st.caption(f"Engine Mode: **{mode_text}**")
    else:
        st.caption("Unable to fetch data. Verify Docker containers are running.")

# Initialize selected ticker state
if "selected_ticker" not in st.session_state:
    st.session_state.selected_ticker = "SCOM.KE"

# Main Layout: Sidebar configuration for stock selection
tickers_list = [
    "SCOM.KE", "EQTY.KE", "KCB.KE", "COOP.KE", "EABL.KE",
    "ABSA.KE", "BAT.KE", "NCBA.KE", "SBIC.KE", "KEGN.KE"
]

selected_ticker = st.selectbox(
    "Select Stock Ticker for Detailed Analysis:",
    tickers_list,
    index=tickers_list.index(st.session_state.selected_ticker)
)
st.session_state.selected_ticker = selected_ticker

# Fetch fresh API records
summary = safe_get("stocks/summary")
latest = safe_get("stocks/latest")
history = safe_get(f"stocks/history/{selected_ticker}?limit=100")

if not latest or not summary:
    st.warning("Awaiting connection/data from API service...")
    time.sleep(2)
    st.rerun()

# Convert lists to Pandas DataFrames for formatting and Plotly visualizations
df_latest = pd.DataFrame(latest)
df_summary = summary

# Process history
if history:
    df_history = pd.DataFrame(history)
    df_history["timestamp"] = pd.to_datetime(df_history["timestamp"])
else:
    df_history = pd.DataFrame()

# 1. TOP METRICS ROW
m1, m2, m3, m4 = st.columns(4)

# Top Gainer Card
gainer = df_summary.get("top_gainer")
with m1:
    gainer_html = f"""
    <div class="glass-card">
        <div class="card-title">Top Gainer</div>
        <div class="card-value">{gainer['ticker'] if gainer else 'N/A'}</div>
        <div class="card-change-pos">{f"+{gainer['percent_change']:.2f}%" if gainer else "0.00%"}</div>
    </div>
    """
    st.markdown(gainer_html, unsafe_allow_html=True)
    
# Top Loser Card
loser = df_summary.get("top_loser")
with m2:
    loser_html = f"""
    <div class="glass-card">
        <div class="card-title">Top Loser</div>
        <div class="card-value">{loser['ticker'] if loser else 'N/A'}</div>
        <div class="card-change-neg">{f"{loser['percent_change']:.2f}%" if loser else "0.00%"}</div>
    </div>
    """
    st.markdown(loser_html, unsafe_allow_html=True)
    
# Average Volatility
avg_vol = df_summary.get("avg_volatility", 0.0)
with m3:
    vol_html = f"""
    <div class="glass-card">
        <div class="card-title">Avg Volatility</div>
        <div class="card-value">{avg_vol:.4f}</div>
        <div style="color: #94A3B8; font-size: 0.95rem;">Rolling std of change</div>
    </div>
    """
    st.markdown(vol_html, unsafe_allow_html=True)
    
# Active Alerts Card
active_alerts_cnt = df_summary.get("total_active_alerts", 0)
anomalies_cnt = df_summary.get("total_anomalies_detected", 0)
with m4:
    alerts_html = f"""
    <div class="glass-card">
        <div class="card-title">Alerts / Anomalies</div>
        <div class="card-value">{active_alerts_cnt} / {anomalies_cnt}</div>
        <div style="color: #F59E0B; font-size: 0.95rem; font-weight: 600;">Active Alerts & Flags</div>
    </div>
    """
    st.markdown(alerts_html, unsafe_allow_html=True)

# 2. CHARTS & GRIDS ROW
col_left, col_right = st.columns([2, 1])

# Left Side: Plotly Stock charts
with col_left:
    st.subheader(f"📈 {selected_ticker} Rolling Averages")
    if not df_history.empty:
        # Plot price with SMA overlays
        fig = go.Figure()
        
        # Raw Stock price line
        fig.add_trace(go.Scatter(
            x=df_history["timestamp"],
            y=df_history["price"],
            mode="lines",
            name="Live Ticks",
            line=dict(color="#3B82F6", width=2.5)
        ))
        
        # Fast SMA (5m)
        fig.add_trace(go.Scatter(
            x=df_history["timestamp"],
            y=df_history["sma_5m"],
            mode="lines",
            name="SMA 5-Min",
            line=dict(color="#10B981", width=1.5, dash="dash")
        ))

        # Slow SMA (15m)
        fig.add_trace(go.Scatter(
            x=df_history["timestamp"],
            y=df_history["sma_15m"],
            mode="lines",
            name="SMA 15-Min",
            line=dict(color="#8B5CF6", width=1.5, dash="dot")
        ))

        # Highlight Anomalies
        anoms_history = df_history[df_history["anomaly_detected"] == True]
        if not anoms_history.empty:
            fig.add_trace(go.Scatter(
                x=anoms_history["timestamp"],
                y=anoms_history["price"],
                mode="markers",
                name="Anomalies",
                marker=dict(color="#F59E0B", size=10, symbol="triangle-up")
            ))
        
        # Highlight Price Drops
        drops_history = df_history[df_history["price_drop_alert"] == True]
        if not drops_history.empty:
            fig.add_trace(go.Scatter(
                x=drops_history["timestamp"],
                y=drops_history["price"],
                mode="markers",
                name="Price Drop (>5%)",
                marker=dict(color="#EF4444", size=10, symbol="triangle-down")
            ))

        # Chart styling for dark mode integration
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(30, 41, 59, 0.2)",
            font=dict(color="#E2E8F0"),
            legend=dict(font=dict(color="#E2E8F0")),
            xaxis=dict(
                showgrid=True,
                gridcolor="rgba(255,255,255,0.05)",
                title="Timestamp (UTC)"
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor="rgba(255,255,255,0.05)",
                title="Price (KES)"
            ),
            margin=dict(l=20, r=20, t=10, b=20),
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Gathering initial historical samples... check back in a few seconds.")

# Right Side: Latest ticker grid
with col_right:
    st.subheader("📁 Live Ticker Monitor")
    monitor_df = df_latest[["ticker", "price", "percent_change", "anomaly_detected", "price_drop_alert"]].copy()
    
    # Format display styling columns
    monitor_df["percent_change"] = monitor_df["percent_change"].apply(lambda x: f"{x:+.2f}%")
    monitor_df["anomaly_detected"] = monitor_df["anomaly_detected"].apply(lambda x: "⚠️ Warning" if x else "✅ Normal")
    monitor_df["price_drop_alert"] = monitor_df["price_drop_alert"].apply(lambda x: "🚨 ALERT" if x else "—")
    
    monitor_df.columns = ["Ticker", "Price (KES)", "Daily Change", "Status", "Drop Alert"]
    
    st.dataframe(
        monitor_df.set_index("Ticker"),
        height=350,
        use_container_width=True
    )

# 3. ALERTS & ANOMALIES LOG ROW
st.markdown("---")
alerts_col, distribution_col = st.columns([1, 1])

with alerts_col:
    st.subheader("🔔 Live Alert & Anomaly Engine Feed")
    
    # Display active price drop alerts
    active_alerts = df_summary.get("active_alerts", [])
    anoms_list = df_summary.get("anomalies", [])
    
    if not active_alerts and not anoms_list:
        st.success("No active anomalies or price drops detected. Market is stable.")
    else:
        for ticker_alert in active_alerts:
            st.markdown(
                f'<div class="alert-ticker-box"><strong>🚨 CRITICAL PRICE DROP ALERT:</strong> '
                f'Ticker <strong>{ticker_alert}</strong> has dropped more than {settings.ALERT_PRICE_DROP_PCT}% '
                f'within its rolling window!</div>',
                unsafe_allow_html=True
            )
            
        for anom in anoms_list:
            st.markdown(
                f'<div class="anomaly-ticker-box"><strong>⚠️ ANOMALY TRIGGERED:</strong> '
                f'Ticker <strong>{anom["ticker"]}</strong> is flagged due to: '
                f'<em>{anom["reason"]}</em>.</div>',
                unsafe_allow_html=True
            )

with distribution_col:
    st.subheader("📊 Stock Daily Return Distribution")
    if not df_latest.empty:
        # Color code returns
        colors = ['#10B981' if x >= 0 else '#EF4444' for x in df_latest['percent_change']]
        
        fig_bar = go.Figure(data=[go.Bar(
            x=df_latest['ticker'],
            y=df_latest['percent_change'],
            marker_color=colors
        )])
        
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(30, 41, 59, 0.2)",
            font=dict(color="#E2E8F0"),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", title="Change (%)"),
            margin=dict(l=20, r=20, t=10, b=20),
            height=250
        )
        st.plotly_chart(fig_bar, use_container_width=True)

# Sleep and rerun natively to refresh
time.sleep(2)
st.rerun()
