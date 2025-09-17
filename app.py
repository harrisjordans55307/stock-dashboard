import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# Konfiguracja strony
st.set_page_config(
    page_title="💎 NASDAQ Diamond Scanner", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .diamond-header {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 1rem;
    }
    .stock-button {
        margin: 0.2rem 0;
        font-size: 12px;
        padding: 0.2rem 0.5rem;
        height: 50px;
    }
</style>
""", unsafe_allow_html=True)

# Funkcje pomocnicze
@st.cache_data(ttl=300)
def calculate_rsi(series, period=14):
    """Oblicza RSI z poprawnym wygładzaniem"""
    delta = series.diff(1)
    if len(delta) < period:
        return pd.Series([np.nan] * len(series), index=series.index)
    
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.ewm(com=period-1, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(com=period-1, min_periods=period, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

@st.cache_data(ttl=300)
def calculate_ema(series, period=200):
    """Oblicza EMA"""
    return series.ewm(span=period, adjust=False, min_periods=1).mean()

@st.cache_data(ttl=600)
def get_all_nasdaq_symbols():
    """Rozszerzona lista symboli NASDAQ"""
    return [
        # Tech Giants & Popular
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'AMD', 'INTC', 'ORCL',
        'IBM', 'CSCO', 'ADBE', 'CRM', 'NOW', 'SNOW', 'ZM', 'TEAM', 'OKTA', 'DDOG',
        'QCOM', 'TXN', 'AVGO', 'AMAT', 'LRCX', 'KLAC', 'MU', 'MCHP', 'ADI', 'MRVL',
        
        # Finance
        'JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'BLK', 'SCHW', 'AXP', 'V', 'MA', 'PYPL',
        'SQ', 'AFRM', 'SOFI', 'HOOD', 'COIN', 'ALLY', 'FIS', 'FISV',
        
        # Healthcare
        'JNJ', 'PFE', 'MRK', 'ABBV', 'LLY', 'ABT', 'MDT', 'BMY', 'UNH',
        'GILD', 'AMGN', 'BIIB', 'REGN', 'VRTX', 'MRNA', 'BNTX',
        
        # Consumer
        'WMT', 'KO', 'PEP', 'PG', 'NKE', 'MCD', 'SBUX', 'COST', 'TGT', 'HD',
        'EBAY', 'ETSY', 'SHOP', 'ROKU', 'NFLX', 'DIS', 'CMCSA', 'TMUS',
        
        # Energy
        'XOM', 'CVX', 'COP', 'SLB', 'HAL', 'KMI', 'OXY', 'MPC', 'PSX', 'VLO',
        
        # Industrial
        'BA', 'CAT', 'GE', 'HON', 'LMT', 'MMM', 'UNP', 'UPS', 'FDX',
        'F', 'GM', 'RIVN', 'LCID',
        
        # Software & Communication
        'INTU', 'ADP', 'WDAY', 'VEEV', 'TWLO', 'DOCU', 'PLTR', 'U', 'RBLX',
        'UBER', 'LYFT', 'DASH', 'ABNB', 'ZS', 'CRWD', 'PANW', 'FTNT',
        'CCI', 'AMT', 'VZ', 'T', 'SPOT', 'PINS', 'SNAP',
        
        # More stocks for better coverage
        'DE', 'RTX', 'NOC', 'GD', 'CSX', 'NSC', 'ODFL', 'EXPD',
        'LOW', 'BBY', 'DG', 'DLTR', 'CHTR', 'ROKU', 'TTD', 'SQ',
        'NVST', 'STNE', 'BILL', 'TTD', 'ZEN', 'NET', 'ESTC',
        'DDOG', 'MDB', 'SNOW', 'CRWD', 'ZS', 'PANW', 'FTNT',
        'VEEV', 'TWLO', 'OKTA', 'DOCU', 'TEAM', 'NOW', 'SNPS',
        'CDNS', 'ANSS', 'MSCI', 'MTCH', 'BIDU', 'JD', 'NTES'
    ]

@st.cache_data(ttl=300)
def get_top_symbols_by_volume(symbol_list, top_n=500):
    """Sortuj symbole po wolumenie"""
    symbol_data = []
    
    progress_text = st.empty()
    
    # Sprawdź pierwsze 600 symboli dla lepszego pokrycia
    for i, symbol in enumerate(symbol_list[:600]):
        try:
            progress_text.text(f"Analizuję wolumen {symbol}... ({i+1}/600)")
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

@st.cache_data(ttl=300)
def analyze_single_stock(symbol, rsi_threshold_max=40):
    """Analizuje pojedynczą spółkę - poprawiona wersja"""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1y", interval="1d")
        
        if df.empty or len(df) < 50:
            return None
            
        # Oblicz wskaźniki
        df['rsi'] = calculate_rsi(df['Close'], 14)
        df['ema_200'] = calculate_ema(df['Close'], 200)
        df['volume_sma'] = df['Volume'].rolling(20).mean()
        
        latest = df.iloc[-1]
        
        # Sprawdź czy RSI jest w interesującym zakresie (25-40)
        if pd.isna(latest['rsi']) or latest['rsi'] > rsi_threshold_max or latest['rsi'] < 25:
            return None
            
        # Określ kategorię (tylko 25-40)
        if 25 <= latest['rsi'] <= 35:
            category = "diamond"
            icon = "💎"
        elif 35 < latest['rsi'] <= 40:
            category = "brown"
            icon = "🟤"
        else:
            return None
            
        # Pobierz podstawowe informacje
        try:
            info = ticker.info
            market_cap = info.get('marketCap', 0)
            sector = info.get('sector', 'N/A')
        except:
            market_cap = 0
            sector = 'N/A'
        
        volume_ratio = latest['Volume'] / latest['volume_sma'] if latest['volume_sma'] > 0 else 1
        
        return {
            'symbol': symbol,
            'price': round(latest['Close'], 2),
            'rsi': round(latest['rsi'], 2),
            'ema_200': round(latest['ema_200'], 2),
            'volume': int(latest['Volume']),
            'avg_volume': int(latest['volume_sma']),
            'volume_ratio': round(volume_ratio, 1),
            'market_cap': market_cap,
            'sector': sector,
            'category': category,
            'icon': icon,
            'data': df
        }
        
    except Exception as e:
        return None

def find_diamond_stocks(rsi_max=40, min_market_cap=0, max_market_cap=float('inf')):
    """Znajdź diamenty - analiza top 500 spółek"""
    # Pobierz top 500 spółek po wolumenie
    all_symbols = get_all_nasdaq_symbols()
    top_symbols = get_top_symbols_by_volume(all_symbols, 500)
    
    results = []
    processed_symbols = set()  # Unikaj duplikatów
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, symbol in enumerate(top_symbols):
        try:
            # Unikaj duplikatów
            if symbol in processed_symbols:
                continue
            processed_symbols.add(symbol)
            
            status_text.text(f"🔍 Analizuję {symbol}... ({i+1}/{len(top_symbols)})")
            progress = (i + 1) / len(top_symbols)
            progress_bar.progress(progress)
            
            result = analyze_single_stock(symbol, rsi_threshold_max=rsi_max)
            if result:
                # Sprawdź filtry kapitalizacji
                if result['market_cap'] >= min_market_cap:
                    if max_market_cap == float('inf') or result['market_cap'] <= max_market_cap:
                        results.append(result)
                
        except Exception as e:
            continue
    
    progress_bar.empty()
    status_text.empty()
    
    return sorted(results, key=lambda x: x['rsi'])

def create_candlestick_chart(stock_data):
    """Wykres świecowy z EMA200"""
    df = stock_data['data'].tail(120)
    
    fig = go.Figure()
    
    # Wykres świecowy
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name=stock_data['symbol']
    ))
    
    # EMA 200
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['ema_200'],
        name='EMA 200',
        line=dict(color='orange', width=2)
    ))
    
    fig.update_layout(
        title=f"{stock_data['icon']} {stock_data['symbol']} - RSI: {stock_data['rsi']}",
        xaxis_title='Data',
        yaxis_title='Cena ($)',
        height=500,
        xaxis_rangeslider_visible=False
    )
    
    return fig

def create_rsi_chart(stock_data):
    """Wykres RSI"""
    df = stock_data['data'].tail(120)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['rsi'], name='RSI (14)'))
    fig.add_hline(y=30, line_dash="dash", line_color="green")
    fig.add_hline(y=70, line_dash="dash", line_color="red")
    fig.add_hline(y=25, line_dash="dot", line_color="darkgreen")
    fig.add_hline(y=40, line_dash="dot", line_color="orange")
    
    fig.update_layout(
        title=f"RSI dla {stock_data['symbol']}",
        xaxis_title='Data',
        yaxis_title='RSI',
        height=300,
        yaxis=dict(range=[0, 100])
    )
    
    return fig

# UI Aplikacji
st.markdown("<div class='diamond-header'><h1>💎 NASDAQ Diamond Scanner</h1><p>Analiza top 500 spółek NASDAQ - RSI 25-40</p></div>", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("🎯 Filtry")
    
    # RSI
    rsi_max = st.slider("Max RSI", 25, 40, 40, 1)
    
    # Kapitalizacja
    st.subheader("Kapitalizacja")
    col1, col2 = st.columns(2)
    with col1:
        min_cap_billions = st.number_input("Min (mld $)", min_value=0, value=0, step=1)
        min_market_cap = min_cap_billions * 1e9
    with col2:
        max_cap_billions = st.number_input("Max (mld $)", min_value=0, value=1000, step=10)
        max_market_cap = max_cap_billions * 1e9 if max_cap_billions > 0 else float('inf')
    
    # Sektor
    sectors = ['Wszystkie'] + sorted(set([s.get('sector', 'N/A') for s in st.session_state.get('diamond_stocks', []) if s.get('sector')]))
    selected_sector = st.selectbox("Sektor", sectors)
    
    # Analiza pojedynczego symbolu
    st.subheader("🔍 Szybka analiza")
    custom_symbol = st.text_input("Symbol", "")
    if custom_symbol and st.button("Analizuj symbol"):
        with st.spinner(f"Analizuję {custom_symbol.upper()}..."):
            result = analyze_single_stock(custom_symbol.upper(), rsi_threshold_max=50)
            if result:
                st.session_state.selected_stock = result
                st.success(f"✅ Znaleziono {custom_symbol.upper()}")
            else:
                st.error("❌ Nie znaleziono danych")
    
    # Przycisk skanowania
    st.markdown("---")
    if st.button("🔍 Skanuj teraz", type="primary", use_container_width=True):
        with st.spinner("🚀 Analizuję top 500 spółek NASDAQ..."):
            diamond_stocks = find_diamond_stocks(
                rsi_max=rsi_max,
                min_market_cap=min_market_cap,
                max_market_cap=max_market_cap
            )
            
            # Filtruj po sektorze
            if selected_sector != "Wszystkie" and diamond_stocks:
                diamond_stocks = [s for s in diamond_stocks if s['sector'] == selected_sector]
            
            if diamond_stocks:
                st.success(f"✅ Znaleziono {len(diamond_stocks)} spółek z RSI 25-{rsi_max}!")
                st.session_state.diamond_stocks = diamond_stocks
                st.balloons()
            else:
                st.warning("⚠️ Brak spółek spełniających kryteria")

# Wyświetlanie wyników
if 'diamond_stocks' in st.session_state:
    stocks = st.session_state.diamond_stocks
    
    # Statystyki
    col1, col2, col3 = st.columns(3)
    diamonds = len([s for s in stocks if s['category'] == 'diamond'])
    browns = len([s for s in stocks if s['category'] == 'brown'])
    
    col1.metric("💎 RSI 25-35", diamonds)
    col2.metric("🟤 RSI 35-40", browns)
    col3.metric("📊 Razem", len(stocks))
    
    # Tabela wyników
    st.subheader("📋 Znalezione spółki")
    
    # Filtruj i sortuj
    if selected_sector != "Wszystkie":
        display_stocks = [s for s in stocks if s['sector'] == selected_sector]
    else:
        display_stocks = stocks
    
    table_data = []
    for s in display_stocks:
        # Formatowanie kapitalizacji
        if s['market_cap'] > 0:
            if s['market_cap'] >= 1e12:
                market_cap_str = f"${s['market_cap']/1e12:.1f}T"
            elif s['market_cap'] >= 1e9:
                market_cap_str = f"${s['market_cap']/1e9:.1f}B"
            elif s['market_cap'] >= 1e6:
                market_cap_str = f"${s['market_cap']/1e6:.1f}M"
            else:
                market_cap_str = f"${s['market_cap']:,.0f}"
        else:
            market_cap_str = "N/A"
        
        # Opis wolumenu
        if s['volume_ratio'] > 2.0:
            vol_desc = "🔥 Bardzo wysoki"
        elif s['volume_ratio'] > 1.5:
            vol_desc = "📈 Wysoki"
        elif s['volume_ratio'] > 1.0:
            vol_desc = "📊 Normalny"
        elif s['volume_ratio'] > 0.5:
            vol_desc = "📉 Niski"
        else:
            vol_desc = "❄️ Bardzo niski"
        
        table_data.append({
            'Symbol': f"{s['icon']} {s['symbol']}",
            'Cena': f"${s['price']}",
            'RSI': f"{s['rsi']}",
            'EMA200': f"${s['ema_200']}",
            'Kapitalizacja': market_cap_str,
            'Vol ratio': f"{s['volume_ratio']}x ({vol_desc})"
        })
    
    df_display = pd.DataFrame(table_data)
    st.dataframe(df_display, use_container_width=True, height=400)
    
    # Przyciski spółek (unikaj duplikatów)
    st.subheader("💎 Kliknij spółkę do analizy")
    
    # Grupuj po ikonach
    diamond_stocks_list = [s for s in display_stocks if s['category'] == 'diamond']
    brown_stocks_list = [s for s in display_stocks if s['category'] == 'brown']
    
    if diamond_stocks_list:
        st.markdown("**💎 RSI 25-35 (najlepsze okazje):**")
        cols = st.columns(6)
        for i, stock in enumerate(diamond_stocks_list):
            col = cols[i % 6]
            button_key = f"diamond_btn_{stock['symbol']}_{i}"
            if col.button(f"{stock['icon']} {stock['symbol']}\nRSI: {stock['rsi']}", key=button_key, help=f"Analiza {stock['symbol']}"):
                st.session_state.selected_stock = stock
                st.rerun()
    
    if brown_stocks_list:
        st.markdown("**🟤 RSI 35-40 (dobre okazje):**")
        cols = st.columns(6)
        for i, stock in enumerate(brown_stocks_list):
            col = cols[i % 6]
            button_key = f"brown_btn_{stock['symbol']}_{i}"
            if col.button(f"{stock['icon']} {stock['symbol']}\nRSI: {stock['rsi']}", key=button_key, help=f"Analiza {stock['symbol']}"):
                st.session_state.selected_stock = stock
                st.rerun()

# Szczegółowa analiza
if 'selected_stock' in st.session_state:
    stock = st.session_state.selected_stock
    
    st.markdown("---")
    st.subheader(f"{stock['icon']} {stock['symbol']} - Szczegółowa analiza")
    
    # Metryki
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("💰 Cena", f"${stock['price']}")
    col2.metric("📊 RSI (14)", f"{stock['rsi']}")
    col3.metric("📉 EMA 200", f"${stock['ema_200']}")
    
    # Formatowanie kapitalizacji
    if stock['market_cap'] > 0:
        if stock['market_cap'] >= 1e12:
            market_cap_str = f"${stock['market_cap']/1e12:.1f}T"
        elif stock['market_cap'] >= 1e9:
            market_cap_str = f"${stock['market_cap']/1e9:.1f}B"
        elif stock['market_cap'] >= 1e6:
            market_cap_str = f"${stock['market_cap']/1e6:.1f}M"
        else:
            market_cap_str = f"${stock['market_cap']:,.0f}"
    else:
        market_cap_str = "N/A"
    
    col4.metric("🏢 Kapitalizacja", market_cap_str)
    
    # Dodatkowe metryki
    col1, col2, col3, col4 = st.columns(4)
    price_vs_ema = ((stock['price'] / stock['ema_200']) - 1) * 100
    col1.metric("⚖️ vs EMA200", f"{price_vs_ema:+.1f}%")
    col2.metric("📊 Wolumen", f"{stock['volume']:,}")
    
    # Opis wolumenu
    if stock['volume_ratio'] > 2.0:
        vol_desc = "🔥 Bardzo wysoki"
    elif stock['volume_ratio'] > 1.5:
        vol_desc = "📈 Wysoki"
    elif stock['volume_ratio'] > 1.0:
        vol_desc = "📊 Normalny"
    elif stock['volume_ratio'] > 0.5:
        vol_desc = "📉 Niski"
    else:
        vol_desc = "❄️ Bardzo niski"
    
    col3.metric("🔥 Vol ratio", f"{stock['volume_ratio']}x")
    col4.metric("🌡️ Aktywność", vol_desc)
    
    # Sektor
    st.metric("🏭 Sektor", stock['sector'])
    
    # Wykresy
    tab1, tab2 = st.tabs(["📊 Świecowy + EMA200", "📈 RSI"])
    
    with tab1:
        st.plotly_chart(create_candlestick_chart(stock), use_container_width=True)
        
    with tab2:
        st.plotly_chart(create_rsi_chart(stock), use_container_width=True)
    
    # Eksport danych
    if st.button("📥 Eksportuj dane do CSV"):
        # Formatowanie danych do eksportu
        if stock['market_cap'] > 0:
            if stock['market_cap'] >= 1e12:
                market_cap_export = f"{stock['market_cap']/1e12:.2f}T"
            elif stock['market_cap'] >= 1e9:
                market_cap_export = f"{stock['market_cap']/1e9:.2f}B"
            elif stock['market_cap'] >= 1e6:
                market_cap_export = f"{stock['market_cap']/1e6:.2f}M"
            else:
                market_cap_export = f"{stock['market_cap']}"
        else:
            market_cap_export = "N/A"
        
        df_export = pd.DataFrame([{
            'Symbol': stock['symbol'],
            'Cena': stock['price'],
            'RSI': stock['rsi'],
            'EMA200': stock['ema_200'],
            'Wolumen': stock['volume'],
            'Vol_ratio': stock['volume_ratio'],
            'Kapitalizacja': market_cap_export,
            'Sektor': stock['sector']
        }])
        st.download_button(
            "Pobierz CSV", 
            df_export.to_csv(index=False), 
            f"{stock['symbol']}_analiza.csv", 
            "text/csv"
        )

else:
    st.info("🚀 Kliknij 'Skanuj teraz' w panelu bocznym, aby rozpocząć analizę")
    st.markdown("""
    **Jak to działa:**
    - Analizujemy top 500 spółek NASDAQ wg wolumenu
    - Szukamy spółek z RSI w zakresie 25-40
    - 💎 RSI 25-35 = najlepsze okazje
    - 🟤 RSI 35-40 = dobre okazje
    - Kliknij dowolną spółkę, aby zobaczyć szczegółową analizę
    """)

# Footer
st.markdown(f"<div style='text-align: center; color: #64748b; font-size: 12px; margin-top: 20px;'>💎 NASDAQ Diamond Scanner | {datetime.now().strftime('%Y-%m-%d %H:%M')} | Dane: Yahoo Finance</div>", unsafe_allow_html=True)
