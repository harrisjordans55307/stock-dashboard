import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from nasdaq_screener import Screener

# --- Konfiguracja strony ---
st.set_page_config(
    page_title="💎 NASDAQ Diamond Scanner",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS ---
st.markdown("""
<style>
    .diamond-header {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# --- Funkcje Pomocnicze ---

@st.cache_data(ttl=3600) # Cache'owanie przez 1 godzinę
def get_all_nasdaq_symbols():
    """Pobiera dynamicznie listę symboli z NASDAQ i dodaje kluczowe spółki jako zapas."""
    try:
        screener = Screener()
        data, _ = screener.get_main_content()
        nasdaq_symbols = list(data.symbol.unique())
        print(f"Pobrano dynamicznie {len(nasdaq_symbols)} symboli z NASDAQ.")
    except Exception as e:
        print(f"Nie udało się dynamicznie pobrać listy NASDAQ, używam listy zapasowej. Błąd: {e}")
        nasdaq_symbols = []

    fallback_list = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'AMD', 'INTC', 'ORCL',
        'IBM', 'CSCO', 'ADBE', 'CRM', 'NOW', 'SNOW', 'ZM', 'TEAM', 'OKTA', 'DDOG',
        'QCOM', 'TXN', 'AVGO', 'AMAT', 'LRCX', 'KLAC', 'MU', 'MCHP', 'ADI', 'MRVL',
        'JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'BLK', 'SCHW', 'AXP', 'V', 'MA', 'PYPL',
        'SQ', 'AFRM', 'SOFI', 'HOOD', 'COIN', 'ALLY', 'FIS', 'FISV',
        'JNJ', 'PFE', 'MRK', 'ABBV', 'LLY', 'ABT', 'MDT', 'BMY', 'UNH',
        'GILD', 'AMGN', 'BIIB', 'REGN', 'VRTX', 'MRNA', 'BNTX',
        'WMT', 'KO', 'PEP', 'PG', 'NKE', 'MCD', 'SBUX', 'COST', 'TGT', 'HD',
        'EBAY', 'ETSY', 'SHOP', 'ROKU', 'NFLX', 'DIS', 'CMCSA', 'TMUS'
    ]
    
    combined_list = nasdaq_symbols + fallback_list
    unique_symbols = sorted(list(set(combined_list)))
    return unique_symbols


@st.cache_data(ttl=600)
def analyze_single_stock(symbol, rsi_threshold_max=40):
    """Analizuje pojedynczą spółkę"""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1y", interval="1d", auto_adjust=True)
        
        if df.empty or len(df) < 200:
            return None
            
        # Oblicz wskaźniki używając pandas_ta
        df.ta.rsi(length=14, append=True)
        df.ta.ema(length=200, append=True)
        df.ta.sma(length=20, column='Volume', append=True)
        
        latest = df.iloc[-1]
        
        # Zmienione nazwy kolumn z pandas_ta
        latest_rsi = latest.get('RSI_14')
        latest_ema_200 = latest.get('EMA_200')
        latest_volume_sma = latest.get('VOLUMEsma_20')

        if pd.isna(latest_rsi) or latest_rsi > rsi_threshold_max or latest_rsi < 25:
            return None
            
        # Określ kategorię
        if 25 <= latest_rsi <= 35:
            category, icon = "diamond", "💎"
        elif 35 < latest_rsi <= 40:
            category, icon = "brown", "🟤"
        else:
            return None
            
        # Pobierz podstawowe informacje
        try:
            info = ticker.info
            market_cap = info.get('marketCap', 0)
            sector = info.get('sector', 'N/A')
        except:
            market_cap, sector = 0, 'N/A'
        
        volume_ratio = latest['Volume'] / latest_volume_sma if latest_volume_sma > 0 else 1
        
        return {
            'symbol': symbol, 'price': round(latest['Close'], 2),
            'rsi': round(latest_rsi, 2), 'ema_200': round(latest_ema_200, 2),
            'volume': int(latest['Volume']), 'avg_volume': int(latest_volume_sma),
            'volume_ratio': round(volume_ratio, 1), 'market_cap': market_cap,
            'sector': sector, 'category': category, 'icon': icon, 'data': df
        }
    except Exception:
        return None

def find_diamond_stocks(rsi_max=40, min_market_cap=0, max_market_cap=float('inf')):
    """Skanuje spółki w poszukiwaniu 'diamentów'"""
    all_symbols = get_all_nasdaq_symbols()
    
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Skanujemy tylko pierwsze 500 symboli dla wydajności
    symbols_to_scan = all_symbols[:500]
    total = len(symbols_to_scan)

    for i, symbol in enumerate(symbols_to_scan):
        status_text.text(f"🔍 Analizuję {symbol}... ({i+1}/{total})")
        progress_bar.progress((i + 1) / total)
        
        result = analyze_single_stock(symbol, rsi_threshold_max=rsi_max)
        if result and min_market_cap <= result['market_cap'] <= max_market_cap:
            results.append(result)
            
    progress_bar.empty()
    status_text.empty()
    
    return sorted(results, key=lambda x: x['rsi'])

# Tutaj reszta kodu UI (wykresy, tabelki), która była w Twojej wersji.
# ... (skopiuj całą resztę Twojego kodu od 'def create_candlestick_chart' do samego końca) ...
# Poniżej wklejam resztę dla kompletności

def create_candlestick_chart(stock_data):
    df = stock_data['data'].tail(120)
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name=stock_data['symbol']))
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_200'], name='EMA 200', line=dict(color='orange', width=2)))
    fig.update_layout(title=f"{stock_data['icon']} {stock_data['symbol']} - RSI: {stock_data['rsi']}", yaxis_title='Cena ($)', height=500, xaxis_rangeslider_visible=False)
    return fig

def create_rsi_chart(stock_data):
    df = stock_data['data'].tail(120)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI_14'], name='RSI (14)'))
    fig.add_hline(y=30, line_dash="dash", line_color="green")
    fig.add_hline(y=70, line_dash="dash", line_color="red")
    fig.update_layout(title=f"RSI dla {stock_data['symbol']}", yaxis_title='RSI', height=300, yaxis=dict(range=[0, 100]))
    return fig

# --- UI Aplikacji ---
st.markdown("<div class='diamond-header'><h1>💎 NASDAQ Diamond Scanner</h1><p>Analiza spółek NASDAQ - RSI 25-40</p></div>", unsafe_allow_html=True)

with st.sidebar:
    st.header("🎯 Filtry")
    rsi_max = st.slider("Max RSI", 25, 40, 40, 1)
    
    st.subheader("Kapitalizacja")
    min_cap_billions = st.number_input("Min (mld $)", min_value=0, value=0, step=1)
    min_market_cap = min_cap_billions * 1e9
    
    if st.button("🔍 Skanuj teraz", type="primary", use_container_width=True):
        st.session_state.selected_stock = None
        with st.spinner("🚀 Skanuję giełdę..."):
            diamond_stocks = find_diamond_stocks(rsi_max=rsi_max, min_market_cap=min_market_cap)
            st.session_state.diamond_stocks = diamond_stocks
        if diamond_stocks:
            st.success(f"✅ Znaleziono {len(diamond_stocks)} spółek!")
            st.balloons()
        else:
            st.warning("⚠️ Brak spółek spełniających kryteria")

if 'diamond_stocks' in st.session_state:
    stocks = st.session_state.diamond_stocks
    
    col1, col2 = st.columns(2)
    diamonds = len([s for s in stocks if s['category'] == 'diamond'])
    browns = len([s for s in stocks if s['category'] == 'brown'])
    col1.metric("💎 RSI 25-35", diamonds)
    col2.metric("🟤 RSI 35-40", browns)
    
    st.subheader("📋 Znalezione spółki")
    for s in stocks:
        if st.button(f"{s['icon']} {s['symbol']} (RSI: {s['rsi']})"):
            st.session_state.selected_stock = s
            st.rerun()

if 'selected_stock' in st.session_state and st.session_state.selected_stock:
    stock = st.session_state.selected_stock
    st.markdown("---")
    st.subheader(f"{stock['icon']} {stock['symbol']} - Szczegółowa analiza")
    
    tab1, tab2 = st.tabs(["📊 Wykres Ceny", "📈 Wykres RSI"])
    with tab1:
        st.plotly_chart(create_candlestick_chart(stock), use_container_width=True)
    with tab2:
        st.plotly_chart(create_rsi_chart(stock), use_container_width=True)
else:
    st.info("🚀 Kliknij 'Skanuj teraz' w panelu bocznym, aby rozpocząć analizę")
