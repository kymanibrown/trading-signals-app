import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta

# Configure page
st.set_page_config(
    page_title="AI Trading Signals",
    page_icon="📈",
    layout="wide"
)

def calculate_rsi(prices, window=14):
    """Calculate RSI"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calculate MACD"""
    ema_fast = prices.ewm(span=fast).mean()
    ema_slow = prices.ewm(span=slow).mean()
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal).mean()
    histogram = macd - signal_line
    return macd, signal_line, histogram

def calculate_bollinger_bands(prices, window=20, num_std=2):
    """Calculate Bollinger Bands"""
    rolling_mean = prices.rolling(window=window).mean()
    rolling_std = prices.rolling(window=window).std()
    upper_band = rolling_mean + (rolling_std * num_std)
    lower_band = rolling_mean - (rolling_std * num_std)
    return upper_band, rolling_mean, lower_band

def get_market_data(symbol, market_type="forex"):
    """Get market data from Yahoo Finance"""
    try:
        if market_type == "forex":
            # Forex symbols
            symbol_map = {
                "EUR/USD": "EURUSD=X",
                "GBP/USD": "GBPUSD=X", 
                "USD/JPY": "USDJPY=X",
                "AUD/USD": "AUDUSD=X",
                "USD/CAD": "USDCAD=X"
            }
            yf_symbol = symbol_map.get(symbol, f"{symbol.replace('/', '')}=X")
        else:
            # Crypto symbols
            symbol_map = {
                "BTC": "BTC-USD",
                "ETH": "ETH-USD",
                "ADA": "ADA-USD", 
                "DOT": "DOT-USD",
                "LINK": "LINK-USD"
            }
            yf_symbol = symbol_map.get(symbol, f"{symbol}-USD")
        
        st.info(f"📊 Fetching {yf_symbol} data...")
        
        ticker = yf.Ticker(yf_symbol)
        df = ticker.history(period="5d", interval="15m")
        
        if df.empty:
            st.error(f"❌ No data found for {symbol}")
            return None
        
        # Rename columns properly
        column_mapping = {
            'Open': 'open',
            'High': 'high', 
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        }
        
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns:
                df = df.rename(columns={old_col: new_col})
        
        # Select only the columns we need
        df = df[['open', 'high', 'low', 'close']]
        
        st.success(f"✅ Successfully fetched {len(df)} data points")
        return df
        
    except Exception as e:
        st.error(f"❌ Error fetching data: {str(e)}")
        return None

def generate_signals(df):
    """Generate trading signals"""
    if df is None or len(df) < 20:
        return None
    
    # Calculate indicators
    df['rsi'] = calculate_rsi(df['close'])
    df['macd'], df['macd_signal'], df['macd_hist'] = calculate_macd(df['close'])
    df['bb_upper'], df['bb_middle'], df['bb_lower'] = calculate_bollinger_bands(df['close'])
    df['sma_20'] = df['close'].rolling(window=20).mean()
    df['sma_50'] = df['close'].rolling(window=50).mean()
    
    # Generate signals
    signals = []
    
    # RSI signals
    if df['rsi'].iloc[-1] < 30:
        signals.append(("RSI", "BUY", "Oversold", 0.7))
    elif df['rsi'].iloc[-1] > 70:
        signals.append(("RSI", "SELL", "Overbought", 0.7))
    
    # MACD signals
    if len(df) > 1:
        if df['macd'].iloc[-1] > df['macd_signal'].iloc[-1] and df['macd'].iloc[-2] <= df['macd_signal'].iloc[-2]:
            signals.append(("MACD", "BUY", "Bullish Crossover", 0.8))
        elif df['macd'].iloc[-1] < df['macd_signal'].iloc[-1] and df['macd'].iloc[-2] >= df['macd_signal'].iloc[-2]:
            signals.append(("MACD", "SELL", "Bearish Crossover", 0.8))
    
    # Bollinger Bands signals
    if df['close'].iloc[-1] < df['bb_lower'].iloc[-1]:
        signals.append(("BB", "BUY", "Below Lower Band", 0.6))
    elif df['close'].iloc[-1] > df['bb_upper'].iloc[-1]:
        signals.append(("BB", "SELL", "Above Upper Band", 0.6))
    
    # Calculate overall signal
    buy_signals = [s for s in signals if s[1] == "BUY"]
    sell_signals = [s for s in signals if s[1] == "SELL"]
    
    buy_strength = sum([s[3] for s in buy_signals]) / len(buy_signals) if buy_signals else 0
    sell_strength = sum([s[3] for s in sell_signals]) / len(sell_signals) if sell_signals else 0
    
    overall_signal = "NEUTRAL"
    if buy_strength > sell_strength and buy_strength > 0.6:
        overall_signal = "BUY"
    elif sell_strength > buy_strength and sell_strength > 0.6:
        overall_signal = "SELL"
    
    return {
        'signals': signals,
        'overall': overall_signal,
        'buy_strength': buy_strength,
        'sell_strength': sell_strength,
        'data': df
    }

def create_chart(df, signals_data):
    """Create trading chart"""
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=('Price & Indicators', 'RSI', 'MACD')
    )
    
    # Candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='Price'
        ),
        row=1, col=1
    )
    
    # Bollinger Bands
    fig.add_trace(go.Scatter(x=df.index, y=df['bb_upper'], line=dict(color='gray', dash='dash'), name='BB Upper'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['bb_middle'], line=dict(color='blue'), name='BB Middle'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['bb_lower'], line=dict(color='gray', dash='dash'), name='BB Lower'), row=1, col=1)
    
    # Moving averages
    fig.add_trace(go.Scatter(x=df.index, y=df['sma_20'], line=dict(color='orange'), name='SMA 20'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['sma_50'], line=dict(color='red'), name='SMA 50'), row=1, col=1)
    
    # RSI
    fig.add_trace(go.Scatter(x=df.index, y=df['rsi'], line=dict(color='purple'), name='RSI'), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
    
    # MACD
    fig.add_trace(go.Scatter(x=df.index, y=df['macd'], line=dict(color='blue'), name='MACD'), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['macd_signal'], line=dict(color='red'), name='Signal'), row=3, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df['macd_hist'], name='Histogram'), row=3, col=1)
    
    fig.update_layout(
        title="Trading Analysis Dashboard",
        xaxis_rangeslider_visible=False,
        height=700
    )
    
    return fig

# Main app
def main():
    st.title("🤖 AI Trading Signal Generator")
    st.markdown("### Real-time forex and crypto trading signals powered by technical analysis")
    
    # Sidebar
    st.sidebar.header("Settings")
    
    market_type = st.sidebar.selectbox("Market Type", ["Forex", "Crypto"])
    
    if market_type == "Forex":
        symbol = st.sidebar.selectbox("Currency Pair", 
                                     ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD"])
    else:
        symbol = st.sidebar.selectbox("Cryptocurrency", 
                                     ["BTC", "ETH", "ADA", "DOT", "LINK"])
    
    # Test data source
    if st.sidebar.button("🔑 Test Data Source"):
        with st.spinner("Testing Yahoo Finance..."):
            try:
                ticker = yf.Ticker("AAPL")
                data = ticker.history(period="1d")
                if not data.empty:
                    st.success("✅ Yahoo Finance is working correctly")
                else:
                    st.error("❌ No data received from Yahoo Finance")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
    
    # Generate signals
    if st.sidebar.button("Generate Signals"):
        with st.spinner("Fetching market data..."):
            df = get_market_data(symbol, market_type.lower())
            
            if df is not None:
                signals_data = generate_signals(df)
                
                if signals_data:
                    # Display signals
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        signal_color = {"BUY": "🟢", "SELL": "🔴", "NEUTRAL": "🟡"}[signals_data['overall']]
                        st.metric("Overall Signal", f"{signal_color} {signals_data['overall']}")
                    
                    with col2:
                        st.metric("Buy Strength", f"{signals_data['buy_strength']:.2f}")
                    
                    with col3:
                        st.metric("Sell Strength", f"{signals_data['sell_strength']:.2f}")
                    
                    # Display individual signals
                    st.subheader("📊 Signal Details")
                    for indicator, signal, reason, strength in signals_data['signals']:
                        emoji = "🟢" if signal == "BUY" else "🔴"
                        st.write(f"{emoji} **{indicator}**: {signal} - {reason} (Strength: {strength:.1f})")
                    
                    # Display chart
                    st.subheader("📈 Technical Analysis Chart")
                    chart = create_chart(signals_data['data'], signals_data)
                    st.plotly_chart(chart, use_container_width=True)
                    
                    # Current price info
                    current_price = df['close'].iloc[-1]
                    price_change = df['close'].iloc[-1] - df['close'].iloc[-2]
                    price_change_pct = (price_change / df['close'].iloc[-2]) * 100
                    
                    st.subheader("💰 Current Market Data")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Price", f"{current_price:.5f}")
                    with col2:
                        st.metric("Change", f"{price_change:.5f}", f"{price_change_pct:.2f}%")
                    with col3:
                        st.metric("RSI", f"{signals_data['data']['rsi'].iloc[-1]:.1f}")
                    
                    # Risk management
                    st.subheader("⚠️ Risk Management")
                    if signals_data['overall'] != "NEUTRAL":
                        st.info(f"""
                        **Suggested Action**: {signals_data['overall']}
                        
                        **Entry Strategy**: Wait for confirmation on next candle
                        **Stop Loss**: Set 1-2% below/above entry point  
                        **Take Profit**: Target 2-3% gain for favorable risk/reward ratio
                        **Position Size**: Risk no more than 1-2% of portfolio
                        """)
                    else:
                        st.warning("Mixed signals detected. Consider waiting for clearer market direction.")

if __name__ == "__main__":
    main() 