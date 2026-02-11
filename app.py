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

st.set_page_config(page_title="Gold Live Terminal", layout="wide")

# Use a persistent container so the screen doesn't "jump"
dashboard_spot = st.empty()

def fetch_and_analyze():
    # Data Fetching
    td = TDClient(apikey=TD_API_KEY)
    ts = td.time_series(symbol="XAU/USD", interval="15min", outputsize=100)
    df = ts.with_rsi().with_atr().with_ema(time_period=20).as_pandas()
    latest = df.iloc[-1]
    
    # AI Sync
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = f"Price: {latest['close']}, RSI: {latest['rsi']}. Score: [0-100] and 2-sentence bias."
    response = client.models.generate_content(model="gemini-2.5-flash-lite", contents=prompt)
    
    try:
        score = int(re.search(r'\d+', response.text.split('\n')[0]).group())
    except:
        score = 50
    
    return df, score, response.text

# --- THE PERMANENT LOOP ---
while True:
    with dashboard_spot.container():
        df, score, ai_text = fetch_and_analyze()
        latest = df.iloc[-1]
        
        # 🚨 UI HEADER
        st.title(f"🥇 GOLD LIVE: ${latest['close']:.2f}")
        st.caption(f"Last Sync: {pd.Timestamp.now().strftime('%H:%M:%S')}")

        # 📈 MAIN CHART
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close']))
        fig.add_trace(go.Scatter(x=df.index, y=df['ema'], line=dict(color='cyan')))
        fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # 📊 BOTTOM METRICS
        c1, c2 = st.columns([1, 2])
        with c1:
            st.metric("Confidence Score", f"{score}%")
        with c2:
            st.info(f"AI Verdict: {ai_text}")

    # This is the "Engine" that keeps it running
    time.sleep(REFRESH_RATE)
