import os
import json
import csv
import io
import math
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# -------------------------------------------------------------
# In-memory analytics engine for E-Commerce Events
# -------------------------------------------------------------
def analyze_events_csv(csv_text_or_file):
    reader = csv.DictReader(io.StringIO(csv_text_or_file) if isinstance(csv_text_or_file, str) else csv_text_or_file)
    rows = list(reader)
    if not rows:
        return {"error": "Empty dataset"}
    
    total_events = len(rows)
    sessions = set()
    users = set()
    events_counter = {}
    purchases = 0
    total_revenue = 0.0
    
    # Stages for funnel
    session_stages = {} # session_id -> set of events
    device_metrics = {} # device -> {sessions: set(), purchases: 0}
    channel_metrics = {} # channel -> {sessions: set(), purchases: 0, rev: 0}
    user_txs = {} # user -> {count: 0, rev: 0, last_date: ''}
    
    for r in rows:
        sess = r.get('session_id') or r.get('user_pseudo_id') or r.get('user_id') or 'unknown'
        user = r.get('user_pseudo_id') or r.get('user_id') or 'unknown'
        ev = r.get('event_name') or r.get('event_type') or ''
        dev = r.get('device_category') or r.get('device') or 'desktop'
        ch = r.get('traffic_medium') or r.get('traffic_source') or r.get('channel') or 'direct'
        
        # Revenue extraction
        rev_raw = r.get('purchase_revenue') or r.get('amount') or r.get('price') or 0.0
        try:
            rev = float(rev_raw) if rev_raw and str(rev_raw).strip() != '' else 0.0
        except ValueError:
            rev = 0.0
            
        dt = r.get('event_date') or r.get('event_timestamp') or ''
        
        sessions.add(sess)
        users.add(user)
        events_counter[ev] = events_counter.get(ev, 0) + 1
        
        if sess not in session_stages:
            session_stages[sess] = set()
        session_stages[sess].add(ev)
        
        if dev not in device_metrics:
            device_metrics[dev] = {'sessions': set(), 'purchases': 0}
        device_metrics[dev]['sessions'].add(sess)
        
        if ch not in channel_metrics:
            channel_metrics[ch] = {'sessions': set(), 'purchases': 0, 'revenue': 0.0}
        channel_metrics[ch]['sessions'].add(sess)
        
        if ev == 'purchase':
            purchases += 1
            total_revenue += rev
            device_metrics[dev]['purchases'] += 1
            channel_metrics[ch]['purchases'] += 1
            channel_metrics[ch]['revenue'] += rev
            
            if user not in user_txs:
                user_txs[user] = {'count': 0, 'rev': 0.0, 'last_date': dt}
            user_txs[user]['count'] += 1
            user_txs[user]['rev'] += rev
            user_txs[user]['last_date'] = max(user_txs[user]['last_date'], dt)

    # Funnel calculation - detect available stage names
    all_events = set(events_counter.keys())
    candidate_stages = [
        ['session_start', 'page_view', 'view_item'],
        ['view_item', 'product_view', 'page_view'],
        ['add_to_cart'],
        ['begin_checkout', 'checkout_start', 'payment_info'],
        ['purchase']
    ]
    
    stages = []
    for cand_group in candidate_stages:
        matched = next((c for c in cand_group if c in all_events), None)
        if matched and matched not in stages:
            stages.append(matched)
            
    if not stages:
        stages = sorted(list(all_events))[:5]
        
    funnel = []
    top_n = len(sessions)
    prev_n = top_n
    
    for s in stages:
        n = sum(1 for sess_id, s_events in session_stages.items() if s in s_events)
        pct_top = round(100.0 * n / top_n, 2) if top_n > 0 else 0
        step_drop = round(100.0 * (1.0 - (n / prev_n)), 2) if prev_n > 0 else 0
        funnel.append({
            "stage": s,
            "sessions": n,
            "pct_of_top": pct_top,
            "drop_off": step_drop
        })
        prev_n = n

    # Device table
    dev_table = []
    for d, val in device_metrics.items():
        s_cnt = len(val['sessions'])
        p_cnt = val['purchases']
        cvr = round(100.0 * p_cnt / s_cnt, 2) if s_cnt > 0 else 0
        dev_table.append({
            "device": d,
            "sessions": s_cnt,
            "purchases": p_cnt,
            "cvr": cvr
        })
    dev_table.sort(key=lambda x: x['sessions'], reverse=True)

    # Channel table
    ch_table = []
    for c, val in channel_metrics.items():
        s_cnt = len(val['sessions'])
        p_cnt = val['purchases']
        cvr = round(100.0 * p_cnt / s_cnt, 2) if s_cnt > 0 else 0
        ch_table.append({
            "channel": c,
            "sessions": s_cnt,
            "purchases": p_cnt,
            "revenue": round(val['revenue'], 2),
            "cvr": cvr
        })
    ch_table.sort(key=lambda x: x['revenue'], reverse=True)

    return {
        "kpis": {
            "total_events": total_events,
            "unique_sessions": len(sessions),
            "unique_users": len(users),
            "purchases": purchases,
            "total_revenue": round(total_revenue, 2),
            "cvr": round(100.0 * purchases / len(sessions), 2) if sessions else 0,
            "aov": round(total_revenue / purchases, 2) if purchases else 0
        },
        "funnel": funnel,
        "device_breakdown": dev_table,
        "channel_breakdown": ch_table
    }

# -------------------------------------------------------------
# Embedded Web Application HTML & JS (No external build tools)
# -------------------------------------------------------------
HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Product Growth Intelligence Tool | Interactive Analytics</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0b0f19;
      --card: #131b2e;
      --card-border: rgba(255, 255, 255, 0.08);
      --primary: #3b82f6;
      --accent: #8b5cf6;
      --text: #f3f4f6;
      --text-muted: #94a3b8;
      --danger: #ef4444;
      --success: #10b981;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Plus Jakarta Sans', sans-serif;
      background: var(--bg);
      color: var(--text);
      display: flex;
      min-height: 100vh;
    }
    aside {
      width: 320px;
      background: #0f172a;
      border-right: 1px solid var(--card-border);
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }
    main {
      flex: 1;
      padding: 30px;
      overflow-y: auto;
    }
    h1 { font-size: 1.6rem; font-weight: 800; color: #fff; margin-bottom: 4px; }
    h2 { font-size: 1.25rem; font-weight: 700; margin: 30px 0 16px; display: flex; align-items: center; gap: 8px; }
    .btn {
      display: inline-flex; align-items: center; justify-content: center; gap: 8px;
      background: linear-gradient(135deg, var(--primary), var(--accent));
      color: white; border: none; padding: 12px 18px; border-radius: 8px;
      font-weight: 700; cursor: pointer; font-size: 0.95rem; width: 100%;
      transition: opacity 0.2s;
    }
    .btn:hover { opacity: 0.9; }
    .file-drop {
      border: 2px dashed rgba(255, 255, 255, 0.2);
      border-radius: 10px; padding: 20px; text-align: center;
      cursor: pointer; background: rgba(255, 255, 255, 0.02);
      font-size: 0.85rem; color: var(--text-muted);
    }
    .file-drop input { display: none; }
    .kpi-grid {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px; margin-bottom: 24px;
    }
    .kpi-card {
      background: var(--card); border: 1px solid var(--card-border);
      border-radius: 12px; padding: 18px;
    }
    .kpi-label { font-size: 0.75rem; text-transform: uppercase; color: var(--text-muted); font-weight: 600; }
    .kpi-val { font-size: 1.8rem; font-weight: 800; color: #fff; margin-top: 6px; }
    .grid-2 {
      display: grid; grid-template-columns: 1fr 1fr; gap: 20px;
    }
    .panel {
      background: var(--card); border: 1px solid var(--card-border);
      border-radius: 14px; padding: 20px; margin-bottom: 20px;
    }
    table { width: 100%; border-collapse: collapse; font-size: 0.9rem; text-align: left; }
    th, td { padding: 10px 14px; border-bottom: 1px solid var(--card-border); }
    th { color: var(--text-muted); font-weight: 600; }
    .badge-drop { background: rgba(239, 68, 68, 0.15); color: var(--danger); padding: 3px 8px; border-radius: 4px; font-weight: 700; }
    .ab-box {
      background: rgba(59, 130, 246, 0.08); border: 1px solid rgba(59, 130, 246, 0.3);
      padding: 16px; border-radius: 10px; margin-top: 15px;
    }
  </style>
</head>
<body>

  <aside>
    <div>
      <h1>🛒 Growth Intelligence</h1>
      <p style="font-size: 0.8rem; color: var(--text-muted);">Interactive E-Commerce Tool</p>
    </div>

    <div>
      <label style="font-size: 0.85rem; font-weight: 600; display: block; margin-bottom: 8px;">Upload Event Dataset (CSV)</label>
      <label class="file-drop" id="dropArea">
        <i class="fa-solid fa-cloud-arrow-up" style="font-size: 1.8rem; margin-bottom: 8px; color: var(--primary);"></i>
        <div id="fileLabel">Drop CSV or Click to Browse</div>
        <input type="file" id="csvFileInput" accept=".csv">
      </label>
    </div>

    <button class="btn" onclick="loadRealData()" style="margin-bottom: 10px; background: linear-gradient(135deg, #10b981, #059669);">
      <i class="fa-solid fa-chart-line"></i> Load Real E-Commerce Dataset
    </button>

    <button class="btn" onclick="loadSampleData()" style="background: rgba(255, 255, 255, 0.08); border: 1px solid var(--card-border);">
      <i class="fa-solid fa-database"></i> Load GA4 Sample Dataset
    </button>

    <div style="font-size: 0.8rem; color: var(--text-muted); line-height: 1.5; margin-top: auto; border-top: 1px solid var(--card-border); padding-top: 16px;">
      <strong>Dev Chahar</strong><br>
      Manipal University Jaipur<br>
      Reg: 23FE10CSE00291<br>
      <a href="https://github.com/devchahar-byte/product-growth-intelligence" target="_blank" style="color: var(--primary); text-decoration: none;">GitHub Repository</a>
    </div>
  </aside>

  <main>
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-label">Total Sessions</div>
        <div class="kpi-val" id="kpiSessions">-</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Unique Users</div>
        <div class="kpi-val" id="kpiUsers">-</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Total Purchases</div>
        <div class="kpi-val" id="kpiPurchases">-</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Overall CVR</div>
        <div class="kpi-val" id="kpiCVR" style="color: var(--success);">-</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Total Revenue</div>
        <div class="kpi-val" id="kpiRev">-</div>
      </div>
    </div>

    <!-- Funnel Section -->
    <h2><i class="fa-solid fa-filter"></i> 1. Dynamic Conversion Funnel</h2>
    <div class="grid-2">
      <div class="panel">
        <canvas id="funnelChart" height="220"></canvas>
      </div>
      <div class="panel">
        <table id="funnelTable">
          <thead>
            <tr><th>Stage</th><th>Sessions</th><th>% of Top</th><th>Step Drop</th></tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
    </div>

    <!-- Channel & Device -->
    <h2><i class="fa-solid fa-chart-column"></i> 2. Segment Analysis & Acquisition Channels</h2>
    <div class="grid-2">
      <div class="panel">
        <h3 style="font-size: 1rem; margin-bottom: 12px;">Mobile vs. Desktop Disparity</h3>
        <canvas id="deviceChart" height="200"></canvas>
      </div>
      <div class="panel">
        <h3 style="font-size: 1rem; margin-bottom: 12px;">Channel Revenue & CVR</h3>
        <table id="channelTable">
          <thead>
            <tr><th>Channel</th><th>Sessions</th><th>Purchases</th><th>CVR</th><th>Revenue</th></tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
    </div>

    <!-- A/B Test Sizing Calculator -->
    <h2><i class="fa-solid fa-calculator"></i> 3. Live A/B Experiment Calculator</h2>
    <div class="panel">
      <p style="color: var(--text-muted); font-size: 0.9rem; margin-bottom: 15px;">Calculate sample size required to validate mobile checkout improvements or evaluate test results dynamically.</p>
      <div class="grid-2">
        <div>
          <label style="font-size: 0.85rem; font-weight: 600;">Minimum Detectable Effect (Lift %)</label>
          <input type="range" id="mdeInput" min="5" max="40" value="15" style="width: 100%; margin: 8px 0;" oninput="updateSampleCalc()">
          <div style="font-size: 0.85rem; color: var(--primary); font-weight: 700;" id="mdeLabel">15% relative lift</div>
          <div class="ab-box" id="sampleSizeResult">Calculating sample size...</div>
        </div>
        <div>
          <label style="font-size: 0.85rem; font-weight: 600;">Run Two-Proportion Significance Test</label>
          <div style="display: flex; gap: 10px; margin-top: 8px;">
            <input type="number" id="ctrlConv" value="120" style="padding: 6px; width: 48%; background: #0b0f19; color: #fff; border: 1px solid var(--card-border); border-radius: 6px;" placeholder="Control Purchases">
            <input type="number" id="treatConv" value="160" style="padding: 6px; width: 48%; background: #0b0f19; color: #fff; border: 1px solid var(--card-border); border-radius: 6px;" placeholder="Treatment Purchases">
          </div>
          <button class="btn" style="margin-top: 10px;" onclick="runZTest()">Compute Z-Score & P-Value</button>
          <div id="zTestResult" style="margin-top: 10px; font-size: 0.85rem; font-weight: 600;"></div>
        </div>
      </div>
    </div>
  </main>

  <script>
    let funnelChartInstance = null;
    let deviceChartInstance = null;
    let currentData = null;

    async function loadRealData() {
      document.getElementById('fileLabel').innerText = "Loading real production dataset...";
      const resp = await fetch('/api/real');
      const data = await resp.json();
      renderDashboard(data);
      document.getElementById('fileLabel').innerText = "Real E-Commerce Dataset Loaded";
    }

    async function loadSampleData() {
      document.getElementById('fileLabel').innerText = "Loading GA4 sample dataset...";
      const resp = await fetch('/api/sample');
      const data = await resp.json();
      renderDashboard(data);
      document.getElementById('fileLabel').innerText = "GA4 Sample Loaded";
    }

    document.getElementById('csvFileInput').addEventListener('change', function(e) {
      const file = e.target.files[0];
      if (!file) return;
      document.getElementById('fileLabel').innerText = file.name;
      const reader = new FileReader();
      reader.onload = async function(evt) {
        const text = evt.target.result;
        const resp = await fetch('/api/analyze', {
          method: 'POST',
          headers: {'Content-Type': 'text/plain'},
          body: text
        });
        const data = await resp.json();
        renderDashboard(data);
      };
      reader.readAsText(file);
    });

    function renderDashboard(data) {
      currentData = data;
      // KPIs
      document.getElementById('kpiSessions').innerText = data.kpis.unique_sessions.toLocaleString();
      document.getElementById('kpiUsers').innerText = data.kpis.unique_users.toLocaleString();
      document.getElementById('kpiPurchases').innerText = data.kpis.purchases.toLocaleString();
      document.getElementById('kpiCVR').innerText = data.kpis.cvr + '%';
      document.getElementById('kpiRev').innerText = '$' + data.kpis.total_revenue.toLocaleString();

      // Funnel Chart
      const stages = data.funnel.map(f => f.stage);
      const counts = data.funnel.map(f => f.sessions);

      if (funnelChartInstance) funnelChartInstance.destroy();
      const ctxF = document.getElementById('funnelChart').getContext('2d');
      funnelChartInstance = new Chart(ctxF, {
        type: 'bar',
        data: {
          labels: stages,
          datasets: [{
            label: 'Sessions',
            data: counts,
            backgroundColor: '#3b82f6',
            borderRadius: 6
          }]
        },
        options: {
          indexAxis: 'y',
          responsive: true,
          plugins: { legend: { display: false } }
        }
      });

      // Funnel Table
      const fBody = document.querySelector('#funnelTable tbody');
      fBody.innerHTML = '';
      data.funnel.forEach(f => {
        fBody.innerHTML += `<tr>
          <td><strong>${f.stage}</strong></td>
          <td>${f.sessions.toLocaleString()}</td>
          <td>${f.pct_of_top}%</td>
          <td>${f.drop_off > 0 ? `<span class="badge-drop">-${f.drop_off}%</span>` : '—'}</td>
        </tr>`;
      });

      // Device Chart
      if (deviceChartInstance) deviceChartInstance.destroy();
      const ctxD = document.getElementById('deviceChart').getContext('2d');
      deviceChartInstance = new Chart(ctxD, {
        type: 'bar',
        data: {
          labels: data.device_breakdown.map(d => d.device),
          datasets: [{
            label: 'Conversion Rate (%)',
            data: data.device_breakdown.map(d => d.cvr),
            backgroundColor: ['#ef4444', '#10b981', '#f59e0b'],
            borderRadius: 6
          }]
        },
        options: {
          responsive: true,
          plugins: { legend: { display: false } },
          scales: { y: { beginAtZero: true } }
        }
      });

      // Channel Table
      const cBody = document.querySelector('#channelTable tbody');
      cBody.innerHTML = '';
      data.channel_breakdown.forEach(c => {
        cBody.innerHTML += `<tr>
          <td><strong>${c.channel}</strong></td>
          <td>${c.sessions.toLocaleString()}</td>
          <td>${c.purchases.toLocaleString()}</td>
          <td style="color: #60a5fa; font-weight: 700;">${c.cvr}%</td>
          <td>$${c.revenue.toLocaleString()}</td>
        </tr>`;
      });

      updateSampleCalc();
    }

    function updateSampleCalc() {
      const mde = document.getElementById('mdeInput').value;
      document.getElementById('mdeLabel').innerText = `${mde}% relative lift`;
      const baseCvr = currentData ? (currentData.kpis.cvr / 100) : 0.02;
      const p1 = baseCvr;
      const p2 = p1 * (1 + mde / 100);
      const zA = 1.96;
      const zB = 0.84;
      const pBar = (p1 + p2) / 2;
      const n = Math.ceil(((zA * Math.sqrt(2 * pBar * (1 - pBar)) + zB * Math.sqrt(p1*(1-p1) + p2*(1-p2)))**2) / (p2 - p1)**2);
      document.getElementById('sampleSizeResult').innerHTML = `
        <strong>Required Sample:</strong> <span style="color: #60a5fa; font-size: 1.1rem;">${n.toLocaleString()}</span> sessions per variant.<br>
        <span style="font-size: 0.8rem; color: var(--text-muted);">Total test: ${(n*2).toLocaleString()} sessions (80% power, 5% alpha).</span>
      `;
    }

    function runZTest() {
      const cA = parseInt(document.getElementById('ctrlConv').value) || 0;
      const cB = parseInt(document.getElementById('treatConv').value) || 0;
      const n = 5000;
      const pA = cA / n;
      const pB = cB / n;
      const pPool = (cA + cB) / (2 * n);
      const se = Math.sqrt(pPool * (1 - pPool) * (2 / n));
      const z = (pB - pA) / se;
      const pVal = 2 * (1 - normalCdf(Math.abs(z)));
      const sig = pVal < 0.05;
      document.getElementById('zTestResult').innerHTML = `
        Z-Score: <strong>${z.toFixed(3)}</strong> | p-value: <strong>${pVal.toFixed(4)}</strong><br>
        <span style="color: ${sig ? 'var(--success)' : 'var(--danger)'};">
          ${sig ? '✅ Statistically Significant (p < 0.05)' : '⚠️ Not Significant (p >= 0.05)'}
        </span>
      `;
    }

    function normalCdf(x) {
      let t = 1 / (1 + 0.2316419 * Math.abs(x));
      let d = 0.3989423 * Math.exp(-x * x / 2);
      let prob = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274))));
      return x > 0 ? 1 - prob : prob;
    }

    // Auto-load on open
    window.onload = loadSampleData;
  </script>
</body>
</html>
"""

# -------------------------------------------------------------
# HTTP Server Request Handler
# -------------------------------------------------------------
class AnalyticsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        if url.path == '/' or url.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode('utf-8'))
        elif url.path == '/api/real':
            real_file = os.path.join(os.path.dirname(__file__), 'data', 'real_ecommerce_events.csv')
            if os.path.exists(real_file):
                with open(real_file, 'r', encoding='utf-8') as f:
                    res = analyze_events_csv(f)
            else:
                res = {"error": "Real dataset file not found"}
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))
        elif url.path == '/api/sample':
            sample_file = os.path.join(os.path.dirname(__file__), 'data', 'sample_ecommerce_events.csv')
            if not os.path.exists(sample_file):
                from python.scripts.generate_sample_data import generate_sample_ecommerce_events
                df = generate_sample_ecommerce_events(n_sessions=6000)
                os.makedirs(os.path.dirname(sample_file), exist_ok=True)
                df.to_csv(sample_file, index=False)
            
            with open(sample_file, 'r', encoding='utf-8') as f:
                res = analyze_events_csv(f)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        url = urlparse(self.path)
        if url.path == '/api/analyze':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            res = analyze_events_csv(body)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

def run_server(port=8501):
    server = HTTPServer(('127.0.0.1', port), AnalyticsHandler)
    print("================================================================")
    print(">> Product Growth Intelligence Tool is running!")
    print(f">> Open in your browser: http://localhost:{port}")
    print("================================================================")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        server.server_close()

if __name__ == '__main__':
    run_server(port=8501)
