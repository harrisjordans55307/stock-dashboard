import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import requests
from io import StringIO

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

@st.cache_data(ttl=86400)  # Cache na 24h
def get_all_nasdaq_symbols():
    """Pobierz pełną listę spółek NASDAQ - tylko darmowe źródła"""
    try:
        # Źródło 1: Publiczne repozytorium GitHub
        url = "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/nasdaq/nasdaq_tickers.csv"
        df = pd.read_csv(url)
        symbols = df['ticker'].tolist()
        st.success(f"✅ Pobrano {len(symbols)} spółek z NASDAQ")
        return symbols[:1000]  # Limit dla wydajności
    except Exception as e1:
        try:
            # Źródło 2: Alternatywne repozytorium
            url = "https://raw.githubusercontent.com/shilewenuw/get_all_tickers/master/get_all_tickers/tickers.csv"
            response = requests.get(url)
            df = pd.read_csv(StringIO(response.text))
            symbols = df['ticker'].tolist()
            st.success(f"✅ Pobrano {len(symbols)} spółek (alternatywne źródło)")
            return symbols[:1000]
        except Exception as e2:
            # Źródło 3: Lista zapasowa
            st.warning("⚠️ Używam listy zapasowej")
            return [
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'AMD', 'INTC', 'ORCL',
                'IBM', 'CSCO', 'ADBE', 'CRM', 'JPM', 'BAC', 'WFC', 'C', 'GS', 'MS',
                'BLK', 'SCHW', 'AXP', 'V', 'MA', 'PYPL', 'SQ', 'JNJ', 'PFE', 'MRK',
                'ABBV', 'LLY', 'ABT', 'MDT', 'BMY', 'UNH', 'GILD', 'AMGN', 'BIIB', 'REGN',
                'VRTX', 'MRNA', 'BNTX', 'WMT', 'KO', 'PEP', 'PG', 'NKE', 'MCD', 'SBUX',
                'COST', 'TGT', 'HD', 'EBAY', 'ETSY', 'SHOP', 'ROKU', 'NFLX', 'DIS', 'CMCSA',
                'TMUS', 'XOM', 'CVX', 'COP', 'SLB', 'HAL', 'KMI', 'OXY', 'MPC', 'PSX',
                'VLO', 'BA', 'CAT', 'GE', 'HON', 'LMT', 'MMM', 'UNP', 'UPS', 'FDX',
                'INTU', 'ADP', 'WDAY', 'VEEV', 'TWLO', 'DOCU', 'PLTR', 'U', 'RBLX',
                'UBER', 'LYFT', 'DASH', 'ABNB', 'ZS', 'CRWD', 'PANW', 'FTNT', 'CCI', 'AMT',
                'VZ', 'T', 'SPOT', 'PINS', 'SNAP', 'DE', 'RTX', 'NOC', 'GD', 'CSX'
            ]

@st.cache_data(ttl=3600)  # Cache na 1h
def get_top_symbols_by_volume(symbol_list, top_n=700):
    """Sortuj symbole po wolumenie - tylko yfinance"""
    symbol_data = []
    
    progress_text = st.empty()
    progress_bar = st.progress(0)
    
    # Sprawdź więcej symboli dla lepszego pokrycia
    test_symbols = symbol_list[:800]
    
    for i, symbol in enumerate(test_symbols):
        try:
            progress_text.text(f"Analizuję wolumen {symbol}... ({i+1}/{len(test_symbols)})")
            progress_bar.progress((i + 1) / len(test_symbols))
            
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1mo")
            
            if not hist.empty and len(hist) > 5:
                avg_volume = hist['Volume'].mean()
                current_price = hist['Close'].iloc[-1]
                
                # Filtruj tylko spółki z sensowną ceną i wolumenem
                if current_price > 1.0 and avg_volume > 10000:
                    symbol_data.append({
                        'symbol': symbol,
                        'volume': float(avg_volume),
                        'price': float(current_price)
                    })
                
        except Exception as e:
            continue
    
    progress_text.empty()
    progress_bar.empty()
    
    # Posortuj po wolumenie
    symbol_data.sort(key=lambda x: x['volume'], reverse=True)
    
    return [s['symbol'] for s in symbol_data[:top_n]]

@st.cache_data(ttl=300)
def analyze_single_stock(symbol, rsi_min=25, rsi_max=40):
    """Analizuje pojedynczą spółkę - tylko yfinance"""
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
        
        latest = df.iloc[-1]
        
        # Sprawdź czy RSI jest w interesującym zakresie
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
        
        # Oblicz prosty potencjał kupna
        buy_potential = calculate_simple_buy_potential(latest, df)
        
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

def calculate_simple_buy_potential(latest, df):
    """Prosty potencjał kupna 0-100"""
    score = 0
    
    # RSI (0-30)
    if latest['rsi'] <= 25:
        score += 30
    elif latest['rsi'] <= 30:
        score += 20
    elif latest['rsi'] <= 35:
        score += 10
    
    # Price vs EMA200 (0-30)
    price_vs_ema = (latest['Close'] / latest['ema_200']) - 1
    if price_vs_ema > 0:
        score += 30
    elif price_vs_ema > -0.05:
        score += 20
    elif price_vs_ema > -0.10:
        score += 10
    
    # Volume ratio (0-20)
    if latest['volume_ratio'] > 2.0:
        score += 20
    elif latest['volume_ratio'] > 1.5:
        score += 15
    elif latest['volume_ratio'] > 1.0:
        score += 10
    
    # Trend z 30 dni (0-20)
    recent_data = df.tail(30)
    if len(recent_data) > 1:
        price_trend = (recent_data['Close'].iloc[-1] / recent_data['Close'].iloc[0]) - 1
        if price_trend > 0:
            score += 20
        elif price_trend > -0.05:
            score += 10
    
    return min(score, 100)

def find_diamond_stocks(rsi_min=25, rsi_max=40, min_market_cap=0, max_market_cap=float('inf')):
    """Znajdź diamenty - tylko yfinance i darmowe źródła"""
    # Pobierz pełną listę spółek NASDAQ
    all_symbols = get_all_nasdaq_symbols()
    
    # Posortuj po wolumenie
    top_symbols = get_top_symbols_by_volume(all_symbols, 700)
    
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
    
    # RSI
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
    
    # Przycisk skanowania
    st.markdown("---")
    if st.button("🔍 Skanuj teraz", type="primary", use_container_width=True):
        with st.spinner("🚀 Analizuję spółki NASDAQ..."):
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
            else:
                st.warning("⚠️ Brak spółek spełniających kryteria")
                
                # Debugowanie
                with st.spinner("Sprawdzam alternatywne kryteria..."):
                    test_stocks = find_diamond_stocks(rsi_min=0, rsi_max=100, min_market_cap=0, max_market_cap=float('inf'))
                    if test_stocks:
                        st.info(f"Znaleziono {len(test_stocks)} spółek bez filtrów RSI")
                        low_rsi_stocks = [s for s in test_stocks if 20 <= s['rsi'] <= 50][:5]
                        if low_rsi_stocks:
                            st.success("Przykładowe spółki z RSI 20-50:")
                            for stock in low_rsi_stocks:
                                st.write(f"  {stock['symbol']}: RSI {stock['rsi']}")
                    else:
                        st.error("Nie znaleziono żadnych spółek")

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

else:
    st.info("🚀 Kliknij 'Skanuj teraz' w panelu bocznym, aby rozpocząć analizę")

# Footer
st.markdown(f"<div style='text-align: center; color: #64748b; font-size: 12px; margin-top: 20px;'>💎 Skaner Diamentów | {datetime.now().strftime('%Y-%m-%d %H:%M')} | Dane: Yahoo Finance</div>", unsafe_allow_html=True)
