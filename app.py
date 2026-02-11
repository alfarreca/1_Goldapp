import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
import textwrap
import time
from twelvedata import TDClient
from google import genai

# --- PAGE CONFIG ---
st.set_page_config(page_title="Gold Command Center", layout="wide", page_icon="🥇")
st.title("🥇 Gold Command Center | February 11, 2026")

# --- CONFIG ---
TD_API_KEY = "cfe2865f704d4d6bb6f5dd759fdee0ff"
GEMINI_API_KEY = "AIzaSyDYSY9rEV2MLwT21s5fjCpdSOtXkyEU_G0"

def get_data():
    td = TDClient(apikey=TD_API_KEY)
    # Fetch 100 periods for accurate ATR averages
    ts = td.time_series(symbol="XAU/USD", interval="15min", outputsize=100)
    df = ts.with_rsi().with_atr().with_ema(time_period=20).as_pandas()
    return df

def get_ai_analysis(row):
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = f"""
    On the first line, provide ONLY the Confidence Score: [0-100].
    Then, provide a 2-sentence 'Strategist Verdict' for Gold at ${row['close']:.2f}.
    RSI is {row['rsi']:.1f} and EMA is ${row['ema']:.2f}.
    """
    response = client.models.generate_content(model="gemini-2.5-flash-lite", contents=prompt)
    text = response.text
    
    # Secure score extraction (Regex fix)
    try:
        score_line = text.split('\n')[0]
        score = int(re.search(r'\d+', score_line).group())
        score = min(score, 100)
    except:
        score = 50
    
    verdict = text.split('\n', 1)[-1].strip().replace('*', '')
    return score, verdict

# --- MAIN LOOP ---
placeholder = st.empty()

while True:
    with placeholder.container():
        df = get_data()
        row = df.iloc[-1]
        
        # Volatility Check
        avg_atr = df['atr'].rolling(window=20).mean().iloc[-1]
        vol_spike = row['atr'] > (avg_atr * 1.20)
        
        score, verdict = get_ai_analysis(row)

        # --- ALERTS ---
        col_a1, col_a2 = st.columns(2)
        if score >= 90:
            col_a1.success("🚀 **GRADE A ENTRY DETECTED**")
        if vol_spike:
            col_a2.warning("🔥 **VOLATILITY SPIKE DETECTED**")

        # --- TOP ROW: CANDLESTICKS ---
        fig_main = go.Figure()
        fig_main.add_trace(go.Candlestick(
            x=df.index, open=df['open'], high=df['high'], 
            low=df['low'], close=df['close'], name="Gold"
        ))
        fig_main.add_trace(go.Scatter(x=df.index, y=df['ema'], line=dict(color='cyan', width=2), name="20 EMA"))
        fig_main.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(t=0, b=0))
        st.plotly_chart(fig_main, use_container_width=True)

        # --- BOTTOM ROW: GAUGE | VERDICT | RSI ---
        c1, c2, c3 = st.columns([1, 2, 1])

        with c1:
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number", value=score,
                title={'text': "CONFIDENCE %", 'font': {'size': 20}},
                number={'font': {'size': 60, 'color': "gold", 'family': "Arial Black"}},
                gauge={'bar': {'color': "gold"}, 'axis': {'range': [0, 100]}}
            ))
            fig_gauge.update_layout(height=300, template="plotly_dark", margin=dict(t=50, b=0))
            st.plotly_chart(fig_gauge, use_container_width=True)

        with c2:
            st.markdown("### 🤖 AI STRATEGIST VERDICT")
            st.info(verdict)
            st.metric("Price", f"${row['close']:.2f}", f"{row['close'] - df.iloc[-2]['close']:.2f}")

        with c3:
            fig_rsi = go.Figure()
            fig_rsi.add_trace(go.Scatter(x=df.index, y=df['rsi'], line=dict(color='purple', width=3)))
            fig_rsi.add_hline(y=70, line_dash="dash", line_color="red")
            fig_rsi.add_hline(y=30, line_dash="dash", line_color="green")
            fig_rsi.update_layout(height=300, template="plotly_dark", title="RSI Momentum", margin=dict(t=50, b=0))
            st.plotly_chart(fig_rsi, use_container_width=True)

    time.sleep(120) # 2-minute sync