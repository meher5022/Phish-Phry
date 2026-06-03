import pandas as pd
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import MiniBatchKMeans
from sklearn.preprocessing import StandardScaler
from scipy.sparse import hstack

# Load phishing URLs from Level 1 output
df = pd.read_csv('models/phishing_urls.csv', names=['url'])

# Numeric features extraction function
def extract_numeric_features(urls):
    features = []
    for url in urls:
        length = len(url)
        digits = sum(c.isdigit() for c in url)
        special = sum(c in "-_./?=&" for c in url)
        ext = 1 if any(url.lower().endswith(e) for e in ['.exe', '.zip', '.scr', '.bat', '.dll']) else 0
        features.append([length, digits, special, ext])
    return np.array(features)

# Extract and scale numeric features
numeric_features = extract_numeric_features(df['url'])
scaler = StandardScaler()
numeric_features_scaled = scaler.fit_transform(numeric_features)

# TF-IDF vectorizer for char n-grams
vectorizer = TfidfVectorizer(analyzer='char', ngram_range=(3, 8), min_df=2, max_df=0.8)
X_text = vectorizer.fit_transform(df['url'])

# Combine text and numeric features
X_combined = hstack([X_text, numeric_features_scaled])

# Cluster using MiniBatchKMeans
num_clusters = 5
kmeans = MiniBatchKMeans(n_clusters=num_clusters, random_state=42, n_init=10)
df['cluster'] = kmeans.fit_predict(X_combined)

# Improved cluster mapping: TF-IDF weighted keyword scoring
terms = vectorizer.get_feature_names_out()
centroids = kmeans.cluster_centers_[:, :len(terms)]  # only TF-IDF part of centroids

subtypes = {
    'freebie': ['free', 'gift', 'bonus', 'reward', 'win', 'prize'],
    'redirect': ['redirect', 'goto', 'login', 'secure'],
    'malware': ['download', 'exe', 'zip', 'patch', 'update', 'alert', 'file', 'virus'],
    'IDN': [chr(i) for i in range(128, 256)]  # extended chars for IDN detection
}

cluster_mapping = {}

for i in range(num_clusters):
    centroid = centroids[i]
    scores = {subtype: 0.0 for subtype in subtypes}
    
    # Weighted scoring by TF-IDF weights
    for idx, weight in enumerate(centroid):
        term = terms[idx]
        for subtype, keywords in subtypes.items():
            if any(keyword in term for keyword in keywords):
                scores[subtype] += weight
    
    # Check for IDN cluster separately using top 20 terms by TF-IDF weight
    top20_idx = centroid.argsort()[-20:][::-1]  # indices of top 20 terms
    top20_terms = [terms[idx] for idx in top20_idx]
    if any(ord(c) > 127 for c in ''.join(top20_terms)):
        cluster_mapping[i] = 'IDN'
    elif max(scores.values()) > 0:
        cluster_mapping[i] = max(scores, key=scores.get)
    else:
        cluster_mapping[i] = 'suspicious'

# Assign phishing subtype labels to URLs
df['phishing_subtype'] = df['cluster'].map(cluster_mapping)

# Save models and labeled data
joblib.dump(vectorizer, 'models/tfidf_vectorizer_level2.pkl')
joblib.dump(scaler, 'models/numeric_scaler_level2.pkl')
joblib.dump(kmeans, 'models/kmeans_level2.pkl')
df.to_csv('models/phishing_labeled_level2.csv', index=False)

print("Level 2 training complete with improved cluster mapping.")
