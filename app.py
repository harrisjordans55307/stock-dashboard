import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# Konfiguracja strony
st.set_page_config(
    page_title="💎 Skaner Diamentów", 
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
    .compact-slider .stSlider {
        padding: 0;
        margin: 0;
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

@st.cache_data(ttl=300)
def calculate_macd(series, fast=12, slow=26, signal=9):
    """Oblicza MACD"""
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    histogram = macd - signal_line
    return macd, signal_line, histogram

@st.cache_data(ttl=300)
def calculate_bollinger_bands(series, period=20, std_dev=2):
    """Oblicza Bollinger Bands"""
    sma = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    return sma, upper, lower

@st.cache_data(ttl=600)
def get_all_nasdaq_symbols():
    """Rozszerzona lista symboli NASDAQ - więcej spółek"""
    return [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'AMD', 'INTC', 'ORCL',
        'IBM', 'CSCO', 'ADBE', 'CRM', 'NOW', 'SNOW', 'ZM', 'TEAM', 'OKTA', 'DDOG',
        'QCOM', 'TXN', 'AVGO', 'AMAT', 'LRCX', 'KLAC', 'MU', 'MCHP', 'ADI', 'MRVL',
        'JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'BLK', 'SCHW', 'AXP', 'V', 'MA', 'PYPL',
        'SQ', 'AFRM', 'SOFI', 'HOOD', 'COIN', 'ALLY', 'FIS', 'FISV',
        'JNJ', 'PFE', 'MRK', 'ABBV', 'LLY', 'ABT', 'MDT', 'BMY', 'UNH',
        'GILD', 'AMGN', 'BIIB', 'REGN', 'VRTX', 'MRNA', 'BNTX',
        'WMT', 'KO', 'PEP', 'PG', 'NKE', 'MCD', 'SBUX', 'COST', 'TGT', 'HD',
        'EBAY', 'ETSY', 'SHOP', 'ROKU', 'NFLX', 'DIS', 'CMCSA', 'TMUS',
        'XOM', 'CVX', 'COP', 'SLB', 'HAL', 'KMI', 'OXY', 'MPC', 'PSX', 'VLO',
        'BA', 'CAT', 'GE', 'HON', 'LMT', 'MMM', 'UNP', 'UPS', 'FDX',
        'INTU', 'ADP', 'WDAY', 'VEEV', 'TWLO', 'DOCU', 'PLTR', 'U', 'RBLX',
        'UBER', 'LYFT', 'DASH', 'ABNB', 'ZS', 'CRWD', 'PANW', 'FTNT',
        'CCI', 'AMT', 'VZ', 'T', 'SPOT', 'PINS', 'SNAP',
        'DE', 'RTX', 'NOC', 'GD', 'CSX', 'NSC', 'ODFL', 'EXPD',
        'LOW', 'BBY', 'DG', 'DLTR', 'CHTR', 'TTD', 'NVST', 'STNE',
        'BILL', 'ZEN', 'NET', 'ESTC', 'MDB', 'SNOW', 'VEEV',
        'TWLO', 'OKTA', 'DOCU', 'TEAM', 'NOW', 'SNPS', 'CDNS', 'ANSS'
    ]

@st.cache_data(ttl=300)
def get_top_symbols_by_volume(symbol_list, top_n=500):
    """Sortuj symbole po wolumenie - więcej spółek"""
    symbol_data = []
    
    progress_text = st.empty()
    
    # Sprawdź więcej symboli dla lepszego pokrycia
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
def analyze_single_stock(symbol, rsi_min=25, rsi_max=40):
    """Analizuje pojedynczą spółkę - poprawiony filtr RSI"""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1y", interval="1d")
        
        if df.empty or len(df) < 50:
            return None
            
        # Oblicz wszystkie wskaźniki
        df['rsi'] = calculate_rsi(df['Close'], 14)
        df['ema_200'] = calculate_ema(df['Close'], 200)
        df['ema_50'] = calculate_ema(df['Close'], 50)
        df['volume_sma'] = df['Volume'].rolling(20).mean()
        df['macd'], df['macd_signal'], df['macd_hist'] = calculate_macd(df['Close'])
        df['bb_mid'], df['bb_upper'], df['bb_lower'] = calculate_bollinger_bands(df['Close'])
        
        latest = df.iloc[-1]
        
        # Sprawdź czy RSI jest w interesującym zakresie (25-40) - POPRAWIONE
        if pd.isna(latest['rsi']) or latest['rsi'] < rsi_min or latest['rsi'] > rsi_max:
            return None
            
        # Określ kategorię
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
        except:
            market_cap = 0
        
        volume_ratio = latest['Volume'] / latest['volume_sma'] if latest['volume_sma'] > 0 else 1
        
        # Oblicz potencjał kupna (0-100 punktów)
        buy_potential = calculate_buy_potential(df, latest)
        
        return {
            'symbol': symbol,
            'price': round(latest['Close'], 2),
            'rsi': round(latest['rsi'], 2),
            'ema_200': round(latest['ema_200'], 2),
            'ema_50': round(latest['ema_50'], 2),
            'volume': int(latest['Volume']),
            'avg_volume': int(latest['volume_sma']),
            'volume_ratio': round(volume_ratio, 1),
            'market_cap': market_cap,
            'category': category,
            'icon': icon,
            'buy_potential': buy_potential,
            'data': df
        }
        
    except Exception as e:
        return None

def calculate_buy_potential(df, latest):
    """Oblicz potencjał kupna na podstawie wielu wskaźników (0-100)"""
    score = 0
    max_score = 100
    
    # RSI score (0-20)
    if latest['rsi'] <= 25:
        score += 20
    elif latest['rsi'] <= 30:
        score += 15
    elif latest['rsi'] <= 35:
        score += 10
    else:
        score += 5
    
    # Price vs EMA200 (0-15)
    price_vs_ema200 = (latest['Close'] / latest['ema_200']) - 1
    if price_vs_ema200 > 0:
        score += 15
    elif price_vs_ema200 > -0.05:
        score += 10
    elif price_vs_ema200 > -0.10:
        score += 5
    
    # MACD score (0-15)
    if latest['macd'] > latest['macd_signal'] and latest['macd_hist'] > 0:
        score += 15
    elif latest['macd'] > latest['macd_signal']:
        score += 10
    elif latest['macd_hist'] > 0:
        score += 5
    
    # Volume ratio (0-15)
    if latest['volume_ratio'] > 2.0:
        score += 15
    elif latest['volume_ratio'] > 1.5:
        score += 10
    elif latest['volume_ratio'] > 1.0:
        score += 5
    
    # Price vs BB (0-15)
    if latest['Close'] < latest['bb_lower']:
        score += 15
    elif latest['Close'] < latest['bb_mid']:
        score += 10
    
    # Trend confirmation (0-20)
    recent_data = df.tail(30)
    price_trend = (recent_data['Close'].iloc[-1] / recent_data['Close'].iloc[0]) - 1
    if price_trend > 0:
        score += 20
    elif price_trend > -0.05:
        score += 10
    else:
        score += 0
    
    return min(score, max_score)

def find_diamond_stocks(rsi_min=25, rsi_max=40, min_market_cap=0, max_market_cap=float('inf')):
    """Znajdź diamenty - poprawiony filtr"""
    # Pobierz spółki po wolumenie
    all_symbols = get_all_nasdaq_symbols()
    top_symbols = get_top_symbols_by_volume(all_symbols, 500)
    
    results = []
    processed_symbols = set()
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, symbol in enumerate(top_symbols):
        try:
            if symbol in processed_symbols:
                continue
            processed_symbols.add(symbol)
            
            status_text.text(f"🔍 Analizuję {symbol}... ({i+1}/{len(top_symbols)})")
            progress = (i + 1) / len(top_symbols)
            progress_bar.progress(progress)
            
            result = analyze_single_stock(symbol, rsi_min=rsi_min, rsi_max=rsi_max)
            if result:
                if result['market_cap'] >= min_market_cap:
                    if max_market_cap == float('inf') or result['market_cap'] <= max_market_cap:
                        results.append(result)
                
        except Exception as e:
            continue
    
    progress_bar.empty()
    status_text.empty()
    
    return sorted(results, key=lambda x: x['buy_potential'], reverse=True)

# UI Aplikacji
st.markdown("<div class='diamond-header'><h1>💎 Skaner Diamentów</h1></div>", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("🎯 Filtry")
    
    # RSI - poprawione min/max
    col1, col2 = st.columns(2)
    with col1:
        rsi_min = st.number_input("Min RSI", min_value=0, max_value=40, value=25, step=1)
    with col2:
        rsi_max = st.number_input("Max RSI", min_value=25, max_value=100, value=40, step=1)
    
    # Kapitalizacja
    st.subheader("Kapitalizacja")
    col1, col2 = st.columns(2)
    with col1:
        min_cap_billions = st.number_input("Min (mld $)", min_value=0, value=0, step=1)
        min_market_cap = min_cap_billions * 1e9
    with col2:
        max_cap_billions = st.number_input("Max (mld $)", min_value=0, value=1000, step=10)
        max_market_cap = max_cap_billions * 1e9 if max_cap_billions > 0 else float('inf')
    
    # Analiza pojedynczego symbolu
    st.subheader("🔍 Szybka analiza")
    custom_symbol = st.text_input("Symbol", "")
    if custom_symbol and st.button("Analizuj symbol"):
        with st.spinner(f"Analizuję {custom_symbol.upper()}..."):
            result = analyze_single_stock(custom_symbol.upper(), rsi_min=0, rsi_max=100)
            if result:
                st.session_state.selected_stock = result
                st.success(f"✅ Znaleziono {custom_symbol.upper()}")
            else:
                st.error("❌ Nie znaleziono danych")
    
    # Przycisk skanowania
    st.markdown("---")
    if st.button("🔍 Skanuj teraz", type="primary", use_container_width=True):
        with st.spinner("🚀 Analizuję 500 spółek NASDAQ..."):
            diamond_stocks = find_diamond_stocks(
                rsi_min=rsi_min,
                rsi_max=rsi_max,
                min_market_cap=min_market_cap,
                max_market_cap=max_market_cap
            )
            
            if diamond_stocks:
                st.success(f"✅ Znaleziono {len(diamond_stocks)} spółek z RSI {rsi_min}-{rsi_max}!")
                st.session_state.diamond_stocks = diamond_stocks
                st.balloons()
                
                # Pokaż przykładowe wyniki dla debugowania
                st.info(f"Przykładowe RSI znalezione: {[s['rsi'] for s in diamond_stocks[:5]]}")
            else:
                st.warning("⚠️ Brak spółek spełniających kryteria")
                
                # Debugowanie - sprawdź czy ogólnie coś znajduje
                with st.spinner("Sprawdzam alternatywne kryteria..."):
                    test_stocks = find_diamond_stocks(rsi_min=0, rsi_max=100, min_market_cap=0, max_market_cap=float('inf'))
                    if test_stocks:
                        st.info(f"Znaleziono {len(test_stocks)} spółek bez filtrów RSI. Przykładowe RSI: {[s['rsi'] for s in test_stocks[:5]]}")
                    else:
                        st.error("Nie znaleziono żadnych spółek - problem z połączeniem lub danymi")

# Reszta kodu bez zmian...
    ))
    
    # Bollinger Bands
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['bb_upper'],
        name='BB Upper',
        line=dict(color='purple', width=1, dash='dot')
    ))
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['bb_lower'],
        name='BB Lower',
        line=dict(color='purple', width=1, dash='dot'),
        fill='tonexty',
        fillcolor='rgba(128, 0, 128, 0.1)'
    ))
    
    fig.update_layout(
        title=f"{stock_data['icon']} {stock_data['symbol']} - Potencjał: {stock_data['buy_potential']}/100",
        xaxis_title='Data',
        yaxis_title='Cena ($)',
        height=500,
        xaxis_rangeslider_visible=False
    )
    
    return fig

def create_technical_chart(stock_data):
    """Wykres techniczny z RSI, MACD, Volume"""
    df = stock_data['data'].tail(120)
    
    fig = go.Figure()
    
    # Cena
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['Close'],
        name='Cena',
        line=dict(color='blue', width=2)
    ))
    
    # EMA linie
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['ema_200'],
        name='EMA 200',
        line=dict(color='orange', width=2)
    ))
    
    # RSI jako subplot
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['rsi'],
        name='RSI',
        yaxis='y2',
        line=dict(color='purple', width=2)
    ))
    
    fig.update_layout(
        title=f"Analiza techniczna {stock_data['symbol']}",
        xaxis_title='Data',
        yaxis_title='Cena ($)',
        yaxis2=dict(
            title='RSI',
            overlaying='y',
            side='right',
            range=[0, 100]
        ),
        height=500
    )
    
    # Dodaj linie RSI
    fig.add_hline(y=30, line_dash="dash", line_color="green", yref="y2")
    fig.add_hline(y=70, line_dash="dash", line_color="red", yref="y2")
    
    return fig

# UI Aplikacji
st.markdown("<div class='diamond-header'><h1>💎 Skaner Diamentów</h1></div>", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("🎯 Filtry")
    
    # RSI - kompaktowy suwak
    st.markdown("<div class='compact-slider'>", unsafe_allow_html=True)
    rsi_max = st.slider("Max RSI", 25, 40, 40, 1)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Kapitalizacja
    st.subheader("Kapitalizacja")
    col1, col2 = st.columns(2)
    with col1:
        min_cap_billions = st.number_input("Min (mld $)", min_value=0, value=0, step=1)
        min_market_cap = min_cap_billions * 1e9
    with col2:
        max_cap_billions = st.number_input("Max (mld $)", min_value=0, value=1000, step=10)
        max_market_cap = max_cap_billions * 1e9 if max_cap_billions > 0 else float('inf')
    
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
        with st.spinner("🚀 Analizuję 700 spółek NASDAQ..."):
            diamond_stocks = find_diamond_stocks(
                rsi_max=rsi_max,
                min_market_cap=min_market_cap,
                max_market_cap=max_market_cap
            )
            
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
    
    # Tabela wyników - bez sektora, z potencjałem kupna
    st.subheader("📋 Znalezione spółki")
    
    table_data = []
    for s in stocks:
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
            vol_desc = "🔥"
        elif s['volume_ratio'] > 1.5:
            vol_desc = "📈"
        elif s['volume_ratio'] > 1.0:
            vol_desc = "📊"
        elif s['volume_ratio'] > 0.5:
            vol_desc = "📉"
        else:
            vol_desc = "❄️"
        
        table_data.append({
            'Symbol': f"{s['icon']} {s['symbol']}",
            'Cena': f"${s['price']}",
            'RSI': f"{s['rsi']}",
            'EMA200': f"${s['ema_200']}",
            'Vol': f"{s['volume_ratio']}x {vol_desc}",
            'Kapitalizacja': market_cap_str,
            'Potencjał': f"{s['buy_potential']}/100"
        })
    
    df_display = pd.DataFrame(table_data)
    st.dataframe(df_display, use_container_width=True, height=500)
    
    # Przyciski spółek
    st.subheader("💎 Kliknij spółkę do analizy")
    
    # Grupuj po ikonach
    diamond_stocks_list = [s for s in stocks if s['category'] == 'diamond']
    brown_stocks_list = [s for s in stocks if s['category'] == 'brown']
    
    if diamond_stocks_list:
        st.markdown("**💎 RSI 25-35 (najlepsze okazje):**")
        cols = st.columns(8)  # Więcej kolumn
        for i, stock in enumerate(diamond_stocks_list[:24]):  # Pokaż pierwsze 24
            col = cols[i % 8]
            button_key = f"diamond_btn_{stock['symbol']}_{i}"
            if col.button(f"{stock['icon']} {stock['symbol']}\nRSI: {stock['rsi']}\nPot: {stock['buy_potential']}", key=button_key, help=f"Analiza {stock['symbol']}"):
                st.session_state.selected_stock = stock
                st.rerun()
    
    if brown_stocks_list:
        st.markdown("**🟤 RSI 35-40 (dobre okazje):**")
        cols = st.columns(8)  # Więcej kolumn
        for i, stock in enumerate(brown_stocks_list[:24]):  # Pokaż pierwsze 24
            col = cols[i % 8]
            button_key = f"brown_btn_{stock['symbol']}_{i}"
            if col.button(f"{stock['icon']} {stock['symbol']}\nRSI: {stock['rsi']}\nPot: {stock['buy_potential']}", key=button_key, help=f"Analiza {stock['symbol']}"):
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
    col4.metric("🎯 Potencjał", f"{stock['buy_potential']}/100")
    
    # Ocena potencjału
    st.subheader("📈 Ocena potencjału kupna")
    if stock['buy_potential'] >= 80:
        st.success(f"🚀 BARDZO DOBRY ({stock['buy_potential']}/100) - Silny sygnał kupna")
    elif stock['buy_potential'] >= 60:
        st.info(f"✅ DOBRY ({stock['buy_potential']}/100) - Umiarkowany sygnał kupna")
    elif stock['buy_potential'] >= 40:
        st.warning(f"🟡 ŚREDNI ({stock['buy_potential']}/100) - Ostrożne obserwowanie")
    else:
        st.error(f"🔴 SŁABY ({stock['buy_potential']}/100) - Niepewny sygnał")
    
    # Wykresy
    tab1, tab2 = st.tabs(["📊 Techniczny", "📈 Szczegóły"])
    
    with tab1:
        st.plotly_chart(create_technical_chart(stock), use_container_width=True)
        
    with tab2:
        st.plotly_chart(create_candlestick_chart(stock), use_container_width=True)
    
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
            'EMA50': stock['ema_50'],
            'Wolumen': stock['volume'],
            'Vol_ratio': stock['volume_ratio'],
            'Kapitalizacja': market_cap_export,
            'Potencjał_kupna': stock['buy_potential']
        }])
        st.download_button(
            "Pobierz CSV", 
            df_export.to_csv(index=False), 
            f"{stock['symbol']}_analiza.csv", 
            "text/csv"
        )

else:
    st.info("🚀 Kliknij 'Skanuj teraz' w panelu bocznym, aby rozpocząć analizę")

# Footer
st.markdown(f"<div style='text-align: center; color: #64748b; font-size: 12px; margin-top: 20px;'>💎 Skaner Diamentów | {datetime.now().strftime('%Y-%m-%d %H:%M')} | Dane: Yahoo Finance</div>", unsafe_allow_html=True)
