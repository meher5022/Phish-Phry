import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split

# Load data
df = pd.read_csv('data/mini_url_dataset.csv')

# Split into train/test (optional but recommended)
train_df, test_df = train_test_split(df, test_size=0.2, random_state=42, stratify=df['type'])

# Fit TF-IDF vectorizer on train URLs
vectorizer = TfidfVectorizer(analyzer='char', ngram_range=(3, 5))
X_train = vectorizer.fit_transform(train_df['url'])
y_train = train_df['type']

# Train models
rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
rf_model.fit(X_train, y_train)

lr_model = LogisticRegression(max_iter=1000, random_state=42)
lr_model.fit(X_train, y_train)

svm_model = SVC(probability=True, random_state=42)
svm_model.fit(X_train, y_train)

# Save models and vectorizer
joblib.dump(rf_model, 'models/rf_model.pkl')
joblib.dump(lr_model, 'models/lr_model.pkl')
joblib.dump(svm_model, 'models/svm_model.pkl')
joblib.dump(vectorizer, 'models/tfidf_vectorizer_level1.pkl')

print("Level 1 Training Complete")
print(f"Training samples: {len(train_df)}")
