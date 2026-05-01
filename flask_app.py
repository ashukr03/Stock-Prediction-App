"""
flask_app.py — Main Flask application for Stock Market Prediction
Run with: python flask_app.py
"""
import numpy as np, pandas as pd, yfinance as yf, requests as req, json, warnings, os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()
from keras.models import load_model
from sklearn.preprocessing import MinMaxScaler
from textblob import TextBlob
from functools import wraps
import google.generativeai as genai
from auth import (init_db, hash_password, check_password, generate_otp, store_otp,
    verify_otp, clear_otp, send_email, otp_email_html, user_exists, register_user,
    get_user, update_last_login, update_password, get_all_users, get_verified_emails,
    log_notification, get_notifications, SMTP_SENDER, APP_NAME, _welcome_email_html)

warnings.filterwarnings('ignore')
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'ai-stock-pro-flask-secret-key-2024')
# ── CONFIG ──
NEWS_API_KEY = os.getenv("NEWS_API_KEY")  
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

TRENDING = {"NVDA":"NVIDIA","AAPL":"Apple","GOOGL":"Alphabet","TSLA":"Tesla",
    "MSFT":"Microsoft","AMZN":"Amazon","META":"Meta","NFLX":"Netflix",
    "RELIANCE.NS":"Reliance","TCS.NS":"TCS","INFY.NS":"Infosys","HDFCBANK.NS":"HDFC Bank"}

SECTOR_TICKERS = {
    "Technology":["AAPL","MSFT","NVDA","AMD","INTC"],
    "EV & Auto":["TSLA","GM","F","RIVN","NIO"],
    "Finance":["JPM","GS","BAC","WFC","C"],
    "Healthcare":["JNJ","PFE","MRNA","UNH","ABBV"],
    "Energy":["XOM","CVX","BP","COP","SLB"],
    "Indian Stocks":["RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS","WIPRO.NS"],
}

GLOSSARY = {
    "Ticker Symbol": {
        "desc": "A short code (like AAPL for Apple) used to identify a company on the stock exchange.",
        "example": "If you want to buy Tesla stock, you don't search for 'Tesla Motors Inc.', you simply search for the ticker 'TSLA'.",
        "type": "html",
        "visual": "<div style='font-family:var(--font-mono);font-size:2rem;color:var(--accent);text-align:center;padding:1rem;background:var(--bg);border-radius:8px;border:1px dashed var(--border)'>$TSLA</div>"
    },
    "Market Cap": {
        "desc": "Total value of a company's shares. Calculated as: Share Price × Total Shares Outstanding.",
        "example": "If a company has 1 million shares and each share costs $50, the Market Cap is $50,000,000.",
        "type": "html",
        "visual": "<div style='text-align:center;font-family:var(--font-mono);background:var(--bg);padding:1rem;border-radius:8px;border:1px dashed var(--border);color:var(--text)'><span style='color:var(--accent)'>Price</span> × <span style='color:var(--purple)'>Shares</span> = <span style='color:var(--green);font-weight:bold'>Market Cap</span></div>"
    },
    "P/E Ratio (Price-to-Earnings)": {
        "desc": "How much investors are willing to pay per dollar of company profit. A high P/E ratio could mean a stock is overvalued, or that investors expect high future growth.",
        "example": "A stock trading at $100 with $5 in earnings per share has a P/E ratio of 20 (100 / 5).",
        "type": "html",
        "visual": "<div style='text-align:center;font-size:1.5rem;font-family:var(--font-mono);background:var(--bg);padding:1rem;border-radius:8px;border:1px dashed var(--border)'><div style='border-bottom:2px solid var(--text);display:inline-block;padding-bottom:.2rem;margin-bottom:.2rem;color:var(--accent)'>$100 (Price)</div><br><div style='color:var(--green)'>$5 (Earnings)</div><div style='margin-top:.5rem;font-weight:bold;color:var(--gold)'>P/E = 20x</div></div>"
    },
    "RSI (Relative Strength Index)": {
        "desc": "A momentum indicator that measures the speed and change of price movements on a scale of 0 to 100. It helps identify overbought or oversold conditions.",
        "example": "If the RSI is above 70, the stock might be 'overbought' (due for a pullback). If it's below 30, it might be 'oversold' (due for a bounce).",
        "type": "chart",
        "visual": "rsi"
    },
    "MACD (Moving Average Convergence Divergence)": {
        "desc": "A trend-following momentum indicator that shows the relationship between two moving averages of a stock's price.",
        "example": "When the MACD line crosses ABOVE the signal line, it generates a bullish signal. When it crosses BELOW, it's a bearish signal.",
        "type": "chart",
        "visual": "macd"
    },
    "Bollinger Bands": {
        "desc": "A technical tool featuring a middle simple moving average (SMA) with an upper and lower band based on standard deviations. It measures volatility.",
        "example": "If a stock price touches the upper band, it might be overextended. If the bands 'squeeze' together, expect a major breakout soon.",
        "type": "chart",
        "visual": "bollinger"
    },
    "Max Drawdown": {
        "desc": "The maximum observed loss from a peak to a trough of a portfolio, before a new peak is attained. It measures downside risk.",
        "example": "If your portfolio goes from $10,000 down to $5,000 before recovering, your Max Drawdown is 50%.",
        "type": "chart",
        "visual": "drawdown"
    },
    "Bullish vs Bearish": {
        "desc": "Market terminology used to describe investor sentiment. Bullish means expecting prices to rise; Bearish means expecting prices to fall.",
        "example": "If you buy a Call option or buy shares, you are Bullish. If you short sell a stock, you are Bearish.",
        "type": "html",
        "visual": "<div style='display:flex;justify-content:center;gap:2rem;background:var(--bg);padding:1rem;border-radius:8px;border:1px dashed var(--border)'><div style='text-align:center'><div style='font-size:2rem'>🐂</div><div style='color:var(--green);font-weight:bold;margin-top:.5rem'>Bullish (UP)</div></div><div style='text-align:center'><div style='font-size:2rem'>🐻</div><div style='color:var(--red);font-weight:bold;margin-top:.5rem'>Bearish (DOWN)</div></div></div>"
    },
    "Dividend Yield": {
        "desc": "A financial ratio that shows how much a company pays out in dividends each year relative to its stock price.",
        "example": "If a stock is priced at $100 and pays an annual dividend of $4 per share, the dividend yield is 4%.",
        "type": "html",
        "visual": "<div style='text-align:center;font-size:2.5rem;font-weight:800;color:var(--green);background:var(--bg);padding:1rem;border-radius:8px;border:1px dashed var(--border)'>4.00%<div style='font-size:.8rem;color:var(--muted);font-weight:normal;margin-top:.5rem'>Annual Return on Price</div></div>"
    },
    "LSTM Prediction": {
        "desc": "Long Short-Term Memory. A type of artificial recurrent neural network (RNN) architecture used in deep learning, exceptionally good at predicting time-series data like stock prices.",
        "example": "Our AI model uses LSTM to analyze the past 15 years of stock price fluctuations, learning patterns to forecast tomorrow's price.",
        "type": "html",
        "visual": "<div style='text-align:center;background:var(--bg);padding:1rem;border-radius:8px;border:1px dashed var(--border)'><div style='font-size:2rem'>🧠 🤖 📈</div><div style='font-size:.85rem;color:var(--accent);margin-top:.5rem'>Deep Learning Architecture</div></div>"
    }
}

CATEGORIES = {
    "📋 Basic Stock Terms":["Ticker Symbol","Current Price","Daily Change","Market Cap",
        "P/E Ratio (Price-to-Earnings)","EPS (Earnings Per Share)","52-Week High / Low",
        "Dividend Yield","Beta","Volume"],
    "📉 Technical Indicators":["RSI (Relative Strength Index)",
        "MACD (Moving Average Convergence Divergence)","Bollinger Bands","MA100 / MA200 (Moving Average)"],
    "🔮 Predictions & Signals":["LSTM Prediction","Sentiment Score","Bullish","Bearish",
        "BUY Signal","SELL Signal","HOLD Signal"],
    "📊 Financial Statements":["Income Statement","Balance Sheet","Cash Flow"],
    "⚡ Risk Metrics":["Annual Volatility","Sharpe Ratio","Max Drawdown"],
}

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def safe_fmt(val, prefix="$", decimals=2):
    try:
        if val is None or (isinstance(val, float) and np.isnan(val)): return "N/A"
        return f"{prefix}{val:,.{decimals}f}"
    except: return "N/A"

# ── GLOBAL STATE & CACHE ──
# Load model once at startup to save time
try:
    GLOBAL_MODEL = load_model('keras_model.keras')
except:
    GLOBAL_MODEL = None

DATA_CACHE = {} # ticker: {timestamp, data}

def get_cached_data(key, ttl=300):
    import time
    if key in DATA_CACHE:
        entry = DATA_CACHE[key]
        if time.time() - entry['time'] < ttl:
            return entry['data']
    return None

def set_cached_data(key, data):
    import time
    DATA_CACHE[key] = {'time': time.time(), 'data': data}

def fmt_cap(v):
    if v is None: return "N/A"
    if v >= 1e12: return f"${v/1e12:.2f}T"
    if v >= 1e9: return f"${v/1e9:.2f}B"
    if v >= 1e6: return f"${v/1e6:.2f}M"
    return f"${v:,.0f}"

def fmt_fin(x):
    try:
        x = float(x)
        if np.isnan(x): return "—"
        if abs(x) >= 1e9: return f"${x/1e9:.2f}B"
        if abs(x) >= 1e6: return f"${x/1e6:.2f}M"
        return f"${x:,.0f}"
    except: return str(x)

# ── AUTH ROUTES ──
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email, pw = request.form.get('email',''), request.form.get('password','')
        if not email or '@' not in email:
            flash('Enter a valid email.', 'error')
        elif not pw:
            flash('Please enter your password.', 'error')
        elif not user_exists(email):
            flash('No account found. Please sign up first.', 'error')
        else:
            user = get_user(email)
            if not user.get('password_hash'):
                flash('Account needs password reset. Use Forgot Password.', 'error')
            elif not check_password(pw, user['password_hash']):
                flash('Incorrect password.', 'error')
            else:
                update_last_login(email)
                session['user'] = user
                flash(f"Welcome back, {user['name']}! 🎉", 'success')
                return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/signup', methods=['GET','POST'])
def signup():
    otp_sent = 'su_pending' in session
    if request.method == 'POST':
        step = request.form.get('step')
        if step == 'send_otp':
            name = request.form.get('name','').strip()
            email = request.form.get('email','')
            pw = request.form.get('password','')
            confirm = request.form.get('confirm','')
            if not name: flash('Please enter your name.', 'error')
            elif not email or '@' not in email: flash('Enter a valid email.', 'error')
            elif not pw or len(pw) < 6: flash('Password must be at least 6 characters.', 'error')
            elif pw != confirm: flash('Passwords do not match.', 'error')
            elif user_exists(email): flash('Account already exists. Please login.', 'error')
            else:
                otp = generate_otp()
                pw_hash = hash_password(pw)
                store_otp(email, otp, 'signup', name, pw_hash)
                ok = send_email(email, f"Welcome to {APP_NAME} — Verify Your Email",
                    otp_email_html(name, otp, 'signup'))
                if ok:
                    flash(f'OTP sent to {email} ✓', 'success')
                    session['su_pending'] = {'name': name, 'email': email}
                    otp_sent = True
                else:
                    flash('Could not send email. Check SMTP config.', 'error')
        elif step == 'verify_otp':
            pending = session.get('su_pending')
            if not pending:
                flash('Session expired. Please try again.', 'error')
                return redirect(url_for('signup'))
            otp_val = request.form.get('otp','')
            ok, name_val, pw_hash = verify_otp(pending['email'], otp_val, 'signup')
            if ok:
                register_user(pending['name'], pending['email'], pw_hash)
                clear_otp(pending['email'])
                user = get_user(pending['email'])
                update_last_login(user['email'])
                session.pop('su_pending', None)
                session['user'] = user
                send_email(user['email'], f"Welcome to {APP_NAME}!", _welcome_email_html(user['name']))
                flash(f"Account created! Welcome, {user['name']} 🚀", 'success')
                return redirect(url_for('dashboard'))
            else:
                flash(name_val, 'error')
                otp_sent = True
    pending_email = session.get('su_pending', {}).get('email', '')
    return render_template('signup.html', otp_sent=otp_sent, pending_email=pending_email)

@app.route('/forgot-password', methods=['GET','POST'])
def forgot_password():
    otp_sent = 'fp_pending' in session
    if request.method == 'POST':
        step = request.form.get('step')
        if step == 'send_otp':
            email = request.form.get('email','')
            if not email or '@' not in email: flash('Enter a valid email.', 'error')
            elif not user_exists(email): flash('No account found with this email.', 'error')
            else:
                user = get_user(email)
                otp = generate_otp()
                store_otp(email, otp, 'reset', user['name'])
                ok = send_email(email, f"{APP_NAME} — Password Reset OTP",
                    otp_email_html(user['name'], otp, 'reset'))
                if ok:
                    flash(f'Reset OTP sent to {email} ✓', 'success')
                    session['fp_pending'] = email
                    otp_sent = True
                else:
                    flash('Could not send email.', 'error')
        elif step == 'reset':
            fp_email = session.get('fp_pending')
            if not fp_email:
                flash('Session expired.', 'error')
                return redirect(url_for('forgot_password'))
            otp_val = request.form.get('otp','')
            pw = request.form.get('password','')
            confirm = request.form.get('confirm','')
            if not pw or len(pw) < 6: flash('Password must be at least 6 characters.', 'error'); otp_sent = True
            elif pw != confirm: flash('Passwords do not match.', 'error'); otp_sent = True
            else:
                ok, name_val, _ = verify_otp(fp_email, otp_val, 'reset')
                if ok:
                    update_password(fp_email, pw)
                    clear_otp(fp_email)
                    session.pop('fp_pending', None)
                    flash('Password reset successful! 🎉 Login with your new password.', 'success')
                    return redirect(url_for('login'))
                else:
                    flash(name_val, 'error'); otp_sent = True
    pending_email = session.get('fp_pending', '')
    return render_template('forgot_password.html', otp_sent=otp_sent, pending_email=pending_email)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ── LANDING ──
@app.route('/')
def index():
    return render_template('index.html')

# ── DASHBOARD ──
@app.route('/dashboard')
@login_required
def dashboard():
    default_ticker = session.get('last_ticker', 'NVDA')
    ticker = request.args.get('ticker', default_ticker).upper().strip()
    if ticker: session['last_ticker'] = ticker

    if not ticker:
        return render_template('dashboard.html', ticker='', trending=TRENDING, error='Please enter a ticker.')

    # Cache check
    cache_key = f"dash_{ticker}"
    cached = get_cached_data(cache_key, ttl=300) # 5 min cache
    if cached:
        return render_template('dashboard.html', **cached)
    try:
        df = yf.download(ticker, start='2010-01-01', progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if df.empty:
            return render_template('dashboard.html', ticker=ticker, trending=TRENDING,
                error=f"No data found for '{ticker}'.")
        info = {}
        try: info = yf.Ticker(ticker).info
        except: pass

        current_price = float(df['Close'].iloc[-1])
        prev_price = float(df['Close'].iloc[-2])
        daily_chg = current_price - prev_price
        daily_pct = daily_chg / prev_price * 100
        price_cls = 'green' if daily_chg >= 0 else 'red'
        mc = info.get('marketCap') or 0
        dy = info.get('dividendYield')

        kpis = [
            ("Current Price", f"${current_price:,.2f}", price_cls),
            ("Daily Change", f"{daily_chg:+.2f} ({daily_pct:+.2f}%)", price_cls),
            ("Market Cap", fmt_cap(mc), "blue"),
            ("P/E Ratio", safe_fmt(info.get('trailingPE'), ""), "gold"),
            ("EPS", safe_fmt(info.get('trailingEps')), "gold"),
            ("52W High", safe_fmt(info.get('fiftyTwoWeekHigh')), "green"),
            ("52W Low", safe_fmt(info.get('fiftyTwoWeekLow')), "red"),
            ("Div Yield", f"{dy*100:.2f}%" if dy and not np.isnan(dy) else "N/A", "gold"),
            ("Beta", safe_fmt(info.get('beta'), ""), "blue"),
            ("Volume", f"{info.get('volume',0):,}" if info.get('volume') else "N/A", "blue"),
        ]

        # LSTM prediction using global model
        if GLOBAL_MODEL is None:
            return render_template('dashboard.html', ticker=ticker, trending=TRENDING, error="Model not found.")
            
        model = GLOBAL_MODEL
        data_close = df.filter(['Close']).values
        train_len = int(np.ceil(len(data_close) * .8))
        scaler = MinMaxScaler(feature_range=(0, 1))
        scaled = scaler.fit_transform(data_close)
        test_data = scaled[train_len - 60:]
        x_test, y_test = [], data_close[train_len:]
        for i in range(60, len(test_data)):
            x_test.append(test_data[i-60:i, 0])
        x_test = np.reshape(np.array(x_test), (len(x_test), 60, 1))
        predictions = scaler.inverse_transform(model.predict(x_test, verbose=0))

        last_60 = scaler.transform(data_close[-60:])
        X_input = np.reshape(np.array([last_60]), (1, 60, 1))
        pred_price = float(scaler.inverse_transform(model.predict(X_input, verbose=0))[0][0])

        # News sentiment
        news_list, score = [], 0.0
        try:
            url = f"https://newsapi.org/v2/everything?q={ticker}+stock&language=en&sortBy=relevancy&pageSize=15&apiKey={NEWS_API_KEY}"
            resp = req.get(url, timeout=10).json()
            sents = []
            for art in resp.get('articles', []):
                t = art.get('title', '')
                if not t or not t.isascii(): continue
                pol = TextBlob(t).sentiment.polarity
                sents.append(pol)
                news_list.append({'title': t[:120], 'source': art.get('source',{}).get('name',''),
                    'polarity': pol, 'published': art.get('publishedAt','')[:10], 'url': art.get('url','')})
                if len(news_list) >= 8: break
            score = float(np.mean(sents)) if sents else 0.0
        except: pass

        final_adjusted = pred_price * (1 + score * 0.015)
        delta_val = final_adjusted - current_price
        delta_pct = delta_val / current_price * 100
        signal = "BUY 🟢" if delta_pct > 1.5 else "SELL 🔴" if delta_pct < -1.5 else "HOLD ⚪"
        sig_color = "#00e676" if "BUY" in signal else "#ff1744" if "SELL" in signal else "#ffd740"
        mape = float(np.mean(np.abs((y_test - predictions) / y_test)) * 100)
        accuracy = 100 - mape

        if "BUY" in signal:
            sig_reason = f"Model predicts ~{delta_pct:.1f}% rise. News sentiment is {'positive 📰' if score > 0.05 else 'neutral'}."
        elif "SELL" in signal:
            sig_reason = f"Model predicts ~{abs(delta_pct):.1f}% fall. News sentiment is {'negative 📰' if score < -0.05 else 'neutral'}."
        else:
            sig_reason = f"Minimal movement predicted ({delta_pct:+.1f}%). Wait for stronger signal."

        # Risk metrics
        returns = df['Close'].pct_change().dropna()
        ann_vol = float(returns.std() * np.sqrt(252) * 100)
        ann_ret = float(returns.mean() * 252 * 100)
        sharpe = (ann_ret - 4.5) / (returns.std() * np.sqrt(252) * 100) if returns.std() > 0 else 0
        max_dd = float(((df['Close'] / df['Close'].cummax()) - 1).min() * 100)

        # Chart data
        test_idx = df.index[train_len:].strftime('%Y-%m-%d').tolist()
        rolling_vol = returns.rolling(30).std() * np.sqrt(252) * 100
        chart_data = {
            'dates': test_idx,
            'actual': y_test.flatten().tolist(),
            'predicted': predictions.flatten().tolist(),
            'returns': (returns * 100).tolist(),
            'vol_dates': returns.index.strftime('%Y-%m-%d').tolist(),
            'rolling_vol': rolling_vol.fillna(0).tolist(),
        }

        output = {
            'ticker': ticker, 'trending': TRENDING, 'info': info, 'kpis': kpis,
            'current_price': current_price, 'pred_price': pred_price,
            'final_adjusted': final_adjusted, 'delta_val': delta_val,
            'delta_pct': delta_pct, 'sentiment': score, 'signal': signal,
            'sig_color': sig_color, 'signal_reason': sig_reason,
            'accuracy': accuracy, 'ann_vol': ann_vol, 'ann_ret': ann_ret,
            'sharpe': sharpe, 'max_dd': max_dd, 'chart_data': chart_data
        }
        set_cached_data(cache_key, output)
        return render_template('dashboard.html', **output)
    except Exception as e:
        # Ensure ticker is defined for the template
        t_err = ticker if 'ticker' in locals() else ''
        return render_template('dashboard.html', ticker=t_err, trending=TRENDING,
            error=f"Error loading data: {str(e)}")

# ── FINANCIALS ──
@app.route('/financials')
@login_required
def financials():
    default_ticker = session.get('last_ticker', '')
    ticker = request.args.get('ticker', default_ticker).upper().strip()
    if ticker: session['last_ticker'] = ticker
    if not ticker:
        return render_template('financials.html', ticker='')

    # Cache check
    cache_key = f"fin_{ticker}"
    cached = get_cached_data(cache_key, ttl=1800) # 30 min cache for financials
    if cached:
        return render_template('financials.html', **cached)

    try:
        t = yf.Ticker(ticker)
        inc = t.income_stmt
        bal = t.balance_sheet
        cf = t.cashflow
        def process(df_fin):
            if df_fin is None or df_fin.empty: return None
            df_show = df_fin.map(fmt_fin)
            df_show.columns = [str(c)[:10] for c in df_show.columns]
            return df_show
        output = {
            'ticker': ticker, 'income': process(inc),
            'balance': process(bal), 'cashflow': process(cf)
        }
        set_cached_data(cache_key, output)
        return render_template('financials.html', **output)
    except Exception as e:
        t_err = ticker if 'ticker' in locals() else ''
        return render_template('financials.html', ticker=t_err, error=str(e))

# ── TECHNICAL ──
@app.route('/technical')
@login_required
def technical():
    default_ticker = session.get('last_ticker', '')
    ticker = request.args.get('ticker', default_ticker).upper().strip()
    if ticker: session['last_ticker'] = ticker
    period = request.args.get('period', '1Y')
    if not ticker:
        return render_template('technical.html', ticker='', period=period)
    try:
        df = yf.download(ticker, start='2010-01-01', progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if df.empty:
            return render_template('technical.html', ticker=ticker, period=period, error='No data found.')
        period_map = {"1M":30,"3M":90,"6M":180,"1Y":365,"3Y":1095,"5Y":1825}
        df_chart = df.tail(period_map.get(period, 365)).copy()
        df_chart['MA100'] = df_chart['Close'].rolling(100).mean()
        df_chart['MA200'] = df_chart['Close'].rolling(200).mean()
        delta = df_chart['Close'].diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss
        df_chart['RSI'] = 100 - (100 / (1 + rs))
        df_chart['EMA12'] = df_chart['Close'].ewm(span=12).mean()
        df_chart['EMA26'] = df_chart['Close'].ewm(span=26).mean()
        df_chart['MACD'] = df_chart['EMA12'] - df_chart['EMA26']
        df_chart['Signal'] = df_chart['MACD'].ewm(span=9).mean()
        df_chart['Hist'] = df_chart['MACD'] - df_chart['Signal']
        bb_mid = df_chart['Close'].rolling(20).mean()
        bb_std = df_chart['Close'].rolling(20).std()
        df_chart['BB_up'] = bb_mid + 2 * bb_std
        df_chart['BB_dn'] = bb_mid - 2 * bb_std

        dates = df_chart.index.strftime('%Y-%m-%d').tolist()
        chart_data = {
            'dates': dates,
            'close': df_chart['Close'].tolist(),
            'ma100': df_chart['MA100'].fillna('null').tolist(),
            'ma200': df_chart['MA200'].fillna('null').tolist(),
            'rsi': df_chart['RSI'].fillna('null').tolist(),
            'macd': df_chart['MACD'].fillna(0).tolist(),
            'signal': df_chart['Signal'].fillna(0).tolist(),
            'hist': df_chart['Hist'].fillna(0).tolist(),
            'bb_up': df_chart['BB_up'].fillna('null').tolist(),
            'bb_dn': df_chart['BB_dn'].fillna('null').tolist(),
        }
        return render_template('technical.html', ticker=ticker, period=period, chart_data=chart_data)
    except Exception as e:
        return render_template('technical.html', ticker=ticker, period=period, error=str(e))

# ── SECTORS ──
@app.route('/sectors')
@login_required
def sectors():
    try:
        results = {}
        for sname, tickers in SECTOR_TICKERS.items():
            perfs = []
            data = yf.download(tickers, period="ytd", progress=False, auto_adjust=True)['Close']
            for t in tickers:
                try:
                    col = data[t] if isinstance(data, pd.DataFrame) else data
                    first = col.dropna().iloc[0]; last = col.dropna().iloc[-1]
                    perf = (last - first) / first * 100
                    perfs.append((t, round(float(perf), 2)))
                except: pass
            results[sname] = perfs
        return render_template('sectors.html', sector_data=results)
    except Exception as e:
        return render_template('sectors.html', error=str(e))

# ── NEWS ──
@app.route('/news')
@login_required
def news():
    default_ticker = session.get('last_ticker', '')
    ticker = request.args.get('ticker', default_ticker).upper().strip()
    if ticker: session['last_ticker'] = ticker
    if not ticker:
        return render_template('news.html', ticker='')
    cache_key = f"news_{ticker}"
    cached = get_cached_data(cache_key, ttl=600)
    if cached:
        return render_template('news.html', **cached)

    try:
        # Strip suffix like .NS or .BO for better search results
        clean_ticker = ticker.split('.')[0]
        search_query = f"{clean_ticker} stock"
        
        try:
            # Try to get company name for even better search results
            info = yf.Ticker(ticker).info
            name = info.get('longName') or info.get('shortName')
            if name:
                search_query = f"{name} stock OR {clean_ticker} stock"
        except:
            pass

        url = f"https://newsapi.org/v2/everything?q={req.utils.quote(search_query)}&language=en&sortBy=relevancy&pageSize=15&apiKey={NEWS_API_KEY}"
        resp = req.get(url, timeout=10).json()
        sents, news_list = [], []
        for art in resp.get('articles', []):
            t = art.get('title', '')
            if not t: continue
            pol = TextBlob(t).sentiment.polarity
            sents.append(pol)
            news_list.append({'title': t[:120], 'source': art.get('source',{}).get('name',''),
                'polarity': pol, 'published': art.get('publishedAt','')[:10], 'url': art.get('url','')})
            if len(news_list) >= 10: break
        score = float(np.mean(sents)) if sents else 0.0
        
        output = {'ticker': ticker, 'news_list': news_list, 'score': score}
        set_cached_data(cache_key, output)
        return render_template('news.html', **output)
    except Exception as e:
        return render_template('news.html', ticker=ticker, error=str(e))

# ── LEARN ──
@app.route('/learn')
@login_required
def learn():
    search = request.args.get('q', '')
    filtered_glossary = {}
    for term, data in GLOSSARY.items():
        if not search or search.lower() in term.lower() or search.lower() in data['desc'].lower():
            filtered_glossary[term] = data
            
    return render_template('learn.html', glossary=filtered_glossary, search=search)

@app.route('/api/ai_search')
@login_required
def api_ai_search():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'error': 'Empty query'}), 400
        
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""Explain "{query}" concisely for a beginner in 2-3 paragraphs.
        Include ONE real-world example.
        If helpful, include a Mermaid.js diagram. 
        CRITICAL: All node labels MUST be in double quotes. 
        Example: A["Buy Stock"] --> B["Price Goes Up"]
        Format in Markdown. Put Mermaid code inside ```mermaid blocks."""
        response = model.generate_content(prompt)
        
        if not response or not response.text:
            return jsonify({'error': 'AI returned an empty response. Check API key permissions.'}), 500
            
        return jsonify({'result': response.text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── API: TICKER TAPE ──
@app.route('/api/ticker-tape')
def api_ticker_tape():
    try:
        tickers = ["NVDA","AAPL","GOOGL","TSLA","MSFT","BTC-USD","AMZN","META"]
        data = yf.download(tickers, period="2d", progress=False, auto_adjust=True)
        closes = data['Close']
        items = []
        for t in tickers:
            try:
                prev, last = float(closes[t].iloc[-2]), float(closes[t].iloc[-1])
                pct = (last - prev) / prev * 100
                items.append({'sym': t, 'price': round(last, 2), 'chg': round(pct, 2)})
            except: pass
        return jsonify(items)
    except:
        return jsonify([])

# ── ADMIN PANEL ──
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('admin') != True:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        pw = request.form.get('password', '')
        if pw == "admin123":
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        flash('Invalid admin password', 'error')
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    users = get_all_users()
    notifs = get_notifications()
    return render_template('admin_dashboard.html', users=users, notifs=notifs)

@app.route('/admin/notify', methods=['POST'])
@admin_required
def admin_notify():
    subject = request.form.get('subject')
    msg = request.form.get('message')
    if subject and msg:
        emails = get_verified_emails()
        success = 0
        for email in emails:
            html = f"<html><body><h3>{subject}</h3><p>{msg}</p></body></html>"
            if send_email(email, subject, html):
                success += 1
        log_notification(subject, msg, success)
        flash(f'Notification sent to {success} users.', 'success')
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
