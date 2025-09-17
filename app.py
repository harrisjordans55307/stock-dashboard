import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go

st.set_page_config(page_title="Dashboard Giełdowy", layout="wide")

# Sidebar
st.sidebar.title("⚙️ Ustawienia")
symbol = st.sidebar.text_input("Symbol giełdowy", "AAPL")
period = st.sidebar.selectbox("Okres danych", ["1y", "2y", "5y"], index=1)

# Main content
st.title("📊 Dashboard Analizy Technicznej")

if symbol:
    with st.spinner(f'Pobieram dane dla {symbol}...'):
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval="1d")
            
            if not df.empty:
                # Obliczenia techniczne
                df.ta.rsi(length=14, append=True)
                df.ta.ema(length=200, append=True)
                
                latest = df.iloc[-1]
                
                # Wyświetlanie metryk
                col1, col2, col3 = st.columns(3)
                col1.metric("📈 Cena", f"${latest['close']:.2f}")
                col2.metric("📊 RSI (14)", f"{latest['RSI_14']:.2f}")
                col3.metric("🟡 EMA 200", f"${latest['EMA_200']:.2f}")
                
                # Wykres
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df.index, y=df['close'], name='Cena zamknięcia', line=dict(color='#1f77b4')))
                fig.add_trace(go.Scatter(x=df.index, y=df['EMA_200'], name='EMA 200', line=dict(color='#ff7f0e')))
                fig.update_layout(title=f'Wykres cen {symbol}', xaxis_title='Data', yaxis_title='Cena ($)', height=500)
                st.plotly_chart(fig, use_container_width=True, theme="streamlit")
                
                # Tabela z danymi
                st.subheader('📋 Ostatnie dane')
                st.dataframe(df[['open', 'high', 'low', 'close', 'RSI_14', 'EMA_200']].tail(10))
                
            else:
                st.error("❌ Nie udało się pobrać danych dla tego symbolu.")
                
        except Exception as e:
            st.error(f"❌ Błąd: {str(e)}")
