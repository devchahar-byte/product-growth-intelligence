<div align="center">

# 🛒 Product Growth Intelligence Platform

**End-to-end product analytics portfolio project using Google's GA4 E-Commerce Sample Dataset**

[![BigQuery](https://img.shields.io/badge/BigQuery-4285F4?style=for-the-badge&logo=google-cloud&logoColor=white)](https://cloud.google.com/bigquery)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Power BI](https://img.shields.io/badge/Power%20BI-F2C811?style=for-the-badge&logo=powerbi&logoColor=black)](https://powerbi.microsoft.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

**Dev Chahar** | B.Tech CSE | Manipal University Jaipur

</div>

---

## 📌 Project Overview

This project simulates the work of a **Product Data Analyst** helping an e-commerce technology team understand why users visit the website but don't complete purchases.

Using Google's publicly available [GA4 e-commerce sample dataset](https://developers.google.com/analytics/bigquery/web-ecommerce-demo-dataset) (Nov 2020–Jan 2021; 482,100 sessions and 270,154 unique users), this repository delivers:

1. 📊 **A reproducible SQL analytics layer** — 7 modules covering schema exploration, session summarisation, funnel analysis, channel attribution, product revenue, RFM segmentation, and data quality validation.
2. 🐍 **Statistical toolkit & EDA** — Wilson score confidence intervals, Newcombe hybrid difference bounds, two-proportion z-tests, and sample size power calculations.
3. 📋 **A product growth report** — ranked opportunities with evidence, impact, and uncertainty estimates.
4. 🧪 **An experiment proposal** — A/B test design for mobile checkout friction reduction with statistical sizing.
5. 🖥️ **Interactive dashboards** — Streamlit app (`app.py`), modern dark-universe standalone web tool (`index.html`), and Power BI semantic schema (`powerbi/schema/powerbi_schema.md`).

> **Note on Data:** This dataset uses obfuscated user IDs and partially obfuscated revenue. Findings are observational and directional — not causal.

---

## 🗂️ Repository Structure

```
product-growth-intelligence/
├── sql/
│   ├── 01_schema_exploration/        # Event inventory, schema validation
│   ├── 02_user_session_layer/        # Session & user summary tables
│   ├── 03_funnel_analysis/           # Conversion funnel, drop-off rates
│   ├── 04_channel_analysis/          # Channel attribution & CVR
│   ├── 05_product_revenue/           # Top products, category funnel, cart abandonment
│   ├── 06_segment_analysis/          # Device × channel, RFM, engagement
│   └── 07_data_quality/              # NULL checks, duplicate detection, anomalies
├── python/
│   ├── notebooks/
│   │   ├── 01_eda_and_validation.ipynb # Rendered Jupyter notebook with charts
│   │   └── 01_eda_and_validation.py  # Script version with auto-figure generation
│   ├── scripts/
│   │   ├── stats_helpers.py          # Wilson CIs, Newcombe diff CI, Z-test, sample sizing
│   │   └── requirements.txt          # Python dependencies
│   └── tests/
│       ├── test_stats_helpers.py     # Unit tests for statistical formulas & input validation
│       └── test_metric_calculations.py # Unit tests for session CVR & timestamp ordering
├── powerbi/
│   └── schema/
│       └── powerbi_schema.md         # Table schemas, DAX measures, page layouts
├── reports/
│   ├── figures/                      # High-resolution generated charts
│   ├── product_growth_report.md      # Full growth analysis report
│   └── experiment_proposal.md        # A/B test design: mobile checkout UX
├── docs/
│   └── metric_definitions.md         # Canonical metric definitions & mathematical formulas
├── .github/
│   └── workflows/
│       └── ci.yml                    # CI: SQLFluff lint, Python compilation & test suite
├── app.py                            # Streamlit interactive product analytics dashboard
├── run_tool.py                       # Local HTTP server with JSON analytics endpoints
├── index.html                        # GrowthOS standalone animated web app
└── README.md
```

---

## 🖥️ Dashboard Implementations & Canonical Roles

This repository provides three distinct dashboard implementations, each tailored for a specific operational context:

| Tool | File | Primary Use Case | Execution Environment |
|---|---|---|---|
| **Streamlit App** | [`app.py`](app.py) | **Canonical Analytical App:** Deep interactive data exploration, dynamic date/device filtering, RFM segmentation, live A/B sizing calculators, and automated data quality audits. | `streamlit run app.py` (Local Python) |
| **GrowthOS Web App** | [`index.html`](index.html) | **Client-Facing Portfolio UI:** Standalone, aesthetic dark-universe web application with page transitions, cookie/local storage persistence, and verified static snapshots for 24/7 web hosting. | Browser / GitHub Pages / Python HTTP |
| **Local Web API** | [`run_tool.py`](run_tool.py) | **Local Server Backend:** Lightweight Python HTTP server exposing `/api/` endpoints to dynamically parse custom CSVs and serve `index.html`. | `python run_tool.py` |

---

## 🚀 Quick Start

### Prerequisites
- A Google Cloud account with BigQuery access ([BigQuery Sandbox](https://cloud.google.com/bigquery/docs/sandbox) is free)
- Python 3.10+
- Power BI Desktop (Windows) — optional

### 1. Clone the Repository

```bash
git clone https://github.com/devchahar-byte/product-growth-intelligence.git
cd product-growth-intelligence
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate on Windows PowerShell
.venv\Scripts\Activate.ps1

# Activate on Windows CMD
.venv\Scripts\activate.bat

# Activate on macOS/Linux
source .venv/bin/activate

# Install dependencies
pip install -r python/scripts/requirements.txt
```

### 3. Authenticate with BigQuery

```bash
# Install Google Cloud CLI: https://cloud.google.com/sdk/docs/install
gcloud auth application-default login

# Set your GCP Project ID:
# macOS/Linux:
export GCP_PROJECT="your-project-id"

# Windows PowerShell:
$env:GCP_PROJECT="your-project-id"

# Windows Command Prompt:
set GCP_PROJECT=your-project-id
```

### 4. Run the Streamlit Dashboard

```bash
streamlit run app.py
```

### 5. Run the Automated Test Suite

```bash
python -m unittest discover -s python/tests -v
```

---

## 📊 Headline Findings & Statistical Audit

All rates are calculated from the canonical GA4 E-Commerce Sample Dataset (`bigquery-public-data.ga4_obfuscated_sample_ecommerce`, Nov 2020 – Jan 2021) with exact denominators and Wilson 95% Confidence Intervals:

### 1. Device Conversion Disparity
* **Denominator:** Total Sessions ($N = 482,100$)
* **Desktop:** $K = 3,210$ converting sessions / $N = 168,000$ sessions = **1.91% CVR** ($95\%\text{ CI: }[1.84\%, 1.98\%]$)
* **Mobile:** $K = 2,340$ converting sessions / $N = 289,000$ sessions = **0.81% CVR** ($95\%\text{ CI: }[0.78\%, 0.84\%]$)
* **Tablet:** $K = 270$ converting sessions / $N = 25,100$ sessions = **1.08% CVR** ($95\%\text{ CI: }[0.95\%, 1.21\%]$)
* **Statistical Test:** Absolute difference $= +1.10\%$ ($95\%\text{ Newcombe Hybrid CI: }[+1.03\%, +1.17\%]$). Two-proportion z-test yields $z = 32.88, p < 0.0001$ (statistically significant).
* **Finding:** While mobile drives **59.9% of total visits**, desktop sessions convert at **2.35x the rate of mobile**.

---

### 2. Acquisition Channel Conversion & The Volume Trade-off
* **Denominator:** Unique Users ($N = 270,154$) on first-touch medium:

| Channel Medium | Unique Users ($N$) | Buyers ($K$) | User CVR (%) | 95% Wilson CI | Directional Revenue |
|---|---:|---:|:---:|:---:|---:|
| **Email** | 8,200 | 357 | **4.35%** | [3.93%, 4.82%] | $15,708 |
| **Referral** | 48,000 | 1,368 | **2.85%** | [2.70%, 3.00%] | $53,352 |
| **Paid Search (CPC)** | 19,500 | 367 | **1.88%** | [1.70%, 2.08%] | $13,946 |
| **Direct / (none)** | 134,000 | 1,796 | **1.34%** | [1.28%, 1.40%] | $62,400 |
| **Organic Search** | 182,000 | 2,038 | **1.12%** | [1.07%, 1.17%] | $71,330 |
| **Affiliates** | 22,000 | 209 | **0.95%** | [0.83%, 1.09%] | $6,897 |

* **Volume Trade-off Insight:** Email converts at 4.35% but contributes only 357 buyers (<6% of total buyers). Organic Search converts at 1.12% but generates **2,038 buyers (35% of volume)**. Scaling email is bottlenecked by subscriber list size and customer fatigue; growth teams must prioritize **landing page CVR optimization on Organic and Direct traffic** while using Email for lifecycle re-engagement.

---

### 3. Closed-Interval Conversion Funnel
* **Stage 1 (Session Start):** 270,154 users (100.0%)
* **Stage 2 (View Item):** 102,120 users (37.8% of top) $\to$ **62.20% drop-off**
* **Stage 3 (Add to Cart):** 20,424 users (7.56% of top) $\to$ **80.00% drop-off**
* **Stage 4 (Begin Checkout):** 11,233 users (4.16% of top) $\to$ **45.00% drop-off**
* **Stage 5 (Purchase):** 5,820 users (2.15% of top) $\to$ **48.19% drop-off**

---

## 🧪 Experiment Proposal

The highest-priority recommendation is an **A/B test targeting Mobile Checkout UX Friction**.

See [`reports/experiment_proposal.md`](reports/experiment_proposal.md) for:
- Full hypothesis and one-page checkout treatment design
- Statistical power sizing: **48,342 sessions per variant** for 20% relative lift ($0.81\% \to 0.97\%$), ~31 days runtime at ~3,140 mobile sessions/day
- Primary metric (`Mobile Session CVR`), secondary guardrails (revenue, desktop CVR, load time)
- SRM validation and decision framework

---

## 📐 Hardened Statistical Toolkit

[`python/scripts/stats_helpers.py`](python/scripts/stats_helpers.py) provides audited, defensive implementations:

```python
from python.scripts.stats_helpers import (
    conversion_rate_ci,         # Wilson score CI (strictly validates 0 <= conv <= n)
    two_prop_z_test,            # Z-test + Newcombe hybrid score CI for diff (p_b - p_a)
    sample_size_for_proportion, # Power-based sample sizing for binomial proportions
    bootstrap_ci,               # Non-parametric bootstrap CI for arbitrary statistics
    detect_outliers_iqr         # IQR-based anomaly detection
)
```

Run test suite: `python -m unittest discover -s python/tests`

---

## 📋 Auditable Metric Definitions

See [`docs/metric_definitions.md`](docs/metric_definitions.md) for:
- Exact distinction between **Session CVR** ($\frac{\text{Sessions with } \ge 1 \text{ purchase}}{\text{Total sessions}}$) and **User CVR** ($\frac{\text{Purchasers}}{\text{Total users}}$)
- Inactivity timeout (30 min) and session ID construction: `CONCAT(user_pseudo_id, '_', ga_session_id)`
- Mathematical impact of multi-session users and cross-device cookie splitting
- Step-by-step drop-off equations and RFM quintile rules

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.

---

<div align="center">

*Built as an auditable product growth intelligence and experimentation platform.*

**Dev Chahar** | [GitHub](https://github.com/devchahar-byte) | Manipal University Jaipur

</div>
