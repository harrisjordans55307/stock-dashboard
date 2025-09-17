import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

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
def get_nasdaq_symbols():
    """Lista popularnych symboli NASDAQ"""
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
        'PLTR', 'SQ', 'ROKU', 'SHOP', 'ETSY', 'SE', 'AFRM', 'U', 'RIVN', 'LCID'
    ]

def get_rsi_icon(rsi_value):
    """Zwróć ikonę dla danego zakresu RSI"""
    if 25 <= rsi_value <= 35:
        return "💎"  # Srebrny diament
    elif 35 < rsi_value <= 40:
        return "🟤"  # Brązowy
    else:
        return None  # Nie wyświetlaj

def analyze_single_stock(symbol):
    """Analiza pojedynczej spółki"""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="2y", interval="1d")
        
        if not df.empty:
            df['rsi'] = calculate_rsi(df['Close'], 14)
            df['ema_200'] = calculate_ema(df['Close'], 200)
            
            latest = df.iloc[-1]
            rsi_icon = get_rsi_icon(latest['rsi'])
            
            if rsi_icon:  # Pokazuj tylko spółki z ikonami
                return {
                    'symbol': symbol,
                    'price': round(latest['Close'], 2),
                    'rsi': round(latest['rsi'], 2),
                    'ema_200': round(latest['ema_200'], 2),
                    'icon': rsi_icon,
                    'data': df
                }
        return None
    except:
        return None

def find_diamond_stocks(symbols):
    """Znajdź tylko spółki z diamentami (RSI 25-40)"""
    results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, symbol in enumerate(symbols):
        try:
            status_text.text(f"🔍 Sprawdzam {symbol}... ({i+1}/{len(symbols)})")
            progress_bar.progress((i + 1) / len(symbols))
            
            result = analyze_single_stock(symbol)
            if result:
                results.append(result)
                
        except Exception as e:
            continue
    
    progress_bar.empty()
    status_text.empty()
    return sorted(results, key=lambda x: x['rsi'])  # Sortuj po RSI

# UI aplikacji
st.set_page_config(page_title="NASDAQ Diamond Scanner", layout="wide")
st.title("💎 Skaner Diamentów NASDAQ")

# Sidebar - tylko spółki z diamentami
st.sidebar.title("💎 Spółki z diamentami (RSI 25-40)")

# Pobierz i analizuj spółki
symbols = get_nasdaq_symbols()

if st.sidebar.button("🔍 Szukaj diamentów", type="primary"):
    with st.spinner("Szukam diamentów na rynku..."):
        diamond_stocks = find_diamond_stocks(symbols)
        
        if diamond_stocks:
            st.success(f"✅ Znaleziono {len(diamond_stocks)} spółek z diamentami!")
            
            # Pokaż spółki w sidebarze
            st.sidebar.markdown("---")
            st.sidebar.subheader("Lista diamentów:")
            
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
            
            # Pokaż statystyki
            col1, col2, col3 = st.columns(3)
            col1.metric("💎 Diamenty (25-35)", len(diamonds_25_35))
            col2.metric("🟤 Brązowe (35-40)", len(browns_35_40))
            col3.metric("📈 Średni RSI", f"{np.mean([s['rsi'] for s in diamond_stocks]):.1f}")
            
            # Pokaż tabelę wszystkich znalezionych
            st.subheader("📋 Wszystkie znalezione diamenty:")
            df_display = pd.DataFrame([
                {
                    'Symbol': f"{stock['icon']} {stock['symbol']}",
                    'RSI': stock['rsi'],
                    'Cena': f"${stock['price']}",
                    'EMA 200': f"${stock['ema_200']}"
                }
                for stock in diamond_stocks
            ])
            st.dataframe(df_display, use_container_width=True)
            
        else:
            st.info("ℹ️ Nie znaleziono spółek z RSI w zakresie 25-40")

# Pokaż szczegółową analizę wybranej spółki
if 'selected_stock' in st.session_state:
    stock = st.session_state.selected_stock
    st.markdown("---")
    st.subheader(f"{stock['icon']} Szczegółowa analiza: {stock['symbol']}")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("📈 Aktualna cena", f"${stock['price']}")
    col2.metric("📊 RSI (14)", stock['rsi'])
    col3.metric("🟡 EMA 200", f"${stock['ema_200']}")
    
    # Wykres
    df = stock['data']
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name='Cena zamknięcia', line=dict(color='#1f77b4')))
    fig.add_trace(go.Scatter(x=df.index, y=df['ema_200'], name='EMA 200', line=dict(color='#ff7f0e')))
    fig.add_trace(go.Scatter(x=df.index, y=[30]*len(df), name='RSI 30 (obszar oversold)', line=dict(color='green', dash='dash')))
    fig.add_trace(go.Scatter(x=df.index, y=[70]*len(df), name='RSI 70 (obszar overbought)', line=dict(color='red', dash='dash')))
    fig.update_layout(title=f'Wykres cen {stock["symbol"]}', xaxis_title='Data', yaxis_title='Cena ($)', height=500)
    st.plotly_chart(fig, use_container_width=True, theme="streamlit")
    
    # Wykres RSI
    fig_rsi = go.Figure()
    fig_rsi.add_trace(go.Scatter(x=df.index, y=df['rsi'], name='RSI (14)', line=dict(color='purple')))
    fig_rsi.add_trace(go.Scatter(x=df.index, y=[30]*len(df), name='Oversold (30)', line=dict(color='green', dash='dash')))
    fig_rsi.add_trace(go.Scatter(x=df.index, y=[70]*len(df), name='Overbought (70)', line=dict(color='red', dash='dash')))
    fig_rsi.add_trace(go.Scatter(x=df.index, y=[25]*len(df), name='Super Oversold (25)', line=dict(color='darkgreen', dash='dot')))
    fig_rsi.add_trace(go.Scatter(x=df.index, y=[40]*len(df), name='Górna granica (40)', line=dict(color='orange', dash='dot')))
    fig_rsi.update_layout(title=f'RSI {stock["symbol"]}', xaxis_title='Data', yaxis_title='RSI', height=300)
    st.plotly_chart(fig_rsi, use_container_width=True, theme="streamlit")

# Informacje początkowe
else:
    st.info("ℹ️ Kliknij 'Szukaj diamentów' w panelu bocznym, aby rozpocząć skanowanie")
    st.markdown("""
    **💎 Jak to działa:**
    - Szukamy spółek z RSI w zakresie 25-40
    - 💎 RSI 25-35 = najlepsze okazje (oversold)
    - 🟤 RSI 35-40 = dobre okazje
    - Pokazujemy tylko spółki z ikonami!
    """)

# Legenda w sidebarze
st.sidebar.markdown("---")
st.sidebar.info("""
**_legenda:_
- 💎 RSI 25-35 = potencjalne oversold
- 🟤 RSI 35-40 = lekko oversold
""")
