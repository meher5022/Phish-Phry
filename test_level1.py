import pandas as pd
import joblib
from collections import Counter
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix, classification_report

# Load dataset
df = pd.read_csv('data/mini_url_dataset.csv')

# Load models
rf_model = joblib.load('models/rf_model.pkl')
lr_model = joblib.load('models/lr_model.pkl')
svm_model = joblib.load('models/svm_model.pkl')
vectorizer = joblib.load('models/tfidf_vectorizer_level1.pkl')

# Vectorize URLs
X = vectorizer.transform(df['url'])
y_true = df['type']

# Predictions
rf_pred = rf_model.predict(X)
lr_pred = lr_model.predict(X)
svm_pred = svm_model.predict(X)

# Majority voting
def majority_vote(preds):
    return Counter(preds).most_common(1)[0][0]

combined_preds = [
    majority_vote(p)
    for p in zip(rf_pred, lr_pred, svm_pred)
]

# ---- RISK PERCENTAGE CALCULATION ----
# Logistic Regression probability for "phishing"
phishing_prob = lr_model.predict_proba(X)[:, 1]

# Convert to percentage
risk_percent = phishing_prob * 100

# Save results
df['rf_pred'] = rf_pred
df['lr_pred'] = lr_pred
df['svm_pred'] = svm_pred
df['final_pred'] = combined_preds
df['risk_percent'] = risk_percent

df.to_csv('models/level1_test_results.csv', index=False)

# High-confidence phishing
PHISHING_THRESHOLD = 90  # percent

phishing_urls = df[
    (df['final_pred'] == 'phishing') &
    (df['risk_percent'] >= PHISHING_THRESHOLD)
]['url']

phishing_urls.to_csv('models/phishing_urls.csv', index=False)

# Metrics
acc = accuracy_score(y_true, combined_preds)
prec = precision_score(y_true, combined_preds, pos_label='phishing')
rec = recall_score(y_true, combined_preds, pos_label='phishing')
f1 = f1_score(y_true, combined_preds, pos_label='phishing')
cm = confusion_matrix(y_true, combined_preds)

print("Level 1 Testing Complete")
print(f"Accuracy: {acc:.4f}")
print(f"Precision: {prec:.4f}")
print(f"Recall: {rec:.4f}")
print(f"F1 Score: {f1:.4f}")
print("\nConfusion Matrix:\n", cm)
print("\nClassification Report:\n", classification_report(y_true, combined_preds))

print(f"Total URLs: {len(df)}")
print(f"Predicted phishing: {(df['final_pred'] == 'phishing').sum()}")
print(f"High-confidence phishing: {len(phishing_urls)}")