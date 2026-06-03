import joblib
from scipy.sparse import hstack
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from urllib.parse import urlparse
import math
from collections import Counter
import re

# ================== HELPERS ==================
def get_domain(url):
    try:
        if not url.startswith(("http://", "https://")):
            url = "http://" + url

        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        domain = domain.split(":")[0]

        if domain.startswith("www."):
            domain = domain[4:]

        return domain
    except:
        return ""

# ================== FIX A HELPERS ==================
BRANDS = [
    "google", "paypal", "amazon", "microsoft",
    "apple", "facebook", "instagram", "netflix"
]

def brand_mismatch(url, domain):
    for brand in BRANDS:
        if brand in url.lower() and brand not in domain:
            return True
    return False

# ================== FIX B HELPER ==================
def too_many_subdomains(domain):
    return domain.count('.') >= 4

# ================== APP ==================
app = Flask(__name__)
CORS(app)

# ================== MODELS ==================
rf_model = joblib.load('models/rf_model.pkl')
lr_model = joblib.load('models/lr_model.pkl')
svm_model = joblib.load('models/svm_model.pkl')
vectorizer_level1 = joblib.load('models/tfidf_vectorizer_level1.pkl')

vectorizer_level2 = joblib.load('models/tfidf_vectorizer_level2.pkl')
kmeans_level2 = joblib.load('models/kmeans_level2.pkl')
scaler_level2 = joblib.load('models/numeric_scaler_level2.pkl')

# ================== WHITELIST ==================
WHITELIST_DOMAINS = {
    "google.com",
    "accounts.google.com",
    "mail.google.com",
    "youtube.com",
    "github.com",
    "openai.com",
    "amazon.com",
    "aws.amazon.com",
    "microsoft.com",
    "login.microsoftonline.com",
    "apple.com",
    "icloud.com",
    "facebook.com",
    "instagram.com",
    "whatsapp.com",
    "linkedin.com",
    "paypal.com",
    "netflix.com",
    "spotify.com",
    "zoom.us"
}

BLACKLIST_DOMAINS = {
    "goog1e.com",
    "g00gle-login.com",
    "secure-google-login.net",
    "paypal-verification-alert.com",
    "amazon-security-update.com",
    "account-update-login.com",
    "login-alert-support.com",
    "verify-now-secure.com",
    "banking-secure-login.net",
    "free-gift-cards.com",
    "claim-your-prize-now.com",
    "update-your-account-info.com",
    "login-authentication-required.com",
    "confirm-payment-details.com",
    "security-check-required.com",
    "reset-password-now.com",
    "limited-time-reward.com",
    "verify-identity-now.net",
    "account-suspended-alert.com",
    "secure-access-portal.net"
}

def is_whitelisted(domain):
    return any(domain == d or domain.endswith("." + d) for d in WHITELIST_DOMAINS)

def is_blacklisted(domain):
    return any(domain == d or domain.endswith("." + d) for d in BLACKLIST_DOMAINS)

# ================== CLUSTER MAPPING ==================
terms = vectorizer_level2.get_feature_names_out()
centroids = kmeans_level2.cluster_centers_[:, :len(terms)]

subtypes = {
    'freebie': ['free', 'gift', 'bonus', 'reward', 'win', 'prize'],
    'redirect': ['redirect', 'goto', 'login', 'secure'],
    'malware': ['download', 'exe', 'zip', 'patch', 'update', 'alert', 'file', 'virus'],
    'IDN': [chr(i) for i in range(128, 256)]
}

cluster_mapping = {}
for i in range(kmeans_level2.n_clusters):
    centroid = centroids[i]
    scores = {k: 0.0 for k in subtypes}

    for idx, weight in enumerate(centroid):
        term = terms[idx]
        for subtype, keywords in subtypes.items():
            if any(k in term for k in keywords):
                scores[subtype] += weight

    top_terms = [terms[idx] for idx in centroid.argsort()[-20:]]
    if any(ord(c) > 127 for c in ''.join(top_terms)):
        cluster_mapping[i] = 'IDN'
    elif max(scores.values()) > 0:
        cluster_mapping[i] = max(scores, key=scores.get)
    else:
        cluster_mapping[i] = 'suspicious'

# ================== FEATURES ==================
def extract_numeric_features(url):
    length = len(url)
    digits = sum(c.isdigit() for c in url)
    special = sum(c in "-_./?=&" for c in url)
    ext = int(url.lower().endswith(('.exe', '.zip', '.scr', '.bat', '.dll')))
    return np.array([[length, digits, special, ext]])

# ================== ENTROPY ==================
def get_entropy_target(url):
    parsed = urlparse(url)
    return (parsed.netloc + parsed.path).lower()

def calculate_entropy(s):
    if not s:
        return 0
    counts = Counter(s)
    length = len(s)
    entropy = 0
    for count in counts.values():
        p = count / length
        entropy -= p * math.log2(p)
    return entropy

# ================== FIX D ==================
SUSPICIOUS_TLDS = (".tk", ".ml", ".ga", ".cf", ".gq", ".xyz", ".click")

# ================== PREDICTION ==================
def predict_url(url):
    domain = get_domain(url)
    print("URL:", url, "| DOMAIN:", domain)

    # ✅ WHITELIST
    if is_whitelisted(domain):
        return {"type": "legitimate", "risk_percent": 0, "source": "whitelist"}

    # ---------- FIX A: BRAND MISMATCH ----------
    if brand_mismatch(url, domain):
        return {"type": "phishing", "risk_percent": 90, "source": "brand_mismatch"}

    # ---------- FIX B: SUBDOMAIN DEPTH ----------
    if too_many_subdomains(domain):
        return {"type": "phishing", "risk_percent": 80, "source": "subdomain_depth"}

    # ---------- ENTROPY ----------
    entropy = calculate_entropy(get_entropy_target(url))
    if entropy > 4.2:
        return {"type": "phishing", "risk_percent": 85, "source": "high_entropy"}

    # ---------- LEVEL 1 ----------
    X1 = vectorizer_level1.transform([url])
    rf_prob = rf_model.predict_proba(X1)[0][1]
    lr_prob = lr_model.predict_proba(X1)[0][1]
    svm_prob = svm_model.predict_proba(X1)[0][1]

    risk_score = (0.4 * rf_prob + 0.4 * lr_prob + 0.2 * svm_prob)
    risk_percent = round(risk_score * 100, 2)

    # ---------- FIX D: SUSPICIOUS TLD BOOST ----------
    if domain.endswith(SUSPICIOUS_TLDS):
        risk_percent = min(risk_percent + 10, 100)

    LOW_RISK = 0.40
    PHISHING_THRESHOLD = 0.65

    if risk_score < LOW_RISK:
        return {"type": "legitimate", "risk_percent": 0}

    if risk_score < PHISHING_THRESHOLD:
        return {"type": "legitimate", "risk_percent": risk_percent}

    # ---------- LEVEL 2 ----------
    X2_text = vectorizer_level2.transform([url])
    X2_num = scaler_level2.transform(extract_numeric_features(url))
    X2 = hstack([X2_text, X2_num])

    cluster = kmeans_level2.predict(X2)[0]
    subtype = cluster_mapping.get(cluster, "suspicious")

    return {"type": "phishing", "risk_percent": risk_percent, "subtype": subtype}

# ================== ROUTES ==================
@app.route('/predict', methods=['POST'])
def predict_endpoint():
    data = request.get_json()
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "URL is required"}), 400
    return jsonify(predict_url(url))

@app.route('/')
def home():
    return {"message": "URL Classifier Backend Running"}

if __name__ == '__main__':
    app.run(debug=True)