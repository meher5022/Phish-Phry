import pandas as pd

# Load the dataset
df = pd.read_csv('data/URL dataset.csv')

# Separate phishing and legitimate URLs
phishing_df = df[df['type'] == 'phishing']
legit_df = df[df['type'] == 'legitimate']

# Number of samples per class (50/50 split)
n_samples_per_class = 250  # 500 total / 2

# Randomly sample from each class
phishing_sample = phishing_df.sample(n=n_samples_per_class, random_state=42)
legit_sample = legit_df.sample(n=n_samples_per_class, random_state=42)

# Combine the samples
sampled_df = pd.concat([phishing_sample, legit_sample]).reset_index(drop=True)

# Shuffle the combined dataset
sampled_df = sampled_df.sample(frac=1, random_state=42).reset_index(drop=True)

# Save to CSV
sampled_df.to_csv('data/mini_url_dataset.csv', index=False)

print("Stratified 50/50 sample of 500 rows saved to 'mini_url_dataset.csv'")
