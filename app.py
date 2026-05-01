import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import yfinance as yf
from keras.models import load_model
import streamlit as st
from sklearn.preprocessing import MinMaxScaler
import requests
from textblob import TextBlob
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ── AUTH MODULE ────────────────────────────────────────────────────────────────
from auth import auth_ui, logout, init_db

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
NEWS_API_KEY = '0b59c6c7f5f74b27bafaa828f368bb95'
st.set_page_config(page_title="Stock Market Prediction", layout="wide", page_icon="📈")

TRENDING = {
    "NVDA": "NVIDIA", "AAPL": "Apple", "GOOGL": "Alphabet",
    "TSLA": "Tesla",  "MSFT": "Microsoft", "AMZN": "Amazon",
    "META": "Meta",   "NFLX": "Netflix",   "AMD": "AMD",
    "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum",
    "RELIANCE.NS": "Reliance", "TCS.NS": "TCS", "INFY.NS": "Infosys",
    "HDFCBANK.NS": "HDFC Bank", "TATAMOTORS.NS": "Tata Motors"
}

SECTOR_TICKERS = {
    "Technology":    ["AAPL", "MSFT", "NVDA", "AMD", "INTC"],
    "EV & Auto":     ["TSLA", "GM", "F", "RIVN", "NIO"],
    "Finance":       ["JPM", "GS", "BAC", "WFC", "C"],
    "Healthcare":    ["JNJ", "PFE", "MRNA", "UNH", "ABBV"],
    "Energy":        ["XOM", "CVX", "BP", "COP", "SLB"],
    "Indian Stocks": ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "WIPRO.NS"],
}

# ── GLOSSARY OF TERMS ─────────────────────────────────────────────────────────
GLOSSARY = {
    "Ticker Symbol": "A short code (like AAPL for Apple, TSLA for Tesla) used to identify a company on the stock exchange. Think of it as a nickname for the stock.",
    "Current Price": "The latest price at which one share of the company is being bought or sold right now in the market.",
    "Daily Change": "How much the stock price has moved (up or down) compared to yesterday's closing price, shown in rupees/dollars and as a percentage.",
    "Market Cap": "Total value of all shares of a company combined. Calculated as: Share Price × Total Number of Shares. Bigger = larger company.",
    "P/E Ratio (Price-to-Earnings)": "How much investors are paying per ₹1 of company profit. Example: P/E of 25 means you pay ₹25 for every ₹1 earned. Higher P/E can mean investors expect strong future growth.",
    "EPS (Earnings Per Share)": "The profit a company makes divided by the number of shares. Higher EPS means the company is more profitable per share.",
    "52-Week High / Low": "The highest and lowest prices a stock has traded at in the past 52 weeks (1 year). Useful to see where the stock stands relative to its recent range.",
    "Dividend Yield": "The percentage return you earn just from dividends (company sharing profits). Example: 2% yield on a ₹1000 stock means ₹20/year per share.",
    "Beta": "Measures how volatile a stock is compared to the overall market. Beta > 1 means more volatile than the market; Beta < 1 means less volatile.",
    "Volume": "Number of shares traded in a day. High volume often signals strong investor interest or major news.",
    "RSI (Relative Strength Index)": "A value between 0–100 that shows if a stock is overbought (>70, possibly overpriced) or oversold (<30, possibly cheap). It helps spot potential reversals.",
    "MACD (Moving Average Convergence Divergence)": "A momentum indicator showing the relationship between two price averages. When the MACD line crosses above the signal line, it can indicate a buying opportunity, and vice versa.",
    "Bollinger Bands": "Three lines drawn around the price: a middle average, and upper/lower bands 2 standard deviations away. When price touches the upper band, it may be overbought; lower band may mean oversold.",
    "MA100 / MA200 (Moving Average)": "The average price of the stock over the last 100 or 200 days. When the price is above these averages, it generally suggests an uptrend.",
    "LSTM Prediction": "LSTM (Long Short-Term Memory) is a type of deep learning model that learns patterns in historical price data to forecast future prices. Like a very advanced pattern-recognition system.",
    "Sentiment Score": "A number from -1 to +1 indicating the overall tone of recent news about the stock. Positive means bullish news, negative means bearish news.",
    "Bullish": "Expectation that the price will go UP. Like a bull charging forward.",
    "Bearish": "Expectation that the price will go DOWN. Like a bear swiping downward.",
    "Annual Volatility": "How much the stock price fluctuates over a year. Higher volatility = higher risk and potential reward.",
    "Sharpe Ratio": "Measures return vs risk. A ratio above 1 is considered good — it means you're getting good returns for the risk you're taking.",
    "Max Drawdown": "The biggest peak-to-trough decline in price. Example: -35% means at its worst, the stock fell 35% from its high. Shows worst-case historical loss.",
    "BUY Signal": "The model predicts the price will rise significantly. Consider buying, but always do your own research.",
    "SELL Signal": "The model predicts the price will fall significantly. Consider selling to avoid losses, but always verify with other sources.",
    "HOLD Signal": "The model predicts little price movement. Best to wait and watch before making a decision.",
    "YTD Performance": "Year-To-Date performance — how much a stock has gained or lost since January 1st of the current year.",
    "Income Statement": "Shows a company's revenue, expenses, and profit over a period. Think of it as the company's report card of earnings.",
    "Balance Sheet": "A snapshot of what the company owns (assets), what it owes (liabilities), and what's left for shareholders (equity).",
    "Cash Flow": "Tracks actual cash moving in and out of the company. Positive cash flow means the company has cash to invest and pay debts.",
}

# ──────────────────────────────────────────────
# GLOBAL CSS
# ──────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@300;500;700;800&family=JetBrains+Mono:wght@300;400;600&display=swap');

html, body, [class*="css"] { font-family: 'Syne', sans-serif; background: #090e1a; color: #e0e6f0; }

@keyframes scroll { 0%{transform:translateX(100%)} 100%{transform:translateX(-100%)} }
.ticker-wrap { width:100%; overflow:hidden; background:#0b1120; border-bottom:1px solid #1e2d50; padding:8px 0; }
.ticker-move  { display:inline-block; white-space:nowrap; animation:scroll 30s linear infinite; font-size:1rem; font-weight:600; }
.ticker-item  { display:inline-block; padding:0 2.5rem; }
.up  { color:#00e676; } .down { color:#ff1744; } .neu { color:#90caf9; }

.card { background:#0d1829; border:1px solid #1e2d50; border-radius:12px; padding:1.2rem 1.5rem; margin-bottom:1rem; }
.kpi-row { display:flex; gap:1rem; flex-wrap:wrap; }
.kpi { background:#111d30; border:1px solid #1e3a5f; border-radius:10px; padding:.9rem 1.2rem; flex:1; min-width:130px; transition: border-color .2s, box-shadow .2s; }
.kpi:hover { border-color:#40c4ff; box-shadow: 0 0 12px rgba(64,196,255,0.15); }
.kpi .label { font-size:.72rem; color:#7a9cc8; text-transform:uppercase; letter-spacing:.08em; }
.kpi .value { font-size:1.35rem; font-weight:700; margin-top:.2rem; }
.green { color:#00e676; } .red { color:#ff1744; } .blue { color:#40c4ff; } .gold { color:#ffd740; }

.section-title { font-size:1.25rem; font-weight:700; color:#40c4ff; border-left:4px solid #40c4ff; padding-left:.7rem; margin:1.5rem 0 .8rem; }

.chip-row { display:flex; flex-wrap:wrap; gap:.4rem; margin-top:.4rem; }
.chip { background:#112240; border:1px solid #1e3a6e; border-radius:20px; padding:.2rem .75rem; font-size:.78rem; cursor:pointer; color:#90caf9; transition: all .15s; }
.chip:hover { background:#1e3a6e; color:#fff; border-color:#40c4ff; }

.news-item { border-bottom:1px solid #1a2c45; padding:.7rem 0; font-size:.82rem; color:#b0c4de; }
.news-item strong { color:#e0e6f0; }

.user-badge {
  display:inline-flex; align-items:center; gap:.5rem;
  background:#0d1526; border:1px solid #1a2d4a; border-radius:8px;
  padding:.4rem .9rem; font-size:.82rem; color:#7a9cc8;
}
.user-badge strong { color:#00d4ff; }

/* Glossary */
.glossary-term {
  background:#0d1829; border:1px solid #1e3a5f; border-radius:8px;
  padding:.7rem 1rem; margin-bottom:.5rem;
}
.glossary-term .term-name { font-size:.9rem; font-weight:700; color:#40c4ff; margin-bottom:.2rem; }
.glossary-term .term-def { font-size:.82rem; color:#b0c4de; line-height:1.5; }

/* Signal box */
.signal-box {
  text-align:center; padding:1.5rem;
  border-radius:16px; margin-top:1rem;
  position:relative; overflow:hidden;
}
.signal-reason { font-size:.85rem; color:#90caf9; margin-top:.5rem; font-style:italic; }

/* News bullet legend */
.legend-row { display:flex; gap:1.5rem; flex-wrap:wrap; margin-bottom:.8rem; }
.legend-item { display:flex; align-items:center; gap:.4rem; font-size:.78rem; color:#7a9cc8; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# AUTH GATE
# ──────────────────────────────────────────────
init_db()
user = auth_ui()

if user is None:
    st.stop()

# ── LOGGED IN HEADER ──────────────────────────
col_brand, col_user = st.columns([5, 1])
with col_brand:
    st.markdown("# 📈 Stock Market Prediction")
with col_user:
    st.markdown(f"""
    <div class="user-badge">
      👤 <strong>{user['name'].split()[0]}</strong>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Logout", key="top_logout"):
        logout()

# ──────────────────────────────────────────────
# TICKER TAPE
# ──────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_tape_prices():
    tickers = ["NVDA", "AAPL", "GOOGL", "TSLA", "MSFT", "BTC-USD", "AMZN", "META"]
    items = []
    data = yf.download(tickers, period="2d", progress=False, auto_adjust=True)
    closes = data['Close']
    for t in tickers:
        try:
            prev, last = float(closes[t].iloc[-2]), float(closes[t].iloc[-1])
            pct = (last - prev) / prev * 100
            cls = "up" if pct > 0 else "down"
            arrow = "▲" if pct > 0 else "▼"
            items.append(f'<span class="ticker-item {cls}">{t}: ${last:,.2f} {arrow} {pct:+.2f}%</span>')
        except:
            pass
    return "".join(items)

tape_html = get_tape_prices()
st.markdown(f'<div class="ticker-wrap"><div class="ticker-move">{tape_html}</div></div>', unsafe_allow_html=True)

# ──────────────────────────────────────────────
# TOP NAVIGATION TABS
# ──────────────────────────────────────────────
nav_tab1, nav_tab2, nav_tab3, nav_tab4, nav_tab5, nav_tab6 = st.tabs([
    "📈 Dashboard", "📊 Financials", "📉 Technical", "🌐 Sectors", "📰 News", "📚 Learn"
])

# ──────────────────────────────────────────────
# TICKER INPUT (in Dashboard tab)
# ──────────────────────────────────────────────
with nav_tab1:
    col_inp, col_sug = st.columns([3, 2])
    with col_inp:
        default_ticker = st.query_params.get("ticker", "GOOGL")
        user_input = st.text_input("🔍 Enter Ticker Symbol", value=default_ticker,
                                   placeholder="e.g. AAPL, TSLA, RELIANCE.NS",
                                   key="main_ticker_input").upper().strip()
    with col_sug:
        st.markdown("**Trending Picks:**")
        # Each chip uses JS to fill the ticker input and re-run
        chip_html = ""
        for k, v in list(TRENDING.items())[:8]:
            chip_html += f'<span class="chip" onclick="(function(){{var el=window.parent.document.querySelector(\'[data-testid=stTextInput] input\');if(el){{el.value=\'{k}\';el.dispatchEvent(new Event(\'input\',{{bubbles:true}}));el.dispatchEvent(new KeyboardEvent(\'keydown\',{{key:\'Enter\',bubbles:true}}));}}}})();">{k} — {v}</span>'
        st.markdown(f'<div class="chip-row">{chip_html}</div>', unsafe_allow_html=True)
        #st.caption("💡 Tip: Click any chip to instantly load that stock")

    if not user_input:
        st.warning("Please enter a ticker symbol.")
        st.stop()

    # ──────────────────────────────────────────────
    # FETCH DATA
    # ──────────────────────────────────────────────
    @st.cache_data(ttl=600)
    def load_stock_data(ticker):
        df = yf.download(ticker, start='2010-01-01', progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df

    @st.cache_data(ttl=600)
    def load_info(ticker):
        try:
            return yf.Ticker(ticker).info
        except:
            return {}

    with st.spinner(f"Fetching data for {user_input}…"):
        df   = load_stock_data(user_input)
        info = load_info(user_input)

    if df.empty:
        st.error(f"No data found for '{user_input}'. Check the ticker symbol.")
        st.stop()

    # ──────────────────────────────────────────────
    # SECTION 1: COMPANY OVERVIEW
    # ──────────────────────────────────────────────
    st.markdown('<div class="section-title">🏢 Company Overview</div>', unsafe_allow_html=True)

    name       = info.get('longName', user_input)
    sector     = info.get('sector', 'N/A')
    industry   = info.get('industry', 'N/A')
    market_cap = info.get('marketCap') or 0
    pe_ratio   = info.get('trailingPE')
    eps        = info.get('trailingEps')
    week52_hi  = info.get('fiftyTwoWeekHigh')
    week52_lo  = info.get('fiftyTwoWeekLow')
    div_yield  = info.get('dividendYield')
    beta       = info.get('beta')
    volume     = info.get('volume')
    country    = info.get('country', 'N/A')
    description= info.get('longBusinessSummary', '')

    def fmt_cap(v):
        if v >= 1e12: return f"${v/1e12:.2f}T"
        if v >= 1e9:  return f"${v/1e9:.2f}B"
        if v >= 1e6:  return f"${v/1e6:.2f}M"
        return f"${v:,.0f}"

    current_price = float(df['Close'].iloc[-1])
    prev_price    = float(df['Close'].iloc[-2])
    daily_chg     = current_price - prev_price
    daily_pct     = daily_chg / prev_price * 100
    price_cls     = "green" if daily_chg >= 0 else "red"

    st.markdown(f"### {name} &nbsp;&nbsp; <span style='color:#7a9cc8;font-size:.9rem'>{sector} · {country}</span>", unsafe_allow_html=True)
    if description:
        with st.expander("About the company"):
            st.write(description[:600] + "…")

    def safe_fmt(val, prefix="$", suffix="", decimals=2):
        try:
            if val is None or (isinstance(val, float) and np.isnan(val)):
                return "N/A"
            return f"{prefix}{val:,.{decimals}f}{suffix}"
        except:
            return "N/A"

    kpis = [
        ("Current Price",  f"${current_price:,.2f}", price_cls),
        ("Daily Change",   f"{daily_chg:+.2f} ({daily_pct:+.2f}%)", price_cls),
        ("Market Cap",     fmt_cap(market_cap) if market_cap else "N/A", "blue"),
        ("P/E Ratio",      safe_fmt(pe_ratio, prefix=""), "gold"),
        ("EPS",            safe_fmt(eps), "gold"),
        ("52W High",       safe_fmt(week52_hi), "green"),
        ("52W Low",        safe_fmt(week52_lo), "red"),
        ("Dividend Yield", f"{div_yield*100:.2f}%" if div_yield and not np.isnan(div_yield) else "N/A", "gold"),
        ("Beta",           safe_fmt(beta, prefix=""), "neu"),
        ("Volume",         f"{volume:,}" if volume else "N/A", "blue"),
    ]
    kpi_html = '<div class="kpi-row">' + "".join(
        f'<div class="kpi"><div class="label">{l}</div><div class="value {c}">{v}</div></div>'
        for l, v, c in kpis
    ) + '</div>'
    st.markdown(kpi_html, unsafe_allow_html=True)

    # ──────────────────────────────────────────────
    # SECTION 6: LSTM PREDICTION
    # ──────────────────────────────────────────────
    st.markdown('<div class="section-title">🔮 Price Prediction (LSTM Model)</div>', unsafe_allow_html=True)

    try:
        model = load_model('keras_model.keras')
    except:
        st.warning("⚠️ Model file 'keras_model.keras' not found. Run LSTM.py first to train the model.")
        st.stop()

    data_close  = df.filter(['Close'])
    dataset     = data_close.values
    train_len   = int(np.ceil(len(dataset) * .8))
    scaler      = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(dataset)
    test_data   = scaled_data[train_len - 60:, :]
    x_test, y_test = [], dataset[train_len:, :]
    for i in range(60, len(test_data)):
        x_test.append(test_data[i-60:i, 0])
    x_test      = np.reshape(np.array(x_test), (len(x_test), 60, 1))
    predictions = scaler.inverse_transform(model.predict(x_test, verbose=0))

    fig_pred, ax_pred = plt.subplots(figsize=(14, 5), facecolor='#090e1a')
    ax_pred.set_facecolor('#0d1829')
    ax_pred.spines[:].set_color('#1e2d50')
    ax_pred.tick_params(colors='#5a7fa8')
    test_idx = df.index[train_len:]
    ax_pred.plot(test_idx, y_test, color='#40c4ff', lw=1.5, label='Actual Price')
    ax_pred.plot(test_idx, predictions, color='#ff9100', lw=1.5, ls='--', label='Model Prediction')
    ax_pred.fill_between(test_idx, y_test.flatten(), predictions.flatten(), alpha=0.08, color='#ffd740')
    ax_pred.legend(fontsize=9, facecolor='#0d1829', edgecolor='#1e2d50', labelcolor='#b0c4de')
    ax_pred.set_title("LSTM Model — Actual vs Predicted Price", color='#e0e6f0', fontsize=11)
    st.pyplot(fig_pred)
    plt.close(fig_pred)

    last_60        = data_close.values[-60:]
    last_60_scaled = scaler.transform(last_60)
    X_input        = np.reshape(np.array([last_60_scaled]), (1, 60, 1))
    pred_price     = float(scaler.inverse_transform(model.predict(X_input, verbose=0))[0][0])

    # ── NEWS SENTIMENT (needed for signal) ────────────────────────────────────
    @st.cache_data(ttl=600)
    def get_news_sentiment(ticker):
        try:
            url = (f"https://newsapi.org/v2/everything?q={ticker}+stock&language=en"
                   f"&sortBy=relevancy&pageSize=15&apiKey={NEWS_API_KEY}")
            resp = requests.get(url, timeout=10).json()
            articles = resp.get('articles', [])
            sentiments, news_list = [], []
            for art in articles:
                title = art.get('title', '')
                url_art = art.get('url', '')
                if not title or not title.isascii(): continue
                pol = TextBlob(title).sentiment.polarity
                sentiments.append(pol)
                news_list.append({
                    'title': title[:120],
                    'source': art.get('source', {}).get('name', ''),
                    'polarity': pol,
                    'published': art.get('publishedAt', '')[:10],
                    'url': url_art,
                })
                if len(news_list) >= 8: break
            return news_list, float(np.mean(sentiments)) if sentiments else 0.0
        except:
            return [], 0.0

    news_list, score = get_news_sentiment(user_input)
    final_adjusted = pred_price * (1 + (score * 0.015))
    delta_val      = final_adjusted - current_price
    delta_pct      = delta_val / current_price * 100

    # ──────────────────────────────────────────────
    # SECTION 7: VERDICT
    # ──────────────────────────────────────────────
    st.markdown('<div class="section-title">🎯 Trade Signal & Verdict</div>', unsafe_allow_html=True)

    signal    = "BUY 🟢"  if delta_pct > 1.5  else "SELL 🔴" if delta_pct < -1.5 else "HOLD ⚪"
    sig_color = "#00e676" if "BUY" in signal else "#ff1744" if "SELL" in signal else "#ffd740"
    mape      = float(np.mean(np.abs((y_test - predictions) / y_test)) * 100)

    # Signal reasons
    if "BUY" in signal:
        signal_reason = f"The model predicts the price will rise ~{delta_pct:.1f}% from current levels. News sentiment is {'positive 📰' if score > 0.05 else 'neutral'}. Consider buying in small portions and monitoring closely."
    elif "SELL" in signal:
        signal_reason = f"The model predicts the price will fall ~{abs(delta_pct):.1f}% from current levels. News sentiment is {'negative 📰' if score < -0.05 else 'neutral'}. Review your holdings and consider whether to exit or reduce position."
    else:
        signal_reason = f"The model predicts minimal price movement ({delta_pct:+.1f}%). Neither a clear opportunity nor a clear risk. Best to wait for a stronger signal before acting."

    v1, v2, v3, v4, v5 = st.columns(5)
    v1.metric("Current Price",        f"${current_price:,.2f}")
    v2.metric("Model Forecast",       f"${pred_price:,.2f}")
    v3.metric("Sentiment Adj. Price", f"${final_adjusted:,.2f}", delta=f"{delta_val:+.2f}")
    v4.metric("Model Accuracy",       f"{100-mape:.1f}%")
    v5.metric("News Sentiment",       f"{score*100:+.1f}%")

    st.markdown(f"""
    <div class="signal-box" style="background:#0d1829;border:2px solid {sig_color};">
      <div style="font-size:2.5rem;font-weight:800;color:{sig_color}">{signal}</div>
      <div style="color:#7a9cc8;font-size:.9rem;margin-top:.3rem">
        Expected move: <strong style="color:{sig_color}">{delta_pct:+.2f}%</strong> &nbsp;·&nbsp;
        LSTM + Sentiment Analysis
      </div>
      <div class="signal-reason">{signal_reason}</div>
    </div>
    <div style="background:rgba(255,193,7,0.07);border:1px solid rgba(255,193,7,0.2);border-radius:10px;
         padding:.7rem 1rem;margin-top:.8rem;font-size:.78rem;color:#7a9cc8;">
      ⚠️ <strong style="color:#ffd740">Disclaimer:</strong> This signal is generated by a mathematical model and does not constitute financial advice. 
      Always do your own research before investing. Past patterns do not guarantee future results.
    </div>
    """, unsafe_allow_html=True)

    # ──────────────────────────────────────────────
    # SECTION 8: RISK & VOLATILITY
    # ──────────────────────────────────────────────
    st.markdown('<div class="section-title">⚡ Volatility & Risk Metrics</div>', unsafe_allow_html=True)

    returns  = df['Close'].pct_change().dropna()
    ann_vol  = returns.std() * np.sqrt(252) * 100
    ann_ret  = returns.mean() * 252 * 100
    sharpe   = (ann_ret - 4.5) / (returns.std() * np.sqrt(252) * 100) if returns.std() > 0 else 0
    max_dd   = ((df['Close'] / df['Close'].cummax()) - 1).min() * 100

    rk1, rk2, rk3, rk4 = st.columns(4)
    rk1.metric("Annual Volatility",     f"{ann_vol:.1f}%")
    rk2.metric("Expected Annual Return",f"{ann_ret:.1f}%")
    rk3.metric("Sharpe Ratio (est.)",   f"{sharpe:.2f}")
    rk4.metric("Max Drawdown",          f"{float(max_dd):.1f}%")

    fig_risk, (ax_r1, ax_r2) = plt.subplots(1, 2, figsize=(14, 4), facecolor='#090e1a')
    for ax in [ax_r1, ax_r2]:
        ax.set_facecolor('#0d1829')
        ax.spines[:].set_color('#1e2d50')
        ax.tick_params(colors='#5a7fa8', labelsize=8)

    ax_r1.hist(returns * 100, bins=80, color='#40c4ff', alpha=0.7, edgecolor='none')
    ax_r1.axvline(0, color='#ff9100', lw=1.2, ls='--')
    ax_r1.set_title("Daily Returns Distribution", color='#e0e6f0', fontsize=10)
    ax_r1.set_xlabel("Return %", color='#5a7fa8', fontsize=8)

    rolling_vol = returns.rolling(30).std() * np.sqrt(252) * 100
    ax_r2.plot(rolling_vol.index, rolling_vol, color='#ff9100', lw=1)
    ax_r2.fill_between(rolling_vol.index, rolling_vol, alpha=0.15, color='#ff9100')
    ax_r2.set_title("30-Day Rolling Volatility", color='#e0e6f0', fontsize=10)
    ax_r2.set_ylabel("Volatility %", color='#5a7fa8', fontsize=8)
    st.pyplot(fig_risk)
    plt.close(fig_risk)

# ──────────────────────────────────────────────
# TAB 2: FINANCIALS
# ──────────────────────────────────────────────
with nav_tab2:
    st.markdown('<div class="section-title">📊 Financials — Balance Sheet & P&L</div>', unsafe_allow_html=True)

    ticker_fin = st.text_input("🔍 Ticker for Financials", value=st.session_state.get("main_ticker_input", "GOOGL"),
                                placeholder="e.g. AAPL").upper().strip()

    @st.cache_data(ttl=3600)
    def load_financials(ticker):
        t = yf.Ticker(ticker)
        return t.income_stmt, t.balance_sheet, t.cashflow

    if ticker_fin:
        inc, bal, cf = load_financials(ticker_fin)

        tab1, tab2, tab3 = st.tabs(["📈 Income Statement", "🏦 Balance Sheet", "💵 Cash Flow"])

        def show_fin_table(df_fin, label):
            if df_fin is None or df_fin.empty:
                st.info(f"No {label} data available.")
                return
            def fmt(x):
                try:
                    x = float(x)
                    if np.isnan(x): return "—"
                    if abs(x) >= 1e9: return f"${x/1e9:.2f}B"
                    if abs(x) >= 1e6: return f"${x/1e6:.2f}M"
                    return f"${x:,.0f}"
                except: return str(x)
            df_show = df_fin.map(fmt)
            df_show.columns = [str(c)[:10] for c in df_show.columns]
            st.dataframe(df_show, use_container_width=True)

        with tab1: show_fin_table(inc, "Income Statement")
        with tab2: show_fin_table(bal, "Balance Sheet")
        with tab3: show_fin_table(cf, "Cash Flow")

# ──────────────────────────────────────────────
# TAB 3: TECHNICAL ANALYSIS
# ──────────────────────────────────────────────
with nav_tab3:
    st.markdown('<div class="section-title">📉 Technical Analysis</div>', unsafe_allow_html=True)

    ticker_tech = st.text_input("🔍 Ticker for Technical Analysis",
                                 value=st.session_state.get("main_ticker_input", "GOOGL"),
                                 placeholder="e.g. TSLA").upper().strip()

    if ticker_tech:
        df_tech = load_stock_data(ticker_tech)
        if df_tech.empty:
            st.error("No data found.")
        else:
            period_opt = st.select_slider("Chart Period", ["1M","3M","6M","1Y","3Y","5Y","MAX"], value="1Y")
            period_map = {"1M":30,"3M":90,"6M":180,"1Y":365,"3Y":1095,"5Y":1825,"MAX":9999}
            df_chart = df_tech.tail(period_map[period_opt]).copy()

            # Only MA100 and MA200 (removed MA20 and MA50)
            df_chart['MA100'] = df_chart['Close'].rolling(100).mean()
            df_chart['MA200'] = df_chart['Close'].rolling(200).mean()

            def compute_rsi(series, period=14):
                delta = series.diff()
                gain  = delta.clip(lower=0).rolling(period).mean()
                loss  = (-delta.clip(upper=0)).rolling(period).mean()
                rs    = gain / loss
                return 100 - (100 / (1 + rs))

            df_chart['RSI']    = compute_rsi(df_chart['Close'])
            df_chart['EMA12']  = df_chart['Close'].ewm(span=12).mean()
            df_chart['EMA26']  = df_chart['Close'].ewm(span=26).mean()
            df_chart['MACD']   = df_chart['EMA12'] - df_chart['EMA26']
            df_chart['Signal'] = df_chart['MACD'].ewm(span=9).mean()
            df_chart['Hist']   = df_chart['MACD'] - df_chart['Signal']
            df_chart['BB_mid'] = df_chart['Close'].rolling(20).mean()
            df_chart['BB_std'] = df_chart['Close'].rolling(20).std()
            df_chart['BB_up']  = df_chart['BB_mid'] + 2 * df_chart['BB_std']
            df_chart['BB_dn']  = df_chart['BB_mid'] - 2 * df_chart['BB_std']

            fig, axes = plt.subplots(3, 1, figsize=(14, 10),
                                      gridspec_kw={'height_ratios': [3, 1, 1]}, facecolor='#090e1a')
            plt.subplots_adjust(hspace=0.1)
            ax1, ax2, ax3 = axes
            for ax in axes:
                ax.set_facecolor('#0d1829')
                ax.tick_params(colors='#5a7fa8', labelsize=8)
                ax.spines[:].set_color('#1e2d50')

            idx = df_chart.index
            ax1.plot(idx, df_chart['Close'], color='#40c4ff', lw=1.5, label='Price', zorder=3)
            ax1.fill_between(idx, df_chart['BB_up'], df_chart['BB_dn'], alpha=0.08, color='#40c4ff')
            ax1.plot(idx, df_chart['BB_up'],  '#e0e6f0', lw=0.6, ls='--', alpha=0.4, label='BB Upper')
            ax1.plot(idx, df_chart['BB_dn'],  '#e0e6f0', lw=0.6, ls='--', alpha=0.4, label='BB Lower')
            ax1.plot(idx, df_chart['MA100'], '#69f0ae', lw=0.9, alpha=0.7, label='MA100')
            ax1.plot(idx, df_chart['MA200'], '#ea80fc', lw=0.9, alpha=0.7, label='MA200')
            ax1.legend(fontsize=7, facecolor='#0d1829', edgecolor='#1e2d50', labelcolor='#b0c4de', ncol=4)
            ax1.set_title(f"{ticker_tech} — Price & Technical Indicators", color='#e0e6f0', fontsize=11)

            ax2.plot(idx, df_chart['RSI'], '#ff9100', lw=1.2)
            ax2.axhline(70, color='#ff1744', lw=0.7, ls='--', alpha=0.7)
            ax2.axhline(30, color='#00e676', lw=0.7, ls='--', alpha=0.7)
            ax2.fill_between(idx, 70, df_chart['RSI'].clip(upper=70), where=df_chart['RSI']>=70, alpha=0.15, color='#ff1744')
            ax2.fill_between(idx, df_chart['RSI'].clip(lower=30), 30, where=df_chart['RSI']<=30, alpha=0.15, color='#00e676')
            ax2.set_ylim(0, 100)
            ax2.set_ylabel('RSI', color='#5a7fa8', fontsize=8)

            bar_colors = ['#00e676' if v >= 0 else '#ff1744' for v in df_chart['Hist']]
            ax3.bar(idx, df_chart['Hist'], color=bar_colors, alpha=0.7, width=1)
            ax3.plot(idx, df_chart['MACD'],   '#40c4ff', lw=0.9, label='MACD')
            ax3.plot(idx, df_chart['Signal'], '#ffd740', lw=0.9, label='Signal')
            ax3.axhline(0, color='#5a7fa8', lw=0.5)
            ax3.legend(fontsize=7, facecolor='#0d1829', edgecolor='#1e2d50', labelcolor='#b0c4de')
            ax3.set_ylabel('MACD', color='#5a7fa8', fontsize=8)
            st.pyplot(fig)
            plt.close(fig)

# ──────────────────────────────────────────────
# TAB 4: SECTOR PERFORMANCE
# ──────────────────────────────────────────────
with nav_tab4:
    st.markdown('<div class="section-title">🌐 Sector-Wise Performance (YTD)</div>', unsafe_allow_html=True)

    @st.cache_data(ttl=1800)
    def get_sector_perf():
        results = {}
        for sector_name, tickers in SECTOR_TICKERS.items():
            perfs = []
            data = yf.download(tickers, period="ytd", progress=False, auto_adjust=True)['Close']
            for t in tickers:
                try:
                    col = data[t] if isinstance(data, pd.DataFrame) else data
                    first_valid = col.dropna().iloc[0]
                    last_valid  = col.dropna().iloc[-1]
                    perf = (last_valid - first_valid) / first_valid * 100
                    perfs.append((t, round(float(perf), 2)))
                except: pass
            results[sector_name] = perfs
        return results

    sector_data = get_sector_perf()
    cols = st.columns(min(len(sector_data), 3))
    for i, (sname, tperf) in enumerate(sector_data.items()):
        with cols[i % 3]:
            st.markdown(f"**{sname}**")
            if not tperf: continue
            fig_s, ax_s = plt.subplots(figsize=(4, 2.5), facecolor='#0d1829')
            ax_s.set_facecolor('#0d1829')
            names  = [x[0] for x in tperf]
            values = [x[1] for x in tperf]
            bar_colors = ['#00e676' if v >= 0 else '#ff1744' for v in values]
            bars = ax_s.barh(names, values, color=bar_colors, edgecolor='none', height=0.55)
            ax_s.axvline(0, color='#5a7fa8', lw=0.8)
            ax_s.tick_params(colors='#b0c4de', labelsize=7)
            ax_s.spines[:].set_color('#1e2d50')
            for bar, val in zip(bars, values):
                ax_s.text(val + (0.5 if val >= 0 else -0.5), bar.get_y() + bar.get_height()/2,
                          f"{val:+.1f}%", va='center', ha='left' if val >= 0 else 'right',
                          fontsize=6.5, color='#e0e6f0')
            ax_s.set_title(sname, color='#40c4ff', fontsize=9)
            st.pyplot(fig_s)
            plt.close(fig_s)

# ──────────────────────────────────────────────
# TAB 5: NEWS & SENTIMENT
# ──────────────────────────────────────────────
with nav_tab5:
    st.markdown('<div class="section-title">📰 Live News & Sentiment</div>', unsafe_allow_html=True)

    ticker_news = st.text_input("🔍 Ticker for News",
                                 value=st.session_state.get("main_ticker_input", "GOOGL"),
                                 placeholder="e.g. AAPL").upper().strip()

    if ticker_news:
        @st.cache_data(ttl=600)
        def get_news_sentiment_tab(ticker):
            try:
                url = (f"https://newsapi.org/v2/everything?q={ticker}+stock&language=en"
                       f"&sortBy=relevancy&pageSize=15&apiKey={NEWS_API_KEY}")
                resp = requests.get(url, timeout=10).json()
                articles = resp.get('articles', [])
                sentiments, news_list = [], []
                for art in articles:
                    title = art.get('title', '')
                    art_url = art.get('url', '')
                    if not title or not title.isascii(): continue
                    pol = TextBlob(title).sentiment.polarity
                    sentiments.append(pol)
                    news_list.append({
                        'title': title[:120],
                        'source': art.get('source', {}).get('name', ''),
                        'polarity': pol,
                        'published': art.get('publishedAt', '')[:10],
                        'url': art_url,
                    })
                    if len(news_list) >= 10: break
                return news_list, float(np.mean(sentiments)) if sentiments else 0.0
            except:
                return [], 0.0

        news_list_tab, score_tab = get_news_sentiment_tab(ticker_news)

        sent_col, news_col = st.columns([1, 3])
        with sent_col:
            sentiment_text = "Bullish 🚀" if score_tab > 0.05 else "Bearish 📉" if score_tab < -0.05 else "Neutral ⚖️"
            gauge_color    = "#00e676" if score_tab > 0.05 else "#ff1744" if score_tab < -0.05 else "#ffd740"
            st.markdown(f"""
            <div class="card" style="text-align:center;">
              <div style="font-size:2.5rem;">{sentiment_text.split()[-1]}</div>
              <div style="font-size:1.3rem;font-weight:700;color:{gauge_color}">{sentiment_text.split()[0]}</div>
              <div style="color:#7a9cc8;font-size:.85rem;margin-top:.3rem">Sentiment Score</div>
              <div style="font-size:1.8rem;font-weight:700;color:{gauge_color}">{score_tab:+.3f}</div>
            </div>
            """, unsafe_allow_html=True)

        with news_col:
            # Bullet legend
            st.markdown("""
            <div class="legend-row">
              <div class="legend-item">🟢 <span>Positive news — likely good for stock price</span></div>
              <div class="legend-item">🔴 <span>Negative news — may put downward pressure on price</span></div>
              <div class="legend-item">⚪ <span>Neutral news — no strong directional impact</span></div>
            </div>
            """, unsafe_allow_html=True)

            if news_list_tab:
                for art in news_list_tab:
                    pol_icon = "🟢" if art['polarity'] > 0.05 else "🔴" if art['polarity'] < -0.05 else "⚪"
                    url_html = f'<a href="{art["url"]}" target="_blank" style="color:#40c4ff;text-decoration:none;font-size:.75rem;">🔗 Read Full Article</a>' if art.get('url') else ''
                    st.markdown(f"""
                    <div class="news-item">
                      {pol_icon} <strong>{art['title']}</strong><br>
                      <span style="color:#5a7fa8;font-size:.75rem;">{art['source']} · {art['published']}</span>
                      &nbsp; {url_html}
                    </div>""", unsafe_allow_html=True)
            else:
                st.info("No news articles found. Try a different ticker or check your NewsAPI key.")

# ──────────────────────────────────────────────
# TAB 6: LEARN (GLOSSARY)
# ──────────────────────────────────────────────
with nav_tab6:
    st.markdown('<div class="section-title">📚 Stock Market — Beginner\'s Guide</div>', unsafe_allow_html=True)

    st.markdown("""
    <div style="background:rgba(64,196,255,0.07);border:1px solid rgba(64,196,255,0.2);
         border-radius:12px;padding:1rem 1.2rem;margin-bottom:1.5rem;font-size:.88rem;color:#90caf9;">
      🎓 New to stock markets? This section explains every term and chart used in this app in plain, simple language.
      No finance degree required!
    </div>
    """, unsafe_allow_html=True)

    search_term = st.text_input("🔍 Search a term", placeholder="e.g. P/E Ratio, RSI, Bullish…")

    # Category groupings
    categories = {
        "📋 Basic Stock Terms": ["Ticker Symbol", "Current Price", "Daily Change", "Market Cap",
                                   "P/E Ratio (Price-to-Earnings)", "EPS (Earnings Per Share)",
                                   "52-Week High / Low", "Dividend Yield", "Beta", "Volume", "YTD Performance"],
        "📉 Technical Indicators": ["RSI (Relative Strength Index)", "MACD (Moving Average Convergence Divergence)",
                                     "Bollinger Bands", "MA100 / MA200 (Moving Average)"],
        "🔮 Predictions & Signals": ["LSTM Prediction", "Sentiment Score", "Bullish", "Bearish",
                                      "BUY Signal", "SELL Signal", "HOLD Signal"],
        "📊 Financial Statements": ["Income Statement", "Balance Sheet", "Cash Flow"],
        "⚡ Risk Metrics": ["Annual Volatility", "Sharpe Ratio", "Max Drawdown"],
    }

    for cat_name, terms in categories.items():
        # Filter based on search
        filtered = [t for t in terms if not search_term or search_term.lower() in t.lower() or
                    (t in GLOSSARY and search_term.lower() in GLOSSARY[t].lower())]
        if not filtered:
            continue

        with st.expander(cat_name, expanded=bool(search_term)):
            for term in filtered:
                definition = GLOSSARY.get(term, "Definition coming soon.")
                st.markdown(f"""
                <div class="glossary-term">
                  <div class="term-name">📌 {term}</div>
                  <div class="term-def">{definition}</div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("""
    <div style="background:#0d1829;border:1px solid #1e3a5f;border-radius:10px;
         padding:1rem 1.2rem;margin-top:1rem;font-size:.85rem;color:#7a9cc8;">
      💡 <strong style="color:#40c4ff">Pro Tip:</strong> Don't rely on any single indicator. 
      Combine price prediction with technical analysis and news sentiment for a more complete picture. 
      Always invest only what you can afford to lose.
    </div>
    """, unsafe_allow_html=True)

# ──────────────────────────────────────────────
# FOOTER
# ──────────────────────────────────────────────
st.divider()
st.markdown(f"""
<div style="text-align:center;color:#3a5a80;font-size:.78rem;padding:.5rem">
  Stock Market Prediction · Logged in as <strong style="color:#40c4ff">{user['name']}</strong>
  &nbsp;·&nbsp; Data via Yahoo Finance & NewsAPI &nbsp;·&nbsp; Not financial advice
</div>
""", unsafe_allow_html=True)