// AI Stock Pro — Client-side JavaScript (Flask Version)

// ── TICKER TAPE ──
function buildTape(data) {
  const tape = document.getElementById('tape');
  if (!tape || !data.length) return;
  let html = '';
  for (let r = 0; r < 2; r++) {
    data.forEach(t => {
      const cls = t.chg >= 0 ? 'up' : 'down';
      const arrow = t.chg >= 0 ? '▲' : '▼';
      html += `<span class="tape-item"><span class="sym">${t.sym}</span><span class="price">$${t.price}</span><span class="chg ${cls}">${arrow} ${t.chg >= 0 ? '+' : ''}${t.chg.toFixed(2)}%</span></span>`;
    });
  }
  tape.innerHTML = html;
}

function loadTape() {
  fetch('/api/ticker-tape').then(r => r.json()).then(data => buildTape(data)).catch(() => {});
}

// ── CHIPS ──
function setTicker(val) {
  const input = document.getElementById('tickerInput');
  if (input) { input.value = val; input.focus(); }
}

function analyzeTicker() {
  const input = document.getElementById('tickerInput');
  if (!input) return;
  const t = input.value.trim().toUpperCase() || 'GOOGL';
  window.location.href = '/dashboard?ticker=' + encodeURIComponent(t);
}

// ── OTP FLOW ──
function sendOTP(url, emailId, btnId, extraFields) {
  const email = document.getElementById(emailId)?.value;
  if (!email || !email.includes('@')) { showAlert('Enter a valid email.', 'error'); return; }
  const btn = document.getElementById(btnId);
  if (btn) { btn.disabled = true; btn.textContent = 'Sending...'; }
  const body = { email, ...extraFields };
  fetch(url, {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body)
  })
  .then(r => r.json())
  .then(data => {
    if (data.success) {
      showAlert(data.message, 'success');
      const otpSection = document.getElementById('otp-section');
      if (otpSection) otpSection.classList.remove('hidden');
    } else {
      showAlert(data.message, 'error');
    }
  })
  .catch(() => showAlert('Network error.', 'error'))
  .finally(() => { if (btn) { btn.disabled = false; btn.textContent = 'Send OTP'; } });
}

// ── ALERT HELPER ──
function showAlert(msg, type) {
  const container = document.getElementById('alert-container');
  if (!container) return;
  const icon = type === 'success' ? '✓' : type === 'error' ? '✕' : 'ⓘ';
  container.innerHTML = `<div class="alert alert-${type}">${icon} ${msg}</div>`;
  setTimeout(() => { if (container.firstChild) container.firstChild.remove(); }, 5000);
}

// ── PLOTLY DARK THEME ──
const PLOTLY_LAYOUT = {
  paper_bgcolor: '#0d1526', plot_bgcolor: '#0d1526',
  font: { family: 'Syne, sans-serif', color: '#b0c4de', size: 11 },
  xaxis: { gridcolor: '#1e2d50', linecolor: '#1e2d50', zerolinecolor: '#1e2d50' },
  yaxis: { gridcolor: '#1e2d50', linecolor: '#1e2d50', zerolinecolor: '#1e2d50' },
  margin: { l: 50, r: 20, t: 40, b: 40 },
  legend: { bgcolor: 'rgba(13,21,38,0.8)', bordercolor: '#1e2d50', font: { color: '#b0c4de', size: 10 } },
};

const PLOTLY_CONFIG = { responsive: true, displayModeBar: true, displaylogo: false,
  modeBarButtonsToRemove: ['lasso2d', 'select2d'] };

function plotlyDarkLayout(overrides) {
  return { ...PLOTLY_LAYOUT, ...overrides,
    xaxis: { ...PLOTLY_LAYOUT.xaxis, ...(overrides?.xaxis || {}) },
    yaxis: { ...PLOTLY_LAYOUT.yaxis, ...(overrides?.yaxis || {}) }
  };
}

// ── GLOSSARY TOGGLE ──
function toggleGlossary(el) {
  const cat = el.closest('.glossary-category');
  if (cat) cat.classList.toggle('collapsed');
}

// ── INIT ──
document.addEventListener('DOMContentLoaded', () => {
  loadTape();
  const tickerInput = document.getElementById('tickerInput');
  if (tickerInput) {
    tickerInput.addEventListener('keydown', e => { if (e.key === 'Enter') analyzeTicker(); });
  }
});
