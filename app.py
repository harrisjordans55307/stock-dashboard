import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Funkcje pomocnicze
def calculate_rsi(series, period=14):
    delta = series.diff()
    if len(delta) < period:
        return pd.Series([None] * len(delta), index=delta.index)
    
    gain = (delta.where(delta > 0, 0)).rolling(window=period, min_periods=1).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period, min_periods=1).mean()
    
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_ema(series, period=200):
    if len(series) < period:
        return series.ewm(span=min(period, len(series))).mean()
    return series.ewm(span=period).mean()

@st.cache_data
def get_top_symbols_by_volume(symbol_list, top_n=200):
    """Sortuj symbole po wolumenie"""
    symbol_data = []
    
    progress_text = st.empty()
    
    for i, symbol in enumerate(symbol_list[:300]):
        try:
            progress_text.text(f"Analizuję wolumen {symbol}... ({i+1}/300)")
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1mo")
            
            if not hist.empty and len(hist) > 5:
                avg_volume = hist['Volume'].mean()
                current_price = hist['Close'].iloc[-1]
                
                symbol_data.append({
                    'symbol': symbol,
                    'volume': float(avg_volume),
                    'price': float(current_price)
                })
                
        except Exception as e:
            continue
    
    progress_text.empty()
    
    # Posortuj po wolumenie
    symbol_data.sort(key=lambda x: x['volume'], reverse=True)
    
    return [s['symbol'] for s in symbol_data[:top_n]]

def get_nasdaq_symbols():
    """Lista symboli NASDAQ"""
    return [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'AMD', 'INTC', 'ORCL',
        'IBM', 'CSCO', 'ADBE', 'CRM', 'NOW', 'SNOW', 'ZM', 'TEAM', 'OKTA', 'DDOG',
        'JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'BLK', 'SCHW', 'AXP', 'V', 'MA', 'PYPL',
        'JNJ', 'PFE', 'MRK', 'ABBV', 'LLY', 'ABT', 'MDT', 'BMY', 'DHR', 'UNH',
        'WMT', 'KO', 'PEP', 'PG', 'NKE', 'MCD', 'DIS', 'CMCSA', 'NFLX', 'SBUX',
        'XOM', 'CVX', 'COP', 'SLB', 'HAL', 'KMI', 'OXY', 'MPC', 'PSX', 'VLO',
        'BA', 'CAT', 'GE', 'HON', 'LMT', 'MMM', 'UNP', 'UPS', 'FDX', 'CSX',
        'QCOM', 'TXN', 'AVGO', 'INTU', 'ADP', 'FIS', 'FISV', 'CCI', 'AMAT', 'LRCX',
        'KLAC', 'MU', 'WDAY', 'NET', 'CRWD', 'ZS', 'PANW', 'FTNT', 'VRNS', 'CHKP',
        'PLTR', 'SQ', 'ROKU', 'SHOP', 'ETSY', 'SE', 'AFRM', 'U', 'RIVN', 'LCID',
        'VRTX', 'REGN', 'ISRG', 'BIIB', 'GILD', 'VRTX', 'ILMN', 'IDXX', 'ALGN', 'VRTX',
        'COST', 'CMG', 'BKNG', 'VRTX', 'VRTX', 'VRTX', 'VRTX', 'VRTX', 'VRTX', 'VRTX'
    ]

def get_rsi_icon(rsi_value):
    """Zwróć ikonę dla danego zakresu RSI"""
    if 25 <= rsi_value <= 35:
        return "💎"
    elif 35 < rsi_value <= 40:
        return "🟤"
    else:
        return None

def analyze_single_stock(symbol):
    """Analiza pojedynczej spółki"""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="2y", interval="1d")
        
        if not df.empty and len(df) > 20:
            df['rsi'] = calculate_rsi(df['Close'], 14)
            df['ema_200'] = calculate_ema(df['Close'], 200)
            
            latest = df.iloc[-1]
            rsi_icon = get_rsi_icon(latest['rsi'])
            
            if rsi_icon:
                return {
                    'symbol': symbol,
                    'price': round(latest['Close'], 2),
                    'rsi': round(latest['rsi'], 2),
                    'ema_200': round(latest['ema_200'], 2),
                    'icon': rsi_icon,
                    'data': df,
                    'volume': int(df['Volume'].iloc[-1])
                }
        return None
    except:
        return None

def find_diamond_stocks():
    """Znajdź spółki z diamentami z top 200 spółek"""
    # Pobierz top 200 spółek po wolumenie
    all_symbols = get_nasdaq_symbols()
    top_symbols = get_top_symbols_by_volume(all_symbols, 200)
    
    results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, symbol in enumerate(top_symbols):
        try:
            status_text.text(f"🔍 Szukam diamentów: {symbol}... ({i+1}/{len(top_symbols)})")
            progress_bar.progress((i + 1) / len(top_symbols))
            
            result = analyze_single_stock(symbol)
            if result:
                results.append(result)
                
        except Exception as e:
            continue
    
    progress_bar.empty()
    status_text.empty()
    return sorted(results, key=lambda x: x['rsi'])

# UI aplikacji
st.set_page_config(page_title="NASDAQ Diamond Scanner", layout="wide")
st.title("💎 Skaner Diamentów NASDAQ (Top 200)")

# Sidebar
st.sidebar.title("💎 Spółki z diamentami")

if st.sidebar.button("🔍 Szukaj diamentów w top 200", type="primary"):
    with st.spinner("Szukam diamentów w top 200 spółek NASDAQ..."):
        diamond_stocks = find_diamond_stocks()
        
        if diamond_stocks:
            st.success(f"✅ Znaleziono {len(diamond_stocks)} spółek z diamentami!")
            st.session_state.diamond_stocks = diamond_stocks
            
            # Pokaż spółki w sidebarze
            st.sidebar.markdown("---")
            
            # Grupuj po ikonach
            diamonds_25_35 = [s for s in diamond_stocks if s['icon'] == '💎']
            browns_35_40 = [s for s in diamond_stocks if s['icon'] == '🟤']
            
            if diamonds_25_35:
                st.sidebar.markdown("**💎 RSI 25-35 (najlepsze okazje):**")
                for stock in diamonds_25_35:
                    if st.sidebar.button(f"{stock['icon']} {stock['symbol']} (RSI: {stock['rsi']})"):
                        st.session_state.selected_stock = stock
            
            if browns_35_40:
                st.sidebar.markdown("**🟤 RSI 35-40 (dobre okazje):**")
                for stock in browns_35_40:
                    if st.sidebar.button(f"{stock['icon']} {stock['symbol']} (RSI: {stock['rsi']})"):
                        st.session_state.selected_stock = stock
            
            # Statystyki
            col1, col2, col3 = st.columns(3)
            col1.metric("💎 Diamenty (25-35)", len(diamonds_25_35))
            col2.metric("🟤 Brązowe (35-40)", len(browns_35_40))
            col3.metric("📈 Średni RSI", f"{np.mean([s['rsi'] for s in diamond_stocks]):.1f}")
            
        else:
            st.info("ℹ️ Nie znaleziono spółek z RSI w zakresie 25-40")

# Pokaż szczegółową analizę wybranej spółki
if 'selected_stock' in st.session_state:
    stock = st.session_state.selected_stock
    st.markdown("---")
    st.subheader(f"{stock['icon']} Szczegółowa analiza: {stock['symbol']}")
    
    # Metryki
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📈 Aktualna cena", f"${stock['price']}")
    col2.metric("📊 RSI (14)", stock['rsi'])
    col3.metric("🟡 EMA 200", f"${stock['ema_200']}")
    col4.metric("📊 Wolumen", f"{stock['volume']:,}")
    
    # Wykres świecowy z EMA200
    df = stock['data']
    fig = go.Figure()
    
    # Wykres świecowy
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='Świeczki'
    ))
    
    # EMA 200
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['ema_200'],
        name='EMA 200',
        line=dict(color='orange', width=2)
    ))
    
    fig.update_layout(
        title=f'Wykres świecowy {stock["symbol"]} z EMA 200',
        xaxis_title='Data',
        yaxis_title='Cena ($)',
        height=600,
        xaxis_rangeslider_visible=False
    )
    st.plotly_chart(fig, use_container_width=True, theme="streamlit")
    
    # Wykres RSI
    fig_rsi = go.Figure()
    fig_rsi.add_trace(go.Scatter(x=df.index, y=df['rsi'], name='RSI (14)', line=dict(color='purple', width=2)))
    fig_rsi.add_trace(go.Scatter(x=df.index, y=[30]*len(df), name='Oversold (30)', line=dict(color='green', dash='dash')))
    fig_rsi.add_trace(go.Scatter(x=df.index, y=[70]*len(df), name='Overbought (70)', line=dict(color='red', dash='dash')))
    fig_rsi.add_trace(go.Scatter(x=df.index, y=[25]*len(df), name='Super Oversold (25)', line=dict(color='darkgreen', dash='dot')))
    fig_rsi.add_trace(go.Scatter(x=df.index, y=[40]*len(df), name='Górna granica (40)', line=dict(color='orange', dash='dot')))
    fig_rsi.update_layout(title=f'RSI {stock["symbol"]}', xaxis_title='Data', yaxis_title='RSI', height=300)
    st.plotly_chart(fig_rsi, use_container_width=True, theme="streamlit")

# Informacje początkowe
else:
    st.info("ℹ️ Kliknij 'Szukaj diamentów w top 200' w panelu bocznym, aby rozpocząć skanowanie")
    st.markdown("""
    **💎 Jak to działa:**
    - Skanujemy top 200 spółek NASDAQ wg wolumenu
    - Szukamy spółek z RSI w zakresie 25-40
    - 💎 RSI 25-35 = najlepsze okazje (oversold)
    - 🟤 RSI 35-40 = dobre okazje
    - Kliknij spółkę, aby zobaczyć wykres świecowy z EMA200!
    """)

# Legenda
st.sidebar.markdown("---")
st.sidebar.info("""
**_legenda:_
- 💎 RSI 25-35 = potencjalne oversold
- 🟤 RSI 35-40 = lekko oversold
""")
