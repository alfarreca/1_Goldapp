import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
import time
from twelvedata import TDClient
from google import genai

# --- CONFIG ---
TD_API_KEY = "cfe2865f704d4d6bb6f5dd759fdee0ff"
GEMINI_API_KEY = "AIzaSyDYSY9rEV2MLwT21s5fjCpdSOtXkyEU_G0"
REFRESH_RATE = 120 

st.set_page_config(page_title="Gold Live Sync", layout="wide")

# Dashboard container to prevent flickering
dashboard = st.empty()

def get_synced_data():
    td = TDClient(apikey=TD_API_KEY)
    # Fetch quote for real-time price accuracy
    quote = td.quote(symbol="XAU/USD").as_json()
    live_p = float(quote['close'])
    
    # Fetch series for the chart
    ts = td.time_series(symbol="XAU/USD", interval="15min", outputsize=100)
    df = ts.with_rsi().with_ema(time_period=20).as_pandas()
    
    # Force sync: update last row close with real-time quote
    df.iloc[-1, df.columns.get_loc('close')] = live_p
    return df, live_p

def get_ai_verdict(df, price):
    latest = df.iloc[-1]
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # Strict prompt to ensure verdict matches chart visual
    prompt = f"""
    ANALYSIS PACK:
    - Current Gold Price: ${price:.2f}
    - 20 EMA: ${latest['ema']:.2f}
    - RSI: {latest['rsi']:.1f}
    
    TASK: Give a Confidence Score (0-100) and a 2-sentence verdict.
    STRICT RULE: If Price is BELOW EMA, you MUST be Bearish. If ABOVE, Bullish.
    """
    response = client.models.generate_content(model="gemini-2.5-flash-lite", contents=prompt)
    
    try:
        score = int(re.search(r'\d+', response.text.split('\n')[0]).group())
    except:
        score = 50
    return score, response.text

# --- PERMANENT LOOP ---
while True:
    with dashboard.container():
        try:
            df, live_p = get_synced_data()
            latest = df.iloc[-1]
            score, ai_msg = get_ai_verdict(df, live_p)

            # 🚨 LIVE HEADER
            st.markdown(f"## 🥇 GOLD LIVE: ${live_p:,.2f} | Score: {score}%")
            
            # 📈 CHART (Top)
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="Gold"))
            fig.add_trace(go.Scatter(x=df.index, y=df['ema'], line=dict(color='cyan', width=2), name="20 EMA"))
            fig.update_layout(height=450, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)

            # 📊 METRICS (Bottom)
            c1, c2 = st.columns([1, 2])
            with c1:
                # RSI Small Chart
                fig_rsi = go.Figure(go.Scatter(x=df.index, y=df['rsi'], line=dict(color='purple')))
                fig_rsi.add_hline(y=70, line_color="red"); fig_rsi.add_hline(y=30, line_color="green")
                fig_rsi.update_layout(height=200, template="plotly_dark", title="RSI Momentum", margin=dict(t=30, b=0))
                st.plotly_chart(fig_rsi, use_container_width=True)
            with c2:
                st.info(f"**AI STRATEGIST VERDICT:**\n\n{ai_msg}")
            
            st.caption(f"Last Sync: {pd.Timestamp.now().strftime('%H:%M:%S')} | Environment: Permanent Cloud")

        except Exception as e:
            st.error(f"Connection Sync Issue: {e}")
            time.sleep(10)

    time.sleep(REFRESH_RATE)
