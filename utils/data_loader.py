import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
import joblib

def load_data(file_path='data/mini_url_dataset.csv'):
    df = pd.read_csv(file_path)
    return df

def extract_features(df, vectorizer_path='models/vectorizer.pkl'):
    # Use TF-IDF vectorizer on URL text
    vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), max_features=500)
    
    # Fit and transform
    X = vectorizer.fit_transform(df['url'])
    
    # Save the vectorizer for later use in testing
    joblib.dump(vectorizer, vectorizer_path)
    
    return X

def prepare_data(df):
    # Extract features
    X = extract_features(df)
    
    # Get labels
    y = df['type']
    
    # Split into train and test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    return X_train, X_test, y_train, y_test
