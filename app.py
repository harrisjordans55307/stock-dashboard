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
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    .diamond-stock {
        background: linear-gradient(45deg, #ffd700, #ffed4e);
        padding: 0.8rem;
        border-radius: 8px;
        margin: 0.3rem 0;
        border-left: 4px solid #f59e0b;
    }
    .brown-stock {
        background: linear-gradient(45deg, #d97706, #f59e0b);
        padding: 0.8rem;
        border-radius: 8px;
        margin: 0.3rem 0;
        border-left: 4px solid #92400e;
    }
</style>
""", unsafe_allow_html=True)

# Funkcje pomocnicze
@st.cache_data(ttl=300)  # Cache na 5 minut
def calculate_rsi(series, period=14):
    """Oblicza RSI"""
    delta = series.diff()
    if len(delta) < period:
        return pd.Series([None] * len(delta), index=delta.index)
    
    gain = (delta.where(delta > 0, 0)).rolling(window=period, min_periods=1).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period, min_periods=1).mean()
    
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi

@st.cache_data(ttl=300)
def calculate_ema(series, period=200):
    """Oblicza EMA"""
    if len(series) < period:
        return series.ewm(span=min(period, len(series)), adjust=False).mean()
    return series.ewm(span=period, adjust=False).mean()

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
def analyze_single_stock(symbol):
    """Analizuje pojedynczą spółkę"""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1y", interval="1d")
        
        if df.empty or len(df) < 50:
            return None
            
        # Oblicz wskaźniki
        df['rsi'] = calculate_rsi(df['Close'], 14)
        df['ema_50'] = calculate_ema(df['Close'], 50)
        df['ema_200'] = calculate_ema(df['Close'], 200)
        df['volume_sma'] = df['Volume'].rolling(20).mean()
        
        latest = df.iloc[-1]
        
        # Sprawdź czy RSI jest w interesującym zakresie
        if pd.isna(latest['rsi']) or latest['rsi'] > 40:
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

def find_diamond_stocks():
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
            
            result = analyze_single_stock(symbol)
            if result:
                results.append(result)
                status_text.text(f"🔍 Znaleziono {len(results)} diamentów... ({i+1}/{len(symbols)})")
                
        except Exception as e:
            continue
    
    progress_bar.empty()
    status_text.empty()
    
    return sorted(results, key=lambda x: x['rsi'])

def create_simple_candlestick_chart(stock_data):
    """Prosty wykres świecowy z EMA - bez subplots"""
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
        line=dict(color='#3b82f6', width=2)
    ))
    
    # EMA 200
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['ema_200'],
        name='EMA 200',
        line=dict(color='#f59e0b', width=3)
    ))
    
    fig.update_layout(
        title=f"{stock_data['icon']} {stock_data['symbol']} | RSI: {stock_data['rsi']} | Sektor: {stock_data['sector']}",
        xaxis_title='Data',
        yaxis_title='Cena ($)',
        height=500,
        template='plotly_dark',
        xaxis_rangeslider_visible=False,
        showlegend=True
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
        line=dict(color='#8b5cf6', width=3)
    ))
    
    # Poziomy RSI
    fig.add_hline(y=70, line_dash="dash", line_color='#ef4444', 
                 annotation_text="Przekupione (70)")
    fig.add_hline(y=30, line_dash="dash", line_color='#10b981', 
                 annotation_text="Wyprzedane (30)")
    fig.add_hline(y=25, line_dash="dot", line_color='#059669', 
                 annotation_text="Super Wyprzedane (25)")
    
    # Aktualny RSI
    current_rsi = df['rsi'].iloc[-1]
    fig.add_scatter(
        x=[df.index[-1]], 
        y=[current_rsi],
        mode='markers',
        marker=dict(size=15, color=stock_data['color'], symbol='diamond'),
        name=f"Aktualny RSI: {current_rsi:.1f}"
    )
    
    fig.update_layout(
        title=f"📊 RSI dla {stock_data['symbol']}",
        xaxis_title='Data',
        yaxis_title='RSI',
        yaxis=dict(range=[0, 100]),
        height=300,
        template='plotly_dark'
    )
    
    return fig

# UI Aplikacji
st.title("💎 Skaner Diamentów NASDAQ")
st.markdown("*Znajdź najlepsze okazje wśród wyprzedanych akcji*")

# Sidebar
with st.sidebar:
    st.header("🎯 Panel Kontrolny")
    
    # Filtry
    st.subheader("🔧 Filtry")
    max_rsi = st.slider("Maksymalny RSI", 20, 50, 40, 5)
    min_market_cap = st.selectbox(
        "Minimalna kapitalizacja", 
        [0, 1e9, 5e9, 10e9, 50e9], 
        format_func=lambda x: f"${x/1e9:.0f}B" if x > 0 else "Wszystkie"
    )
    
    # Przycisk skanowania
    scan_button = st.button(
        "🔍 Skanuj Diamenty", 
        type="primary", 
        use_container_width=True
    )
    
    if scan_button:
        with st.spinner("🚀 Szukam diamentów..."):
            diamond_stocks = find_diamond_stocks()
            
            # Filtruj wyniki
            filtered_stocks = [
                s for s in diamond_stocks 
                if s['rsi'] <= max_rsi and s['market_cap'] >= min_market_cap
            ]
            
            if filtered_stocks:
                st.success(f"✅ Znaleziono {len(filtered_stocks)} diamentów!")
                st.session_state.diamond_stocks = filtered_stocks
            else:
                st.warning("⚠️ Nie znaleziono spółek spełniających kryteria")

# Wyświetlanie wyników
if 'diamond_stocks' in st.session_state:
    stocks = st.session_state.diamond_stocks
    
    # Statystyki
    col1, col2, col3, col4 = st.columns(4)
    
    super_oversold = [s for s in stocks if s['category'] == 'super_oversold']
    oversold = [s for s in stocks if s['category'] == 'oversold']
    mild_oversold = [s for s in stocks if s['category'] == 'mild_oversold']
    watchlist = [s for s in stocks if s['category'] == 'watchlist']
    
    with col1:
        st.metric("💎 Super Wyprzedane (<25)", len(super_oversold))
    with col2:
        st.metric("💍 Wyprzedane (<30)", len(oversold))
    with col3:
        st.metric("🟡 Lekko Wyprzedane (<35)", len(mild_oversold))
    with col4:
        st.metric("🟤 Lista Obserwacji (<40)", len(watchlist))
    
    # Tabela wyników
    st.subheader("📊 Znalezione Diamenty")
    
    # Przygotuj dane do tabeli
    table_data = []
    for stock in stocks:
        market_cap_str = f"${stock['market_cap']/1e9:.1f}B" if stock['market_cap'] > 0 else "N/A"
        
        table_data.append({
            'Symbol': f"{stock['icon']} {stock['symbol']}",
            'Cena': f"${stock['price']}",
            'RSI': f"{stock['rsi']:.1f}",
            'Sektor': stock['sector'][:15] + "..." if len(stock['sector']) > 15 else stock['sector'],
            'Kapitalizacja': market_cap_str,
            'Wolumen (x średnia)': f"{stock['volume_ratio']}x"
        })
    
    # Wyświetl tabelę
    df_display = pd.DataFrame(table_data)
    st.dataframe(df_display, use_container_width=True, height=400)
    
    # Sidebar z listą spółek
    with st.sidebar:
        st.markdown("---")
        st.subheader("📋 Kliknij aby analizować:")
        
        # Grupuj według kategorii
        categories = [
            ('💎 SUPER DIAMENTY (RSI <25)', super_oversold),
            ('💍 DIAMENTY (RSI <30)', oversold),
            ('🟡 ŻÓŁTE (RSI <35)', mild_oversold),
            ('🟤 OBSERWACJA (RSI <40)', watchlist)
        ]
        
        for cat_name, cat_stocks in categories:
            if cat_stocks:
                st.markdown(f"**{cat_name}**")
                for stock in cat_stocks:
                    if st.button(
                        f"{stock['icon']} {stock['symbol']} ({stock['rsi']:.1f})",
                        key=f"btn_{stock['symbol']}"
                    ):
                        st.session_state.selected_stock = stock

# Szczegółowa analiza wybranej spółki
if 'selected_stock' in st.session_state:
    stock = st.session_state.selected_stock
    
    st.markdown("---")
    st.subheader(f"{stock['icon']} Szczegółowa Analiza: {stock['symbol']}")
    
    # Metryki
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("💰 Cena", f"${stock['price']}")
    with col2:
        delta_text = "Wyprzedane" if stock['rsi'] < 30 else "Neutralne"
        st.metric("📊 RSI", f"{stock['rsi']}", delta=delta_text)
    with col3:
        st.metric("📈 EMA 50", f"${stock['ema_50']}")
    with col4:
        st.metric("📉 EMA 200", f"${stock['ema_200']}")
    with col5:
        market_cap_display = f"${stock['market_cap']/1e9:.1f}B" if stock['market_cap'] > 0 else "N/A"
        st.metric("🏢 Kapitalizacja", market_cap_display)
    
    col6, col7, col8 = st.columns(3)
    
    with col6:
        st.metric("📊 Wolumen", f"{stock['volume']:,}")
    with col7:
        st.metric("🔥 Wol./Średnia", f"{stock['volume_ratio']}x")
    with col8:
        price_to_ema = ((stock['price'] / stock['ema_200']) - 1) * 100
        st.metric("📍 Cena vs EMA200", f"{price_to_ema:+.1f}%")
    
    # Wykresy
    st.plotly_chart(create_simple_candlestick_chart(stock), use_container_width=True)
    st.plotly_chart(create_rsi_chart(stock), use_container_width=True)
    
    # Analiza
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("🎯 Sygnały Handlowe")
        
        if stock['rsi'] < 25:
            st.success("🔥 **SILNY SYGNAŁ KUPNA** - RSI poniżej 25")
        elif stock['rsi'] < 30:
            st.success("💚 **SYGNAŁ KUPNA** - RSI poniżej 30")
        elif stock['rsi'] < 35:
            st.warning("🟡 **MOŻLIWOŚĆ KUPNA** - RSI poniżej 35")
        else:
            st.info("🟤 **OBSERWACJA** - RSI poniżej 40")
            
        if stock['price'] < stock['ema_200']:
            st.warning("⚠️ Cena poniżej EMA200 - trend spadkowy")
        else:
            st.success("✅ Cena powyżej EMA200 - trend wzrostowy")
            
        if stock['volume_ratio'] > 1.5:
            st.info("🔥 Podwyższony wolumen")
    
    with col_right:
        st.subheader("📊 Kluczowe Dane")
        
        df_recent = stock['data'].tail(60)
        resistance = df_recent['High'].quantile(0.8)
        support = df_recent['Low'].quantile(0.2)
        
        st.write(f"**🔴 Opór:** ${resistance:.2f}")
        st.write(f"**🟢 Wsparcie:** ${support:.2f}")
        
        upside_potential = ((resistance / stock['price']) - 1) * 100
        st.write(f"**📈 Potencjał wzrostu:** {upside_potential:.1f}%")
        
        st.write(f"**🏭 Sektor:** {stock['sector']}")

else:
    # Strona startowa
    st.info("🚀 **Jak zacząć:** Kliknij 'Skanuj Diamenty' w panelu bocznym")
    
    with st.expander("📚 Instrukcja obsługi", expanded=True):
        st.markdown("""
        ### 💎 Co to są "diamenty"?
        - **💎 Super Diamenty (RSI <25)**: Ekstremalne wyprzedanie
        - **💍 Diamenty (RSI <30)**: Silne wyprzedanie  
        - **🟡 Żółte (RSI <35)**: Lekkie wyprzedanie
        - **🟤 Obserwacja (RSI <40)**: Lista obserwacji
        
        ### 📊 Jak interpretować:
        - **RSI poniżej 30** = akcja wyprzedana, możliwa okazja
        - **EMA 200** = długoterminowy trend
        - **Zwiększony wolumen** = potwierdza ruch cenowy
        
        ### 🎯 Strategia:
        1. Szukaj RSI <30 przy wsparciu
        2. Sprawdź trend na EMA 200
        3. Potwierdź wolumenem
        4. Ustaw stop-loss poniżej wsparcia
        """)
    
    st.warning("""
    ⚠️ **DISCLAIMER**: Narzędzie edukacyjne. Nie stanowi porady inwestycyjnej.
    Zawsze rób własną analizę przed inwestycją.
    """)

# Footer
st.markdown("---")
st.markdown(
    f"<div style='text-align: center; color: #64748b;'>"
    f"💎 NASDAQ Diamond Scanner | {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    f"</div>", 
    unsafe_allow_html=True
)
