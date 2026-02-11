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
REFRESH_RATE = 60 # Faster refresh to catch price moves

st.set_page_config(page_title="Gold Real-Time Terminal", layout="wide")

dashboard_spot = st.empty()

def fetch_realtime_data():
    td = TDClient(apikey=TD_API_KEY)
    
    # 1. Fetch the Live Quote (Price right now)
    quote = td.quote(symbol="XAU/USD").as_json()
    live_price = float(quote['close'])
    
    # 2. Fetch the Time Series (The Chart)
    ts = td.time_series(symbol="XAU/USD", interval="15min", outputsize=100)
    df = ts.with_rsi().with_ema(time_period=20).as_pandas()
    
    # 3. CRITICAL SYNC: Replace the last row's close with the Real-Time Quote
    # This ensures your chart doesn't "lag" behind eToro
    df.iloc[-1, df.columns.get_loc('close')] = live_price
    
    return df, live_price

def get_ai_sync(price, rsi, ema):
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = f"LIVE GOLD PRICE: ${price}. RSI: {rsi:.1f}. EMA: {ema:.2f}. Give 0-100 Score and 1-sentence bias."
    response = client.models.generate_content(model="gemini-2.5-flash-lite", contents=prompt)
    
    try:
        score = int(re.search(r'\d+', response.text.split('\n')[0]).group())
    except:
        score = 50
    return score, response.text

# --- THE PERMANENT LOOP ---
while True:
    with dashboard_spot.container():
        try:
            df, live_price = fetch_realtime_data()
            latest = df.iloc[-1]
            
            score, ai_verdict = get_ai_sync(live_price, latest['rsi'], latest['ema'])

            # 🚨 LIVE PRICE HEADER (Huge and Bold)
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                st.markdown(f"# 🥇 XAU/USD: ${live_price:,.2f}")
            with c2:
                st.metric("EMA Divergence", f"{live_price - latest['ema']:.2f}")
            with c3:
                st.metric("Confidence", f"{score}%")

            # 📈 CHART
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close']))
            fig.add_trace(go.Scatter(x=df.index, y=df['ema'], line=dict(color='cyan')))
            fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)

            st.info(f"**AI VERDICT:** {ai_verdict}")
            st.caption(f"Last Server Sync: {pd.Timestamp.now().strftime('%H:%M:%S')} (Real-time Endpoint)")

        except Exception as e:
            st.error(f"Sync Error: {e}")

    time.sleep(REFRESH_RATE)
