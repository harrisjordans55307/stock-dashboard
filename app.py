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

# Custom CSS
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
        font-size: 12px;
    }
    .stDataFrame {
        font-size: 12px;
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
def get_top_nasdaq_symbols():
    """Lista popularnych symboli NASDAQ"""
    return [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'AMD', 'INTC', 'ORCL',
        'IBM', 'CSCO', 'ADBE', 'CRM', 'NOW', 'SNOW', 'ZM', 'TEAM', 'OKTA', 'DDOG',
        'JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'BLK', 'SCHW', 'AXP', 'V', 'MA', 'PYPL',
        'JNJ', 'PFE', 'MRK', 'ABBV', 'LLY', 'ABT', 'MDT', 'BMY', 'UNH',
        'WMT', 'KO', 'PEP', 'PG', 'NKE', 'MCD', 'SBUX', 'COST', 'TGT', 'HD',
        'XOM', 'CVX', 'COP', 'SLB', 'HAL', 'KMI', 'OXY',
        'BA', 'CAT', 'GE', 'HON', 'LMT', 'MMM', 'UNP', 'UPS', 'FDX',
        'QCOM', 'TXN', 'AVGO', 'AMAT', 'LRCX', 'KLAC', 'MU', 'MCHP', 'ADI', 'MRVL',
        'INTU', 'ADP', 'WDAY', 'TWLO', 'DOCU', 'PLTR', 'U', 'RBLX',
        'UBER', 'LYFT', 'DASH', 'ABNB', 'CCI', 'AMT', 'TMUS', 'VZ', 'T'
    ]

@st.cache_data(ttl=300)
def analyze_single_stock(symbol, period="1y", rsi_threshold=40):
    """Analizuje pojedynczą spółkę"""
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

def find_diamond_stocks(rsi_threshold=40, min_market_cap=0, max_market_cap=float('inf')):
    """Znajdź diamenty"""
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
            if result and result['market_cap'] >= min_market_cap and result['market_cap'] <= max_market_cap:
                results.append(result)
                status_text.text(f"🔍 Znaleziono {len(results)} diamentów... ({i+1}/{len(symbols)})")
                
        except Exception as e:
            continue
    
    progress_bar.empty()
    status_text.empty()
    
    return sorted(results, key=lambda x: x['rsi'])

def create_simple_candlestick_chart(stock_data):
    """Prosty wykres świecowy z EMA i Bollinger Bands"""
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
        line=dict(color='#8b5cf6', width=1, dash='dot'),
        fill='tonexty',
        fillcolor='rgba(139, 92, 246, 0.1)'
    ))
    
    fig.update_layout(
        title=f"{stock_data['icon']} {stock_data['symbol']} | RSI: {stock_data['rsi']} | Sektor: {stock_data['sector']}",
        xaxis_title='Data',
        yaxis_title='Cena ($)',
        height=500,
        template='plotly_dark',
        xaxis_rangeslider_visible=False,
        showlegend=True,
        margin=dict(l=20, r=20, t=60, b=20)
    )
    
    return fig

def create_rsi_chart(stock_data):
    """Osobny wykres RSI"""
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
    fig.add_hline(y=70, line_dash="dash", line_color='#ef4444', annotation_text="Przekupione")
    fig.add_hline(y=30, line_dash="dash", line_color='#10b981', annotation_text="Wyprzedane")
    fig.add_hline(y=25, line_dash="dot", line_color='#059669', annotation_text="Ekstremalne")
    
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
        height=300,
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
        height=300,
        template='plotly_dark',
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig

# UI Aplikacji
st.title("💎 Skaner Diamentów NASDAQ")
st.markdown("*Znajdź okazje wśród wyprzedanych akcji*")

# Sidebar
with st.sidebar:
    st.header("🎯 Kontrola")
    
    # Filtry
    max_rsi = st.slider("Max RSI", 20, 50, 40, 1)
    
    # Filtry kapitalizacji
    col1, col2 = st.columns(2)
    with col1:
        min_market_cap_billions = st.number_input("Min kapitalizacja (mld $)", min_value=0, value=0, step=1)
        min_market_cap = min_market_cap_billions * 1e9
    with col2:
        max_market_cap_billions = st.number_input("Max kapitalizacja (mld $)", min_value=0, value=1000, step=10)
        max_market_cap = max_market_cap_billions * 1e9 if max_market_cap_billions > 0 else float('inf')
    
    sectors = ['Wszystkie'] + sorted(set([s.get('sector', 'N/A') for s in st.session_state.get('diamond_stocks', []) if s.get('sector')]))
    selected_sector = st.selectbox("Sektor", sectors)
    
    # Okres danych
    data_period = st.selectbox("Okres danych", ["1y", "6mo", "3mo", "1mo"], index=0)
    
    # Wyszukiwanie pojedynczego symbolu
    custom_symbol = st.text_input("Analizuj symbol", "")
    if custom_symbol:
        if st.button("🔍 Analizuj"):
            with st.spinner(f"Analizuję {custom_symbol.upper()}..."):
                result = analyze_single_stock(custom_symbol.upper(), period=data_period, rsi_threshold=max_rsi)
                if result:
                    st.session_state.selected_stock = result
                    st.success(f"✅ Znaleziono {custom_symbol.upper()}")
                else:
                    st.error("❌ Nie znaleziono danych")
    
    # Przycisk skanowania
    if st.button("🔍 Skanuj", type="primary"):
        with st.spinner("🚀 Szukam diamentów..."):
            diamond_stocks = find_diamond_stocks(
                rsi_threshold=max_rsi,
                min_market_cap=min_market_cap,
                max_market_cap=max_market_cap
            )
            
            # Filtruj wyniki
            filtered_stocks = [
                s for s in diamond_stocks 
                if (selected_sector == "Wszystkie" or s['sector'] == selected_sector)
            ]
            
            if filtered_stocks:
                st.success(f"✅ Znaleziono {len(filtered_stocks)} diamentów!")
                st.session_state.diamond_stocks = filtered_stocks
            else:
                st.warning("⚠️ Brak wyników spełniających kryteria")
    
    # Eksport do CSV
    if 'diamond_stocks' in st.session_state:
        df_export = pd.DataFrame([{
            'Symbol': s['symbol'],
            'Cena': s['price'],
            'RSI': s['rsi'],
            'EMA50': s['ema_50'],
            'EMA200': s['ema_200'],
            'Sektor': s['sector'],
            'Kapitalizacja': f"${s['market_cap']/1e9:.1f}B" if s['market_cap'] > 0 else "N/A",
            'Wolumen x': s['volume_ratio']
        } for s in st.session_state.diamond_stocks])
        st.download_button("📥 Eksport CSV", df_export.to_csv(index=False), "diamenty.csv", "text/csv")

# Wyświetlanie wyników
if 'diamond_stocks' in st.session_state:
    stocks = st.session_state.diamond_stocks
    
    # Statystyki
    col1, col2, col3, col4 = st.columns(4)
    super_oversold = len([s for s in stocks if s['category'] == 'super_oversold'])
    oversold = len([s for s in stocks if s['category'] == 'oversold'])
    mild_oversold = len([s for s in stocks if s['category'] == 'mild_oversold'])
    
    col1.metric("💎 RSI <25", super_oversold)
    col2.metric("💍 RSI <30", oversold)
    col3.metric("🟡 RSI <35", mild_oversold)
    col4.metric("📊 Razem", len(stocks))
    
    # Tabela wyników
    st.subheader("📋 Diamenty")
    table_data = []
    for s in stocks:
        table_data.append({
            'Symbol': f"{s['icon']} {s['symbol']}",
            'Cena': f"${s['price']}",
            'RSI': f"{s['rsi']:.1f}",
            'EMA200': f"${s['ema_200']}",
            'Sektor': s['sector'][:15] + "..." if len(s['sector']) > 15 else s['sector'],
            'Vol x': f"{s['volume_ratio']:.1f}x"
        })
    
    df_display = pd.DataFrame(table_data)
    st.dataframe(df_display, use_container_width=True, height=300)
    
    # Lista spółek do klikania
    st.subheader("💎 Spółki do analizy")
    cols = st.columns(5)
    for i, stock in enumerate(stocks):
        col = cols[i % 5]
        if col.button(f"{stock['icon']} {stock['symbol']}\nRSI: {stock['rsi']}", key=f"btn_{stock['symbol']}"):
            st.session_state.selected_stock = stock
            st.rerun()

# Szczegółowa analiza
if 'selected_stock' in st.session_state:
    stock = st.session_state.selected_stock
    
    st.markdown("---")
    st.subheader(f"{stock['icon']} {stock['symbol']} - Szczegółowa analiza")
    
    # Metryki
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💰 Aktualna cena", f"${stock['price']}")
        st.metric("📊 RSI (14)", f"{stock['rsi']}")
    with col2:
        st.metric("📈 EMA 50", f"${stock['ema_50']}")
        st.metric("📉 EMA 200", f"${stock['ema_200']}")
    with col3:
        st.metric("📊 Wolumen", f"{stock['volume']:,}")
        volume_desc = "Wysoki" if stock['volume_ratio'] > 1.5 else "Normalny" if stock['volume_ratio'] > 0.8 else "Niski"
        st.metric("🔥 Aktywność", f"{volume_desc} ({stock['volume_ratio']}x)")
    with col4:
        price_to_ema = ((stock['price'] / stock['ema_200']) - 1) * 100
        st.metric("⚖️ vs EMA200", f"{price_to_ema:+.1f}%")
        market_cap_formatted = f"${stock['market_cap']/1e9:.1f}B" if stock['market_cap'] > 0 else "N/A"
        st.metric("🏢 Kapitalizacja", market_cap_formatted)
    
    # Wykresy
    tab1, tab2, tab3 = st.tabs(["📊 Świecowy", "📈 RSI", "📉 MACD"])
    
    with tab1:
        st.plotly_chart(create_simple_candlestick_chart(stock), use_container_width=True)
        
    with tab2:
        st.plotly_chart(create_rsi_chart(stock), use_container_width=True)
        
    with tab3:
        st.plotly_chart(create_macd_chart(stock), use_container_width=True)
    
    # Analiza sygnałów
    with st.expander("🎯 Sygnały handlowe", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("RSI")
            if stock['rsi'] < 25:
                st.success("🔥 EKSTREMALNE WYPRZEDANIE")
            elif stock['rsi'] < 30:
                st.success("💚 SILNE WYPRZEDANIE")
            elif stock['rsi'] < 35:
                st.warning("🟡 LEKKIE WYPRZEDANIE")
            else:
                st.info("🟤 OBSERWACJA")
        
        with col2:
            st.subheader("EMA")
            if stock['price'] > stock['ema_200']:
                st.success("📈 Trend WZROSTOWY")
            else:
                st.warning("📉 Trend SPADKOWY")
            
            if stock['price'] > stock['ema_50'] > stock['ema_200']:
                st.success("🚀 EMA: Bycza formacja")
            elif stock['price'] < stock['ema_50'] < stock['ema_200']:
                st.warning("🐻 EMA: Niedźwiedzia formacja")
        
        with col3:
            st.subheader("MACD")
            latest = stock['data'].iloc[-1]
            if latest['macd'] > latest['macd_signal'] and latest['macd_hist'] > 0:
                st.success("📈 Byczy crossover")
            elif latest['macd'] < latest['macd_signal'] and latest['macd_hist'] < 0:
                st.warning("📉 Niedźwiedzi crossover")
            else:
                st.info("⏸️ Neutralny")
    
    # Dane techniczne
    with st.expander("📊 Dane techniczne", expanded=False):
        df_recent = stock['data'].tail(60)
        resistance = df_recent['High'].quantile(0.8)
        support = df_recent['Low'].quantile(0.2)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🔴 Opór", f"${resistance:.2f}")
        with col2:
            st.metric("🟢 Wsparcie", f"${support:.2f}")
        with col3:
            upside = ((resistance / stock['price']) - 1) * 100
            st.metric("📈 Potencjał wzrostu", f"{upside:.1f}%")
        
        st.write(f"🏭 Sektor: {stock['sector']}")
        st.write(f"📊 Ostatnia aktualizacja: {df_recent.index[-1].strftime('%Y-%m-%d')}")

else:
    st.info("🚀 Kliknij 'Skanuj' w panelu bocznym, aby rozpocząć")
    
    with st.expander("📚 Jak używać", expanded=True):
        st.markdown("""
        **🔍 Jak szukać diamentów:**
        1. Ustaw maksymalny RSI (np. 35 dla agresywnych, 40 dla konserwatywnych)
        2. Wybierz zakres kapitalizacji (np. 10-100 mld dla średnich spółek)
        3. Wybierz sektor lub zostaw "Wszystkie"
        4. Kliknij "Skanuj"
        5. Kliknij dowolną spółkę, aby zobaczyć szczegółową analizę
        
        **💎 Interpretacja RSI:**
        - **<25**: Ekstremalne wyprzedanie - agresywne kupno
        - **25-30**: Silne wyprzedanie - kupno
        - **30-35**: Lekkie wyprzedanie - obserwacja
        - **35-40**: Neutralne - ostrożność
        """)

# Footer
st.markdown(f"<div style='text-align: center; color: #64748b; font-size: 12px; margin-top: 20px;'>💎 NASDAQ Diamond Scanner | {datetime.now().strftime('%Y-%m-%d %H:%M')} | Dane: Yahoo Finance</div>", unsafe_allow_html=True)
