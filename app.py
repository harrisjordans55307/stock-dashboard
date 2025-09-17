import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

# Konfiguracja strony
st.set_page_config(
    page_title="💎 NASDAQ Diamond Scanner", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS - uczynione bardziej kompaktowym
st.markdown("""
<style>
    .metric-container {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0.2rem 0;
    }
    .diamond-stock {
        background: linear-gradient(45deg, #ffd700, #ffed4e);
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0.2rem 0;
        border-left: 3px solid #f59e0b;
    }
    .brown-stock {
        background: linear-gradient(45deg, #d97706, #f59e0b);
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0.2rem 0;
        border-left: 3px solid #92400e;
    }
    .stButton > button {
        width: 100%;
        margin-bottom: 0.2rem;
    }
    .stDataFrame {
        font-size: 12px;
    }
</style>
""", unsafe_allow_html=True)

# Funkcje pomocnicze
@st.cache_data(ttl=300)  # Cache na 5 minut
def calculate_rsi(series, period=14):
    """Oblicza RSI z poprawnym wygładzaniem (używa EMA zamiast SMA dla avg gain/loss)"""
    delta = series.diff(1)
    if len(delta) < period:
        return pd.Series([np.nan] * len(series), index=series.index)
    
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    # Użyj ewm z com=period-1 dla Wilder's smoothing
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
def get_top_nasdaq_symbols():
    """Lista popularnych symboli NASDAQ - zmniejszona dla stabilności"""
    return [
        # Tech Giants & Popular stocks
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'AMD', 'INTC', 'ORCL',
        'IBM', 'CSCO', 'ADBE', 'CRM', 'NOW', 'SNOW', 'ZM', 'TEAM', 'OKTA', 'DDOG',
        
        # Finance
        'JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'BLK', 'SCHW', 'AXP', 'V', 'MA', 'PYPL',
        'SQ', 'AFRM', 'SOFI', 'HOOD', 'COIN',
        
        # Healthcare & Biotech
        'JNJ', 'PFE', 'MRK', 'ABBV', 'LLY', 'ABT', 'MDT', 'BMY', 'UNH',
        'GILD', 'AMGN', 'BIIB', 'REGN', 'VRTX', 'MRNA', 'BNTX',
        
        # Consumer
        'WMT', 'KO', 'PEP', 'PG', 'NKE', 'MCD', 'SBUX', 'COST', 'TGT', 'HD',
        'EBAY', 'ETSY', 'SHOP', 'ROKU', 'NFLX', 'DIS',
        
        # Energy
        'XOM', 'CVX', 'COP', 'SLB', 'HAL', 'KMI', 'OXY',
        
        # Industrial
        'BA', 'CAT', 'GE', 'HON', 'LMT', 'MMM', 'UNP', 'UPS', 'FDX',
        'F', 'GM', 'RIVN', 'LCID',
        
        # Semiconductors
        'QCOM', 'TXN', 'AVGO', 'AMAT', 'LRCX', 'KLAC', 'MU', 'MCHP', 'ADI', 'MRVL',
        
        # Software
        'INTU', 'ADP', 'WDAY', 'VEEV', 'TWLO', 'DOCU', 'PLTR', 'U', 'RBLX',
        'UBER', 'LYFT', 'DASH', 'ABNB',
        
        # Communication
        'CCI', 'AMT', 'TMUS', 'VZ', 'T', 'SPOT', 'PINS', 'SNAP'
    ]

@st.cache_data(ttl=300)
def analyze_single_stock(symbol, period="1y", rsi_threshold=40):
    """Analizuje pojedynczą spółkę - dodano MACD i Bollinger Bands"""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval="1d")
        
        if df.empty or len(df) < 50:
            return None
            
        # Oblicz wskaźniki
        df['rsi'] = calculate_rsi(df['Close'], 14)
        df['ema_50'] = calculate_ema(df['Close'], 50)
        df['ema_200'] = calculate_ema(df['Close'], 200)
        df['volume_sma'] = df['Volume'].rolling(20).mean()
        df['macd'], df['macd_signal'], df['macd_hist'] = calculate_macd(df['Close'])
        df['bb_mid'], df['bb_upper'], df['bb_lower'] = calculate_bollinger_bands(df['Close'])
        
        latest = df.iloc[-1]
        
        # Sprawdź czy RSI jest w interesującym zakresie
        if pd.isna(latest['rsi']) or latest['rsi'] > rsi_threshold:
            return None
            
        # Określ kategorię
        if latest['rsi'] <= 25:
            category = "super_oversold"
            icon = "💎"
            color = "#10b981"
        elif latest['rsi'] <= 30:
            category = "oversold"
            icon = "💍"
            color = "#3b82f6"
        elif latest['rsi'] <= 35:
            category = "mild_oversold"
            icon = "🟡"
            color = "#f59e0b"
        else:
            category = "watchlist"
            icon = "🟤"
            color = "#d97706"
            
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
            'ema_50': round(latest['ema_50'], 2),
            'ema_200': round(latest['ema_200'], 2),
            'volume': int(latest['Volume']),
            'avg_volume': int(latest['volume_sma']),
            'volume_ratio': round(volume_ratio, 1),
            'market_cap': market_cap,
            'sector': sector,
            'category': category,
            'icon': icon,
            'color': color,
            'data': df
        }
        
    except Exception as e:
        return None

def find_diamond_stocks(rsi_threshold=40):
    """Znajdź diamenty - wersja bez threading"""
    symbols = get_top_nasdaq_symbols()
    results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, symbol in enumerate(symbols):
        try:
            status_text.text(f"🔍 Analizuję {symbol}... ({i+1}/{len(symbols)})")
            progress = (i + 1) / len(symbols)
            progress_bar.progress(progress)
            
            result = analyze_single_stock(symbol, rsi_threshold=rsi_threshold)
            if result:
                results.append(result)
                status_text.text(f"🔍 Znaleziono {len(results)} diamentów... ({i+1}/{len(symbols)})")
                
        except Exception as e:
            continue
    
    progress_bar.empty()
    status_text.empty()
    
    return sorted(results, key=lambda x: x['rsi'])

def create_simple_candlestick_chart(stock_data):
    """Prosty wykres świecowy z EMA i Bollinger Bands - kompaktowy"""
    df = stock_data['data'].tail(90)  # Ostatnie 90 dni
    
    fig = go.Figure()
    
    # Wykres świecowy
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name=stock_data['symbol'],
        increasing_line_color='#10b981',
        decreasing_line_color='#ef4444'
    ))
    
    # EMA 50
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['ema_50'],
        name='EMA 50',
        line=dict(color='#3b82f6', width=1.5)
    ))
    
    # EMA 200
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['ema_200'],
        name='EMA 200',
        line=dict(color='#f59e0b', width=2)
    ))
    
    # Bollinger Bands
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['bb_upper'],
        name='BB Upper',
        line=dict(color='#8b5cf6', width=1, dash='dot')
    ))
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['bb_lower'],
        name='BB Lower',
        line=dict(color='#8b5cf6', width=1, dash='dot')
    ))
    
    fig.update_layout(
        title=f"{stock_data['icon']} {stock_data['symbol']} | RSI: {stock_data['rsi']} | Sektor: {stock_data['sector']}",
        xaxis_title='Data',
        yaxis_title='Cena ($)',
        height=400,  # Zmniejszona wysokość dla kompaktowości
        template='plotly_dark',
        xaxis_rangeslider_visible=False,
        showlegend=True,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig

def create_rsi_chart(stock_data):
    """Osobny wykres RSI - kompaktowy"""
    df = stock_data['data'].tail(90)
    
    fig = go.Figure()
    
    # RSI
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['rsi'],
        name='RSI (14)',
        line=dict(color='#8b5cf6', width=2)
    ))
    
    # Poziomy RSI
    fig.add_hline(y=70, line_dash="dash", line_color='#ef4444')
    fig.add_hline(y=30, line_dash="dash", line_color='#10b981')
    fig.add_hline(y=25, line_dash="dot", line_color='#059669')
    
    # Aktualny RSI
    current_rsi = df['rsi'].iloc[-1]
    fig.add_scatter(
        x=[df.index[-1]], 
        y=[current_rsi],
        mode='markers',
        marker=dict(size=10, color=stock_data['color'], symbol='diamond'),
        name=f"RSI: {current_rsi:.1f}"
    )
    
    fig.update_layout(
        title=f"📊 RSI dla {stock_data['symbol']}",
        xaxis_title='Data',
        yaxis_title='RSI',
        yaxis=dict(range=[0, 100]),
        height=250,  # Zmniejszona wysokość
        template='plotly_dark',
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig

def create_macd_chart(stock_data):
    """Nowy wykres MACD"""
    df = stock_data['data'].tail(90)
    
    fig = go.Figure()
    
    # MACD Line
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['macd'],
        name='MACD',
        line=dict(color='#3b82f6', width=2)
    ))
    
    # Signal Line
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['macd_signal'],
        name='Signal',
        line=dict(color='#f59e0b', width=2)
    ))
    
    # Histogram
    fig.add_trace(go.Bar(
        x=df.index,
        y=df['macd_hist'],
        name='Histogram',
        marker_color=np.where(df['macd_hist'] >= 0, '#10b981', '#ef4444')
    ))
    
    fig.update_layout(
        title=f"📉 MACD dla {stock_data['symbol']}",
        xaxis_title='Data',
        yaxis_title='MACD',
        height=250,
        template='plotly_dark',
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig

# UI Aplikacji - bardziej kompaktowy, z tabs i expanderami
st.title("💎 Skaner Diamentów NASDAQ")
st.markdown("*Znajdź okazje wśród wyprzedanych akcji*")

# Sidebar - kompaktowy
with st.sidebar:
    st.header("🎯 Kontrola")
    
    # Filtry
    max_rsi = st.slider("Max RSI", 20, 50, 40, 5)
    min_market_cap = st.selectbox(
        "Min Kap.", 
        [0, 1e9, 5e9, 10e9, 50e9], 
        format_func=lambda x: f"${x/1e9:.0f}B" if x > 0 else "Wszystkie"
    )
    sectors = sorted(set([s.get('sector', 'N/A') for s in st.session_state.get('diamond_stocks', [])]))
    selected_sector = st.selectbox("Sektor", ["Wszystkie"] + sectors)
    
    # Okres danych
    data_period = st.selectbox("Okres danych", ["1y", "6mo", "3mo", "1mo"], index=0)
    
    # Wyszukiwanie pojedynczego symbolu - nowa funkcja
    custom_symbol = st.text_input("Analizuj symbol", "")
    if custom_symbol:
        if st.button("Analizuj"):
            result = analyze_single_stock(custom_symbol.upper(), period=data_period, rsi_threshold=max_rsi)
            if result:
                st.session_state.selected_stock = result
            else:
                st.error("Nie znaleziono danych dla symbolu.")
    
    # Przycisk skanowania
    if st.button("🔍 Skanuj", type="primary"):
        with st.spinner("🚀 Szukam..."):
            diamond_stocks = find_diamond_stocks(rsi_threshold=max_rsi)
            
            # Filtruj wyniki
            filtered_stocks = [
                s for s in diamond_stocks 
                if s['rsi'] <= max_rsi and s['market_cap'] >= min_market_cap
                and (selected_sector == "Wszystkie" or s['sector'] == selected_sector)
            ]
            
            if filtered_stocks:
                st.success(f"✅ {len(filtered_stocks)} diamentów!")
                st.session_state.diamond_stocks = filtered_stocks
            else:
                st.warning("⚠️ Brak wyników")
    
    # Automatyczne odświeżanie - nowa funkcja
    auto_refresh = st.checkbox("Auto-odśwież co 5 min")
    if auto_refresh:
        time.sleep(300)
        st.rerun()
    
    # Eksport do CSV - nowa funkcja
    if 'diamond_stocks' in st.session_state:
        df_export = pd.DataFrame([{
            'Symbol': s['symbol'],
            'Cena': s['price'],
            'RSI': s['rsi'],
            'Sektor': s['sector'],
            'Kapitalizacja': s['market_cap']
        } for s in st.session_state.diamond_stocks])
        st.download_button("📥 Eksport CSV", df_export.to_csv(index=False), "diamenty.csv")

# Wyświetlanie wyników - w expanderze dla kompaktowości
if 'diamond_stocks' in st.session_state:
    stocks = st.session_state.diamond_stocks
    
    # Statystyki - mniej kolumn
    col1, col2 = st.columns(2)
    super_oversold = len([s for s in stocks if s['category'] == 'super_oversold'])
    oversold = len([s for s in stocks if s['category'] == 'oversold'])
    mild_oversold = len([s for s in stocks if s['category'] == 'mild_oversold'])
    watchlist = len([s for s in stocks if s['category'] == 'watchlist'])
    
    with col1:
        st.metric("💎 <25", super_oversold)
        st.metric("💍 <30", oversold)
    with col2:
        st.metric("🟡 <35", mild_oversold)
        st.metric("🟤 <40", watchlist)
    
    # Tabela wyników - mniejsza
    with st.expander("📊 Diamenty", expanded=True):
        table_data = [{
            'Symbol': f"{s['icon']} {s['symbol']}",
            'Cena': f"${s['price']}",
            'RSI': f"{s['rsi']:.1f}",
            'Sektor': s['sector'][:10] + "..." if len(s['sector']) > 10 else s['sector'],
            'Vol x': f"{s['volume_ratio']}x"
        } for s in stocks]
        df_display = pd.DataFrame(table_data)
        st.dataframe(df_display, use_container_width=True, height=200)  # Zmniejszona wysokość
    
    # Lista spółek w sidebar - już jest

# Szczegółowa analiza - w tabs dla kompaktowości
if 'selected_stock' in st.session_state:
    stock = st.session_state.selected_stock
    
    st.subheader(f"{stock['icon']} {stock['symbol']}")
    
    # Metryki - mniej kolumn
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💰 Cena", f"${stock['price']}")
        st.metric("📊 RSI", f"{stock['rsi']}")
    with col2:
        st.metric("📈 EMA50", f"${stock['ema_50']}")
        st.metric("📉 EMA200", f"${stock['ema_200']}")
    with col3:
        st.metric("🔥 Vol x", f"{stock['volume_ratio']}x")
        price_to_ema = ((stock['price'] / stock['ema_200']) - 1) * 100
        st.metric("vs EMA200", f"{price_to_ema:+.1f}%")
    
    # Wykresy w tabs
    tab1, tab2, tab3 = st.tabs(["Świece", "RSI", "MACD"])
    with tab1:
        st.plotly_chart(create_simple_candlestick_chart(stock), use_container_width=True)
    with tab2:
        st.plotly_chart(create_rsi_chart(stock), use_container_width=True)
    with tab3:
        st.plotly_chart(create_macd_chart(stock), use_container_width=True)
    
    # Analiza w expanderach
    with st.expander("🎯 Sygnały"):
        if stock['rsi'] < 25:
            st.success("🔥 SILNY KUPNO")
        elif stock['rsi'] < 30:
            st.success("💚 KUPNO")
        elif stock['rsi'] < 35:
            st.warning("🟡 MOŻLIWOŚĆ")
        else:
            st.info("🟤 OBSERWACJA")
        
        if stock['price'] < stock['ema_200']:
            st.warning("⚠️ Trend spadkowy")
        else:
            st.success("✅ Trend wzrostowy")
        
        if stock['volume_ratio'] > 1.5:
            st.info("🔥 Wysoki wolumen")
        
        # Dodatkowe sygnały z MACD i BB
        latest = stock['data'].iloc[-1]
        if latest['macd'] > latest['macd_signal'] and latest['macd_hist'] > 0:
            st.success("📈 MACD: Byczy crossover")
        elif latest['macd'] < latest['macd_signal'] and latest['macd_hist'] < 0:
            st.warning("📉 MACD: Niedźwiedzi crossover")
        
        if stock['price'] < latest['bb_lower']:
            st.success("🟢 BB: Poniżej dolnej bandy - wyprzedane")
        elif stock['price'] > latest['bb_upper']:
            st.warning("🔴 BB: Powyżej górnej bandy - przekupione")
    
    with st.expander("📊 Dane"):
        df_recent = stock['data'].tail(60)
        resistance = df_recent['High'].quantile(0.8)
        support = df_recent['Low'].quantile(0.2)
        
        st.write(f"🔴 Opór: ${resistance:.2f}")
        st.write(f"🟢 Wsparcie: ${support:.2f}")
        upside = ((resistance / stock['price']) - 1) * 100
        st.write(f"📈 Potencjał: {upside:.1f}%")
        st.write(f"🏭 Sektor: {stock['sector']}")

else:
    st.info("🚀 Kliknij 'Skanuj' w panelu bocznym")
    
    with st.expander("📚 Instrukcja", expanded=False):
        st.markdown("""
        - **💎 <25**: Ekstremalne
        - **💍 <30**: Silne  
        - **🟡 <35**: Lekkie
        - **🟤 <40**: Obserwacja
        
        Interpretuj RSI <30 jako okazję, sprawdź EMA200 i wolumen.
        """)
    
    st.warning("⚠️ Edukacyjne. Nie porada inwestycyjna.")

# Footer - kompaktowy
st.markdown(f"<div style='text-align: center; color: #64748b; font-size: 12px;'>💎 Scanner | {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>", unsafe_allow_html=True)
