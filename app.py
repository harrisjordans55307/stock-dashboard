import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import threading
import queue
import time

# Konfiguracja strony
st.set_page_config(
    page_title="💎 NASDAQ Diamond Scanner", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS dla lepszego wyglądu
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
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #10b981, #34d399);
    }
</style>
""", unsafe_allow_html=True)

# Funkcje pomocnicze
@st.cache_data(ttl=300)  # Cache na 5 minut
def calculate_rsi(series, period=14):
    """Oblicza RSI z optymalizacją"""
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
    """Oblicza EMA z optymalizacją"""
    if len(series) < period:
        return series.ewm(span=min(period, len(series)), adjust=False).mean()
    return series.ewm(span=period, adjust=False).mean()

def calculate_support_resistance(df, window=20):
    """Oblicza poziomy wsparcia i oporu"""
    highs = df['High'].rolling(window=window).max()
    lows = df['Low'].rolling(window=window).min()
    return highs, lows

@st.cache_data(ttl=600)  # Cache na 10 minut
def get_extended_nasdaq_symbols():
    """Rozszerzona lista symboli NASDAQ z różnych sektorów"""
    return [
        # Tech Giants
        'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'META', 'NVDA', 'TSLA', 'AMD', 'INTC',
        'ORCL', 'IBM', 'CSCO', 'ADBE', 'CRM', 'NOW', 'SNOW', 'ZM', 'TEAM', 'OKTA',
        'DDOG', 'CRWD', 'ZS', 'PANW', 'FTNT', 'VRNS', 'CHKP', 'NET', 'CFLT', 'S',
        
        # Finance
        'JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'BLK', 'SCHW', 'AXP', 'V', 'MA', 'PYPL',
        'SQ', 'AFRM', 'SOFI', 'LC', 'UPST', 'HOOD', 'COIN', 'MSTR',
        
        # Healthcare & Biotech
        'JNJ', 'PFE', 'MRK', 'ABBV', 'LLY', 'ABT', 'MDT', 'BMY', 'DHR', 'UNH',
        'GILD', 'AMGN', 'BIIB', 'REGN', 'VRTX', 'MRNA', 'BNTX', 'ILMN', 'ISRG',
        
        # Consumer & Retail
        'WMT', 'KO', 'PEP', 'PG', 'NKE', 'MCD', 'SBUX', 'COST', 'TGT', 'HD',
        'AMZN', 'EBAY', 'ETSY', 'SHOP', 'ROKU', 'NFLX', 'DIS', 'CMCSA',
        
        # Energy & Commodities
        'XOM', 'CVX', 'COP', 'SLB', 'HAL', 'KMI', 'OXY', 'MPC', 'PSX', 'VLO',
        
        # Industrial & Transport
        'BA', 'CAT', 'GE', 'HON', 'LMT', 'MMM', 'UNP', 'UPS', 'FDX', 'CSX',
        'TSLA', 'F', 'GM', 'RIVN', 'LCID', 'NIO', 'XPEV', 'LI',
        
        # Semiconductors & Hardware
        'QCOM', 'TXN', 'AVGO', 'AMAT', 'LRCX', 'KLAC', 'MU', 'MCHP', 'ADI', 'MRVL',
        'ON', 'SWKS', 'QRVO', 'MPWR', 'ENPH', 'SEDG',
        
        # Software & Services
        'INTU', 'ADP', 'FIS', 'FISV', 'WDAY', 'VEEV', 'TWLO', 'DOCU', 'ZEN', 'PD',
        'PLTR', 'U', 'RBLX', 'UBER', 'LYFT', 'DASH', 'ABNB',
        
        # Communication & Media
        'CCI', 'AMT', 'TMUS', 'VZ', 'T', 'NFLX', 'SPOT', 'PINS', 'SNAP', 'TWTR',
        
        # REITs & Infrastructure
        'PLD', 'AMT', 'CCI', 'EQIX', 'DLR', 'PSA', 'EXR', 'AVB', 'EQR', 'UDR'
    ]

def analyze_stock_batch(symbols_batch, results_queue):
    """Analizuje grupę symboli w osobnym wątku"""
    for symbol in symbols_batch:
        try:
            result = analyze_single_stock(symbol)
            if result and result['rsi'] <= 40:  # Tylko RSI <= 40
                results_queue.put(result)
        except:
            continue

@st.cache_data(ttl=300)
def analyze_single_stock(symbol):
    """Analizuje pojedynczą spółkę z dodatkowymi wskaźnikami"""
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
        
        # Sprawdź trend EMA
        latest = df.iloc[-1]
        prev = df.iloc[-10] if len(df) >= 10 else df.iloc[-2]
        
        ema_trend = "📈" if latest['ema_50'] > prev['ema_50'] else "📉"
        volume_status = "🔥" if latest['Volume'] > latest['volume_sma'] * 1.5 else "📊"
        
        # Określ kategorię RSI
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
        elif latest['rsi'] <= 40:
            category = "watchlist"
            icon = "🟤"
            color = "#d97706"
        else:
            return None
            
        # Pobierz informacje o spółce
        info = ticker.info
        market_cap = info.get('marketCap', 0)
        sector = info.get('sector', 'N/A')
        
        return {
            'symbol': symbol,
            'price': round(latest['Close'], 2),
            'rsi': round(latest['rsi'], 2),
            'ema_50': round(latest['ema_50'], 2),
            'ema_200': round(latest['ema_200'], 2),
            'volume': int(latest['Volume']),
            'avg_volume': int(latest['volume_sma']),
            'market_cap': market_cap,
            'sector': sector,
            'category': category,
            'icon': icon,
            'color': color,
            'ema_trend': ema_trend,
            'volume_status': volume_status,
            'data': df
        }
        
    except Exception as e:
        return None

def find_diamond_stocks_threaded():
    """Znajdź diamenty używając wielowątkowości"""
    symbols = get_extended_nasdaq_symbols()
    results_queue = queue.Queue()
    threads = []
    
    # Podziel symbole na grupy dla wątków
    batch_size = 20
    batches = [symbols[i:i + batch_size] for i in range(0, len(symbols), batch_size)]
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Uruchom wątki
    for i, batch in enumerate(batches):
        thread = threading.Thread(target=analyze_stock_batch, args=(batch, results_queue))
        thread.start()
        threads.append(thread)
    
    # Zbieraj wyniki podczas pracy wątków
    results = []
    processed = 0
    total = len(symbols)
    
    while processed < total:
        try:
            result = results_queue.get(timeout=0.1)
            results.append(result)
            processed += 1
            
            progress = processed / total
            progress_bar.progress(progress)
            status_text.text(f"🔍 Znaleziono {len(results)} diamentów... ({processed}/{total})")
            
        except queue.Empty:
            # Sprawdź czy wątki jeszcze pracują
            alive_threads = [t for t in threads if t.is_alive()]
            if not alive_threads and results_queue.empty():
                break
            time.sleep(0.1)
    
    # Poczekaj na zakończenie wszystkich wątków
    for thread in threads:
        thread.join()
    
    progress_bar.empty()
    status_text.empty()
    
    return sorted(results, key=lambda x: x['rsi'])

def create_advanced_chart(stock_data):
    """Tworzy zaawansowany wykres z wieloma wskaźnikami"""
    df = stock_data['data'].tail(120)  # Ostatnie 120 dni
    
    # Twórz subplot z RSI na dole
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxis=True,
        vertical_spacing=0.1,
        subplot_titles=(f"📈 {stock_data['symbol']} - Analiza Techniczna", "📊 RSI (14)"),
        row_heights=[0.7, 0.3]
    )
    
    # Wykres świecowy
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name=stock_data['symbol'],
            increasing_line_color='#10b981',
            decreasing_line_color='#ef4444'
        ),
        row=1, col=1
    )
    
    # EMA 50
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['ema_50'],
            name='EMA 50',
            line=dict(color='#3b82f6', width=2)
        ),
        row=1, col=1
    )
    
    # EMA 200
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['ema_200'],
            name='EMA 200',
            line=dict(color='#f59e0b', width=3)
        ),
        row=1, col=1
    )
    
    # RSI
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['rsi'],
            name='RSI (14)',
            line=dict(color='#8b5cf6', width=2)
        ),
        row=2, col=1
    )
    
    # Linie RSI
    for level, color, name in [(70, '#ef4444', 'Przekupione (70)'), 
                               (30, '#10b981', 'Wyprzedane (30)'),
                               (25, '#059669', 'Super Wyprzedane (25)')]:
        fig.add_hline(y=level, line_dash="dash", line_color=color, 
                     annotation_text=name, row=2, col=1)
    
    # Podświetl aktualny RSI
    current_rsi = df['rsi'].iloc[-1]
    fig.add_scatter(
        x=[df.index[-1]], y=[current_rsi],
        mode='markers',
        marker=dict(size=12, color=stock_data['color'], symbol='diamond'),
        name=f"Aktualny RSI: {current_rsi:.1f}",
        row=2, col=1
    )
    
    # Formatowanie
    fig.update_layout(
        title=f"{stock_data['icon']} {stock_data['symbol']} | Sektor: {stock_data['sector']} | RSI: {stock_data['rsi']}",
        height=800,
        template='plotly_dark',
        xaxis_rangeslider_visible=False,
        font=dict(size=12)
    )
    
    fig.update_yaxes(title_text="Cena ($)", row=1, col=1)
    fig.update_yaxes(title_text="RSI", range=[0, 100], row=2, col=1)
    
    return fig

# UI Aplikacji
st.title("💎 Skaner Diamentów NASDAQ Pro")
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
        with st.spinner("🚀 Szukam diamentów w NASDAQ..."):
            diamond_stocks = find_diamond_stocks_threaded()
            
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
        st.metric("💎 Super Wyprzedane (<25)", len(super_oversold), 
                 delta=f"Śr. RSI: {np.mean([s['rsi'] for s in super_oversold]):.1f}" if super_oversold else "0")
    
    with col2:
        st.metric("💍 Wyprzedane (<30)", len(oversold),
                 delta=f"Śr. RSI: {np.mean([s['rsi'] for s in oversold]):.1f}" if oversold else "0")
    
    with col3:
        st.metric("🟡 Lekko Wyprzedane (<35)", len(mild_oversold),
                 delta=f"Śr. RSI: {np.mean([s['rsi'] for s in mild_oversold]):.1f}" if mild_oversold else "0")
    
    with col4:
        st.metric("🟤 Lista Obserwacji (<40)", len(watchlist),
                 delta=f"Śr. RSI: {np.mean([s['rsi'] for s in watchlist]):.1f}" if watchlist else "0")
    
    # Tabela wyników
    st.subheader("📊 Znalezione Diamenty")
    
    # Przygotuj dane do tabeli
    table_data = []
    for stock in stocks:
        market_cap_str = f"${stock['market_cap']/1e9:.1f}B" if stock['market_cap'] > 0 else "N/A"
        volume_ratio = stock['volume'] / stock['avg_volume'] if stock['avg_volume'] > 0 else 1
        
        table_data.append({
            'Symbol': f"{stock['icon']} {stock['symbol']}",
            'Cena': f"${stock['price']}",
            'RSI': f"{stock['rsi']:.1f}",
            'Sektor': stock['sector'][:15] + "..." if len(stock['sector']) > 15 else stock['sector'],
            'Kap. (B$)': market_cap_str,
            'Wolumen': f"{stock['volume_status']} {volume_ratio:.1f}x",
            'Trend EMA': stock['ema_trend']
        })
    
    # Wyświetl tabelę z możliwością sortowania
    df_display = pd.DataFrame(table_data)
    st.dataframe(
        df_display, 
        use_container_width=True,
        height=400
    )
    
    # Sidebar z listą spółek
    with st.sidebar:
        st.markdown("---")
        st.subheader("📋 Kliknij aby analizować:")
        
        # Grupuj według kategorii
        categories = {
            'super_oversold': ('💎 SUPER DIAMENTY (RSI <25)', super_oversold),
            'oversold': ('💍 DIAMENTY (RSI <30)', oversold),
            'mild_oversold': ('🟡 ŻÓŁTE (RSI <35)', mild_oversold),
            'watchlist': ('🟤 OBSERWACJA (RSI <40)', watchlist)
        }
        
        for cat_key, (cat_name, cat_stocks) in categories.items():
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
    
    # Metryki w dwóch rzędach
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("💰 Cena", f"${stock['price']}")
    with col2:
        st.metric("📊 RSI", f"{stock['rsi']}", 
                 delta="Wyprzedane" if stock['rsi'] < 30 else "Neutralne")
    with col3:
        st.metric("📈 EMA 50", f"${stock['ema_50']}")
    with col4:
        st.metric("📉 EMA 200", f"${stock['ema_200']}")
    with col5:
        market_cap_display = f"${stock['market_cap']/1e9:.1f}B" if stock['market_cap'] > 0 else "N/A"
        st.metric("🏢 Kapitalizacja", market_cap_display)
    
    col6, col7, col8, col9, col10 = st.columns(5)
    
    with col6:
        st.metric("📊 Wolumen", f"{stock['volume']:,}")
    with col7:
        vol_ratio = stock['volume'] / stock['avg_volume'] if stock['avg_volume'] > 0 else 1
        st.metric("🔥 Wol./Średnia", f"{vol_ratio:.1f}x")
    with col8:
        st.metric("🏭 Sektor", stock['sector'][:10] + "..." if len(stock['sector']) > 10 else stock['sector'])
    with col9:
        price_to_ema = ((stock['price'] / stock['ema_200']) - 1) * 100
        st.metric("📍 Cena vs EMA200", f"{price_to_ema:+.1f}%")
    with col10:
        ema_position = "🟢 Powyżej" if stock['price'] > stock['ema_200'] else "🔴 Poniżej"
        st.metric("📊 Pozycja vs EMA200", ema_position)
    
    # Zaawansowany wykres
    st.plotly_chart(
        create_advanced_chart(stock), 
        use_container_width=True,
        config={'displayModeBar': True}
    )
    
    # Dodatkowe analizy
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("🎯 Sygnały Handlowe")
        
        signals = []
        if stock['rsi'] < 25:
            signals.append("🔥 **SILNY SYGNAŁ KUPNA** - RSI poniżej 25")
        elif stock['rsi'] < 30:
            signals.append("💚 **SYGNAŁ KUPNA** - RSI poniżej 30")
        elif stock['rsi'] < 35:
            signals.append("🟡 **MOŻLIWOŚĆ KUPNA** - RSI poniżej 35")
            
        if stock['price'] < stock['ema_200']:
            signals.append("⚠️ Cena poniżej EMA200 - długoterminowy trend spadkowy")
        else:
            signals.append("✅ Cena powyżej EMA200 - długoterminowy trend wzrostowy")
            
        if stock['volume'] > stock['avg_volume'] * 1.5:
            signals.append("🔥 Podwyższony wolumen - zwiększone zainteresowanie")
            
        for signal in signals:
            st.markdown(signal)
    
    with col_right:
        st.subheader("⚡ Kluczowe Poziomy")
        
        df_recent = stock['data'].tail(60)
        resistance = df_recent['High'].quantile(0.8)
        support = df_recent['Low'].quantile(0.2)
        
        st.markdown(f"**🔴 Opór:** ${resistance:.2f}")
        st.markdown(f"**🟢 Wsparcie:** ${support:.2f}")
        st.markdown(f"**📊 Zakres:** ${resistance - support:.2f} ({((resistance/support - 1) * 100):.1f}%)")
        
        # Potencjał wzrostu do oporu
        upside_potential = ((resistance / stock['price']) - 1) * 100
        st.markdown(f"**📈 Potencjał do oporu:** {upside_potential:.1f}%")

else:
    # Strona startowa
    st.info("🚀 **Jak zacząć:** Kliknij 'Skanuj Diamenty' w panelu bocznym")
    
    # Instrukcja
    with st.expander("📚 Jak korzystać ze skanera", expanded=True):
        st.markdown("""
        ### 💎 Co to są "diamenty"?
        - **💎 Super Diamenty (RSI <25)**: Ekstremalne wyprzedanie - największe okazje
        - **💍 Diamenty (RSI <30)**: Silne wyprzedanie - dobre okazje zakupu  
        - **🟡 Żółte (RSI <35)**: Lekkie wyprzedanie - warto obserwować
        - **🟤 Obserwacja (RSI <40)**: Możliwe okazje - lista obserwacji
        
        ### 📊 Dodatkowe wskaźniki:
        - **EMA 50/200**: Średnie kroczące pokazujące trend
        - **Wolumen**: Potwierdza siłę ruchu cenowego
        - **Poziomy wsparcia/oporu**: Kluczowe obszary cenowe
        
        ### 🎯 Jak handlować:
        1. Szukaj akcji z RSI <30 (wyprzedane)
        2. Sprawdź czy cena jest blisko wsparcia
        3. Potwierdź zwiększonym wolumenem
        4. Ustaw stop-loss poniżej wsparcia
        5. Cel: poziom oporu lub RSI ~70
        """)
    
    # Disclaimer
    st.warning("""
    ⚠️ **DISCLAIMER**: To narzędzie służy wyłącznie celom edukacyjnym i informacyjnym. 
    Nie stanowi porady inwestycyjnej. Zawsze przeprowadź własną analizę przed podjęciem decyzji inwestycyjnych.
    """)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #64748b;'>"
    "💎 NASDAQ Diamond Scanner Pro | Dane z Yahoo Finance | "
    f"Ostatnia aktualizacja: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    "</div>", 
    unsafe_allow_html=True
)
