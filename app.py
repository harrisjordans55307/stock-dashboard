import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Własne funkcje zamiast pandas-ta
def calculate_rsi(series, period=14):
    delta = series.diff()
    # Upewnij się, że mamy wystarczającą liczbę danych
    if len(delta) < period:
        return pd.Series([None] * len(delta), index=delta.index)
    
    gain = (delta.where(delta > 0, 0)).rolling(window=period, min_periods=1).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period, min_periods=1).mean()
    
    # Unikaj dzielenia przez zero
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_ema(series, period=200):
    # Sprawdź czy mamy wystarczające dane
    if len(series) < period:
        st.warning(f"⚠️ Za mało danych dla EMA {period} (mamy {len(series)} dni)")
        return series.ewm(span=min(period, len(series))).mean()
    return series.ewm(span=period).mean()

st.set_page_config(page_title="Dashboard Giełdowy", layout="wide")

# Sidebar
st.sidebar.title("⚙️ Ustawienia")
symbol = st.sidebar.text_input("Symbol giełdowy", "AAPL")
period = st.sidebar.selectbox("Okres danych", ["1y", "2y", "5y"], index=1)

# Main content
st.title("📊 Dashboard Analizy Technicznej")

# Informacja pomocnicza
st.info("ℹ️ Wpisz symbol giełdowy w panelu bocznym (np. AAPL, GOOGL, MSFT)")

if symbol:
    with st.spinner(f'Pobieram dane dla {symbol}...'):
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval="1d")
            
            if df.empty:
                st.error(f"❌ Nie znaleziono danych dla symbolu: {symbol}")
                st.info("ℹ️ Spróbuj innego symbolu, np. AAPL, GOOGL, MSFT, TSLA")
            else:
                st.success(f"✅ Pobrano {len(df)} dni danych")
                
                # Obliczenia techniczne (własne funkcje)
                df['RSI_14'] = calculate_rsi(df['close'], 14)
                df['EMA_200'] = calculate_ema(df['close'], 200)
                
                # Filtruj tylko ostatnie dane z wartościami
                df_display = df.dropna(subset=['RSI_14', 'EMA_200']).tail(10)
                
                if not df_display.empty:
                    latest = df_display.iloc[-1]
                    
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
                    st.subheader('📋 Ostatnie dane (z obliczeniami technicznymi)')
                    st.dataframe(df_display[['open', 'high', 'low', 'close', 'RSI_14', 'EMA_200']].round(2))
                else:
                    st.warning("⚠️ Za mało danych do obliczenia wskaźników technicznych")
                    st.dataframe(df.tail(10))
                
        except Exception as e:
            st.error(f"❌ Błąd: {str(e)}")
            st.info("ℹ️ Spróbuj innego symbolu lub sprawdź połączenie internetowe")
