# 🐡 PhishPhry URL Detector

> A real-time phishing URL detection system built as a Google Chrome browser extension, powered by a local machine learning backend. Hover over any link — PhishPhry tells you if it's safe before you click.

<br>
---

## About the Project

Phishing attacks are responsible for the majority of credential theft, financial fraud, and data breaches reported worldwide each year. Traditional defences — antivirus blacklists and browser warnings — are **reactive**. They only block URLs that have already been identified and reported. A brand new phishing domain can victimise hundreds of users before it ever appears on a blacklist.

**PhishPhry** was built to close this gap.

It is a **proactive, hover-triggered phishing detection system** that analyses every hyperlink you hover over in real-time, before you click. The system uses a weighted ensemble of three machine learning classifiers backed by a two-tier classification architecture — binary detection in Level 1, and specific attack subtype identification in Level 2. Everything runs **entirely on your local machine**. No URL data is ever sent to an external server. No cloud account. No subscription.

This project was developed as a final-year B.Sc. Data Science project at **Thakur College of Science and Commerce, Mumbai** (A.Y. 2025-26).

---

## Key Features

- **Hover-triggered detection** — analyses links before you click, with results in under 200ms
- **Two-tier ML classification** — binary phishing/legitimate (Level 1) + attack subtype identification (Level 2)
- **Multi-layer heuristic defence** — whitelist/blacklist, brand mismatch, Shannon entropy, subdomain depth, suspicious TLD
- **Built-in analytics dashboard** — KPIs, charts, scan logs, dark mode, date/category filters
- **Fully local** — zero data transmitted externally, no cloud dependency, GDPR-friendly
- **Zero infrastructure cost** — 100% open-source stack
- **Sub-second latency** — 50–200ms average for the full pipeline

---

## System Architecture

PhishPhry follows a **three-tier client-server architecture**, all running locally on the user's machine:

```
┌─────────────────────────────────────────────────────────┐
│                  PRESENTATION TIER                      │
│         Chrome Extension (content.js, popup,            │
│                     dashboard)                          │
│         Hover detection · Tooltips · Dashboard UI       │
└────────────────────────┬────────────────────────────────┘
                         │  HTTP POST /predict
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  APPLICATION TIER                       │
│        Flask REST API (app.py) + Service Worker         │
│                   (background.js)                       │
│    Heuristic checks · ML inference · JSON responses     │
└────────────────────────┬────────────────────────────────┘
                         │  joblib.load()
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   DATA / ML TIER                        │
│     Trained .pkl model files · CSV datasets ·           │
│                Chrome local storage                     │
│   Model artefacts · Training data · Session scan logs   │
└─────────────────────────────────────────────────────────┘
```

---

## ML Pipeline

### Feature Engineering — TF-IDF Character N-Grams

Machine learning models can't process raw URL strings directly. PhishPhry converts each URL into a numerical feature vector using **TF-IDF vectorisation applied to character-level n-grams**.

Instead of splitting by words, the system extracts overlapping sequences of characters. F

This is intentional — phishing URLs use character substitutions, hyphens, and encoded strings that defeat word-level tokenisation. Character n-grams catch these patterns naturally.

| Level | N-gram Range | Purpose |
|-------|-------------|---------|
| Level 1 | `(3, 5)` | Binary classification — catches short character tricks |
| Level 2 | `(3, 8)` | Subtype clustering — captures full keywords like `"download"`, `"free-gift"` |

Output is a **high-dimensional sparse matrix** — memory-efficient and directly usable by all three classifiers without dense conversion.

---

### Level 1 — Weighted Ensemble Classifier

Three supervised classifiers are trained independently on TF-IDF features from **5,000 labelled URLs** (80/20 stratified train-test split). Their probability outputs are combined using a weighted formula:

```
Risk Score = (0.40 × Random Forest) + (0.40 × Logistic Regression) + (0.20 × SVM)
```

| Model | Weight | Test Accuracy | Rationale |
|-------|--------|--------------|-----------|
| Random Forest (100 trees) | **40%** | 100.00% | Excellent on sparse TF-IDF; handles high dimensionality |
| Logistic Regression | **40%** | 99.22% | Stable, well-calibrated probabilities on sparse data |
| Support Vector Machine | **20%** | 99.80% | Refines boundaries but sensitive to scaling — lower weight |
| **Weighted Ensemble** | **100%** | **99.80%** | FP = 0 · FN = 10 · F1 = 99.57% |

The risk score maps to three classification tiers:

| Risk Score | Classification | Action |
|-----------|----------------|--------|
| `< 40%` | Legitimate | Green tooltip — safe to click |
| `40% – 65%` | Suspicious | Caution advised |
| `> 65%` | Phishing | Red tooltip + forwarded to Level 2 |

> **Why ensemble over a single model?** Different algorithms capture different URL patterns. Combining them reduces overfitting, lowers bias and variance, and improves generalisation to unseen zero-day phishing URLs.

---

### Level 2 — Phishing Subtype Detection (KMeans)

Once a URL is confirmed as phishing (risk score > 65%), it passes to an **unsupervised KMeans clustering model** that identifies the specific type of attack.

Training corpus: **88 high-confidence phishing URLs** (risk score ≥ 0.90 from the Level 1 test set).

Level 2 uses a combined feature set:
- TF-IDF character n-grams `(3, 8)`
- URL length (character count)
- Digit count
- Special character count (`- _ . / ? = &`)
- Dangerous extension flag (`1` if URL ends in `.exe`, `.zip`, `.scr`, `.bat`, `.dll`)

Numeric features are normalised with `StandardScaler` then concatenated with the TF-IDF sparse matrix using `scipy.sparse.hstack()`.

Cluster centroids are analysed with keyword scoring to assign human-readable labels:

| Subtype | Trigger Keywords | Example |
|---------|-----------------|---------|
| Redirect Attack | `login, secure, goto, verify` | `http://paypal-verification.xyz/login` |
| Freebie / Reward Scam | `free, gift, prize, reward, claim` | `http://free-gift-cards-now.com/claim` |
| Malware Distribution | `exe, zip, download, patch, install` | `http://update-patch.com/fix.exe` |
| IDN Homograph | Non-ASCII Unicode chars in domain | Cyrillic chars mimicking `google.com` |
| Suspicious (default) | No dominant keyword match | Unknown phishing pattern |

---

### Heuristic Pre-Checks

Before any ML model is invoked, every URL passes through **six ordered rule-based checks**. An early return on any match skips all remaining checks and ML inference entirely — keeping latency minimal.

```
Whitelist → Blacklist → Brand Mismatch → Subdomain Depth → Shannon Entropy → Suspicious TLD → [ML Pipeline]
```

| Check | Logic | Catches |
|-------|-------|---------|
|  Whitelist | Domain matches trusted list (`google.com`, `github.com`, etc.) | Returns Legitimate instantly |
|  Blacklist | Domain matches known phishing threat list | Returns Phishing instantly |
|  Brand Mismatch | Brand name in URL path but NOT in actual domain | `paypal-verification.xyz/login` |
|  Subdomain Depth | 4+ dot-separated subdomain levels | `a.b.c.d.malicious.com` |
|  Shannon Entropy | High character randomness in domain = likely auto-generated | `xjz8k2mf9qw.netlify.app` |
|  Suspicious TLD | `.tk` `.ml` `.ga` `.cf` `.gq` `.xyz` `.click` | `free-prize.tk/claim` |

---

## 🧩 Chrome Extension

Built using **Manifest Version 3 (MV3)** — the latest Chrome extension platform. MV3 replaces persistent background pages with service workers that sleep when idle, minimising memory usage.

### Three JavaScript Components

| File | Role |
|------|------|
| `content.js` | Runs on every webpage. Listens for hover events. Manages 500ms debounce. Injects tooltips. Handles custom pufferfish cursor. |
| `background.js` | Service worker. Bridges extension ↔ Flask API. Sends POST requests to `/predict`. Writes scan logs to `chrome.storage.local`. |
| `dashboard.js` | Powers the analytics dashboard tab. Reads from `chrome.storage.local`. Applies filters. Renders KPIs, charts, and scan table. |

### Hover Detection Flow

```
User hovers over link
        ↓
content.js detects mouseover event
        ↓
500ms debounce timer starts
        ↓
Cursor leaves? → Timer cleared, nothing happens
        ↓
Timer fires → check urlCache
        ↓
Cache hit? → Show tooltip instantly (< 1ms)
        ↓
Cache miss → Send CHECK_URL to background.js
        ↓
background.js POSTs URL to Flask /predict
        ↓
Flask returns { type, risk_percent, subtype }
        ↓
content.js injects colour-coded tooltip into DOM
        ↓
Result cached in urlCache + logged to chrome.storage.local
```

### Custom Pufferfish Cursor

`content.js` injects a `<style>` block into every webpage that replaces the default cursor with a pufferfish icon. When a phishing URL is detected, the class `phishphry-danger` is added to `document.body`, switching the cursor to an alert variant — giving the user an instant visual warning before they even read the tooltip text.

---

## Analytics Dashboard

Opens as a new Chrome tab. Reads all data from `chrome.storage.local` — makes zero external network requests.

| Section | Contents |
|---------|----------|
| **Top Bar** | Date range pickers (max 30 days), Apply/Clear Filters, Toggle Dark Mode |
| **Filter Row** | Category multi-select · Manual URL checker · Avg Risk % KPI |
| **KPI Cards** | Total URLs Scanned · Malicious Detected · Safe URLs · Average Risk % |
| **Bar Chart** | Scan category distribution (Safe / Phishing / Malware / IDN) |
| **Pie Chart** | Threat proportion breakdown |
| **Line Chart** | Risk score trend over time |
| **Scan Logs** | Full scrollable table — URL · Category · Status · Timestamp |
| **Dark Mode** | Full dark theme, persisted in `chrome.storage.local` |

---

## 📈 Performance Results

Evaluated on a **held-out test set of 5,000 labelled URLs** (never seen during training):

| Metric | Value |
|--------|-------|
| Accuracy | **99.80%** |
| Precision | **100.00%** |
| Recall | **99.13%** |
| F1 Score | **99.57%** |
| False Positives | **0** |
| False Negatives | 10 |
| Avg API Latency | 50–200ms |
| Extension Memory | < 5 MB |

### Confusion Matrix

```
                    Predicted: Legitimate    Predicted: Phishing
Actual: Legitimate       3,845 (100%)              0 (0%)
Actual: Phishing            10 (0.87%)         1,145 (99.13%)
```

> Zero false positives means no legitimate URL was ever incorrectly flagged across all 3,845 legitimate test URLs — the most critical metric for user trust in a security tool.

---

## Project Structure

```
PhishPhry/
├── app.py                          ← Flask API + full prediction pipeline
├── train_level1.py                 ← Level 1 supervised model training
├── train_level2.py                 ← Level 2 KMeans clustering training
├── test_level1.py                  ← Level 1 model evaluation + metrics
├── requirements.txt                ← Python dependencies
│
├── data/
│   ├── mini_url_dataset.csv        ← Primary dataset (5,000 URLs)
│   ├── mini_url_dataset_50k.csv    ← Extended dataset (50,000 URLs)
│   └── phishing_labeled_level2.csv ← Level 2 subtype labels
│
├── models/
│   ├── rf_model.pkl                ← Trained Random Forest
│   ├── lr_model.pkl                ← Trained Logistic Regression
│   ├── svm_model.pkl               ← Trained SVM
│   ├── tfidf_vectorizer_level1.pkl ← Level 1 TF-IDF vectorizer
│   ├── tfidf_vectorizer_level2.pkl ← Level 2 TF-IDF vectorizer
│   ├── kmeans_level2.pkl           ← KMeans clustering model
│   └── numeric_scaler_level2.pkl   ← StandardScaler for numeric features
│
└── extension/
    ├── manifest.json               ← Chrome MV3 configuration
    ├── background.js               ← Service worker: API bridge + storage
    ├── content.js                  ← Hover detection + tooltip + cursor
    ├── popup.html / popup.js       ← Extension popup interface
    ├── dashboard.html              ← Analytics dashboard page
    ├── dashboard.js                ← Dashboard logic and Chart.js rendering
    └── styles.css                  ← Extension styles
```

---

## Installation & Setup

### Prerequisites

- Python 3.10 or above
- Google Chrome (latest stable, supports MV3)
- ~500 MB free disk space (for model files and datasets)
- Git

---

### Step 1 — Clone the Repository

```bash
git clone https://github.com/your-username/PhishPhry.git
cd PhishPhry
```

---

### Step 2 — Install Python Dependencies

```bash
pip install flask flask-cors joblib numpy scipy scikit-learn pandas
```

Or using the requirements file:

```bash
pip install -r requirements.txt
```

---

### Step 3 — Train the Models (if `.pkl` files are not included)

Train the Level 1 ensemble classifiers:

```bash
python train_level1.py
```

Train the Level 2 KMeans clustering model:

```bash
python train_level2.py
```

> This generates all seven `.pkl` files in the `models/` directory. If pre-trained model files are already present, skip this step.

---

### Step 4 — Start the Flask Backend

```bash
python app.py
```

You should see:

```
* Running on http://127.0.0.1:5000
```

**Keep this terminal open while using the extension.**

To confirm the backend is running, visit `http://127.0.0.1:5000` in your browser — you should see a health check response.

---

### Step 5 — Load the Chrome Extension

1. Open Google Chrome and navigate to `chrome://extensions`
2. Enable **Developer Mode** (toggle in the top-right corner)
3. Click **Load unpacked**
4. Select the `extension/` folder from the project directory
5. The PhishPhry pufferfish icon should appear in your Chrome toolbar

> If the icon isn't visible, click the puzzle piece icon in the toolbar and pin PhishPhry.

---

### Step 6 — Verify Installation

Navigate to any website (e.g. `https://www.google.com`) and hover over a hyperlink. A **green tooltip** labelled ✅ Legitimate should appear within one second.

---

## 🖱️ Usage Guide

### Automatic Hover Detection

PhishPhry works silently in the background once the Flask server is running and the extension is loaded. Simply browse normally — hover over any link to see its classification.

- ✅ **Green tooltip** → URL is safe (Legitimate)
- 🚨 **Red tooltip** → URL is phishing — includes the attack subtype (e.g. `Phishing (redirect)`)
- The pufferfish cursor switches to a **danger state** when a phishing link is detected

### Manual URL Check (via Dashboard)

1. Click the PhishPhry icon in the Chrome toolbar
2. The analytics dashboard opens as a new tab
3. Enter any URL in the **Check URL** field and click **Check**
4. The result appears instantly with the risk percentage

### Scan Current Tab

1. Click the PhishPhry pufferfish icon in the toolbar
2. Click **Scan Current URL** in the popup
3. The classification of the current browser tab's URL is displayed

### Retrain Models with New Data

Replace or update the dataset CSV files in the `data/` directory, then re-run:

```bash
python train_level1.py
python train_level2.py
```

The new `.pkl` files will be loaded automatically the next time `app.py` starts.

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| ML Training | Python, scikit-learn | RandomForest, LogisticRegression, SVM, KMeans |
| Feature Extraction | TF-IDF (char n-grams), NumPy, SciPy | URL vectorisation and sparse matrix ops |
| Backend API | Flask, Flask-CORS, joblib | REST API, model serving, serialisation |
| Browser Extension | JavaScript ES6+, Chrome MV3 | Content script, service worker, popup |
| Dashboard UI | HTML5, CSS3, Chart.js | KPIs, bar/pie/line charts, scan logs |
| Data | pandas, CSV (Kaggle, PhishTank, OpenPhish) | Dataset loading and preprocessing |
| Dev Tools | VS Code, Git, GitHub | Development and version control |

---

## Limitations

- **URL-only analysis** — the system analyses the URL string only. It does not fetch or inspect webpage content, run JavaScript, or check DNS/SSL records.
- **Chrome only** — built for Manifest V3; Firefox and Safari are not currently supported.
- **Requires local Flask** — users must have Python installed and run `app.py` before using the extension.
- **Static models** — `.pkl` files are trained on a fixed dataset snapshot. Models need periodic retraining as phishing patterns evolve.
- **Level 2 dataset skew** — the Level 2 training corpus is dominated by redirect-type attacks (the majority of PhishTank data), which affects subtype diversity.

---

## 👩‍💻 Team
| Meher Vaswani |   
| Prajakta Kambli | 

**Project Guide:** Ms. Femenca Noronha
**Department:** Data Science, Thakur College of Science and Commerce
**University:** University of Mumbai
**Academic Year:** 2025–26

---

<div align="center">

Made with 🐡 by Prajakta & Meher &nbsp;|&nbsp; Thakur College of Science and Commerce, Mumbai &nbsp;|&nbsp; 2025–26

</div>
